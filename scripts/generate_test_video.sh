#!/bin/bash
# 生成测试视频文件的脚本
# 需要先安装 FFmpeg: sudo apt-get install ffmpeg

set -e

OUTPUT_DIR="media"
OUTPUT_FILE="${OUTPUT_DIR}/sample.mp4"

# 创建媒体目录
mkdir -p "${OUTPUT_DIR}"

echo "正在生成测试视频..."

# 生成60秒的测试视频
# 使用 testsrc 测试源，分辨率 1280x720，帧率 25fps
ffmpeg -f lavfi -i testsrc=duration=60:size=1280x720:rate=25 \
  -f lavfi -i sine=frequency=1000:duration=60 \
  -vcodec libx264 -pix_fmt yuv420p \
  -acodec aac -ar 44100 -ac 2 \
  -y "${OUTPUT_FILE}"

echo "测试视频已生成: ${OUTPUT_FILE}"

# 显示视频信息
ffprobe -v error -show_format -show_streams "${OUTPUT_FILE}"

echo ""
echo "✅ 测试视频生成完成!"
