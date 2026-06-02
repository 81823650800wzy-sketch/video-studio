#!/usr/bin/env python3
"""
字幕引擎 — 快速字幕处理
========================
源自 auto-caption skill，整合到 Video Studio
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ============================================================
# FFmpeg 路径检测
# ============================================================

def _find_ffmpeg():
    """查找 FFmpeg 路径 (优先 PATH, 再搜索常见位置)"""
    for name in ["ffmpeg", "ffprobe"]:
        found = shutil.which(name)
        if found:
            continue
        winget_base = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
        if winget_base.exists():
            for candidate in winget_base.rglob(f"{name}.exe"):
                os.environ["PATH"] = str(candidate.parent) + os.pathsep + os.environ.get("PATH", "")
                break

_find_ffmpeg()

# ============================================================
# 配置
# ============================================================

CONFIG_DIR = Path.home() / ".claude" / "skills" / "video-studio"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "model": "small",
    "language": "zh",
    "subtitle_style": {
        "font_size": 20,
        "font_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "border_style": 4,
        "margin_v": 50,
    },
    "filler_words": [
        "嗯", "啊", "呃", "哦", "唔", "嘛", "呢", "吧",
        "这个", "那个", "就是说", "然后", "就是", "所以",
        "那个那个", "这个这个", "对吧", "是不是", "对不对",
        "你知道吗", "你懂吗", "说实话", "老实说",
    ],
    "min_segment_duration": 0.5,
    "max_chars_per_line": 20,
    "silence_threshold": 1.5,
}


def load_config():
    """加载配置，从 caption 部分读取"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            full_cfg = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            # 从 caption 部分读取配置
            cfg.update(full_cfg.get("caption", {}))
            return cfg
    return DEFAULT_CONFIG.copy()


# ============================================================
# FFmpeg 工具函数
# ============================================================

def run_ffmpeg(args, desc="", cwd=None):
    """运行 FFmpeg 命令"""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    print(f"  🎬 {desc}...")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"  ⚠️ FFmpeg 警告: {result.stderr[:200]}")
    return result.returncode == 0


def extract_audio(video_path, audio_path):
    """从视频中提取音频为 WAV (16kHz mono, Whisper 需要)"""
    return run_ffmpeg([
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ], "提取音频")


def get_video_duration(video_path):
    """获取视频时长(秒)"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


# ============================================================
# Whisper 转写
# ============================================================

def transcribe_audio(audio_path, model_name="small", language="zh"):
    """使用 Whisper 转写音频，返回分段结果"""
    import whisper

    print(f"  🎙️ 加载 Whisper 模型 '{model_name}' (首次加载会下载)...")
    model = whisper.load_model(model_name)

    print(f"  📝 正在识别语音...")
    result = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        verbose=False,
    )

    return result


# ============================================================
# 字幕生成
# ============================================================

def format_timestamp(seconds):
    """秒 → SRT 时间戳格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def detect_fillers(text, filler_words):
    """检测文本中的语气词，返回 (清理后文本, 找到的语气词列表)"""
    found = []
    cleaned = text
    for word in sorted(filler_words, key=len, reverse=True):
        if word in cleaned:
            found.append(word)
    return cleaned, found


def segments_to_srt(segments, config):
    """Whisper 分段 → SRT 字幕内容"""
    filler_words = config["filler_words"]
    max_chars = config["max_chars_per_line"]
    min_dur = config["min_segment_duration"]

    srt_lines = []
    index = 1
    filler_report = []

    for seg in segments:
        text = seg["text"].strip()
        start = seg["start"]
        end = seg["end"]
        duration = end - start

        if duration < min_dur:
            continue

        if not text:
            continue

        _, fillers = detect_fillers(text, filler_words)
        if fillers:
            filler_report.append({
                "time": format_timestamp(start),
                "text": text,
                "fillers": fillers,
            })

        if len(text) > max_chars:
            parts = re.split(r'([。，！？,.!?])', text)
            lines = []
            current = ""
            for part in parts:
                if len(current + part) <= max_chars:
                    current += part
                else:
                    if current:
                        lines.append(current)
                    current = part
            if current:
                lines.append(current)
            text = "\n".join(lines[:2])

        srt_lines.append(f"{index}")
        srt_lines.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
        srt_lines.append(text)
        srt_lines.append("")
        index += 1

    return "\n".join(srt_lines), filler_report


# ============================================================
# 字幕烧录
# ============================================================

def burn_subtitles(video_path, srt_path, output_path, style_config):
    """将字幕烧录到视频中"""
    style = style_config
    force_style = (
        f"FontSize={style['font_size']},"
        f"PrimaryColour={style['font_color']},"
        f"OutlineColour={style['outline_color']},"
        f"BackColour={style['back_color']},"
        f"BorderStyle={style['border_style']},"
        f"MarginV={style['margin_v']}"
    )

    srt_dir = srt_path.parent
    srt_name = srt_path.name
    return run_ffmpeg([
        "-i", str(video_path),
        "-vf", f"subtitles={srt_name}:force_style='{force_style}'",
        "-c:a", "copy",
        str(output_path),
    ], "烧录字幕到视频", cwd=str(srt_dir))


# ============================================================
# 静音检测
# ============================================================

def detect_silences(video_path, threshold=1.5):
    """检测视频中的长静音段落"""
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-af", f"silencedetect=noise=-30dB:d={threshold}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True)
    stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    silences = []
    for line in stderr_text.split("\n"):
        if "silence_start" in line:
            m = re.search(r"silence_start:\s*([\d.]+)", line)
            if m:
                silences.append({"start": float(m.group(1))})
        if "silence_end" in line and silences:
            m = re.search(r"silence_end:\s*([\d.]+)", line)
            if m:
                silences[-1]["end"] = float(m.group(1))
                silences[-1]["duration"] = silences[-1]["end"] - silences[-1]["start"]
    return silences


# ============================================================
# 主流程
# ============================================================

def open_in_jianying(file_path, jianying_exe):
    """用剪映打开文件"""
    if not jianying_exe or not Path(jianying_exe).exists():
        print(f"  ⚠️ 未找到剪映: {jianying_exe}")
        return False
    print(f"  🎞️ 正在用剪映打开...")
    subprocess.Popen([jianying_exe, str(file_path)],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def process_video(
    video_path,
    model=None,
    language=None,
    srt_only=False,
    burn=False,
    output_dir=None,
    open_jianying=False,
):
    """主函数：处理视频，生成字幕"""

    video_path = Path(video_path).resolve()
    if not video_path.exists():
        print(f"❌ 文件不存在: {video_path}")
        sys.exit(1)

    config = load_config()
    model = model or config["model"]
    language = language or config["language"]
    jianying_path = config.get("jianying_path", "")

    output_dir = Path(output_dir or config.get("output_dir") or video_path.parent)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = video_path.stem
    srt_path = output_dir / f"{stem}.srt"
    transcript_path = output_dir / f"{stem}_transcript.txt"
    report_path = output_dir / f"{stem}_filler_report.json"

    print(f"\n{'='*60}")
    print(f"🎬 Video Studio — 字幕处理")
    print(f"{'='*60}")
    print(f"📹 输入: {video_path}")
    print(f"🤖 模型: {model}")
    print(f"🌐 语言: {language}")
    print(f"📁 输出: {output_dir}")
    print()

    # 1. 提取音频
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.wav"
        if not extract_audio(video_path, audio_path):
            print("❌ 音频提取失败")
            sys.exit(1)

        # 2. Whisper 转写
        result = transcribe_audio(audio_path, model, language)

    # 3. 生成 SRT 字幕
    print(f"  📄 生成 SRT 字幕...")
    segments = result.get("segments", [])
    if not segments:
        print("❌ 未识别到语音内容")
        sys.exit(1)

    srt_content, filler_report = segments_to_srt(segments, config)

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    print(f"  ✅ 字幕文件: {srt_path}")

    # 4. 保存纯文本稿
    full_text = "\n".join(seg["text"].strip() for seg in segments)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"  ✅ 文本文稿: {transcript_path}")

    # 5. 语气词报告
    if filler_report:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(filler_report, f, ensure_ascii=False, indent=2)
        print(f"  📋 发现 {len(filler_report)} 处语气词 → {report_path}")

    # 6. 静音检测
    print(f"  🔇 静音检测...")
    silences = detect_silences(video_path, config["silence_threshold"])
    long_silences = [s for s in silences if s.get("duration", 0) > config["silence_threshold"]]
    if long_silences:
        print(f"  📋 发现 {len(long_silences)} 处长静音 (> {config['silence_threshold']}s)")

    # 7. 字幕烧录 (仅 --burn 模式，非 --srt-only)
    captioned_path = None
    if burn and not srt_only:
        captioned_path = output_dir / f"{stem}_captioned.mp4"
        if burn_subtitles(video_path, srt_path, captioned_path, config["subtitle_style"]):
            print(f"  ✅ 硬字幕成品: {captioned_path}")
        else:
            print(f"  ⚠️ 字幕烧录失败，请用剪映导入 SRT 文件")

    # 8. 总结
    duration = get_video_duration(video_path)
    print(f"\n{'='*60}")
    print(f"✨ 处理完成!")
    print(f"{'='*60}")
    if duration:
        print(f"  🎥 视频时长: {duration:.1f}s")
    print(f"  📝 字幕段数: {len(segments)}")
    print(f"  🗣️  语气词: {len(filler_report)} 处")
    print(f"  🔇 长静音: {len(long_silences)} 处")
    print()

    print(f"  📦 输出文件:")
    print(f"     字幕 → {srt_path}")
    if captioned_path:
        print(f"     成品 → {captioned_path}")
    print(f"     文稿 → {transcript_path}")
    print()
    print(f"  💡 剪映二次编辑步骤:")
    print(f"     1. 打开剪映 → 导入原始视频")
    print(f"     2. 拖入 SRT 字幕文件到字幕轨道")
    print(f"     3. 修正识别错误、调整时间轴、加特效")
    print(f"     4. 导出成品")
    print()

    # 9. 自动打开剪映
    if open_jianying:
        open_in_jianying(str(srt_path), jianying_path)

    print()

    return {
        "srt": str(srt_path),
        "transcript": str(transcript_path),
        "captioned": str(captioned_path) if captioned_path else None,
        "filler_report": filler_report,
        "silences": long_silences,
        "duration": duration,
    }
