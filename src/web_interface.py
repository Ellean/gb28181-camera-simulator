"""
Web 控制界面
提供简单的 Web 页面用于控制模拟设备的行为
"""
import logging
import threading
import os
import yaml
import re
import secrets
from flask import Flask, render_template_string, jsonify, request
from typing import List, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)


def require_auth(f):
    """简单的认证装饰器 - 检查配置的访问令牌"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取配置的访问令牌
        auth_token = os.getenv('WEB_AUTH_TOKEN', '')
        
        # 如果没有配置令牌，则不需要认证
        if not auth_token:
            return f(*args, **kwargs)
        
        # 检查请求头中的令牌（使用恒定时间比较防止时序攻击）
        provided_token = request.headers.get('X-Auth-Token', '')
        if not secrets.compare_digest(provided_token, auth_token):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        return f(*args, **kwargs)
    return decorated_function


class WebInterface:
    """Web 控制界面"""
    
    def __init__(self, simulator_instance, port: int = 8000, host: str = '0.0.0.0'):
        """
        初始化 Web 界面
        
        Args:
            simulator_instance: GB28181Simulator 实例
            port: Web 服务器端口
            host: Web 服务器绑定地址 (默认 0.0.0.0 监听所有接口)
        """
        self.simulator = simulator_instance
        self.port = port
        self.host = host
        self.app = Flask(__name__)
        self.server_thread = None
        
        # 设置路由
        self._setup_routes()
        
        logger.info(f"Web interface initialized on {host}:{port}")
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template_string(HTML_TEMPLATE)
        
        @self.app.route('/api/devices')
        def get_devices():
            """获取设备列表"""
            devices_info = []
            for client in self.simulator.clients:
                device_info = {
                    'device_id': client.device_id,
                    'name': client.device_config.get('name', 'Unknown'),
                    'device_type': client.device_config.get('device_type', 'IPC'),
                    'registered': client.registered,
                    'status': 'online' if client.registered else 'offline',
                    'manufacturer': client.device_config.get('manufacturer', 'SimCamera'),
                    'model': client.device_config.get('model', 'SC-2000'),
                    'channels': len(client.device_config.get('channels', []))
                }
                devices_info.append(device_info)
            
            return jsonify({
                'success': True,
                'devices': devices_info,
                'total': len(devices_info)
            })
        
        @self.app.route('/api/device/<device_id>/unregister', methods=['POST'])
        def unregister_device(device_id):
            """注销设备"""
            client = self._find_client(device_id)
            if not client:
                return jsonify({'success': False, 'error': 'Device not found'}), 404
            
            try:
                client.unregister()
                return jsonify({'success': True, 'message': 'Device unregistered'})
            except Exception as e:
                logger.error(f"Error unregistering device: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/device/<device_id>/register', methods=['POST'])
        def register_device(device_id):
            """重新注册设备"""
            client = self._find_client(device_id)
            if not client:
                return jsonify({'success': False, 'error': 'Device not found'}), 404
            
            try:
                if client.register():
                    return jsonify({'success': True, 'message': 'Device registered'})
                else:
                    return jsonify({'success': False, 'error': 'Registration failed'}), 500
            except Exception as e:
                logger.error(f"Error registering device: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/device/<device_id>/keepalive', methods=['POST'])
        def send_keepalive(device_id):
            """发送心跳"""
            client = self._find_client(device_id)
            if not client:
                return jsonify({'success': False, 'error': 'Device not found'}), 404
            
            try:
                client.send_keepalive()
                return jsonify({'success': True, 'message': 'Keepalive sent'})
            except Exception as e:
                logger.error(f"Error sending keepalive: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/stats')
        def get_stats():
            """获取统计信息"""
            total = len(self.simulator.clients)
            registered = sum(1 for client in self.simulator.clients if client.registered)
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_devices': total,
                    'registered_devices': registered,
                    'offline_devices': total - registered,
                    'running': self.simulator.running
                }
            })
        
        @self.app.route('/api/config/devices', methods=['GET'])
        def get_device_configs():
            """获取设备配置列表"""
            try:
                config_path = self.simulator.devices_config_path
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                devices = config.get('devices', [])
                return jsonify({
                    'success': True,
                    'devices': devices,
                    'config_path': config_path
                })
            except Exception as e:
                logger.error(f"Error reading device config: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/config/device', methods=['POST'])
        @require_auth
        def add_device_config():
            """添加设备配置"""
            try:
                device_data = request.get_json()
                
                # 验证必需字段
                required_fields = ['device_id', 'name', 'sip_user', 'sip_password']
                for field in required_fields:
                    if field not in device_data:
                        return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
                
                # 验证设备ID格式（20位数字）
                if not re.match(r'^\d{20}$', device_data['device_id']):
                    return jsonify({'success': False, 'error': 'Invalid device_id format (must be 20 digits)'}), 400
                
                # 读取当前配置
                config_path = self.simulator.devices_config_path
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                devices = config.get('devices', [])
                
                # 检查设备ID是否已存在
                if any(d['device_id'] == device_data['device_id'] for d in devices):
                    return jsonify({'success': False, 'error': 'Device ID already exists'}), 400
                
                # 设置默认值
                if 'device_type' not in device_data:
                    device_data['device_type'] = 'IPC'
                if 'manufacturer' not in device_data:
                    device_data['manufacturer'] = 'SimCamera'
                if 'model' not in device_data:
                    device_data['model'] = 'SC-2000'
                if 'firmware' not in device_data:
                    device_data['firmware'] = 'V1.0.0'
                if 'channels' not in device_data:
                    device_data['channels'] = [{
                        'channel_id': device_data['device_id'],
                        'name': '主码流',
                        'ptz_enabled': False
                    }]
                
                # 添加新设备
                devices.append(device_data)
                config['devices'] = devices
                
                # 写入配置文件（先写入临时文件，然后重命名）
                temp_path = config_path + '.tmp'
                with open(temp_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)
                
                # 原子性替换
                os.replace(temp_path, config_path)
                
                logger.info(f"Device {device_data['device_id']} added to configuration")
                
                return jsonify({
                    'success': True,
                    'message': 'Device configuration added successfully',
                    'note': 'Restart simulator to apply changes'
                })
                
            except Exception as e:
                logger.error(f"Error adding device config: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/config/device/<device_id>', methods=['PUT'])
        @require_auth
        def update_device_config(device_id):
            """更新设备配置"""
            try:
                device_data = request.get_json()
                
                # 读取当前配置
                config_path = self.simulator.devices_config_path
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                devices = config.get('devices', [])
                
                # 查找设备
                device_index = None
                for i, d in enumerate(devices):
                    if d['device_id'] == device_id:
                        device_index = i
                        break
                
                if device_index is None:
                    return jsonify({'success': False, 'error': 'Device not found'}), 404
                
                # 更新设备配置（保留device_id）
                device_data['device_id'] = device_id
                devices[device_index] = device_data
                config['devices'] = devices
                
                # 写入配置文件（先写入临时文件，然后重命名）
                temp_path = config_path + '.tmp'
                with open(temp_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)
                
                # 原子性替换
                os.replace(temp_path, config_path)
                
                logger.info(f"Device {device_id} configuration updated")
                
                return jsonify({
                    'success': True,
                    'message': 'Device configuration updated successfully',
                    'note': 'Restart simulator to apply changes'
                })
                
            except Exception as e:
                logger.error(f"Error updating device config: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/config/device/<device_id>', methods=['DELETE'])
        @require_auth
        def delete_device_config(device_id):
            """删除设备配置"""
            try:
                # 读取当前配置
                config_path = self.simulator.devices_config_path
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                devices = config.get('devices', [])
                
                # 过滤掉要删除的设备
                original_count = len(devices)
                devices = [d for d in devices if d['device_id'] != device_id]
                
                if len(devices) == original_count:
                    return jsonify({'success': False, 'error': 'Device not found'}), 404
                
                config['devices'] = devices
                
                # 写入配置文件（先写入临时文件，然后重命名）
                temp_path = config_path + '.tmp'
                with open(temp_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)
                
                # 原子性替换
                os.replace(temp_path, config_path)
                
                logger.info(f"Device {device_id} deleted from configuration")
                
                return jsonify({
                    'success': True,
                    'message': 'Device configuration deleted successfully',
                    'note': 'Restart simulator to apply changes'
                })
                
            except Exception as e:
                logger.error(f"Error deleting device config: {e}", exc_info=True)
                return jsonify({'success': False, 'error': str(e)}), 500
    
    def _find_client(self, device_id: str):
        """查找客户端"""
        for client in self.simulator.clients:
            if client.device_id == device_id:
                return client
        return None
    
    def start(self):
        """启动 Web 服务器"""
        def run_server():
            # 禁用 Flask 开发服务器的自动重载
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"Web interface started at http://{self.host}:{self.port}")


# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GB28181 设备模拟器控制面板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .stat-label {
            color: #666;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .stat-value {
            color: #333;
            font-size: 32px;
            font-weight: bold;
        }
        .devices {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .device-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .device-card:hover {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .device-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-online {
            background: #4caf50;
            color: white;
        }
        .status-offline {
            background: #f44336;
            color: white;
        }
        .device-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 5px;
        }
        .info-item {
            font-size: 14px;
        }
        .info-label {
            color: #666;
            font-weight: 500;
        }
        .info-value {
            color: #333;
        }
        .device-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        .btn-primary {
            background: #2196f3;
            color: white;
        }
        .btn-success {
            background: #4caf50;
            color: white;
        }
        .btn-danger {
            background: #f44336;
            color: white;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .loading {
            text-align: center;
            padding: 50px;
            color: #666;
        }
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .refresh-btn {
            float: right;
            background: #667eea;
            color: white;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .tab {
            padding: 15px 25px;
            background: transparent;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
        }
        .tab:hover {
            color: #667eea;
            background: #f5f5f5;
        }
        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            font-size: 14px;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 100px;
        }
        .form-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
        }
        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .modal-content {
            background: white;
            border-radius: 10px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-header h3 {
            margin: 0;
            color: #333;
        }
        .close-btn {
            background: transparent;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
        }
        .close-btn:hover {
            color: #333;
        }
        .config-list {
            list-style: none;
            padding: 0;
        }
        .config-item {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .config-item-info {
            flex: 1;
        }
        .config-item-actions {
            display: flex;
            gap: 10px;
        }
        .btn-small {
            padding: 5px 10px;
            font-size: 12px;
        }
        .warning-note {
            background: #fff3cd;
            color: #856404;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border: 1px solid #ffeaa7;
        }
        .warning-note strong {
            display: block;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 GB28181 设备模拟器控制面板</h1>
            <p class="subtitle">实时控制和监控模拟设备的行为</p>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-label">总设备数</div>
                <div class="stat-value" id="total-devices">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">在线设备</div>
                <div class="stat-value" id="registered-devices" style="color: #4caf50;">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">离线设备</div>
                <div class="stat-value" id="offline-devices" style="color: #f44336;">-</div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('devices')">运行状态</button>
            <button class="tab" onclick="switchTab('config')">设备配置</button>
        </div>
        
        <div id="devices-tab" class="tab-content active">
            <div class="devices">
                <h2 style="margin-bottom: 20px;">
                    设备列表
                    <button class="btn refresh-btn" onclick="loadDevices()">🔄 刷新</button>
                </h2>
                <div id="devices-container" class="loading">
                    加载中...
                </div>
            </div>
        </div>
        
        <div id="config-tab" class="tab-content">
            <div class="devices">
                <div class="warning-note">
                    <strong>⚠️ 安全提示</strong>
                    配置修改操作会直接写入文件系统。如果启用了 WEB_AUTH_TOKEN 环境变量，需要在请求头中提供认证令牌。修改后需要重启模拟器才能生效。
                </div>
                
                <h2 style="margin-bottom: 20px;">
                    设备配置管理
                    <button class="btn btn-success refresh-btn" onclick="loadConfigs()">🔄 刷新</button>
                    <button class="btn btn-primary refresh-btn" style="margin-right: 10px;" onclick="showAddModal()">➕ 添加设备</button>
                </h2>
                
                <div id="configs-container" class="loading">
                    加载中...
                </div>
            </div>
        </div>
    </div>
    
    <!-- 添加/编辑设备模态框 -->
    <div id="deviceModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modal-title">添加设备</h3>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <form id="deviceForm">
                <div class="form-group">
                    <label>设备 ID *</label>
                    <input type="text" id="device_id" name="device_id" required pattern="\\d{20}" 
                           placeholder="20位数字" maxlength="20">
                </div>
                <div class="form-group">
                    <label>设备名称 *</label>
                    <input type="text" id="name" name="name" required placeholder="例如：摄像头-1">
                </div>
                <div class="form-group">
                    <label>设备类型</label>
                    <select id="device_type" name="device_type">
                        <option value="IPC">IPC - 网络摄像机</option>
                        <option value="摄像机">摄像机</option>
                        <option value="DVR">DVR - 数字视频录像机</option>
                        <option value="NVR">NVR - 网络视频录像机</option>
                        <option value="报警控制器">报警控制器</option>
                        <option value="显示器">显示器</option>
                        <option value="报警输入设备">报警输入设备</option>
                        <option value="报警输出设备">报警输出设备</option>
                        <option value="语音输入设备">语音输入设备</option>
                        <option value="语音输出设备">语音输出设备</option>
                        <option value="移动传输设备">移动传输设备</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>SIP 用户名 *</label>
                    <input type="text" id="sip_user" name="sip_user" required placeholder="通常与设备ID相同">
                </div>
                <div class="form-group">
                    <label>SIP 密码 *</label>
                    <input type="password" id="sip_password" name="sip_password" required placeholder="SIP 认证密码">
                </div>
                <div class="form-group">
                    <label>制造商</label>
                    <input type="text" id="manufacturer" name="manufacturer" placeholder="默认: SimCamera">
                </div>
                <div class="form-group">
                    <label>型号</label>
                    <input type="text" id="model" name="model" placeholder="默认: SC-2000">
                </div>
                <div class="form-group">
                    <label>固件版本</label>
                    <input type="text" id="firmware" name="firmware" placeholder="默认: V1.0.0">
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">保存</button>
                    <button type="button" class="btn" onclick="closeModal()">取消</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let refreshInterval;

        async function loadDevices() {
            try {
                const response = await fetch('/api/devices');
                const data = await response.json();
                
                if (data.success) {
                    displayDevices(data.devices);
                    updateStats();
                }
            } catch (error) {
                console.error('Error loading devices:', error);
                document.getElementById('devices-container').innerHTML = 
                    '<div class="error">加载设备列表失败: ' + error.message + '</div>';
            }
        }

        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('total-devices').textContent = data.stats.total_devices;
                    document.getElementById('registered-devices').textContent = data.stats.registered_devices;
                    document.getElementById('offline-devices').textContent = data.stats.offline_devices;
                }
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        function displayDevices(devices) {
            const container = document.getElementById('devices-container');
            
            if (devices.length === 0) {
                container.innerHTML = '<p class="loading">没有设备</p>';
                return;
            }
            
            container.innerHTML = devices.map(device => `
                <div class="device-card">
                    <div class="device-header">
                        <div class="device-title">${device.name}</div>
                        <span class="status-badge status-${device.status}">
                            ${device.status === 'online' ? '在线' : '离线'}
                        </span>
                    </div>
                    <div class="device-info">
                        <div class="info-item">
                            <span class="info-label">设备ID:</span><br>
                            <span class="info-value">${device.device_id}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">设备类型:</span><br>
                            <span class="info-value">${device.device_type}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">制造商:</span><br>
                            <span class="info-value">${device.manufacturer}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">型号:</span><br>
                            <span class="info-value">${device.model}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">通道数:</span><br>
                            <span class="info-value">${device.channels}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">注册状态:</span><br>
                            <span class="info-value">${device.registered ? '已注册' : '未注册'}</span>
                        </div>
                    </div>
                    <div class="device-actions">
                        ${device.registered ? 
                            `<button class="btn btn-danger" onclick="unregisterDevice('${device.device_id}')">注销设备</button>` :
                            `<button class="btn btn-success" onclick="registerDevice('${device.device_id}')">注册设备</button>`
                        }
                        <button class="btn btn-primary" onclick="sendKeepalive('${device.device_id}')" 
                                ${!device.registered ? 'disabled' : ''}>
                            发送心跳
                        </button>
                    </div>
                </div>
            `).join('');
        }

        async function unregisterDevice(deviceId) {
            if (!confirm('确定要注销此设备吗？')) return;
            
            try {
                const response = await fetch(`/api/device/${deviceId}/unregister`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success) {
                    alert('设备已注销');
                    loadDevices();
                } else {
                    alert('注销失败: ' + data.error);
                }
            } catch (error) {
                alert('操作失败: ' + error.message);
            }
        }

        async function registerDevice(deviceId) {
            try {
                const response = await fetch(`/api/device/${deviceId}/register`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success) {
                    alert('设备已注册');
                    loadDevices();
                } else {
                    alert('注册失败: ' + data.error);
                }
            } catch (error) {
                alert('操作失败: ' + error.message);
            }
        }

        async function sendKeepalive(deviceId) {
            try {
                const response = await fetch(`/api/device/${deviceId}/keepalive`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success) {
                    alert('心跳已发送');
                } else {
                    alert('发送失败: ' + data.error);
                }
            } catch (error) {
                alert('操作失败: ' + error.message);
            }
        }

        // ========== 配置管理功能 ==========
        let currentEditDevice = null;
        const authToken = localStorage.getItem('authToken') || '';

        function switchTab(tabName) {
            // 切换标签
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
            
            // 加载对应内容
            if (tabName === 'config') {
                loadConfigs();
            }
        }

        async function loadConfigs() {
            try {
                const response = await fetch('/api/config/devices');
                const data = await response.json();
                
                if (data.success) {
                    displayConfigs(data.devices);
                }
            } catch (error) {
                console.error('Error loading configs:', error);
                document.getElementById('configs-container').innerHTML = 
                    '<div class="error">加载配置失败: ' + error.message + '</div>';
            }
        }

        function displayConfigs(devices) {
            const container = document.getElementById('configs-container');
            
            if (devices.length === 0) {
                container.innerHTML = '<p class="loading">没有设备配置</p>';
                return;
            }
            
            container.innerHTML = '<ul class="config-list">' + devices.map(device => `
                <li class="config-item">
                    <div class="config-item-info">
                        <strong>${device.name}</strong> (${device.device_type || 'IPC'})<br>
                        <small>ID: ${device.device_id}</small>
                    </div>
                    <div class="config-item-actions">
                        <button class="btn btn-primary btn-small" onclick='editConfig(${JSON.stringify(device)})'>编辑</button>
                        <button class="btn btn-danger btn-small" onclick="deleteConfig('${device.device_id}', '${device.name}')">删除</button>
                    </div>
                </li>
            `).join('') + '</ul>';
        }

        function showAddModal() {
            currentEditDevice = null;
            document.getElementById('modal-title').textContent = '添加设备';
            document.getElementById('deviceForm').reset();
            document.getElementById('device_id').disabled = false;
            document.getElementById('deviceModal').classList.add('active');
        }

        function editConfig(device) {
            currentEditDevice = device.device_id;
            document.getElementById('modal-title').textContent = '编辑设备';
            
            // 填充表单
            document.getElementById('device_id').value = device.device_id;
            document.getElementById('device_id').disabled = true;
            document.getElementById('name').value = device.name;
            document.getElementById('device_type').value = device.device_type || 'IPC';
            document.getElementById('sip_user').value = device.sip_user;
            document.getElementById('sip_password').value = device.sip_password;
            document.getElementById('manufacturer').value = device.manufacturer || '';
            document.getElementById('model').value = device.model || '';
            document.getElementById('firmware').value = device.firmware || '';
            
            document.getElementById('deviceModal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('deviceModal').classList.remove('active');
            document.getElementById('deviceForm').reset();
            currentEditDevice = null;
        }

        async function saveDevice(formData) {
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // 添加认证令牌（如果有）
            if (authToken) {
                headers['X-Auth-Token'] = authToken;
            }
            
            try {
                let response;
                if (currentEditDevice) {
                    // 更新设备
                    response = await fetch(`/api/config/device/${currentEditDevice}`, {
                        method: 'PUT',
                        headers: headers,
                        body: JSON.stringify(formData)
                    });
                } else {
                    // 添加设备
                    response = await fetch('/api/config/device', {
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify(formData)
                    });
                }
                
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message + ' ' + (data.note || ''));
                    closeModal();
                    loadConfigs();
                } else {
                    if (response.status === 401) {
                        const token = prompt('需要认证令牌。请输入 WEB_AUTH_TOKEN：');
                        if (token) {
                            localStorage.setItem('authToken', token);
                            location.reload();
                        }
                    } else {
                        alert('保存失败: ' + data.error);
                    }
                }
            } catch (error) {
                alert('操作失败: ' + error.message);
            }
        }

        async function deleteConfig(deviceId, deviceName) {
            if (!confirm(`确定要删除设备 "${deviceName}" 吗？\n\n此操作将修改配置文件，需要重启模拟器才能生效。`)) {
                return;
            }
            
            const headers = {};
            if (authToken) {
                headers['X-Auth-Token'] = authToken;
            }
            
            try {
                const response = await fetch(`/api/config/device/${deviceId}`, {
                    method: 'DELETE',
                    headers: headers
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message + ' ' + (data.note || ''));
                    loadConfigs();
                } else {
                    if (response.status === 401) {
                        const token = prompt('需要认证令牌。请输入 WEB_AUTH_TOKEN：');
                        if (token) {
                            localStorage.setItem('authToken', token);
                            location.reload();
                        }
                    } else {
                        alert('删除失败: ' + data.error);
                    }
                }
            } catch (error) {
                alert('操作失败: ' + error.message);
            }
        }

        // 页面加载时执行（合并所有初始化逻辑）
        document.addEventListener('DOMContentLoaded', function() {
            // 加载初始设备状态
            loadDevices();
            
            // 每5秒自动刷新设备状态
            refreshInterval = setInterval(loadDevices, 5000);
            
            // 设置表单提交处理
            document.getElementById('deviceForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = {
                    device_id: document.getElementById('device_id').value,
                    name: document.getElementById('name').value,
                    device_type: document.getElementById('device_type').value,
                    sip_user: document.getElementById('sip_user').value,
                    sip_password: document.getElementById('sip_password').value,
                    manufacturer: document.getElementById('manufacturer').value || 'SimCamera',
                    model: document.getElementById('model').value || 'SC-2000',
                    firmware: document.getElementById('firmware').value || 'V1.0.0'
                };
                
                saveDevice(formData);
            });
        });

        // 页面卸载时清理
        window.addEventListener('beforeunload', function() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        });
    </script>
</body>
</html>
"""
