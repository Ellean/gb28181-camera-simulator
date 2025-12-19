"""
GB28181 Protocol Constants and Utilities
支持 GB/T28181-2011、2016、2022 版本
"""

# SIP 方法
SIP_METHOD_REGISTER = "REGISTER"
SIP_METHOD_MESSAGE = "MESSAGE"
SIP_METHOD_INVITE = "INVITE"
SIP_METHOD_ACK = "ACK"
SIP_METHOD_BYE = "BYE"
SIP_METHOD_CANCEL = "CANCEL"

# GB28181 命令类型
CMD_CATALOG = "Catalog"
CMD_DEVICE_INFO = "DeviceInfo"
CMD_DEVICE_STATUS = "DeviceStatus"
CMD_DEVICE_CONTROL = "DeviceControl"
CMD_KEEPALIVE = "Keepalive"
CMD_RECORD_INFO = "RecordInfo"

# PTZ 命令字节位
PTZ_STOP = 0x00
PTZ_RIGHT = 0x01  # 右
PTZ_LEFT = 0x02   # 左
PTZ_DOWN = 0x04   # 下
PTZ_UP = 0x08     # 上
PTZ_ZOOM_IN = 0x10   # 焦距变大(倍率变大)
PTZ_ZOOM_OUT = 0x20  # 焦距变小(倍率变小)
PTZ_FOCUS_FAR = 0x40  # 焦点前调
PTZ_FOCUS_NEAR = 0x80 # 焦点后调

# PTZ 第二字节
PTZ_IRIS_OPEN = 0x01   # 光圈扩大
PTZ_IRIS_CLOSE = 0x02  # 光圈缩小

# XML 命名空间
XML_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'

# 设备状态
DEVICE_STATUS_ON = "ON"
DEVICE_STATUS_OFF = "OFF"

# 媒体传输协议
TRANSPORT_UDP = "UDP"
TRANSPORT_TCP_PASSIVE = "TCP/RTP/AVP"
TRANSPORT_TCP_ACTIVE = "TCP/RTP/AVP"

# SIP 响应码
SIP_OK = 200
SIP_TRYING = 100
SIP_RINGING = 180
SIP_UNAUTHORIZED = 401
SIP_NOT_FOUND = 404
SIP_REQUEST_TIMEOUT = 408
SIP_SERVER_ERROR = 500


def parse_ptz_command(ptz_data: str) -> dict:
    """
    解析 PTZ 控制命令
    格式: A50F01{command}{speed1}{speed2}{zoom}{checksum}
    
    Args:
        ptz_data: PTZ 控制数据 (hex string)
        
    Returns:
        dict: 解析后的控制命令
    """
    if not ptz_data or len(ptz_data) < 16:
        return {"error": "Invalid PTZ data"}
    
    try:
        # 移除可能的空格
        ptz_data = ptz_data.replace(" ", "").upper()
        
        # 验证前缀
        if not ptz_data.startswith("A50F01"):
            return {"error": "Invalid PTZ prefix"}
        
        # 解析命令字节
        cmd_byte = int(ptz_data[6:8], 16)
        speed1 = int(ptz_data[8:10], 16)  # 水平速度
        speed2 = int(ptz_data[10:12], 16)  # 垂直速度
        zoom = int(ptz_data[12:14], 16)    # 变倍速度
        
        result = {
            "raw": ptz_data,
            "command_byte": cmd_byte,
            "horizontal_speed": speed1,
            "vertical_speed": speed2,
            "zoom_speed": zoom,
            "actions": []
        }
        
        # 解析动作
        if cmd_byte & PTZ_RIGHT:
            result["actions"].append("right")
        if cmd_byte & PTZ_LEFT:
            result["actions"].append("left")
        if cmd_byte & PTZ_DOWN:
            result["actions"].append("down")
        if cmd_byte & PTZ_UP:
            result["actions"].append("up")
        if cmd_byte & PTZ_ZOOM_IN:
            result["actions"].append("zoom_in")
        if cmd_byte & PTZ_ZOOM_OUT:
            result["actions"].append("zoom_out")
        if cmd_byte & PTZ_FOCUS_FAR:
            result["actions"].append("focus_far")
        if cmd_byte & PTZ_FOCUS_NEAR:
            result["actions"].append("focus_near")
        
        if not result["actions"]:
            result["actions"].append("stop")
            
        return result
        
    except Exception as e:
        return {"error": f"Parse error: {str(e)}"}


def calculate_checksum(data: str) -> str:
    """
    计算 PTZ 命令校验和
    
    Args:
        data: 需要计算校验和的数据
        
    Returns:
        str: 两位十六进制校验和
    """
    checksum = 0
    for i in range(0, len(data), 2):
        checksum += int(data[i:i+2], 16)
    return format(checksum % 256, '02X')
