#!/usr/bin/env python3
"""
LLM-based Test Generator
使用Qwen3 Coder通过提示工程生成单元测试
"""

import json
import logging
import os
import re
from typing import Optional, Dict, List
from dataclasses import dataclass
from llm_client import VLLMClient
from c_code_analyzer import FunctionDependency
from compile_commands_analyzer import CompileInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMTestGenerator:
    """基于LLM的测试代码生成器"""
    
    def __init__(self, llm_client: VLLMClient):
        """
        初始化LLM测试生成器
        
        Args:
            llm_client: VLLMClient实例
        """
        self.llm = llm_client
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        return """You are an expert C/C++ unit test engineer. Your task is to generate comprehensive, high-quality unit tests for C functions using Google Test (gtest) framework.

Guidelines:
1. Generate tests with multiple test cases covering:
   - Normal/valid inputs
   - Edge cases and boundary conditions
   - Invalid inputs and error handling
   - Special cases (null pointers, zero, empty strings, etc.)

2. Use appropriate mock objects (gmock) for external function dependencies
3. Use meaningful test names that describe what is being tested
4. Include setup and teardown code when needed
5. Add comments explaining complex test logic
6. Ensure tests are independent and can run in any order

Return ONLY the C++ test code, no explanations."""
    
    def generate_test_file(self, func_dep: FunctionDependency, 
                          compile_info: Optional[CompileInfo] = None,
                          extra_context: str = "",
                          project_root: str = ".") -> str:
        """
        使用LLM生成测试文件
        
        Args:
            func_dep: 函数依赖信息
            compile_info: 编译信息
            extra_context: 额外的上下文信息
            project_root: 项目根目录（用于读取源文件）
            
        Returns:
            生成的测试代码
        """
        prompt = self._build_prompt(func_dep, compile_info, extra_context, project_root)
        
        logger.info(f"Generating tests for {func_dep.name}...")
        
        # 调用LLM
        response = self.llm.generate(
            prompt,
            temperature=0.7,
            max_tokens=8192,
            top_p=0.95
        )
        
        if not response:
            logger.error(f"Failed to generate test for {func_dep.name}")
            return self._generate_fallback_test(func_dep)
        
        # 清理响应（移除markdown标记等）
        test_code = self._clean_response(response)
        
        return test_code
    
    def _build_prompt(self, func_dep: FunctionDependency,
                     compile_info: Optional[CompileInfo] = None,
                     extra_context: str = "",
                     project_root: str = ".") -> str:
        """构建提示词"""
        
        # 读取被测函数的源代码
        function_source = self._read_function_source(func_dep, project_root)
        
        # 读取依赖的头文件内容
        header_contents = self._read_header_files(func_dep, project_root)
        
        # 基本信息
        prompt = f"""Generate comprehensive unit tests for this C function:

Function Name: {func_dep.name}
Return Type: {func_dep.return_type}
Source File: {func_dep.source_file}

Parameters:
"""
        
        if func_dep.parameters:
            for ptype, pname in func_dep.parameters:
                prompt += f"  - {ptype} {pname}\n"
        else:
            prompt += "  - void (no parameters)\n"
        
        # 添加函数实际源代码
        if function_source:
            prompt += f"\n=== FUNCTION SOURCE CODE ===\n```c\n{function_source}\n```\n"
        
        # 外部调用/依赖
        if func_dep.external_calls:
            prompt += f"\nExternal Function Calls (requires mocking):\n"
            for call in sorted(func_dep.external_calls):
                prompt += f"  - {call}()\n"
        else:
            prompt += f"\nExternal Function Calls: None\n"
        
        # 依赖的头文件
        if func_dep.include_files:
            prompt += f"\nInclude Files:\n"
            for inc in sorted(func_dep.include_files):
                prompt += f"  - {inc}\n"
        
        # 添加头文件内容
        if header_contents:
            for header_name, content in header_contents.items():
                prompt += f"\n=== HEADER FILE: {header_name} ===\n```c\n{content}\n```\n"
        
        # 编译信息
        if compile_info:
            prompt += f"\nCompilation Info:\n"
            prompt += f"  C Standard: {compile_info.c_standard or 'default'}\n"
            prompt += f"  C++ Standard: {compile_info.cxx_standard or 'c++14'}\n"
            
            if compile_info.defines:
                prompt += f"  Macros: {', '.join(compile_info.defines.keys())}\n"
        
        # 额外上下文
        if extra_context:
            prompt += f"\nAdditional Context:\n{extra_context}\n"
        
        # 生成要求
        prompt += """
Generate a complete test file with:
1. All necessary #include directives
2. Mock definitions for external calls
3. A test fixture class
4. Multiple test cases covering various scenarios
5. Proper error handling and assertions

Make sure the tests are:
- Comprehensive and cover edge cases
- Independent and isolated
- Using Google Test (gtest) framework
- Using Google Mock (gmock) for mocking

Return ONLY the C++ code, no markdown wrappers."""
        
        return prompt
    
    def _clean_response(self, response: str) -> str:
        """清理LLM响应"""
        # 移除markdown代码块标记
        if response.startswith("```"):
            lines = response.split('\n')
            # 移除第一行的```cpp或```c++等
            if lines[0].startswith("```"):
                lines = lines[1:]
            # 移除最后的```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = '\n'.join(lines)
        
        # 移除开头和结尾的空白
        response = response.strip()
        
        return response
    
    def _generate_fallback_test(self, func_dep: FunctionDependency) -> str:
        """生成备选测试代码"""
        logger.warning(f"Generating fallback test for {func_dep.name}")
        
        # 根据函数签名生成一个基本的测试框架
        test_template = f"""#include <gtest/gtest.h>
#include <gmock/gmock.h>

// TODO: Generate proper tests for {func_dep.name}()
// This is a fallback template - please review and complete

class {func_dep.name.capitalize()}Test : public ::testing::Test {{
protected:
    void SetUp() override {{
        // Initialize test fixtures
    }}
    
    void TearDown() override {{
        // Cleanup
    }}
}};

TEST_F({func_dep.name.capitalize()}Test, BasicTest) {{
    // TODO: Implement test
    EXPECT_TRUE(true);
}}
"""
        return test_template
    
    def _read_function_source(self, func_dep: FunctionDependency, project_root: str) -> str:
        """读取函数的源代码"""
        try:
            # 构建源文件的完整路径
            source_path = os.path.join(project_root, func_dep.source_file)
            if not os.path.exists(source_path):
                logger.warning(f"Source file not found: {source_path}")
                return ""
            
            with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 提取函数定义（从函数声明到 } 结束）
            # 更宽松的模式：允许返回类型和函数名之间有多个空格/换行
            # 例如: int32_t validate_name(...) { 或 int32_t\nvalidate_name(...)\n{
            pattern = rf'{re.escape(func_dep.return_type)}\s+{re.escape(func_dep.name)}\s*\('
            match = re.search(pattern, content)
            
            if match:
                # 从匹配位置开始，找到函数体的开始 {
                start_pos = match.start()
                open_brace_pos = content.find('{', match.end())
                
                if open_brace_pos == -1:
                    logger.warning(f"Could not find opening brace for {func_dep.name}")
                    return ""
                
                # 从 { 开始计数括号，找到对应的结束 }
                brace_count = 1  # 已经找到第一个 {
                end_pos = open_brace_pos + 1
                
                for i in range(open_brace_pos + 1, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                if brace_count == 0:
                    function_code = content[start_pos:end_pos]
                    return function_code.strip()
                else:
                    logger.warning(f"Unbalanced braces for function {func_dep.name}")
                    return ""
            
            logger.warning(f"Could not find function {func_dep.name} in {source_path}")
            return ""
            
        except Exception as e:
            logger.error(f"Error reading function source: {e}")
            return ""
    
    def _read_header_files(self, func_dep: FunctionDependency, project_root: str) -> Dict[str, str]:
        """读取依赖的头文件内容"""
        headers = {}
        
        for header_name in func_dep.include_files:
            # 尝试多个可能的路径
            possible_paths = [
                os.path.join(project_root, 'include', header_name),
                os.path.join(project_root, header_name),
                os.path.join(project_root, 'src', header_name),
            ]
            
            for header_path in possible_paths:
                if os.path.exists(header_path):
                    try:
                        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        # 清理内容（移除注释等，保留主要定义）
                        content = self._clean_header_content(content)
                        headers[header_name] = content
                        break
                    except Exception as e:
                        logger.error(f"Error reading header {header_path}: {e}")
        
        return headers
    
    def _clean_header_content(self, content: str) -> str:
        """清理头文件内容，保留关键部分"""
        # 移除多行注释
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # 移除单行注释
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        # 移除多余的空行
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        return content.strip()
    
    def generate_batch_tests(self, func_deps: List[FunctionDependency],
                            compile_info_map: Optional[Dict[str, CompileInfo]] = None,
                            project_root: str = ".") -> Dict[str, str]:
        """
        批量生成多个函数的测试
        
        Args:
            func_deps: 函数依赖列表
            compile_info_map: 编译信息映射
            project_root: 项目根目录
            
        Returns:
            {函数名: 测试代码}
        """
        results = {}
        
        for func_dep in func_deps:
            compile_info = None
            if compile_info_map and func_dep.source_file in compile_info_map:
                compile_info = compile_info_map[func_dep.source_file]
            
            test_code = self.generate_test_file(func_dep, compile_info, project_root=project_root)
            results[func_dep.name] = test_code
        
        return results


class PromptBuilder:
    """提示词构建工具"""
    
    @staticmethod
    def build_header_documentation(header_content: str) -> str:
        """从头文件内容构建文档"""
        # 提取函数声明、宏定义等
        lines = []
        
        # 查找struct/typedef定义
        if 'struct' in header_content or 'typedef' in header_content:
            lines.append("Data structures defined:")
            # 简单地包含相关行
            for line in header_content.split('\n'):
                if 'struct' in line or 'typedef' in line:
                    lines.append(f"  {line.strip()}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def build_source_context(source_code: str, func_name: str, lines_context: int = 5) -> str:
        """提取源代码上下文"""
        lines = source_code.split('\n')
        
        # 查找函数定义
        for i, line in enumerate(lines):
            if f'{func_name}(' in line:
                # 提取函数定义及其上下文
                start = max(0, i - lines_context)
                end = min(len(lines), i + 20)  # 包含函数体
                
                context = '\n'.join(lines[start:end])
                return f"Source context:\n```c\n{context}\n```"
        
        return ""


if __name__ == "__main__":
    # 简单测试
    from llm_client import create_client
    
    client = create_client("http://localhost:8000", "qwen-coder")
    generator = LLMTestGenerator(client)
    
    # 创建一个测试的FunctionDependency对象
    test_func = FunctionDependency(
        name="validate_name",
        return_type="int",
        parameters=[("const char*", "name")],
        external_calls=set(),
        source_file="validator.c",
        include_files={"validator.h"}
    )
    
    test_code = generator.generate_test_file(test_func)
    print("Generated Test Code:")
    print("=" * 60)
    print(test_code)
