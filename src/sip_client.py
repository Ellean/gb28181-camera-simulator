"""
SIP 客户端实现
处理 SIP 信令：注册、心跳、消息、INVITE 等
"""
import socket
import threading
import time
import logging
import re
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from utils import (
    generate_call_id, generate_tag, generate_branch,
    calculate_digest_response, parse_sip_auth_header,
    format_sip_uri, get_local_ip
)
from xml_builder import XMLBuilder, parse_xml_message
from catalog_handler import CatalogHandler
from ptz_handler import PTZHandler
from media_server import MediaServer

logger = logging.getLogger(__name__)


class SIPClient:
    """SIP 客户端"""
    
    def __init__(self, device_config: Dict[str, Any], server_config: Dict[str, Any],
                 media_server: MediaServer):
        """
        初始化 SIP 客户端
        
        Args:
            device_config: 设备配置
            server_config: SIP 服务器配置
            media_server: 媒体服务器实例
        """
        self.device_id = device_config.get("device_id")
        self.sip_user = device_config.get("sip_user")
        self.sip_password = device_config.get("sip_password")
        self.device_config = device_config
        
        self.server_ip = server_config.get("server_ip")
        self.server_port = server_config.get("server_port", 5060)
        self.server_id = server_config.get("server_id")
        self.domain = server_config.get("domain")
        
        self.local_ip = get_local_ip()
        self.local_port = self._find_available_port(5060)
        
        self.media_server = media_server
        
        # 创建处理器
        self.catalog_handler = CatalogHandler(device_config)
        self.ptz_handler = PTZHandler(device_config)
        
        # SIP 会话状态
        self.cseq = 1
        self.registered = False
        self.call_id = generate_call_id()
        self.from_tag = generate_tag()
        self.auth_info = {}
        
        # 活动的 INVITE 会话
        self.active_calls = {}  # call_id -> session_info
        
        # UDP Socket
        self.sock = None
        self.running = False
        
        # 线程
        self.recv_thread = None
        self.keepalive_thread = None
        
        logger.info(f"SIPClient initialized for device {self.device_id}")
    
    def _find_available_port(self, preferred_port: int) -> int:
        """
        查找可用端口
        
        Args:
            preferred_port: 首选端口
            
        Returns:
            int: 可用端口
        """
        import socket
        
        # 尝试首选端口
        for port in range(preferred_port, preferred_port + 100):
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_sock.bind((self.local_ip, port))
                test_sock.close()
                return port
            except OSError:
                continue
        
        # 如果都不可用，使用0让系统分配
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.bind((self.local_ip, 0))
        port = test_sock.getsockname()[1]
        test_sock.close()
        return port
    
    def start(self) -> bool:
        """
        启动 SIP 客户端
        
        Returns:
            bool: 是否启动成功
        """
        try:
            # 创建 UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.local_ip, self.local_port))
            self.sock.settimeout(1.0)
            
            self.running = True
            
            # 启动接收线程
            self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.recv_thread.start()
            
            logger.info(f"SIP client started on {self.local_ip}:{self.local_port}")
            
            # 发送注册请求
            if self.register():
                logger.info("Registration successful")
                
                # 启动心跳线程
                self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
                self.keepalive_thread.start()
                
                return True
            else:
                logger.error("Registration failed")
                return False
                
        except Exception as e:
            logger.error(f"Error starting SIP client: {e}", exc_info=True)
            return False
    
    def stop(self):
        """停止 SIP 客户端"""
        logger.info("Stopping SIP client")
        self.running = False
        
        # 注销
        if self.registered:
            self.unregister()
        
        # 停止所有媒体流
        self.media_server.stop_all_streams()
        
        # 关闭 socket
        if self.sock:
            self.sock.close()
        
        logger.info("SIP client stopped")
    
    def register(self) -> bool:
        """
        发送 REGISTER 请求
        
        Returns:
            bool: 是否注册成功
        """
        try:
            # 第一次注册请求（无认证）
            request = self._build_register_request()
            self._send_request(request)
            
            # 等待响应
            time.sleep(1)
            
            # 如果需要认证，发送带认证的请求
            if self.auth_info:
                request = self._build_register_request(with_auth=True)
                self._send_request(request)
                time.sleep(1)
            
            return self.registered
            
        except Exception as e:
            logger.error(f"Error in register: {e}", exc_info=True)
            return False
    
    def unregister(self):
        """注销设备"""
        try:
            logger.info("Unregistering device")
            request = self._build_register_request(expires=0, with_auth=True)
            self._send_request(request)
            self.registered = False
        except Exception as e:
            logger.error(f"Error in unregister: {e}", exc_info=True)
    
    def _build_register_request(self, expires: int = 3600, with_auth: bool = False) -> str:
        """
        构建 REGISTER 请求
        
        Args:
            expires: 过期时间（秒）
            with_auth: 是否包含认证信息
            
        Returns:
            str: SIP 请求消息
        """
        self.cseq += 1
        branch = generate_branch()
        
        uri = format_sip_uri(self.sip_user, self.domain)
        server_uri = f"sip:{self.server_ip}:{self.server_port}"
        
        lines = [
            f"REGISTER {server_uri} SIP/2.0",
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};rport;branch={branch}",
            f"From: <{uri}>;tag={self.from_tag}",
            f"To: <{uri}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} REGISTER",
            f"Contact: <sip:{self.sip_user}@{self.local_ip}:{self.local_port}>",
            f"Max-Forwards: 70",
            f"Expires: {expires}",
            f"User-Agent: GB28181-Simulator/1.0",
        ]
        
        # 添加认证信息
        if with_auth and self.auth_info:
            auth_header = self._build_auth_header("REGISTER", server_uri)
            lines.append(f"Authorization: {auth_header}")
        
        lines.extend([
            f"Content-Length: 0",
            "",
            ""
        ])
        
        return "\r\n".join(lines)
    
    def _build_auth_header(self, method: str, uri: str) -> str:
        """
        构建认证头
        
        Args:
            method: SIP 方法
            uri: 请求 URI
            
        Returns:
            str: Authorization 头内容
        """
        response = calculate_digest_response(
            username=self.sip_user,
            realm=self.auth_info.get("realm", ""),
            password=self.sip_password,
            method=method,
            uri=uri,
            nonce=self.auth_info.get("nonce", "")
        )
        
        parts = [
            f'Digest username="{self.sip_user}"',
            f'realm="{self.auth_info.get("realm", "")}"',
            f'nonce="{self.auth_info.get("nonce", "")}"',
            f'uri="{uri}"',
            f'response="{response}"',
            f'algorithm=MD5',
        ]
        
        return ", ".join(parts)
    
    def _send_request(self, request: str):
        """
        发送 SIP 请求
        
        Args:
            request: SIP 请求消息
        """
        try:
            logger.debug(f"Sending request:\n{request}")
            self.sock.sendto(request.encode(), (self.server_ip, self.server_port))
        except Exception as e:
            logger.error(f"Error sending request: {e}", exc_info=True)
    
    def _send_response(self, response: str, addr: tuple):
        """
        发送 SIP 响应
        
        Args:
            response: SIP 响应消息
            addr: 目标地址
        """
        try:
            logger.debug(f"Sending response to {addr}:\n{response}")
            self.sock.sendto(response.encode(), addr)
        except Exception as e:
            logger.error(f"Error sending response: {e}", exc_info=True)
    
    def _receive_loop(self):
        """接收循环"""
        logger.info("Receive loop started")
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                message = data.decode('utf-8', errors='ignore')
                
                logger.debug(f"Received from {addr}:\n{message}")
                
                # 处理消息
                self._handle_message(message, addr)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error in receive loop: {e}", exc_info=True)
        
        logger.info("Receive loop stopped")
    
    def _handle_message(self, message: str, addr: tuple):
        """
        处理接收到的 SIP 消息
        
        Args:
            message: SIP 消息
            addr: 发送方地址
        """
        try:
            lines = message.split('\r\n')
            if not lines:
                return
            
            first_line = lines[0]
            
            # 解析消息类型
            if first_line.startswith('SIP/2.0'):
                # 这是响应
                self._handle_response(message, lines, addr)
            else:
                # 这是请求
                self._handle_request(message, lines, addr)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    def _handle_response(self, message: str, lines: list, addr: tuple):
        """
        处理 SIP 响应
        
        Args:
            message: 完整消息
            lines: 消息行列表
            addr: 发送方地址
        """
        try:
            status_line = lines[0]
            status_code = int(status_line.split()[1])
            
            logger.info(f"Received response: {status_code}")
            
            if status_code == 200:
                # OK 响应
                if 'REGISTER' in message:
                    self.registered = True
                    logger.info("Device registered successfully")
                    
            elif status_code == 401:
                # 需要认证
                logger.info("Authentication required")
                for line in lines:
                    if line.startswith('WWW-Authenticate:'):
                        auth_str = line[17:].strip()
                        self.auth_info = parse_sip_auth_header(auth_str)
                        logger.debug(f"Auth info: {self.auth_info}")
                        
        except Exception as e:
            logger.error(f"Error handling response: {e}", exc_info=True)
    
    def _handle_request(self, message: str, lines: list, addr: tuple):
        """
        处理 SIP 请求
        
        Args:
            message: 完整消息
            lines: 消息行列表
            addr: 发送方地址
        """
        try:
            request_line = lines[0]
            method = request_line.split()[0]
            
            logger.info(f"Received request: {method}")
            
            if method == "MESSAGE":
                self._handle_message_request(message, lines, addr)
            elif method == "INVITE":
                self._handle_invite_request(message, lines, addr)
            elif method == "ACK":
                self._handle_ack_request(message, lines, addr)
            elif method == "BYE":
                self._handle_bye_request(message, lines, addr)
            else:
                logger.warning(f"Unsupported method: {method}")
                
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
    
    def _handle_message_request(self, message: str, lines: list, addr: tuple):
        """处理 MESSAGE 请求"""
        try:
            # 提取头部字段
            headers = self._parse_headers(lines)
            
            # 提取消息体
            body_start = message.find('\r\n\r\n')
            if body_start != -1:
                body = message[body_start + 4:]
                
                # 解析 XML 消息
                parsed = parse_xml_message(body)
                cmd_type = parsed.get("CmdType", "")
                
                logger.info(f"Received MESSAGE with CmdType: {cmd_type}")
                
                # 发送 200 OK
                self._send_message_ok(headers, addr)
                
                # 处理不同类型的查询
                response_body = None
                if cmd_type == "Catalog":
                    response_body = self.catalog_handler.handle_catalog_query(body)
                elif cmd_type == "DeviceInfo":
                    response_body = self.catalog_handler.handle_device_info_query(body)
                elif cmd_type == "DeviceStatus":
                    response_body = self.catalog_handler.handle_device_status_query(body)
                elif cmd_type == "DeviceControl":
                    response_body = self.ptz_handler.handle_ptz_control(body)
                
                # 发送响应消息
                if response_body:
                    time.sleep(0.1)  # 短暂延迟
                    self._send_message_with_body(response_body, headers)
                    
        except Exception as e:
            logger.error(f"Error handling MESSAGE request: {e}", exc_info=True)
    
    def _handle_invite_request(self, message: str, lines: list, addr: tuple):
        """处理 INVITE 请求"""
        try:
            headers = self._parse_headers(lines)
            
            # 提取 SDP
            body_start = message.find('\r\n\r\n')
            if body_start != -1:
                sdp = message[body_start + 4:]
                
                # 解析 SDP 获取媒体信息
                media_info = self._parse_sdp(sdp)
                
                logger.info(f"Received INVITE with media info: {media_info}")
                
                # 发送 100 Trying
                self._send_trying(headers, addr)
                
                # 发送 200 OK with SDP
                time.sleep(0.1)
                call_id = headers.get("Call-ID", "")
                
                # 构建 SDP 响应
                response_sdp = self._build_sdp_response(media_info)
                self._send_invite_ok(headers, response_sdp, addr)
                
                # 保存会话信息
                self.active_calls[call_id] = {
                    "media_info": media_info,
                    "headers": headers,
                    "start_time": time.time()
                }
                
        except Exception as e:
            logger.error(f"Error handling INVITE request: {e}", exc_info=True)
    
    def _handle_ack_request(self, message: str, lines: list, addr: tuple):
        """处理 ACK 请求"""
        try:
            headers = self._parse_headers(lines)
            call_id = headers.get("Call-ID", "")
            
            logger.info(f"Received ACK for call {call_id}")
            
            # 启动媒体流推送
            if call_id in self.active_calls:
                session = self.active_calls[call_id]
                media_info = session["media_info"]
                
                # 启动 FFmpeg 推流
                target_ip = media_info.get("ip")
                target_port = media_info.get("port")
                
                if target_ip and target_port:
                    self.media_server.start_stream(
                        call_id=call_id,
                        target_ip=target_ip,
                        target_port=target_port,
                        transport=media_info.get("transport", "UDP")
                    )
                    
        except Exception as e:
            logger.error(f"Error handling ACK request: {e}", exc_info=True)
    
    def _handle_bye_request(self, message: str, lines: list, addr: tuple):
        """处理 BYE 请求"""
        try:
            headers = self._parse_headers(lines)
            call_id = headers.get("Call-ID", "")
            
            logger.info(f"Received BYE for call {call_id}")
            
            # 发送 200 OK
            self._send_bye_ok(headers, addr)
            
            # 停止媒体流
            self.media_server.stop_stream(call_id)
            
            # 移除会话
            if call_id in self.active_calls:
                del self.active_calls[call_id]
                
        except Exception as e:
            logger.error(f"Error handling BYE request: {e}", exc_info=True)
    
    def _parse_headers(self, lines: list) -> dict:
        """解析 SIP 头部"""
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        return headers
    
    def _parse_sdp(self, sdp: str) -> dict:
        """解析 SDP"""
        info = {}
        for line in sdp.split('\r\n'):
            if line.startswith('c='):
                # c=IN IP4 192.168.1.100
                parts = line.split()
                if len(parts) >= 3:
                    info["ip"] = parts[2]
            elif line.startswith('m='):
                # m=video 30000 RTP/AVP 96
                parts = line.split()
                if len(parts) >= 2:
                    info["port"] = int(parts[1])
                if len(parts) >= 3:
                    info["transport"] = "TCP" if "TCP" in parts[2] else "UDP"
        return info
    
    def _build_sdp_response(self, request_media: dict) -> str:
        """构建 SDP 响应"""
        sdp_lines = [
            "v=0",
            f"o={self.sip_user} 0 0 IN IP4 {self.local_ip}",
            "s=Play",
            f"c=IN IP4 {self.local_ip}",
            "t=0 0",
            f"m=video {request_media.get('port', 30000)} RTP/AVP 96 98 97",
            "a=rtpmap:96 PS/90000",
            "a=rtpmap:98 H264/90000",
            "a=rtpmap:97 MPEG4/90000",
            "a=recvonly",
            f"y={self.device_id.zfill(10)}",
        ]
        return "\r\n".join(sdp_lines) + "\r\n"
    
    def _send_message_ok(self, request_headers: dict, addr: tuple):
        """发送 MESSAGE 的 200 OK 响应"""
        response = self._build_ok_response("MESSAGE", request_headers)
        self._send_response(response, addr)
    
    def _send_trying(self, request_headers: dict, addr: tuple):
        """发送 100 Trying"""
        response = self._build_response(100, "Trying", request_headers)
        self._send_response(response, addr)
    
    def _send_invite_ok(self, request_headers: dict, sdp: str, addr: tuple):
        """发送 INVITE 的 200 OK 响应"""
        response = self._build_ok_response("INVITE", request_headers, body=sdp)
        self._send_response(response, addr)
    
    def _send_bye_ok(self, request_headers: dict, addr: tuple):
        """发送 BYE 的 200 OK 响应"""
        response = self._build_ok_response("BYE", request_headers)
        self._send_response(response, addr)
    
    def _build_ok_response(self, method: str, request_headers: dict, body: str = "") -> str:
        """构建 200 OK 响应"""
        return self._build_response(200, "OK", request_headers, method, body)
    
    def _build_response(self, code: int, reason: str, request_headers: dict, 
                       method: str = "", body: str = "") -> str:
        """构建 SIP 响应"""
        lines = [
            f"SIP/2.0 {code} {reason}",
            f"Via: {request_headers.get('Via', '')}",
            f"From: {request_headers.get('From', '')}",
            f"To: {request_headers.get('To', '')}",
            f"Call-ID: {request_headers.get('Call-ID', '')}",
            f"CSeq: {request_headers.get('CSeq', '')}",
        ]
        
        if body:
            lines.extend([
                f"Content-Type: application/sdp",
                f"Content-Length: {len(body)}",
                "",
                body
            ])
        else:
            lines.extend([
                f"Content-Length: 0",
                "",
                ""
            ])
        
        return "\r\n".join(lines)
    
    def _send_message_with_body(self, body: str, request_headers: dict):
        """发送带 XML 消息体的 MESSAGE 请求"""
        try:
            self.cseq += 1
            branch = generate_branch()
            
            from_uri = format_sip_uri(self.sip_user, self.domain)
            to_uri = format_sip_uri(self.server_id, self.domain)
            
            lines = [
                f"MESSAGE sip:{self.server_ip}:{self.server_port} SIP/2.0",
                f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};rport;branch={branch}",
                f"From: <{from_uri}>;tag={self.from_tag}",
                f"To: <{to_uri}>",
                f"Call-ID: {generate_call_id()}",
                f"CSeq: {self.cseq} MESSAGE",
                f"Content-Type: Application/MANSCDP+xml",
                f"Max-Forwards: 70",
                f"Content-Length: {len(body)}",
                "",
                body
            ]
            
            request = "\r\n".join(lines)
            self._send_request(request)
            
        except Exception as e:
            logger.error(f"Error sending MESSAGE: {e}", exc_info=True)
    
    def _keepalive_loop(self):
        """心跳循环"""
        logger.info("Keepalive loop started")
        
        while self.running and self.registered:
            try:
                # 发送心跳消息
                self._send_keepalive()
                
                # 每60秒发送一次心跳
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in keepalive loop: {e}", exc_info=True)
        
        logger.info("Keepalive loop stopped")
    
    def _send_keepalive(self):
        """发送心跳消息"""
        try:
            body = XMLBuilder.build_keepalive(self.device_id, status="OK")
            
            self.cseq += 1
            branch = generate_branch()
            
            from_uri = format_sip_uri(self.sip_user, self.domain)
            to_uri = format_sip_uri(self.server_id, self.domain)
            
            lines = [
                f"MESSAGE sip:{self.server_ip}:{self.server_port} SIP/2.0",
                f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};rport;branch={branch}",
                f"From: <{from_uri}>;tag={self.from_tag}",
                f"To: <{to_uri}>",
                f"Call-ID: {generate_call_id()}",
                f"CSeq: {self.cseq} MESSAGE",
                f"Content-Type: Application/MANSCDP+xml",
                f"Max-Forwards: 70",
                f"Content-Length: {len(body)}",
                "",
                body
            ]
            
            request = "\r\n".join(lines)
            self._send_request(request)
            
            logger.debug("Keepalive sent")
            
        except Exception as e:
            logger.error(f"Error sending keepalive: {e}", exc_info=True)
