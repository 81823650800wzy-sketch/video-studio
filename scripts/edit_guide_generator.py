#!/usr/bin/env python3
"""
剪辑指南生成器
==============
生成详细的剪辑指南，让用户按照指南在剪映中操作

核心理念:
- AI负责分析和决策
- 用户负责在剪映中执行
- 指南详细到每一步操作
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class EditStep:
    """剪辑步骤"""
    order: int
    action: str
    target: str
    details: str
    time_position: str = ""
    search_keyword: str = ""


@dataclass
class EditGuide:
    """剪辑指南"""
    project_name: str
    video_path: str
    total_duration: float
    subtitle_count: int
    cut_count: int
    overall_emotion: str
    steps: List[EditStep]
    bgm_keywords: List[str]
    sfx_keywords: List[str]
    effect_keywords: List[str]
    sticker_keywords: List[str]


class EditGuideGenerator:
    """剪辑指南生成器"""

    def __init__(self):
        self.emotion_keywords = {
            "calm": ["平静", "轻音乐", "钢琴", "ambient"],
            "excited": ["欢快", "活力", " upbeat", "energetic"],
            "intense": ["紧张", "悬疑", "suspense", "dramatic"],
            "sad": ["感动", "抒情", "emotional", "piano"],
            "epic": ["史诗", "震撼", "epic", "cinematic"],
        }

        self.sfx_keywords = {
            "transition": ["whoosh", "嗖", "转场"],
            "impact": ["impact", "砰", "冲击"],
            "ambient": ["ambient", "环境", "氛围"],
        }

        self.effect_keywords = {
            "slow_motion": ["慢动作", "slow motion"],
            "speed_ramp": ["速度", "speed ramp"],
            "shake": ["抖动", "shake"],
            "flash": ["闪白", "flash"],
        }

    def generate_guide(
        self,
        project_name: str,
        video_path: str,
        srt_path: str,
        decisions: Dict,
        output_path: str,
    ) -> str:
        """生成剪辑指南"""

        # 分析整体情感
        overall_emotion = self._analyze_overall_emotion(decisions)

        # 生成步骤
        steps = self._generate_steps(decisions)

        # 生成关键词
        bgm_keywords = self.emotion_keywords.get(overall_emotion, ["轻音乐"])
        sfx_keywords = self.sfx_keywords["transition"]
        effect_keywords = self.effect_keywords.get("slow_motion", ["慢动作"])

        # 创建指南对象
        guide = EditGuide(
            project_name=project_name,
            video_path=video_path,
            total_duration=decisions.get("total_duration", 0),
            subtitle_count=decisions.get("subtitle_count", 0),
            cut_count=decisions.get("cut_count", 0),
            overall_emotion=overall_emotion,
            steps=steps,
            bgm_keywords=bgm_keywords,
            sfx_keywords=sfx_keywords,
            effect_keywords=effect_keywords,
            sticker_keywords=[],
        )

        # 生成Markdown指南
        markdown = self._to_markdown(guide)

        # 保存指南
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)

        return output_path

    def _analyze_overall_emotion(self, decisions: Dict) -> str:
        """分析整体情感"""
        emotions = decisions.get("emotions", [])
        if not emotions:
            return "calm"

        # 统计情感分布
        emotion_count = {}
        for emotion in emotions:
            emotion_count[emotion] = emotion_count.get(emotion, 0) + 1

        # 返回最主要的情感
        return max(emotion_count, key=emotion_count.get)

    def _generate_steps(self, decisions: Dict) -> List[EditStep]:
        """生成剪辑步骤"""
        steps = []
        order = 1

        # 步骤1: 创建新项目
        steps.append(EditStep(
            order=order,
            action="创建新项目",
            target="剪映",
            details="打开剪映，点击「开始创作」，创建新项目",
        ))
        order += 1

        # 步骤2: 导入视频素材
        steps.append(EditStep(
            order=order,
            action="导入视频素材",
            target="媒体库",
            details=f"导入视频文件: {decisions.get('video_path', '视频文件')}",
        ))
        order += 1

        # 步骤3: 添加视频到时间轴
        steps.append(EditStep(
            order=order,
            action="添加视频到时间轴",
            target="时间轴",
            details="将视频拖拽到时间轴的视频轨道",
        ))
        order += 1

        # 步骤4: 剪切视频
        cuts = decisions.get("cuts", [])
        for i, cut in enumerate(cuts[:10]):  # 最多显示10个切口
            steps.append(EditStep(
                order=order,
                action=f"剪切视频 #{i+1}",
                target="时间轴",
                details=f"在 {cut.get('time', 0):.1f} 秒处剪切视频",
                time_position=f"{cut.get('time', 0):.1f}s",
            ))
            order += 1

        # 步骤5: 调整片段速度
        speed_changes = decisions.get("speed_changes", [])
        for change in speed_changes:
            steps.append(EditStep(
                order=order,
                action="调整片段速度",
                target="时间轴",
                details=f"选择片段，调整速度为 {change.get('speed', 1.0)}x",
                time_position=f"{change.get('start', 0):.1f}s",
            ))
            order += 1

        # 步骤6: 添加字幕
        steps.append(EditStep(
            order=order,
            action="添加字幕",
            target="字幕轨道",
            details="点击「字幕」，选择合适的字幕样式，添加字幕",
        ))
        order += 1

        # 步骤7: 添加BGM
        steps.append(EditStep(
            order=order,
            action="添加BGM",
            target="音频轨道",
            details="点击「音频」→「音乐」，搜索并添加合适的BGM",
            search_keyword="、".join(self.emotion_keywords.get("calm", [])),
        ))
        order += 1

        # 步骤8: 添加音效
        steps.append(EditStep(
            order=order,
            action="添加转场音效",
            target="音频轨道",
            details="在每个切口处添加转场音效",
            search_keyword="whoosh",
        ))
        order += 1

        # 步骤9: 添加转场
        steps.append(EditStep(
            order=order,
            action="添加转场效果",
            target="时间轴",
            details="在片段之间添加转场效果",
        ))
        order += 1

        # 步骤10: 调色
        steps.append(EditStep(
            order=order,
            action="调色",
            target="滤镜",
            details="点击「滤镜」，选择合适的滤镜进行调色",
        ))
        order += 1

        return steps

    def _to_markdown(self, guide: EditGuide) -> str:
        """转换为Markdown格式"""

        markdown = f"""# 🎬 剪辑指南

## 项目信息

| 项目 | 内容 |
|------|------|
| 项目名称 | {guide.project_name} |
| 视频时长 | {guide.total_duration:.1f} 秒 |
| 字幕数量 | {guide.subtitle_count} 条 |
| 剪辑切口 | {guide.cut_count} 个 |
| 整体情感 | {guide.overall_emotion} |

## 操作步骤

"""

        for step in guide.steps:
            markdown += f"### 步骤 {step.order}: {step.action}\n\n"
            markdown += f"**目标:** {step.target}\n\n"
            markdown += f"**操作:** {step.details}\n\n"

            if step.time_position:
                markdown += f"**时间位置:** {step.time_position}\n\n"

            if step.search_keyword:
                markdown += f"**搜索关键词:** {step.search_keyword}\n\n"

            markdown += "---\n\n"

        markdown += f"""## 素材搜索关键词

### BGM
搜索关键词: {', '.join(guide.bgm_keywords)}

### 音效
搜索关键词: {', '.join(guide.sfx_keywords)}

### 特效
搜索关键词: {', '.join(guide.effect_keywords)}

## 完成后的操作

1. 预览视频，确认效果
2. 调整不满意的地方
3. 导出视频

---

*本指南由 Video Studio AI 自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return markdown


def generate_edit_guide(
    project_name: str,
    video_path: str,
    srt_path: str,
    decisions: Dict,
    output_dir: str,
) -> str:
    """生成剪辑指南的便捷函数"""

    generator = EditGuideGenerator()
    output_path = Path(output_dir) / f"{project_name}_剪辑指南.md"

    return generator.generate_guide(
        project_name=project_name,
        video_path=video_path,
        srt_path=srt_path,
        decisions=decisions,
        output_path=str(output_path),
    )


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="生成剪辑指南")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--video", required=True, help="视频文件路径")
    parser.add_argument("--srt", help="SRT字幕文件路径")
    parser.add_argument("--decisions", help="剪辑决策JSON文件")
    parser.add_argument("--output", default="E:/", help="输出目录")

    args = parser.parse_args()

    # 加载决策文件
    decisions = {}
    if args.decisions and Path(args.decisions).exists():
        with open(args.decisions, 'r', encoding='utf-8') as f:
            decisions = json.load(f)

    # 生成指南
    output_path = generate_edit_guide(
        project_name=args.project,
        video_path=args.video,
        srt_path=args.srt or "",
        decisions=decisions,
        output_dir=args.output,
    )

    print(f"剪辑指南已生成: {output_path}")
