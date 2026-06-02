#!/usr/bin/env python3
"""
剪映草稿构建器
==============
生成完整的剪映草稿，包含:
- 视频轨道（有切口、有速度变化）
- 字幕轨道（每句话独立）
- BGM轨道（预留位置）
- 转场效果

关键点:
1. 时间单位是微秒 (1秒 = 1000000微秒)
2. 每个segment需要唯一的ID
3. material_id需要在materials中定义
"""

import json
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def generate_id():
    """生成32位ID"""
    return uuid.uuid4().hex


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


def parse_srt(srt_path: str) -> List[Dict]:
    """解析SRT字幕文件"""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    segments = []
    blocks = content.strip().split("\n\n")

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            time_line = lines[1]
            start_str, end_str = time_line.split(" --> ")
            start = srt_time_to_seconds(start_str.strip())
            end = srt_time_to_seconds(end_str.strip())
            text = "\n".join(lines[2:]).strip()
            segments.append({
                "text": text,
                "start": start,
                "end": end,
                "duration": end - start,
            })

    return segments


def srt_time_to_seconds(time_str: str) -> float:
    """SRT时间格式转秒"""
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def build_jianying_draft(
    project_name: str,
    video_path: str,
    srt_path: Optional[str] = None,
    bgm_path: Optional[str] = None,
    cuts: Optional[List[Dict]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    构建剪映草稿

    Args:
        project_name: 项目名称
        video_path: 视频文件路径
        srt_path: SRT字幕文件路径（可选）
        bgm_path: BGM音频文件路径（可选）
        cuts: 切口列表 [{"time": 秒, "speed": 1.0}, ...]（可选）
        output_dir: 输出目录（默认使用剪映草稿目录）

    Returns:
        草稿目录路径
    """
    # 剪映草稿目录
    if output_dir is None:
        jianying_draft_dir = Path(os.path.expanduser(
            "~/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft"
        ))
    else:
        jianying_draft_dir = Path(output_dir)

    # 获取视频信息
    video_info = get_video_info(video_path)
    duration_us = int(video_info["duration"] * 1_000_000)

    # 创建草稿目录
    draft_dir = jianying_draft_dir / project_name
    draft_dir.mkdir(parents=True, exist_ok=True)

    # 复制视频到草稿目录
    video_dest = draft_dir / Path(video_path).name
    if not video_dest.exists():
        shutil.copy2(video_path, video_dest)

    # 复制字幕到草稿目录
    srt_dest = None
    if srt_path and Path(srt_path).exists():
        srt_dest = draft_dir / Path(srt_path).name
        if not srt_dest.exists():
            shutil.copy2(srt_path, srt_dest)

    # 复制BGM到草稿目录
    bgm_dest = None
    if bgm_path and Path(bgm_path).exists():
        bgm_dest = draft_dir / Path(bgm_path).name
        if not bgm_dest.exists():
            shutil.copy2(bgm_path, bgm_dest)

    # ========== 构建轨道 ==========

    # 1. 视频轨道
    video_track = build_video_track(
        video_path=str(video_dest),
        duration_us=duration_us,
        video_info=video_info,
        cuts=cuts,
    )

    # 2. 字幕轨道
    text_track = None
    if srt_dest:
        text_track = build_text_track(srt_path=str(srt_dest))

    # 3. BGM轨道
    bgm_track = None
    if bgm_dest:
        bgm_track = build_bgm_track(
            bgm_path=str(bgm_dest),
            duration_us=duration_us,
        )

    # ========== 组装草稿 ==========

    tracks = [video_track]
    if text_track:
        tracks.append(text_track)
    if bgm_track:
        tracks.append(bgm_track)

    # 构建materials
    materials = build_materials(
        video_path=str(video_dest),
        video_info=video_info,
        srt_path=str(srt_dest) if srt_dest else None,
        bgm_path=str(bgm_dest) if bgm_dest else None,
    )

    # 构建draft_content
    draft_content = {
        "id": generate_id(),
        "version": 360000,
        "duration": duration_us,
        "canvas_config": {
            "width": video_info["width"],
            "height": video_info["height"],
            "ratio": "original",
        },
        "color_space": 0,
        "config": {},
        "cover": None,
        "create_time": 0,
        "extra_info": None,
        "fps": video_info["fps"],
        "free_render_index_mode_on": False,
        "group_container": None,
        "keyframe_graph_list": [],
        "last_modified_platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "10.7.0",
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
            "app_version": "10.7.0",
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

    # 保存draft_content.json
    content_path = draft_dir / "draft_content.json"
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(draft_content, f, ensure_ascii=False, indent=2)

    # 保存draft_meta_info.json
    meta_info = {
        "draft_fold_path": str(draft_dir),
        "draft_id": draft_content["id"],
        "draft_name": project_name,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": str(jianying_draft_dir),
        "draft_timeline_materials_size_": 0,
        "draft_type": "",
        "tm_draft_create": int(datetime.now().timestamp()),
        "tm_draft_modified": int(datetime.now().timestamp()),
        "tm_duration": duration_us,
    }

    meta_path = draft_dir / "draft_meta_info.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=2)

    # 输出统计
    print(f"✅ 剪映草稿已创建: {draft_dir}")
    print(f"   名称: {project_name}")
    print(f"   时长: {video_info['duration']:.1f}秒")
    print(f"   分辨率: {video_info['width']}x{video_info['height']}")
    print(f"   视频轨道: {len(video_track['segments'])} 个片段")
    if text_track:
        print(f"   字幕轨道: {len(text_track['segments'])} 条字幕")
    if bgm_track:
        print(f"   音频轨道: BGM")

    return str(draft_dir)


def build_video_track(
    video_path: str,
    duration_us: int,
    video_info: Dict,
    cuts: Optional[List[Dict]] = None,
) -> Dict:
    """构建视频轨道"""

    video_id = generate_id()
    segments = []

    if cuts and len(cuts) > 0:
        # 使用指定的切口
        for i, cut in enumerate(cuts):
            cut_time_us = int(cut["time"] * 1_000_000)
            speed = cut.get("speed", 1.0)

            # 计算片段时长
            if i < len(cuts) - 1:
                next_cut_us = int(cuts[i + 1]["time"] * 1_000_000)
                segment_duration_us = next_cut_us - cut_time_us
            else:
                segment_duration_us = duration_us - cut_time_us

            # 速度调整
            if speed != 1.0:
                source_duration_us = int(segment_duration_us / speed)
            else:
                source_duration_us = segment_duration_us

            segment = {
                "id": generate_id(),
                "material_id": video_id,
                "source_timerange": {
                    "start": cut_time_us,
                    "duration": source_duration_us,
                },
                "target_timerange": {
                    "start": cut_time_us,
                    "duration": segment_duration_us,
                },
                "speed": speed,
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
                "intensifies_audio": None,
                "is_placeholder": False,
                "is_tone_modify": False,
                "keyframe_refs": [],
                "last_nonzero_db_value": -5.91,
                "render_index": i,
                "responsive_layout": {
                    "enable": False,
                    "horizontal_pos_layout": 0,
                    "size_layout": 0,
                    "target_follow": "",
                    "vertical_pos_layout": 0,
                },
                "reverse": False,
                "template_id": "",
                "template_scene": "default",
                "track_attribute": 0,
                "track_render_index": 0,
                "uniform_scale": {"on": True, "value": 1.0},
                "visible": True,
                "volume": 1.0,
            }
            segments.append(segment)
    else:
        # 没有切口，整段视频
        segment = {
            "id": generate_id(),
            "material_id": video_id,
            "source_timerange": {
                "start": 0,
                "duration": duration_us,
            },
            "target_timerange": {
                "start": 0,
                "duration": duration_us,
            },
            "speed": 1.0,
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
            "intensifies_audio": None,
            "is_placeholder": False,
            "is_tone_modify": False,
            "keyframe_refs": [],
            "last_nonzero_db_value": -5.91,
            "render_index": 0,
            "responsive_layout": {
                "enable": False,
                "horizontal_pos_layout": 0,
                "size_layout": 0,
                "target_follow": "",
                "vertical_pos_layout": 0,
            },
            "reverse": False,
            "template_id": "",
            "template_scene": "default",
            "track_attribute": 0,
            "track_render_index": 0,
            "uniform_scale": {"on": True, "value": 1.0},
            "visible": True,
            "volume": 1.0,
        }
        segments.append(segment)

    return {
        "attribute": 0,
        "flag": 0,
        "id": generate_id(),
        "is_default_name": True,
        "name": "",
        "segments": segments,
        "type": "video",
    }


def build_text_track(srt_path: str) -> Dict:
    """构建字幕轨道"""

    srt_segments = parse_srt(srt_path)
    segments = []

    for i, srt_seg in enumerate(srt_segments):
        start_us = int(srt_seg["start"] * 1_000_000)
        duration_us = int(srt_seg["duration"] * 1_000_000)
        text_id = generate_id()

        segment = {
            "id": generate_id(),
            "material_id": text_id,
            "target_timerange": {
                "start": start_us,
                "duration": duration_us,
            },
            "source_timerange": {
                "start": 0,
                "duration": duration_us,
            },
            "speed": 1.0,
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
            "extra_material_refs": [text_id],
            "group_id": "",
            "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
            "intensifies_audio": None,
            "is_placeholder": False,
            "is_tone_modify": False,
            "keyframe_refs": [],
            "last_nonzero_db_value": -5.91,
            "render_index": i,
            "responsive_layout": {
                "enable": False,
                "horizontal_pos_layout": 0,
                "size_layout": 0,
                "target_follow": "",
                "vertical_pos_layout": 0,
            },
            "reverse": False,
            "template_id": "",
            "template_scene": "default",
            "track_attribute": 0,
            "track_render_index": 0,
            "uniform_scale": {"on": True, "value": 1.0},
            "visible": True,
            "volume": 1.0,
        }
        segments.append(segment)

    return {
        "attribute": 0,
        "flag": 0,
        "id": generate_id(),
        "is_default_name": True,
        "name": "字幕",
        "segments": segments,
        "type": "text",
    }


def build_bgm_track(bgm_path: str, duration_us: int) -> Dict:
    """构建BGM轨道"""

    bgm_id = generate_id()

    segment = {
        "id": generate_id(),
        "material_id": bgm_id,
        "source_timerange": {
            "start": 0,
            "duration": duration_us,
        },
        "target_timerange": {
            "start": 0,
            "duration": duration_us,
        },
        "speed": 1.0,
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
        "intensifies_audio": None,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_db_value": -5.91,
        "render_index": 0,
        "responsive_layout": {
            "enable": False,
            "horizontal_pos_layout": 0,
            "size_layout": 0,
            "target_follow": "",
            "vertical_pos_layout": 0,
        },
        "reverse": False,
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": 0.3,
    }

    return {
        "attribute": 0,
        "flag": 0,
        "id": generate_id(),
        "is_default_name": True,
        "name": "BGM",
        "segments": [segment],
        "type": "audio",
    }


def build_materials(
    video_path: str,
    video_info: Dict,
    srt_path: Optional[str] = None,
    bgm_path: Optional[str] = None,
) -> Dict:
    """构建materials"""

    video_id = generate_id()
    duration_us = int(video_info["duration"] * 1_000_000)

    materials = {
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
                    "upper_right_y": 0.0,
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
                    "flag": 0,
                    "has_use_quick_brush": False,
                    "has_use_quick_eraser": False,
                    "interactiveTime": [],
                    "path": "",
                    "strokes": [],
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
        ],
        "vocal_beautifys": [],
        "vocal_separations": [],
    }

    # 添加BGM素材
    if bgm_path:
        bgm_id = generate_id()
        materials["audios"].append({
            "id": bgm_id,
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
            "name": Path(bgm_path).stem,
            "path": str(bgm_path).replace("\\", "/"),
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
            "video_id": "",
            "wave_points": [],
        })

    return materials


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="构建剪映草稿")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--video", required=True, help="视频文件路径")
    parser.add_argument("--srt", help="SRT字幕文件路径")
    parser.add_argument("--bgm", help="BGM音频文件路径")
    parser.add_argument("--cuts", help="切口JSON文件")
    parser.add_argument("--output", help="输出目录")

    args = parser.parse_args()

    # 加载切口配置
    cuts = None
    if args.cuts and Path(args.cuts).exists():
        with open(args.cuts, "r", encoding="utf-8") as f:
            cuts = json.load(f)

    # 构建草稿
    draft_path = build_jianying_draft(
        project_name=args.project,
        video_path=args.video,
        srt_path=args.srt,
        bgm_path=args.bgm,
        cuts=cuts,
        output_dir=args.output,
    )

    print(f"\n草稿路径: {draft_path}")
