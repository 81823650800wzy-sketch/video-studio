#!/usr/bin/env python3
"""
生产线引擎 — 完整视频制作流程
==============================
源自 video-pipeline skill，整合到 Video Studio
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 确保能找到同目录下的模块
_SCRIPT_DIR = Path(__file__).parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from pipeline_utils import section, step, ok, warn, fail, ensure_dir, sanitize_filename


def load_config():
    """加载配置"""
    config_file = Path.home() / ".claude" / "skills" / "video-studio" / "config.json"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def resolve_paths(config):
    """解析路径中的 ~"""
    pipeline = config.get("pipeline", {})
    if "project_base_dir" in pipeline:
        pipeline["project_base_dir"] = str(Path(pipeline["project_base_dir"]).expanduser())
    if "temp_dir" in pipeline:
        pipeline["temp_dir"] = str(Path(pipeline["temp_dir"]).expanduser())
    return config


def merge_with_cli(config, cli_args):
    """合并 CLI 参数到配置"""
    if cli_args.get("output"):
        config.setdefault("pipeline", {})["output_drive"] = cli_args["output"]
    return config


def validate_config(config):
    """验证配置"""
    warnings = []
    pipeline = config.get("pipeline", {})
    if not pipeline.get("output_drive"):
        warnings.append("未设置输出目录，将使用默认值 E:/")
    return warnings


def stage1_collect_inputs(images, videos, inspiration, inspiration_file, config):
    """Stage 1: 多模态素材采集"""
    from input_collector import collect_inputs as ci
    project_dir = ensure_dir(
        Path(config["pipeline"]["output_drive"]) / config.get("_project_name", "project"))
    return ci(
        images=images, videos=videos,
        inspiration=inspiration, inspiration_file=inspiration_file,
        project_dir=project_dir,
    )


def stage2_analyze_content(manifest, config):
    """Stage 2: 内容分析 + 风格分类"""
    from content_analyzer import analyze_content
    return analyze_content(manifest, config.get("_explicit_style", "auto"))


def stage3_learn_reference(reference_urls, content_style_key, project_dir, config):
    """Stage 3: 参考博主风格学习"""
    from reference_learner import learn_from_references
    return learn_from_references(reference_urls, content_style_key, project_dir, config)


def stage4_plan_timeline(manifest, content, reference, project_dir, config):
    """Stage 4: 时间线规划 + 缺口检测"""
    from timeline_planner import build_timeline
    return build_timeline(manifest, content, reference, project_dir, config)


def stage5_generate_ai_video(timeline, config):
    """Stage 5: AI视频补全缺口"""
    gaps = timeline.get("gaps", [])
    if not gaps:
        step("无缺口，跳过AI视频生成")
        return timeline
    ai_cfg = config.get("ai_video", {})
    if not ai_cfg.get("enabled"):
        step("AI视频未启用，缺口将用文字卡片填充")
        return timeline
    return timeline


def stage6_select_bgm(style_profile, timeline, project_dir, config):
    """Stage 6: BGM匹配"""
    from bgm_manager import select_bgm
    return select_bgm(style_profile, timeline["target_duration"], project_dir, config)


def stage7_assemble(timeline, bgm, project_dir, config):
    """Stage 7: FFmpeg剪辑合成"""
    from editing_engine import assemble_timeline
    return assemble_timeline(timeline, bgm, project_dir, config)


def stage8_add_caption(video_path, config):
    """Stage 8: 字幕 + 剪映 (调用 caption_engine)"""
    section("Stage 8: 字幕生成")
    from caption_engine import process_video

    cap_cfg = config.get("caption", {})
    jianying_cfg = config.get("jianying", {})

    step("调用字幕引擎...")
    result = process_video(
        video_path=video_path,
        model=cap_cfg.get("model", "small"),
        language=cap_cfg.get("language", "zh"),
        burn=True,
        output_dir=video_path.parent,
        open_jianying=jianying_cfg.get("auto_open", True)
    )
    captioned = result.get("captioned") or result.get("srt")
    ok("字幕完成: {}".format(captioned))
    return Path(captioned) if captioned else video_path


def run_pipeline(
    project_name=None,
    images=None,
    videos=None,
    inspiration=None,
    inspiration_file=None,
    reference=None,
    style="auto",
    output=None,
    dry_run=False,
    no_open=False,
):
    """运行完整的视频生产线"""

    # 加载配置
    config = load_config()
    config = resolve_paths(config)
    config = merge_with_cli(config, {"output": output})
    warnings = validate_config(config)
    for w in warnings:
        warn(w)

    # 项目名
    if not project_name:
        if inspiration:
            project_name = sanitize_filename(inspiration[:30])
        else:
            project_name = datetime.now().strftime("%Y%m%d_%H%M%S")

    project_dir = ensure_dir(
        Path(config.get("pipeline", {}).get("output_drive", "E:/")) / project_name)

    config["_project_name"] = project_name
    config["_explicit_style"] = style

    print(f"\n{'='*60}")
    print(f"  Video Studio — 视频生产线")
    print(f"{'='*60}")
    print(f"  项目: {project_name}")
    print(f"  输出: {project_dir}")
    print(f"  风格: {style}")
    print(f"  干跑: {'是' if dry_run else '否'}")
    print(f"{'='*60}")

    if dry_run:
        step("干跑模式 - 仅规划不生成")

    # ===== 流水线执行 =====
    manifest = stage1_collect_inputs(
        images or [], videos or [], inspiration, inspiration_file, config)
    content = stage2_analyze_content(manifest, config)
    reference_result = stage3_learn_reference(
        reference or [], content.get("style_key", "bilibili_ai_tutorial"),
        str(project_dir), config)
    style_profile = reference_result if reference_result else content.get("style_profile")
    timeline = stage4_plan_timeline(manifest, content, style_profile, str(project_dir), config)
    timeline = stage5_generate_ai_video(timeline, config)
    bgm = stage6_select_bgm(style_profile, timeline, str(project_dir), config)

    if not dry_run:
        assembly = stage7_assemble(timeline, bgm, project_dir, config)
        final = stage8_add_caption(assembly, config)

        print(f"\n{'='*60}")
        print(f"  生产完成!")
        print(f"{'='*60}")
        print(f"  成品: {final}")
        print(f"  项目: {project_dir}")
        print(f"{'='*60}\n")

        # 保存项目报告
        report = {
            "project_name": project_name,
            "timestamp": datetime.now().isoformat(),
            "style": content.get("style_profile", {}).get("name", ""),
            "output": str(final) if final else "",
            "config": config,
        }
        report_path = project_dir / "project_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        ok("项目报告: {}".format(report_path))
    else:
        print(f"\n{'='*60}")
        print(f"  干跑完成 - 未生成视频")
        print(f"{'='*60}\n")

        tl_path = project_dir / "timeline_plan.json"
        with open(tl_path, "w", encoding="utf-8") as f:
            json.dump({"manifest": manifest, "content": content,
                        "timeline": timeline}, f, ensure_ascii=False, indent=2)
        ok("规划结果: {}".format(tl_path))
