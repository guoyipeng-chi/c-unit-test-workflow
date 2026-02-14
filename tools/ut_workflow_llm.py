#!/usr/bin/env python3
"""
UT Workflow with LLM (vLLM + Qwen3 Coder)
集成LLM的完整单元测试生成工作流
"""

import sys
import os
import argparse
import json
import subprocess
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
                 test_output_dir: Optional[str] = None,
                 include_dir: Optional[str] = None,
                 src_dir: Optional[str] = None,
                 llm_api_base: Optional[str] = None,
                 llm_model: Optional[str] = None):
        """
        初始化工作流
        
        配置优先级: 环境变量 > 参数 > 默认值
        
        Args:
            project_dir: 项目根目录
            compile_commands_file: compile_commands.json路径
            test_output_dir: 测试输出目录（相对于project_dir，默认'test'）
            include_dir: 头文件目录（相对于project_dir，默认'include'）
            src_dir: 源文件目录（相对于project_dir，默认'src'）
            llm_api_base: vLLM API地址（可通过环境变量 VLLM_API_BASE 覆盖）
            llm_model: 模型名称（可通过环境变量 VLLM_MODEL 覆盖）
        """
        self.project_dir = os.path.abspath(project_dir)
        
        # 使用提供的目录或默认值
        self.include_dir = os.path.join(self.project_dir, include_dir or 'include')
        self.src_dir = os.path.join(self.project_dir, src_dir or 'src')
        self.test_dir = os.path.join(self.project_dir, test_output_dir or 'test')
        
        # 确保输出目录存在
        os.makedirs(self.test_dir, exist_ok=True)
        
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
    
    @classmethod
    def from_config(cls, config_file: str, 
                   project_root_override: Optional[str] = None,
                   compile_commands_override: Optional[str] = None) -> 'LLMUTWorkflow':
        """
        从配置文件创建工作流实例
        
        Args:
            config_file: llm_workflow_config.json 路径
            project_root_override: 覆盖配置文件中的项目根路径
            compile_commands_override: 覆盖compile_commands.json的搜索位置
            
        Returns:
            LLMUTWorkflow 实例
            
        示例:
            # 使用配置文件
            workflow = LLMUTWorkflow.from_config('llm_workflow_config.json')
            
            # 覆盖某些配置
            workflow = LLMUTWorkflow.from_config(
                'llm_workflow_config.json',
                project_root_override='/path/to/my-project'
            )
        """
        config_path = Path(config_file).absolute()
        config_dir = config_path.parent
        
        # 加载配置文件
        with open(config_path) as f:
            config = json.load(f)
        
        # 获取路径配置
        paths_config = config.get('paths', {})
        
        # 确定项目根目录
        project_root = project_root_override
        if not project_root:
            project_root = paths_config.get('project_root', '.')
            # 如果是相对路径，相对于配置文件所在目录
            if not os.path.isabs(project_root):
                project_root = os.path.join(config_dir, project_root)
        
        project_root = os.path.abspath(project_root)
        
        # 获取其他路径配置
        test_output_dir = paths_config.get('test_output_dir', 'test')
        include_dir = paths_config.get('include_dir', 'include')
        src_dir = paths_config.get('src_dir', 'src')
        
        # 确定compile_commands.json位置
        if compile_commands_override:
            compile_commands_file = compile_commands_override
        else:
            compile_commands_paths = config.get('compile_commands', {}).get('search_paths', [])
            compile_commands_file = None
            
            for search_path in compile_commands_paths:
                # 如果是相对路径，相对于项目根目录
                if not os.path.isabs(search_path):
                    full_path = os.path.join(project_root, search_path)
                else:
                    full_path = search_path
                
                if os.path.exists(full_path):
                    compile_commands_file = full_path
                    break
            
            if not compile_commands_file:
                raise FileNotFoundError(
                    f"Cannot find compile_commands.json in search paths: {compile_commands_paths}\n"
                    f"Project root: {project_root}"
                )
        
        # 获取LLM配置
        llm_config = config.get('llm', {})
        llm_api_base = llm_config.get('api_base', 'http://localhost:8000')
        llm_model = llm_config.get('model', 'qwen-coder')
        
        print(f"[Config] Loading from: {config_path}")
        print(f"[Config] Project root: {project_root}")
        print(f"[Config] Compile commands: {compile_commands_file}")
        print(f"[Config] Test output dir: {test_output_dir}")
        
        return cls(
            project_dir=project_root,
            compile_commands_file=compile_commands_file,
            test_output_dir=test_output_dir,
            include_dir=include_dir,
            src_dir=src_dir,
            llm_api_base=llm_api_base,
            llm_model=llm_model
        )
    
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
    
    def run_tests(self, test_dir: Optional[str] = None, build_dir: str = "build-test") -> bool:
        """
        编译并执行生成的测试用例
        
        Args:
            test_dir: 测试文件所在目录
            build_dir: 测试编译目录
            
        Returns:
            是否执行成功
        """
        print("\n[Step 5/5] Compiling and running tests...")
        print("=" * 60)
        
        if test_dir is None:
            test_dir = self.test_dir
        
        test_files = [f for f in os.listdir(test_dir) if f.endswith('_llm_test.cpp')]
        
        if not test_files:
            print("✗ No test files found to run!")
            return False
        
        print(f"Found {len(test_files)} test file(s) to run")
        
        # 创建编译目录
        build_path = os.path.join(self.project_dir, build_dir)
        os.makedirs(build_path, exist_ok=True)
        
        # 使用CMake配置建立测试编译环境
        print(f"\nSetting up CMake for tests in {build_path}...")
        
        try:
            # 运行CMake配置
            cmake_result = subprocess.run(
                ["cmake", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-S", self.project_dir, "-B", build_path],
                capture_output=True,
                timeout=60,
                text=True
            )
            
            if cmake_result.returncode != 0:
                print("⚠ CMake configuration had issues, but continuing...")
                if cmake_result.stderr:
                    print(f"  Error: {cmake_result.stderr[:500]}")
            else:
                print("✓ CMake configured successfully")
        except Exception as e:
            print(f"⚠ CMake configuration failed: {e}")
            print("  Attempting to run tests anyway...")
        
        # 收集源文件进行编译
        source_files = []
        for root, dirs, files in os.walk(self.src_dir):
            for file in files:
                if file.endswith('.c'):
                    source_files.append(os.path.join(root, file))
        
        print(f"Found {len(source_files)} source file(s)")
        
        # 尝试编译并运行每个测试文件
        all_passed = True
        results = []
        
        for test_file in test_files:
            test_path = os.path.join(test_dir, test_file)
            test_name = os.path.splitext(test_file)[0]
            exe_path = os.path.join(build_path, test_name)
            
            print(f"\n[Test] {test_file}")
            print("-" * 40)
            
            # 构建编译命令
            # 收集include目录
            include_dirs = ["-I" + self.include_dir]
            
            # 从compile_commands.json中提取include路径
            if hasattr(self.compile_analyzer, 'compile_info'):
                for src_file, compile_info in self.compile_analyzer.compile_info.items():
                    if 'includes' in compile_info:
                        for inc in compile_info['includes']:
                            if inc not in include_dirs:
                                include_dirs.append("-I" + inc)
            
            # 准备编译命令
            compile_cmd = ["g++", "-std=c99", "-o", exe_path]
            compile_cmd.extend(include_dirs)
            compile_cmd.append("-I/usr/include/gtest")
            compile_cmd.extend(source_files)
            compile_cmd.append(test_path)
            compile_cmd.extend(["-lgtest", "-lgtest_main", "-lpthread"])
            
            try:
                # 编译测试
                print(f"Compiling: {test_name}...")
                compile_result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    timeout=120,
                    text=True,
                    cwd=self.project_dir
                )
                
                if compile_result.returncode != 0:
                    print(f"  ✗ Compilation failed")
                    if compile_result.stderr:
                        # 只显示前几行错误信息
                        error_lines = compile_result.stderr.split('\n')[:5]
                        for line in error_lines:
                            if line.strip():
                                print(f"    {line}")
                        if len(compile_result.stderr.split('\n')) > 5:
                            print(f"    ... (more errors)")
                    all_passed = False
                    results.append((test_name, "COMPILE_FAILED"))
                    continue
                
                print(f"  ✓ Compiled successfully")
                
                # 运行测试
                print(f"Running: {test_name}...")
                run_result = subprocess.run(
                    [exe_path],
                    capture_output=True,
                    timeout=60,
                    text=True,
                    cwd=self.project_dir
                )
                
                # 解析GTest输出
                if run_result.returncode == 0:
                    print(f"  ✓ All tests passed")
                    results.append((test_name, "PASSED"))
                    
                    # 显示简要的测试统计
                    output_lines = run_result.stderr.split('\n')
                    for line in output_lines:
                        if 'passed' in line.lower() or 'ok' in line.lower():
                            print(f"    {line.strip()}")
                else:
                    print(f"  ✗ Some tests failed")
                    results.append((test_name, "FAILED"))
                    all_passed = False
                    
                    # 显示失败信息
                    if run_result.stderr:
                        error_lines = run_result.stderr.split('\n')
                        for line in error_lines:
                            if 'FAILED' in line or 'ERROR' in line or 'failed' in line:
                                print(f"    {line.strip()}")
            
            except subprocess.TimeoutExpired:
                print(f"  ✗ Test execution timeout")
                results.append((test_name, "TIMEOUT"))
                all_passed = False
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append((test_name, "ERROR"))
                all_passed = False
        
        # 显示总结
        print("\n" + "=" * 60)
        print("Test Execution Summary")
        print("=" * 60)
        
        for test_name, status in results:
            status_symbol = "✓" if status == "PASSED" else "✗"
            print(f"{status_symbol} {test_name:<40} {status}")
        
        if all_passed:
            print("\n✓ All tests executed successfully!")
        else:
            print("\n⚠ Some tests failed or couldn't run")
        
        return all_passed

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
5. Run tests - Compile and execute tests with GTest

Usage:
  python ut_workflow_llm.py --help
""")
    
    def run_full_workflow(self, target_functions: Optional[List[str]] = None, skip_run: bool = False) -> None:
        """
        运行完整工作流
        
        Args:
            target_functions: 目标函数列表
            skip_run: 是否跳过测试执行步骤
        """
        self.show_workflow_info()
        self.analyze_codebase()
        self.print_compile_info()
        self.generate_tests(target_functions)
        self.verify_tests()
        
        if not skip_run:
            self.run_tests()
        
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
        "--config",
        help="Load from configuration file (llm_workflow_config.json)"
    )
    
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project root directory (覆盖config中的设置)"
    )
    
    parser.add_argument(
        "--compile-commands",
        default="build/compile_commands.json",
        help="Path to compile_commands.json (覆盖config中的设置)"
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
    
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip running tests (only generate, don't execute)"
    )
    
    args = parser.parse_args()
    
    # 优先从配置文件加载
    if args.config:
        try:
            print(f"[Config] Loading from: {args.config}")
            workflow = LLMUTWorkflow.from_config(
                args.config,
                project_root_override=args.project_dir if args.project_dir != "." else None,
                compile_commands_override=args.compile_commands if args.compile_commands != "build/compile_commands.json" else None
            )
        except Exception as e:
            print(f"✗ Failed to load config: {e}")
            sys.exit(1)
    else:
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
        workflow.run_full_workflow(
            target_functions=args.functions,
            skip_run=args.skip_run
        )


if __name__ == "__main__":
    main()
