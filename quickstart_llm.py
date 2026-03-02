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
import shutil
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
            last_decode_error = None
            for encoding in ("utf-8", "utf-8-sig", "gbk"):
                try:
                    with open(self.config_file, 'r', encoding=encoding) as f:
                        return json.load(f)
                except UnicodeDecodeError as e:
                    last_decode_error = e
                    continue
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in config file: {self.config_file}") from e
            raise ValueError(
                f"Failed to decode config file: {self.config_file}. Please save it as UTF-8."
            ) from last_decode_error
        
        return {
            "llm": {
                "api_base": "http://localhost:8000",
                "model": "qwen-coder"
            }
        }
    
    def _resolve_compiler(self) -> tuple[Optional[str], Optional[str]]:
        """解析可用C++编译器（优先配置项）。返回(compiler_path, detail_msg)。"""
        build_cfg = self.config.get("build", {})
        configured = str(build_cfg.get("compiler", "")).strip()

        if configured:
            candidate = Path(configured)
            if candidate.exists():
                return str(candidate), None
            found = shutil.which(configured)
            if found:
                return found, None
            return None, f"Configured compiler not found: {configured}"

        auto_found = shutil.which("g++") or shutil.which("clang++") or shutil.which("cl")
        if auto_found:
            return auto_found, None

        # 常见Windows安装路径兜底（PATH未刷新场景）
        common_windows_compilers = [
            Path("C:/Program Files/LLVM/bin/clang++.exe"),
            Path("C:/Program Files/LLVM/bin/clang-cl.exe"),
        ]
        for compiler_path in common_windows_compilers:
            if compiler_path.exists():
                return str(compiler_path), "Found in common install path"

        return None, None

    def _auto_install_compiler(self) -> bool:
        """自动安装编译器（当前仅Windows支持winget安装LLVM）。"""
        if os.name != 'nt':
            print("[Install] Auto install is currently implemented for Windows only.")
            return False

        winget = shutil.which("winget")
        if not winget:
            print("[Install] winget not found. Please install Visual Studio Build Tools or LLVM manually.")
            return False

        print("[Install] Installing LLVM (clang++) via winget...")
        cmd = [
            winget,
            "install",
            "--id", "LLVM.LLVM",
            "-e",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--silent"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("[Install] Failed to install LLVM automatically.")
            if result.stderr:
                print(result.stderr[:500])
            return False

        # 尝试将常见LLVM路径加入当前进程PATH，便于立即检测
        llvm_bin = Path("C:/Program Files/LLVM/bin")
        if llvm_bin.exists():
            current_path = os.environ.get("PATH", "")
            if str(llvm_bin) not in current_path:
                os.environ["PATH"] = str(llvm_bin) + os.pathsep + current_path

        return True

    def check_environment(self, prompt_install_compiler: bool = False) -> bool:
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
        checks.append(("LLM service", has_vllm, api_base))

        # 检查C++编译器（支持配置）
        compiler, compiler_detail = self._resolve_compiler()
        has_compiler = compiler is not None
        compiler_msg = compiler or "Not found"
        if compiler_detail:
            compiler_msg = f"{compiler_msg} ({compiler_detail})"

        # 交互模式可询问自动安装
        if (not has_compiler) and prompt_install_compiler and self.config.get("build", {}).get("auto_install_on_missing", True):
            answer = input("C++ compiler not found. Auto install LLVM clang++ now? (y/N): ").strip().lower()
            if answer in ("y", "yes"):
                if self._auto_install_compiler():
                    compiler, compiler_detail = self._resolve_compiler()
                    has_compiler = compiler is not None
                    compiler_msg = compiler or "Not found after install"
                    if compiler_detail:
                        compiler_msg = f"{compiler_msg} ({compiler_detail})"

        checks.append(("C++ compiler", has_compiler, compiler_msg))
        
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
        """检查LLM连接（vLLM或Ollama）"""
        backup_keys = [
            "LLM_BACKEND", "VLLM_API_BASE", "VLLM_MODEL", "VLLM_TIMEOUT",
            "OLLAMA_API_BASE", "OLLAMA_MODEL", "OLLAMA_TIMEOUT", "OLLAMA_MAX_TOKENS",
            "VLLM_FALLBACK_TO_OLLAMA"
        ]
        backup = {k: os.environ.get(k) for k in backup_keys}

        try:
            llm_cfg = self.config.get("llm", {})
            ollama_cfg = llm_cfg.get("ollama", {})

            if llm_cfg.get("backend"):
                os.environ["LLM_BACKEND"] = str(llm_cfg.get("backend"))
            if llm_cfg.get("api_base"):
                os.environ["VLLM_API_BASE"] = str(llm_cfg.get("api_base"))
            if llm_cfg.get("model"):
                os.environ["VLLM_MODEL"] = str(llm_cfg.get("model"))
            if llm_cfg.get("timeout") is not None:
                os.environ["VLLM_TIMEOUT"] = str(llm_cfg.get("timeout"))

            if ollama_cfg.get("api_base"):
                os.environ["OLLAMA_API_BASE"] = str(ollama_cfg.get("api_base"))
            if ollama_cfg.get("model"):
                os.environ["OLLAMA_MODEL"] = str(ollama_cfg.get("model"))
            if ollama_cfg.get("timeout") is not None:
                os.environ["OLLAMA_TIMEOUT"] = str(ollama_cfg.get("timeout"))
            if ollama_cfg.get("max_tokens") is not None:
                os.environ["OLLAMA_MAX_TOKENS"] = str(ollama_cfg.get("max_tokens"))
            if ollama_cfg.get("fallback_from_vllm") is not None:
                os.environ["VLLM_FALLBACK_TO_OLLAMA"] = str(ollama_cfg.get("fallback_from_vllm"))

            sys.path.insert(0, str(self.tools_dir))
            from llm_client import VLLMClient

            client = VLLMClient(api_base=api_base)
            return client.active_backend is not None
        except Exception:
            return False
        finally:
            for key, value in backup.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    
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
                     analyze_only: bool = False,
                     max_fix_attempts: Optional[int] = None,
                     max_test_fix_attempts: Optional[int] = None,
                     auto_fix_compile_errors: Optional[bool] = None,
                     auto_fix_test_failures: Optional[bool] = None,
                     llm_triage_enabled: Optional[bool] = None,
                     triage_min_confidence: Optional[float] = None) -> bool:
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

        quality_cfg = self.config.get("test_generation", {}).get("quality_gates", {})
        if quality_cfg.get("enabled") is False:
            cmd.append("--skip-quality-gates")
        if quality_cfg.get("strict") is True:
            cmd.append("--quality-strict")

        compile_fix_cfg = self.config.get("test_generation", {}).get("compile_fix", {})
        effective_auto_fix = compile_fix_cfg.get("auto_fix_compile_errors", True)
        if auto_fix_compile_errors is not None:
            effective_auto_fix = auto_fix_compile_errors

        effective_max_fix_attempts = compile_fix_cfg.get("max_fix_attempts", 2)
        try:
            effective_max_fix_attempts = int(effective_max_fix_attempts)
        except (TypeError, ValueError):
            effective_max_fix_attempts = 2
        if max_fix_attempts is not None:
            effective_max_fix_attempts = max_fix_attempts
        effective_max_fix_attempts = max(0, effective_max_fix_attempts)

        if not effective_auto_fix:
            cmd.append("--no-auto-fix-compile")
        cmd.extend(["--max-fix-attempts", str(effective_max_fix_attempts)])

        effective_auto_fix_test = compile_fix_cfg.get("auto_fix_test_failures", True)
        if auto_fix_test_failures is not None:
            effective_auto_fix_test = auto_fix_test_failures

        effective_max_test_fix_attempts = compile_fix_cfg.get("max_test_fix_attempts", 2)
        try:
            effective_max_test_fix_attempts = int(effective_max_test_fix_attempts)
        except (TypeError, ValueError):
            effective_max_test_fix_attempts = 2
        if max_test_fix_attempts is not None:
            effective_max_test_fix_attempts = max_test_fix_attempts
        effective_max_test_fix_attempts = max(0, effective_max_test_fix_attempts)

        if not effective_auto_fix_test:
            cmd.append("--no-auto-fix-test-fail")
        cmd.extend(["--max-test-fix-attempts", str(effective_max_test_fix_attempts)])

        effective_llm_triage_enabled = compile_fix_cfg.get("llm_triage_enabled", True)
        if llm_triage_enabled is not None:
            effective_llm_triage_enabled = llm_triage_enabled

        effective_triage_min_conf = compile_fix_cfg.get("triage_min_confidence", 0.55)
        try:
            effective_triage_min_conf = float(effective_triage_min_conf)
        except (TypeError, ValueError):
            effective_triage_min_conf = 0.55
        if triage_min_confidence is not None:
            effective_triage_min_conf = triage_min_confidence
        effective_triage_min_conf = max(0.0, min(1.0, effective_triage_min_conf))

        if not effective_llm_triage_enabled:
            cmd.append("--disable-llm-triage")
        cmd.extend(["--triage-min-confidence", f"{effective_triage_min_conf:.2f}"])

        # 从配置透传LLM后端与Ollama设置到子进程环境
        env = os.environ.copy()
        llm_cfg = self.config.get("llm", {})
        ollama_cfg = llm_cfg.get("ollama", {})

        if llm_cfg.get("backend"):
            env["LLM_BACKEND"] = str(llm_cfg.get("backend"))
        if llm_cfg.get("api_base"):
            env["VLLM_API_BASE"] = str(llm_cfg.get("api_base"))
        if llm_cfg.get("model"):
            env["VLLM_MODEL"] = str(llm_cfg.get("model"))
        if llm_cfg.get("timeout") is not None:
            env["VLLM_TIMEOUT"] = str(llm_cfg.get("timeout"))

        if ollama_cfg.get("api_base"):
            env["OLLAMA_API_BASE"] = str(ollama_cfg.get("api_base"))
        if ollama_cfg.get("model"):
            env["OLLAMA_MODEL"] = str(ollama_cfg.get("model"))
        if ollama_cfg.get("timeout") is not None:
            env["OLLAMA_TIMEOUT"] = str(ollama_cfg.get("timeout"))
        if ollama_cfg.get("max_tokens") is not None:
            env["OLLAMA_MAX_TOKENS"] = str(ollama_cfg.get("max_tokens"))
        if ollama_cfg.get("fallback_from_vllm") is not None:
            env["VLLM_FALLBACK_TO_OLLAMA"] = str(ollama_cfg.get("fallback_from_vllm"))

        # 透传编译器配置
        build_cfg = self.config.get("build", {})
        configured_compiler = str(build_cfg.get("compiler", "")).strip()
        if configured_compiler:
            env["CXX"] = configured_compiler
        else:
            resolved_compiler, _ = self._resolve_compiler()
            if resolved_compiler:
                env["CXX"] = resolved_compiler
        
        # 运行工作流
        result = subprocess.run(cmd, cwd=str(self.tools_dir), env=env)
        
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
    
    def interactive_mode(self,
                         max_fix_attempts: Optional[int] = None,
                         max_test_fix_attempts: Optional[int] = None,
                         auto_fix_compile_errors: Optional[bool] = None,
                         auto_fix_test_failures: Optional[bool] = None,
                         llm_triage_enabled: Optional[bool] = None,
                         triage_min_confidence: Optional[float] = None) -> None:
        """交互模式"""
        while True:
            self.show_menu()
            
            choice = input("> ").strip()
            
            if choice == "1":
                self.check_environment(prompt_install_compiler=True)
            elif choice == "2":
                self.setup_vllm()
            elif choice == "3":
                self.generate_compile_commands()
            elif choice == "4":
                if not self.check_environment(prompt_install_compiler=True):
                    print("✗ Environment check failed!")
                    continue
                self.run_workflow(
                    analyze_only=True,
                    max_fix_attempts=max_fix_attempts,
                    max_test_fix_attempts=max_test_fix_attempts,
                    auto_fix_compile_errors=auto_fix_compile_errors,
                    auto_fix_test_failures=auto_fix_test_failures,
                    llm_triage_enabled=llm_triage_enabled,
                    triage_min_confidence=triage_min_confidence
                )
            elif choice == "5":
                if not self.check_environment(prompt_install_compiler=True):
                    print("✗ Environment check failed!")
                    continue
                functions = input("Enter function names (space-separated, or leave blank for all): ")
                func_list = functions.split() if functions.strip() else None
                self.run_workflow(
                    functions=func_list,
                    max_fix_attempts=max_fix_attempts,
                    max_test_fix_attempts=max_test_fix_attempts,
                    auto_fix_compile_errors=auto_fix_compile_errors,
                    auto_fix_test_failures=auto_fix_test_failures,
                    llm_triage_enabled=llm_triage_enabled,
                    triage_min_confidence=triage_min_confidence
                )
            elif choice == "6":
                if not self.check_environment(prompt_install_compiler=True):
                    print("✗ Environment check failed!")
                    continue
                if not self._find_compile_commands():
                    print("No compile_commands.json found. Generating...")
                    if not self.generate_compile_commands():
                        continue
                self.run_workflow(
                    max_fix_attempts=max_fix_attempts,
                    max_test_fix_attempts=max_test_fix_attempts,
                    auto_fix_compile_errors=auto_fix_compile_errors,
                    auto_fix_test_failures=auto_fix_test_failures,
                    llm_triage_enabled=llm_triage_enabled,
                    triage_min_confidence=triage_min_confidence
                )
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

    parser.add_argument(
        "--max-fix-attempts",
        type=int,
        default=None,
        help="Override compile auto-fix max retry attempts for quickstart"
    )

    parser.add_argument(
        "--no-auto-fix-compile",
        action="store_true",
        help="Disable compile auto-fix phase in quickstart"
    )

    parser.add_argument(
        "--max-test-fix-attempts",
        type=int,
        default=None,
        help="Override runtime test-failure auto-fix max retry attempts for quickstart"
    )

    parser.add_argument(
        "--no-auto-fix-test-fail",
        action="store_true",
        help="Disable runtime test-failure auto-fix phase in quickstart"
    )

    parser.add_argument(
        "--disable-llm-triage",
        action="store_true",
        help="Disable analyze-then-fix triage before LLM patch"
    )

    parser.add_argument(
        "--triage-min-confidence",
        type=float,
        default=None,
        help="Minimum triage confidence [0,1] required to apply LLM fix"
    )
    
    args = parser.parse_args()
    
    quickstart = QuickStart(project_root=args.project_dir)

    action_requested = any([
        args.check,
        args.setup_vllm,
        args.generate_compile_commands,
        args.analyze,
        args.generate is not None,
    ])
    
    # 交互模式（默认）
    if args.interactive or not action_requested:
        quickstart.interactive_mode(
            max_fix_attempts=args.max_fix_attempts,
            max_test_fix_attempts=args.max_test_fix_attempts,
            auto_fix_compile_errors=(False if args.no_auto_fix_compile else None),
            auto_fix_test_failures=(False if args.no_auto_fix_test_fail else None),
            llm_triage_enabled=(False if args.disable_llm_triage else None),
            triage_min_confidence=args.triage_min_confidence
        )
    
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
        if quickstart.run_workflow(
            analyze_only=True,
            max_fix_attempts=args.max_fix_attempts,
            max_test_fix_attempts=args.max_test_fix_attempts,
            auto_fix_compile_errors=(False if args.no_auto_fix_compile else None),
            auto_fix_test_failures=(False if args.no_auto_fix_test_fail else None),
            llm_triage_enabled=(False if args.disable_llm_triage else None),
            triage_min_confidence=args.triage_min_confidence
        ):
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.generate is not None:
        if not quickstart.check_environment():
            sys.exit(1)
        functions = args.generate if args.generate else None
        if quickstart.run_workflow(
            functions=functions,
            max_fix_attempts=args.max_fix_attempts,
            max_test_fix_attempts=args.max_test_fix_attempts,
            auto_fix_compile_errors=(False if args.no_auto_fix_compile else None),
            auto_fix_test_failures=(False if args.no_auto_fix_test_fail else None),
            llm_triage_enabled=(False if args.disable_llm_triage else None),
            triage_min_confidence=args.triage_min_confidence
        ):
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
