"""
工具函数模块
"""
import hashlib
import random
import string
from typing import Optional


def generate_call_id() -> str:
    """生成 SIP Call-ID"""
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    return random_str


def generate_tag() -> str:
    """生成 SIP Tag"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


def generate_branch() -> str:
    """生成 SIP Branch"""
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    return f"z9hG4bK{random_str}"


def calculate_digest_response(username: str, realm: str, password: str, 
                               method: str, uri: str, nonce: str) -> str:
    """
    计算 Digest 认证响应
    
    Args:
        username: 用户名
        realm: 认证域
        password: 密码
        method: SIP 方法 (如 REGISTER)
        uri: 请求 URI
        nonce: 服务器 nonce
        
    Returns:
        str: response 值
    """
    # HA1 = MD5(username:realm:password)
    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    
    # HA2 = MD5(method:uri)
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    
    # response = MD5(HA1:nonce:HA2)
    response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
    
    return response


def parse_sip_auth_header(auth_header: str) -> dict:
    """
    解析 SIP WWW-Authenticate 或 Authorization 头
    
    Args:
        auth_header: 认证头字符串
        
    Returns:
        dict: 解析后的认证参数
    """
    result = {}
    
    # 移除 "Digest " 前缀
    if auth_header.startswith("Digest "):
        auth_header = auth_header[7:]
    
    # 解析参数
    parts = auth_header.split(',')
    for part in parts:
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"')
            result[key] = value
    
    return result


def format_sip_uri(user: str, host: str, port: Optional[int] = None) -> str:
    """
    格式化 SIP URI
    
    Args:
        user: 用户名
        host: 主机地址
        port: 端口号 (可选)
        
    Returns:
        str: SIP URI
    """
    if port and port != 5060:
        return f"sip:{user}@{host}:{port}"
    return f"sip:{user}@{host}"


def get_local_ip() -> str:
    """
    获取本地 IP 地址
    
    Returns:
        str: 本地 IP
    """
    import socket
    try:
        # 创建一个 UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个外部地址（不需要真的连接）
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"
