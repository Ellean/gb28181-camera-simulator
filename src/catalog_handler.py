"""
目录查询处理器
处理平台的 Catalog 查询请求
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from xml_builder import XMLBuilder, parse_xml_message
from gb28181_protocol import (
    get_device_type_code, extract_device_type_from_id,
    VIDEO_DEVICE_TYPES, RECORDING_DEVICE_TYPES, ALARM_DEVICE_TYPES,
    AUDIO_DEVICE_TYPES, DISPLAY_DEVICE_TYPES
)

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
        self.device_type = device_config.get("device_type", "IPC")  # 默认为网络摄像机
        
        logger.info(f"CatalogHandler initialized for device {self.device_id}, type: {self.device_type}")
    
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
            
            # 根据设备类型设置设备能力
            device_info = {
                "name": self.device_name,
                "manufacturer": self.manufacturer,
                "model": self.model,
                "firmware": self.firmware,
                "channel_count": len(self.channels)
            }
            
            # 设备类型特定属性
            if self.device_type in VIDEO_DEVICE_TYPES:
                if self.device_type not in ["显示器"]:
                    device_info["ptz_support"] = any(ch.get("ptz_enabled", False) for ch in self.channels)
            
            if self.device_type in RECORDING_DEVICE_TYPES:
                device_info["recording_support"] = True
            
            if self.device_type in ALARM_DEVICE_TYPES:
                if self.device_type == "报警输出设备":
                    device_info["alarm_output_support"] = True
                else:
                    device_info["alarm_support"] = True
            
            if self.device_type in AUDIO_DEVICE_TYPES:
                device_info["audio_support"] = True
            
            if self.device_type in DISPLAY_DEVICE_TYPES:
                device_info["display_support"] = True
            
            if self.device_type == "移动传输设备":
                device_info["mobile_support"] = True
            
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
    
    def handle_record_info_query(self, xml_message: str) -> str:
        """
        处理录像信息查询请求（NVR/DVR 功能）
        
        Args:
            xml_message: XML 查询消息
            
        Returns:
            str: XML 响应消息
        """
        try:
            parsed = parse_xml_message(xml_message)
            sn = parsed.get("SN", "1")
            start_time = parsed.get("StartTime", "")
            end_time = parsed.get("EndTime", "")
            
            logger.info(f"Processing RecordInfo query with SN={sn}, StartTime={start_time}, EndTime={end_time}")
            
            # 检查设备类型，只有 NVR/DVR 支持录像查询
            if self.device_type not in RECORDING_DEVICE_TYPES:
                logger.warning(f"Device type {self.device_type} does not support RecordInfo query")
                # 返回空录像列表
                response = XMLBuilder.build_record_info_response(
                    device_id=self.device_id,
                    sn=sn,
                    records=[]
                )
            else:
                # 为 NVR/DVR 生成模拟录像文件列表
                # 在实际应用中，这里应该查询真实的录像文件
                records = self._generate_mock_records(start_time, end_time)
                response = XMLBuilder.build_record_info_response(
                    device_id=self.device_id,
                    sn=sn,
                    records=records
                )
            
            logger.debug(f"RecordInfo response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error handling record info query: {e}", exc_info=True)
            return None
    
    def _generate_mock_records(self, start_time: str, end_time: str) -> list:
        """
        生成模拟录像文件记录（用于测试）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            list: 录像文件列表
        """
        # 解析时间
        try:
            if start_time and end_time:
                start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
                end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")
            else:
                # 如果没有指定时间，返回最近24小时的模拟录像
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(hours=24)
        except (ValueError, TypeError) as e:
            # 时间解析失败，返回空列表
            logger.warning(f"Failed to parse time range: {e}")
            return []
        
        # 生成模拟录像文件（每小时一个文件）
        records = []
        current = start_dt
        file_num = 1
        
        while current < end_dt and file_num <= 10:  # 最多返回10个文件
            record_end = min(current + timedelta(hours=1), end_dt)
            
            # 为每个通道生成录像
            for channel in self.channels:
                record = {
                    "device_id": channel.get("channel_id"),
                    "name": f"{channel.get('name', 'Channel')}_Record_{file_num}",
                    "file_path": f"/record/{current.strftime('%Y%m%d')}/{channel.get('channel_id')}/{file_num}.mp4",
                    "start_time": current.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end_time": record_end.strftime("%Y-%m-%dT%H:%M:%S"),
                    "secrecy": "0",
                    "type": "time",  # time: 定时录像, alarm: 报警录像, manual: 手动录像
                    "file_size": "102400"  # 100MB（模拟）
                }
                records.append(record)
            
            current = record_end
            file_num += 1
        
        logger.info(f"Generated {len(records)} mock record files for device {self.device_id}")
        return records
    
    def send_alarm_notification(self, alarm_type: str = "Motion", alarm_priority: int = 3) -> str:
        """
        发送报警通知（用于报警类设备）
        
        Args:
            alarm_type: 报警类型 (Motion, IO, Temperature, etc.)
            alarm_priority: 报警优先级 (1-4, 1=highest)
            
        Returns:
            str: 报警通知 XML
        """
        if self.device_type not in ALARM_DEVICE_TYPES:
            logger.warning(f"Device type {self.device_type} does not support alarm notifications")
            return None
        
        # 构建报警通知 XML
        alarm_info = {
            "alarm_type": alarm_type,
            "alarm_priority": alarm_priority,
            "alarm_method": "1",  # 1=报警, 2=故障
            "alarm_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "alarm_description": f"{alarm_type} alarm triggered"
        }
        
        response = XMLBuilder.build_alarm_notification(
            device_id=self.device_id,
            alarm_info=alarm_info
        )
        
        logger.info(f"Alarm notification generated for device {self.device_id}")
        return response
    
    def get_device_capabilities(self) -> dict:
        """
        获取设备能力集（根据设备类型）
        
        Returns:
            dict: 设备能力描述
        """
        capabilities = {
            "device_type": self.device_type,
            "basic": ["Catalog", "DeviceInfo", "DeviceStatus", "Keepalive"]
        }
        
        # 根据设备类型添加能力
        if self.device_type in VIDEO_DEVICE_TYPES:
            capabilities["video"] = ["RealPlay", "RTP", "PS"]
            if any(ch.get("ptz_enabled", False) for ch in self.channels):
                capabilities["ptz"] = ["PTZControl"]
        
        if self.device_type in RECORDING_DEVICE_TYPES:
            capabilities["recording"] = ["RecordInfo", "Playback"]
        
        if self.device_type in ALARM_DEVICE_TYPES:
            capabilities["alarm"] = ["AlarmNotify", "AlarmQuery"]
        
        if self.device_type in AUDIO_DEVICE_TYPES:
            capabilities["audio"] = ["AudioBroadcast", "AudioTalk"]
        
        if self.device_type in DISPLAY_DEVICE_TYPES:
            capabilities["display"] = ["VideoDisplay"]
        
        return capabilities
