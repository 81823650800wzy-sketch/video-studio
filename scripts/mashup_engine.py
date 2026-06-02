#!/usr/bin/env python3
"""
混剪引擎 — 智能卡点混剪
========================
BGM高潮检测 + 情节冲突识别 + 卡点匹配 + 特效剪辑

功能:
1. BGM高潮点检测 (librosa)
2. 视频情节冲突识别 (场景变化 + 音频能量)
3. 智能卡点匹配算法
4. 特效和转场 (FFmpeg)
5. PR工程文件生成 (可选)
6. 风格学习和应用
"""

import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

from pipeline_utils import section, step, ok, warn, fail, ensure_dir, run_ffmpeg


class BGAnalyzer:
    """BGM分析器 - 检测高潮点和节拍"""

    def __init__(self, audio_path):
        self.audio_path = audio_path
        self.tempo = None
        self.beats = []
        self.peaks = []
        self.sections = []

    def analyze(self):
        """完整BGM分析"""
        import librosa
        import numpy as np

        section("BGM分析")
        step("加载音频...")
        y, sr = librosa.load(str(self.audio_path), sr=22050)

        # 1. 节拍检测
        step("检测节拍...")
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        self.tempo = float(tempo) if hasattr(tempo, '__len__') else tempo
        self.beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        ok(f"BPM: {self.tempo:.0f}, 节拍数: {len(self.beats)}")

        # 2. 高潮点检测 (基于能量和频谱变化)
        step("检测高潮点...")
        self.peaks = self._detect_peaks(y, sr)
        ok(f"高潮点: {len(self.peaks)} 个")

        # 3. 段落分析 (intro/verse/chorus/outro)
        step("分析段落结构...")
        self.sections = self._analyze_sections(y, sr)
        ok(f"段落: {len(self.sections)} 个")

        return {
            "tempo": self.tempo,
            "beats": self.beats,
            "peaks": self.peaks,
            "sections": self.sections,
            "duration": float(librosa.get_duration(y=y, sr=sr)),
        }

    def _detect_peaks(self, y, sr):
        """检测能量高潮点"""
        import librosa
        import numpy as np

        # 计算能量包络
        rms = librosa.feature.rms(y=y)[0]
        times = librosa.times_like(rms, sr=sr)

        # 计算频谱对比度 (检测突变)
        spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        contrast_mean = np.mean(spec_contrast, axis=0)

        # 归一化
        rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-8)
        contrast_norm = (contrast_mean - contrast_mean.min()) / (contrast_mean.max() - contrast_mean.min() + 1e-8)

        # 综合分数
        combined = 0.6 * rms_norm + 0.4 * contrast_norm

        # 找峰值 (高于平均值 + 1个标准差)
        threshold = np.mean(combined) + 0.5 * np.std(combined)
        peaks = []
        in_peak = False
        peak_start = 0

        for i, (t, score) in enumerate(zip(times, combined)):
            if score > threshold and not in_peak:
                in_peak = True
                peak_start = t
            elif score < threshold and in_peak:
                in_peak = False
                peak_duration = t - peak_start
                if peak_duration > 0.5:  # 至少0.5秒
                    peaks.append({
                        "start": round(peak_start, 2),
                        "end": round(t, 2),
                        "duration": round(peak_duration, 2),
                        "intensity": round(float(np.max(combined[i-int(peak_duration*50):i])), 2),
                    })

        return peaks

    def _analyze_sections(self, y, sr):
        """分析音乐段落结构"""
        import librosa
        import numpy as np

        # 使用MFCC进行段落边界检测
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        bounds = librosa.segment.agglomerative(mfcc, k=6)

        if len(bounds) == 0:
            return []

        bound_times = librosa.frames_to_time(bounds, sr=sr).tolist()
        duration = float(librosa.get_duration(y=y, sr=sr))

        sections = []
        labels = ["intro", "verse", "chorus", "verse2", "chorus2", "outro"]

        for i, start in enumerate(bound_times):
            end = bound_times[i + 1] if i + 1 < len(bound_times) else duration
            sections.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "label": labels[i] if i < len(labels) else f"section_{i}",
            })

        return sections


class VideoAnalyzer:
    """视频分析器 - 检测情节冲突和关键帧"""

    def __init__(self, video_path):
        self.video_path = video_path
        self.scenes = []
        self.energy_points = []
        self.motion_points = []

    def analyze(self):
        """完整视频分析"""
        section("视频分析")
        step("分析视频内容...")

        # 1. 场景检测
        step("检测场景切换...")
        self.scenes = self._detect_scenes()
        ok(f"场景切换: {len(self.scenes)} 处")

        # 2. 音频能量分析
        step("分析音频能量...")
        self.energy_points = self._analyze_audio_energy()
        ok(f"高能量点: {len(self.energy_points)} 处")

        # 3. 运动检测
        step("检测画面运动...")
        self.motion_points = self._detect_motion()
        ok(f"高运动点: {len(self.motion_points)} 处")

        return {
            "scenes": self.scenes,
            "energy_points": self.energy_points,
            "motion_points": self.motion_points,
        }

    def _detect_scenes(self):
        """检测场景切换"""
        try:
            from scenedetect import detect, ContentDetector
            scenes = detect(str(self.video_path), ContentDetector(threshold=27))

            result = []
            for scene in scenes:
                start = scene[0].get_seconds()
                end = scene[1].get_seconds()
                if end - start > 0.5:
                    result.append({
                        "start": round(start, 2),
                        "end": round(end, 2),
                        "duration": round(end - start, 2),
                    })
            return result
        except Exception as e:
            warn(f"场景检测失败: {e}")
            return []

    def _analyze_audio_energy(self):
        """分析视频音频的能量变化"""
        import librosa
        import numpy as np

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "audio.wav"
            # 提取音频
            run_ffmpeg([
                "-i", str(self.video_path),
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "22050", "-ac", "1",
                str(audio_path),
            ], "提取音频")

            y, sr = librosa.load(str(audio_path), sr=22050)
            rms = librosa.feature.rms(y=y)[0]
            times = librosa.times_like(rms, sr=sr)

            # 找高能量点
            threshold = np.mean(rms) + np.std(rms)
            peaks = []
            for t, e in zip(times, rms):
                if e > threshold:
                    peaks.append({"time": round(float(t), 2), "energy": round(float(e), 4)})

            # 合并相邻点
            return self._merge_points(peaks, min_gap=1.0)

    def _detect_motion(self):
        """检测画面运动强度"""
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(str(self.video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 每秒采样5帧
            sample_interval = max(int(fps / 5), 1)
            prev_gray = None
            motion_points = []

            for frame_idx in range(0, frame_count, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 240))

                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    motion = np.mean(diff)
                    if motion > 15:  # 阈值
                        time = frame_idx / fps
                        motion_points.append({
                            "time": round(time, 2),
                            "motion": round(float(motion), 2),
                        })

                prev_gray = gray

            cap.release()
            return self._merge_points(motion_points, min_gap=1.0)
        except Exception as e:
            warn(f"运动检测失败: {e}")
            return []

    def _merge_points(self, points, min_gap=1.0):
        """合并相邻的时间点"""
        if not points:
            return []

        merged = [points[0]]
        for p in points[1:]:
            if p["time"] - merged[-1]["time"] < min_gap:
                # 合并
                merged[-1]["time"] = (merged[-1]["time"] + p["time"]) / 2
            else:
                merged.append(p)
        return merged


class MashupPlanner:
    """混剪规划器 - 卡点匹配和时间线生成"""

    def __init__(self, bgm_info, video_analyses, style_profile=None):
        self.bgm = bgm_info
        self.videos = video_analyses
        self.style = style_profile or {}

    def plan(self, target_duration=60):
        """生成混剪时间线"""
        section("混剪规划")

        # 1. 选择BGM高潮段落
        step("选择BGM高潮段落...")
        chorus = self._find_chorus()
        ok(f"选取段落: {chorus['start']:.1f}s - {chorus['end']:.1f}s")

        # 2. 提取卡点时间
        step("提取卡点时间...")
        beat_times = self._get_beat_times(chorus, target_duration)
        ok(f"卡点数: {len(beat_times)}")

        # 3. 匹配视频片段
        step("匹配视频片段...")
        segments = self._match_segments(beat_times)
        ok(f"匹配片段: {len(segments)}")

        # 4. 添加特效
        step("规划特效...")
        effects = self._plan_effects(segments)
        ok(f"特效数: {len(effects)}")

        timeline = {
            "bgm_section": chorus,
            "beat_times": beat_times,
            "segments": segments,
            "effects": effects,
            "total_duration": target_duration,
        }

        return timeline

    def _find_chorus(self):
        """找到BGM的高潮段落"""
        sections = self.bgm.get("sections", [])
        peaks = self.bgm.get("peaks", [])

        # 优先找chorus段落
        for s in sections:
            if "chorus" in s.get("label", ""):
                # 检查这个段落是否有高潮点
                section_peaks = [p for p in peaks
                                 if s["start"] <= p["start"] <= s["end"]]
                if section_peaks:
                    return s

        # 如果没有chorus标记，找高潮点最密集的区域
        if peaks:
            best_peak = max(peaks, key=lambda p: p.get("intensity", 0))
            return {
                "start": max(0, best_peak["start"] - 5),
                "end": best_peak["end"] + 5,
                "label": "peak_section",
            }

        # 默认取中间段落
        duration = self.bgm.get("duration", 60)
        return {"start": duration * 0.2, "end": duration * 0.6, "label": "default"}

    def _get_beat_times(self, section, target_duration):
        """获取卡点时间"""
        beats = self.bgm.get("beats", [])
        tempo = self.bgm.get("tempo", 120)

        # 筛选在目标段落内的节拍
        section_beats = [b for b in beats if section["start"] <= b <= section["end"]]

        # 如果节拍不够，用高潮点补充
        if len(section_beats) < 5:
            peaks = self.bgm.get("peaks", [])
            section_peaks = [p["start"] for p in peaks
                             if section["start"] <= p["start"] <= section["end"]]
            section_beats.extend(section_peaks)
            section_beats.sort()

        # 限制数量
        max_beats = int(target_duration * tempo / 60 / 2)  # 每2拍一个卡点
        if len(section_beats) > max_beats:
            # 均匀采样
            step_size = len(section_beats) / max_beats
            section_beats = [section_beats[int(i * step_size)] for i in range(max_beats)]

        return section_beats

    def _match_segments(self, beat_times):
        """匹配视频片段到卡点"""
        segments = []
        all_scenes = []

        # 收集所有视频的场景
        for i, v in enumerate(self.videos):
            for s in v.get("scenes", []):
                s["video_index"] = i
                all_scenes.append(s)

        # 为每个卡点分配视频片段
        for i, beat_time in enumerate(beat_times):
            if i >= len(beat_times) - 1:
                break

            duration = beat_times[i + 1] - beat_time

            # 选择最佳匹配的场景
            best_scene = self._find_best_scene(all_scenes, duration, i)
            if best_scene:
                segments.append({
                    "start_time": beat_time,
                    "duration": duration,
                    "video_index": best_scene["video_index"],
                    "source_start": best_scene["start"],
                    "source_duration": min(duration, best_scene["duration"]),
                })

        return segments

    def _find_best_scene(self, scenes, target_duration, index):
        """找到最匹配目标时长的场景"""
        if not scenes:
            return None

        # 循环使用视频
        video_count = len(self.videos)
        preferred_video = index % video_count

        # 优先选择对应视频的场景
        preferred = [s for s in scenes if s["video_index"] == preferred_video]
        if preferred:
            # 选择时长最接近的
            return min(preferred, key=lambda s: abs(s["duration"] - target_duration))

        return min(scenes, key=lambda s: abs(s["duration"] - target_duration))

    def _plan_effects(self, segments):
        """规划特效"""
        effects = []
        style_effects = self.style.get("effects", ["cut", "zoom", "flash"])

        for i, seg in enumerate(segments):
            effect_type = style_effects[i % len(style_effects)]

            effects.append({
                "segment_index": i,
                "type": effect_type,
                "params": self._get_effect_params(effect_type, seg),
            })

        return effects

    def _get_effect_params(self, effect_type, segment):
        """获取特效参数"""
        if effect_type == "cut":
            return {"transition": "none"}
        elif effect_type == "zoom":
            return {"zoom_ratio": 1.2, "direction": "in"}
        elif effect_type == "flash":
            return {"brightness": 1.5, "duration": 0.1}
        elif effect_type == "shake":
            return {"intensity": 5, "frequency": 10}
        elif effect_type == "fade":
            return {"duration": 0.3}
        else:
            return {}


class MashupRenderer:
    """混剪渲染器 - 生成最终视频"""

    def __init__(self, video_paths, bgm_path, timeline, output_path):
        self.video_paths = video_paths
        self.bgm_path = bgm_path
        self.timeline = timeline
        self.output_path = output_path

    def render(self):
        """渲染混剪视频"""
        section("渲染混剪视频")

        segments = self.timeline.get("segments", [])
        effects = self.timeline.get("effects", [])

        if not segments:
            fail("没有可渲染的片段")
            return False

        # 1. 提取和处理每个片段
        step("处理视频片段...")
        processed_clips = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, seg in enumerate(segments):
                clip_path = Path(tmpdir) / f"clip_{i:03d}.mp4"
                effect = effects[i] if i < len(effects) else {"type": "cut", "params": {}}

                if self._process_clip(seg, effect, clip_path):
                    processed_clips.append(clip_path)

            if not processed_clips:
                fail("所有片段处理失败")
                return False

            # 2. 拼接片段
            step("拼接片段...")
            concat_path = Path(tmpdir) / "concat.mp4"
            if not self._concat_clips(processed_clips, concat_path):
                fail("片段拼接失败")
                return False

            # 3. 添加BGM
            step("混合BGM...")
            if not self._add_bgm(concat_path, self.output_path):
                fail("BGM混合失败")
                return False

        ok(f"渲染完成: {self.output_path}")
        return True

    def _process_clip(self, segment, effect, output_path):
        """处理单个片段（应用特效）"""
        video_idx = segment.get("video_index", 0)
        if video_idx >= len(self.video_paths):
            return False

        video_path = self.video_paths[video_idx]
        source_start = segment.get("source_start", 0)
        source_duration = segment.get("source_duration", 2)

        # 基础剪辑命令
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(source_start),
            "-i", str(video_path),
            "-t", str(source_duration),
        ]

        # 应用特效
        effect_type = effect.get("type", "cut")
        params = effect.get("params", {})
        vf = self._build_effect_filter(effect_type, params)

        if vf:
            cmd.extend(["-vf", vf])

        cmd.extend([
            "-c:v", "libx264", "-crf", "23",
            "-an",  # 去掉原音频
            str(output_path),
        ])

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def _build_effect_filter(self, effect_type, params):
        """构建特效滤镜"""
        if effect_type == "cut":
            return "scale=1280:720"
        elif effect_type == "zoom":
            ratio = params.get("zoom_ratio", 1.2)
            return f"scale=1280*{ratio}:720*{ratio},crop=1280:720"
        elif effect_type == "flash":
            return "eq=brightness=0.3:saturation=1.5,scale=1280:720"
        elif effect_type == "shake":
            intensity = params.get("intensity", 5)
            return f"crop=1280-{intensity}:720-{intensity},{intensity}:{intensity},scale=1280:720"
        elif effect_type == "fade":
            dur = params.get("duration", 0.3)
            return f"fade=t=in:st=0:d={dur},fade=t=out:st={1-dur}:d={dur},scale=1280:720"
        else:
            return "scale=1280:720"

    def _concat_clips(self, clip_paths, output_path):
        """拼接所有片段"""
        list_file = output_path.parent / "concat_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def _add_bgm(self, video_path, output_path):
        """添加BGM"""
        bgm_section = self.timeline.get("bgm_section", {})
        bgm_start = bgm_section.get("start", 0)
        target_duration = self.timeline.get("total_duration", 60)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", str(bgm_start),
            "-i", str(self.bgm_path),
            "-t", str(target_duration),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0


def generate_premiere_project(timeline, video_paths, bgm_path, output_path):
    """生成Premiere Pro工程文件 (XML格式)"""
    section("生成PR工程文件")

    segments = timeline.get("segments", [])
    bgm_section = timeline.get("bgm_section", {})

    # 生成FCP XML格式 (Premiere可导入)
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence>
    <name>Video Studio Mashup</name>
    <duration>{total_frames}</duration>
    <rate>
      <timebase>30</timebase>
    </rate>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <width>1280</width>
            <height>720</height>
          </samplecharacteristics>
        </format>
        <track>
""".format(total_frames=int(timeline.get("total_duration", 60) * 30))

    # 添加视频片段
    frame_offset = 0
    for i, seg in enumerate(segments):
        duration_frames = int(seg.get("duration", 2) * 30)
        video_idx = seg.get("video_index", 0)

        xml_content += """          <clipitem id="clipitem-{i}">
            <name>Segment {i}</name>
            <duration>{dur}</duration>
            <rate><timebase>30</timebase></rate>
            <start>{start}</start>
            <end>{end}</end>
            <file id="file-{i}">
              <name>{filename}</name>
              <pathurl>file:///{filepath}</pathurl>
            </file>
          </clipitem>
""".format(
            i=i,
            dur=duration_frames,
            start=frame_offset,
            end=frame_offset + duration_frames,
            filename=Path(video_paths[video_idx]).name if video_idx < len(video_paths) else "unknown",
            filepath=str(video_paths[video_idx]).replace("\\", "/") if video_idx < len(video_paths) else "",
        )
        frame_offset += duration_frames

    xml_content += """        </track>
      </video>
      <audio>
        <track>
          <clipitem id="clipitem-bgm">
            <name>BGM</name>
            <file id="file-bgm">
              <name>{bgm_name}</name>
              <pathurl>file:///{bgm_path}</pathurl>
            </file>
            <start>{bgm_start}</start>
          </clipitem>
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>""".format(
        bgm_name=Path(bgm_path).name,
        bgm_path=str(bgm_path).replace("\\", "/"),
        bgm_start=int(bgm_section.get("start", 0) * 30),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    ok(f"PR工程文件: {output_path}")
    return output_path


def run_mashup(
    video_paths,
    bgm_path,
    output_path,
    style_profile=None,
    target_duration=60,
    generate_pr=False,
):
    """运行完整的混剪流程"""
    section("开始混剪")

    # 1. 分析BGM
    bgm_analyzer = BGAnalyzer(bgm_path)
    bgm_info = bgm_analyzer.analyze()

    # 2. 分析所有视频
    video_analyses = []
    for vpath in video_paths:
        analyzer = VideoAnalyzer(vpath)
        result = analyzer.analyze()
        video_analyses.append(result)

    # 3. 规划混剪
    planner = MashupPlanner(bgm_info, video_analyses, style_profile)
    timeline = planner.plan(target_duration)

    # 4. 渲染视频
    renderer = MashupRenderer(video_paths, bgm_path, timeline, output_path)
    success = renderer.render()

    # 5. 生成PR工程文件 (可选)
    if generate_pr and success:
        pr_path = Path(output_path).with_suffix(".xml")
        generate_premiere_project(timeline, video_paths, bgm_path, pr_path)

    # 6. 保存混剪报告
    if success:
        report_path = Path(output_path).parent / "mashup_report.json"
        report = {
            "timestamp": datetime.now().isoformat(),
            "bgm_info": bgm_info,
            "video_count": len(video_paths),
            "timeline": timeline,
            "output": str(output_path),
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        ok(f"混剪报告: {report_path}")

    return success


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="混剪引擎 - 智能卡点混剪")
    parser.add_argument("--videos", nargs="+", required=True, help="输入视频列表")
    parser.add_argument("--bgm", required=True, help="BGM音频文件")
    parser.add_argument("--output", default="E:/mashup_output.mp4", help="输出路径")
    parser.add_argument("--duration", type=int, default=60, help="目标时长(秒)")
    parser.add_argument("--style", default=None, help="风格配置JSON文件")
    parser.add_argument("--pr", action="store_true", help="生成PR工程文件")

    args = parser.parse_args()

    style = None
    if args.style and Path(args.style).exists():
        with open(args.style, "r", encoding="utf-8") as f:
            style = json.load(f)

    run_mashup(
        video_paths=args.videos,
        bgm_path=args.bgm,
        output_path=args.output,
        style_profile=style,
        target_duration=args.duration,
        generate_pr=args.pr,
    )
