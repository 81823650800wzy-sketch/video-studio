#!/usr/bin/env python3
"""
Video Studio — 一站式视频制作
==============================
整合字幕处理和视频生产线的统一入口

模式:
  caption  - 快速字幕处理 (原 auto-caption)
  pipeline - 完整视频生产线 (原 video-pipeline)
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

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    if args.mode == "caption":
        cmd_caption(args)
    elif args.mode == "pipeline":
        cmd_pipeline(args)


if __name__ == "__main__":
    main()
