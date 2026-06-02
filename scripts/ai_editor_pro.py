#!/usr/bin/env python3
"""
AI 剪辑师 Pro — 学习百万剪辑狮的思路
=====================================
核心理念: 节奏随故事动，围绕内容和旋律剪辑

不是固定模板，而是:
1. 分析视频内容 → 提取故事线
2. 分析BGM旋律 → 找到情感曲线
3. 内容×旋律 → 动态匹配剪辑节奏
4. 情绪递进 → 从低潮到高潮的节奏变化
"""

import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np

from pipeline_utils import section, step, ok, warn, fail, ensure_dir, run_ffmpeg


# ============================================================
#  数据结构
# ============================================================

@dataclass
class ContentBeat:
    """内容节拍 - 视频中的关键时刻"""
    time: float              # 时间点
    duration: float          # 持续时长
    intensity: float         # 强度 0-1
    emotion: str             # 情感类型
    visual_change: float     # 视觉变化程度
    audio_energy: float      # 音频能量
    scene_type: str          # 场景类型
    story_phase: str         # 故事阶段 (setup/rising/climax/falling/resolution)


@dataclass
class MusicBeat:
    """音乐节拍 - BGM中的节奏点"""
    time: float
    beat_type: str           # downbeat/upbeat/peak/transition
    intensity: float
    frequency: float         # 频率特征
    energy: float


@dataclass
class EditPoint:
    """剪辑点 - 内容和音乐的匹配点"""
    content_time: float      # 原视频时间
    music_time: float        # BGM时间
    duration: float          # 片段时长
    speed: float             # 播放速度 (1.0=正常, <1=慢动作, >1=加速)
    transition: str          # 转场类型
    effect: str              # 特效
    intensity: float         # 强度


@dataclass
class StoryArc:
    """故事弧线"""
    phases: List[Dict]       # 故事阶段
    climax_index: int        # 高潮位置
    total_duration: float


# ============================================================
#  内容分析器 - 提取故事线
# ============================================================

class ContentStoryAnalyzer:
    """分析视频内容，提取故事线和情感曲线"""

    def analyze_story(self, video_path: str) -> Dict:
        """分析视频的故事结构"""
        section("📖 故事分析")
        step("提取内容结构...")

        # 1. 场景检测
        scenes = self._detect_scenes(video_path)

        # 2. 音频情感分析
        audio_emotions = self._analyze_audio_emotions(video_path)

        # 3. 视觉变化分析
        visual_changes = self._analyze_visual_changes(video_path)

        # 4. 构建内容节拍
        content_beats = self._build_content_beats(scenes, audio_emotions, visual_changes)

        # 5. 提取故事弧线
        story_arc = self._extract_story_arc(content_beats)

        ok(f"故事分析完成: {len(content_beats)}个内容节拍, {len(story_arc.phases)}个阶段")

        return {
            "scenes": scenes,
            "content_beats": content_beats,
            "story_arc": story_arc,
            "audio_emotions": audio_emotions,
            "visual_changes": visual_changes,
        }

    def _detect_scenes(self, video_path: str) -> List[Dict]:
        """检测场景"""
        try:
            from scenedetect import detect, ContentDetector
            scenes = detect(str(video_path), ContentDetector(threshold=27))

            result = []
            for i, scene in enumerate(scenes):
                start = scene[0].get_seconds()
                end = scene[1].get_seconds()
                if end - start > 0.3:  # 最短0.3秒
                    result.append({
                        "index": i,
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "duration": round(end - start, 3),
                    })
            return result
        except Exception as e:
            warn(f"场景检测失败: {e}")
            return []

    def _analyze_audio_emotions(self, video_path: str) -> List[Dict]:
        """分析音频情感变化"""
        try:
            import librosa

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = Path(tmpdir) / "audio.wav"
                run_ffmpeg([
                    "-i", str(video_path),
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "22050", "-ac", "1",
                    str(audio_path),
                ], "提取音频")

                y, sr = librosa.load(str(audio_path), sr=22050)

                # 能量曲线
                rms = librosa.feature.rms(y=y)[0]
                times = librosa.times_like(rms, sr=sr)

                # 频谱质心（音色亮度）
                spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

                # 过零率（噪音/清音）
                zcr = librosa.feature.zero_crossing_rate(y)[0]

                # 构建情感曲线
                emotions = []
                window_size = int(sr * 0.5)  # 0.5秒窗口

                for i in range(0, len(times), window_size):
                    end_idx = min(i + window_size, len(times))
                    t = float(times[i])
                    energy = float(np.mean(rms[i:end_idx]))
                    brightness = float(np.mean(spectral_centroid[i:end_idx]))
                    clarity = float(np.mean(zcr[i:end_idx]))

                    # 根据特征判断情感
                    if energy > 0.1 and brightness > 2000:
                        emotion = "intense"
                    elif energy > 0.05 and brightness > 1500:
                        emotion = "excited"
                    elif energy < 0.02:
                        emotion = "calm"
                    else:
                        emotion = "neutral"

                    emotions.append({
                        "time": round(t, 2),
                        "energy": round(energy, 4),
                        "brightness": round(brightness, 2),
                        "clarity": round(clarity, 4),
                        "emotion": emotion,
                    })

                return emotions
        except Exception as e:
            warn(f"音频情感分析失败: {e}")
            return []

    def _analyze_visual_changes(self, video_path: str) -> List[Dict]:
        """分析视觉变化"""
        try:
            import cv2

            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # 每秒采样10帧
            sample_interval = max(int(fps / 10), 1)
            changes = []
            prev_frame = None

            for frame_idx in range(0, total_frames, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                # 缩小尺寸加速处理
                small = cv2.resize(frame, (160, 120))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

                if prev_frame is not None:
                    # 计算帧差
                    diff = cv2.absdiff(gray, prev_frame)
                    change_score = np.mean(diff) / 255.0

                    # 计算光流（运动检测）
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                    )
                    motion = np.mean(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2))

                    time = frame_idx / fps
                    changes.append({
                        "time": round(time, 2),
                        "visual_change": round(float(change_score), 4),
                        "motion": round(float(motion), 4),
                    })

                prev_frame = gray

            cap.release()
            return changes
        except Exception as e:
            warn(f"视觉变化分析失败: {e}")
            return []

    def _build_content_beats(self, scenes: List[Dict],
                              audio_emotions: List[Dict],
                              visual_changes: List[Dict]) -> List[ContentBeat]:
        """构建内容节拍"""
        beats = []

        # 合并场景、音频、视觉信息
        for scene in scenes:
            start = scene["start"]
            end = scene["end"]
            duration = scene["duration"]

            # 找对应的音频情感
            audio_match = self._find_closest(audio_emotions, start, "time")
            visual_match = self._find_closest(visual_changes, start, "time")

            # 计算综合强度
            audio_energy = audio_match.get("energy", 0) if audio_match else 0
            visual_change = visual_match.get("visual_change", 0) if visual_match else 0
            motion = visual_match.get("motion", 0) if visual_match else 0

            intensity = (audio_energy * 0.4 + visual_change * 0.3 + motion * 0.3)
            intensity = min(1.0, intensity * 10)  # 归一化

            # 判断情感
            emotion = audio_match.get("emotion", "neutral") if audio_match else "neutral"

            # 判断故事阶段
            position_ratio = start / (scenes[-1]["end"] if scenes else 1)
            story_phase = self._determine_phase(position_ratio, intensity)

            beats.append(ContentBeat(
                time=start,
                duration=duration,
                intensity=intensity,
                emotion=emotion,
                visual_change=visual_change,
                audio_energy=audio_energy,
                scene_type="scene",
                story_phase=story_phase,
            ))

        return beats

    def _find_closest(self, data: List[Dict], time: float, key: str) -> Optional[Dict]:
        """找到最接近时间点的数据"""
        if not data:
            return None
        return min(data, key=lambda x: abs(x.get(key, 0) - time))

    def _determine_phase(self, position: float, intensity: float) -> str:
        """判断故事阶段"""
        if position < 0.15:
            return "setup"
        elif position < 0.4:
            return "rising"
        elif position < 0.6:
            return "climax" if intensity > 0.5 else "rising"
        elif position < 0.85:
            return "falling"
        else:
            return "resolution"

    def _extract_story_arc(self, content_beats: List[ContentBeat]) -> StoryArc:
        """提取故事弧线"""
        if not content_beats:
            return StoryArc(phases=[], climax_index=0, total_duration=0)

        # 按阶段分组
        phases = []
        current_phase = content_beats[0].story_phase
        phase_start = content_beats[0].time
        phase_beats = []

        for beat in content_beats:
            if beat.story_phase != current_phase:
                phases.append({
                    "phase": current_phase,
                    "start": phase_start,
                    "end": beat.time,
                    "avg_intensity": np.mean([b.intensity for b in phase_beats]) if phase_beats else 0,
                })
                current_phase = beat.story_phase
                phase_start = beat.time
                phase_beats = []
            phase_beats.append(beat)

        # 添加最后一个阶段
        if phase_beats:
            phases.append({
                "phase": current_phase,
                "start": phase_start,
                "end": content_beats[-1].time + content_beats[-1].duration,
                "avg_intensity": np.mean([b.intensity for b in phase_beats]),
            })

        # 找高潮点
        climax_index = max(range(len(phases)),
                           key=lambda i: phases[i].get("avg_intensity", 0))

        total_duration = content_beats[-1].time + content_beats[-1].duration

        return StoryArc(
            phases=phases,
            climax_index=climax_index,
            total_duration=total_duration,
        )


# ============================================================
#  音乐分析器 - 提取旋律和情感曲线
# ============================================================

class MusicAnalyzer:
    """分析BGM的旋律、节拍和情感曲线"""

    def analyze_music(self, music_path: str) -> Dict:
        """深度分析BGM"""
        section("🎵 旋律分析")
        step("提取音乐结构...")

        try:
            import librosa

            y, sr = librosa.load(str(music_path), sr=22050)
            duration = librosa.get_duration(y=y, sr=sr)

            # 1. 节拍检测
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

            # 处理tempo类型
            if hasattr(tempo, '__len__'):
                tempo_val = float(tempo[0]) if len(tempo) > 0 else 120.0
            else:
                tempo_val = float(tempo)

            # 2. 高潮点检测
            peaks = self._detect_peaks(y, sr)

            # 3. 段落结构
            sections = self._analyze_sections(y, sr)

            # 4. 情感曲线
            emotion_curve = self._build_emotion_curve(y, sr)

            # 5. 频率能量分布
            freq_bands = self._analyze_frequency_bands(y, sr)

            ok(f"音乐分析完成: BPM={tempo_val:.0f}, {len(beat_times)}个节拍, {len(peaks)}个高潮点")

            return {
                "tempo": tempo_val,
                "beat_times": beat_times,
                "peaks": peaks,
                "sections": sections,
                "emotion_curve": emotion_curve,
                "freq_bands": freq_bands,
                "duration": duration,
            }
        except Exception as e:
            warn(f"音乐分析失败: {e}")
            return {"tempo": 120, "beat_times": [], "peaks": [], "sections": [], "duration": 0}

    def _detect_peaks(self, y, sr) -> List[Dict]:
        """检测音乐高潮点"""
        import librosa

        # 能量
        rms = librosa.feature.rms(y=y)[0]
        times = librosa.times_like(rms, sr=sr)

        # 频谱对比度
        spec_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        contrast_mean = np.mean(spec_contrast, axis=0)

        # 色度特征（和弦变化）
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_change = np.diff(np.mean(chroma, axis=0))

        # 确保长度一致
        min_len = min(len(rms), len(contrast_mean), len(chroma_change))
        rms = rms[:min_len]
        times = times[:min_len]
        contrast_mean = contrast_mean[:min_len]
        chroma_change = chroma_change[:min_len]

        # 综合分数
        rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-8)
        contrast_norm = (contrast_mean - contrast_mean.min()) / (contrast_mean.max() - contrast_mean.min() + 1e-8)

        combined = 0.5 * rms_norm + 0.3 * contrast_norm + 0.2 * np.abs(chroma_change)

        # 找峰值
        threshold = np.mean(combined) + 0.8 * np.std(combined)
        peaks = []
        in_peak = False
        peak_start = 0

        for i, (t, score) in enumerate(zip(times[:len(combined)], combined)):
            if score > threshold and not in_peak:
                in_peak = True
                peak_start = t
            elif score < threshold and in_peak:
                in_peak = False
                peak_duration = t - peak_start
                if peak_duration > 0.3:
                    peaks.append({
                        "start": round(peak_start, 2),
                        "end": round(t, 2),
                        "duration": round(peak_duration, 2),
                        "intensity": round(float(np.max(combined[max(0,i-int(peak_duration*50)):i])), 3),
                    })

        return peaks

    def _analyze_sections(self, y, sr) -> List[Dict]:
        """分析音乐段落"""
        import librosa

        # 使用MFCC进行段落边界检测
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

        # 自动检测6个段落
        bounds = librosa.segment.agglomerative(mfcc, k=6)
        bound_times = librosa.frames_to_time(bounds, sr=sr).tolist()
        duration = float(librosa.get_duration(y=y, sr=sr))

        # 计算每个段落的能量特征
        rms = librosa.feature.rms(y=y)[0]
        times = librosa.times_like(rms, sr=sr)

        sections = []
        labels = ["intro", "verse1", "chorus1", "verse2", "chorus2", "outro"]

        for i, start in enumerate(bound_times):
            end = bound_times[i + 1] if i + 1 < len(bound_times) else duration

            # 计算段落平均能量
            mask = (times >= start) & (times < end)
            if np.any(mask):
                avg_energy = float(np.mean(rms[mask]))
            else:
                avg_energy = 0

            sections.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "label": labels[i] if i < len(labels) else f"section_{i}",
                "energy": round(avg_energy, 4),
            })

        return sections

    def _build_emotion_curve(self, y, sr) -> List[Dict]:
        """构建音乐情感曲线"""
        import librosa

        rms = librosa.feature.rms(y=y)[0]
        times = librosa.times_like(rms, sr=sr)

        # 频谱质心
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

        # 色度
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        harmonic_richness = np.std(chroma, axis=0)

        # 每秒一个数据点
        curve = []
        for t in range(int(times[-1]) + 1):
            mask = (times >= t) & (times < t + 1)
            if np.any(mask):
                energy = float(np.mean(rms[mask]))
                brightness = float(np.mean(spectral_centroid[mask]))
                harmony = float(np.mean(harmonic_richness[mask[:len(harmonic_richness)]]))

                # 判断情感
                if energy > 0.08 and brightness > 2000:
                    emotion = "climax"
                elif energy > 0.05 and brightness > 1500:
                    emotion = "building"
                elif energy < 0.02:
                    emotion = "calm"
                else:
                    emotion = "flowing"

                curve.append({
                    "time": t,
                    "energy": round(energy, 4),
                    "brightness": round(brightness, 2),
                    "harmony": round(harmony, 4),
                    "emotion": emotion,
                })

        return curve

    def _analyze_frequency_bands(self, y, sr) -> Dict:
        """分析频率能量分布"""
        import librosa

        # 计算STFT
        S = np.abs(librosa.stft(y))

        # 分离频率带
        freqs = librosa.fft_frequencies(sr=sr)

        # 低频 (20-200Hz) - bass
        bass_mask = (freqs >= 20) & (freqs < 200)
        bass_energy = np.mean(S[bass_mask, :]) if np.any(bass_mask) else 0

        # 中频 (200-2000Hz) - 人声/旋律
        mid_mask = (freqs >= 200) & (freqs < 2000)
        mid_energy = np.mean(S[mid_mask, :]) if np.any(mid_mask) else 0

        # 高频 (2000-20000Hz) - 亮度/细节
        high_mask = (freqs >= 2000) & (freqs < 20000)
        high_energy = np.mean(S[high_mask, :]) if np.any(high_mask) else 0

        return {
            "bass": round(float(bass_energy), 4),
            "mid": round(float(mid_energy), 4),
            "high": round(float(high_energy), 4),
        }


# ============================================================
#  百万剪辑狮风格匹配器
# ============================================================

class MillionEditorMatcher:
    """
    学习B站百万剪辑狮的剪辑思路:

    1. 踩点精准 - 每个cut都落在BGM节拍上
    2. 情绪递进 - 从低潮到高潮，节奏逐渐加快
    3. 内容驱动 - 剪辑节奏跟随故事发展
    4. 旋律匹配 - 画面变化与音乐旋律同步
    5. 呼吸感 - 有快有慢，有张有弛
    """

    def match_content_to_music(
        self,
        content_analysis: Dict,
        music_analysis: Dict,
        target_duration: float,
    ) -> List[EditPoint]:
        """将内容匹配到音乐"""
        section("🎯 节奏匹配")
        step("内容×旋律 智能匹配...")

        content_beats = content_analysis.get("content_beats", [])
        story_arc = content_analysis.get("story_arc")
        music_beats = music_analysis.get("beat_times", [])
        music_peaks = music_analysis.get("peaks", [])
        music_sections = music_analysis.get("sections", [])
        music_emotion = music_analysis.get("emotion_curve", [])

        if not content_beats or not music_beats:
            warn("内容或音乐分析数据不足")
            return []

        # 1. 找到音乐的高潮段落
        chorus_section = self._find_chorus(music_sections, music_peaks)
        step(f"  高潮段落: {chorus_section['start']:.1f}s - {chorus_section['end']:.1f}s")

        # 2. 选取音乐段落（从高潮前开始）
        music_start = max(0, chorus_section["start"] - 10)
        music_end = min(music_analysis["duration"], music_start + target_duration)

        # 3. 提取该段落的节拍
        section_beats = [b for b in music_beats if music_start <= b <= music_end]

        # 4. 根据音乐情感调整剪辑节奏
        edit_points = self._dynamic_match(
            content_beats, section_beats, music_emotion,
            music_start, target_duration, story_arc
        )

        # 5. 应用百万剪辑狮的技巧
        edit_points = self._apply_million_editor_style(edit_points, music_peaks)

        ok(f"匹配完成: {len(edit_points)}个剪辑点")
        return edit_points

    def _find_chorus(self, sections: List[Dict], peaks: List[Dict]) -> Dict:
        """找到音乐高潮段落"""
        # 优先找chorus标签
        for s in sections:
            if "chorus" in s.get("label", ""):
                return s

        # 找能量最高的段落
        if sections:
            return max(sections, key=lambda s: s.get("energy", 0))

        # 用高潮点推断
        if peaks:
            best_peak = max(peaks, key=lambda p: p.get("intensity", 0))
            return {
                "start": max(0, best_peak["start"] - 5),
                "end": best_peak["end"] + 5,
            }

        return {"start": 0, "end": 30}

    def _dynamic_match(
        self,
        content_beats: List[ContentBeat],
        music_beats: List[float],
        music_emotion: List[Dict],
        music_start: float,
        target_duration: float,
        story_arc: StoryArc,
    ) -> List[EditPoint]:
        """动态匹配 - 节奏随故事动"""
        edit_points = []

        # 计算每个阶段的剪辑密度
        if story_arc and story_arc.phases:
            phase_densities = self._calculate_phase_densities(story_arc)
        else:
            phase_densities = {"setup": 0.5, "rising": 0.7, "climax": 1.0, "falling": 0.6, "resolution": 0.4}

        # 遍历音乐节拍，匹配内容
        content_idx = 0
        for i, music_beat in enumerate(music_beats):
            if content_idx >= len(content_beats):
                break

            # 获取当前位置的音乐情感
            beat_emotion = self._get_emotion_at_time(music_emotion, music_beat)

            # 获取当前位置的故事阶段
            story_phase = self._get_story_phase_at_time(story_arc, music_beat - music_start)

            # 根据阶段调整剪辑密度
            density = phase_densities.get(story_phase, 0.5)

            # 决定是否在这个节拍点剪辑
            if i % max(1, int(1 / density)) == 0:
                content_beat = content_beats[content_idx]

                # 计算片段时长（根据情感强度调整）
                if beat_emotion == "climax":
                    duration = 0.5  # 高潮时快速剪辑
                    speed = 1.2
                elif beat_emotion == "building":
                    duration = 1.0
                    speed = 1.0
                elif beat_emotion == "calm":
                    duration = 2.0  # 平静时放慢
                    speed = 0.8
                else:
                    duration = 1.5
                    speed = 1.0

                # 选择转场
                transition = self._select_transition(story_phase, beat_emotion)

                edit_points.append(EditPoint(
                    content_time=content_beat.time,
                    music_time=music_beat - music_start,
                    duration=duration,
                    speed=speed,
                    transition=transition,
                    effect=self._select_effect(story_phase),
                    intensity=content_beat.intensity,
                ))

                content_idx += 1

        return edit_points

    def _calculate_phase_densities(self, story_arc: StoryArc) -> Dict[str, float]:
        """计算每个阶段的剪辑密度"""
        densities = {}
        for phase in story_arc.phases:
            phase_name = phase["phase"]
            intensity = phase.get("avg_intensity", 0.5)

            # 根据阶段和强度计算密度
            if phase_name == "setup":
                densities[phase_name] = 0.4 + intensity * 0.2
            elif phase_name == "rising":
                densities[phase_name] = 0.5 + intensity * 0.3
            elif phase_name == "climax":
                densities[phase_name] = 0.8 + intensity * 0.2
            elif phase_name == "falling":
                densities[phase_name] = 0.5 + intensity * 0.1
            else:  # resolution
                densities[phase_name] = 0.3 + intensity * 0.1

        return densities

    def _get_emotion_at_time(self, emotion_curve: List[Dict], time: float) -> str:
        """获取指定时间的音乐情感"""
        if not emotion_curve:
            return "neutral"

        closest = min(emotion_curve, key=lambda e: abs(e["time"] - time))
        return closest.get("emotion", "neutral")

    def _get_story_phase_at_time(self, story_arc: StoryArc, time: float) -> str:
        """获取指定时间的故事阶段"""
        if not story_arc or not story_arc.phases:
            return "rising"

        for phase in story_arc.phases:
            if phase["start"] <= time <= phase["end"]:
                return phase["phase"]

        return "rising"

    def _select_transition(self, story_phase: str, music_emotion: str) -> str:
        """选择转场类型"""
        if music_emotion == "climax":
            return "flash"  # 高潮用闪白
        elif story_phase == "setup":
            return "fade"  # 开场用淡入
        elif story_phase == "rising":
            return "cut"  # 上升用硬切
        elif story_phase == "climax":
            return "zoom"  # 高潮用缩放
        elif story_phase == "falling":
            return "dissolve"  # 下降用溶解
        else:
            return "cut"

    def _select_effect(self, story_phase: str) -> str:
        """选择特效"""
        effects = {
            "setup": "fade_in",
            "rising": "speed_ramp",
            "climax": "slow_motion",
            "falling": "normal",
            "resolution": "fade_out",
        }
        return effects.get(story_phase, "normal")

    def _apply_million_editor_style(self, edit_points: List[EditPoint],
                                      music_peaks: List[Dict]) -> List[EditPoint]:
        """应用百万剪辑狮的风格技巧"""
        if not edit_points:
            return edit_points

        # 1. 在音乐高潮点使用慢动作
        for peak in music_peaks:
            for ep in edit_points:
                if abs(ep.music_time - peak["start"]) < 1.0:
                    ep.speed = 0.5  # 慢动作
                    ep.effect = "slow_motion"

        # 2. 高潮前加速（蓄力感）
        for i, ep in enumerate(edit_points):
            if i > 0 and i < len(edit_points) - 1:
                next_ep = edit_points[i + 1]
                if ep.effect == "slow_motion" and next_ep.effect != "slow_motion":
                    # 高潮前的片段加速
                    edit_points[i - 1].speed = 1.5

        # 3. 确保有呼吸感（不能一直快）
        fast_count = 0
        for ep in edit_points:
            if ep.duration < 1.0:
                fast_count += 1
                if fast_count > 4:
                    # 连续快切后给一个长镜头
                    ep.duration = 2.5
                    ep.speed = 0.8
                    fast_count = 0

        return edit_points


# ============================================================
#  渲染引擎
# ============================================================

class ProRenderer:
    """专业渲染引擎"""

    def render(
        self,
        video_path: str,
        edit_points: List[EditPoint],
        bgm_path: str,
        output_path: str,
        color_grading: Dict = None,
    ) -> str:
        """渲染最终视频"""
        section("🎬 渲染成品")
        step(f"剪辑点: {len(edit_points)}个")

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 渲染每个片段
            step("渲染片段...")
            clips = []
            for i, ep in enumerate(edit_points):
                clip_path = Path(tmpdir) / f"clip_{i:04d}.mp4"
                if self._render_clip(video_path, ep, str(clip_path)):
                    clips.append(str(clip_path))

            # 2. 拼接
            step("拼接视频...")
            concat_path = Path(tmpdir) / "concat.mp4"
            self._concat_clips(clips, str(concat_path))

            # 3. 添加BGM
            step("混合BGM...")
            with_bgm = Path(tmpdir) / "with_bgm.mp4"
            self._add_bgm(str(concat_path), bgm_path, str(with_bgm), edit_points)

            # 4. 调色
            if color_grading:
                step("应用调色...")
                self._apply_color_grading(str(with_bgm), output_path, color_grading)
            else:
                import shutil
                shutil.copy2(str(with_bgm), output_path)

        ok(f"渲染完成: {output_path}")
        return output_path

    def _render_clip(self, video_path: str, ep: EditPoint, output_path: str) -> bool:
        """渲染单个片段"""
        # 构建滤镜
        vf_parts = ["scale=1280:720"]

        # 速度调整
        if ep.speed != 1.0:
            vf_parts.append(f"setpts={1/ep.speed}*PTS")

        # 特效
        if ep.effect == "slow_motion":
            vf_parts.append("eq=brightness=0.05")
        elif ep.effect == "fade_in":
            vf_parts.append("fade=t=in:st=0:d=0.3")
        elif ep.effect == "fade_out":
            vf_parts.append(f"fade=t=out:st={ep.duration-0.3}:d=0.3")

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ep.content_time),
            "-i", video_path,
            "-t", str(ep.duration),
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
                  edit_points: List[EditPoint]):
        """添加BGM"""
        # 计算BGM起始时间（从第一个剪辑点对应的音乐时间）
        bgm_start = edit_points[0].music_time if edit_points else 0

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

    def _apply_color_grading(self, input_path: str, output_path: str, grading: Dict):
        """应用调色"""
        temperature = grading.get("temperature", "neutral")
        contrast = grading.get("contrast", 1.1)
        saturation = grading.get("saturation", 1.0)

        vf_parts = [f"eq=contrast={contrast}:saturation={saturation}"]

        if temperature == "warm":
            vf_parts.append("colorbalance=rs=0.1:gs=-0.05:bs=-0.1")
        elif temperature == "cool":
            vf_parts.append("colorbalance=rs=-0.1:gs=0:bs=0.1")
        elif temperature == "cinematic":
            vf_parts.append("colorbalance=rs=0.05:gs=0:bs=-0.05,eq=gamma=0.95")

        vf = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "23",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True)


# ============================================================
#  TTS + 字幕
# ============================================================

class AudioProcessor:
    """音频处理器"""

    def generate_narration(self, text: str, output_path: str,
                           voice: str = "zh-CN-YunxiNeural") -> str:
        """生成TTS旁白"""
        import asyncio
        import edge_tts

        async def gen():
            communicate = edge_tts.Communicate(text, voice, rate="+10%")
            await communicate.save(output_path)

        asyncio.run(gen())
        return output_path

    def generate_srt(self, video_path: str, output_path: str) -> str:
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

                srt_lines = []
                for i, seg in enumerate(result.get("segments", []), 1):
                    start = seg["start"]
                    end = seg["end"]
                    text = seg["text"].strip()
                    srt_lines.append(f"{i}")
                    srt_lines.append(f"{self._format_time(start)} --> {self._format_time(end)}")
                    srt_lines.append(text)
                    srt_lines.append("")

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(srt_lines))

                return output_path
        except Exception as e:
            warn(f"字幕生成失败: {e}")
            return ""

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ============================================================
#  AI剪辑师 Pro - 主控制器
# ============================================================

class AIEditorPro:
    """
    AI剪辑师 Pro - 学习百万剪辑狮的思路

    核心理念: 节奏随故事动，围绕内容和旋律剪辑

    工作流:
    1. 分析视频内容 → 提取故事线
    2. 分析BGM旋律 → 找到情感曲线
    3. 内容×旋律 → 动态匹配剪辑节奏
    4. 情绪递进 → 从低潮到高潮的节奏变化
    5. 渲染成品 → 导出剪映草稿
    """

    def __init__(self):
        self.content_analyzer = ContentStoryAnalyzer()
        self.music_analyzer = MusicAnalyzer()
        self.matcher = MillionEditorMatcher()
        self.renderer = ProRenderer()
        self.audio_processor = AudioProcessor()

    def edit(
        self,
        video_path: str,
        bgm_path: str,
        output_dir: str = "E:/",
        target_duration: float = 30,
        style: str = "auto",
        export_jianying: bool = True,
    ) -> Dict:
        """
        一句话剪辑

        Args:
            video_path: 视频素材路径
            bgm_path: BGM音频路径
            output_dir: 输出目录
            target_duration: 目标时长
            style: 风格 (auto/cinematic/vlog/ghoul)
            export_jianying: 是否导出剪映
        """
        section("🎬 AI剪辑师 Pro")
        step(f"视频: {Path(video_path).name}")
        step(f"BGM: {Path(bgm_path).name}")
        step(f"目标: {target_duration}秒")

        results = {
            "timestamp": datetime.now().isoformat(),
            "video": video_path,
            "bgm": bgm_path,
            "outputs": {},
        }

        # 1. 分析视频内容
        content = self.content_analyzer.analyze_story(video_path)
        results["content_analysis"] = {
            "beats": len(content.get("content_beats", [])),
            "phases": len(content.get("story_arc", StoryArc([], 0, 0)).phases),
        }

        # 2. 分析BGM旋律
        music = self.music_analyzer.analyze_music(bgm_path)
        results["music_analysis"] = {
            "tempo": music.get("tempo", 0),
            "beats": len(music.get("beat_times", [])),
            "peaks": len(music.get("peaks", [])),
        }

        # 3. 节奏匹配
        edit_points = self.matcher.match_content_to_music(
            content, music, target_duration
        )
        results["edit_points"] = len(edit_points)

        # 4. 确定调色风格
        if style == "auto":
            # 根据BGM风格自动选择
            tempo = music.get("tempo", 120)
            if tempo > 140:
                color_grading = {"temperature": "vivid", "contrast": 1.3, "saturation": 1.4}
            elif tempo > 100:
                color_grading = {"temperature": "cinematic", "contrast": 1.2, "saturation": 0.9}
            else:
                color_grading = {"temperature": "warm", "contrast": 1.1, "saturation": 1.0}
        else:
            color_grading = {"temperature": style, "contrast": 1.1, "saturation": 1.0}

        # 5. 渲染成品
        output_path = str(Path(output_dir) / "成品.mp4")
        self.renderer.render(video_path, edit_points, bgm_path, output_path, color_grading)
        results["outputs"]["video"] = output_path

        # 6. 生成字幕
        srt_path = str(Path(output_dir) / "字幕.srt")
        self.audio_processor.generate_srt(output_path, srt_path)
        results["outputs"]["srt"] = srt_path

        # 7. 导出剪映草稿
        if export_jianying:
            step("导出剪映草稿...")
            from jianying_export import export_to_jianying
            draft_path = export_to_jianying(
                video_path=output_path,
                srt_path=srt_path,
                bgm_path=bgm_path,
                draft_name=f"AI剪辑_{datetime.now().strftime('%H%M%S')}",
            )
            results["outputs"]["jianying"] = str(draft_path)

        # 8. 保存报告
        report_path = str(Path(output_dir) / "剪辑报告.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        results["outputs"]["report"] = report_path

        # 完成
        section("✨ 剪辑完成!")
        for key, path in results["outputs"].items():
            ok(f"{key}: {path}")

        return results


# ============================================================
#  CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI剪辑师 Pro - 学习百万剪辑狮的思路")
    parser.add_argument("video", help="视频素材路径")
    parser.add_argument("bgm", help="BGM音频路径")
    parser.add_argument("--output", default="E:/", help="输出目录")
    parser.add_argument("--duration", type=float, default=30, help="目标时长")
    parser.add_argument("--style", default="auto", help="风格 (auto/cinematic/vlog/ghoul)")
    parser.add_argument("--no-jianying", action="store_true", help="不导出剪映草稿")

    args = parser.parse_args()

    editor = AIEditorPro()
    editor.edit(
        video_path=args.video,
        bgm_path=args.bgm,
        output_dir=args.output,
        target_duration=args.duration,
        style=args.style,
        export_jianying=not args.no_jianying,
    )
