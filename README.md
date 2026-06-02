# Video Studio

一站式视频制作 skill，整合字幕处理和完整视频生产线。

## 两种模式

### 1️⃣ 字幕模式 (caption)

输入原始视频 → Whisper 语音识别 → 生成 SRT 字幕 → 可选烧录 → 自动打开剪映

```bash
python scripts/video_studio.py caption video.mp4
python scripts/video_studio.py caption video.mp4 --srt-only
python scripts/video_studio.py caption video.mp4 --model medium
```

### 2️⃣ 生产线模式 (pipeline)

输入素材 + 灵感文字 → 自动分析风格 → 学习对标博主 → 智能剪辑 → 字幕 → 成品

```bash
python scripts/video_studio.py pipeline \
  --project-name "AI入门第一课" \
  --images E:/素材/*.png \
  --videos E:/素材/*.mp4 \
  --inspiration "今天教大家用AI写周报..."

# 干跑模式 (仅规划不生成)
python scripts/video_studio.py pipeline \
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
| 🎬 素材采集分析 | - | ✅ |
| 🎯 风格自动识别 | - | ✅ |
| 📚 参考博主学习 | - | ✅ |
| 🎨 时间线规划 | - | ✅ |
| 🎵 BGM 智能匹配 | - | ✅ |
| ✂️ FFmpeg 剪辑合成 | - | ✅ |
| 🤖 AI 视频补全 | - | ✅ (可选) |

## 依赖

- Python 3.10+
- FFmpeg
- openai-whisper (语音识别)
- yt-dlp + scenedetect + opencv-python + librosa (生产线模式)
- 剪映专业版 (可选)

## 配置

编辑 `config.json` 自定义行为。

## License

MIT
