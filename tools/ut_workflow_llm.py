#!/usr/bin/env python3
"""
UT Workflow with LLM (vLLM + Qwen3 Coder)
集成LLM的完整单元测试生成工作流
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional

# 添加tools目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from c_code_analyzer import CCodeAnalyzer
from compile_commands_analyzer import CompileCommandsAnalyzer
from llm_client import VLLMClient, create_client
from llm_test_generator import LLMTestGenerator


class LLMUTWorkflow:
    """集成LLM的UT生成工作流"""
    
    def __init__(self, project_dir: str, compile_commands_file: str,
                 llm_api_base: Optional[str] = None,
                 llm_model: Optional[str] = None):
        """
        初始化工作流
        
        配置优先级: 环境变量 > 参数 > 默认值
        
        Args:
            project_dir: 项目根目录
            compile_commands_file: compile_commands.json路径
            llm_api_base: vLLM API地址（可通过环境变量 VLLM_API_BASE 覆盖）
            llm_model: 模型名称（可通过环境变量 VLLM_MODEL 覆盖）
        """
        self.project_dir = project_dir
        self.include_dir = os.path.join(project_dir, 'include')
        self.src_dir = os.path.join(project_dir, 'src')
        self.test_dir = os.path.join(project_dir, 'test')
        
        # 初始化各组件
        self.code_analyzer = CCodeAnalyzer(self.include_dir, self.src_dir)
        
        # 解析compile_commands.json
        self.compile_analyzer = CompileCommandsAnalyzer(compile_commands_file)
        self.compile_analyzer.analyze_all()
        
        # 获取最终的API地址（环境变量优先）
        final_api_base = os.getenv('VLLM_API_BASE') or llm_api_base or "http://localhost:8000"
        final_model = os.getenv('VLLM_MODEL') or llm_model or "qwen-coder"
        
        # 初始化LLM客户端（VLLMClient内部也会检查环境变量）
        print(f"[Init] Connecting to vLLM at {final_api_base}...")
        self.llm_client = VLLMClient(api_base=final_api_base, model=final_model)
        
        # 初始化LLM测试生成器
        self.test_generator = LLMTestGenerator(self.llm_client)
    
    def analyze_codebase(self) -> None:
        """分析代码库"""
        print("\n[Step 1/4] Analyzing C codebase...")
        print("=" * 60)
        
        # 分析所有源文件
        for file in self.code_analyzer._extract_c_files(self.src_dir):
            self.code_analyzer.analyze_file(file)
        
        # 分析所有头文件
        for file in self.code_analyzer._extract_c_files(self.include_dir):
            if file.endswith('.h'):
                self.code_analyzer.analyze_file(file)
        
        functions = self.code_analyzer.get_all_functions()
        print(f"✓ Found {len(functions)} functions")
        
        for fname, fdep in list(functions.items())[:10]:
            print(f"  - {fdep.return_type} {fname}(...)")
            if fdep.external_calls:
                print(f"    Calls: {', '.join(sorted(list(fdep.external_calls)[:3]))}")
        
        if len(functions) > 10:
            print(f"  ... and {len(functions) - 10} more")
    
    def print_compile_info(self) -> None:
        """打印编译信息"""
        print("\n[Step 2/4] Extracting compile information...")
        print("=" * 60)
        
        self.compile_analyzer.print_summary()
    
    def generate_tests(self, target_functions: Optional[List[str]] = None,
                      output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        生成单元测试
        
        Args:
            target_functions: 目标函数名列表（None表示全部）
            output_dir: 输出目录
            
        Returns:
            {函数名: 测试代码}
        """
        print("\n[Step 3/4] Generating tests with LLM...")
        print("=" * 60)
        
        if output_dir is None:
            output_dir = self.test_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        functions = self.code_analyzer.get_all_functions()
        
        if target_functions:
            # 过滤目标函数
            targets = {
                name: func for name, func in functions.items()
                if name in target_functions
            }
            
            if not targets:
                print(f"✗ No matching functions found: {target_functions}")
                return {}
        else:
            targets = functions
        
        # 构建编译信息映射
        compile_info_map = {}
        for src_file, compile_info in self.compile_analyzer.compile_info.items():
            compile_info_map[src_file] = compile_info
        
        results = {}
        
        print(f"Generating tests for {len(targets)} functions...")
        for i, (fname, fdep) in enumerate(targets.items(), 1):
            print(f"\n[{i}/{len(targets)}] {fname}() from {fdep.source_file}")
            
            # 获取编译信息
            compile_info = compile_info_map.get(fdep.source_file)
            
            # 生成测试（传递项目根目录）
            test_code = self.test_generator.generate_test_file(
                fdep,
                compile_info=compile_info,
                project_root=self.project_dir
            )
            
            results[fname] = test_code
            
            # 保存到文件
            test_filename = os.path.join(output_dir, f"{fname}_llm_test.cpp")
            try:
                with open(test_filename, 'w', encoding='utf-8') as f:
                    f.write(test_code)
                print(f"  ✓ Saved to {test_filename}")
            except Exception as e:
                print(f"  ✗ Failed to save: {e}")
        
        return results
    
    def verify_tests(self, test_dir: Optional[str] = None) -> bool:
        """验证生成的测试（基本的语法检查）"""
        print("\n[Step 4/4] Verifying generated tests...")
        print("=" * 60)
        
        if test_dir is None:
            test_dir = self.test_dir
        
        test_files = [f for f in os.listdir(test_dir) if f.endswith('_llm_test.cpp')]
        
        if not test_files:
            print("No test files generated!")
            return False
        
        print(f"Found {len(test_files)} test files")
        
        # 基本的验证
        all_valid = True
        for test_file in test_files:
            filepath = os.path.join(test_dir, test_file)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查必要的包含
            has_gtest = '#include <gtest/gtest.h>' in content
            has_tests = 'TEST(' in content or 'TEST_F(' in content
            has_assertions = 'EXPECT_' in content or 'ASSERT_' in content
            
            if has_gtest and has_tests and has_assertions:
                print(f"  ✓ {test_file} - Valid")
            else:
                print(f"  ✗ {test_file} - Invalid (missing gtest={has_gtest}, tests={has_tests}, assertions={has_assertions})")
                all_valid = False
        
        return all_valid
    
    def show_workflow_info(self) -> None:
        """显示工作流信息"""
        print("\n[LLM-based Unit Test Generation Workflow]")
        print("=" * 60)
        print("""
This workflow uses:
1. Code Analyzer - Extract function signatures and dependencies
2. Compile Commands Parser - Extract compile flags and includes
3. vLLM + Qwen3 Coder - Generate comprehensive tests via LLM
4. Google Test (gtest) - Unit test framework

Workflow Steps:
1. Analyze C codebase - Parse functions and their dependencies
2. Extract compile info - Parse compile_commands.json
3. Generate tests - Use LLM to generate test code
4. Verify tests - Basic validation of generated tests

Usage:
  python ut_workflow_llm.py --help
""")
    
    def run_full_workflow(self, target_functions: Optional[List[str]] = None) -> None:
        """运行完整工作流"""
        self.show_workflow_info()
        self.analyze_codebase()
        self.print_compile_info()
        self.generate_tests(target_functions)
        self.verify_tests()
        
        print("\n" + "=" * 60)
        print("✓ Workflow completed!")


class CCodeAnalyzer:
    """扩展的代码分析器，添加文件查找功能"""
    
    def __init__(self, include_dir, src_dir):
        # 导入原始分析器
        from c_code_analyzer import CCodeAnalyzer as OrigAnalyzer
        self._analyzer = OrigAnalyzer(include_dir, src_dir)
        
        # 复制属性
        self.__dict__.update(self._analyzer.__dict__)
    
    def _extract_c_files(self, directory: str) -> List[str]:
        """提取目录中的C/H文件"""
        files = []
        for ext in ['*.c', '*.h']:
            for file in Path(directory).glob(ext):
                files.append(str(file))
        return files
    
    def get_all_functions(self):
        """获取所有函数"""
        return self._analyzer.function_map
    
    def analyze_file(self, filepath):
        """分析文件"""
        return self._analyzer.analyze_file(filepath)


def main():
    parser = argparse.ArgumentParser(
        description="LLM-based C Unit Test Generation Workflow"
    )
    
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project root directory"
    )
    
    parser.add_argument(
        "--compile-commands",
        default="build/compile_commands.json",
        help="Path to compile_commands.json"
    )
    
    parser.add_argument(
        "--llm-api",
        default=None,
        help="vLLM API base URL (优先级: 环境变量 VLLM_API_BASE > 命令行 > 默认localhost:8000). "
             "示例: http://192.168.1.100:8000 或 http://your-server.com:8000"
    )
    
    parser.add_argument(
        "--llm-model",
        default=None,
        help="LLM model name (环境变量: VLLM_MODEL, 默认: qwen-coder)"
    )
    
    parser.add_argument(
        "--functions",
        nargs="+",
        help="Target functions to generate tests for"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Output directory for generated tests"
    )
    
    parser.add_argument(
        "--info-only",
        action="store_true",
        help="Only show workflow information"
    )
    
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze codebase"
    )
    
    args = parser.parse_args()
    
    # 检查文件存在
    if not os.path.exists(args.compile_commands):
        print(f"✗ compile_commands.json not found: {args.compile_commands}")
        print("  Please run: cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON <project_root>")
        sys.exit(1)
    
    # 创建工作流
    try:
        workflow = LLMUTWorkflow(
            project_dir=args.project_dir,
            compile_commands_file=args.compile_commands,
            llm_api_base=args.llm_api,
            llm_model=args.llm_model
        )
    except Exception as e:
        print(f"✗ Failed to initialize workflow: {e}")
        sys.exit(1)
    
    if args.info_only:
        workflow.show_workflow_info()
    elif args.analyze_only:
        workflow.analyze_codebase()
        workflow.print_compile_info()
    else:
        workflow.run_full_workflow(target_functions=args.functions)


if __name__ == "__main__":
    main()
