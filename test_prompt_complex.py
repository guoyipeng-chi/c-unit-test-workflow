#!/usr/bin/env python3
"""
测试有外部依赖的函数的prompt生成
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

from c_code_analyzer import FunctionDependency
from llm_test_generator import LLMTestGenerator

class MockLLMClient:
    def __init__(self):
        self.last_prompt = None
    
    def generate(self, prompt, **kwargs):
        self.last_prompt = prompt
        print("\n" + "="*80)
        print("生成的PROMPT (截取关键部分):")
        print("="*80)
        
        # 只显示关键部分
        if "=== FUNCTION SOURCE CODE ===" in prompt:
            idx = prompt.find("=== FUNCTION SOURCE CODE ===")
            end_idx = prompt.find("```", idx + 100) + 3
            print(prompt[idx:end_idx])
        
        # 检查外部调用信息
        if "External Function Calls" in prompt:
            idx = prompt.find("External Function Calls")
            end_idx = prompt.find("\n\n", idx)
            print(f"\n{prompt[idx:end_idx]}")
        
        print("\n" + "="*80)
        
        checks = {
            "包含函数源代码": "=== FUNCTION SOURCE CODE ===" in prompt,
            "包含头文件": "=== HEADER FILE:" in prompt,  
            "包含外部调用": "External Function Calls" in prompt,
            "源代码包含db_": "db_" in prompt,
        }
        
        print("\n检查结果:")
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
        
        return "// Mock test"

# 测试 add_student 函数（调用了 db_add_student）
def test_function_with_dependencies():
    mock_client = MockLLMClient()
    generator = LLMTestGenerator(mock_client)
    
    # 从 student_manager.c 读取真实函数
    test_func = FunctionDependency(
        name="add_student",
        return_type="int32_t",
        parameters=[("int32_t", "id"), ("const char*", "name"), ("float", "score")],
        external_calls={"validate_student_name", "validate_score", "validate_student_id", "db_add_student"},
        source_file="src/student_manager.c",
        include_files={"student_manager.h", "validator.h", "database.h"}
    )
    
    print("测试函数: add_student")
    print("源文件: src/student_manager.c")
    print(f"外部调用: {test_func.external_calls}")
    
    project_root = os.path.dirname(__file__)
    test_code = generator.generate_test_file(test_func, project_root=project_root)
    
    return mock_client.last_prompt

if __name__ == "__main__":
    test_function_with_dependencies()
