"""
Web 控制界面
提供简单的 Web 页面用于控制模拟设备的行为
"""
import logging
import threading
from flask import Flask, render_template_string, jsonify, request
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


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

        // 页面加载时执行
        document.addEventListener('DOMContentLoaded', function() {
            loadDevices();
            // 每5秒自动刷新
            refreshInterval = setInterval(loadDevices, 5000);
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
