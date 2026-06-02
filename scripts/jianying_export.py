#!/usr/bin/env python3
"""
剪映草稿导出器
==============
将视频导出为剪映草稿格式，保存到剪映草稿目录
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path


# 剪映草稿目录
JIANYING_DRAFT_DIR = Path(os.path.expanduser(
    "~/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft"
))


def generate_draft_id():
    """生成剪映风格的草稿ID"""
    return uuid.uuid4().hex


def create_draft_content(video_path, srt_path=None, bgm_path=None, duration=30):
    """创建剪映draft_content.json格式"""

    # 生成唯一ID
    video_id = generate_draft_id()
    audio_id = generate_draft_id()
    track_id = generate_draft_id()

    # 获取视频信息
    video_info = get_video_info(video_path)

    content = {
        "canvas_config": {
            "height": video_info.get("height", 720),
            "width": video_info.get("width", 1280),
            "ratio": "original"
        },
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None
        },
        "cover": None,
        "create_time": 0,
        "duration": int(duration * 1000000),  # 微秒
        "extra_info": None,
        "fps": 30.0,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": generate_draft_id(),
        "keyframe_graph_list": [],
        "last_modified_platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.8.0",
            "device_id": "",
            "hard_disk_id": "",
            "mac_address": "",
            "os": "windows",
            "os_version": "10.0.26200"
        },
        "materials": {
            "audios": [],
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
            "speeds": [],
            "stickers": [],
            "tail_leaders": [],
            "text_templates": [],
            "texts": [],
            "transitions": [],
            "video_effects": [],
            "video_trackings": [],
            "videos": [
                {
                    "id": video_id,
                    "type": "video",
                    "category_id": "",
                    "category_name": "local",
                    "check_flag": 63487,
                    "crop": {
                        "lower_left_x": 0.0,
                        "lower_left_y": 1.0,
                        "lower_right_x": 1.0,
                        "lower_right_y": 1.0,
                        "upper_left_x": 0.0,
                        "upper_left_y": 0.0,
                        "upper_right_x": 1.0,
                        "upper_right_y": 0.0
                    },
                    "crop_ratio": "free",
                    "crop_scale": 1.0,
                    "duration": int(duration * 1000000),
                    "extra_type_option": 0,
                    "formula_id": "",
                    "freeze": None,
                    "gameplay": None,
                    "has_audio": True,
                    "height": video_info.get("height", 720),
                    "id": video_id,
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
                    "matting": {"flag": 0, "has_use_quick_brush": False, "has_use_quick_eraser": False, "interactiveTime": [], "path": "", "strokes": []},
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
                    "type": "video",
                    "video_algorithm": {
                        "algorithms": [],
                        "deflicker": None,
                        "motion_blur_config": None,
                        "noise_reduction": None,
                        "path": "",
                        "quality_enhance": None,
                        "time_range": None
                    },
                    "width": video_info.get("width", 1280)
                }
            ],
            "vocal_beautifys": [],
            "vocal_separations": []
        },
        "mutable_config": None,
        "name": "",
        "new_version": "",
        "platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.8.0",
            "device_id": "",
            "hard_disk_id": "",
            "mac_address": "",
            "os": "windows",
            "os_version": "10.0.26200"
        },
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "tracks": [
            {
                "attribute": 0,
                "flag": 0,
                "id": track_id,
                "is_default_name": True,
                "name": "",
                "segments": [
                    {
                        "cartoon": False,
                        "clip": {
                            "alpha": 1.0,
                            "flip": {"horizontal": False, "vertical": False},
                            "rotation": 0.0,
                            "scale": {"x": 1.0, "y": 1.0},
                            "transform": {"x": 0.0, "y": 0.0}
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
                        "id": generate_draft_id(),
                        "intensifies_audio": None,
                        "is_placeholder": False,
                        "is_tone_modify": False,
                        "keyframe_refs": [],
                        "last_nonzero_db_value": -5.91,
                        "material_id": video_id,
                        "render_index": 0,
                        "responsive_layout": {"enable": False, "horizontal_pos_layout": 0, "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0},
                        "reverse": False,
                        "source_timerange": {"duration": int(duration * 1000000), "start": 0},
                        "speed": 1.0,
                        "target_timerange": {"duration": int(duration * 1000000), "start": 0},
                        "template_id": "",
                        "template_scene": "default",
                        "track_attribute": 0,
                        "track_render_index": 0,
                        "uniform_scale": {"on": True, "value": 1.0},
                        "visible": True,
                        "volume": 1.0
                    }
                ],
                "type": "video"
            }
        ],
        "update_time": 0,
        "version": 360000
    }

    # 添加字幕轨道
    if srt_path and Path(srt_path).exists():
        srt_segments = parse_srt_to_segments(srt_path)
        if srt_segments:
            subtitle_track = create_subtitle_track(srt_segments)
            content["tracks"].append(subtitle_track)

    # 添加BGM轨道
    if bgm_path and Path(bgm_path).exists():
        bgm_track = create_bgm_track(bgm_path, duration)
        content["tracks"].append(bgm_track)

    return content


def parse_srt_to_segments(srt_path):
    """解析SRT文件为片段列表"""
    segments = []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            # 解析时间
            time_line = lines[1]
            start_str, end_str = time_line.split(" --> ")
            start = srt_time_to_us(start_str.strip())
            end = srt_time_to_us(end_str.strip())
            text = "\n".join(lines[2:])

            segments.append({
                "start": start,
                "end": end,
                "text": text,
            })

    return segments


def srt_time_to_us(time_str):
    """SRT时间格式转微秒"""
    # 格式: HH:MM:SS,mmm
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    h = int(parts[0])
    m = int(parts[1])
    s = float(parts[2])
    total_seconds = h * 3600 + m * 60 + s
    return int(total_seconds * 1000000)


def create_subtitle_track(segments):
    """创建字幕轨道"""
    track_segments = []
    for seg in segments:
        seg_id = generate_draft_id()
        track_segments.append({
            "cartoon": False,
            "clip": {
                "alpha": 1.0,
                "flip": {"horizontal": False, "vertical": False},
                "rotation": 0.0,
                "scale": {"x": 1.0, "y": 1.0},
                "transform": {"x": 0.0, "y": 0.0}
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
            "id": seg_id,
            "intensifies_audio": None,
            "is_placeholder": False,
            "is_tone_modify": False,
            "keyframe_refs": [],
            "last_nonzero_db_value": -5.91,
            "material_id": seg_id,
            "render_index": 0,
            "responsive_layout": {"enable": False, "horizontal_pos_layout": 0, "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0},
            "reverse": False,
            "source_timerange": {"duration": seg["end"] - seg["start"], "start": 0},
            "speed": 1.0,
            "target_timerange": {"duration": seg["end"] - seg["start"], "start": seg["start"]},
            "template_id": "",
            "template_scene": "default",
            "track_attribute": 0,
            "track_render_index": 0,
            "uniform_scale": {"on": True, "value": 1.0},
            "visible": True,
            "volume": 1.0
        })

    return {
        "attribute": 0,
        "flag": 0,
        "id": generate_draft_id(),
        "is_default_name": True,
        "name": "字幕",
        "segments": track_segments,
        "type": "text"
    }


def create_bgm_track(bgm_path, duration):
    """创建BGM轨道"""
    bgm_id = generate_draft_id()

    return {
        "attribute": 0,
        "flag": 0,
        "id": generate_draft_id(),
        "is_default_name": True,
        "name": "BGM",
        "segments": [
            {
                "cartoon": False,
                "clip": {
                    "alpha": 1.0,
                    "flip": {"horizontal": False, "vertical": False},
                    "rotation": 0.0,
                    "scale": {"x": 1.0, "y": 1.0},
                    "transform": {"x": 0.0, "y": 0.0}
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
                "id": generate_draft_id(),
                "intensifies_audio": None,
                "is_placeholder": False,
                "is_tone_modify": False,
                "keyframe_refs": [],
                "last_nonzero_db_value": -5.91,
                "material_id": bgm_id,
                "render_index": 0,
                "responsive_layout": {"enable": False, "horizontal_pos_layout": 0, "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0},
                "reverse": False,
                "source_timerange": {"duration": int(duration * 1000000), "start": 0},
                "speed": 1.0,
                "target_timerange": {"duration": int(duration * 1000000), "start": 0},
                "template_id": "",
                "template_scene": "default",
                "track_attribute": 0,
                "track_render_index": 0,
                "uniform_scale": {"on": True, "value": 1.0},
                "visible": True,
                "volume": 1.0
            }
        ],
        "type": "audio"
    }


def get_video_info(video_path):
    """获取视频信息"""
    import subprocess
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=width,height,duration",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        info = json.loads(result.stdout)
        width = int(info["streams"][0].get("width", 1280))
        height = int(info["streams"][0].get("height", 720))
        duration = float(info["format"].get("duration", 0))
        return {"width": width, "height": height, "duration": duration}
    except:
        return {"width": 1280, "height": 720, "duration": 0}


def export_to_jianying(video_path, srt_path=None, bgm_path=None, draft_name=None):
    """导出视频到剪映草稿"""

    if not JIANYING_DRAFT_DIR.exists():
        print(f"❌ 剪映草稿目录不存在: {JIANYING_DRAFT_DIR}")
        return None

    # 获取视频信息
    video_info = get_video_info(video_path)
    duration = video_info["duration"]

    # 生成草稿名称
    if not draft_name:
        draft_name = f"VideoStudio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 创建草稿目录
    draft_dir = JIANYING_DRAFT_DIR / draft_name
    draft_dir.mkdir(parents=True, exist_ok=True)

    # 复制视频文件到草稿目录
    video_filename = Path(video_path).name
    video_dest = draft_dir / video_filename
    shutil.copy2(video_path, video_dest)

    # 复制字幕文件
    srt_dest = None
    if srt_path and Path(srt_path).exists():
        srt_dest = draft_dir / Path(srt_path).name
        shutil.copy2(srt_path, srt_dest)

    # 复制BGM文件
    bgm_dest = None
    if bgm_path and Path(bgm_path).exists():
        bgm_dest = draft_dir / Path(bgm_path).name
        shutil.copy2(bgm_path, bgm_dest)

    # 创建draft_content.json
    content = create_draft_content(
        video_path=video_dest,
        srt_path=srt_dest,
        bgm_path=bgm_dest,
        duration=duration,
    )

    content_path = draft_dir / "draft_content.json"
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    # 创建draft_meta_info.json
    meta_info = {
        "draft_fold_path": str(draft_dir),
        "draft_id": content["id"],
        "draft_name": draft_name,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": str(JIANYING_DRAFT_DIR),
        "draft_timeline_materials_size_": 0,
        "draft_type": "",
        "tm_draft_create": int(datetime.now().timestamp()),
        "tm_draft_modified": int(datetime.now().timestamp()),
        "tm_duration": int(duration * 1000000),
    }

    meta_path = draft_dir / "draft_meta_info.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=2)

    print(f"✅ 剪映草稿已创建: {draft_dir}")
    print(f"   名称: {draft_name}")
    print(f"   时长: {duration:.1f}秒")
    print(f"   视频: {video_filename}")
    if srt_dest:
        print(f"   字幕: {Path(srt_dest).name}")
    if bgm_dest:
        print(f"   BGM: {Path(bgm_dest).name}")

    return draft_dir


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导出视频到剪映草稿")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("--srt", help="SRT字幕文件路径")
    parser.add_argument("--bgm", help="BGM音频文件路径")
    parser.add_argument("--name", help="草稿名称")

    args = parser.parse_args()

    export_to_jianying(
        video_path=args.video,
        srt_path=args.srt,
        bgm_path=args.bgm,
        draft_name=args.name,
    )
