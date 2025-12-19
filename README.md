# GB28181 摄像头模拟器

基于 Docker 的 GB28181 摄像头模拟器，能够让接入平台识别为真实的摄像头设备。

## ✨ 功能特性

### 核心功能
- ✅ **SIP 信令处理**：支持 GB/T28181-2011、2016、2022 所有版本
- ✅ **设备注册**：完整的 Digest 认证支持
- ✅ **心跳保活**：自动发送心跳消息保持在线状态
- ✅ **设备目录**：响应 Catalog 查询，返回设备通道信息
- ✅ **实时视频流**：使用 FFmpeg 推送 H.264 编码视频（PS 封装 + RTP 传输）
- ✅ **PTZ 云台控制**：解析并响应云台控制命令
- ✅ **设备信息查询**：返回设备制造商、型号、固件版本等信息
- ✅ **设备状态查询**：返回设备在线状态
- ✅ **多设备模拟**：支持同时模拟多个虚拟摄像头

### 技术特点
- 🐍 Python 3.10+ 实现
- 🐳 Docker 容器化部署
- 📺 FFmpeg 媒体流推送
- 🔧 完全可配置（.env + YAML）
- 📝 详细日志输出

## 🚀 快速开始

### 前置要求

- Docker 和 Docker Compose
- GB28181 平台服务器（用于接入测试）

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/Ellean/gb28181-camera-simulator.git
cd gb28181-camera-simulator
```

2. **准备配置文件**
```bash
cp .env.example .env
```

3. **编辑配置文件**

编辑 `.env` 文件，配置 SIP 服务器信息：
```env
SIP_SERVER_IP=192.168.1.100        # SIP 服务器 IP
SIP_SERVER_PORT=5060               # SIP 服务器端口
SIP_SERVER_ID=34020000002000000001 # 平台/服务器 ID
SIP_DOMAIN=3402000000              # SIP 域
```

4. **准备测试视频**

将测试视频文件放置到 `media/` 目录：
```bash
# 将你的测试视频复制到 media 目录
cp /path/to/your/video.mp4 media/sample.mp4
```

或使用 FFmpeg 生成测试视频：
```bash
ffmpeg -f lavfi -i testsrc=duration=60:size=1280x720:rate=25 \
  -vcodec libx264 -pix_fmt yuv420p media/sample.mp4
```

5. **配置设备信息**

编辑 `config/devices.yaml` 配置虚拟摄像头设备：
```yaml
devices:
  - device_id: "34020000001320000001"
    name: "模拟摄像头-1"
    manufacturer: "SimCamera"
    model: "SC-2000"
    firmware: "V1.0.0"
    channels:
      - channel_id: "34020000001320000001"
        name: "主码流"
        ptz_enabled: true
    sip_user: "34020000001320000001"
    sip_password: "12345678"
```

6. **启动模拟器**
```bash
docker-compose up -d
```

7. **查看日志**
```bash
# 查看实时日志
docker-compose logs -f

# 查看日志文件
tail -f logs/simulator.log
```

## 📋 配置说明

### 环境变量配置 (.env)

| 变量 | 说明 | 示例 |
|------|------|------|
| `SIP_SERVER_IP` | SIP 服务器 IP 地址 | `192.168.1.100` |
| `SIP_SERVER_PORT` | SIP 服务器端口 | `5060` |
| `SIP_SERVER_ID` | 平台/服务器设备 ID | `34020000002000000001` |
| `SIP_DOMAIN` | SIP 域 | `3402000000` |
| `DEVICES_CONFIG` | 设备配置文件路径 | `config/devices.yaml` |
| `VIDEO_FILE` | 测试视频文件路径 | `media/sample.mp4` |
| `RTP_PORT_START` | RTP 端口范围起始 | `30000` |
| `RTP_PORT_END` | RTP 端口范围结束 | `30100` |
| `LOG_LEVEL` | 日志级别 | `INFO` / `DEBUG` |
| `LOG_DIR` | 日志目录 | `logs` |

### 设备配置 (config/devices.yaml)

```yaml
devices:
  - device_id: "34020000001320000001"      # 设备 ID（20位国标编码）
    name: "模拟摄像头-1"                    # 设备名称
    manufacturer: "SimCamera"              # 制造商
    model: "SC-2000"                       # 型号
    firmware: "V1.0.0"                     # 固件版本
    channels:                              # 通道列表
      - channel_id: "34020000001320000001" # 通道 ID
        name: "主码流"                      # 通道名称
        ptz_enabled: true                  # 是否支持 PTZ
    sip_user: "34020000001320000001"       # SIP 用户名
    sip_password: "12345678"               # SIP 密码
```

## 📖 使用示例

### 单设备模拟

最简配置 `config/devices.yaml`：
```yaml
devices:
  - device_id: "34020000001320000001"
    name: "测试摄像头"
    sip_user: "34020000001320000001"
    sip_password: "12345678"
    channels:
      - channel_id: "34020000001320000001"
        name: "主码流"
        ptz_enabled: true
```

### 多设备模拟

配置多个设备：
```yaml
devices:
  - device_id: "34020000001320000001"
    name: "摄像头-1"
    sip_user: "34020000001320000001"
    sip_password: "12345678"
    channels:
      - channel_id: "34020000001320000001"
        name: "主码流"
        ptz_enabled: true
  
  - device_id: "34020000001320000002"
    name: "摄像头-2"
    sip_user: "34020000001320000002"
    sip_password: "12345678"
    channels:
      - channel_id: "34020000001320000002"
        name: "主码流"
        ptz_enabled: true
```

### 本地开发运行

不使用 Docker 运行：
```bash
# 安装依赖
pip install -r requirements.txt

# 安装 FFmpeg
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# 设置环境变量
export PYTHONPATH=./src

# 运行模拟器
python src/main.py
```

## 🔧 常见问题

### 1. 设备无法注册到平台

**检查项：**
- SIP 服务器 IP 和端口是否正确
- 设备 ID 和密码是否与平台配置一致
- 网络连接是否正常
- 查看日志 `logs/simulator.log` 获取详细错误信息

### 2. 平台无法拉取视频流

**检查项：**
- 视频文件 `media/sample.mp4` 是否存在
- FFmpeg 是否正确安装
- RTP 端口范围（30000-30100）是否被占用
- 网络防火墙是否允许 UDP 流量

### 3. Docker 容器网络问题

**解决方案：**
```bash
# 使用 host 网络模式（推荐）
# docker-compose.yml 中已配置 network_mode: host

# 或者使用 bridge 模式并映射端口
# 需要修改 docker-compose.yml：
# ports:
#   - "5060:5060/udp"
#   - "30000-30100:30000-30100/udp"
```

### 4. 查看详细调试信息

修改 `.env` 文件：
```env
LOG_LEVEL=DEBUG
```

然后重启容器：
```bash
docker-compose restart
```

### 5. 清理和重启

```bash
# 停止并移除容器
docker-compose down

# 重新构建并启动
docker-compose up -d --build

# 清理日志
rm -rf logs/*.log
```

## 📊 支持的 GB28181 功能

| 功能 | 支持状态 | 说明 |
|------|---------|------|
| SIP REGISTER | ✅ | 设备注册 |
| Digest 认证 | ✅ | MD5 摘要认证 |
| Keepalive | ✅ | 心跳保活 |
| Catalog 查询 | ✅ | 设备目录查询 |
| DeviceInfo 查询 | ✅ | 设备信息查询 |
| DeviceStatus 查询 | ✅ | 设备状态查询 |
| 实时视频 INVITE | ✅ | 实时视频邀请 |
| RTP 视频推送 | ✅ | PS 封装 H.264 |
| PTZ 控制 | ✅ | 云台控制（模拟响应）|
| TCP 传输 | ✅ | 支持 TCP 模式 |
| UDP 传输 | ✅ | 支持 UDP 模式 |
| 录像查询 | ❌ | 不支持（NVR 功能）|
| 录像回放 | ❌ | 不支持（NVR 功能）|

## 🛠️ 技术架构

```
┌─────────────────────────────────────────────┐
│           GB28181 Platform                  │
│         (SIP Server + Media Client)         │
└────────────────┬────────────────────────────┘
                 │ SIP/UDP 5060
                 │ RTP/UDP 30000-30100
                 │
┌────────────────▼────────────────────────────┐
│       GB28181 Camera Simulator              │
│  ┌──────────────────────────────────────┐   │
│  │         SIP Client (main.py)         │   │
│  │  - Device Registration               │   │
│  │  - Keepalive Loop                    │   │
│  │  - Message Handler                   │   │
│  └──────────┬──────────────┬────────────┘   │
│             │              │                 │
│  ┌──────────▼──────┐  ┌───▼────────────┐    │
│  │ Catalog Handler │  │  PTZ Handler   │    │
│  │ - Device List   │  │  - Commands    │    │
│  │ - Device Info   │  │  - Control     │    │
│  └─────────────────┘  └────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │      Media Server (FFmpeg)           │   │
│  │  - Video Streaming                   │   │
│  │  - PS Encapsulation                  │   │
│  │  - RTP Transport                     │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## 📝 开发说明

### 项目结构

```
gb28181-camera-simulator/
├── Dockerfile                  # Docker 构建文件
├── docker-compose.yml          # Docker Compose 配置
├── .env.example               # 环境变量示例
├── .gitignore                 # Git 忽略文件
├── requirements.txt           # Python 依赖
├── README.md                  # 项目文档
├── config/
│   └── devices.yaml          # 设备配置文件
├── src/
│   ├── __init__.py
│   ├── main.py               # 程序入口
│   ├── sip_client.py         # SIP 信令处理
│   ├── media_server.py       # 媒体流推送
│   ├── ptz_handler.py        # PTZ 控制
│   ├── catalog_handler.py    # 目录查询
│   ├── xml_builder.py        # XML 消息构建
│   ├── gb28181_protocol.py   # 协议常量
│   └── utils.py              # 工具函数
├── media/
│   ├── .gitkeep
│   └── sample.mp4            # 测试视频（自行添加）
└── logs/                     # 日志目录
```

### 添加新功能

1. **扩展 XML 消息类型**：编辑 `src/xml_builder.py`
2. **添加新的命令处理**：扩展 `src/catalog_handler.py` 或 `src/ptz_handler.py`
3. **修改 SIP 行为**：编辑 `src/sip_client.py`

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关资源

- [GB/T 28181-2016 标准文档](http://www.gab.gov.cn/)
- [SIP Protocol RFC 3261](https://tools.ietf.org/html/rfc3261)
- [FFmpeg 官方文档](https://ffmpeg.org/documentation.html)

## 📧 联系方式

如有问题或建议，请通过 GitHub Issues 联系。

---

**⚠️ 注意**: 本项目仅用于测试和学习目的，请勿用于非法用途。
