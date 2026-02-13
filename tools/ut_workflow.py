#!/usr/bin/env python3
"""
C Unit Test Generation Workflow
主要工作流程脚本
"""

import sys
import os
import argparse
import json
from pathlib import Path

# 添加tools目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from c_code_analyzer import CCodeAnalyzer
from gtest_generator import GTestGenerator


class UTWorkflow:
    """单元测试生成工作流"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.include_dir = os.path.join(project_dir, 'include')
        self.src_dir = os.path.join(project_dir, 'src')
        self.test_dir = os.path.join(project_dir, 'test')
        
        self.analyzer = CCodeAnalyzer(self.include_dir, self.src_dir)
        self.generator = GTestGenerator()
    
    def run_analysis(self) -> None:
        """运行代码分析"""
        print("[1/4] Analyzing C code structure...")
        self.analyzer.analyze_directory()
        
        functions = self.analyzer.get_all_functions()
        print(f"  ✓ Found {len(functions)} functions")
        for fname, fdep in functions.items():
            print(f"    - {fdep.return_type} {fname}(...)")
            if fdep.external_calls:
                print(f"      Calls: {', '.join(sorted(fdep.external_calls))}")
    
    def generate_tests(self, target_func: str = None) -> None:
        """生成测试代码"""
        print("\n[2/4] Generating test code...")
        
        functions = self.analyzer.get_all_functions()
        
        if target_func:
            if target_func not in functions:
                print(f"  ✗ Function '{target_func}' not found")
                return
            targets = {target_func: functions[target_func]}
        else:
            targets = functions
        
        for fname, fdep in targets.items():
            test_code = self.generator.generate_test_file(fdep, fname)
            test_filename = os.path.join(self.test_dir, f"{fname}_test.cpp")
            
            with open(test_filename, 'w', encoding='utf-8') as f:
                f.write(test_code)
            
            print(f"  ✓ Generated: {fname}_test.cpp")
    
    def list_functions(self) -> None:
        """列表显示所有函数"""
        print("\n[Analysis Results]")
        print("=" * 60)
        
        functions = self.analyzer.get_all_functions()
        
        if not functions:
            print("No functions found!")
            return
        
        for fname, fdep in sorted(functions.items()):
            print(f"\nFunction: {fname}")
            print(f"  Return Type: {fdep.return_type}")
            print(f"  Source File: {fdep.source_file}")
            print(f"  Parameters:")
            if fdep.parameters:
                for ptype, pname in fdep.parameters:
                    print(f"    - {ptype} {pname}")
            else:
                print(f"    - void")
            
            if fdep.external_calls:
                print(f"  External Calls (需要Mock):")
                for call in sorted(fdep.external_calls):
                    print(f"    - {call}()")
            else:
                print(f"  External Calls: None")
            
            print(f"  Dependencies:")
            for inc in sorted(fdep.include_files):
                print(f"    - {inc}")
    
    def show_workflow_info(self) -> None:
        """显示工作流信息"""
        print("""
╔════════════════════════════════════════════════════════════════╗
║     C Unit Test Workflow - 工作流程说明                        ║
╚════════════════════════════════════════════════════════════════╝

📋 工作流程步骤:

1️⃣  代码分析阶段
   • 扫描include/和src/目录中的所有C/H文件
   • 提取函数签名、返回类型、参数列表
   • 分析函数间的依赖关系（函数调用关系）
   • 识别需要Mock的外部调用

2️⃣  测试代码生成阶段
   • 为每个公共函数生成gtest测试文件
   • 自动生成Mock宏定义（在文件头部高亮显示）
   • 生成Test Fixture类
   • 生成标准的AAA测试用例模板（Arrange-Act-Assert）

3️⃣  编译构建阶段
   • 使用CMake编译生成的测试代码
   • 链接gtest框架和待测试源文件

4️⃣  执行验证阶段
   • 运行生成的测试用例
   • 自动分析测试结果
   • 生成覆盖率报告（可选）

═══════════════════════════════════════════════════════════════

🔑 关键特性:

✓ Mock管理
  - 所有Mock定义集中在测试文件头部
  - 以宏的形式显示，便于后续修改
  - 示例: /* ========== MOCK DEFINITIONS ========== */

✓ 自动生成三类测试用例
  - 正常情况: 测试正常执行路径
  - 边界情况: 测试边界条件
  - 异常情况: 测试错误处理

✓ 测试断言自动化
  - 基于函数返回类型自动生成预期值
  - 支持int、float、void等基本类型
  - 可根据实际执行结果调整

═══════════════════════════════════════════════════════════════

📝 使用方法:

1. 分析项目代码:
   python util_workflow.py --project . --analyze

2. 查看所有函数:
   python util_workflow.py --project . --list

3. 生成所有测试:
   python util_workflow.py --project . --generate

4. 生成特定函数的测试:
   python util_workflow.py --project . --generate --target validate_score

═══════════════════════════════════════════════════════════════
        """)


def main():
    parser = argparse.ArgumentParser(
        description='C Unit Test Generation Workflow'
    )
    parser.add_argument('--project', required=True, 
                       help='Project root directory')
    parser.add_argument('--analyze', action='store_true',
                       help='Run code analysis only')
    parser.add_argument('--generate', action='store_true',
                       help='Generate test files')
    parser.add_argument('--target', type=str,
                       help='Target function name for test generation')
    parser.add_argument('--list', action='store_true',
                       help='List all functions found')
    parser.add_argument('--info', action='store_true',
                       help='Show workflow information')
    
    args = parser.parse_args()
    
    # 验证项目目录
    if not os.path.isdir(args.project):
        print(f"✗ Project directory not found: {args.project}")
        sys.exit(1)
    
    workflow = UTWorkflow(args.project)
    
    if args.info:
        workflow.show_workflow_info()
        return
    
    # 总是先做分析
    workflow.run_analysis()
    
    if args.list:
        workflow.list_functions()
    
    if args.generate:
        workflow.generate_tests(args.target)
    
    # 如果没有指定任何操作，显示帮助
    if not (args.analyze or args.list or args.generate or args.info):
        parser.print_help()


if __name__ == '__main__':
    main()
