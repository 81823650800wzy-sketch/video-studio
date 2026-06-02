#!/usr/bin/env python3
"""
TTS 语音合成引擎
================
使用 edge-tts 生成中文旁白音频
"""

import asyncio
import subprocess
from pathlib import Path


async def generate_speech(text, output_path, voice="zh-CN-YunxiNeural", rate="+0%"):
    """生成语音文件"""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))
    return output_path


def generate_narration(text, output_path, voice="zh-CN-YunxiNeural", rate="+0%"):
    """同步接口：生成语音"""
    return asyncio.run(generate_speech(text, output_path, voice, rate))


def get_audio_duration(audio_path):
    """获取音频时长"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0


# 可用的中文语音列表
VOICES = {
    "yunxi": {"name": "云希", "id": "zh-CN-YunxiNeural", "desc": "男声，年轻活泼"},
    "yunxia": {"name": "云夏", "id": "zh-CN-YunxiaNeural", "desc": "男声，少年"},
    "yunjian": {"name": "云健", "id": "zh-CN-YunjianNeural", "desc": "男声，成熟稳重"},
    "xiaoxiao": {"name": "晓晓", "id": "zh-CN-XiaoxiaoNeural", "desc": "女声，温柔甜美"},
    "xiaoyi": {"name": "晓艺", "id": "zh-CN-XiaoyiNeural", "desc": "女声，活泼可爱"},
}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TTS 语音合成")
    parser.add_argument("text", help="要合成的文字")
    parser.add_argument("-o", "--output", default="narration.mp3", help="输出文件")
    parser.add_argument("-v", "--voice", default="yunxi", choices=list(VOICES.keys()),
                        help="语音选择")
    parser.add_argument("-r", "--rate", default="+0%", help="语速 (如 +10%, -10%)")
    args = parser.parse_args()

    voice_id = VOICES[args.voice]["id"]
    path = generate_narration(args.text, args.output, voice_id, args.rate)
    dur = get_audio_duration(path)
    print(f"生成完成: {path} ({dur:.1f}s)")
