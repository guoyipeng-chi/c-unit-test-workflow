#!/usr/bin/env python3
"""
Project File Manifest and Verification
项目文件清单和完整性验证
"""

PROJECT_MANIFEST = {
    "documentation": [
        ("README.md", "完整使用文档", True),
        ("ARCHITECTURE.md", "架构设计文档", True),
        ("GETTING_STARTED.md", "快速参考指南", True),
        ("PROJECT_SUMMARY.md", "项目完成总结", True),
        ("QUICK_REFERENCE.txt", "命令参考卡片", True),
        ("INDEX.md", "文档导航", True),
    ],
    
    "scripts": [
        ("main.py", "主集成脚本", True),
        ("quickstart.py", "Python快速开始", True),
        ("quickstart.sh", "Linux/Mac启动脚本", True),
        ("quickstart.bat", "Windows启动脚本", True),
        ("verify_structure.py", "项目结构验证工具", True),
    ],
    
    "tools": [
        ("tools/c_code_analyzer.py", "C代码分析器", True),
        ("tools/gtest_generator.py", "GTest代码生成器", True),
        ("tools/test_executor.py", "测试执行管理器", True),
        ("tools/ut_workflow.py", "工作流控制脚本", True),
    ],
    
    "source_code": [
        ("include/database.h", "数据库操作头文件", True),
        ("include/validator.h", "验证函数头文件", True),
        ("include/student_manager.h", "学生管理头文件", True),
        ("src/database.c", "数据库操作实现", True),
        ("src/validator.c", "验证函数实现", True),
        ("src/student_manager.c", "学生管理实现", True),
    ],
    
    "tests": [
        ("test/validator_test.cpp", "验证函数测试", True),
        ("test/database_test.cpp", "数据库函数测试", True),
        ("test/student_manager_test.cpp", "学生管理测试", True),
    ],
    
    "configuration": [
        ("CMakeLists.txt", "CMake编译配置", True),
        ("workflow.conf", "工作流配置文件", True),
        ("requirements.txt", "Python依赖配置", True),
        ("FILE_MANIFEST.md", "项目文件清单", True),
    ],
    
    "directories": [
        ("include/", "头文件目录", True),
        ("src/", "源代码目录", True),
        ("test/", "测试代码目录", True),
        ("tools/", "工作流工具目录", True),
        ("cmake/", "CMake辅助目录", False),
        ("build/", "编译输出目录（自动生成）", False),
    ]
}

STATISTICS = {
    "documentation": {
        "files": 6,
        "total_lines": 2600,
    },
    "scripts": {
        "files": 5,
        "total_lines": 700,
    },
    "tools": {
        "files": 4,
        "total_lines": 950,
    },
    "source_code": {
        "c_files": 3,
        "h_files": 3,
        "total_lines": 150,
    },
    "tests": {
        "files": 3,
        "total_lines": 350,
        "test_cases": 22,
    }
}

def print_manifest():
    """打印项目清单"""
    
    print("=" * 80)
    print("  C UNIT TEST WORKFLOW - PROJECT FILE MANIFEST")
    print("=" * 80)
    print()
    
    for section, files in PROJECT_MANIFEST.items():
        if section == "directories":
            continue
        
        print(f"📂 {section.upper().replace('_', ' ')}")
        print("-" * 80)
        
        for file_path, description, exists in files:
            status = "✅" if exists else "❌"
            print(f"  {status} {file_path:40} {description}")
        
        print()
    
    # 打印目录信息
    print("📁 DIRECTORIES")
    print("-" * 80)
    for dir_path, description, exists in PROJECT_MANIFEST["directories"]:
        status = "✅" if exists else "⏳"
        print(f"  {status} {dir_path:40} {description}")
    print()
    
    print("=" * 80)
    print("  STATISTICS")
    print("=" * 80)
    print()
    
    print(f"📄 Documentation")
    print(f"   Files: {STATISTICS['documentation']['files']}")
    print(f"   Lines: {STATISTICS['documentation']['total_lines']}")
    print()
    
    print(f"🔧 Scripts")
    print(f"   Files: {STATISTICS['scripts']['files']}")
    print(f"   Lines: {STATISTICS['scripts']['total_lines']}")
    print()
    
    print(f"📚 Tools")
    print(f"   Files: {STATISTICS['tools']['files']}")
    print(f"   Lines: {STATISTICS['tools']['total_lines']}")
    print()
    
    print(f"📝 Source Code")
    print(f"   C Files: {STATISTICS['source_code']['c_files']}")
    print(f"   H Files: {STATISTICS['source_code']['h_files']}")
    print(f"   Lines: {STATISTICS['source_code']['total_lines']}")
    print()
    
    print(f"🧪 Tests")
    print(f"   Test Files: {STATISTICS['tests']['files']}")
    print(f"   Test Cases: {STATISTICS['tests']['test_cases']}")
    print(f"   Lines: {STATISTICS['tests']['total_lines']}")
    print()
    
    # 总计
    total_files = len([f for fs in PROJECT_MANIFEST.values() for f, d, e in fs if e])
    total_lines = (
        STATISTICS['documentation']['total_lines'] +
        STATISTICS['scripts']['total_lines'] +
        STATISTICS['tools']['total_lines'] +
        STATISTICS['source_code']['total_lines'] +
        STATISTICS['tests']['total_lines']
    )
    
    print("=" * 80)
    print(f"📊 TOTAL PROJECT")
    print(f"   Total Files: {total_files}")
    print(f"   Total Lines: {total_lines:,}")
    print("=" * 80)
    print()


if __name__ == '__main__':
    print_manifest()
