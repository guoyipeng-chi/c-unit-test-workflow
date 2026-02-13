#!/usr/bin/env python3
"""
Quick Start: LLM-based UT Generation
快速启动脚本 - 一键运行LLM UT生成工作流
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional


class QuickStart:
    """快速启动助手"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).absolute()
        self.config_file = self.project_root / "llm_workflow_config.json"
        self.tools_dir = self.project_root / "tools"
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        return {
            "llm": {
                "api_base": "http://localhost:8000",
                "model": "qwen-coder"
            }
        }
    
    def check_environment(self) -> bool:
        """检查环境"""
        print("[Check] Checking environment...")
        print("=" * 60)
        
        checks = []
        
        # 检查Python版本
        python_version = sys.version_info
        has_python = python_version.major >= 3 and python_version.minor >= 8
        checks.append(("Python 3.8+", has_python, f"Python {python_version.major}.{python_version.minor}"))
        
        # 检查tools目录
        has_tools = self.tools_dir.exists()
        checks.append(("Tools directory", has_tools, str(self.tools_dir)))
        
        # 检查compile_commands.json
        compile_cmd = self._find_compile_commands()
        has_compile_cmd = compile_cmd is not None
        checks.append((
            "compile_commands.json",
            has_compile_cmd,
            str(compile_cmd) if compile_cmd else "Not found"
        ))
        
        # 检查vLLM连接
        api_base = self.config.get("llm", {}).get("api_base", "http://localhost:8000")
        has_vllm = self._check_vllm_connection(api_base)
        checks.append(("vLLM service", has_vllm, api_base))
        
        # 打印检查结果
        all_passed = True
        for check_name, passed, details in checks:
            status = "✓" if passed else "✗"
            print(f"{status} {check_name:<30} {details}")
            if not passed:
                all_passed = False
        
        print("=" * 60)
        return all_passed
    
    def _find_compile_commands(self) -> Optional[Path]:
        """查找compile_commands.json"""
        search_paths = self.config.get("compile_commands", {}).get("search_paths", [])
        
        for search_path in search_paths:
            full_path = self.project_root / search_path
            if full_path.exists():
                return full_path
        
        return None
    
    def _check_vllm_connection(self, api_base: str) -> bool:
        """检查vLLM连接"""
        try:
            import requests
            response = requests.get(
                f"{api_base}/v1/models",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def setup_vllm(self) -> None:
        """帮助设置vLLM"""
        print("\n[Setup] vLLM Configuration")
        print("=" * 60)
        print("""
To use LLM-based test generation, you need to setup vLLM with Qwen3 Coder:

Option 1: Local Installation
  pip install vllm
  python -m vllm.entrypoints.openai.api_server \\
    --model Qwen/Qwen2.5-Coder-32B-Instruct \\
    --tensor-parallel-size 2 \\
    --port 8000

Option 2: Docker Container
  docker run --gpus all \\
    -p 8000:8000 \\
    --ipc=host \\
    vllm/vllm-openai:latest \\
    --model Qwen/Qwen2.5-Coder-32B-Instruct

Option 3: Remote Server
  Update llm_workflow_config.json:
  {
    "llm": {
      "api_base": "http://remote-server:8000",
      "model": "qwen-coder"
    }
  }

Then verify with:
  curl http://localhost:8000/v1/models
""")
    
    def generate_compile_commands(self) -> bool:
        """生成compile_commands.json"""
        print("\n[Generate] Creating compile_commands.json...")
        print("=" * 60)
        
        build_dir = self.project_root / "build"
        
        if not build_dir.exists():
            print(f"Creating build directory: {build_dir}")
            build_dir.mkdir(parents=True)
        
        # 运行cmake
        print("Running CMake...")
        result = subprocess.run(
            ["cmake", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", ".."],
            cwd=str(build_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ CMake failed: {result.stderr}")
            return False
        
        compile_cmd_file = build_dir / "compile_commands.json"
        if compile_cmd_file.exists():
            print(f"✓ Generated: {compile_cmd_file}")
            return True
        else:
            print("✗ compile_commands.json not generated")
            return False
    
    def run_workflow(self, functions: Optional[list] = None,
                     analyze_only: bool = False) -> bool:
        """运行工作流"""
        print("\n[Run] Starting LLM UT Generation Workflow...")
        print("=" * 60)
        
        compile_cmd = self._find_compile_commands()
        if not compile_cmd:
            print("✗ compile_commands.json not found")
            return False
        
        # 构建命令
        cmd = [
            sys.executable,
            str(self.tools_dir / "ut_workflow_llm.py"),
            "--project-dir", str(self.project_root),
            "--compile-commands", str(compile_cmd),
            "--llm-api", self.config.get("llm", {}).get("api_base", "http://localhost:8000"),
            "--llm-model", self.config.get("llm", {}).get("model", "qwen-coder"),
        ]
        
        if analyze_only:
            cmd.append("--analyze-only")
        
        if functions:
            cmd.extend(["--functions"] + functions)
        
        # 运行工作流
        result = subprocess.run(cmd, cwd=str(self.tools_dir))
        
        return result.returncode == 0
    
    def show_menu(self) -> None:
        """显示交互菜单"""
        print("\n[Menu] LLM UT Generation - Quick Start")
        print("=" * 60)
        print("""
1. Check Environment       - 检查环境配置
2. Setup vLLM             - 配置vLLM (本地/远程)
3. Generate Compile Info  - 生成compile_commands.json
4. Analyze Code           - 仅分析代码（不生成测试）
5. Generate Tests         - 生成单元测试
6. Full Workflow          - 执行完整工作流
7. Exit                   - 退出

Enter your choice (1-7):
""")
    
    def interactive_mode(self) -> None:
        """交互模式"""
        while True:
            self.show_menu()
            
            choice = input("> ").strip()
            
            if choice == "1":
                self.check_environment()
            elif choice == "2":
                self.setup_vllm()
            elif choice == "3":
                self.generate_compile_commands()
            elif choice == "4":
                if not self.check_environment():
                    print("✗ Environment check failed!")
                    continue
                self.run_workflow(analyze_only=True)
            elif choice == "5":
                if not self.check_environment():
                    print("✗ Environment check failed!")
                    continue
                functions = input("Enter function names (space-separated, or leave blank for all): ")
                func_list = functions.split() if functions.strip() else None
                self.run_workflow(functions=func_list)
            elif choice == "6":
                if not self.check_environment():
                    print("✗ Environment check failed!")
                    continue
                if not self._find_compile_commands():
                    print("No compile_commands.json found. Generating...")
                    if not self.generate_compile_commands():
                        continue
                self.run_workflow()
            elif choice == "7":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
            
            print()


def main():
    parser = argparse.ArgumentParser(
        description="LLM-based C Unit Test Generation - Quick Start"
    )
    
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project root directory"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check environment only"
    )
    
    parser.add_argument(
        "--setup-vllm",
        action="store_true",
        help="Show vLLM setup instructions"
    )
    
    parser.add_argument(
        "--generate-compile-commands",
        action="store_true",
        help="Generate compile_commands.json"
    )
    
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze code only (no test generation)"
    )
    
    parser.add_argument(
        "--generate",
        nargs="*",
        help="Generate tests for functions"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode"
    )
    
    args = parser.parse_args()
    
    quickstart = QuickStart(project_root=args.project_dir)
    
    # 交互模式（默认）
    if args.interactive or len(sys.argv) == 1:
        quickstart.interactive_mode()
    
    # 命令行模式
    elif args.check:
        if quickstart.check_environment():
            print("\n✓ Environment OK")
            sys.exit(0)
        else:
            print("\n✗ Environment issues detected")
            sys.exit(1)
    
    elif args.setup_vllm:
        quickstart.setup_vllm()
    
    elif args.generate_compile_commands:
        if quickstart.generate_compile_commands():
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.analyze:
        if not quickstart.check_environment():
            sys.exit(1)
        if quickstart.run_workflow(analyze_only=True):
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.generate is not None:
        if not quickstart.check_environment():
            sys.exit(1)
        functions = args.generate if args.generate else None
        if quickstart.run_workflow(functions=functions):
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
