"""
PTZ 云台控制处理器
处理平台的 PTZ 控制命令
"""
import logging
from typing import Dict, Any
from xml_builder import XMLBuilder, parse_xml_message
from gb28181_protocol import parse_ptz_command

logger = logging.getLogger(__name__)


class PTZHandler:
    """PTZ 云台控制处理器"""
    
    def __init__(self, device_config: Dict[str, Any]):
        """
        初始化 PTZ 处理器
        
        Args:
            device_config: 设备配置
        """
        self.device_id = device_config.get("device_id")
        self.channels = device_config.get("channels", [])
        
        # 检查是否支持 PTZ
        self.ptz_enabled = any(
            channel.get("ptz_enabled", False) 
            for channel in self.channels
        )
        
        logger.info(f"PTZHandler initialized for device {self.device_id}, PTZ enabled: {self.ptz_enabled}")
    
    def handle_ptz_control(self, xml_message: str) -> str:
        """
        处理 PTZ 控制命令
        
        Args:
            xml_message: XML 控制消息
            
        Returns:
            str: XML 响应消息
        """
        try:
            parsed = parse_xml_message(xml_message)
            sn = parsed.get("SN", "1")
            device_id = parsed.get("DeviceID")
            ptz_cmd = parsed.get("PTZCmd", "")
            
            logger.info(f"Processing PTZ control for device {device_id} with SN={sn}")
            logger.debug(f"PTZ command: {ptz_cmd}")
            
            # 解析 PTZ 命令
            if ptz_cmd:
                parsed_ptz = parse_ptz_command(ptz_cmd)
                logger.info(f"PTZ command parsed: {parsed_ptz}")
                
                # 模拟 PTZ 响应（实际硬件会执行动作）
                if "error" not in parsed_ptz:
                    logger.info(f"PTZ actions: {parsed_ptz.get('actions', [])}")
                else:
                    logger.warning(f"PTZ parse error: {parsed_ptz.get('error')}")
            
            # 构建响应
            response = XMLBuilder.build_device_control_response(
                device_id=self.device_id,
                sn=sn,
                result="OK"
            )
            
            logger.debug(f"PTZ control response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error handling PTZ control: {e}", exc_info=True)
            return None
    
    def handle_preset(self, preset_id: int, action: str) -> bool:
        """
        处理预置位命令
        
        Args:
            preset_id: 预置位ID
            action: 操作类型 (set/goto/delete)
            
        Returns:
            bool: 是否成功
        """
        logger.info(f"PTZ preset {action} for preset {preset_id}")
        # 模拟预置位操作
        return True
    
    def handle_cruise(self, cruise_id: int, action: str) -> bool:
        """
        处理巡航命令
        
        Args:
            cruise_id: 巡航ID
            action: 操作类型 (start/stop)
            
        Returns:
            bool: 是否成功
        """
        logger.info(f"PTZ cruise {action} for cruise {cruise_id}")
        # 模拟巡航操作
        return True
