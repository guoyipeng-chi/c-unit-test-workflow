#!/usr/bin/env python3
"""
C Unit Test Workflow - Master Integration Script
统一入口脚本 - 整合所有步骤
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# 添加tools路径
tools_dir = os.path.join(os.path.dirname(__file__), 'tools')
sys.path.insert(0, tools_dir)

from ut_workflow import UTWorkflow
from test_executor import TestExecutor


class MasterWorkflow:
    """主工作流程管理类"""
    
    def __init__(self, project_dir: str):
        self.project_dir = os.path.abspath(project_dir)
        self.workflow = UTWorkflow(self.project_dir)
        self.executor = TestExecutor(self.project_dir)
    
    def run_full_workflow(self, target_func: str = None) -> bool:
        """运行完整的工作流程"""
        print("=" * 70)
        print("  C Language Unit Test Generation Workflow - Full Pipeline")
        print("=" * 70)
        
        # 步骤1: 分析代码
        print("\n[Step 1/4] Code Analysis")
        print("-" * 70)
        self.workflow.run_analysis()
        
        # 步骤2: 生成测试代码
        print("\n[Step 2/4] Test Code Generation")
        print("-" * 70)
        self.workflow.generate_tests(target_func)
        
        # 步骤3: 编译测试
        print("\n[Step 3/4] Building Tests")
        print("-" * 70)
        if not self.executor.build_tests():
            print("\n✗ Build failed!")
            return False
        
        # 步骤4: 执行测试
        print("\n[Step 4/4] Running Tests")
        print("-" * 70)
        results = self.executor.run_tests()
        success = self.executor.print_summary(results)
        
        return success
    
    def run_analysis_only(self, show_list: bool = False) -> None:
        """只运行分析"""
        self.workflow.run_analysis()
        if show_list:
            self.workflow.list_functions()
    
    def run_generate_only(self, target_func: str = None) -> None:
        """只运行代码生成"""
        self.workflow.run_analysis()
        self.workflow.generate_tests(target_func)
    
    def run_build_only(self) -> bool:
        """只编译"""
        return self.executor.build_tests()
    
    def run_test_only(self) -> bool:
        """只运行测试"""
        results = self.executor.run_tests()
        return self.executor.print_summary(results)
    
    def run_build_and_test(self) -> bool:
        """编译并运行测试"""
        print("\n[Step 3/4] Building Tests")
        print("-" * 70)
        if not self.executor.build_tests():
            return False
        
        print("\n[Step 4/4] Running Tests")
        print("-" * 70)
        results = self.executor.run_tests()
        return self.executor.print_summary(results)


def create_arg_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='C Unit Test Generation Workflow - Master Controller',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full workflow (analyze + generate + build + run)
  python main.py --project . --full

  # Only analyze code
  python main.py --project . --analyze --list

  # Generate tests for specific function
  python main.py --project . --generate --target validate_score

  # Build and run tests
  python main.py --project . --build-and-run

  # Run existing tests
  python main.py --project . --run
        """
    )
    
    parser.add_argument('--project', required=True,
                       help='Project root directory')
    
    # Main operations
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--full', action='store_true',
                      help='Run full workflow (analyze + generate + build + run)')
    group.add_argument('--analyze', action='store_true',
                      help='Analysis only')
    group.add_argument('--generate', action='store_true',
                      help='Generate tests only')
    group.add_argument('--build', action='store_true',
                      help='Build tests only')
    group.add_argument('--run', action='store_true',
                      help='Run tests only')
    group.add_argument('--build-and-run', action='store_true',
                      help='Build and run tests')
    group.add_argument('--info', action='store_true',
                      help='Show workflow information')
    
    # Additional options
    parser.add_argument('--list', action='store_true',
                       help='List all functions (with --analyze)')
    parser.add_argument('--target', type=str,
                       help='Target function name (with --generate)')
    
    return parser


def main():
    # 解析参数
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # 验证项目目录
    if not os.path.isdir(args.project):
        print(f"✗ Project directory not found: {args.project}")
        sys.exit(1)
    
    # 创建工作流实例
    master = MasterWorkflow(args.project)
    
    # 执行对应操作
    try:
        if args.full:
            success = master.run_full_workflow(args.target)
            sys.exit(0 if success else 1)
        
        elif args.info:
            master.workflow.show_workflow_info()
        
        elif args.analyze:
            master.run_analysis_only(args.list)
        
        elif args.generate:
            master.run_generate_only(args.target)
        
        elif args.build:
            success = master.run_build_only()
            sys.exit(0 if success else 1)
        
        elif args.run:
            success = master.run_test_only()
            sys.exit(0 if success else 1)
        
        elif args.build_and_run:
            success = master.run_build_and_test()
            sys.exit(0 if success else 1)
        
        else:
            # 默认运行完整工作流
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\n✗ Workflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Workflow error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
