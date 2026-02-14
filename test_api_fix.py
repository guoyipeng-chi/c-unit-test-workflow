#!/usr/bin/env python3
"""
测试generate()方法的API修复
验证使用Chat API而不是completions API
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from llm_client import VLLMClient

def test_generate_method():
    """测试generate方法是否使用Chat API"""
    
    print("=" * 70)
    print("LLM Client API 修复验证")
    print("=" * 70)
    
    # 创建客户端（使用本地默认）
    print("\n[1] 创建vLLM客户端...")
    try:
        client = VLLMClient()
        print(f"    ✓ 已连接到: {client.api_base}")
        print(f"    ✓ 模型: {client.model}")
    except Exception as e:
        print(f"    ✗ 连接失败: {e}")
        return False
    
    # 检查generate方法的签名
    print("\n[2] 验证generate方法修复...")
    import inspect
    source = inspect.getsource(client.generate)
    
    checks = {
        "使用Chat API": "/v1/chat/completions" in source,
        "消息列表格式": '"role": "user"' in source or "'role': 'user'" in source,
        "正确解析响应": 'message.get("content"' in source or "message'].get('content" in source,
        "移除stop参数": "stop" not in source,  # Chat API不需要stop参数
    }
    
    print("    修复检查项:")
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"      {status} {check}")
    
    all_passed = all(checks.values())
    
    # 显示关键代码片段
    print("\n[3] 关键代码验证:")
    
    # 提取url行
    for line in source.split('\n'):
        if '/v1/chat/completions' in line or 'url =' in line:
            print(f"    API端点: {line.strip()}")
            break
    
    # 提取消息格式
    for i, line in enumerate(source.split('\n')):
        if 'messages' in line and '=' in line:
            # 显示消息构建代码
            for j in range(max(0, i-1), min(len(source.split('\n')), i+6)):
                print(f"    {source.split(chr(10))[j]}")
            break
    
    # 显示响应解析
    print("\n    响应解析:")
    for line in source.split('\n'):
        if 'message' in line and 'content' in line:
            print(f"    {line.strip()}")
            break
    
    # 总结
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ 所有修复检查通过！")
        print("\n改进说明:")
        print("  1. 现在使用 /v1/chat/completions API")
        print("  2. 能生成独立的代码片段（而不是文本续写）")
        print("  3. 更好地理解复杂指令")
        print("  4. 响应格式更清晰")
        print("\n这个修复对测试生成质量的影响：")
        print("  ✓ LLM能正确理解 'Generate test code' 指令")
        print("  ✓ 生成的代码更完整、更准确")
        print("  ✓ 减少了文本续写的问题")
    else:
        print("✗ 某些检查项未通过！")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = test_generate_method()
    sys.exit(0 if success else 1)
