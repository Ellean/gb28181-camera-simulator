"""
GB28181 XML 消息构建器
用于构建各种 GB28181 协议要求的 XML 消息
"""
from datetime import datetime
from typing import List, Dict, Any
import xml.etree.ElementTree as ET


class XMLBuilder:
    """GB28181 XML 消息构建器"""
    
    @staticmethod
    def build_keepalive(device_id: str, status: str = "OK") -> str:
        """
        构建心跳消息
        
        Args:
            device_id: 设备ID
            status: 设备状态 (OK/ERROR)
            
        Returns:
            str: XML 字符串
        """
        root = ET.Element("Notify")
        
        ET.SubElement(root, "CmdType").text = "Keepalive"
        ET.SubElement(root, "SN").text = str(int(datetime.now().timestamp() * 1000))
        ET.SubElement(root, "DeviceID").text = device_id
        ET.SubElement(root, "Status").text = status
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    
    @staticmethod
    def build_catalog_response(device_id: str, sn: str, channels: List[Dict[str, Any]]) -> str:
        """
        构建目录查询响应
        
        Args:
            device_id: 设备ID
            sn: 命令序列号
            channels: 通道列表
            
        Returns:
            str: XML 字符串
        """
        root = ET.Element("Response")
        
        ET.SubElement(root, "CmdType").text = "Catalog"
        ET.SubElement(root, "SN").text = sn
        ET.SubElement(root, "DeviceID").text = device_id
        ET.SubElement(root, "SumNum").text = str(len(channels))
        
        device_list = ET.SubElement(root, "DeviceList")
        device_list.set("Num", str(len(channels)))
        
        for channel in channels:
            item = ET.SubElement(device_list, "Item")
            ET.SubElement(item, "DeviceID").text = channel.get("channel_id", "")
            ET.SubElement(item, "Name").text = channel.get("name", "Camera")
            ET.SubElement(item, "Manufacturer").text = channel.get("manufacturer", "SimCamera")
            ET.SubElement(item, "Model").text = channel.get("model", "SC-2000")
            ET.SubElement(item, "Owner").text = "Owner"
            ET.SubElement(item, "CivilCode").text = device_id[:9]
            ET.SubElement(item, "Address").text = "Address"
            ET.SubElement(item, "Parental").text = "0"
            ET.SubElement(item, "ParentID").text = device_id
            ET.SubElement(item, "SafetyWay").text = "0"
            ET.SubElement(item, "RegisterWay").text = "1"
            ET.SubElement(item, "Secrecy").text = "0"
            ET.SubElement(item, "Status").text = "ON"
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    
    @staticmethod
    def build_device_info_response(device_id: str, sn: str, device_info: Dict[str, Any]) -> str:
        """
        构建设备信息查询响应
        
        Args:
            device_id: 设备ID
            sn: 命令序列号
            device_info: 设备信息字典
            
        Returns:
            str: XML 字符串
        """
        root = ET.Element("Response")
        
        ET.SubElement(root, "CmdType").text = "DeviceInfo"
        ET.SubElement(root, "SN").text = sn
        ET.SubElement(root, "DeviceID").text = device_id
        ET.SubElement(root, "DeviceName").text = device_info.get("name", "SimCamera")
        ET.SubElement(root, "Manufacturer").text = device_info.get("manufacturer", "SimCamera")
        ET.SubElement(root, "Model").text = device_info.get("model", "SC-2000")
        ET.SubElement(root, "Firmware").text = device_info.get("firmware", "V1.0.0")
        ET.SubElement(root, "Channel").text = str(device_info.get("channel_count", 1))
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    
    @staticmethod
    def build_device_status_response(device_id: str, sn: str, status: str = "ON") -> str:
        """
        构建设备状态查询响应
        
        Args:
            device_id: 设备ID
            sn: 命令序列号
            status: 设备状态 (ON/OFF)
            
        Returns:
            str: XML 字符串
        """
        root = ET.Element("Response")
        
        ET.SubElement(root, "CmdType").text = "DeviceStatus"
        ET.SubElement(root, "SN").text = sn
        ET.SubElement(root, "DeviceID").text = device_id
        ET.SubElement(root, "Result").text = "OK"
        ET.SubElement(root, "Online").text = "ONLINE" if status == "ON" else "OFFLINE"
        ET.SubElement(root, "Status").text = status
        ET.SubElement(root, "Encode").text = "ON"
        ET.SubElement(root, "Record").text = "OFF"
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    
    @staticmethod
    def build_device_control_response(device_id: str, sn: str, result: str = "OK") -> str:
        """
        构建设备控制响应 (如 PTZ 控制)
        
        Args:
            device_id: 设备ID
            sn: 命令序列号
            result: 控制结果 (OK/ERROR)
            
        Returns:
            str: XML 字符串
        """
        root = ET.Element("Response")
        
        ET.SubElement(root, "CmdType").text = "DeviceControl"
        ET.SubElement(root, "SN").text = sn
        ET.SubElement(root, "DeviceID").text = device_id
        ET.SubElement(root, "Result").text = result
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    
    @staticmethod
    def build_record_info_response(device_id: str, sn: str, records: List[Dict[str, Any]]) -> str:
        """
        构建录像文件查询响应 (NVR/DVR 功能)
        
        Args:
            device_id: 设备ID
            sn: 命令序列号
            records: 录像文件列表
            
        Returns:
            str: XML 字符串
        """
        root = ET.Element("Response")
        
        ET.SubElement(root, "CmdType").text = "RecordInfo"
        ET.SubElement(root, "SN").text = sn
        ET.SubElement(root, "DeviceID").text = device_id
        ET.SubElement(root, "Name").text = "RecordInfo"
        ET.SubElement(root, "SumNum").text = str(len(records))
        
        if records:
            record_list = ET.SubElement(root, "RecordList")
            record_list.set("Num", str(len(records)))
            
            for record in records:
                item = ET.SubElement(record_list, "Item")
                ET.SubElement(item, "DeviceID").text = record.get("device_id", device_id)
                ET.SubElement(item, "Name").text = record.get("name", "Record")
                ET.SubElement(item, "FilePath").text = record.get("file_path", "")
                ET.SubElement(item, "Address").text = "Address"
                ET.SubElement(item, "StartTime").text = record.get("start_time", "")
                ET.SubElement(item, "EndTime").text = record.get("end_time", "")
                ET.SubElement(item, "Secrecy").text = record.get("secrecy", "0")
                ET.SubElement(item, "Type").text = record.get("type", "time")
                ET.SubElement(item, "RecorderID").text = device_id
                if "file_size" in record:
                    ET.SubElement(item, "FileSize").text = record.get("file_size")
        
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def parse_xml_message(xml_str: str) -> Dict[str, Any]:
    """
    解析 GB28181 XML 消息
    
    Args:
        xml_str: XML 字符串
        
    Returns:
        dict: 解析后的消息内容
    """
    try:
        # 移除 XML 声明
        if xml_str.startswith('<?xml'):
            xml_str = xml_str[xml_str.index('?>') + 2:].strip()
        
        root = ET.fromstring(xml_str)
        result = {"root_tag": root.tag}
        
        # 提取所有子元素
        for child in root:
            result[child.tag] = child.text
        
        # 特殊处理 DeviceList
        if root.tag == "Query" or root.tag == "Response":
            device_list = root.find("DeviceList")
            if device_list is not None:
                result["DeviceList"] = []
                for item in device_list.findall("Item"):
                    device_item = {}
                    for field in item:
                        device_item[field.tag] = field.text
                    result["DeviceList"].append(device_item)
        
        return result
        
    except Exception as e:
        return {"error": f"XML parse error: {str(e)}", "raw": xml_str}
