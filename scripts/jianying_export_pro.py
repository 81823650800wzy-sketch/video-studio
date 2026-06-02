#!/usr/bin/env python3
"""
剪映草稿导出器 Pro
==================
创建真正的剪映工程结构，包含:
- 视频轨道（多个片段 + 切口）
- 字幕轨道（每个字幕独立segment）
- 音频轨道（BGM）
- 特效和关键帧
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# 剪映草稿目录
JIANYING_DRAFT_DIR = Path(os.path.expanduser(
    "~/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft"
))


def generate_id():
    """生成32位ID"""
    return uuid.uuid4().hex


def srt_time_to_us(time_str: str) -> int:
    """SRT时间格式转微秒: HH:MM:SS,mmm -> microseconds"""
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    h = int(parts[0])
    m = int(parts[1])
    s = float(parts[2])
    total_seconds = h * 3600 + m * 60 + s
    return int(total_seconds * 1_000_000)


def parse_srt(srt_path: str) -> List[Dict]:
    """解析SRT文件"""
    segments = []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            time_line = lines[1]
            start_str, end_str = time_line.split(" --> ")
            start = srt_time_to_us(start_str.strip())
            end = srt_time_to_us(end_str.strip())
            text = "\n".join(lines[2:])
            segments.append({"start": start, "end": end, "text": text})

    return segments


def get_video_info(video_path: str) -> Dict:
    """获取视频信息"""
    import subprocess
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=width,height,duration,r_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json", str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)

    width = int(info["streams"][0].get("width", 1280))
    height = int(info["streams"][0].get("height", 720))
    duration = float(info["format"].get("duration", 0))

    # 解析帧率
    fps_str = info["streams"][0].get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) > 0 else 30
    else:
        fps = float(fps_str)

    return {"width": width, "height": height, "duration": duration, "fps": fps}


def create_video_material(video_path: str, video_info: Dict) -> Dict:
    """创建视频素材对象"""
    video_id = generate_id()
    duration_us = int(video_info["duration"] * 1_000_000)

    return {
        "id": video_id,
        "type": "video",
        "category_id": "",
        "category_name": "local",
        "check_flag": 63487,
        "crop": {
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
        },
        "crop_ratio": "free",
        "crop_scale": 1.0,
        "duration": duration_us,
        "extra_type_option": 0,
        "formula_id": "",
        "freeze": None,
        "gameplay": None,
        "has_audio": True,
        "height": video_info["height"],
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_ai_generate_content": False,
        "is_copyright": False,
        "is_text_edit_overdub": False,
        "is_unified_beauty_mode": False,
        "local_id": "",
        "local_material_id": "",
        "material_id": "",
        "material_name": Path(video_path).stem,
        "material_url": "",
        "matting": {
            "flag": 0, "has_use_quick_brush": False,
            "has_use_quick_eraser": False, "interactiveTime": [],
            "path": "", "strokes": [],
        },
        "media_path": "",
        "object_locked": None,
        "origin_material_id": "",
        "path": str(video_path).replace("\\", "/"),
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "smart_motion": None,
        "source": 0,
        "source_platform": 0,
        "stable": None,
        "team_id": "",
        "video_algorithm": {
            "algorithms": [],
            "deflicker": None,
            "motion_blur_config": None,
            "noise_reduction": None,
            "path": "",
            "quality_enhance": None,
            "time_range": None,
        },
        "width": video_info["width"],
    }


def create_audio_material(audio_path: str, duration_us: int) -> Dict:
    """创建音频素材对象"""
    audio_id = generate_id()

    return {
        "id": audio_id,
        "type": "music",
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 0,
        "duration": duration_us,
        "effect_id": "",
        "formula_id": "",
        "intensifies_path": "",
        "is_ugc": False,
        "local_material_id": "",
        "music_id": "",
        "name": Path(audio_path).stem,
        "path": str(audio_path).replace("\\", "/"),
        "query": "",
        "resource_id": "",
        "search_id": "",
        "source_from": "",
        "source_platform": 0,
        "team_id": "",
        "text_id": "",
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "tone_platform": "",
        "tone_second_category_id": "",
        "tone_second_category_name": "",
        "tone_speaker": "",
        "tone_type": "",
        "type": "music",
        "video_id": "",
        "wave_points": [],
    }


def create_video_segment(
    material_id: str,
    source_start: int,
    duration: int,
    target_start: int,
    speed: float = 1.0,
    segment_index: int = 0,
) -> Dict:
    """创建视频片段（带切口信息）"""
    segment_id = generate_id()

    # 速度调整
    if speed != 1.0:
        source_duration = int(duration / speed)
    else:
        source_duration = duration

    return {
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0},
        },
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": False,
        "enable_lut": False,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": segment_id,
        "intensifies_audio": None,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_db_value": -5.91,
        "material_id": material_id,
        "render_index": segment_index,
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0,
        },
        "reverse": False,
        "source_timerange": {
            "duration": source_duration,
            "start": source_start,
        },
        "speed": speed,
        "target_timerange": {
            "duration": duration,
            "start": target_start,
        },
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": 1.0,
    }


def create_text_segment(
    text: str,
    start_us: int,
    duration_us: int,
    segment_index: int = 0,
    font_size: int = 8,
    font_color: str = "#FFFFFF",
) -> Dict:
    """创建字幕片段"""
    segment_id = generate_id()
    content_id = generate_id()

    return {
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.35},
        },
        "common_keyframes": [],
        "enable_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": False,
        "enable_lut": False,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [content_id],
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": segment_id,
        "intensifies_audio": None,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_db_value": -5.91,
        "material_id": content_id,
        "render_index": segment_index,
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0,
        },
        "reverse": False,
        "source_timerange": {"duration": duration_us, "start": 0},
        "speed": 1.0,
        "target_timerange": {"duration": duration_us, "start": start_us},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": 1.0,
    }


def create_text_content(text: str, font_size: int = 8, font_color: str = "#FFFFFF") -> Dict:
    """创建字幕内容对象"""
    content_id = generate_id()

    return {
        "id": content_id,
        "type": "text",
        "add_type": 0,
        "alignment": 1,
        "background_alpha": 1.0,
        "background_color": "",
        "background_height": 0.14,
        "background_horizontal_offset": 0.0,
        "background_round_radius": 0.0,
        "background_style": 0,
        "background_vertical_offset": 0.004,
        "background_width": 0.14,
        "bold_width": 0.0,
        "border_alpha": 1.0,
        "border_color": "#000000",
        "border_width": 0.08,
        "caption_template_info": {
            "category_id": "",
            "category_name": "",
            "effect_id": "",
            "is_new": False,
            "path": "",
            "request_id": "",
            "resource_id": "",
            "resource_name": "",
            "source_from": "",
        },
        "check_flag": 7,
        "combo_info": {"text_templates": []},
        "content": text,
        "fixed_height": -1.0,
        "fixed_width": -1.0,
        "font_category_id": "",
        "font_category_name": "",
        "font_id": "",
        "font_name": "",
        "font_path": "",
        "font_resource_id": "",
        "font_size": font_size,
        "font_source_platform": 0,
        "font_team_id": "",
        "font_title": "系统默认",
        "font_url": "",
        "fonts": [],
        "force_apply_line_max_width": False,
        "global_alpha": 1.0,
        "group_id": "",
        "has_shadow": False,
        "initial_scale": 1.0,
        "inner_padding": -1.0,
        "is_rich_text": False,
        "italic_degree": 0,
        "ktv_color": "",
        "language": "",
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "line_feed": 1,
        "line_max_width": 0.82,
        "line_spacing": 0.02,
        "multi_language_current": "none",
        "name": "",
        "original_size": [],
        "preset_category": "",
        "preset_category_id": "",
        "preset_has_set_alignment": False,
        "preset_id": "",
        "preset_index": 0,
        "preset_name": "",
        "recognize_task_id": "",
        "recognize_type": 0,
        "relevance_segment": [],
        "shadow_alpha": 0.9,
        "shadow_angle": -45.0,
        "shadow_color": "",
        "shadow_distance": 0.04,
        "shadow_point": {"x": 0.6503114709854126, "y": -0.6503114709854126},
        "shadow_smoothing": 0.45,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "style_name": "",
        "sub_type": 0,
        "subtitle_keywords": None,
        "text_alpha": 1.0,
        "text_color": font_color,
        "text_curve": None,
        "text_preset_resource_id": "",
        "text_size": font_size,
        "text_to_audio_ids": [],
        "tts_auto_update": False,
        "underline": False,
        "underline_offset": 0.22,
        "underline_width": 0.05,
        "use_effect_default_color": True,
        "words": {
            "end_time": [],
            "start_time": [],
            "text": [],
        },
    }


def create_audio_segment(
    material_id: str,
    start_us: int,
    duration_us: int,
    target_start: int = 0,
    volume: float = 1.0,
) -> Dict:
    """创建音频片段"""
    segment_id = generate_id()

    return {
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0},
        },
        "common_keyframes": [],
        "enable_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": False,
        "enable_lut": False,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": segment_id,
        "intensifies_audio": None,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_db_value": -5.91,
        "material_id": material_id,
        "render_index": 0,
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0,
        },
        "reverse": False,
        "source_timerange": {"duration": duration_us, "start": start_us},
        "speed": 1.0,
        "target_timerange": {"duration": duration_us, "start": target_start},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": volume,
    }


def create_speed_material(speed: float = 1.0) -> Dict:
    """创建速度控制素材"""
    return {
        "id": generate_id(),
        "type": "speed",
        "mode": 0,
        "speed": speed,
        "curve_speed": None,
    }


def export_to_jianying_pro(
    video_path: str,
    srt_path: Optional[str] = None,
    bgm_path: Optional[str] = None,
    draft_name: Optional[str] = None,
    clips: Optional[List[Dict]] = None,
) -> str:
    """
    导出到剪映草稿（专业版）

    Args:
        video_path: 视频文件路径
        srt_path: SRT字幕文件路径
        bgm_path: BGM音频文件路径
        draft_name: 草稿名称
        clips: 视频切点列表 [{"start": 秒, "duration": 秒, "speed": 1.0}, ...]
    """
    if not JIANYING_DRAFT_DIR.exists():
        print(f"❌ 剪映草稿目录不存在: {JIANYING_DRAFT_DIR}")
        return None

    # 获取视频信息
    video_info = get_video_info(video_path)
    duration_us = int(video_info["duration"] * 1_000_000)

    # 生成草稿名称
    if not draft_name:
        draft_name = f"VS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 创建草稿目录
    draft_dir = JIANYING_DRAFT_DIR / draft_name
    draft_dir.mkdir(parents=True, exist_ok=True)

    # 复制文件到草稿目录
    video_dest = draft_dir / Path(video_path).name
    shutil.copy2(video_path, video_dest)

    srt_dest = None
    if srt_path and Path(srt_path).exists():
        srt_dest = draft_dir / Path(srt_path).name
        shutil.copy2(srt_path, srt_dest)

    bgm_dest = None
    if bgm_path and Path(bgm_path).exists():
        bgm_dest = draft_dir / Path(bgm_path).name
        shutil.copy2(bgm_path, bgm_dest)

    # ========== 创建工程结构 ==========

    # 1. 视频素材
    video_material = create_video_material(str(video_dest), video_info)
    video_material_id = video_material["id"]

    # 2. 视频轨道（多个片段 + 切口）
    video_segments = []
    if clips:
        # 使用指定的切点
        target_start = 0
        for i, clip in enumerate(clips):
            source_start_us = int(clip["start"] * 1_000_000)
            duration_us = int(clip["duration"] * 1_000_000)
            speed = clip.get("speed", 1.0)

            segment = create_video_segment(
                material_id=video_material_id,
                source_start=source_start_us,
                duration=duration_us,
                target_start=target_start,
                speed=speed,
                segment_index=i,
            )
            video_segments.append(segment)
            target_start += duration_us
    else:
        # 整段视频作为一个segment
        video_segments.append(create_video_segment(
            material_id=video_material_id,
            source_start=0,
            duration=duration_us,
            target_start=0,
            speed=1.0,
            segment_index=0,
        ))

    video_track = {
        "attribute": 0,
        "flag": 0,
        "id": generate_id(),
        "is_default_name": True,
        "name": "",
        "segments": video_segments,
        "type": "video",
    }

    # 3. 字幕轨道
    text_track = None
    text_materials = []
    if srt_dest:
        srt_segments = parse_srt(str(srt_dest))
        text_segments = []

        for i, srt_seg in enumerate(srt_segments):
            duration = srt_seg["end"] - srt_seg["start"]
            text_content = create_text_content(srt_seg["text"], font_size=8)
            text_materials.append(text_content)

            text_seg = create_text_segment(
                text=srt_seg["text"],
                start_us=srt_seg["start"],
                duration_us=duration,
                segment_index=i,
            )
            # 关联content ID
            text_seg["material_id"] = text_content["id"]
            text_seg["extra_material_refs"] = [text_content["id"]]
            text_segments.append(text_seg)

        text_track = {
            "attribute": 0,
            "flag": 0,
            "id": generate_id(),
            "is_default_name": True,
            "name": "字幕",
            "segments": text_segments,
            "type": "text",
        }

    # 4. 音频轨道
    audio_track = None
    audio_material = None
    if bgm_dest:
        bgm_info = get_video_info(str(bgm_dest))
        bgm_duration_us = int(bgm_info["duration"] * 1_000_000)

        audio_material = create_audio_material(str(bgm_dest), bgm_duration_us)

        audio_seg = create_audio_segment(
            material_id=audio_material["id"],
            start_us=0,
            duration_us=min(bgm_duration_us, duration_us),
            target_start=0,
            volume=0.7,
        )

        audio_track = {
            "attribute": 0,
            "flag": 0,
            "id": generate_id(),
            "is_default_name": True,
            "name": "BGM",
            "segments": [audio_seg],
            "type": "audio",
        }

    # 5. 组装tracks
    tracks = [video_track]
    if text_track:
        tracks.append(text_track)
    if audio_track:
        tracks.append(audio_track)

    # 6. 组装materials
    materials = {
        "audios": [audio_material] if audio_material else [],
        "canvases": [],
        "digital_humans": [],
        "drafts": [],
        "effects": [],
        "flowers": [],
        "green_screens": [],
        "handwrites": [],
        "images": [],
        "log_color_wheels": [],
        "loudnesses": [],
        "manual_deformations": [],
        "material_animations": [],
        "material_colors": [],
        "multi_language_refs": [],
        "placeholders": [],
        "plugin_effects": [],
        "realtime_denoises": [],
        "shapes": [],
        "smart_crops": [],
        "smart_relights": [],
        "sound_channel_mappings": [],
        "speeds": [create_speed_material()],
        "stickers": [],
        "tail_leaders": [],
        "text_templates": [],
        "texts": text_materials,
        "transitions": [],
        "video_effects": [],
        "video_trackings": [],
        "videos": [video_material],
        "vocal_beautifys": [],
        "vocal_separations": [],
    }

    # 7. 组装draft_content
    draft_content = {
        "canvas_config": {
            "height": video_info["height"],
            "width": video_info["width"],
            "ratio": "original",
        },
        "color_space": 0,
        "config": {},
        "cover": None,
        "create_time": 0,
        "duration": duration_us,
        "extra_info": None,
        "fps": video_info["fps"],
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": generate_id(),
        "keyframe_graph_list": [],
        "last_modified_platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.8.0",
            "device_id": "",
            "hard_disk_id": "",
            "mac_address": "",
            "os": "windows",
            "os_version": "10.0.26200",
        },
        "materials": materials,
        "mutable_config": None,
        "name": "",
        "new_version": "",
        "path": "",
        "platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.8.0",
            "device_id": "",
            "hard_disk_id": "",
            "mac_address": "",
            "os": "windows",
            "os_version": "10.0.26200",
        },
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "tracks": tracks,
        "uneven_animation_template_info": {},
        "update_time": 0,
        "version": 360000,
        "smart_ads_info": {},
        "function_assistant_info": {
            "algorithm_list": [],
            "function_type": 0,
        },
    }

    # 8. 保存draft_content.json
    content_path = draft_dir / "draft_content.json"
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(draft_content, f, ensure_ascii=False, indent=2)

    # 9. 保存draft_meta_info.json
    meta_info = {
        "draft_fold_path": str(draft_dir),
        "draft_id": draft_content["id"],
        "draft_name": draft_name,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": str(JIANYING_DRAFT_DIR),
        "draft_timeline_materials_size_": 0,
        "draft_type": "",
        "tm_draft_create": int(datetime.now().timestamp()),
        "tm_draft_modified": int(datetime.now().timestamp()),
        "tm_duration": duration_us,
    }

    meta_path = draft_dir / "draft_meta_info.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=2)

    # 10. 输出统计
    print(f"✅ 剪映草稿已创建: {draft_dir}")
    print(f"   名称: {draft_name}")
    print(f"   时长: {video_info['duration']:.1f}秒")
    print(f"   分辨率: {video_info['width']}x{video_info['height']}")
    print(f"   视频轨道: {len(video_segments)} 个片段")
    if text_track:
        print(f"   字幕轨道: {len(text_track['segments'])} 条字幕")
    if audio_track:
        print(f"   音频轨道: BGM")

    return str(draft_dir)


# ============================================================
#  CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导出视频到剪映草稿（专业版）")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("--srt", help="SRT字幕文件路径")
    parser.add_argument("--bgm", help="BGM音频文件路径")
    parser.add_argument("--name", help="草稿名称")
    parser.add_argument("--clips", help="切点JSON文件")

    args = parser.parse_args()

    clips = None
    if args.clips and Path(args.clips).exists():
        with open(args.clips, "r", encoding="utf-8") as f:
            clips = json.load(f)

    export_to_jianying_pro(
        video_path=args.video,
        srt_path=args.srt,
        bgm_path=args.bgm,
        draft_name=args.name,
        clips=clips,
    )
