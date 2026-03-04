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
import re
from pathlib import Path
from typing import Optional, List, Tuple, Dict


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

    @staticmethod
    def _ansi_enabled() -> bool:
        if os.environ.get("NO_COLOR"):
            return False
        term = (os.environ.get("TERM") or "").lower()
        if term == "dumb":
            return False
        return True

    @classmethod
    def _gray_text(cls, text: str) -> str:
        if not cls._ansi_enabled():
            return text
        return f"\033[90m{text}\033[0m"
    
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

    @staticmethod
    def _default_external_experience_path() -> str:
        """返回仓库外的经验库默认路径（用于不跟Git场景）。"""
        if os.name == 'nt':
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            return str(Path(base) / "c-unit-test-workflow" / "experience_store.jsonl")
        return str(Path.home() / ".local" / "share" / "c-unit-test-workflow" / "experience_store.jsonl")

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

    def _discover_generated_function_names(self) -> set:
        test_dir = self.project_root / self.config.get("paths", {}).get("test_dir", "test")
        if not test_dir.exists():
            return set()

        generated = set()
        for test_file in test_dir.glob("*_llm_test.cpp"):
            stem = test_file.stem
            if stem.endswith("_llm_test"):
                generated.add(stem[:-9])
        return generated

    def _load_function_status_index(self) -> Dict[str, Dict[str, str]]:
        status_path = self.project_root / "log" / "function_status_index.json"
        if not status_path.exists():
            return {}
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            functions = payload.get("functions", {}) if isinstance(payload, dict) else {}
            return functions if isinstance(functions, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _normalize_picker_status(raw_status: Optional[str], is_generated: bool) -> str:
        if not is_generated:
            return "NEW"
        status = str(raw_status or "").strip().upper()
        if status == "PASSED":
            return "PASS"
        if status in {"FAILED", "COMPILE_FAILED", "TIMEOUT", "ERROR"}:
            return "FAIL"
        return "GEN"

    @staticmethod
    def _is_failed_picker_status(status: str) -> bool:
        return str(status or "").upper() == "FAIL"

    def _discover_functions_for_selection(self) -> List[Tuple[str, str, bool, str]]:
        include_dir = self.project_root / self.config.get("paths", {}).get("include_dir", "include")
        src_dir = self.project_root / self.config.get("paths", {}).get("src_dir", "src")

        if not include_dir.exists() or not src_dir.exists():
            return []

        sys.path.insert(0, str(self.tools_dir))
        from c_code_analyzer import CCodeAnalyzer

        analyzer = CCodeAnalyzer(str(include_dir), str(src_dir))
        analyzer.analyze_directory()
        funcs = analyzer.get_all_functions()
        generated_names = self._discover_generated_function_names()
        status_index = self._load_function_status_index()

        records: List[Tuple[str, str, bool, str]] = []
        for name, dep in funcs.items():
            source = str(dep.source_file).replace('\\', '/')
            is_generated = name in generated_names
            raw_status = ""
            if is_generated:
                raw_status = str(status_index.get(name, {}).get("status", ""))
            picker_status = self._normalize_picker_status(raw_status, is_generated)
            records.append((name, source, is_generated, picker_status))

        records.sort(key=lambda item: item[0].lower())
        return records

    @staticmethod
    def _with_function_tab_completion(function_names: List[str]):
        try:
            import readline

            original_completer = readline.get_completer()
            original_delims = readline.get_completer_delims()

            choices = sorted(set(function_names), key=str.lower)

            def completer(text, state):
                buffer = readline.get_line_buffer()
                begidx = readline.get_begidx()
                token = buffer[:begidx].split()[-1] if buffer[:begidx].split() else ""
                prefix = text or token
                matches = [name for name in choices if name.lower().startswith(prefix.lower())]
                if state < len(matches):
                    return matches[state]
                return None

            readline.set_completer_delims(" \t\n;")
            readline.parse_and_bind("tab: complete")
            readline.set_completer(completer)

            def restore():
                readline.set_completer(original_completer)
                readline.set_completer_delims(original_delims)

            return restore
        except Exception:
            return lambda: None

    @staticmethod
    def _parse_index_tokens(raw: str, max_index: int) -> List[int]:
        selected: List[int] = []
        tokens = [t for t in re.split(r"[\s,]+", raw.strip()) if t]
        for token in tokens:
            if "-" in token:
                left, right = token.split("-", 1)
                if left.isdigit() and right.isdigit():
                    start = int(left)
                    end = int(right)
                    if start > end:
                        start, end = end, start
                    for index in range(start, end + 1):
                        if 1 <= index <= max_index:
                            selected.append(index)
                continue
            if token.isdigit():
                index = int(token)
                if 1 <= index <= max_index:
                    selected.append(index)
        return sorted(set(selected))

    def select_functions_interactively(self) -> Tuple[Optional[List[str]], bool]:
        records = self._discover_functions_for_selection()
        if not records:
            print("✗ No functions discovered under current include/src paths.")
            return None, True

        page_size = 12
        current_page = 0
        selected_record_indices = set()
        filter_mode = "all"  # all | ungenerated | failed
        function_names = [name for name, _, _, _ in records]
        restore_completion = self._with_function_tab_completion(function_names)

        try:
            while True:
                visible_record_indices = [
                    i for i, (_, _, is_generated, picker_status) in enumerate(records)
                    if (
                        (filter_mode == "all")
                        or (filter_mode == "ungenerated" and (not is_generated))
                        or (filter_mode == "failed" and is_generated and self._is_failed_picker_status(picker_status))
                    )
                ]
                total = len(visible_record_indices)
                total_generated = sum(1 for _, _, is_generated, _ in records if is_generated)
                total_new = len(records) - total_generated
                total_failed = sum(1 for _, _, is_generated, status in records if is_generated and self._is_failed_picker_status(status))

                if total == 0:
                    print("\n[Function Picker]")
                    print(f"No functions visible under current filter ({filter_mode}).")
                    print("Commands: u(ungenerated), f(failed-generated), s(show all), q(cancel)")
                    raw = input("select> ").strip().lower()
                    if raw in {"u", "ungenerated"}:
                        filter_mode = "ungenerated"
                        continue
                    if raw in {"f", "failed"}:
                        filter_mode = "failed"
                        continue
                    if raw in {"s", "show", "all"}:
                        filter_mode = "all"
                        continue
                    if raw in {"q", "quit", "cancel"}:
                        return None, True
                    continue

                total_pages = max(1, (total + page_size - 1) // page_size)
                current_page = max(0, min(current_page, total_pages - 1))
                start = current_page * page_size
                end = min(total, start + page_size)

                print("\n[Function Picker]")
                print(
                    f"Page {current_page + 1}/{total_pages}, visible: {total}, "
                    f"all: {len(records)} (new={total_new}, generated={total_generated}, failed={total_failed}), "
                    f"filter: {filter_mode}"
                )
                print("Commands: n(next), p(prev), u(ungenerated), f(failed-generated), s(show all), a(all), d(done), c(clear), q(cancel)")
                print("Input: number(s) like 1 3 8-12, or function name/prefix (Tab to complete)")
                print("-" * 72)

                for visible_idx in range(start, end):
                    rec_idx = visible_record_indices[visible_idx]
                    name, src, is_generated, picker_status = records[rec_idx]
                    marker = "*" if rec_idx in selected_record_indices else " "
                    state = picker_status
                    row = f"{marker} {visible_idx + 1:>3}. [{state}] {name:<26} {src}"
                    if is_generated:
                        row = self._gray_text(row)
                    print(row)

                if selected_record_indices:
                    preview = [records[i][0] for i in sorted(selected_record_indices)[:8]]
                    tail = " ..." if len(selected_record_indices) > 8 else ""
                    print(f"Selected({len(selected_record_indices)}): {', '.join(preview)}{tail}")

                raw = input("select> ").strip()
                if not raw:
                    continue

                cmd = raw.lower()
                if cmd in {"n", "next"}:
                    current_page = min(current_page + 1, total_pages - 1)
                    continue
                if cmd in {"p", "prev"}:
                    current_page = max(current_page - 1, 0)
                    continue
                if cmd in {"u", "ungenerated"}:
                    filter_mode = "ungenerated"
                    current_page = 0
                    continue
                if cmd in {"f", "failed"}:
                    filter_mode = "failed"
                    current_page = 0
                    continue
                if cmd in {"s", "show", "showall", "allview"}:
                    filter_mode = "all"
                    current_page = 0
                    continue
                if cmd in {"a", "all"}:
                    if filter_mode != "all":
                        selected = [records[i][0] for i in visible_record_indices]
                        print(f"✓ Select all visible functions ({len(selected)}) under filter '{filter_mode}'")
                        return selected, False
                    print("✓ Select all functions")
                    return None, False
                if cmd in {"c", "clear"}:
                    selected_record_indices.clear()
                    continue
                if cmd in {"q", "quit", "cancel"}:
                    return None, True
                if cmd in {"d", "done", "ok"}:
                    if not selected_record_indices:
                        print("⚠ No selected function, use a/all or choose indices first.")
                        continue
                    selected = [records[i][0] for i in sorted(selected_record_indices)]
                    return selected, False

                index_hits = self._parse_index_tokens(raw, total)
                if index_hits:
                    for visible_idx in index_hits:
                        rec_idx = visible_record_indices[visible_idx - 1]
                        if rec_idx in selected_record_indices:
                            selected_record_indices.remove(rec_idx)
                        else:
                            selected_record_indices.add(rec_idx)
                    continue

                name_tokens = [t for t in re.split(r"[\s,]+", raw) if t]
                matched_any = False
                for token in name_tokens:
                    exact = [i for i, (name, _, _, _) in enumerate(records) if name == token]
                    if exact:
                        rec_idx = exact[0]
                        if rec_idx in selected_record_indices:
                            selected_record_indices.remove(rec_idx)
                        else:
                            selected_record_indices.add(rec_idx)
                        matched_any = True
                        continue

                    pref = [i for i, (name, _, _, _) in enumerate(records) if name.lower().startswith(token.lower())]
                    if len(pref) == 1:
                        rec_idx = pref[0]
                        if rec_idx in selected_record_indices:
                            selected_record_indices.remove(rec_idx)
                        else:
                            selected_record_indices.add(rec_idx)
                        matched_any = True
                        continue

                    if len(pref) > 1:
                        examples = ", ".join(records[i][0] for i in pref[:8])
                        print(f"⚠ Prefix '{token}' matches multiple functions: {examples}")
                        matched_any = True
                        continue

                if not matched_any:
                    print("⚠ Unrecognized input. Use n/p/a/d/c/q, indices, or function name prefix.")
        finally:
            restore_completion()
    
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
                     triage_min_confidence: Optional[float] = None,
                     web_research_enabled: Optional[bool] = None,
                     web_research_max_results: Optional[int] = None,
                     experience_learning_enabled: Optional[bool] = None,
                     experience_top_k: Optional[int] = None,
                     experience_store_path: Optional[str] = None) -> bool:
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

        effective_web_research_enabled = compile_fix_cfg.get("web_research_enabled", True)
        if web_research_enabled is not None:
            effective_web_research_enabled = web_research_enabled

        effective_web_research_max_results = compile_fix_cfg.get("web_research_max_results", 4)
        try:
            effective_web_research_max_results = int(effective_web_research_max_results)
        except (TypeError, ValueError):
            effective_web_research_max_results = 4
        if web_research_max_results is not None:
            effective_web_research_max_results = web_research_max_results
        effective_web_research_max_results = max(1, effective_web_research_max_results)

        if not effective_web_research_enabled:
            cmd.append("--disable-web-research")
        cmd.extend(["--web-research-max-results", str(effective_web_research_max_results)])

        effective_experience_learning_enabled = compile_fix_cfg.get("experience_learning_enabled", True)
        if experience_learning_enabled is not None:
            effective_experience_learning_enabled = experience_learning_enabled

        effective_experience_top_k = compile_fix_cfg.get("experience_top_k", 3)
        try:
            effective_experience_top_k = int(effective_experience_top_k)
        except (TypeError, ValueError):
            effective_experience_top_k = 3
        if experience_top_k is not None:
            effective_experience_top_k = experience_top_k
        effective_experience_top_k = max(1, effective_experience_top_k)

        effective_experience_store_path = compile_fix_cfg.get("experience_store_path", "./log/experience_store.jsonl")
        if experience_store_path is not None:
            effective_experience_store_path = experience_store_path

        effective_experience_track_in_git = compile_fix_cfg.get("experience_track_in_git", True)
        if experience_store_path is None and not bool(effective_experience_track_in_git):
            effective_experience_store_path = self._default_external_experience_path()

        if not effective_experience_learning_enabled:
            cmd.append("--disable-experience-learning")
        cmd.extend(["--experience-top-k", str(effective_experience_top_k)])
        if effective_experience_store_path:
            cmd.extend(["--experience-store-path", str(effective_experience_store_path)])

        execution_cfg = self.config.get("test_generation", {}).get("execution", {})
        compile_exec_cfg = execution_cfg.get("compile", {}) if isinstance(execution_cfg, dict) else {}
        run_exec_cfg = execution_cfg.get("run", {}) if isinstance(execution_cfg, dict) else {}

        compile_template = str(compile_exec_cfg.get("command", "")).strip() if isinstance(compile_exec_cfg, dict) else ""
        compile_cwd = str(compile_exec_cfg.get("cwd", "")).strip() if isinstance(compile_exec_cfg, dict) else ""
        run_template = str(run_exec_cfg.get("command", "")).strip() if isinstance(run_exec_cfg, dict) else ""
        run_cwd = str(run_exec_cfg.get("cwd", "")).strip() if isinstance(run_exec_cfg, dict) else ""

        if compile_template:
            cmd.extend(["--compile-command-template", compile_template])
        if compile_cwd:
            cmd.extend(["--compile-command-cwd", compile_cwd])
        if run_template:
            cmd.extend(["--run-command-template", run_template])
        if run_cwd:
            cmd.extend(["--run-command-cwd", run_cwd])

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
                         triage_min_confidence: Optional[float] = None,
                         web_research_enabled: Optional[bool] = None,
                         web_research_max_results: Optional[int] = None,
                         experience_learning_enabled: Optional[bool] = None,
                         experience_top_k: Optional[int] = None,
                         experience_store_path: Optional[str] = None) -> None:
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
                    triage_min_confidence=triage_min_confidence,
                    web_research_enabled=web_research_enabled,
                    web_research_max_results=web_research_max_results,
                    experience_learning_enabled=experience_learning_enabled,
                    experience_top_k=experience_top_k,
                    experience_store_path=experience_store_path
                )
            elif choice == "5":
                if not self.check_environment(prompt_install_compiler=True):
                    print("✗ Environment check failed!")
                    continue
                func_list, cancelled = self.select_functions_interactively()
                if cancelled:
                    print("Selection cancelled.")
                    continue
                self.run_workflow(
                    functions=func_list,
                    max_fix_attempts=max_fix_attempts,
                    max_test_fix_attempts=max_test_fix_attempts,
                    auto_fix_compile_errors=auto_fix_compile_errors,
                    auto_fix_test_failures=auto_fix_test_failures,
                    llm_triage_enabled=llm_triage_enabled,
                    triage_min_confidence=triage_min_confidence,
                    web_research_enabled=web_research_enabled,
                    web_research_max_results=web_research_max_results,
                    experience_learning_enabled=experience_learning_enabled,
                    experience_top_k=experience_top_k,
                    experience_store_path=experience_store_path
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
                    triage_min_confidence=triage_min_confidence,
                    web_research_enabled=web_research_enabled,
                    web_research_max_results=web_research_max_results,
                    experience_learning_enabled=experience_learning_enabled,
                    experience_top_k=experience_top_k,
                    experience_store_path=experience_store_path
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

    parser.add_argument(
        "--disable-web-research",
        action="store_true",
        help="Disable online root-cause research after triage"
    )

    parser.add_argument(
        "--web-research-max-results",
        type=int,
        default=None,
        help="Maximum number of web references used as fix context"
    )

    parser.add_argument(
        "--disable-experience-learning",
        action="store_true",
        help="Disable experience accumulation and historical experience retrieval"
    )

    parser.add_argument(
        "--experience-top-k",
        type=int,
        default=None,
        help="Top-K historical experiences used as fix context"
    )

    parser.add_argument(
        "--experience-store-path",
        default=None,
        help="Path to experience store jsonl file"
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
            triage_min_confidence=args.triage_min_confidence,
            web_research_enabled=(False if args.disable_web_research else None),
            web_research_max_results=args.web_research_max_results,
            experience_learning_enabled=(False if args.disable_experience_learning else None),
            experience_top_k=args.experience_top_k,
            experience_store_path=args.experience_store_path
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
            triage_min_confidence=args.triage_min_confidence,
            web_research_enabled=(False if args.disable_web_research else None),
            web_research_max_results=args.web_research_max_results,
            experience_learning_enabled=(False if args.disable_experience_learning else None),
            experience_top_k=args.experience_top_k,
            experience_store_path=args.experience_store_path
        ):
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.generate is not None:
        if not quickstart.check_environment():
            sys.exit(1)
        functions = args.generate if args.generate else None
        if args.generate == []:
            if sys.stdin.isatty():
                functions, cancelled = quickstart.select_functions_interactively()
                if cancelled:
                    print("✗ Function selection cancelled")
                    sys.exit(1)
            else:
                print("⚠ --generate without names in non-interactive mode defaults to all functions")
                functions = None
        if quickstart.run_workflow(
            functions=functions,
            max_fix_attempts=args.max_fix_attempts,
            max_test_fix_attempts=args.max_test_fix_attempts,
            auto_fix_compile_errors=(False if args.no_auto_fix_compile else None),
            auto_fix_test_failures=(False if args.no_auto_fix_test_fail else None),
            llm_triage_enabled=(False if args.disable_llm_triage else None),
            triage_min_confidence=args.triage_min_confidence,
            web_research_enabled=(False if args.disable_web_research else None),
            web_research_max_results=args.web_research_max_results,
            experience_learning_enabled=(False if args.disable_experience_learning else None),
            experience_top_k=args.experience_top_k,
            experience_store_path=args.experience_store_path
        ):
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
