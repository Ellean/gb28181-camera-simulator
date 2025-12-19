"""
GB28181 摄像头模拟器主程序
支持多设备模拟
"""
import os
import sys
import logging
import signal
import time
import yaml
from typing import List
from dotenv import load_dotenv

from sip_client import SIPClient
from media_server import MediaServer
from web_interface import WebInterface

# 配置日志
def setup_logging(log_level: str, log_dir: str):
    """配置日志系统"""
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'simulator.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )


class GB28181Simulator:
    """GB28181 摄像头模拟器"""
    
    def __init__(self):
        """初始化模拟器"""
        self.clients: List[SIPClient] = []
        self.media_server: MediaServer = None
        self.web_interface: WebInterface = None
        self.running = False
        
        # 加载配置
        load_dotenv()
        
        # 日志配置
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_dir = os.getenv('LOG_DIR', 'logs')
        setup_logging(log_level, log_dir)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("GB28181 Camera Simulator Starting...")
        
        # Web 界面配置
        self.web_port = int(os.getenv('WEB_PORT', 8000))
        self.web_host = os.getenv('WEB_HOST', '0.0.0.0')
        self.enable_web = os.getenv('ENABLE_WEB', 'true').lower() in ['true', '1', 'yes']
        
        # SIP 服务器配置
        self.server_config = {
            'server_ip': os.getenv('SIP_SERVER_IP'),
            'server_port': int(os.getenv('SIP_SERVER_PORT', 5060)),
            'server_id': os.getenv('SIP_SERVER_ID'),
            'domain': os.getenv('SIP_DOMAIN')
        }
        
        # 媒体配置
        self.video_file = os.getenv('VIDEO_FILE', 'media/sample.mp4')
        
        # 设备配置
        self.devices_config_path = os.getenv('DEVICES_CONFIG', 'config/devices.yaml')
        
        # 验证配置
        self._validate_config()
        
        # 加载设备配置
        self.devices = self._load_devices_config()
        
        self.logger.info(f"Loaded {len(self.devices)} device(s) from config")
    
    def _validate_config(self):
        """验证必要的配置"""
        required_env = ['SIP_SERVER_IP', 'SIP_SERVER_ID', 'SIP_DOMAIN']
        missing = [env for env in required_env if not os.getenv(env)]
        
        if missing:
            self.logger.error(f"Missing required environment variables: {', '.join(missing)}")
            self.logger.error("Please check your .env file")
            sys.exit(1)
        
        # 检查设备配置文件
        if not os.path.exists(self.devices_config_path):
            self.logger.error(f"Devices config file not found: {self.devices_config_path}")
            sys.exit(1)
    
    def _load_devices_config(self) -> list:
        """加载设备配置"""
        try:
            with open(self.devices_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('devices', [])
        except Exception as e:
            self.logger.error(f"Error loading devices config: {e}", exc_info=True)
            sys.exit(1)
    
    def start(self):
        """启动模拟器"""
        try:
            self.running = True
            
            # 创建媒体服务器（共享）
            self.media_server = MediaServer(self.video_file)
            
            # 为每个设备创建 SIP 客户端
            for device in self.devices:
                try:
                    self.logger.info(f"Starting device: {device.get('device_id')}")
                    
                    client = SIPClient(
                        device_config=device,
                        server_config=self.server_config,
                        media_server=self.media_server
                    )
                    
                    if client.start():
                        self.clients.append(client)
                        self.logger.info(f"Device {device.get('device_id')} started successfully")
                    else:
                        self.logger.error(f"Failed to start device {device.get('device_id')}")
                        
                except Exception as e:
                    self.logger.error(f"Error starting device {device.get('device_id')}: {e}", exc_info=True)
            
            if not self.clients:
                self.logger.error("No devices started successfully")
                sys.exit(1)
            
            self.logger.info(f"Simulator started with {len(self.clients)} active device(s)")
            
            # 启动 Web 界面
            if self.enable_web:
                try:
                    self.web_interface = WebInterface(self, port=self.web_port, host=self.web_host)
                    self.web_interface.start()
                    self.logger.info(f"Web interface available at http://{self.web_host}:{self.web_port}")
                except Exception as e:
                    self.logger.error(f"Error starting web interface: {e}", exc_info=True)
                    self.logger.warning("Continuing without web interface")
            
            # 保持运行
            self._run()
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error in simulator: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """停止模拟器"""
        self.logger.info("Stopping simulator...")
        self.running = False
        
        # 停止所有客户端
        for client in self.clients:
            try:
                client.stop()
            except Exception as e:
                self.logger.error(f"Error stopping client: {e}", exc_info=True)
        
        # 停止所有媒体流
        if self.media_server:
            self.media_server.stop_all_streams()
        
        self.logger.info("Simulator stopped")
    
    def _run(self):
        """主运行循环"""
        self.logger.info("Simulator running... Press Ctrl+C to stop")
        
        try:
            while self.running:
                time.sleep(1)
                
                # 检查客户端状态
                active_clients = sum(1 for client in self.clients if client.registered)
                if active_clients == 0 and len(self.clients) > 0:
                    self.logger.warning("No active registered clients")
                    
        except KeyboardInterrupt:
            pass


def signal_handler(signum, frame):
    """信号处理器"""
    print("\nReceived signal, shutting down...")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动模拟器
    simulator = GB28181Simulator()
    simulator.start()


if __name__ == "__main__":
    main()
