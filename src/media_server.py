"""
媒体流推送服务
使用 FFmpeg 推送 PS 封装的 RTP 视频流
"""
import logging
import subprocess
import threading
import time
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MediaServer:
    """媒体流推送服务器"""
    
    def __init__(self, video_file: str):
        """
        初始化媒体服务器
        
        Args:
            video_file: 视频文件路径
        """
        self.video_file = video_file
        self.active_streams = {}  # call_id -> process
        self.stream_lock = threading.Lock()
        
        logger.info(f"MediaServer initialized with video file: {video_file}")
    
    def start_stream(self, call_id: str, target_ip: str, target_port: int, 
                     transport: str = "UDP", ssrc: Optional[str] = None) -> bool:
        """
        启动视频流推送
        
        Args:
            call_id: 会话标识
            target_ip: 目标IP地址
            target_port: 目标端口
            transport: 传输协议 (UDP/TCP)
            ssrc: SSRC 标识
            
        Returns:
            bool: 是否启动成功
        """
        try:
            # 检查视频文件是否存在
            if not os.path.exists(self.video_file):
                logger.error(f"Video file not found: {self.video_file}")
                return False
            
            with self.stream_lock:
                # 检查是否已有流在推送
                if call_id in self.active_streams:
                    logger.warning(f"Stream already exists for call_id: {call_id}")
                    return False
                
                # 构建 FFmpeg 命令
                # 使用 PS 封装格式通过 RTP 推送
                cmd = [
                    "ffmpeg",
                    "-re",  # 实时推流
                    "-stream_loop", "-1",  # 循环播放
                    "-i", self.video_file,  # 输入文件
                    "-vcodec", "libx264",  # H.264 编码
                    "-preset", "ultrafast",  # 编码速度
                    "-tune", "zerolatency",  # 零延迟调优
                    "-an",  # 禁用音频
                    "-f", "rtp_mpegts",  # PS 封装通过 RTP
                ]
                
                # 添加 SSRC 如果提供
                if ssrc:
                    cmd.extend(["-ssrc", ssrc])
                
                # 目标地址
                if transport.upper() == "TCP":
                    cmd.append(f"rtp://{target_ip}:{target_port}?rtcpport={target_port}")
                else:
                    cmd.append(f"rtp://{target_ip}:{target_port}")
                
                logger.info(f"Starting stream to {target_ip}:{target_port} (transport: {transport})")
                logger.debug(f"FFmpeg command: {' '.join(cmd)}")
                
                # 启动 FFmpeg 进程
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE
                )
                
                # 保存进程引用
                self.active_streams[call_id] = {
                    "process": process,
                    "target_ip": target_ip,
                    "target_port": target_port,
                    "start_time": time.time()
                }
                
                # 启动监控线程
                monitor_thread = threading.Thread(
                    target=self._monitor_stream,
                    args=(call_id,),
                    daemon=True
                )
                monitor_thread.start()
                
                logger.info(f"Stream started successfully for call_id: {call_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error starting stream: {e}", exc_info=True)
            return False
    
    def stop_stream(self, call_id: str) -> bool:
        """
        停止视频流推送
        
        Args:
            call_id: 会话标识
            
        Returns:
            bool: 是否停止成功
        """
        try:
            with self.stream_lock:
                if call_id not in self.active_streams:
                    logger.warning(f"No active stream found for call_id: {call_id}")
                    return False
                
                stream_info = self.active_streams[call_id]
                process = stream_info["process"]
                
                # 终止 FFmpeg 进程
                logger.info(f"Stopping stream for call_id: {call_id}")
                
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"FFmpeg process did not terminate, killing it")
                    process.kill()
                    process.wait()
                
                # 移除流信息
                del self.active_streams[call_id]
                
                logger.info(f"Stream stopped successfully for call_id: {call_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error stopping stream: {e}", exc_info=True)
            return False
    
    def _monitor_stream(self, call_id: str):
        """
        监控流状态
        
        Args:
            call_id: 会话标识
        """
        while True:
            time.sleep(5)
            
            with self.stream_lock:
                if call_id not in self.active_streams:
                    break
                
                stream_info = self.active_streams[call_id]
                process = stream_info["process"]
                
                # 检查进程状态
                if process.poll() is not None:
                    logger.warning(f"Stream process exited for call_id: {call_id}")
                    # 读取错误输出
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    if stderr:
                        logger.error(f"FFmpeg error output: {stderr}")
                    del self.active_streams[call_id]
                    break
    
    def get_active_streams(self) -> Dict[str, Any]:
        """
        获取当前活动的流信息
        
        Returns:
            dict: 活动流信息
        """
        with self.stream_lock:
            return {
                call_id: {
                    "target_ip": info["target_ip"],
                    "target_port": info["target_port"],
                    "start_time": info["start_time"],
                    "duration": time.time() - info["start_time"]
                }
                for call_id, info in self.active_streams.items()
            }
    
    def stop_all_streams(self):
        """停止所有流"""
        logger.info("Stopping all streams")
        with self.stream_lock:
            call_ids = list(self.active_streams.keys())
        
        for call_id in call_ids:
            self.stop_stream(call_id)
