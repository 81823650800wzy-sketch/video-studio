# 剪映深度分析报告

## 1. 目录结构

```
C:\Users\{用户}\AppData\Local\JianyingPro\
├── User Data/
│   ├── Config/              # 配置文件
│   ├── Cache/               # 缓存（特效、音乐等）
│   │   ├── effect/          # 特效缓存 (270个)
│   │   ├── music/           # 音乐缓存 (120个)
│   │   ├── artistEffect/    # 艺术特效
│   │   └── AITextTemplate/  # AI字幕模板
│   ├── Projects/            # 项目
│   │   └── com.lveditor.draft/  # 草稿目录
│   ├── Resources/           # 资源
│   │   ├── Font/            # 字体
│   │   └── Lut/             # 滤镜
│   └── Presets/             # 预设
└── Apps/                    # 应用程序
```

## 2. 草稿格式

### 2.1 草稿文件结构

```
草稿名称/
├── draft_content.json      # 工程主文件（可能加密）
├── draft_meta_info.json    # 元信息
├── draft_settings          # 设置
├── [素材文件]              # 本地素材
└── template-2.tmp          # 模板文件
```

### 2.2 draft_content.json 结构

```json
{
  "id": "项目ID",
  "version": 360000,
  "duration": 时长(微秒),
  "canvas_config": {
    "width": 1920,
    "height": 1080,
    "ratio": "16:9"
  },
  "tracks": [...],           # 轨道数组
  "materials": {...},        # 素材引用
  "fps": 30.0,
  "platform": {...},
  "last_modified_platform": {...}
}
```

### 2.3 轨道类型

| 类型 | 说明 | segments内容 |
|------|------|-------------|
| video | 视频轨道 | 视频片段 |
| text | 字幕轨道 | 字幕片段 |
| audio | 音频轨道 | 音频片段 |
| effect | 特效轨道 | 特效片段 |
| sticker | 贴纸轨道 | 贴纸片段 |

### 2.4 视频 Segment 结构

```json
{
  "id": "segment_id",
  "material_id": "video_material_id",
  "source_timerange": {
    "start": 0,           # 源视频开始时间(微秒)
    "duration": 4000000   # 持续时间(微秒)
  },
  "target_timerange": {
    "start": 0,           # 目标时间轴开始时间(微秒)
    "duration": 4000000   # 持续时间(微秒)
  },
  "speed": 1.0,           # 播放速度
  "clip": {
    "scale": {"x": 1.0, "y": 1.0},
    "transform": {"x": 0.0, "y": 0.0},
    "rotation": 0.0,
    "flip": {"horizontal": false, "vertical": false}
  },
  "transitions": {        # 转场
    "in": {"id": "transition_id", "duration": 500},
    "out": {"id": "transition_id", "duration": 500}
  },
  "effects": ["effect_id"]  # 特效
}
```

### 2.5 字幕 Segment 结构

```json
{
  "id": "segment_id",
  "material_id": "text_material_id",
  "target_timerange": {
    "start": 0,
    "duration": 2640000
  },
  "content": "字幕内容",
  "style": {
    "font": "字体",
    "size": 8,
    "color": "#FFFFFF",
    "background": {"enabled": true, "color": "#000000", "alpha": 0.7}
  },
  "animation": {
    "in": {"type": "typewriter", "duration": 500},
    "out": {"type": "fade", "duration": 300}
  },
  "position": {"x": 0.5, "y": 0.85}
}
```

## 3. 素材引用机制

### 3.1 本地素材

- 直接复制到草稿目录
- 通过文件路径引用

### 3.2 内置素材

- 通过素材ID引用
- 剪映自动从云端下载
- 缓存在 Cache 目录

### 3.3 已发现的素材ID

**字幕模板ID** (来自 ai_lyrics_template.ini):
```
7411168473918754084, 7580995030433778990, 7591420714515844395, ...
```

**特效ID** (来自 Cache/effect/):
```
115534218, 115534219, 115534220, ... (270个)
```

## 4. 关键发现

1. **草稿可能被加密** - 剪映会加密 draft_content.json
2. **素材通过ID引用** - 内置素材使用数字ID
3. **时间单位是微秒** - 所有时间都以微秒为单位
4. **支持多种轨道** - 视频、字幕、音频、特效、贴纸

## 5. 实现策略

### 5.1 方案A: 生成明文JSON

- 生成标准格式的 draft_content.json
- 剪映可能需要重新加密才能读取

### 5.2 方案B: 使用剪映的导入功能

- 生成剪映可识别的格式
- 通过剪映的导入功能加载

### 5.3 方案C: 直接操作剪映

- 使用 UI 自动化工具
- 模拟用户操作

## 6. 下一步

1. 测试明文JSON是否能被剪映读取
2. 研究剪映的加密机制
3. 实现基本的草稿生成
