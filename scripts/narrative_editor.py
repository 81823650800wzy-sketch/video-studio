#!/usr/bin/env python3
"""
叙事剪辑器 — 以字幕为核心的电影解说剪辑
==========================================
核心理念: 字幕是剪辑的灵魂

电影解说剪辑的特点:
1. 字幕驱动节奏 - 每句话决定切口位置
2. 画面服务文案 - 视频内容配合字幕情绪
3. BGM烘托氛围 - 音乐随文案情绪变化
4. 特效强化表达 - 转场和特效配合文案
"""

import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import numpy as np

from pipeline_utils import section, step, ok, warn, fail, ensure_dir, run_ffmpeg


@dataclass
class NarrationSegment:
    """叙事段落 - 字幕驱动的核心单元"""
    index: int               # 序号
    text: str                # 字幕内容
    start: float             # 开始时间（秒）
    end: float               # 结束时间（秒）
    duration: float          # 时长
    emotion: str             # 情感: calm/excited/intense/sad/epic
    intensity: float         # 强度 0-1
    story_phase: str         # 故事阶段: setup/rising/climax/falling/resolution
    video_keyword: str       # 关联的视频关键词
    effect: str              # 特效类型
    transition: str          # 转场类型
    speed: float             # 播放速度


@dataclass
class EditDecision:
    """剪辑决策"""
    narration: NarrationSegment
    video_source: str
    video_start: float
    video_duration: float
    speed: float
    effect: str
    transition: str
    zoom: float              # 缩放比例
    color_grading: Dict      # 调色参数


class NarrativeAnalyzer:
    """叙事分析器 - 从字幕提取故事结构"""

    def analyze_narration(self, srt_path: str) -> List[NarrationSegment]:
        """分析字幕文件，提取叙事结构"""
        section("📖 叙事分析")
        step("解析字幕文件...")

        # 解析SRT
        raw_segments = self._parse_srt(srt_path)
        ok(f"解析到 {len(raw_segments)} 条字幕")

        # 分析每条字幕的情感和故事阶段
        segments = []
        for i, seg in enumerate(raw_segments):
            # 分析情感
            emotion = self._analyze_emotion(seg["text"])

            # 分析故事阶段
            position = i / len(raw_segments)
            story_phase = self._determine_phase(position, emotion)

            # 计算强度
            intensity = self._calculate_intensity(seg["text"], emotion)

            # 选择特效
            effect = self._select_effect(emotion, story_phase)

            # 选择转场
            transition = self._select_transition(story_phase, i, segments)

            # 计算速度
            speed = self._calculate_speed(emotion, story_phase)

            # 提取关键词（用于匹配视频）
            keyword = self._extract_keyword(seg["text"])

            segments.append(NarrationSegment(
                index=i,
                text=seg["text"],
                start=seg["start"],
                end=seg["end"],
                duration=seg["duration"],
                emotion=emotion,
                intensity=intensity,
                story_phase=story_phase,
                video_keyword=keyword,
                effect=effect,
                transition=transition,
                speed=speed,
            ))

        # 输出故事结构
        self._print_story_structure(segments)

        return segments

    def _parse_srt(self, srt_path: str) -> List[Dict]:
        """解析SRT文件"""
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        segments = []
        blocks = content.strip().split("\n\n")

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                time_line = lines[1]
                start_str, end_str = time_line.split(" --> ")
                start = self._srt_to_seconds(start_str.strip())
                end = self._srt_to_seconds(end_str.strip())
                text = "\n".join(lines[2:]).strip()

                segments.append({
                    "text": text,
                    "start": start,
                    "end": end,
                    "duration": end - start,
                })

        return segments

    def _srt_to_seconds(self, time_str: str) -> float:
        """SRT时间转秒"""
        time_str = time_str.replace(",", ".")
        parts = time_str.split(":")
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])

    def _analyze_emotion(self, text: str) -> str:
        """分析字幕情感"""
        text = text.lower()

        # 激昂/史诗
        epic_words = ["震撼", "史诗", "传奇", "伟大", "巅峰", "极致", "辉煌", "不朽", "永恒"]
        if any(w in text for w in epic_words):
            return "epic"

        # 兴奋/激动
        excited_words = ["太", "真的", "简直", "竟然", "没想到", "惊喜", "疯狂", "爆"]
        if any(w in text for w in excited_words):
            return "excited"

        # 紧张/激烈
        intense_words = ["危险", "紧急", "最后", "关键时刻", "生死", "决战", "爆发"]
        if any(w in text for w in intense_words):
            return "intense"

        # 悲伤/感伤
        sad_words = ["遗憾", "可惜", "离开", "告别", "回忆", "曾经", "再也", "回不去"]
        if any(w in text for w in sad_words):
            return "sad"

        # 平静/叙述
        return "calm"

    def _determine_phase(self, position: float, emotion: str) -> str:
        """确定故事阶段"""
        if emotion == "epic" or emotion == "intense":
            return "climax"
        elif position < 0.15:
            return "setup"
        elif position < 0.4:
            return "rising"
        elif position < 0.6:
            return "climax" if emotion == "excited" else "rising"
        elif position < 0.85:
            return "falling"
        else:
            return "resolution"

    def _calculate_intensity(self, text: str, emotion: str) -> float:
        """计算情感强度"""
        base_intensity = {
            "calm": 0.3,
            "excited": 0.7,
            "intense": 0.9,
            "sad": 0.5,
            "epic": 1.0,
        }

        intensity = base_intensity.get(emotion, 0.5)

        # 根据标点调整
        if "！" in text or "!" in text:
            intensity = min(1.0, intensity + 0.2)
        if "..." in text or "…" in text:
            intensity = max(0.1, intensity - 0.1)

        # 根据字数调整（短句更有力）
        if len(text) < 10:
            intensity = min(1.0, intensity + 0.1)

        return round(intensity, 2)

    def _select_effect(self, emotion: str, story_phase: str) -> str:
        """选择特效"""
        effects = {
            "epic": "slow_motion",
            "excited": "speed_ramp",
            "intense": "shake",
            "sad": "fade_slow",
            "calm": "normal",
        }
        return effects.get(emotion, "normal")

    def _select_transition(self, story_phase: str, index: int, prev_segments: List) -> str:
        """选择转场"""
        if index == 0:
            return "fade_in"

        transitions = {
            "setup": "dissolve",
            "rising": "cut",
            "climax": "flash",
            "falling": "dissolve",
            "resolution": "fade_out",
        }

        return transitions.get(story_phase, "cut")

    def _calculate_speed(self, emotion: str, story_phase: str) -> float:
        """计算播放速度"""
        if emotion == "epic" and story_phase == "climax":
            return 0.6  # 高潮慢动作
        elif emotion == "intense":
            return 0.8  # 紧张场面稍慢
        elif emotion == "excited":
            return 1.2  # 兴奋加速
        else:
            return 1.0

    def _extract_keyword(self, text: str) -> str:
        """提取关键词（用于匹配视频）"""
        # 简单的关键词提取
        keywords = []
        word_list = [
            "城市", "夜景", "人群", "自然", "风景", "天空", "海洋",
            "建筑", "街道", "日出", "日落", "星空", "森林", "山",
            "运动", "奔跑", "战斗", "音乐", "舞蹈", "笑容",
        ]

        for word in word_list:
            if word in text:
                keywords.append(word)

        return keywords[0] if keywords else "default"

    def _print_story_structure(self, segments: List[NarrationSegment]):
        """打印故事结构"""
        step("\n故事结构:")
        phases = {}
        for seg in segments:
            phase = seg.story_phase
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(seg)

        for phase, segs in phases.items():
            avg_intensity = np.mean([s.intensity for s in segs])
            print(f"  {phase}: {len(segs)}段, 平均强度={avg_intensity:.2f}")


class VideoMatcher:
    """视频匹配器 - 根据字幕选择最佳画面"""

    def __init__(self):
        pass

    def match_videos(
        self,
        narration_segments: List[NarrationSegment],
        video_path: str,
    ) -> List[EditDecision]:
        """为每段字幕匹配视频画面"""
        section("🎬 画面匹配")
        step("分析视频场景...")

        # 分析视频场景
        scenes = self._analyze_scenes(video_path)
        ok(f"检测到 {len(scenes)} 个场景")

        # 为每段字幕匹配最佳场景
        decisions = []
        used_scenes = set()

        for i, narr in enumerate(narration_segments):
            # 根据情感和位置选择场景
            scene = self._select_best_scene(
                scenes, narr, used_scenes, i, len(narration_segments)
            )

            if scene:
                used_scenes.add(scene["index"])

                decisions.append(EditDecision(
                    narration=narr,
                    video_source=video_path,
                    video_start=scene["start"],
                    video_duration=narr.duration,
                    speed=narr.speed,
                    effect=narr.effect,
                    transition=narr.transition,
                    zoom=self._calculate_zoom(narr.emotion, narr.intensity),
                    color_grading=self._select_color_grading(narr.emotion),
                ))

        ok(f"匹配完成: {len(decisions)} 个剪辑决策")
        return decisions

    def _analyze_scenes(self, video_path: str) -> List[Dict]:
        """分析视频场景"""
        try:
            from scenedetect import detect, ContentDetector
            scenes = detect(str(video_path), ContentDetector(threshold=27))

            result = []
            for i, scene in enumerate(scenes):
                start = scene[0].get_seconds()
                end = scene[1].get_seconds()
                if end - start > 0.5:
                    result.append({
                        "index": i,
                        "start": start,
                        "end": end,
                        "duration": end - start,
                    })
            return result
        except Exception as e:
            warn(f"场景检测失败: {e}")
            return []

    def _select_best_scene(
        self,
        scenes: List[Dict],
        narration: NarrationSegment,
        used_scenes: set,
        position: int,
        total: int,
    ) -> Optional[Dict]:
        """选择最佳场景"""
        available = [s for s in scenes if s["index"] not in used_scenes]
        if not available:
            available = scenes  # 重用已用场景

        if not available:
            return None

        # 根据故事阶段选择位置
        phase = narration.story_phase
        if phase == "setup":
            # 开场选择前面的场景
            preferred = [s for s in available if s["start"] < 60]
        elif phase == "climax":
            # 高潮选择中间偏后的场景
            preferred = [s for s in available if 60 < s["start"] < 300]
        elif phase == "resolution":
            # 结尾选择后面的场景
            preferred = [s for s in available if s["start"] > 300]
        else:
            preferred = available

        if not preferred:
            preferred = available

        # 选择时长最匹配的
        target_duration = narration.duration
        best = min(preferred, key=lambda s: abs(s["duration"] - target_duration))

        return best

    def _calculate_zoom(self, emotion: str, intensity: float) -> float:
        """计算缩放比例"""
        base_zoom = 1.0
        if emotion == "epic":
            return 1.2 + intensity * 0.3
        elif emotion == "intense":
            return 1.1 + intensity * 0.2
        else:
            return base_zoom

    def _select_color_grading(self, emotion: str) -> Dict:
        """选择调色参数"""
        gradings = {
            "epic": {"contrast": 1.3, "saturation": 0.9, "temperature": "cinematic"},
            "excited": {"contrast": 1.2, "saturation": 1.3, "temperature": "vivid"},
            "intense": {"contrast": 1.4, "saturation": 0.8, "temperature": "cool"},
            "sad": {"contrast": 0.9, "saturation": 0.7, "temperature": "cool"},
            "calm": {"contrast": 1.0, "saturation": 1.0, "temperature": "neutral"},
        }
        return gradings.get(emotion, {"contrast": 1.0, "saturation": 1.0, "temperature": "neutral"})


class NarrativeRenderer:
    """叙事渲染器 - 生成最终视频"""

    def render(
        self,
        decisions: List[EditDecision],
        output_path: str,
        bgm_path: str = None,
    ) -> str:
        """渲染最终视频"""
        section("🎬 渲染视频")
        step(f"剪辑决策: {len(decisions)} 个")

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 渲染每个片段
            step("渲染片段...")
            clips = []
            for i, decision in enumerate(decisions):
                clip_path = Path(tmpdir) / f"clip_{i:03d}.mp4"
                if self._render_clip(decision, str(clip_path)):
                    clips.append(str(clip_path))

            # 2. 拼接
            step("拼接视频...")
            concat_path = Path(tmpdir) / "concat.mp4"
            self._concat_clips(clips, str(concat_path))

            # 3. 添加BGM
            if bgm_path:
                step("混合BGM...")
                self._add_bgm(str(concat_path), bgm_path, output_path, decisions)
            else:
                import shutil
                shutil.copy2(str(concat_path), output_path)

        ok(f"渲染完成: {output_path}")
        return output_path

    def _render_clip(self, decision: EditDecision, output_path: str) -> bool:
        """渲染单个片段"""
        narr = decision.narration

        # 构建滤镜链
        vf_parts = []

        # 1. 缩放
        if decision.zoom != 1.0:
            w = int(1280 * decision.zoom)
            h = int(720 * decision.zoom)
            vf_parts.append(f"scale={w}:{h}")
            vf_parts.append(f"crop=1280:720")
        else:
            vf_parts.append("scale=1280:720")

        # 2. 速度
        if decision.speed != 1.0:
            vf_parts.append(f"setpts={1/decision.speed}*PTS")

        # 3. 特效
        if decision.effect == "slow_motion":
            vf_parts.append("eq=brightness=0.05:saturation=1.2")
        elif decision.effect == "speed_ramp":
            vf_parts.append("eq=saturation=1.3")
        elif decision.effect == "shake":
            vf_parts.append("crop=iw-20:ih-20:10*sin(t*20):10*cos(t*20)")
        elif decision.effect == "fade_slow":
            vf_parts.append("eq=brightness=-0.05:saturation=0.8")

        # 4. 转场效果
        if decision.transition == "fade_in":
            vf_parts.append("fade=t=in:st=0:d=0.5")
        elif decision.transition == "fade_out":
            vf_parts.append(f"fade=t=out:st={narr.duration-0.5}:d=0.5")
        elif decision.transition == "flash":
            vf_parts.append("eq=brightness=0.3:saturation=2.0")

        # 5. 调色
        grading = decision.color_grading
        contrast = grading.get("contrast", 1.0)
        saturation = grading.get("saturation", 1.0)
        vf_parts.append(f"eq=contrast={contrast}:saturation={saturation}")

        if grading.get("temperature") == "cinematic":
            vf_parts.append("colorbalance=rs=0.05:gs=0:bs=-0.05")
        elif grading.get("temperature") == "cool":
            vf_parts.append("colorbalance=rs=-0.1:gs=0:bs=0.1")
        elif grading.get("temperature") == "vivid":
            vf_parts.append("eq=saturation=1.2")

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(decision.video_start),
            "-i", decision.video_source,
            "-t", str(decision.video_duration),
            "-vf", vf,
            "-c:v", "libx264", "-crf", "23",
            "-an",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def _concat_clips(self, clips: List[str], output_path: str):
        """拼接片段"""
        list_file = Path(output_path).parent / "list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True)

    def _add_bgm(self, video_path: str, bgm_path: str, output_path: str,
                  decisions: List[EditDecision]):
        """添加BGM，音量随情绪变化"""
        # 计算BGM起始时间
        bgm_start = 0

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(bgm_start),
            "-i", bgm_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True)


class JianyingExporter:
    """剪映导出器 - 带完整轨道"""

    def export(
        self,
        video_path: str,
        decisions: List[EditDecision],
        bgm_path: str,
        draft_name: str,
    ) -> str:
        """导出到剪映草稿"""
        from jianying_export_pro import export_to_jianying_pro

        # 构建切点配置
        clips = []
        for decision in decisions:
            clips.append({
                "start": decision.video_start,
                "duration": decision.video_duration,
                "speed": decision.speed,
            })

        return export_to_jianying_pro(
            video_path=video_path,
            bgm_path=bgm_path,
            draft_name=draft_name,
            clips=clips,
        )


class NarrativeEditor:
    """叙事剪辑器 - 以字幕为核心的电影解说剪辑"""

    def __init__(self):
        self.analyzer = NarrativeAnalyzer()
        self.matcher = VideoMatcher()
        self.renderer = NarrativeRenderer()
        self.exporter = JianyingExporter()

    def edit(
        self,
        srt_path: str,
        video_path: str,
        bgm_path: str = None,
        output_dir: str = "E:/",
        draft_name: str = None,
    ) -> Dict:
        """
        以字幕为核心的剪辑

        Args:
            srt_path: SRT字幕文件（核心驱动）
            video_path: 视频素材
            bgm_path: BGM音频
            output_dir: 输出目录
            draft_name: 剪映草稿名称
        """
        section("🎬 叙事剪辑器")
        step(f"字幕: {Path(srt_path).name}")
        step(f"视频: {Path(video_path).name}")
        if bgm_path:
            step(f"BGM: {Path(bgm_path).name}")

        results = {"outputs": {}}

        # 1. 分析字幕（核心）
        narration_segments = self.analyzer.analyze_narration(srt_path)
        results["narration_count"] = len(narration_segments)

        # 2. 匹配视频画面
        decisions = self.matcher.match_videos(narration_segments, video_path)
        results["decisions_count"] = len(decisions)

        # 3. 渲染视频
        output_path = str(Path(output_dir) / "叙事剪辑_成品.mp4")
        self.renderer.render(decisions, output_path, bgm_path)
        results["outputs"]["video"] = output_path

        # 4. 生成新字幕（与剪辑同步）
        new_srt_path = str(Path(output_dir) / "叙事剪辑_字幕.srt")
        self._generate_synced_srt(decisions, new_srt_path)
        results["outputs"]["srt"] = new_srt_path

        # 5. 导出剪映草稿
        if not draft_name:
            draft_name = f"叙事剪辑_{datetime.now().strftime('%H%M%S')}"

        draft_path = self.exporter.export(
            video_path=output_path,
            decisions=decisions,
            bgm_path=bgm_path,
            draft_name=draft_name,
        )
        results["outputs"]["jianying"] = draft_path

        # 6. 保存剪辑决策报告
        report_path = str(Path(output_dir) / "剪辑决策.json")
        self._save_report(decisions, report_path)
        results["outputs"]["report"] = report_path

        # 完成
        section("✨ 叙事剪辑完成!")
        for key, path in results["outputs"].items():
            ok(f"{key}: {path}")

        return results

    def _generate_synced_srt(self, decisions: List[EditDecision], output_path: str):
        """生成与剪辑同步的字幕"""
        srt_lines = []
        current_time = 0

        for i, decision in enumerate(decisions, 1):
            narr = decision.narration
            duration = decision.video_duration

            start_str = self._seconds_to_srt(current_time)
            end_str = self._seconds_to_srt(current_time + duration)

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(narr.text)
            srt_lines.append("")

            current_time += duration

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

    def _seconds_to_srt(self, seconds: float) -> str:
        """秒转SRT时间格式"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _save_report(self, decisions: List[EditDecision], output_path: str):
        """保存剪辑决策报告"""
        report = []
        for d in decisions:
            report.append({
                "text": d.narration.text,
                "emotion": d.narration.emotion,
                "phase": d.narration.story_phase,
                "intensity": d.narration.intensity,
                "video_start": d.video_start,
                "duration": d.video_duration,
                "speed": d.speed,
                "effect": d.effect,
                "transition": d.transition,
                "zoom": d.zoom,
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


# ============================================================
#  CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="叙事剪辑器 - 以字幕为核心的电影解说剪辑")
    parser.add_argument("srt", help="SRT字幕文件（核心驱动）")
    parser.add_argument("video", help="视频素材")
    parser.add_argument("--bgm", help="BGM音频")
    parser.add_argument("--output", default="E:/", help="输出目录")
    parser.add_argument("--name", help="剪映草稿名称")

    args = parser.parse_args()

    editor = NarrativeEditor()
    editor.edit(
        srt_path=args.srt,
        video_path=args.video,
        bgm_path=args.bgm,
        output_dir=args.output,
        draft_name=args.name,
    )
