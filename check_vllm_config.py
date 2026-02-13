#!/usr/bin/env python3
"""
验证vLLM配置是否正确
快速检查环境变量和连接状态
"""

import os
import sys
import requests

def check_vllm_config():
    """检查vLLM配置"""
    print("=" * 60)
    print("vLLM 配置检查")
    print("=" * 60)
    
    # 1. 检查环境变量
    print("\n[1] 环境变量:")
    env_vars = {
        'VLLM_API_BASE': os.getenv('VLLM_API_BASE', '未设置（使用默认值）'),
        'VLLM_MODEL': os.getenv('VLLM_MODEL', '未设置（使用默认值）'),
        'VLLM_API_KEY': '***' if os.getenv('VLLM_API_KEY') else '未设置',
        'VLLM_TIMEOUT': os.getenv('VLLM_TIMEOUT', '未设置（使用默认值）'),
    }
    
    for key, value in env_vars.items():
        print(f"  {key}: {value}")
    
    # 2. 检查最终使用的配置
    print("\n[2] 最终配置:")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
    from llm_client import VLLMClient
    
    try:
        client = VLLMClient()  # 使用默认配置（会读取环境变量）
        print(f"  API地址: {client.api_base}")
        print(f"  模型名称: {client.model}")
        print(f"  超时设置: {client.timeout}秒")
    except Exception as e:
        print(f"  ✗ 初始化失败: {e}")
        return False
    
    # 3. 测试连接
    print("\n[3] 连接测试:")
    try:
        response = requests.get(
            f"{client.api_base}/v1/models",
            timeout=5,
            headers={"Authorization": f"Bearer {client.api_key}"}
        )
        
        if response.status_code == 200:
            print(f"  ✓ 成功连接到 {client.api_base}")
            
            # 显示可用模型
            try:
                models_data = response.json()
                if 'data' in models_data and len(models_data['data']) > 0:
                    print(f"  ✓ 可用模型:")
                    for model in models_data['data']:
                        model_id = model.get('id', 'unknown')
                        marker = " ← 当前" if model_id == client.model else ""
                        print(f"    - {model_id}{marker}")
                else:
                    print(f"  ⚠ 未找到模型信息")
            except:
                print(f"  ⚠ 无法解析模型列表")
        else:
            print(f"  ✗ 连接失败 (HTTP {response.status_code})")
            print(f"  响应: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"  ✗ 无法连接到 {client.api_base}")
        print(f"  提示: 请检查vLLM服务是否启动")
        return False
    except requests.exceptions.Timeout:
        print(f"  ✗ 连接超时")
        print(f"  提示: 服务器响应太慢或地址不正确")
        return False
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False
    
    # 4. 总结
    print("\n" + "=" * 60)
    print("✓ 配置检查通过！可以开始生成测试了。")
    print("=" * 60)
    print("\n下一步:")
    print("  python quickstart_llm.py --interactive")
    print("  或")
    print("  python tools/ut_workflow_llm.py --functions validate_student_name")
    
    return True


if __name__ == "__main__":
    success = check_vllm_config()
    sys.exit(0 if success else 1)
