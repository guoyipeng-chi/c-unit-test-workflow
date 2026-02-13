#!/usr/bin/env python3
"""
Project Structure Verification Script
项目结构验证脚本
"""

import os
import sys
from pathlib import Path

def verify_project_structure(project_dir):
    """验证项目结构完整性"""
    
    print("=" * 70)
    print("  Project Structure Verification")
    print("=" * 70)
    print()
    
    project_path = Path(project_dir)
    
    # 定义必需的目录和文件
    required_dirs = [
        'include',
        'src', 
        'test',
        'tools',
        'cmake'
    ]
    
    required_files = [
        'CMakeLists.txt',
        'README.md',
        'ARCHITECTURE.md',
        'GETTING_STARTED.md',
        'main.py',
        'quickstart.py',
        'workflow.conf',
        'requirements.txt'
    ]
    
    required_tools = [
        'tools/c_code_analyzer.py',
        'tools/gtest_generator.py',
        'tools/test_executor.py',
        'tools/ut_workflow.py'
    ]
    
    required_src = [
        'include/database.h',
        'include/validator.h',
        'include/student_manager.h',
        'src/database.c',
        'src/validator.c',
        'src/student_manager.c'
    ]
    
    required_test = [
        'test/validator_test.cpp',
        'test/database_test.cpp',
        'test/student_manager_test.cpp'
    ]
    
    all_passed = True
    
    # 检查目录
    print("📁 Checking Directories:")
    for dir_name in required_dirs:
        dir_path = project_path / dir_name
        if dir_path.is_dir():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ (MISSING)")
            all_passed = False
    
    print()
    
    # 检查文件
    print("📄 Checking Files:")
    for file_name in required_files:
        file_path = project_path / file_name
        if file_path.is_file():
            size = file_path.stat().st_size
            print(f"  ✓ {file_name} ({size} bytes)")
        else:
            print(f"  ✗ {file_name} (MISSING)")
            all_passed = False
    
    print()
    
    # 检查工具
    print("🔧 Checking Tools:")
    for tool_file in required_tools:
        tool_path = project_path / tool_file
        if tool_path.is_file():
            lines = len(open(tool_path).readlines())
            print(f"  ✓ {tool_file} ({lines} lines)")
        else:
            print(f"  ✗ {tool_file} (MISSING)")
            all_passed = False
    
    print()
    
    # 检查源代码
    print("📝 Checking Source Code:")
    for src_file in required_src:
        src_path = project_path / src_file
        if src_path.is_file():
            lines = len(open(src_path).readlines())
            print(f"  ✓ {src_file} ({lines} lines)")
        else:
            print(f"  ✗ {src_file} (MISSING)")
            all_passed = False
    
    print()
    
    # 检查生成的测试
    print("🧪 Checking Generated Tests:")
    for test_file in required_test:
        test_path = project_path / test_file
        if test_path.is_file():
            lines = len(open(test_path).readlines())
            print(f"  ✓ {test_file} ({lines} lines)")
        else:
            print(f"  ✗ {test_file} (MISSING)")
            all_passed = False
    
    print()
    print("=" * 70)
    
    if all_passed:
        print("✓ All checks passed! Project structure is complete.")
        print()
        return True
    else:
        print("✗ Some checks failed. Please verify project structure.")
        print()
        return False


def main():
    if len(sys.argv) > 1:
        project_dir = sys.argv[1]
    else:
        project_dir = os.path.dirname(os.path.abspath(__file__))
    
    success = verify_project_structure(project_dir)
    
    if success:
        print("Next steps:")
        print("  1. python main.py --project . --info")
        print("  2. python main.py --project . --full")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
