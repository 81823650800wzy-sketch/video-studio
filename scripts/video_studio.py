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


def cmd_jianying(args):
    """剪映模式 — 导出到剪映草稿"""
    from jianying_builder import build_jianying_draft
    import json

    # 加载切点配置
    cuts = None
    if args.cuts and Path(args.cuts).exists():
        with open(args.cuts, "r", encoding="utf-8") as f:
            cuts = json.load(f)

    result = build_jianying_draft(
        project_name=args.name or f"VS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        video_path=args.video,
        srt_path=args.srt,
        bgm_path=args.bgm,
        cuts=cuts,
    )
    return result


def cmd_edit(args):
    """AI全自动剪辑模式"""
    from ai_editor import AutoEditor

    editor = AutoEditor()
    result = editor.auto_edit(
        task=args.task,
        video_paths=args.videos,
        reference_url=args.reference,
        bgm_path=args.bgm,
        style_preset=args.style,
        target_duration=args.duration,
        output_dir=args.output,
        export_jianying=not args.no_jianying,
    )
    return result


def cmd_edit_pro(args):
    """百万剪辑狮风格剪辑 - 节奏随故事动"""
    from ai_editor_pro import AIEditorPro

    editor = AIEditorPro()
    result = editor.edit(
        video_path=args.video,
        bgm_path=args.bgm,
        output_dir=args.output,
        target_duration=args.duration,
        style=args.style,
        export_jianying=not args.no_jianying,
    )
    return result


def cmd_narrate(args):
    """叙事剪辑 - 以字幕为核心的电影解说剪辑"""
    from narrative_editor import NarrativeEditor

    editor = NarrativeEditor()
    result = editor.edit(
        srt_path=args.srt,
        video_path=args.video,
        bgm_path=args.bgm,
        output_dir=args.output,
        draft_name=args.name,
    )
    return result


def cmd_guide(args):
    """生成剪辑指南"""
    from edit_guide_generator import generate_edit_guide
    import json

    # 加载决策文件
    decisions = {}
    if args.decisions and Path(args.decisions).exists():
        with open(args.decisions, 'r', encoding='utf-8') as f:
            decisions = json.load(f)

    output_path = generate_edit_guide(
        project_name=args.project,
        video_path=args.video,
        srt_path=args.srt or "",
        decisions=decisions,
        output_dir=args.output,
    )

    print(f"剪辑指南已生成: {output_path}")
    return output_path


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

    # ===== jianying 子命令 =====
    jianying_parser = subparsers.add_parser(
        "jianying",
        help="导出到剪映草稿",
        description="将视频导出为剪映草稿格式",
    )
    jianying_parser.add_argument("video", help="视频文件路径")
    jianying_parser.add_argument("--srt", help="SRT字幕文件路径")
    jianying_parser.add_argument("--bgm", help="BGM音频文件路径")
    jianying_parser.add_argument("--name", help="草稿名称")
    jianying_parser.add_argument("--cuts", help="切口JSON文件")

    # ===== edit 子命令 (AI全自动剪辑) =====
    edit_parser = subparsers.add_parser(
        "edit",
        help="AI全自动剪辑",
        description="一句话描述需求，AI自动完成全部剪辑工作",
    )
    edit_parser.add_argument("task", help="剪辑任务描述（如'电影混剪'、'vlog日常'）")
    edit_parser.add_argument("--videos", nargs="*", default=[], help="本地视频路径")
    edit_parser.add_argument("--reference", help="参考视频URL")
    edit_parser.add_argument("--bgm", help="BGM音频路径")
    edit_parser.add_argument("--style", help="风格预设")
    edit_parser.add_argument("--duration", type=float, default=30, help="目标时长(秒)")
    edit_parser.add_argument("--output", default="E:/", help="输出目录")
    edit_parser.add_argument("--no-jianying", action="store_true", help="不导出剪映草稿")

    # ===== edit-pro 子命令 (百万剪辑狮风格) =====
    editpro_parser = subparsers.add_parser(
        "edit-pro",
        help="百万剪辑狮风格剪辑",
        description="节奏随故事动，围绕内容和旋律剪辑",
    )
    editpro_parser.add_argument("video", help="视频素材路径")
    editpro_parser.add_argument("bgm", help="BGM音频路径")
    editpro_parser.add_argument("--output", default="E:/", help="输出目录")
    editpro_parser.add_argument("--duration", type=float, default=30, help="目标时长(秒)")
    editpro_parser.add_argument("--style", default="auto",
                                choices=["auto", "cinematic", "vlog", "ghoul"],
                                help="风格 (默认: auto)")
    editpro_parser.add_argument("--no-jianying", action="store_true", help="不导出剪映草稿")

    # ===== narrate 子命令 (叙事剪辑 - 字幕驱动) =====
    narrate_parser = subparsers.add_parser(
        "narrate",
        help="叙事剪辑（字幕驱动）",
        description="以字幕为核心的电影解说剪辑，字幕决定节奏、切口、特效",
    )
    narrate_parser.add_argument("srt", help="SRT字幕文件（核心驱动）")
    narrate_parser.add_argument("video", help="视频素材路径")
    narrate_parser.add_argument("--bgm", help="BGM音频路径")
    narrate_parser.add_argument("--output", default="E:/", help="输出目录")
    narrate_parser.add_argument("--name", help="剪映草稿名称")

    # ===== guide 子命令 (剪辑指南) =====
    guide_parser = subparsers.add_parser(
        "guide",
        help="生成剪辑指南",
        description="生成详细的剪辑指南，让用户按照指南在剪映中操作",
    )
    guide_parser.add_argument("--project", required=True, help="项目名称")
    guide_parser.add_argument("--video", required=True, help="视频文件路径")
    guide_parser.add_argument("--srt", help="SRT字幕文件路径")
    guide_parser.add_argument("--decisions", help="剪辑决策JSON文件")
    guide_parser.add_argument("--output", default="E:/", help="输出目录")

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
    elif args.mode == "jianying":
        cmd_jianying(args)
    elif args.mode == "edit":
        cmd_edit(args)
    elif args.mode == "edit-pro":
        cmd_edit_pro(args)
    elif args.mode == "narrate":
        cmd_narrate(args)
    elif args.mode == "guide":
        cmd_guide(args)


if __name__ == "__main__":
    main()
