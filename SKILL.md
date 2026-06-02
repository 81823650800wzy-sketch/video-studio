# Video Studio — 一站式视频制作

整合字幕处理和视频生产线的统一技能。支持快速字幕模式和完整视频制作流水线。

## 两种模式

### 1️⃣ 字幕模式 (caption)

输入原始视频 → Whisper 语音识别 → 生成 SRT 字幕 → 可选烧录 → 自动打开剪映

```bash
# 一键字幕处理
python ~/.claude/skills/video-studio/scripts/video_studio.py caption video.mp4

# 只生成 SRT (不烧录)
python ~/.claude/skills/video-studio/scripts/video_studio.py caption video.mp4 --srt-only

# 高精度模型
python ~/.claude/skills/video-studio/scripts/video_studio.py caption video.mp4 --model medium
```

### 2️⃣ 生产线模式 (pipeline)

输入素材 + 灵感文字 → 自动分析风格 → 学习对标博主 → 智能剪辑 → 字幕 → 成品

```bash
# 完整流程
python ~/.claude/skills/video-studio/scripts/video_studio.py pipeline \
  --project-name "AI入门第一课" \
  --images E:/素材/*.png \
  --videos E:/素材/*.mp4 \
  --inspiration "今天教大家用AI写周报..."

# 干跑模式 (仅规划不生成)
python ~/.claude/skills/video-studio/scripts/video_studio.py pipeline \
  --images E:/素材/*.png \
  --inspiration "AI工具对比" \
  --dry-run
```

## 核心能力

| 功能 | 字幕模式 | 生产线模式 |
|------|----------|------------|
| 🎙️ Whisper 语音转字幕 | ✅ | ✅ |
| 🗑️ 语气词检测标记 | ✅ | ✅ |
| 🔇 静音检测 | ✅ | ✅ |
| 📝 SRT 导出 | ✅ | ✅ |
| 📄 纯文本文稿 | ✅ | ✅ |
| 🎞️ 自动打开剪映 | ✅ | ✅ |
| 🔊 TTS 语音合成 | ✅ | ✅ |
| 🎬 素材采集分析 | - | ✅ |
| 🎯 风格自动识别 | - | ✅ |
| 📚 参考博主学习 | - | ✅ |
| 🎨 时间线规划 | - | ✅ |
| 🎵 BGM 智能匹配 | - | ✅ |
| ✂️ FFmpeg 剪辑合成 | - | ✅ |
| 🤖 AI 视频补全 | - | ✅ (可选) |

### 3️⃣ TTS 语音合成

生成中文旁白音频，支持多种语音和语速调节。

```bash
# 生成旁白
python ~/.claude/skills/video-studio/scripts/tts_engine.py "大家好，欢迎观看" -o narration.mp3

# 选择语音
python ~/.claude/skills/video-studio/scripts/tts_engine.py "测试内容" -v xiaoxiao

# 调节语速
python ~/.claude/skills/video-studio/scripts/tts_engine.py "快速旁白" -r "+20%"

# 可用语音: yunxi(男), yunjian(成熟男), xiaoxiao(女), xiaoyi(活泼女)
```

## 配置

编辑 `~/.claude/skills/video-studio/config.json`：

```json
{
  "caption": {
    "model": "small",
    "language": "zh",
    "output_dir": "E:/",
    "subtitle_style": { ... }
  },
  "pipeline": {
    "output_drive": "E:/",
    "default_style": "auto",
    "resolution": {"width": 1920, "height": 1080}
  }
}
```

## 依赖

- Python 3.10+
- FFmpeg
- openai-whisper (语音识别)
- yt-dlp + scenedetect + opencv-python + librosa (生产线模式)
- 剪映专业版 (可选)
