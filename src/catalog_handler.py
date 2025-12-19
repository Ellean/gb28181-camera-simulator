"""
目录查询处理器
处理平台的 Catalog 查询请求
"""
import logging
from typing import Dict, Any, List
from xml_builder import XMLBuilder, parse_xml_message

logger = logging.getLogger(__name__)


class CatalogHandler:
    """目录查询处理器"""
    
    def __init__(self, device_config: Dict[str, Any]):
        """
        初始化目录处理器
        
        Args:
            device_config: 设备配置
        """
        self.device_id = device_config.get("device_id")
        self.device_name = device_config.get("name")
        self.manufacturer = device_config.get("manufacturer", "SimCamera")
        self.model = device_config.get("model", "SC-2000")
        self.firmware = device_config.get("firmware", "V1.0.0")
        self.channels = device_config.get("channels", [])
        
        logger.info(f"CatalogHandler initialized for device {self.device_id}")
    
    def handle_catalog_query(self, xml_message: str) -> str:
        """
        处理目录查询请求
        
        Args:
            xml_message: XML 查询消息
            
        Returns:
            str: XML 响应消息
        """
        try:
            parsed = parse_xml_message(xml_message)
            sn = parsed.get("SN", "1")
            
            logger.info(f"Processing Catalog query with SN={sn}")
            
            # 构建通道信息列表
            channel_list = []
            for channel in self.channels:
                channel_info = {
                    "channel_id": channel.get("channel_id"),
                    "name": channel.get("name", "Camera"),
                    "manufacturer": self.manufacturer,
                    "model": self.model,
                }
                channel_list.append(channel_info)
            
            # 构建响应
            response = XMLBuilder.build_catalog_response(
                device_id=self.device_id,
                sn=sn,
                channels=channel_list
            )
            
            logger.debug(f"Catalog response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error handling catalog query: {e}", exc_info=True)
            return None
    
    def handle_device_info_query(self, xml_message: str) -> str:
        """
        处理设备信息查询请求
        
        Args:
            xml_message: XML 查询消息
            
        Returns:
            str: XML 响应消息
        """
        try:
            parsed = parse_xml_message(xml_message)
            sn = parsed.get("SN", "1")
            
            logger.info(f"Processing DeviceInfo query with SN={sn}")
            
            device_info = {
                "name": self.device_name,
                "manufacturer": self.manufacturer,
                "model": self.model,
                "firmware": self.firmware,
                "channel_count": len(self.channels)
            }
            
            response = XMLBuilder.build_device_info_response(
                device_id=self.device_id,
                sn=sn,
                device_info=device_info
            )
            
            logger.debug(f"DeviceInfo response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error handling device info query: {e}", exc_info=True)
            return None
    
    def handle_device_status_query(self, xml_message: str) -> str:
        """
        处理设备状态查询请求
        
        Args:
            xml_message: XML 查询消息
            
        Returns:
            str: XML 响应消息
        """
        try:
            parsed = parse_xml_message(xml_message)
            sn = parsed.get("SN", "1")
            
            logger.info(f"Processing DeviceStatus query with SN={sn}")
            
            response = XMLBuilder.build_device_status_response(
                device_id=self.device_id,
                sn=sn,
                status="ON"
            )
            
            logger.debug(f"DeviceStatus response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error handling device status query: {e}", exc_info=True)
            return None
