#!/usr/bin/env python3
"""
Quick Start Script - 快速开始脚本
这个脚本演示如何使用完整的工作流程
"""

import os
import sys
import subprocess
from pathlib import Path


def print_banner(title):
    """打印横幅"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def run_example_workflow():
    """运行示例工作流"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = script_dir
    
    print_banner("C语言单元测试工作流 - 完整演示")
    
    print("""
这个脚本将演示以下步骤：
1. 分析项目中的所有C代码文件
2. 生成对应的Gtest测试代码  
3. 编译测试代码（需要cmake和编译器）
4. 执行测试用例
5. 显示测试执行结果

开始演示...
    """)
    
    # 使用main.py运行完整工作流
    main_script = os.path.join(script_dir, 'main.py')
    
    try:
        # 运行完整工作流
        result = subprocess.run(
            [sys.executable, main_script, '--project', project_dir, '--full'],
            timeout=300
        )
        
        if result.returncode == 0:
            print_banner("✓ 演示完成 - 所有测试通过！")
        else:
            print_banner("⚠ 演示完成 - 但有一些测试失败")
        
        print("""
下一步操作：

1. 查看生成的测试代码：
   ls test/*_test.cpp

2. 修改Mock定义：
   编辑 test/*_test.cpp 文件中的:
   /* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

3. 添加自定义测试用例：
   在生成的测试文件中添加新的TEST_F宏

4. 重新编译和运行：
   python main.py --project . --build-and-run

5. 查看具体支持的命令：
   python main.py --info
        """)
        
        return result.returncode == 0
    
    except subprocess.TimeoutExpired:
        print_banner("✗ 演示超时")
        return False
    except Exception as e:
        print_banner(f"✗ 演示失败: {e}")
        return False


def print_usage():
    """打印使用说明"""
    print_banner("快速开始指南")
    
    print("""
📋 命令行使用:

# 完整工作流 (推荐)
python main.py --project . --full

# 仅分析代码
python main.py --project . --analyze --list

# 生成所有测试
python main.py --project . --generate

# 生成特定函数的测试
python main.py --project . --generate --target validate_score

# 编译并运行测试
python main.py --project . --build-and-run

# 查看所有可用命令
python main.py --help

# 查看工作流信息
python main.py --project . --info

═══════════════════════════════════════════════════════════════

📁 项目结构:

src/            - C源代码文件
include/        - C头文件
test/           - 生成的测试代码
tools/          - 工作流脚本
  ├── ut_workflow.py      - 代码分析和测试生成
  ├── test_executor.py    - 编译和执行测试
  ├── c_code_analyzer.py  - C代码分析模块
  └── gtest_generator.py  - Gtest代码生成

CMakeLists.txt  - CMake配置文件
main.py         - 主集成脚本
README.md       - 详细文档

═══════════════════════════════════════════════════════════════
    """)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Quick Start Guide for C Unit Test Workflow'
    )
    parser.add_argument('--demo', action='store_true',
                       help='Run demonstration workflow')
    parser.add_argument('--help-usage', action='store_true',
                       help='Print usage guide')
    
    args = parser.parse_args()
    
    if args.demo or not sys.argv[1:]:
        success = run_example_workflow()
        sys.exit(0 if success else 1)
    elif args.help_usage:
        print_usage()
    else:
        parser.print_help()
