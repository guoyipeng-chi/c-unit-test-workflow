#!/usr/bin/env python3
"""
测试prompt生成，验证是否包含源代码和头文件
"""

import sys
import os

# 添加tools目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from c_code_analyzer import FunctionDependency
from llm_test_generator import LLMTestGenerator
from llm_client import VLLMClient

def test_prompt_generation():
    """测试prompt是否包含源代码和头文件"""
    
    # 创建一个模拟的LLM客户端（不实际调用）
    class MockLLMClient:
        def __init__(self):
            self.last_prompt = None
        
        def generate(self, prompt, **kwargs):
            self.last_prompt = prompt
            print("\n" + "="*80)
            print("生成的PROMPT:")
            print("="*80)
            print(prompt)
            print("="*80)
            
            # 检查关键内容
            checks = {
                "函数源代码": "=== FUNCTION SOURCE CODE ===" in prompt,
                "头文件内容": "=== HEADER FILE:" in prompt,
                "函数名称": "validate_student_name" in prompt,
                "参数信息": "Parameters:" in prompt,
                "包含实际C代码": "```c" in prompt,
                "包含函数体": "strlen" in prompt or "return" in prompt,
            }
            
            print("\n检查结果:")
            for check_name, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"  {status} {check_name}")
            
            all_passed = all(checks.values())
            print(f"\n总体结果: {'✓ 通过' if all_passed else '✗ 失败'}")
            
            return "// Mock test code"
    
    # 创建生成器
    mock_client = MockLLMClient()
    generator = LLMTestGenerator(mock_client)
    
    # 创建一个测试函数依赖
    test_func = FunctionDependency(
        name="validate_student_name",
        return_type="int32_t",
        parameters=[("const char*", "name")],
        external_calls=set(),
        source_file="src/validator.c",
        include_files={"validator.h", "database.h"}
    )
    
    print("测试函数: validate_student_name")
    print("源文件: src/validator.c")
    print("依赖头文件: validator.h, database.h")
    
    # 生成测试（应该会读取实际文件）
    project_root = os.path.dirname(__file__)
    test_code = generator.generate_test_file(
        test_func,
        project_root=project_root
    )
    
    return mock_client.last_prompt

if __name__ == "__main__":
    test_prompt_generation()
