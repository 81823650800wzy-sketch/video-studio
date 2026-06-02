#!/usr/bin/env python3
"""
AI 剪辑师 — 全自动视频剪辑系统
================================
用户输入需求 → AI分析 → 自动剪辑 → 输出到剪映

工作流:
1. 素材提取: 从网络/本地获取视频素材
2. 内容分析: AI分析视频情节、情感、节奏
3. 风格学习: 分析参考视频的剪辑风格
4. 文案生成: 根据主题生成旁白文案
5. 智能剪辑: 自动截取片段、卡点、转场
6. 音频处理: TTS旁白 + BGM混合
7. 字幕生成: Whisper语音识别
8. 特效调色: 根据风格自动调色
9. 输出成品: 导出视频 + 剪映草稿
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from pipeline_utils import section, step, ok, warn, fail, ensure_dir, run_ffmpeg


@dataclass
class VideoSegment:
    """视频片段"""
    source_path: str
    start: float
    end: float
    score: float = 0.0
    emotion: str = "neutral"
    scene_type: str = "unknown"
    text: str = ""


@dataclass
class EditPlan:
    """剪辑计划"""
    title: str
    theme: str
    style: str
    target_duration: float
    segments: List[VideoSegment] = field(default_factory=list)
    narration: List[Dict] = field(default_factory=list)
    bgm_path: str = ""
    effects: List[Dict] = field(default_factory=list)
    transitions: List[str] = field(default_factory=list)
    color_grading: Dict = field(default_factory=dict)


class ContentAnalyzer:
    """内容分析器 - AI驱动"""

    def __init__(self):
        self.scene_types = [
            "opening", "action", "dialogue", "emotional",
            "transition", "climax", "ending", "b-roll"
        ]

    def analyze_video(self, video_path: str) -> Dict:
        """深度分析视频内容"""
        section("AI内容分析")
        step(f"分析视频: {Path(video_path).name}")

        info = self._get_video_info(video_path)
        scenes = self._detect_scenes(video_path)
        audio_features = self._analyze_audio(video_path)
        key_frames = self._extract_key_frames(video_path)
        emotions = self._analyze_emotions(video_path, scenes)

        analysis = {
            "duration": info["duration"],
            "resolution": f"{info['width']}x{info['height']}",
            "scenes": scenes,
            "audio": audio_features,
            "key_frames": key_frames,
            "emotions": emotions,
            "pacing": self._calculate_pacing(scenes),
            "energy_curve": audio_features.get("energy_curve", []),
        }

        ok(f"分析完成: {len(scenes)}个场景, {len(key_frames)}个关键帧")
        return analysis

    def _get_video_info(self, video_path):
        """获取视频基础信息"""
        import subprocess
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,duration",
            "-show_entries", "format=duration",
            "-of", "json", str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(result.stdout)
        return {
            "width": int(info["streams"][0].get("width", 1280)),
            "height": int(info["streams"][0].get("height", 720)),
            "duration": float(info["format"].get("duration", 0)),
        }

    def _detect_scenes(self, video_path: str) -> List[Dict]:
        """检测场景切换"""
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
                        "start": round(start, 2),
                        "end": round(end, 2),
                        "duration": round(end - start, 2),
                        "type": self._classify_scene(start, end),
                    })
            return result
        except Exception as e:
            warn(f"场景检测失败: {e}")
            return []

    def _classify_scene(self, start: float, end: float) -> str:
        """根据时长分类场景类型"""
        duration = end - start
        if duration < 2:
            return "cut"
        elif duration < 5:
            return "action"
        elif duration < 15:
            return "dialogue"
        else:
            return "long_take"

    def _analyze_audio(self, video_path: str) -> Dict:
        """分析音频特征"""
        try:
            import librosa
            import numpy as np

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = Path(tmpdir) / "audio.wav"
                run_ffmpeg([
                    "-i", str(video_path),
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "22050", "-ac", "1",
                    str(audio_path),
                ], "提取音频")

                y, sr = librosa.load(str(audio_path), sr=22050)

                # 能量分析
                rms = librosa.feature.rms(y=y)[0]
                times = librosa.times_like(rms, sr=sr)

                # 节拍检测
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

                # 频谱特征
                spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

                # 生成能量曲线 (每秒一个值)
                energy_curve = []
                for t in range(int(times[-1]) + 1):
                    mask = (times >= t) & (times < t + 1)
                    if np.any(mask):
                        energy_curve.append(round(float(np.mean(rms[mask])), 4))

                return {
                    "tempo": float(tempo) if not hasattr(tempo, '__len__') else float(tempo[0]),
                    "energy_curve": energy_curve,
                    "avg_energy": round(float(np.mean(rms)), 4),
                    "max_energy": round(float(np.max(rms)), 4),
                    "spectral_centroid_mean": round(float(np.mean(spectral_centroids)), 2),
                }
        except Exception as e:
            warn(f"音频分析失败: {e}")
            return {"tempo": 120, "energy_curve": [], "avg_energy": 0}

    def _extract_key_frames(self, video_path: str) -> List[Dict]:
        """提取关键帧"""
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 每秒采样2帧
            sample_interval = max(int(fps / 2), 1)
            key_frames = []
            prev_hist = None

            for frame_idx in range(0, total_frames, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                # 计算直方图
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()

                # 与前一帧比较，检测变化
                if prev_hist is not None:
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                    if diff > 0.3:  # 显著变化
                        time = frame_idx / fps
                        key_frames.append({
                            "time": round(time, 2),
                            "frame": frame_idx,
                            "change_score": round(diff, 3),
                        })

                prev_hist = hist

            cap.release()
            return key_frames
        except Exception as e:
            warn(f"关键帧提取失败: {e}")
            return []

    def _analyze_emotions(self, video_path: str, scenes: List[Dict]) -> List[Dict]:
        """分析场景情感（基于音频能量和视觉变化）"""
        emotions = []
        for scene in scenes:
            # 基于场景时长和位置推断情感
            duration = scene["duration"]
            position = scene["start"]

            if duration < 2:
                emotion = "intense"
            elif duration < 5:
                emotion = "active"
            elif duration < 10:
                emotion = "calm"
            else:
                emotion = "slow"

            emotions.append({
                "scene_index": scene["index"],
                "emotion": emotion,
                "intensity": min(1.0, 2.0 / duration),
            })

        return emotions

    def _calculate_pacing(self, scenes: List[Dict]) -> Dict:
        """计算剪辑节奏"""
        if not scenes:
            return {"avg_duration": 0, "cuts_per_minute": 0}

        durations = [s["duration"] for s in scenes]
        total_duration = sum(durations)

        return {
            "avg_duration": round(sum(durations) / len(durations), 2),
            "min_duration": round(min(durations), 2),
            "max_duration": round(max(durations), 2),
            "cuts_per_minute": round(len(scenes) / (total_duration / 60), 1) if total_duration > 0 else 0,
        }


class StyleLearner:
    """风格学习器 - 学习参考视频的剪辑风格"""

    def __init__(self):
        self.style_presets = {
            "电影混剪": {
                "avg_shot_duration": 3.0,
                "cuts_per_minute": 20,
                "transitions": ["cut", "fade", "dissolve"],
                "color_grading": {"contrast": 1.2, "saturation": 0.9, "temperature": "warm"},
                "effects": ["slow_motion", "speed_ramp", "letterbox"],
            },
            "vlog": {
                "avg_shot_duration": 5.0,
                "cuts_per_minute": 12,
                "transitions": ["cut", "slide", "zoom"],
                "color_grading": {"contrast": 1.1, "saturation": 1.2, "temperature": "bright"},
                "effects": ["text_overlay", "sticker", "speed_ramp"],
            },
            "鬼畜": {
                "avg_shot_duration": 0.8,
                "cuts_per_minute": 75,
                "transitions": ["cut", "flash", "shake"],
                "color_grading": {"contrast": 1.3, "saturation": 1.4, "temperature": "vivid"},
                "effects": ["loop", "mirror", "zoom_repeat"],
            },
            "纪录片": {
                "avg_shot_duration": 6.0,
                "cuts_per_minute": 10,
                "transitions": ["cut", "dissolve", "wipe"],
                "color_grading": {"contrast": 1.0, "saturation": 0.85, "temperature": "neutral"},
                "effects": ["ken_burns", "text_overlay", "letterbox"],
            },
            "教程": {
                "avg_shot_duration": 8.0,
                "cuts_per_minute": 8,
                "transitions": ["cut", "fade"],
                "color_grading": {"contrast": 1.1, "saturation": 1.0, "temperature": "neutral"},
                "effects": ["text_overlay", "zoom_in", "highlight"],
            },
        }

    def learn_from_reference(self, reference_path: str) -> Dict:
        """从参考视频学习风格"""
        section("风格学习")
        step(f"分析参考视频: {Path(reference_path).name}")

        analyzer = ContentAnalyzer()
        analysis = analyzer.analyze_video(reference_path)

        pacing = analysis["pacing"]
        audio = analysis["audio"]

        # 推断风格
        style = self._infer_style(pacing, audio)

        ok(f"学习到风格: {style['name']}")
        return style

    def _infer_style(self, pacing: Dict, audio: Dict) -> Dict:
        """根据节奏和音频推断风格"""
        cuts_per_minute = pacing.get("cuts_per_minute", 10)
        avg_duration = pacing.get("avg_duration", 5)
        tempo = audio.get("tempo", 120)

        if cuts_per_minute > 50:
            style_name = "鬼畜"
        elif cuts_per_minute > 20:
            style_name = "电影混剪"
        elif cuts_per_minute > 10:
            style_name = "vlog"
        elif avg_duration > 6:
            style_name = "纪录片"
        else:
            style_name = "教程"

        base_style = self.style_presets.get(style_name, self.style_presets["vlog"])

        return {
            "name": style_name,
            "pacing": pacing,
            "tempo": tempo,
            **base_style,
        }

    def get_preset(self, preset_name: str) -> Dict:
        """获取预设风格"""
        return self.style_presets.get(preset_name, self.style_presets["vlog"])


class ScriptGenerator:
    """文案生成器 - 根据主题生成剪辑文案"""

    def __init__(self):
        self.templates = {
            "电影混剪": {
                "intro": "在这个光影交织的世界里，每一个镜头都诉说着独特的故事。",
                "body": [
                    "画面与音乐的完美融合，创造出令人心动的瞬间。",
                    "每一个转场，每一次定格，都是情感的升华。",
                    "让我们一起感受这份来自银幕的震撼。",
                ],
                "outro": "这就是电影的魅力，永远让人回味无穷。",
            },
            "vlog": {
                "intro": "生活中的美好，值得被记录。",
                "body": [
                    "每一天都是独一无二的旅程。",
                    "简单的瞬间，往往是最珍贵的回忆。",
                    "让我们一起分享这份快乐。",
                ],
                "outro": "感谢观看，我们下期再见！",
            },
            "教程": {
                "intro": "大家好，今天我来教大家一个实用的技巧。",
                "body": [
                    "首先，让我们了解一下基本概念。",
                    "接下来是具体的操作步骤。",
                    "最后，我们来总结一下重点内容。",
                ],
                "outro": "学会了就赶紧试试吧！记得点赞收藏。",
            },
        }

    def generate_script(self, theme: str, style: str, duration: float) -> List[Dict]:
        """生成剪辑文案"""
        section("文案生成")
        step(f"主题: {theme}, 风格: {style}")

        template = self.templates.get(style, self.templates["vlog"])

        # 根据时长调整文案段落数
        if duration <= 15:
            segments = 3
        elif duration <= 30:
            segments = 5
        elif duration <= 60:
            segments = 8
        else:
            segments = 12

        script = []

        # 开场
        script.append({
            "index": 0,
            "type": "intro",
            "text": template["intro"],
            "duration": min(3.0, duration * 0.1),
        })

        # 主体
        body_duration = duration * 0.7
        segment_duration = body_duration / (segments - 2)

        for i in range(segments - 2):
            body_text = template["body"][i % len(template["body"])]
            # 根据主题定制
            if theme and i == 0:
                body_text = f"关于{theme}，{body_text}"

            script.append({
                "index": i + 1,
                "type": "body",
                "text": body_text,
                "duration": segment_duration,
            })

        # 结尾
        script.append({
            "index": segments - 1,
            "type": "outro",
            "text": template["outro"],
            "duration": min(4.0, duration * 0.15),
        })

        ok(f"生成文案: {len(script)}段")
        return script


class VideoCutter:
    """智能剪辑器 - 自动截取和拼接片段"""

    def __init__(self):
        pass

    def cut_segments(self, video_path: str, analysis: Dict,
                     target_duration: float, style: Dict) -> List[VideoSegment]:
        """根据分析结果智能截取片段"""
        section("智能截取")
        step("分析最佳片段...")

        scenes = analysis.get("scenes", [])
        audio = analysis.get("audio", {})
        energy_curve = audio.get("energy_curve", [])

        # 为每个场景评分
        scored_scenes = []
        for scene in scenes:
            score = self._score_scene(scene, energy_curve, style)
            scored_scenes.append((scene, score))

        # 按分数排序
        scored_scenes.sort(key=lambda x: x[1], reverse=True)

        # 选择片段直到达到目标时长
        segments = []
        total_duration = 0
        avg_shot = style.get("avg_shot_duration", 3.0)

        for scene, score in scored_scenes:
            if total_duration >= target_duration:
                break

            # 计算这个片段的时长
            scene_duration = scene["duration"]
            clip_duration = min(avg_shot, scene_duration)

            if clip_duration < 0.5:
                continue

            segment = VideoSegment(
                source_path=video_path,
                start=scene["start"],
                end=scene["start"] + clip_duration,
                score=score,
                scene_type=scene.get("type", "unknown"),
            )
            segments.append(segment)
            total_duration += clip_duration

        # 按时间排序（保持原始顺序）
        segments.sort(key=lambda s: s.start)

        ok(f"选取 {len(segments)} 个片段, 总时长 {total_duration:.1f}s")
        return segments

    def _score_scene(self, scene: Dict, energy_curve: List[float], style: Dict) -> float:
        """为场景评分"""
        score = 0.5  # 基础分

        duration = scene["duration"]
        avg_shot = style.get("avg_shot_duration", 3.0)

        # 时长匹配度
        duration_ratio = min(duration, avg_shot) / avg_shot
        score += duration_ratio * 0.3

        # 能量匹配
        scene_start = int(scene["start"])
        if scene_start < len(energy_curve):
            energy = energy_curve[scene_start]
            score += energy * 0.3

        # 位置权重（开头和结尾更重要）
        position = scene["start"]
        if position < 5 or position > scene.get("end", 0) - 5:
            score += 0.2

        return round(score, 3)


class AudioMixer:
    """音频混合器 - TTS + BGM"""

    def __init__(self):
        pass

    def create_audio_track(self, script: List[Dict], bgm_path: str,
                           output_path: str, voice: str = "zh-CN-YunxiNeural") -> str:
        """创建完整音频轨道"""
        section("音频处理")

        # 1. 生成TTS旁白
        step("生成TTS旁白...")
        narration_path = self._generate_narration(script, output_path, voice)

        # 2. 混合BGM
        step("混合BGM...")
        final_path = self._mix_bgm(narration_path, bgm_path, output_path)

        ok(f"音频轨道: {final_path}")
        return final_path

    def _generate_narration(self, script: List[Dict], output_path: str, voice: str) -> str:
        """生成TTS旁白"""
        import asyncio
        import edge_tts

        # 合并所有文案
        full_text = "\n".join([seg["text"] for seg in script])

        narration_path = Path(output_path).parent / "narration.mp3"

        async def gen():
            communicate = edge_tts.Communicate(full_text, voice, rate="+10%")
            await communicate.save(str(narration_path))

        asyncio.run(gen())
        step(f"  旁白生成完成: {narration_path}")
        return str(narration_path)

    def _mix_bgm(self, narration_path: str, bgm_path: str, output_path: str) -> str:
        """混合旁白和BGM"""
        if not bgm_path or not Path(bgm_path).exists():
            return narration_path

        mixed_path = Path(output_path).parent / "mixed_audio.mp3"

        cmd = [
            "ffmpeg", "-y",
            "-i", narration_path,
            "-i", bgm_path,
            "-filter_complex",
            "[0:a]volume=1.0[narration];"
            "[1:a]volume=0.3[bgm];"
            "[narration][bgm]amix=inputs=2:duration=shortest[out]",
            "-map", "[out]",
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(mixed_path),
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            return str(mixed_path)
        return narration_path


class EffectEngine:
    """特效引擎 - 转场和视觉效果"""

    def __init__(self):
        self.transitions = {
            "cut": "",
            "fade": "fade=t=in:st=0:d=0.5,fade=t=out:st=0.5:d=0.5",
            "dissolve": "fade=t=in:st=0:d=0.8:alpha=1",
            "zoom_in": "zoompan=z='min(zoom+0.0015,1.5)':d=125:s=1280x720",
            "zoom_out": "zoompan=z='if(eq(on,1),1.5,max(1.001,zoom-0.0015))':d=125:s=1280x720",
            "slide_left": "crop=iw-100:ih:100*t/1:0",
            "shake": "crop=iw-10:ih-10:5*sin(t*10):5*cos(t*10)",
        }

        self.color_presets = {
            "warm": "eq=contrast=1.1:saturation=1.1:gamma=1.1,colorbalance=rs=0.1:gs=-0.05:bs=-0.1",
            "cool": "eq=contrast=1.1:saturation=0.9,colorbalance=rs=-0.1:gs=0:bs=0.1",
            "vivid": "eq=contrast=1.3:saturation=1.4",
            "cinematic": "eq=contrast=1.2:saturation=0.85:gamma=0.95,colorbalance=rs=0.05:gs=0:bs=-0.05",
            "vintage": "eq=contrast=0.9:saturation=0.7:gamma=1.1,colorbalance=rs=0.15:gs=0.05:bs=-0.1",
        }

    def apply_effect(self, input_path: str, output_path: str,
                     effect_type: str, params: Dict = None) -> bool:
        """应用特效"""
        vf = self._build_filter(effect_type, params)

        if not vf:
            return False

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "23",
            "-an",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    def _build_filter(self, effect_type: str, params: Dict = None) -> str:
        """构建滤镜"""
        params = params or {}

        if effect_type in self.transitions:
            return self.transitions[effect_type]
        elif effect_type in self.color_presets:
            return self.color_presets[effect_type]
        else:
            return ""

    def apply_color_grading(self, input_path: str, output_path: str, grading: Dict) -> bool:
        """应用调色"""
        temperature = grading.get("temperature", "neutral")
        contrast = grading.get("contrast", 1.0)
        saturation = grading.get("saturation", 1.0)

        # 构建调色滤镜
        vf_parts = [f"eq=contrast={contrast}:saturation={saturation}"]

        if temperature == "warm":
            vf_parts.append("colorbalance=rs=0.1:gs=-0.05:bs=-0.1")
        elif temperature == "cool":
            vf_parts.append("colorbalance=rs=-0.1:gs=0:bs=0.1")

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "23",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0


class AutoEditor:
    """自动剪辑师 - 整合所有模块"""

    def __init__(self):
        self.analyzer = ContentAnalyzer()
        self.style_learner = StyleLearner()
        self.script_gen = ScriptGenerator()
        self.cutter = VideoCutter()
        self.audio_mixer = AudioMixer()
        self.effect_engine = EffectEngine()

    def auto_edit(
        self,
        task: str,
        video_paths: List[str] = None,
        reference_url: str = None,
        bgm_path: str = None,
        style_preset: str = None,
        target_duration: float = 30,
        output_dir: str = "E:/",
        export_jianying: bool = True,
    ) -> Dict:
        """
        全自动剪辑

        Args:
            task: 剪辑任务描述（如"电影混剪"、"vlog剪辑"）
            video_paths: 本地视频路径列表
            reference_url: 参考视频URL（用于风格学习）
            bgm_path: BGM音频路径
            style_preset: 风格预设名称
            target_duration: 目标时长（秒）
            output_dir: 输出目录
            export_jianying: 是否导出到剪映
        """
        section("🎬 AI自动剪辑师")
        step(f"任务: {task}")
        step(f"目标时长: {target_duration}秒")

        results = {
            "task": task,
            "timestamp": datetime.now().isoformat(),
            "outputs": {},
        }

        # 1. 解析任务
        theme, style_hint = self._parse_task(task)

        # 2. 获取素材
        if not video_paths:
            video_paths = self._download_materials(task, output_dir)

        if not video_paths:
            fail("没有可用的视频素材")
            return results

        # 3. 分析风格
        style = {}
        if reference_url:
            style = self.style_learner.learn_from_reference(reference_url)
        elif style_preset:
            style = self.style_learner.get_preset(style_preset)
        else:
            style = self.style_learner.get_preset(style_hint or "vlog")

        # 4. 生成文案
        script = self.script_gen.generate_script(theme, style.get("name", "vlog"), target_duration)
        results["script"] = script

        # 5. 分析视频并截取片段
        all_segments = []
        for vpath in video_paths:
            analysis = self.analyzer.analyze_video(vpath)
            segments = self.cutter.cut_segments(vpath, analysis, target_duration / len(video_paths), style)
            all_segments.extend(segments)

        # 6. 渲染片段
        step("渲染视频片段...")
        rendered_clips = self._render_segments(all_segments, style, output_dir)

        # 7. 拼接视频
        step("拼接视频...")
        concat_path = Path(output_dir) / "concat_raw.mp4"
        self._concat_clips(rendered_clips, str(concat_path))

        # 8. 生成音频
        if bgm_path:
            audio_path = self.audio_mixer.create_audio_track(
                script, bgm_path,
                str(Path(output_dir) / "audio.mp3")
            )
        else:
            audio_path = self.audio_mixer.create_audio_track(
                script, "",
                str(Path(output_dir) / "audio.mp3")
            )
        results["outputs"]["audio"] = audio_path

        # 9. 合并音视频
        step("合并音视频...")
        final_path = Path(output_dir) / f"{task}_成品.mp4"
        self._merge_av(str(concat_path), audio_path, str(final_path))
        results["outputs"]["video"] = str(final_path)

        # 10. 生成字幕
        step("生成字幕...")
        srt_path = Path(output_dir) / f"{task}_字幕.srt"
        self._generate_srt(str(final_path), str(srt_path))
        results["outputs"]["srt"] = str(srt_path)

        # 11. 应用调色
        step("应用调色...")
        graded_path = Path(output_dir) / f"{task}_调色.mp4"
        color_grading = style.get("color_grading", {})
        if color_grading:
            self.effect_engine.apply_color_grading(str(final_path), str(graded_path), color_grading)
            results["outputs"]["graded"] = str(graded_path)

        # 12. 导出剪映草稿
        if export_jianying:
            step("导出剪映草稿...")
            from jianying_export import export_to_jianying
            draft_path = export_to_jianying(
                video_path=str(final_path),
                srt_path=str(srt_path),
                bgm_path=bgm_path,
                draft_name=f"AI_{task}_{datetime.now().strftime('%H%M%S')}",
            )
            results["outputs"]["jianying_draft"] = str(draft_path)

        # 13. 保存报告
        report_path = Path(output_dir) / "edit_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        results["outputs"]["report"] = str(report_path)

        # 完成
        section("✨ 剪辑完成!")
        for key, path in results["outputs"].items():
            ok(f"{key}: {path}")

        return results

    def _parse_task(self, task: str) -> Tuple[str, str]:
        """解析任务，提取主题和风格"""
        task_lower = task.lower()

        # 检测风格关键词
        style_map = {
            "电影": "电影混剪",
            "混剪": "电影混剪",
            "vlog": "vlog",
            "日常": "vlog",
            "鬼畜": "鬼畜",
            "教程": "教程",
            "纪录片": "纪录片",
        }

        style_hint = "vlog"
        for keyword, style in style_map.items():
            if keyword in task:
                style_hint = style
                break

        # 提取主题（去掉风格关键词）
        theme = task
        for keyword in style_map:
            theme = theme.replace(keyword, "")
        theme = theme.strip() or task

        return theme, style_hint

    def _download_materials(self, task: str, output_dir: str) -> List[str]:
        """从网络下载素材"""
        step("搜索网络素材...")

        try:
            import yt_dlp

            # 搜索视频
            search_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "default_search": "bilisearch",
                "max_downloads": 3,
            }

            with yt_dlp.YoutubeDL(search_opts) as ydl:
                result = ydl.extract_info(f"bilisearch3:{task}", download=False)

            if not result or "entries" not in result:
                return []

            # 下载前3个
            downloaded = []
            materials_dir = ensure_dir(Path(output_dir) / "materials")

            for entry in list(result["entries"])[:3]:
                url = entry.get("url")
                if not url:
                    continue

                try:
                    dl_opts = {
                        "outtmpl": str(materials_dir / "%(id)s.%(ext)s"),
                        "format": "best[height<=480][ext=mp4]/best[height<=480]",
                        "quiet": True,
                        "merge_output_format": "mp4",
                    }

                    with yt_dlp.YoutubeDL(dl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                        if Path(filename).exists():
                            downloaded.append(filename)
                            step(f"  下载: {info.get('title', '')[:30]}")
                except Exception as e:
                    warn(f"  下载失败: {e}")

            return downloaded
        except Exception as e:
            warn(f"素材搜索失败: {e}")
            return []

    def _render_segments(self, segments: List[VideoSegment], style: Dict, output_dir: str) -> List[str]:
        """渲染所有片段"""
        rendered = []
        clips_dir = ensure_dir(Path(output_dir) / "clips")

        for i, seg in enumerate(segments):
            clip_path = clips_dir / f"clip_{i:03d}.mp4"

            # 应用特效
            effect = style.get("effects", ["cut"])[i % len(style.get("effects", ["cut"]))]

            vf = self.effect_engine._build_filter(effect)
            if not vf:
                vf = "scale=1280:720"
            else:
                vf += ",scale=1280:720"

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(seg.start),
                "-i", seg.source_path,
                "-t", str(seg.end - seg.start),
                "-vf", vf,
                "-c:v", "libx264", "-crf", "23",
                "-an",
                str(clip_path),
            ]

            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                rendered.append(str(clip_path))

        return rendered

    def _concat_clips(self, clips: List[str], output_path: str):
        """拼接片段"""
        list_file = Path(output_path).parent / "concat_list.txt"
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

    def _merge_av(self, video_path: str, audio_path: str, output_path: str):
        """合并音视频"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True)

    def _generate_srt(self, video_path: str, srt_path: str):
        """生成字幕"""
        try:
            import whisper

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = Path(tmpdir) / "audio.wav"
                run_ffmpeg([
                    "-i", video_path,
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1",
                    str(audio_path),
                ], "提取音频")

                model = whisper.load_model("small")
                result = model.transcribe(str(audio_path), language="zh", verbose=False)

                # 生成SRT
                srt_lines = []
                for i, seg in enumerate(result.get("segments", []), 1):
                    start = seg["start"]
                    end = seg["end"]
                    text = seg["text"].strip()
                    srt_lines.append(f"{i}")
                    srt_lines.append(f"{self._format_time(start)} --> {self._format_time(end)}")
                    srt_lines.append(text)
                    srt_lines.append("")

                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(srt_lines))

        except Exception as e:
            warn(f"字幕生成失败: {e}")

    def _format_time(self, seconds: float) -> str:
        """格式化SRT时间"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI剪辑师 - 全自动视频剪辑")
    parser.add_argument("task", help="剪辑任务描述（如'电影混剪'、'vlog日常'）")
    parser.add_argument("--videos", nargs="*", default=[], help="本地视频路径")
    parser.add_argument("--reference", help="参考视频URL")
    parser.add_argument("--bgm", help="BGM音频路径")
    parser.add_argument("--style", help="风格预设")
    parser.add_argument("--duration", type=float, default=30, help="目标时长")
    parser.add_argument("--output", default="E:/", help="输出目录")
    parser.add_argument("--no-jianying", action="store_true", help="不导出剪映草稿")

    args = parser.parse_args()

    editor = AutoEditor()
    editor.auto_edit(
        task=args.task,
        video_paths=args.videos,
        reference_url=args.reference,
        bgm_path=args.bgm,
        style_preset=args.style,
        target_duration=args.duration,
        output_dir=args.output,
        export_jianying=not args.no_jianying,
    )
