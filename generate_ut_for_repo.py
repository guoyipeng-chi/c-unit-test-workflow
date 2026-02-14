#!/usr/bin/env python3
"""
针对真实项目生成UT的便捷工具
Select a real project and generate UT for it
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional


class UTGenerator:
    """单元测试生成器"""
    
    def __init__(self):
        self.current_dir = Path.cwd()
        self.workflow_dir = Path(__file__).parent
        self.config_file = self.workflow_dir / "llm_workflow_config.json"
    
    def setup_from_config(self) -> bool:
        """
        从配置文件设置项目
        
        Returns:
            是否成功
        """
        if not self.config_file.exists():
            print(f"✗ 配置文件不存在: {self.config_file}")
            return False
        
        print("\n" + "=" * 70)
        print("【UT生成工具】 从配置文件加载项目")
        print("=" * 70)
        print(f"\n使用配置文件: {self.config_file}")
        
        # 加载配置
        with open(self.config_file) as f:
            config = json.load(f)
        
        paths_config = config.get('paths', {})
        project_root = paths_config.get('project_root', '.')
        
        # 如果是相对路径，相对于config文件的目录
        if not os.path.isabs(project_root):
            project_root = os.path.join(self.workflow_dir, project_root)
        
        project_root = os.path.abspath(project_root)
        
        print(f"项目路径: {project_root}")
        print(f"测试输出目录: {paths_config.get('test_output_dir', 'test')}")
        
        if not os.path.exists(project_root):
            print(f"✗ 项目路径不存在: {project_root}")
            return False
        
        return self.setup_project(project_root)
        
    def setup_project(self, project_path: str) -> bool:
        """
        为项目设置UT生成环境
        
        Args:
            project_path: 目标项目路径
            
        Returns:
            是否成功
        """
        project = Path(project_path).absolute()
        
        print("\n" + "=" * 70)
        print("【UT生成工具】 Real Project UT Generator")
        print("=" * 70)
        
        # 1. 验证项目结构
        print("\n[Step 1/5] 验证项目结构...")
        if not self._validate_project(project):
            print("✗ 项目结构不符合要求")
            return False
        
        # 2. 生成/检查 compile_commands.json
        print("\n[Step 2/5] 生成compile_commands.json...")
        compile_commands = self._generate_compile_commands(project)
        if not compile_commands:
            print("✗ 无法生成compile_commands.json")
            return False
        print(f"✓ compile_commands.json: {compile_commands}")
        
        # 3. 创建测试目录
        print("\n[Step 3/5] 创建测试输出目录...")
        test_dir = project / "test"
        test_dir.mkdir(exist_ok=True)
        print(f"✓ 测试目录: {test_dir}")
        
        # 4. 分析代码库
        print("\n[Step 4/5] 分析代码库...")
        functions = self._analyze_codebase(project, compile_commands)
        if not functions:
            print("✗ 没有找到可测试的函数")
            return False
        print(f"✓ 找到 {len(functions)} 个函数：")
        for i, func in enumerate(functions[:10], 1):
            print(f"   {i}. {func}")
        if len(functions) > 10:
            print(f"   ... 还有 {len(functions) - 10} 个")
        
        # 5. 显示下一步操作
        print("\n[Step 5/5] 准备开始生成UT...")
        print("\n" + "=" * 70)
        print("✓ 项目已准备就绪！")
        print("=" * 70)
        
        print("\n【选择一个选项】")
        print("=" * 70)
        options = {
            "1": ("生成所有函数的UT", self._generate_all, (project, compile_commands)),
            "2": ("为特定函数生成UT", self._generate_specific, (project, compile_commands, functions)),
            "3": ("分析函数依赖关系", self._analyze_dependencies, (project,)),
            "4": ("预览LLM Prompt", self._preview_prompt, (project,)),
            "q": ("退出", None, None),
        }
        
        for key, (desc, _, _) in options.items():
            print(f"  [{key}] {desc}")
        
        choice = input("\n请选择 (1-4, q退出): ").strip().lower()
        
        if choice == "q":
            return True
        
        if choice in options:
            desc, func, args = options[choice]
            if func:
                print(f"\n正在执行: {desc}...")
                return func(*args)
        
        print("✗ 无效的选择")
        return False
    
    def _validate_project(self, project: Path) -> bool:
        """验证项目结构"""
        required = {
            "CMakeLists.txt": "CMakeLists.txt (CMake配置文件)",
            "include": "include/ (头文件目录)",
            "src": "src/ (源文件目录)",
        }
        
        for req, desc in required.items():
            path = project / req
            exists = path.exists()
            status = "✓" if exists else "✗"
            print(f"  {status} {desc}")
            if not exists:
                return False
        
        # 检查CMakeLists.txt中是否有CMAKE_EXPORT_COMPILE_COMMANDS
        cmake_file = project / "CMakeLists.txt"
        with open(cmake_file) as f:
            content = f.read()
            has_export = "CMAKE_EXPORT_COMPILE_COMMANDS" in content
            if has_export:
                print("  ✓ CMAKE_EXPORT_COMPILE_COMMANDS 已配置")
            else:
                print("  ⚠ 警告: CMAKE_EXPORT_COMPILE_COMMANDS 未配置")
                print("          需要在CMakeLists.txt中添加这一行:")
                print("          set(CMAKE_EXPORT_COMPILE_COMMANDS ON)")
        
        return True
    
    def _generate_compile_commands(self, project: Path) -> Optional[Path]:
        """生成compile_commands.json"""
        build_dir = project / "build"
        
        # 如果build目录存在且compile_commands.json已有，直接使用
        compile_commands = build_dir / "compile_commands.json"
        if compile_commands.exists():
            print(f"  ✓ 使用已存在的: {compile_commands}")
            return compile_commands
        
        # 否则生成一个新的
        build_dir.mkdir(exist_ok=True)
        
        print("  正在运行CMake...")
        try:
            # 尝试使用Ninja（快速）
            result = subprocess.run(
                ["cmake", "-G", "Ninja", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", ".."],
                cwd=build_dir,
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                # 回退到Unix Makefiles
                result = subprocess.run(
                    ["cmake", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", ".."],
                    cwd=build_dir,
                    capture_output=True,
                    timeout=60
                )
            
            if result.returncode == 0 and compile_commands.exists():
                print(f"  ✓ 生成成功")
                return compile_commands
        except Exception as e:
            print(f"  ✗ CMake错误: {e}")
        
        return None
    
    def _analyze_codebase(self, project: Path, compile_commands: Path) -> list:
        """分析代码库，返回函数列表"""
        sys.path.insert(0, str(self.workflow_dir / "tools"))
        
        try:
            from c_code_analyzer import CCodeAnalyzer
            
            include_dir = project / "include"
            src_dir = project / "src"
            
            analyzer = CCodeAnalyzer(str(include_dir), str(src_dir))
            
            # 分析所有源文件
            for file in src_dir.glob("*.c"):
                analyzer.analyze_file(str(file))
            
            # 分析头文件
            for file in include_dir.glob("*.h"):
                analyzer.analyze_file(str(file))
            
            functions = analyzer.get_all_functions()
            return list(functions.keys())
        except Exception as e:
            print(f"  ✗ 分析失败: {e}")
            return []
    
    def _generate_all(self, project: Path, compile_commands: Path) -> bool:
        """生成所有函数的UT"""
        print("\n正在生成所有函数的单元测试...")
        print("(这可能需要几分钟，取决于代码量和vLLM模型)")
        
        try:
            # 运行完整工作流
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.workflow_dir / "tools" / "ut_workflow_llm.py"),
                    "--project", str(project),
                    "--compile-commands", str(compile_commands),
                ],
                timeout=3600
            )
            
            if result.returncode == 0:
                print("\n✓ 生成成功!")
                test_dir = project / "test"
                print(f"\n生成的测试文件已保存到: {test_dir}")
                
                # 列出生成的测试文件
                test_files = list(test_dir.glob("*_llm_test.cpp"))
                if test_files:
                    print(f"\n找到 {len(test_files)} 个测试文件：")
                    for f in test_files[:5]:
                        print(f"  - {f.name}")
                    if len(test_files) > 5:
                        print(f"  ... 还有 {len(test_files) - 5} 个")
                
                return True
        except subprocess.TimeoutExpired:
            print("✗ 超时（超过1小时）")
        except Exception as e:
            print(f"✗ 生成失败: {e}")
        
        return False
    
    def _generate_specific(self, project: Path, compile_commands: Path, functions: list) -> bool:
        """为特定函数生成UT"""
        print("\n可用的函数：")
        for i, func in enumerate(functions, 1):
            print(f"  {i:2d}. {func}")
        
        try:
            choice = input("\n请输入函数序号 (或函数名): ").strip()
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(functions):
                    function_name = functions[idx]
                else:
                    print("✗ 序号无效")
                    return False
            else:
                function_name = choice
            
            print(f"\n正在为函数 '{function_name}' 生成UT...")
            
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.workflow_dir / "tools" / "llm_test_generator.py"),
                    "--project", str(project),
                    "--compile-commands", str(compile_commands),
                    "--function", function_name,
                ],
                timeout=600
            )
            
            if result.returncode == 0:
                print(f"\n✓ 为 {function_name} 生成UT成功!")
                return True
        except subprocess.TimeoutExpired:
            print("✗ 超时（超过10分钟）")
        except Exception as e:
            print(f"✗ 生成失败: {e}")
        
        return False
    
    def _analyze_dependencies(self, project: Path) -> bool:
        """分析函数依赖关系"""
        print("\n分析函数依赖关系...")
        # TODO: 实现依赖关系分析
        print("✓ 功能开发中...")
        return True
    
    def _preview_prompt(self, project: Path) -> bool:
        """预览LLM Prompt"""
        print("\n预览LLM Prompt...")
        # TODO: 实现prompt预览
        print("✓ 功能开发中...")
        return True


def main():
    """主程序"""
    print("\n" + "=" * 70)
    print("欢迎使用 LLM UT生成工具")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        # 命令行参数方式
        project_path = sys.argv[1]
    else:
        # 交互式输入
        print("\n请输入目标项目路径:")
        print("示例:")
        print("  /home/user/my-c-project")
        print("  D:\\Projects\\my-code")
        print("  .  (当前目录)")
        
        project_path = input("\n项目路径: ").strip()
    
    if not project_path:
        print("✗ 路径不能为空")
        return False
    
    # 检查路径是否存在
    project = Path(project_path)
    if not project.exists():
        print(f"✗ 路径不存在: {project_path}")
        return False
    
    project = project.absolute()
    print(f"\n使用项目: {project}")
    
    # 运行生成器
    generator = UTGenerator()
    return generator.setup_project(str(project))


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
