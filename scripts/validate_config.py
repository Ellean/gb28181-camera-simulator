#!/usr/bin/env python3
"""
配置验证脚本
验证 .env 和 devices.yaml 配置是否正确
"""
import os
import sys
import yaml
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def validate_env():
    """验证环境变量配置"""
    print("检查环境变量配置...")
    
    required_vars = [
        'SIP_SERVER_IP',
        'SIP_SERVER_PORT',
        'SIP_SERVER_ID',
        'SIP_DOMAIN',
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"  ✗ {var}: 未设置")
        else:
            print(f"  ✓ {var}: {value}")
    
    if missing:
        print(f"\n❌ 缺少必需的环境变量: {', '.join(missing)}")
        return False
    
    print("✅ 环境变量配置正确\n")
    return True

def validate_devices_config():
    """验证设备配置文件"""
    print("检查设备配置文件...")
    
    config_path = os.getenv('DEVICES_CONFIG', 'config/devices.yaml')
    
    if not os.path.exists(config_path):
        print(f"  ✗ 配置文件不存在: {config_path}")
        return False
    
    print(f"  ✓ 配置文件存在: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        devices = config.get('devices', [])
        if not devices:
            print("  ✗ 没有配置任何设备")
            return False
        
        print(f"  ✓ 找到 {len(devices)} 个设备配置")
        
        for i, device in enumerate(devices):
            print(f"\n  设备 {i+1}:")
            
            required_fields = ['device_id', 'sip_user', 'sip_password', 'channels']
            for field in required_fields:
                if field not in device:
                    print(f"    ✗ 缺少字段: {field}")
                    return False
                else:
                    if field == 'sip_password':
                        print(f"    ✓ {field}: ****")
                    else:
                        print(f"    ✓ {field}: {device[field]}")
            
            channels = device.get('channels', [])
            if not channels:
                print(f"    ✗ 没有配置通道")
                return False
            print(f"    ✓ 通道数: {len(channels)}")
        
        print("\n✅ 设备配置正确\n")
        return True
        
    except Exception as e:
        print(f"  ✗ 解析配置文件失败: {e}")
        return False

def validate_media():
    """验证媒体文件"""
    print("检查媒体文件...")
    
    video_file = os.getenv('VIDEO_FILE', 'media/sample.mp4')
    
    if not os.path.exists(video_file):
        print(f"  ⚠ 视频文件不存在: {video_file}")
        print(f"  提示: 使用 scripts/generate_test_video.sh 生成测试视频")
        print(f"  或将视频文件复制到: {video_file}")
        return False
    
    print(f"  ✓ 视频文件存在: {video_file}")
    
    file_size = os.path.getsize(video_file)
    print(f"  ✓ 文件大小: {file_size / 1024 / 1024:.2f} MB")
    
    print("✅ 媒体文件正确\n")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("GB28181 摄像头模拟器 - 配置验证")
    print("=" * 60)
    print()
    
    # 加载 .env 文件
    env_file = '.env'
    if os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv()
        print(f"已加载环境变量文件: {env_file}\n")
    else:
        print(f"⚠ 环境变量文件不存在: {env_file}")
        print(f"提示: 复制 .env.example 为 .env 并修改配置\n")
    
    # 验证各项配置
    results = [
        validate_env(),
        validate_devices_config(),
        validate_media()
    ]
    
    print("=" * 60)
    if all(results):
        print("✅ 所有配置验证通过!")
        print("可以运行模拟器: docker-compose up -d")
        return 0
    else:
        print("❌ 配置验证失败，请检查上述错误")
        return 1

if __name__ == '__main__':
    sys.exit(main())
