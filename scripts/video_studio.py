#!/usr/bin/env python3
"""
Video Studio — 一站式视频制作
==============================
整合字幕处理和视频生产线的统一入口

模式:
  caption  - 快速字幕处理 (原 auto-caption)
  pipeline - 完整视频生产线 (原 video-pipeline)
  mashup   - 智能卡点混剪 (BGM高潮 + 情节冲突 + 特效)
  tts      - TTS语音合成
"""

import argparse
import sys
from pathlib import Path

# 确保能找到同目录下的模块
_SCRIPT_DIR = Path(__file__).parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# 修复 Windows GBK 终端编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def cmd_caption(args):
    """字幕模式 — 快速处理单个视频"""
    from caption_engine import process_video

    result = process_video(
        video_path=args.video,
        model=args.model,
        language=args.language,
        srt_only=args.srt_only,
        burn=args.burn,
        output_dir=args.output_dir,
        open_jianying=not args.no_open,
    )
    return result


def cmd_pipeline(args):
    """生产线模式 — 完整视频制作流程"""
    from pipeline_engine import run_pipeline

    result = run_pipeline(
        project_name=args.project_name,
        images=args.images,
        videos=args.videos,
        inspiration=args.inspiration,
        inspiration_file=args.inspiration_file,
        reference=args.reference,
        style=args.style,
        output=args.output,
        dry_run=args.dry_run,
        no_open=args.no_open,
    )
    return result


def cmd_mashup(args):
    """混剪模式 — 智能卡点混剪"""
    from mashup_engine import run_mashup

    # 加载风格配置
    style = None
    if args.style_config:
        import json
        config_path = Path(args.style_config)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                style = json.load(f)

    result = run_mashup(
        video_paths=args.videos,
        bgm_path=args.bgm,
        output_path=args.output,
        style_profile=style,
        target_duration=args.duration,
        generate_pr=args.pr,
    )
    return result


def cmd_tts(args):
    """TTS模式 — 语音合成"""
    from tts_engine import generate_narration, get_audio_duration, VOICES

    voice_id = VOICES.get(args.voice, {}).get("id", "zh-CN-YunxiNeural")
    path = generate_narration(args.text, args.output, voice_id, args.rate)
    dur = get_audio_duration(path)
    print(f"生成完成: {path} ({dur:.1f}s)")
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Video Studio — 一站式视频制作",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="mode", help="运行模式")

    # ===== caption 子命令 =====
    cap_parser = subparsers.add_parser(
        "caption",
        help="快速字幕处理",
        description="输入视频 → Whisper 语音识别 → 生成 SRT 字幕 → 可选烧录",
    )
    cap_parser.add_argument("video", help="输入视频文件路径")
    cap_parser.add_argument("--model", default=None,
                            choices=["tiny", "base", "small", "medium", "large"],
                            help="Whisper 模型 (默认: small)")
    cap_parser.add_argument("--language", default=None, help="语言 (默认: zh)")
    cap_parser.add_argument("--srt-only", action="store_true",
                            help="只生成 SRT，不烧录字幕")
    cap_parser.add_argument("--burn", action="store_true",
                            help="烧录硬字幕到视频")
    cap_parser.add_argument("--output-dir", default=None,
                            help="输出目录 (默认: E:/)")
    cap_parser.add_argument("--no-open", action="store_true",
                            help="不自动打开剪映")

    # ===== pipeline 子命令 =====
    pipe_parser = subparsers.add_parser(
        "pipeline",
        help="完整视频生产线",
        description="素材 + 灵感文字 → 分析 → 剪辑 → 字幕 → 成品",
    )
    pipe_parser.add_argument("--project-name", default=None,
                             help="项目名称 (默认自动生成)")
    pipe_parser.add_argument("--images", nargs="*", default=[],
                             help="输入图片路径列表")
    pipe_parser.add_argument("--videos", nargs="*", default=[],
                             help="输入视频路径列表")
    pipe_parser.add_argument("--inspiration", default=None,
                             help="灵感文字 (直接输入字符串)")
    pipe_parser.add_argument("--inspiration-file", default=None,
                             help="灵感文字文件路径 (.txt/.md)")
    pipe_parser.add_argument("--reference", nargs="*", default=[],
                             help="参考博主视频链接 (B站/抖音)")
    pipe_parser.add_argument("--style", default="auto",
                             choices=["auto", "bilibili_ai_tutorial", "douyin_short",
                                      "documentary", "review"],
                             help="视频风格 (默认: auto 自动检测)")
    pipe_parser.add_argument("--output", default=None,
                             help="输出目录 (默认: E:/成品/)")
    pipe_parser.add_argument("--dry-run", action="store_true",
                             help="仅分析和规划，不实际生成视频")
    pipe_parser.add_argument("--no-open", action="store_true",
                             help="不自动打开剪映")

    # ===== mashup 子命令 =====
    mashup_parser = subparsers.add_parser(
        "mashup",
        help="智能卡点混剪",
        description="BGM高潮检测 + 情节冲突识别 + 卡点匹配 + 特效剪辑",
    )
    mashup_parser.add_argument("--videos", nargs="+", required=True,
                               help="输入视频列表")
    mashup_parser.add_argument("--bgm", required=True,
                               help="BGM音频文件")
    mashup_parser.add_argument("--output", default="E:/mashup_output.mp4",
                               help="输出路径 (默认: E:/mashup_output.mp4)")
    mashup_parser.add_argument("--duration", type=int, default=60,
                               help="目标时长秒数 (默认: 60)")
    mashup_parser.add_argument("--style-config", default=None,
                               help="风格配置JSON文件")
    mashup_parser.add_argument("--pr", action="store_true",
                               help="生成Premiere Pro工程文件")

    # ===== tts 子命令 =====
    tts_parser = subparsers.add_parser(
        "tts",
        help="TTS语音合成",
        description="生成中文旁白音频",
    )
    tts_parser.add_argument("text", help="要合成的文字")
    tts_parser.add_argument("-o", "--output", default="E:/narration.mp3",
                            help="输出文件 (默认: E:/narration.mp3)")
    tts_parser.add_argument("-v", "--voice", default="yunxi",
                            choices=["yunxi", "yunxia", "yunjian", "xiaoxiao", "xiaoyi"],
                            help="语音选择 (默认: yunxi)")
    tts_parser.add_argument("-r", "--rate", default="+0%",
                            help="语速调节 (如 +10%%, -10%%)")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    if args.mode == "caption":
        cmd_caption(args)
    elif args.mode == "pipeline":
        cmd_pipeline(args)
    elif args.mode == "mashup":
        cmd_mashup(args)
    elif args.mode == "tts":
        cmd_tts(args)


if __name__ == "__main__":
    main()
