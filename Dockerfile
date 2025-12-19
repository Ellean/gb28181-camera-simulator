FROM python:3.10-slim

# 安装 FFmpeg 和其他依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY src/ ./src/
COPY config/ ./config/
COPY media/ ./media/

# 创建日志目录
RUN mkdir -p logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# 暴露 SIP 端口
EXPOSE 5060/udp

# 暴露 RTP 端口范围
EXPOSE 30000-30100/udp

# 运行模拟器
CMD ["python", "src/main.py"]
