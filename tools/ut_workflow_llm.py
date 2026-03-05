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
import shutil
import re
import difflib
import shlex
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# 添加tools目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from c_code_analyzer import CCodeAnalyzer
from compile_commands_analyzer import CompileCommandsAnalyzer
from llm_client import VLLMClient, create_client
from llm_test_generator import LLMTestGenerator
from experience_store import ExperienceStore


class LLMUTWorkflow:
    """集成LLM的UT生成工作流"""
    
    def __init__(self, project_dir: str, compile_commands_file: str,
                 test_output_dir: Optional[str] = None,
                 include_dir: Optional[str] = None,
                 src_dir: Optional[str] = None,
                 llm_api_base: Optional[str] = None,
                 llm_model: Optional[str] = None,
                 experience_store_path: Optional[str] = None,
                 experience_learning_enabled: bool = True,
                 experience_top_k: int = 3,
                 cmakelists_autogen_enabled: bool = False,
                 compile_command_template: Optional[str] = None,
                 compile_command_cwd: Optional[str] = None,
                 run_command_template: Optional[str] = None,
                 run_command_cwd: Optional[str] = None):
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
        
        # 初始化LLM测试生成器（传入compile_analyzer用于提取完整的include）
        self.test_generator = LLMTestGenerator(self.llm_client, compile_analyzer=self.compile_analyzer)

        self.experience_learning_enabled = bool(experience_learning_enabled)
        self.experience_top_k = max(1, int(experience_top_k or 3))
        self.cmakelists_autogen_enabled = bool(cmakelists_autogen_enabled)
        self.experience_store = None
        self.function_status_index_path = os.path.join(
            self.project_dir,
            "log",
            "function_status_index.json"
        )
        self.compile_command_template = str(compile_command_template or "").strip() or None
        self.compile_command_cwd = str(compile_command_cwd or "").strip() or None
        self.run_command_template = str(run_command_template or "").strip() or None
        self.run_command_cwd = str(run_command_cwd or "").strip() or None
        self._current_target_functions_for_cmake_sync: Optional[List[str]] = None
        if self.experience_learning_enabled:
            exp_path = experience_store_path or os.path.join(self.project_dir, "log", "experience_store.jsonl")
            self.experience_store = ExperienceStore(exp_path)
            print(f"[Memory] Experience store: {exp_path}")

    @staticmethod
    def _shell_quote(value: str) -> str:
        if os.name == 'nt':
            return subprocess.list2cmdline([str(value)])
        return shlex.quote(str(value))

    def _resolve_custom_cwd(self, cwd_value: Optional[str], fallback: str) -> str:
        cwd_text = str(cwd_value or "").strip()
        if not cwd_text:
            return fallback
        if os.path.isabs(cwd_text):
            return cwd_text
        return os.path.abspath(os.path.join(self.project_dir, cwd_text))

    def _build_command_context(self,
                               test_name: str,
                               test_path: str,
                               exe_path: str,
                               build_path: str,
                               include_dirs: Optional[List[str]] = None,
                               source_files_active: Optional[List[str]] = None,
                               runtime_xml_path: Optional[str] = None,
                               gtest_filter: Optional[str] = None) -> Dict[str, str]:
        include_dirs = include_dirs or []
        source_files_active = source_files_active or []
        include_flags = " ".join(include_dirs)
        source_files = " ".join(source_files_active)

        context = {
            "project_dir": self.project_dir,
            "project_dir_q": self._shell_quote(self.project_dir),
            "build_dir": build_path,
            "build_dir_q": self._shell_quote(build_path),
            "test_name": test_name,
            "test_file": os.path.basename(test_path),
            "test_path": test_path,
            "test_path_q": self._shell_quote(test_path),
            "exe_path": exe_path,
            "exe_path_q": self._shell_quote(exe_path),
            "include_flags": include_flags,
            "source_files": source_files,
            "runtime_xml": runtime_xml_path or "",
            "runtime_xml_q": self._shell_quote(runtime_xml_path or ""),
            "gtest_filter": gtest_filter or "",
            "gtest_filter_q": self._shell_quote(gtest_filter or ""),
        }
        return context

    def _render_command_template(self, template: str, context: Dict[str, str]) -> str:
        try:
            return str(template).format(**context)
        except KeyError as e:
            missing = str(e).strip("'")
            raise ValueError(f"Unknown command template placeholder: {missing}")

    def _run_custom_shell_command(self,
                                  command_text: str,
                                  cwd: str,
                                  timeout: int = 120) -> subprocess.CompletedProcess:
        command_steps = self._split_command_steps(command_text)
        if not command_steps:
            return subprocess.CompletedProcess(
                args=command_text,
                returncode=0,
                stdout="",
                stderr=""
            )

        all_stdout: List[str] = []
        all_stderr: List[str] = []

        for idx, step_cmd in enumerate(command_steps, 1):
            print(f"  [CmdStep {idx}/{len(command_steps)}] {step_cmd}")
            result = subprocess.run(
                step_cmd,
                shell=True,
                capture_output=True,
                timeout=timeout,
                text=True,
                cwd=cwd
            )

            step_stdout = result.stdout or ""
            step_stderr = result.stderr or ""
            all_stdout.append(step_stdout)
            all_stderr.append(step_stderr)

            if result.returncode == 0:
                continue

            evidence = (step_stdout + "\n" + step_stderr).strip()
            issue_domain = self._classify_issue_domain(evidence, phase_hint="command_step")
            self._print_key_event(
                f"[CmdReview] step#{idx} failed, domain={issue_domain}",
                bg_code="43"
            )

            if issue_domain == "cmakelists":
                if not self.cmakelists_autogen_enabled:
                    self._print_key_event(
                        "[CmdAction] CMake auto-generation disabled by config, skip auto-fix",
                        bg_code="43"
                    )
                    return subprocess.CompletedProcess(
                        args=command_text,
                        returncode=result.returncode,
                        stdout="\n".join([s for s in all_stdout if s]),
                        stderr="\n".join([s for s in all_stderr if s])
                    )

                self._print_key_event(
                    "[CmdAction] Auto-sync CMakeLists, then LLM-repair if needed",
                    bg_code="45"
                )
                try:
                    self.ensure_cmakelists_for_tests(
                        test_dir=self.test_dir,
                        compile_cwd=cwd,
                        target_functions=self._current_target_functions_for_cmake_sync
                    )
                    retry_result = subprocess.run(
                        step_cmd,
                        shell=True,
                        capture_output=True,
                        timeout=timeout,
                        text=True,
                        cwd=cwd
                    )
                    retry_stdout = retry_result.stdout or ""
                    retry_stderr = retry_result.stderr or ""
                    all_stdout.append(retry_stdout)
                    all_stderr.append(retry_stderr)
                    if retry_result.returncode == 0:
                        self._print_key_event(
                            f"[CmdAction] step#{idx} recovered after CMake sync",
                            bg_code="42"
                        )
                        continue

                    retry_evidence = ((retry_result.stdout or "") + "\n" + (retry_result.stderr or "")).strip()
                    llm_fixed = self._llm_repair_cmakelists(
                        evidence=retry_evidence,
                        compile_cwd=cwd,
                        test_dir=self.test_dir
                    )
                    if llm_fixed:
                        retry2_result = subprocess.run(
                            step_cmd,
                            shell=True,
                            capture_output=True,
                            timeout=timeout,
                            text=True,
                            cwd=cwd
                        )
                        all_stdout.append(retry2_result.stdout or "")
                        all_stderr.append(retry2_result.stderr or "")
                        if retry2_result.returncode == 0:
                            self._print_key_event(
                                f"[CmdAction] step#{idx} recovered after LLM CMake repair",
                                bg_code="42"
                            )
                            continue
                        result = retry2_result
                    else:
                        result = retry_result
                except Exception as cmake_fix_error:
                    all_stderr.append(f"\n[CMakeSyncError] {cmake_fix_error}\n")

            if issue_domain == "test_case":
                self._print_key_event(
                    "[CmdAction] Test-case issue detected -> hand over to existing compile/runtime fix loop",
                    bg_code="45"
                )

            return subprocess.CompletedProcess(
                args=command_text,
                returncode=result.returncode,
                stdout="\n".join([s for s in all_stdout if s]),
                stderr="\n".join([s for s in all_stderr if s])
            )

        return subprocess.CompletedProcess(
            args=command_text,
            returncode=0,
            stdout="\n".join([s for s in all_stdout if s]),
            stderr="\n".join([s for s in all_stderr if s])
        )

    @staticmethod
    def _split_command_steps(command_text: str) -> List[str]:
        text = str(command_text or "").strip()
        if not text:
            return []
        steps = [part.strip() for part in re.split(r"\s*&&\s*", text) if part.strip()]
        return steps or [text]

    @staticmethod
    def _classify_command_issue_domain(output_text: str) -> str:
        text = str(output_text or "").lower()
        if not text:
            return "unknown"

        cmake_signals = [
            "cmakelists.txt",
            "cmake error",
            "cmake error at",
            "the source directory",
            "the build directory",
            "does not appear to contain cmakelists.txt",
            "add_subdirectory",
            "unknown cmake command",
            "target not found",
            "no cmakelists.txt",
            "cannot find source file",
            "cannot specify link libraries for target",
            "no sources given to target"
        ]
        if any(signal in text for signal in cmake_signals):
            return "cmakelists"

        test_case_signals = [
            "_llm_test.cpp",
            "gtest",
            "gmock",
            "expect_call",
            "assert_",
            "[  failed  ]",
            "test body",
            "failure"
        ]
        if any(signal in text for signal in test_case_signals):
            return "test_case"

        return "other"

    @staticmethod
    def _extract_json_object_from_text(raw_text: str) -> Optional[Dict[str, Any]]:
        text = str(raw_text or "").strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return None

        return None

    def _classify_issue_domain(self, output_text: str, phase_hint: str = "compile") -> str:
        """先交给LLM分流，失败时回退到规则分流。"""
        text = str(output_text or "").strip()
        if not text:
            return "unknown"

        prompt = f"""You are classifying build/test failure domain for a C/C++ unit-test workflow.
Return STRICT JSON only:
{{"domain":"cmakelists|test_case|other","confidence":0.0,"reason":"short"}}

Rules:
- domain=cmakelists: CMake configuration / target wiring / CMakeLists related failures
- domain=test_case: generated test code issue (compile/runtime/assert/mock/test logic)
- domain=other: toolchain/env/dependency or unclear
- no markdown, no extra text

Phase hint: {phase_hint}

Evidence:
```
{text[:8000]}
```
"""

        try:
            response = self.llm_client.generate(
                prompt,
                temperature=0.0,
                max_tokens=120,
                top_p=0.9
            )
            parsed = self._extract_json_object_from_text(response)
            if isinstance(parsed, dict):
                domain = str(parsed.get("domain", "")).strip().lower()
                if domain in {"cmakelists", "test_case", "other"}:
                    confidence = parsed.get("confidence", "")
                    reason = str(parsed.get("reason", "")).strip()
                    self._print_key_event(
                        f"[DomainLLM] domain={domain}, confidence={confidence}, reason={reason[:80]}",
                        bg_code="46"
                    )
                    return domain
        except Exception as llm_domain_error:
            print(f"  ⚠ LLM domain classify failed, fallback to rules: {llm_domain_error}")

        fallback = self._classify_command_issue_domain(text)
        self._print_key_event(
            f"[DomainFallback] domain={fallback}",
            bg_code="45"
        )
        return fallback

    @staticmethod
    def _normalize_command_template(value) -> str:
        """支持 execution.*.command 为字符串或字符串数组。"""
        if isinstance(value, str):
            return value.strip()

        if isinstance(value, (list, tuple)):
            parts = [str(item).strip() for item in value if str(item).strip()]
            return " && ".join(parts)

        return str(value or "").strip()

    @staticmethod
    def _default_external_experience_path() -> str:
        """返回仓库外的经验库默认路径（用于不跟Git场景）。"""
        if os.name == 'nt':
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            return os.path.join(base, "c-unit-test-workflow", "experience_store.jsonl")
        return os.path.join(os.path.expanduser("~"), ".local", "share", "c-unit-test-workflow", "experience_store.jsonl")

    def _load_function_status_index(self) -> Dict[str, Dict[str, object]]:
        path = self.function_status_index_path
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            functions = payload.get("functions", {}) if isinstance(payload, dict) else {}
            return functions if isinstance(functions, dict) else {}
        except Exception:
            return {}

    def _save_function_status_index(self, functions: Dict[str, Dict[str, object]]) -> None:
        path = self.function_status_index_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "schema": 1,
            "updated_at": datetime.now().isoformat(),
            "functions": functions,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _update_function_status_index(self,
                                      updates: Dict[str, str],
                                      log_dir: str,
                                      timestamp: str) -> None:
        if not updates:
            return

        existing = self._load_function_status_index()
        updated_at = datetime.now().isoformat()
        for function_name, status in updates.items():
            if not function_name:
                continue
            existing[function_name] = {
                "status": str(status),
                "updated_at": updated_at,
                "test_file": f"{function_name}_llm_test.cpp",
                "last_timestamp": str(timestamp),
                "log_dir": str(log_dir).replace('\\', '/')
            }

        self._save_function_status_index(existing)
    
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
        compile_fix_cfg = config.get('test_generation', {}).get('compile_fix', {})
        exec_cfg = config.get('test_generation', {}).get('execution', {})
        experience_learning_enabled = bool(compile_fix_cfg.get('experience_learning_enabled', True))
        experience_top_k = int(compile_fix_cfg.get('experience_top_k', 3) or 3)
        cmakelists_autogen_enabled = bool(compile_fix_cfg.get('cmakelists_autogen_enabled', False))
        experience_track_in_git = bool(compile_fix_cfg.get('experience_track_in_git', True))
        configured_exp_path = compile_fix_cfg.get('experience_store_path')

        if experience_track_in_git:
            experience_store_path = configured_exp_path or './log/experience_store.jsonl'
            if not os.path.isabs(str(experience_store_path)):
                experience_store_path = os.path.join(project_root, str(experience_store_path))
        else:
            experience_store_path = LLMUTWorkflow._default_external_experience_path()

        # 透传后端/Ollama配置到环境变量（仅在未显式设置环境变量时）
        backend = llm_config.get('backend')
        if backend and 'LLM_BACKEND' not in os.environ:
            os.environ['LLM_BACKEND'] = str(backend)

        if llm_config.get('timeout') is not None and 'VLLM_TIMEOUT' not in os.environ:
            os.environ['VLLM_TIMEOUT'] = str(llm_config.get('timeout'))

        ollama_config = llm_config.get('ollama', {})
        if ollama_config.get('api_base') and 'OLLAMA_API_BASE' not in os.environ:
            os.environ['OLLAMA_API_BASE'] = str(ollama_config.get('api_base'))
        if ollama_config.get('model') and 'OLLAMA_MODEL' not in os.environ:
            os.environ['OLLAMA_MODEL'] = str(ollama_config.get('model'))
        if ollama_config.get('timeout') is not None and 'OLLAMA_TIMEOUT' not in os.environ:
            os.environ['OLLAMA_TIMEOUT'] = str(ollama_config.get('timeout'))
        if ollama_config.get('max_tokens') is not None and 'OLLAMA_MAX_TOKENS' not in os.environ:
            os.environ['OLLAMA_MAX_TOKENS'] = str(ollama_config.get('max_tokens'))
        if ollama_config.get('fallback_from_vllm') is not None and 'VLLM_FALLBACK_TO_OLLAMA' not in os.environ:
            os.environ['VLLM_FALLBACK_TO_OLLAMA'] = str(ollama_config.get('fallback_from_vllm'))
        
        print(f"[Config] Loading from: {config_path}")
        print(f"[Config] Project root: {project_root}")
        print(f"[Config] Compile commands: {compile_commands_file}")
        print(f"[Config] Test output dir: {test_output_dir}")
        print(f"[Config] CMake auto-generation: {cmakelists_autogen_enabled}")
        
        compile_exec_cfg = exec_cfg.get('compile', {}) if isinstance(exec_cfg, dict) else {}
        run_exec_cfg = exec_cfg.get('run', {}) if isinstance(exec_cfg, dict) else {}

        compile_raw = ''
        run_raw = ''
        if isinstance(compile_exec_cfg, dict):
            compile_raw = compile_exec_cfg.get('command', compile_exec_cfg.get('commands', ''))
        if isinstance(run_exec_cfg, dict):
            run_raw = run_exec_cfg.get('command', run_exec_cfg.get('commands', ''))

        compile_template = cls._normalize_command_template(compile_raw)
        compile_cwd = str(compile_exec_cfg.get('cwd', '')).strip() if isinstance(compile_exec_cfg, dict) else ''
        run_template = cls._normalize_command_template(run_raw)
        run_cwd = str(run_exec_cfg.get('cwd', '')).strip() if isinstance(run_exec_cfg, dict) else ''

        return cls(
            project_dir=project_root,
            compile_commands_file=compile_commands_file,
            test_output_dir=test_output_dir,
            include_dir=include_dir,
            src_dir=src_dir,
            llm_api_base=llm_api_base,
            llm_model=llm_model,
            experience_store_path=str(experience_store_path),
            experience_learning_enabled=experience_learning_enabled,
            experience_top_k=experience_top_k,
            cmakelists_autogen_enabled=cmakelists_autogen_enabled,
            compile_command_template=compile_template,
            compile_command_cwd=compile_cwd,
            run_command_template=run_template,
            run_command_cwd=run_cwd
        )

    @staticmethod
    def _summarize_code_change(before_code: str, after_code: str, max_lines: int = 24) -> str:
        if before_code == after_code:
            return "no_text_change"
        diff_lines = list(
            difflib.unified_diff(
                before_code.splitlines(),
                after_code.splitlines(),
                fromfile="before",
                tofile="after",
                lineterm=""
            )
        )
        if not diff_lines:
            return "text_changed"
        preview = "\n".join(diff_lines[:max_lines])
        if len(diff_lines) > max_lines:
            preview += "\n..."
        return preview

    @staticmethod
    def _build_unified_diff(before_code: str,
                            after_code: str,
                            fromfile: str = "before",
                            tofile: str = "after",
                            max_lines: Optional[int] = None) -> str:
        if before_code == after_code:
            return ""

        diff_lines = list(
            difflib.unified_diff(
                before_code.splitlines(),
                after_code.splitlines(),
                fromfile=fromfile,
                tofile=tofile,
                lineterm=""
            )
        )
        if not diff_lines:
            return ""

        if max_lines is not None and max_lines > 0 and len(diff_lines) > max_lines:
            return "\n".join(diff_lines[:max_lines]) + "\n..."

        return "\n".join(diff_lines)

    def _emit_fix_diff(self,
                       before_code: str,
                       after_code: str,
                       log_dir: str,
                       test_name: str,
                       phase: str,
                       attempt: int,
                       timestamp: str,
                       preview_max_lines: int = 40) -> str:
        """输出修复diff预览并保存完整patch日志，返回patch路径（无变化则返回空字符串）。"""
        full_diff = self._build_unified_diff(
            before_code,
            after_code,
            fromfile=f"{test_name}.before.cpp",
            tofile=f"{test_name}.after.cpp"
        )
        if not full_diff:
            self._print_key_event("[Diff] No textual changes after fix step", bg_code="45")
            return ""

        preview = self._build_unified_diff(
            before_code,
            after_code,
            fromfile=f"{test_name}.before.cpp",
            tofile=f"{test_name}.after.cpp",
            max_lines=preview_max_lines
        )
        self._print_key_event(
            f"[Diff] {phase} auto-fix attempt {attempt} patch preview",
            bg_code="44"
        )
        self._print_diff_preview(preview)

        diff_log_path = os.path.join(
            log_dir,
            f"{test_name}_{phase}_diff_attempt{attempt}_{timestamp}.patch"
        )
        with open(diff_log_path, 'w', encoding='utf-8') as diff_file:
            diff_file.write(full_diff)
            diff_file.write("\n")

        print(f"  ↳ Diff patch saved: {diff_log_path}")
        return diff_log_path

    @classmethod
    def _colorize_diff_line(cls, line: str) -> str:
        if not cls._ansi_enabled():
            return line
        if line.startswith("+++") or line.startswith("---"):
            return f"\033[90m{line}\033[0m"
        if line.startswith("@@"):
            return f"\033[36m{line}\033[0m"
        if line.startswith("+"):
            return f"\033[32m{line}\033[0m"
        if line.startswith("-"):
            return f"\033[31m{line}\033[0m"
        return line

    @classmethod
    def _print_diff_preview(cls, diff_text: str) -> None:
        for line in (diff_text or "").splitlines():
            print("    " + cls._colorize_diff_line(line))

    @staticmethod
    def _ansi_enabled() -> bool:
        if os.environ.get("NO_COLOR"):
            return False
        term = (os.environ.get("TERM") or "").lower()
        if term == "dumb":
            return False
        return True

    @classmethod
    def _with_bg(cls, text: str, bg_code: str = "44", fg_code: str = "97") -> str:
        if not cls._ansi_enabled():
            return text
        return f"\033[{bg_code};{fg_code}m{text}\033[0m"

    @classmethod
    def _print_key_node(cls, title: str, bg_code: str = "44") -> None:
        tag = f"  {title}  "
        print(cls._with_bg(tag, bg_code=bg_code, fg_code="97"))

    @classmethod
    def _print_key_event(cls, text: str, bg_code: str = "46") -> None:
        print(cls._with_bg(f" {text} ", bg_code=bg_code, fg_code="30"))

    @staticmethod
    def _normalize_issue_text(text: str) -> str:
        normalized = re.sub(r'\s+', ' ', (text or '').strip().lower())
        return normalized[:240]

    @classmethod
    def _build_issue_fingerprint(cls,
                                 error_type: str,
                                 root_cause: str,
                                 key_symbols: Optional[List[str]] = None,
                                 raw_output: str = "") -> str:
        key_symbols = key_symbols or []
        etype = cls._normalize_issue_text(error_type or "unknown")
        cause = cls._normalize_issue_text(root_cause or "")
        if not cause:
            raw_lines = []
            for line in (raw_output or "").splitlines():
                stripped = line.strip()
                if stripped:
                    raw_lines.append(stripped)
                if len(raw_lines) >= 4:
                    break
            cause = cls._normalize_issue_text(" | ".join(raw_lines))

        symbols = sorted({str(s).strip().lower() for s in key_symbols if str(s).strip()})
        symbols_sig = ",".join(symbols[:6])
        return f"{etype}|{cause}|{symbols_sig}"

    @staticmethod
    def _parse_gtest_xml_result(xml_path: str) -> Dict[str, object]:
        result: Dict[str, object] = {
            "xml_path": xml_path,
            "exists": False,
            "failed_tests": [],
            "failure_locations": [],
            "tests": 0,
            "failures": 0,
            "errors": 0
        }
        if not xml_path or (not os.path.exists(xml_path)):
            return result

        result["exists"] = True
        try:
            root = ET.parse(xml_path).getroot()
            suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
            failed_tests: List[str] = []
            failure_locations: List[Dict[str, object]] = []

            tests = int(root.attrib.get("tests", 0) or 0)
            failures = int(root.attrib.get("failures", 0) or 0)
            errors = int(root.attrib.get("errors", 0) or 0)

            for suite in suites:
                suite_name = suite.attrib.get("name", "")
                for case in suite.findall("testcase"):
                    case_name = case.attrib.get("name", "")
                    class_name = case.attrib.get("classname", "") or suite_name
                    full_name = f"{class_name}.{case_name}" if class_name else case_name

                    failure_nodes = list(case.findall("failure")) + list(case.findall("error"))
                    if failure_nodes:
                        failed_tests.append(full_name)

                    for node in failure_nodes:
                        message = (node.attrib.get("message", "") or (node.text or "")).strip()
                        file_name = (node.attrib.get("file", "") or "").strip()
                        line_no = node.attrib.get("line", "")
                        line_val = int(line_no) if str(line_no).isdigit() else 1
                        failure_locations.append({
                            "test": full_name,
                            "file": file_name.replace('\\', '/'),
                            "line": line_val,
                            "message": message[:300]
                        })

            result["failed_tests"] = sorted({t for t in failed_tests if t})
            result["failure_locations"] = failure_locations[:20]
            result["tests"] = tests
            result["failures"] = failures
            result["errors"] = errors
            return result
        except Exception as xml_error:
            result["parse_error"] = str(xml_error)
            return result

    @staticmethod
    def _extract_failed_tests_from_output(run_output: str) -> List[str]:
        if not run_output:
            return []
        failed: List[str] = []
        for line in run_output.splitlines():
            match = re.search(r"\[\s*FAILED\s*\]\s+([A-Za-z0-9_\./:]+)", line)
            if match:
                name = match.group(1).strip()
                if name and name not in failed:
                    failed.append(name)
        return failed

    @staticmethod
    def _extract_mock_violations(run_output: str, max_items: int = 6) -> List[Dict[str, str]]:
        if not run_output:
            return []

        patterns = [
            ("unexpected_call", r"Unexpected mock function call"),
            ("uninteresting_call", r"Uninteresting mock function call"),
            ("call_count_mismatch", r"Actual function call count doesn't match"),
            ("call_overflow", r"called more times than expected"),
            ("expectation_unmet", r"Expected:.*to be called"),
            ("matcher_mismatch", r"Expected arg|Actual arg|which is"),
        ]

        violations: List[Dict[str, str]] = []
        lines = run_output.splitlines()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            for vtype, pattern in patterns:
                if re.search(pattern, stripped, flags=re.IGNORECASE):
                    context = " | ".join([
                        lines[i].strip()
                        for i in range(max(0, idx - 1), min(len(lines), idx + 2))
                        if lines[i].strip()
                    ])
                    violations.append({
                        "type": vtype,
                        "message": stripped[:280],
                        "context": context[:400]
                    })
                    break
            if len(violations) >= max_items:
                break
        return violations

    def _rerun_failed_tests_for_stability(self,
                                          exe_path: str,
                                          failed_tests: List[str],
                                          log_dir: str,
                                          test_name: str,
                                          timestamp: str,
                                          reruns: int = 2,
                                          run_command_template: Optional[str] = None,
                                          run_command_cwd: Optional[str] = None,
                                          test_path: Optional[str] = None,
                                          build_path: Optional[str] = None) -> Dict[str, object]:
        failed_tests = [t for t in failed_tests if t]
        if not failed_tests:
            return {
                "enabled": False,
                "status": "no_failed_tests",
                "reruns": 0,
                "failed_count_each_run": []
            }

        reruns = max(1, int(reruns or 2))
        filter_value = ":".join(failed_tests[:30])
        failed_count_each_run: List[int] = []
        run_details: List[Dict[str, object]] = []

        for rerun_index in range(1, reruns + 1):
            rerun_xml = os.path.join(
                log_dir,
                f"{test_name}_rerun{rerun_index}_{timestamp}.xml"
            )
            if run_command_template:
                rerun_context = self._build_command_context(
                    test_name=test_name,
                    test_path=test_path or "",
                    exe_path=exe_path,
                    build_path=build_path or self.project_dir,
                    runtime_xml_path=rerun_xml,
                    gtest_filter=filter_value
                )
                rerun_cmd_text = self._render_command_template(run_command_template, rerun_context)
                print(f"  [RunCmd:Rerun#{rerun_index}] {rerun_cmd_text}")
                rerun_result = self._run_custom_shell_command(
                    rerun_cmd_text,
                    cwd=run_command_cwd or self.project_dir,
                    timeout=60
                )
            else:
                rerun_cmd = [exe_path, f"--gtest_filter={filter_value}", f"--gtest_output=xml:{rerun_xml}"]
                print(f"  [RunCmd:Rerun#{rerun_index}] {' '.join(rerun_cmd)}")
                rerun_result = subprocess.run(
                    rerun_cmd,
                    capture_output=True,
                    timeout=60,
                    text=True,
                    cwd=self.project_dir
                )
            rerun_output = (rerun_result.stdout or "") + "\n" + (rerun_result.stderr or "")
            rerun_xml_summary = self._parse_gtest_xml_result(rerun_xml)
            rerun_failed = rerun_xml_summary.get("failed_tests", []) or self._extract_failed_tests_from_output(rerun_output)
            rerun_failed_count = len(rerun_failed)
            failed_count_each_run.append(rerun_failed_count)

            run_details.append({
                "rerun_index": rerun_index,
                "returncode": int(rerun_result.returncode),
                "failed_tests": rerun_failed[:20],
                "failed_count": rerun_failed_count,
                "xml": rerun_xml
            })

        all_zero = all(count == 0 for count in failed_count_each_run)
        all_nonzero = all(count > 0 for count in failed_count_each_run)
        if all_zero:
            stability = "not_reproducible"
        elif all_nonzero:
            stability = "stable_failure"
        else:
            stability = "flaky"

        return {
            "enabled": True,
            "status": stability,
            "reruns": reruns,
            "filter": filter_value,
            "failed_count_each_run": failed_count_each_run,
            "details": run_details
        }
    
    def analyze_codebase(self) -> None:
        """分析代码库"""
        self._print_key_node("[Step 1/4] Analyzing C codebase", bg_code="44")
        print("=" * 60)

        # 统一使用分析器的目录扫描逻辑，避免与quickstart函数选择阶段出现差异
        self.code_analyzer.analyze_directory()
        
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
        self._print_key_node("[Step 2/4] Extracting compile information", bg_code="44")
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
        self._print_key_node("[Step 3/4] Generating tests with LLM", bg_code="44")
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

            same_tu_symbols = sorted([
                other_name
                for other_name, other_dep in functions.items()
                if other_name != fname and other_dep.source_file == fdep.source_file
            ])
            same_tu_external_calls = sorted([
                symbol for symbol in fdep.external_calls
                if symbol in same_tu_symbols
            ])

            extra_context = ""
            if same_tu_external_calls:
                extra_context = (
                    "Linkage constraint: The following called symbols are implemented in the same "
                    f"source file as target function '{fname}': "
                    + ", ".join(same_tu_external_calls)
                    + ". Do NOT redefine/mock-wrap these symbols in test file; "
                      "let production object provide them to avoid duplicate-definition linker errors."
                )
            
            # 生成测试（传递项目根目录）
            test_code = self.test_generator.generate_test_file(
                fdep,
                compile_info=compile_info,
                extra_context=extra_context,
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

    @staticmethod
    def _resolve_target_test_files(test_dir: str,
                                   target_functions: Optional[List[str]] = None) -> List[str]:
        """根据目标函数解析本轮应处理的测试文件列表。"""
        all_tests = sorted([f for f in os.listdir(test_dir) if f.endswith('_llm_test.cpp')])
        if not target_functions:
            return all_tests

        target_set = {str(name).strip() for name in target_functions if str(name).strip()}
        expected = {f"{name}_llm_test.cpp" for name in target_set}
        return [f for f in all_tests if f in expected]

    @staticmethod
    def _read_text_file(path: str) -> str:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _write_text_file(path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def _normalize_cmake_path(path_text: str) -> str:
        return str(path_text or "").replace('\\', '/')

    @classmethod
    def _upsert_marked_block(cls,
                             content: str,
                             begin_marker: str,
                             end_marker: str,
                             block_body: str) -> str:
        block = f"{begin_marker}\n{block_body.rstrip()}\n{end_marker}"
        if begin_marker in content and end_marker in content:
            pattern = re.compile(
                rf"{re.escape(begin_marker)}[\\s\\S]*?{re.escape(end_marker)}",
                re.MULTILINE
            )
            return pattern.sub(block, content, count=1)

        if content and not content.endswith('\n'):
            content += '\n'
        spacer = "\n" if content.strip() else ""
        return f"{content}{spacer}{block}\n"

    def _ensure_test_dir_cmakelists(self,
                                    test_dir: str,
                                    test_files: List[str]) -> str:
        """确保测试目录存在可维护的CMakeLists.txt，并同步本轮测试文件列表。"""
        cmake_path = os.path.join(test_dir, "CMakeLists.txt")
        rel_files = sorted({os.path.basename(f) for f in test_files if f})

        file_lines = "\n".join([f"  {name}" for name in rel_files]) if rel_files else ""
        begin_sources = "# >>> LLM AUTO TEST SOURCES BEGIN >>>"
        end_sources = "# <<< LLM AUTO TEST SOURCES END <<<"
        block_sources = "set(LLM_GENERATED_TEST_SOURCES\n" + file_lines + "\n)"

        begin_targets = "# >>> LLM AUTO TEST TARGETS BEGIN >>>"
        end_targets = "# <<< LLM AUTO TEST TARGETS END <<<"
        block_targets = (
            "if(LLM_GENERATED_TEST_SOURCES)\n"
            "  foreach(llm_test_src IN LISTS LLM_GENERATED_TEST_SOURCES)\n"
            "    get_filename_component(llm_test_name \"${llm_test_src}\" NAME_WE)\n"
            "    if(TARGET ${llm_test_name})\n"
            "      continue()\n"
            "    endif()\n"
            "\n"
            "    add_executable(${llm_test_name} ${llm_test_src})\n"
            "\n"
            "    if(EXISTS \"${CMAKE_CURRENT_LIST_DIR}/../include\")\n"
            "      target_include_directories(${llm_test_name} PRIVATE \"${CMAKE_CURRENT_LIST_DIR}/../include\")\n"
            "    endif()\n"
            "\n"
            "    if(TARGET GTest::gtest_main)\n"
            "      target_link_libraries(${llm_test_name} PRIVATE GTest::gtest_main)\n"
            "    elseif(TARGET gtest_main)\n"
            "      target_link_libraries(${llm_test_name} PRIVATE gtest_main)\n"
            "    elseif(TARGET gtest)\n"
            "      target_link_libraries(${llm_test_name} PRIVATE gtest)\n"
            "    endif()\n"
            "\n"
            "    add_test(NAME ${llm_test_name} COMMAND ${llm_test_name})\n"
            "  endforeach()\n"
            "endif()"
        )

        if os.path.exists(cmake_path):
            existing = self._read_text_file(cmake_path)
            updated = self._upsert_marked_block(existing, begin_sources, end_sources, block_sources)
            updated = self._upsert_marked_block(updated, begin_targets, end_targets, block_targets)
            if "enable_testing()" not in updated:
                updated = updated.rstrip() + "\n\nenable_testing()\n"
        else:
            updated = (
                "cmake_minimum_required(VERSION 3.16)\n"
                "project(LLMGeneratedTests LANGUAGES C CXX)\n\n"
                "enable_testing()\n\n"
                "# Auto-managed by ut_workflow_llm.py\n"
                f"{begin_sources}\n{block_sources}\n{end_sources}\n\n"
                f"{begin_targets}\n{block_targets}\n{end_targets}\n"
            )

        self._write_text_file(cmake_path, updated)
        return cmake_path

    def _llm_repair_cmakelists(self,
                               evidence: str,
                               compile_cwd: str,
                               test_dir: str) -> bool:
        """使用LLM对两个CMakeLists做定向修复，成功返回True。"""
        compile_cmake = os.path.join(compile_cwd, "CMakeLists.txt")
        test_cmake = os.path.join(test_dir, "CMakeLists.txt")

        compile_text = self._read_text_file(compile_cmake) if os.path.exists(compile_cmake) else ""
        test_text = self._read_text_file(test_cmake) if os.path.exists(test_cmake) else ""

        prompt = f"""You are fixing CMakeLists files for a C/C++ test workflow.
Return STRICT JSON only:
{{
  "changed": true,
  "reason": "short",
  "compile_cmakelists": "full file content",
  "test_cmakelists": "full file content"
}}

Rules:
- Keep existing user content unless required to fix the reported error.
- Preserve the managed marker blocks if present.
- Ensure test CMakeLists can build generated *_llm_test.cpp and register tests.
- Do not output markdown.

Error evidence:
```
{str(evidence or '')[:10000]}
```

compile_cwd/CMakeLists.txt current:
```cmake
{compile_text[:12000]}
```

test/CMakeLists.txt current:
```cmake
{test_text[:12000]}
```
"""

        try:
            response = self.llm_client.generate(
                prompt,
                temperature=0.0,
                max_tokens=2500,
                top_p=0.9
            )
            parsed = self._extract_json_object_from_text(response)
            if not isinstance(parsed, dict):
                return False

            new_compile = str(parsed.get("compile_cmakelists", "")).strip()
            new_test = str(parsed.get("test_cmakelists", "")).strip()
            changed = bool(parsed.get("changed", False))

            if (not changed) or (not new_compile) or (not new_test):
                return False

            if new_compile != compile_text:
                self._write_text_file(compile_cmake, new_compile + "\n")
            if new_test != test_text:
                self._write_text_file(test_cmake, new_test + "\n")

            self._print_key_event(
                f"[CMakeLLMFix] Applied LLM CMake repair: {str(parsed.get('reason', ''))[:80]}",
                bg_code="46"
            )
            return True
        except Exception as cmake_llm_error:
            print(f"  ⚠ LLM CMake repair failed: {cmake_llm_error}")
            return False

    def _ensure_compile_cwd_cmakelists(self,
                                       compile_cwd: str,
                                       test_dir: str,
                                       test_files: List[str]) -> str:
        """确保编译工作目录存在CMakeLists.txt并接入测试目录。"""
        cmake_path = os.path.join(compile_cwd, "CMakeLists.txt")
        os.makedirs(compile_cwd, exist_ok=True)

        rel_test_dir = os.path.relpath(test_dir, compile_cwd)
        rel_test_dir = self._normalize_cmake_path(rel_test_dir)

        rel_files = sorted({os.path.basename(f) for f in test_files if f})
        begin = "# >>> LLM AUTO TEST DIR BEGIN >>>"
        end = "# <<< LLM AUTO TEST DIR END <<<"
        files_preview = ", ".join(rel_files[:10])
        if len(rel_files) > 10:
            files_preview += f", ... (+{len(rel_files) - 10})"
        block_body = (
            f"# test_dir: {rel_test_dir}\n"
            f"# generated_tests: {files_preview or 'none'}\n"
            f"if(EXISTS \"${{CMAKE_CURRENT_LIST_DIR}}/{rel_test_dir}/CMakeLists.txt\")\n"
            f"  add_subdirectory(\"{rel_test_dir}\")\n"
            "endif()"
        )

        if os.path.exists(cmake_path):
            existing = self._read_text_file(cmake_path)
            updated = self._upsert_marked_block(existing, begin, end, block_body)
            if "enable_testing()" not in updated:
                updated = updated.rstrip() + "\n\nenable_testing()\n"
        else:
            updated = (
                "cmake_minimum_required(VERSION 3.16)\n"
                "project(UTWorkflowHost LANGUAGES C CXX)\n\n"
                "enable_testing()\n\n"
                "# Auto-managed by ut_workflow_llm.py\n"
                f"{begin}\n{block_body}\n{end}\n"
            )

        self._write_text_file(cmake_path, updated)
        return cmake_path

    def ensure_cmakelists_for_tests(self,
                                    test_dir: str,
                                    compile_cwd: str,
                                    target_functions: Optional[List[str]] = None) -> Dict[str, str]:
        """根据当前测试文件，自动创建/补全测试目录与编译目录的 CMakeLists.txt。"""
        scoped = self._resolve_target_test_files(test_dir, target_functions)
        test_files = [os.path.join(test_dir, name) for name in scoped]

        test_cmake = self._ensure_test_dir_cmakelists(test_dir, test_files)
        compile_cmake = self._ensure_compile_cwd_cmakelists(compile_cwd, test_dir, test_files)

        print(f"[CMakeSync] test dir CMakeLists: {test_cmake}")
        print(f"[CMakeSync] compile cwd CMakeLists: {compile_cmake}")
        print(f"[CMakeSync] synced test files: {len(test_files)}")

        return {
            "test_cmakelists": test_cmake,
            "compile_cmakelists": compile_cmake,
            "tests": str(len(test_files))
        }
    
    def verify_tests(self,
                     test_dir: Optional[str] = None,
                     target_functions: Optional[List[str]] = None) -> bool:
        """验证生成的测试（基本的语法检查）"""
        self._print_key_node("[Step 4/4] Verifying generated tests", bg_code="44")
        print("=" * 60)
        
        if test_dir is None:
            test_dir = self.test_dir
        
        test_files = self._resolve_target_test_files(test_dir, target_functions)
        
        if not test_files:
            print("No test files generated!")
            return False

        if target_functions:
            print(f"Scoped verification for selected functions: {', '.join(target_functions)}")
        
        print(f"Found {len(test_files)} test files")
        
        # 基本的验证
        all_valid = True
        for test_file in test_files:
            filepath = os.path.join(test_dir, test_file)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查必要的包含
            has_gtest = (
                '#include <gtest/gtest.h>' in content
                or '#include "gtest/gtest.h"' in content
            )
            has_tests = 'TEST(' in content or 'TEST_F(' in content
            has_assertions = 'EXPECT_' in content or 'ASSERT_' in content
            
            if has_gtest and has_tests and has_assertions:
                print(f"  ✓ {test_file} - Valid")
            else:
                print(f"  ✗ {test_file} - Invalid (missing gtest={has_gtest}, tests={has_tests}, assertions={has_assertions})")
                all_valid = False
        
        return all_valid

    def run_quality_gates(self,
                          test_dir: Optional[str] = None,
                          strict: bool = False,
                          target_functions: Optional[List[str]] = None) -> bool:
        """
        运行生成测试代码的质量闸门工具：clang-format / clang-tidy / cppcheck

        Args:
            test_dir: 测试文件目录
            strict: 严格模式（任一工具报错即失败）

        Returns:
            质量闸门整体是否通过
        """
        print("\n[Quality] Running quality gates (clang-format / clang-tidy / cppcheck)...")
        print("=" * 60)

        if test_dir is None:
            test_dir = self.test_dir

        log_dir = os.path.join(self.project_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        scoped_files = self._resolve_target_test_files(test_dir, target_functions)
        test_files = [os.path.join(test_dir, f) for f in scoped_files]

        if not test_files:
            print("⚠ No generated test files for quality gates")
            return False if strict else True

        if target_functions:
            print(f"[Quality] Scoped to selected functions: {', '.join(target_functions)}")

        include_dirs = ["-I" + self.include_dir]
        if hasattr(self.compile_analyzer, 'compile_info'):
            for _, compile_info in self.compile_analyzer.compile_info.items():
                include_list = []
                if hasattr(compile_info, 'include_dirs'):
                    include_list = compile_info.include_dirs
                elif isinstance(compile_info, dict):
                    include_list = compile_info.get('includes') or compile_info.get('include_dirs', [])
                for inc in include_list:
                    include_flag = "-I" + inc
                    if include_flag not in include_dirs:
                        include_dirs.append(include_flag)

        tools = {
            "clang-format": self._find_tool("clang-format"),
            "clang-tidy": self._find_tool("clang-tidy"),
            "cppcheck": self._find_tool("cppcheck"),
        }

        passed = True
        tool_failures = []

        for tool_name, tool_path in tools.items():
            if not tool_path:
                print(f"- {tool_name}: not found, skipped")
                continue

            print(f"- {tool_name}: {tool_path}")

            if tool_name == "clang-format":
                for test_file in test_files:
                    # 先自动格式化，保证生成文件最小可读性
                    fmt_result = subprocess.run(
                        [tool_path, "-i", test_file],
                        capture_output=True,
                        text=True,
                        cwd=self.project_dir
                    )
                    if fmt_result.returncode != 0:
                        passed = False
                        tool_failures.append((tool_name, test_file))
                        log_path = os.path.join(log_dir, f"quality_clang_format_{Path(test_file).name}_{timestamp}.log")
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.write(fmt_result.stdout or "")
                            f.write("\n")
                            f.write(fmt_result.stderr or "")
                        print(f"  ✗ clang-format failed for {Path(test_file).name}")
                        print(f"    ↳ log: {log_path}")

            elif tool_name == "clang-tidy":
                for test_file in test_files:
                    tidy_cmd = [
                        tool_path,
                        test_file,
                        "--",
                        "-std=c++14",
                    ]
                    tidy_cmd.extend(include_dirs)
                    tidy_result = subprocess.run(
                        tidy_cmd,
                        capture_output=True,
                        text=True,
                        cwd=self.project_dir
                    )
                    if tidy_result.returncode != 0:
                        passed = False
                        tool_failures.append((tool_name, test_file))
                        log_path = os.path.join(log_dir, f"quality_clang_tidy_{Path(test_file).name}_{timestamp}.log")
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.write("Command:\n")
                            f.write(" ".join(tidy_cmd) + "\n\n")
                            f.write(tidy_result.stdout or "")
                            f.write("\n")
                            f.write(tidy_result.stderr or "")
                        print(f"  ✗ clang-tidy reported issues for {Path(test_file).name}")
                        print(f"    ↳ log: {log_path}")

            elif tool_name == "cppcheck":
                for test_file in test_files:
                    cppcheck_cmd = [
                        tool_path,
                        "--language=c++",
                        "--enable=warning,style,performance,portability",
                        "--std=c++14",
                        "--error-exitcode=1",
                        test_file,
                    ]
                    cppcheck_cmd.extend(include_dirs)
                    cppcheck_result = subprocess.run(
                        cppcheck_cmd,
                        capture_output=True,
                        text=True,
                        cwd=self.project_dir
                    )
                    if cppcheck_result.returncode != 0:
                        passed = False
                        tool_failures.append((tool_name, test_file))
                        log_path = os.path.join(log_dir, f"quality_cppcheck_{Path(test_file).name}_{timestamp}.log")
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.write("Command:\n")
                            f.write(" ".join(cppcheck_cmd) + "\n\n")
                            f.write(cppcheck_result.stdout or "")
                            f.write("\n")
                            f.write(cppcheck_result.stderr or "")
                        print(f"  ✗ cppcheck reported issues for {Path(test_file).name}")
                        print(f"    ↳ log: {log_path}")

        if passed:
            print("✓ Quality gates passed (or no issues from available tools)")
            return True

        print("⚠ Quality gates found issues")
        if strict:
            print("  Strict mode enabled: stopping workflow")
            return False

        print("  Non-strict mode: continue workflow")
        return True

    def _resolve_gtest_link_inputs(self,
                                   include_dirs: List[str],
                                   build_path: str,
                                   prefer_sources: bool = False) -> List[str]:
        """
        解析gtest链接输入，优先级：
        1) 本地已构建的静态库（libgtest_main/libgtest）
        2) gtest源码（gtest-all.cc + gtest_main.cc）
        3) 系统库回退（-lgtest -lgtest_main）
        """
        candidate_roots = [
            build_path,
            os.path.join(self.project_dir, "build"),
            os.path.join(self.project_dir, "build-test"),
            os.path.join(self.project_dir, "cmake-build-debug"),
            os.path.join(self.project_dir, "build-ninja-msvc"),
        ]

        def _find_gtest_sources() -> Optional[List[str]]:
            gtest_root = None
            gmock_root = None
            for inc_flag in include_dirs:
                if not inc_flag.startswith("-I"):
                    continue
                inc_path = inc_flag[2:]
                marker = os.path.join("googletest", "include")
                if marker in inc_path:
                    gtest_root = inc_path.split(marker)[0] + "googletest"
                gmock_marker = os.path.join("googlemock", "include")
                if gmock_marker in inc_path:
                    gmock_root = inc_path.split(gmock_marker)[0] + "googlemock"
                    break

            if not gtest_root:
                for root in candidate_roots:
                    candidate = os.path.join(root, "_deps", "googletest-src", "googletest")
                    if os.path.isdir(candidate):
                        gtest_root = candidate
                        break

            if not gmock_root:
                for root in candidate_roots:
                    candidate = os.path.join(root, "_deps", "googletest-src", "googlemock")
                    if os.path.isdir(candidate):
                        gmock_root = candidate
                        break

            if gtest_root:
                gtest_all = os.path.join(gtest_root, "src", "gtest-all.cc")
                gtest_main = os.path.join(gtest_root, "src", "gtest_main.cc")
                if os.path.exists(gtest_all) and os.path.exists(gtest_main):
                    root_inc = f"-I{gtest_root}"
                    include_inc = f"-I{os.path.join(gtest_root, 'include')}"
                    if root_inc not in include_dirs:
                        include_dirs.append(root_inc)
                    if include_inc not in include_dirs:
                        include_dirs.append(include_inc)

                    source_inputs = [gtest_all, gtest_main]

                    if gmock_root:
                        gmock_all = os.path.join(gmock_root, "src", "gmock-all.cc")
                        if os.path.exists(gmock_all):
                            gmock_root_inc = f"-I{gmock_root}"
                            gmock_include_inc = f"-I{os.path.join(gmock_root, 'include')}"
                            if gmock_root_inc not in include_dirs:
                                include_dirs.append(gmock_root_inc)
                            if gmock_include_inc not in include_dirs:
                                include_dirs.append(gmock_include_inc)
                            source_inputs.insert(0, gmock_all)

                    print(f"[Link] Using gtest/gmock sources: {', '.join(source_inputs)}")
                    return source_inputs
            return None

        # 对非MSVC编译器，优先源码方式避免Windows CRT/ABI不匹配
        if prefer_sources:
            source_inputs = _find_gtest_sources()
            if source_inputs:
                return source_inputs

        # 1) 查找已构建库
        gtest_main_lib = None
        gtest_lib = None
        gmock_lib = None
        lib_main_names = {"libgtest_main.a", "gtest_main.lib", "libgtest_main.so"}
        lib_names = {"libgtest.a", "gtest.lib", "libgtest.so"}
        gmock_names = {"libgmock.a", "gmock.lib", "libgmock.so"}

        for root in candidate_roots:
            if not os.path.isdir(root):
                continue
            for walk_root, _, files in os.walk(root):
                for file_name in files:
                    full_path = os.path.join(walk_root, file_name)
                    if file_name in lib_main_names and gtest_main_lib is None:
                        gtest_main_lib = full_path
                    elif file_name in lib_names and gtest_lib is None:
                        gtest_lib = full_path
                    elif file_name in gmock_names and gmock_lib is None:
                        gmock_lib = full_path
                if gtest_main_lib and gtest_lib and gmock_lib:
                    break
            if gtest_main_lib and gtest_lib and gmock_lib:
                break

        if gtest_main_lib and gtest_lib and gmock_lib:
            print(f"[Link] Using local gtest/gmock libs: {gtest_main_lib}, {gtest_lib}, {gmock_lib}")
            return [gmock_lib, gtest_main_lib, gtest_lib]

        # 2) 查找gtest源码（避免依赖系统安装的 -lgtest）
        source_inputs = _find_gtest_sources()
        if source_inputs:
            return source_inputs

        # 3) 回退到系统库
        print("[Link] Fallback to system gtest libs: -lgtest -lgtest_main")
        return ["-lgtest", "-lgtest_main"]

    @staticmethod
    def _is_toolchain_link_error(stderr_text: str) -> bool:
        """判断是否为工具链/库缺失类错误（不适合LLM改代码修复）"""
        if not stderr_text:
            return False
        lower = stderr_text.lower()
        return (
            "cannot find -lgtest" in lower
            or "cannot find -lgtest_main" in lower
            or "ld returned 1 exit status" in lower and "cannot find -l" in lower
            or "library not found for -lgtest" in lower
            or "lnk2005" in lower
            or "lnk2038" in lower
            or "lnk1561" in lower
            or "must define an entry point" in lower
            or "invalid argument '-std=c++14' not allowed with 'c'" in lower
            or "clang++: error: invalid argument" in lower
        )

    @staticmethod
    def _extract_unresolved_symbols(error_text: str) -> List[str]:
        """从链接错误输出中提取未解析符号名。"""
        if not error_text:
            return []

        patterns = [
            r"无法解析的外部符号\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"unresolved external symbol\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"undefined reference to [`']([A-Za-z_][A-Za-z0-9_]*)",
        ]

        skip = {
            "main",
            "WinMain",
            "DllMain",
        }

        symbols: List[str] = []
        seen = set()
        for pattern in patterns:
            for match in re.findall(pattern, error_text, flags=re.IGNORECASE):
                symbol = match.strip()
                if not symbol or symbol in skip or symbol.startswith("__"):
                    continue
                if symbol not in seen:
                    seen.add(symbol)
                    symbols.append(symbol)

        return symbols

    @staticmethod
    def _extract_duplicate_symbols(error_text: str) -> List[str]:
        """从链接重复定义错误输出中提取符号名。"""
        if not error_text:
            return []

        patterns = [
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s+已经在\s+.*中定义",
            r"LNK2005\s+([A-Za-z_][A-Za-z0-9_]*)\s+already defined",
            r"multiple definition of [`']([A-Za-z_][A-Za-z0-9_]*)",
        ]

        symbols: List[str] = []
        seen = set()
        for pattern in patterns:
            for match in re.findall(pattern, error_text, flags=re.IGNORECASE):
                symbol = str(match).strip()
                if symbol and symbol not in seen:
                    seen.add(symbol)
                    symbols.append(symbol)
        return symbols

    @staticmethod
    def _remove_symbol_definitions_from_test_file(test_path: str,
                                                  symbols: List[str],
                                                  protected_symbols: Optional[List[str]] = None) -> List[str]:
        """从测试文件移除指定符号函数定义，用于解决重复定义冲突。"""
        if not symbols:
            return []

        protected = {s for s in (protected_symbols or []) if s}

        with open(test_path, 'r', encoding='utf-8') as f:
            content = f.read()

        removed_symbols: List[str] = []
        for symbol in symbols:
            if symbol in protected:
                continue

            pattern = re.compile(
                rf'\b{re.escape(symbol)}\s*\([^;{{}}]*\)\s*\{{',
                re.MULTILINE
            )

            search_pos = 0
            while True:
                match = pattern.search(content, search_pos)
                if not match:
                    break

                brace_open = content.find('{', match.end() - 1)
                if brace_open == -1:
                    break

                brace_count = 1
                end_pos = brace_open + 1
                while end_pos < len(content) and brace_count > 0:
                    ch = content[end_pos]
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                    end_pos += 1

                if brace_count != 0:
                    search_pos = match.end()
                    continue

                line_start = content.rfind('\n', 0, match.start())
                line_start = 0 if line_start == -1 else line_start + 1
                delete_end = end_pos
                if delete_end < len(content) and content[delete_end:delete_end + 1] == '\n':
                    delete_end += 1

                content = content[:line_start] + content[delete_end:]
                removed_symbols.append(symbol)
                search_pos = line_start

        if removed_symbols:
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 去重保序
        dedup: List[str] = []
        seen = set()
        for item in removed_symbols:
            if item not in seen:
                seen.add(item)
                dedup.append(item)
        return dedup

    @staticmethod
    def _remove_symbol_definitions_from_code(content: str,
                                             symbols: List[str],
                                             protected_symbols: Optional[List[str]] = None) -> (str, List[str]):
        """从代码文本中移除指定符号函数定义，返回(新代码, 移除符号列表)。"""
        if not symbols:
            return content, []

        protected = {s for s in (protected_symbols or []) if s}
        updated = content
        removed_symbols: List[str] = []

        for symbol in symbols:
            if symbol in protected:
                continue

            pattern = re.compile(
                rf'\b{re.escape(symbol)}\s*\([^;{{}}]*\)\s*\{{',
                re.MULTILINE
            )

            search_pos = 0
            while True:
                match = pattern.search(updated, search_pos)
                if not match:
                    break

                brace_open = updated.find('{', match.end() - 1)
                if brace_open == -1:
                    break

                brace_count = 1
                end_pos = brace_open + 1
                while end_pos < len(updated) and brace_count > 0:
                    ch = updated[end_pos]
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                    end_pos += 1

                if brace_count != 0:
                    search_pos = match.end()
                    continue

                line_start = updated.rfind('\n', 0, match.start())
                line_start = 0 if line_start == -1 else line_start + 1
                delete_end = end_pos
                if delete_end < len(updated) and updated[delete_end:delete_end + 1] == '\n':
                    delete_end += 1

                updated = updated[:line_start] + updated[delete_end:]
                removed_symbols.append(symbol)
                search_pos = line_start

        dedup: List[str] = []
        seen = set()
        for item in removed_symbols:
            if item not in seen:
                seen.add(item)
                dedup.append(item)
        return updated, dedup

    def _inject_linker_stubs(self, test_path: str, symbols: List[str]) -> List[str]:
        """向测试文件注入最小C链接桩函数，解决与目标测试无关的未解析符号。"""
        if not symbols:
            return []

        with open(test_path, 'r', encoding='utf-8') as f:
            content = f.read()

        function_map = self.code_analyzer.get_all_functions()
        stubs: List[str] = []
        vars_to_define: List[str] = []
        injected_symbols: List[str] = []

        for symbol in symbols:
            if symbol == "g_next_id":
                has_definition = re.search(
                    r"(?:^|\n)\s*(?:static\s+)?(?:extern\s+)?[A-Za-z_][A-Za-z0-9_\s\*]*\bg_next_id\s*=",
                    content
                ) is not None
                if not has_definition:
                    vars_to_define.append("int32_t g_next_id = 0;")
                    injected_symbols.append(symbol)
                continue

            if re.search(rf"\b{re.escape(symbol)}\s*\(", content):
                continue

            func_dep = function_map.get(symbol)
            if not func_dep:
                continue

            return_type = (func_dep.return_type or "int").strip()
            params = func_dep.parameters or []
            if not params:
                param_sig = "void"
            else:
                param_parts: List[str] = []
                for idx, param in enumerate(params):
                    ptype = (param[0] or "int").strip()
                    pname = (param[1] or f"arg{idx}").strip()

                    while pname.startswith("*"):
                        ptype += " *"
                        pname = pname[1:].strip()

                    if not pname:
                        pname = f"arg{idx}"

                    param_parts.append(f"{ptype} {pname}")
                param_sig = ", ".join(param_parts)

            if return_type == "void":
                body = "return;"
            else:
                body = f"return ({return_type})0;"

            stubs.append(f"{return_type} {symbol}({param_sig}) {{ {body} }}")
            injected_symbols.append(symbol)

        if not stubs and not vars_to_define:
            return []

        block_lines = []
        if vars_to_define:
            block_lines.extend(vars_to_define)
        if stubs:
            block_lines.append('extern "C" {')
            block_lines.extend(stubs)
            block_lines.append("}")

        block = "\n\n" + "\n".join(block_lines) + "\n"
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(content.rstrip() + block + "\n")

        return injected_symbols

    @staticmethod
    def _c_symbol_to_mock_method_name(symbol: str) -> str:
        """将C符号名映射为常见Mock方法命名（snake_case -> PascalCase）。"""
        raw = str(symbol or "").strip().strip("_")
        if not raw:
            return ""
        parts = [p for p in re.split(r"_+", raw) if p]
        return "".join(part[:1].upper() + part[1:] for part in parts)

    @staticmethod
    def _extract_never_called_mock_methods(runtime_output: str) -> List[str]:
        """从gMock输出中提取 never called 的 EXPECT_CALL 方法名。"""
        if not runtime_output:
            return []

        pattern = re.compile(
            r"EXPECT_CALL\(\s*mock_\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\([^\)]*\)\s*\)"
            r"[\s\S]{0,400}?never called",
            re.IGNORECASE
        )

        methods: List[str] = []
        seen = set()
        for match in pattern.findall(runtime_output):
            method = str(match).strip()
            if method and method not in seen:
                seen.add(method)
                methods.append(method)
        return methods

    @staticmethod
    def _remove_expect_call_blocks_for_methods(test_path: str,
                                               method_names: List[str]) -> List[str]:
        """从测试文件中移除指定方法的 EXPECT_CALL 语句块（含链式 Times/WillOnce）。"""
        if not method_names:
            return []

        with open(test_path, 'r', encoding='utf-8') as f:
            content = f.read()

        removed: List[str] = []
        for method in method_names:
            method = str(method or "").strip()
            if not method:
                continue

            pattern = re.compile(
                rf"^[ \t]*EXPECT_CALL\(\s*mock_\s*,\s*{re.escape(method)}\s*\([^\)]*\)\s*\)"
                rf"[\s\S]*?;[ \t]*\n?",
                re.MULTILINE
            )

            changed = False
            while True:
                new_content, count = pattern.subn("", content, count=1)
                if count <= 0:
                    break
                content = new_content
                changed = True

            if changed:
                removed.append(method)

        if removed:
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return removed

    def _get_same_tu_unmockable_symbols(self, target_symbol: str) -> List[str]:
        """找出目标函数 external_calls 中与其同源文件定义的符号（不应在测试里重定义/mock-wrapper）。"""
        symbol = str(target_symbol or "").strip()
        if not symbol:
            return []

        try:
            functions = self.code_analyzer.get_all_functions()
        except Exception:
            return []

        dep = functions.get(symbol)
        if not dep:
            return []

        same_tu_symbols: List[str] = []
        for callee in (dep.external_calls or []):
            callee_name = str(callee or "").strip()
            if not callee_name:
                continue
            callee_dep = functions.get(callee_name)
            if not callee_dep:
                continue
            if callee_dep.source_file == dep.source_file:
                same_tu_symbols.append(callee_name)

        return sorted(list(dict.fromkeys(same_tu_symbols)))

    @staticmethod
    def _find_tool(tool_name: str) -> Optional[str]:
        """查找工具可执行文件，支持PATH和常见Windows安装目录兜底。"""
        found = shutil.which(tool_name)
        if found:
            return found

        if os.name == 'nt':
            common_paths = {
                "clang++": ["C:/Program Files/LLVM/bin/clang++.exe"],
                "clang-format": ["C:/Program Files/LLVM/bin/clang-format.exe"],
                "clang-tidy": ["C:/Program Files/LLVM/bin/clang-tidy.exe"],
                "cppcheck": [
                    "C:/Program Files/cppcheck/cppcheck.exe",
                    "C:/Program Files (x86)/Cppcheck/cppcheck.exe",
                ],
            }
            for path in common_paths.get(tool_name, []):
                if os.path.exists(path):
                    return path

        return None

    @staticmethod
    def _detect_cpp_compiler() -> Optional[str]:
        """检测可用的C++编译器，优先顺序适配Windows/Linux。"""
        configured = os.getenv("CXX")
        if configured:
            configured = configured.strip()
            if configured:
                if os.path.exists(configured):
                    return configured
                configured_which = shutil.which(configured)
                if configured_which:
                    return configured_which

        for compiler in ["g++", "clang++", "cl"]:
            path = LLMUTWorkflow._find_tool(compiler)
            if path:
                return path
        return None

    @staticmethod
    def _is_msvc_compiler(compiler_path: str) -> bool:
        name = os.path.basename(compiler_path).lower()
        return name in ("cl", "cl.exe")

    def _build_compile_command(self,
                               compiler_path: str,
                               include_dirs: List[str],
                               source_files: List[str],
                               test_path: str,
                               exe_path: str,
                               gtest_link_inputs: List[str]) -> List[str]:
        """按编译器类型构建编译命令。"""
        if self._is_msvc_compiler(compiler_path):
            cmd = [compiler_path, "/nologo", "/EHsc", "/std:c++14", f"/Fe:{exe_path}"]

            for inc in include_dirs:
                if inc.startswith("-I"):
                    cmd.append(f"/I{inc[2:]}")

            if source_files:
                cmd.append("/TC")
                cmd.extend(source_files)
            cmd.append("/TP")
            cmd.append(test_path)

            for item in gtest_link_inputs:
                if item.startswith("-l"):
                    lib_name = item[2:]
                    cmd.append(f"{lib_name}.lib")
                else:
                    cmd.append(item)

            return cmd

        # GCC/Clang 风格
        cmd = [
            compiler_path,
            "-std=c++14",
            "-D_CRT_SECURE_NO_WARNINGS",
            "-ffunction-sections",
            "-fdata-sections",
            "-Wno-deprecated",
            "-Wno-deprecated-declarations",
            "-o",
            exe_path
        ]
        cmd.extend(include_dirs)
        cmd.append("-I/usr/include/gtest")
        # 对clang++/g++直接传入.c与.cpp，避免-std与-x c冲突
        cmd.extend(source_files)
        cmd.append(test_path)
        cmd.extend(gtest_link_inputs)

        if os.name == 'nt':
            cmd.append("-Wl,/OPT:REF")

        # Windows上使用MinGW可加上pthread，MSVC路径不需要
        if os.name != 'nt':
            cmd.append("-lpthread")

        return cmd

    def _resolve_source_files_for_test(self, test_name: str, all_sources: List[str]) -> List[str]:
        """按测试名解析最小源文件集合，避免不必要的重复符号链接。"""
        function_name = test_name.replace("_llm_test", "")
        function_map = self.code_analyzer.get_all_functions()
        func_dep = function_map.get(function_name)
        if not func_dep:
            return all_sources

        source_file = func_dep.source_file
        source_path = source_file if os.path.isabs(source_file) else os.path.join(self.project_dir, source_file)
        source_path = os.path.abspath(source_path)

        if os.path.exists(source_path):
            return [source_path]

        return all_sources
    
    def run_tests(self, test_dir: Optional[str] = None,
                  build_dir: str = "build-test",
                  target_functions: Optional[List[str]] = None,
                  auto_fix_compile_errors: bool = True,
                  max_fix_attempts: int = 2,
                  auto_fix_test_failures: bool = True,
                  max_test_fix_attempts: int = 2,
                  llm_triage_enabled: bool = True,
                  triage_min_confidence: float = 0.55,
                  web_research_enabled: bool = True,
                  web_research_max_results: int = 4,
                  experience_learning_enabled: bool = True,
                  experience_top_k: int = 3,
                  compile_command_template: Optional[str] = None,
                  compile_command_cwd: Optional[str] = None,
                  run_command_template: Optional[str] = None,
                  run_command_cwd: Optional[str] = None) -> bool:
        """
        编译并执行生成的测试用例
        
        Args:
            test_dir: 测试文件所在目录
            build_dir: 测试编译目录
            target_functions: 本轮限定处理的函数列表（仅处理对应测试文件）
            auto_fix_compile_errors: 编译失败后是否自动进入LLM修复阶段
            max_fix_attempts: 最大自动修复重试次数
            auto_fix_test_failures: 测试运行失败后是否自动进入LLM修复阶段
            max_test_fix_attempts: 测试运行失败最大自动修复重试次数
            llm_triage_enabled: 是否启用“先分析再修复”诊断阶段
            triage_min_confidence: 触发修复的最低诊断置信度
            web_research_enabled: triage后是否进行在线检索增强
            web_research_max_results: 在线检索最多返回条数
            experience_learning_enabled: 是否启用经验积累与检索
            experience_top_k: 经验检索返回条数
            
        Returns:
            是否执行成功
        """
        self._print_key_node("[Step 5/5] Compiling and running tests", bg_code="45")
        print("=" * 60)
        
        if test_dir is None:
            test_dir = self.test_dir

        log_dir = os.path.join(self.project_dir, "log")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        test_files = self._resolve_target_test_files(test_dir, target_functions)
        
        if not test_files:
            print("✗ No test files found to run!")
            self._current_target_functions_for_cmake_sync = None
            return False

        if target_functions:
            print(f"Scoped run for selected functions: {', '.join(target_functions)}")
        self._current_target_functions_for_cmake_sync = list(target_functions or [])
        
        print(f"Found {len(test_files)} test file(s) to run")

        effective_compile_template = self._normalize_command_template(
            compile_command_template if compile_command_template is not None else (self.compile_command_template or "")
        )
        effective_compile_cwd = self._resolve_custom_cwd(
            compile_command_cwd if compile_command_cwd is not None else self.compile_command_cwd,
            fallback=self.project_dir
        )
        effective_run_template = self._normalize_command_template(
            run_command_template if run_command_template is not None else (self.run_command_template or "")
        )
        effective_run_cwd = self._resolve_custom_cwd(
            run_command_cwd if run_command_cwd is not None else self.run_command_cwd,
            fallback=self.project_dir
        )

        if effective_compile_template:
            print(f"[Build] Using custom compile command template (cwd={effective_compile_cwd})")
        if effective_run_template:
            print(f"[Run] Using custom run command template (cwd={effective_run_cwd})")

        if self.cmakelists_autogen_enabled:
            try:
                self.ensure_cmakelists_for_tests(
                    test_dir=test_dir,
                    compile_cwd=effective_compile_cwd,
                    target_functions=target_functions
                )
            except Exception as cmake_sync_error:
                print(f"⚠ CMake sync skipped due to error: {cmake_sync_error}")
        else:
            print("[CMakeSync] Auto-generation disabled by config")
        
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

        compiler_path = self._detect_cpp_compiler()
        if not compiler_path:
            print("✗ No C++ compiler found (expected one of: g++, clang++, cl)")
            print("  Please install a compiler or run from a Developer Command Prompt.")
            self._current_target_functions_for_cmake_sync = None
            return False
        print(f"[Build] Using compiler: {compiler_path}")
        
        # 尝试编译并运行每个测试文件
        all_passed = True
        results = []
        
        for test_file in test_files:
            test_path = os.path.join(test_dir, test_file)
            test_name = os.path.splitext(test_file)[0]
            target_symbol = test_name.replace("_llm_test", "")
            exe_path = os.path.join(build_path, test_name)
            if self._is_msvc_compiler(compiler_path) and not exe_path.lower().endswith('.exe'):
                exe_path += '.exe'
            
            self._print_key_node(f"[Test] {test_file}", bg_code="100")
            print("-" * 40)
            
            # 构建编译命令
            # 收集include目录
            include_dirs = ["-I" + self.include_dir]
            
            # 从compile_commands.json中提取include路径
            if hasattr(self.compile_analyzer, 'compile_info'):
                for src_file, compile_info in self.compile_analyzer.compile_info.items():
                    include_list = []
                    if hasattr(compile_info, 'include_dirs'):
                        include_list = compile_info.include_dirs
                    elif isinstance(compile_info, dict):
                        include_list = compile_info.get('includes') or compile_info.get('include_dirs', [])
                    
                    for inc in include_list:
                        include_flag = "-I" + inc
                        if include_flag not in include_dirs:
                            include_dirs.append(include_flag)
            
            # 准备编译命令
            source_files_for_test = self._resolve_source_files_for_test(test_name, source_files)
            source_files_active = list(source_files_for_test)
            full_source_link_mode = False

            gtest_link_inputs = self._resolve_gtest_link_inputs(
                include_dirs,
                build_path,
                prefer_sources=(os.name == 'nt' and not self._is_msvc_compiler(compiler_path))
            )
            compile_cmd = self._build_compile_command(
                compiler_path=compiler_path,
                include_dirs=include_dirs,
                source_files=source_files_active,
                test_path=test_path,
                exe_path=exe_path,
                gtest_link_inputs=gtest_link_inputs
            )
            
            try:
                compile_result = None
                llm_fix_count = 0
                runtime_fix_count = 0
                compile_round = 0
                max_compile_rounds = max_fix_attempts + 2
                compile_seen_issue_fingerprints = set()
                runtime_seen_issue_fingerprints = set()
                compile_issue_counts = defaultdict(int)
                runtime_issue_counts = defaultdict(int)
                compile_consumed_attempts = 0
                runtime_consumed_attempts = 0
                runtime_prev_failed_tests = None
                test_finished = False
                same_tu_unmockable_symbols = self._get_same_tu_unmockable_symbols(target_symbol)
                blocked_redefinition_symbols = set(same_tu_unmockable_symbols)

                if same_tu_unmockable_symbols:
                    with open(test_path, 'r', encoding='utf-8') as f:
                        precheck_before_code = f.read()
                    pre_removed = self._remove_symbol_definitions_from_test_file(
                        test_path=test_path,
                        symbols=same_tu_unmockable_symbols,
                        protected_symbols=[target_symbol]
                    )
                    if pre_removed:
                        with open(test_path, 'r', encoding='utf-8') as f:
                            precheck_after_code = f.read()
                        self._emit_fix_diff(
                            before_code=precheck_before_code,
                            after_code=precheck_after_code,
                            log_dir=log_dir,
                            test_name=test_name,
                            phase="precheck",
                            attempt=1,
                            timestamp=timestamp
                        )
                        self._print_key_event(
                            "[PreCheck] Removed same-TU symbol definitions before compile: "
                            + ", ".join(pre_removed[:6])
                            + (" ..." if len(pre_removed) > 6 else ""),
                            bg_code="45"
                        )

                while not test_finished:
                    compile_success = False

                    while compile_round < max_compile_rounds:
                        if compile_round == 0:
                            print(f"Compiling: {test_name}...")
                        else:
                            print(
                                f"Compiling after retry {compile_round}/{max_compile_rounds - 1}: {test_name}..."
                            )

                        if effective_compile_template:
                            compile_context = self._build_command_context(
                                test_name=test_name,
                                test_path=test_path,
                                exe_path=exe_path,
                                build_path=build_path,
                                include_dirs=include_dirs,
                                source_files_active=source_files_active,
                            )
                            compile_cmd_display = self._render_command_template(
                                effective_compile_template,
                                compile_context
                            )
                            print(f"  [CompileCmd] {compile_cmd_display}")
                            compile_result = self._run_custom_shell_command(
                                compile_cmd_display,
                                cwd=effective_compile_cwd,
                                timeout=120
                            )
                        else:
                            compile_cmd_display = ' '.join(compile_cmd)
                            print(f"  [CompileCmd] {compile_cmd_display}")
                            compile_result = subprocess.run(
                                compile_cmd,
                                capture_output=True,
                                timeout=120,
                                text=True,
                                cwd=self.project_dir
                            )

                        if compile_result.returncode == 0:
                            compile_success = True
                            break

                        print(f"  ✗ Compilation failed")
                        if compile_result.stderr:
                            error_lines = compile_result.stderr.split('\n')[:5]
                            for line in error_lines:
                                if line.strip():
                                    print(f"    {line}")
                            if len(compile_result.stderr.split('\n')) > 5:
                                print(f"    ... (more errors)")

                        compile_log_path = os.path.join(log_dir, f"{test_name}_compile_attempt{compile_round}_{timestamp}.log")
                        with open(compile_log_path, 'w', encoding='utf-8') as log_file:
                            log_file.write("Compile command:\n")
                            log_file.write(compile_cmd_display + "\n\n")
                            log_file.write("STDOUT:\n")
                            log_file.write(compile_result.stdout or "")
                            log_file.write("\nSTDERR:\n")
                            log_file.write(compile_result.stderr or "")
                        print(f"  ↳ Compile log saved: {compile_log_path}")

                        compile_output_full = (compile_result.stdout or "") + "\n" + (compile_result.stderr or "")

                        issue_domain = self._classify_issue_domain(compile_output_full, phase_hint="compile")
                        if issue_domain == "cmakelists":
                            if not self.cmakelists_autogen_enabled:
                                self._print_key_event(
                                    "[CompileRoute] CMake auto-generation disabled by config -> stop compile auto-fix",
                                    bg_code="43"
                                )
                                break

                            self._print_key_event(
                                "[CompileRoute] CMakeLists issue detected -> sync CMake and retry compile",
                                bg_code="45"
                            )
                            try:
                                self.ensure_cmakelists_for_tests(
                                    test_dir=test_dir,
                                    compile_cwd=effective_compile_cwd,
                                    target_functions=target_functions
                                )
                                self._llm_repair_cmakelists(
                                    evidence=compile_output_full,
                                    compile_cwd=effective_compile_cwd,
                                    test_dir=test_dir
                                )
                            except Exception as cmake_sync_error:
                                print(f"  ⚠ CMake sync failed: {cmake_sync_error}")
                                print("    Skip test-code auto-fix because issue belongs to CMake/project setup")
                                break

                            compile_round += 1
                            continue

                        duplicate_symbols = self._extract_duplicate_symbols(compile_output_full)
                        if duplicate_symbols:
                            with open(test_path, 'r', encoding='utf-8') as f:
                                detfix_before_code = f.read()
                            removed_symbols = self._remove_symbol_definitions_from_test_file(
                                test_path=test_path,
                                symbols=duplicate_symbols,
                                protected_symbols=[test_name.replace("_llm_test", "")]
                            )
                            if removed_symbols:
                                blocked_redefinition_symbols.update(removed_symbols)
                                with open(test_path, 'r', encoding='utf-8') as f:
                                    detfix_after_code = f.read()
                                self._emit_fix_diff(
                                    before_code=detfix_before_code,
                                    after_code=detfix_after_code,
                                    log_dir=log_dir,
                                    test_name=test_name,
                                    phase="compile_detfix",
                                    attempt=compile_round + 1,
                                    timestamp=timestamp
                                )
                                self._print_key_event(
                                    "[DeterministicFix] Removed duplicate symbol definitions: "
                                    + ", ".join(removed_symbols[:6])
                                    + (" ..." if len(removed_symbols) > 6 else ""),
                                    bg_code="45"
                                )
                                compile_round += 1
                                continue

                        unresolved_symbols = self._extract_unresolved_symbols(
                            compile_output_full
                        )

                        if (
                            unresolved_symbols
                            and (not full_source_link_mode)
                            and target_symbol in unresolved_symbols
                            and len(source_files_active) < len(source_files)
                        ):
                            full_source_link_mode = True
                            source_files_active = list(source_files)
                            compile_cmd = self._build_compile_command(
                                compiler_path=compiler_path,
                                include_dirs=include_dirs,
                                source_files=source_files_active,
                                test_path=test_path,
                                exe_path=exe_path,
                                gtest_link_inputs=gtest_link_inputs
                            )
                            self._print_key_event(
                                "[Escalation] Target symbol unresolved -> switch to full-source linking",
                                bg_code="45"
                            )
                            compile_round += 1
                            continue

                        if unresolved_symbols:
                            injected_symbols = self._inject_linker_stubs(test_path, unresolved_symbols)
                            if injected_symbols:
                                print(
                                    f"  [Fix] Injected {len(injected_symbols)} linker stub(s): "
                                    + ", ".join(injected_symbols[:6])
                                    + (" ..." if len(injected_symbols) > 6 else "")
                                )
                                if compile_round >= max_compile_rounds - 1:
                                    max_compile_rounds += 1
                                compile_round += 1
                                continue

                        if self._is_toolchain_link_error(compile_result.stderr or ""):
                            self._print_key_event("⚠ Linker/toolchain issue detected", bg_code="43")
                            print("  ⚠ Linker/toolchain error detected (e.g. missing gtest library).")
                            print("    Skipping LLM code-fix because this is not a test code issue.")
                            break

                        if not auto_fix_compile_errors:
                            break

                        triage_result = {
                            "error_type": "unknown",
                            "root_cause": "triage_skipped",
                            "should_fix": True,
                            "confidence": 1.0,
                            "fix_strategy": ["direct_fix"],
                            "key_symbols": [],
                            "minimal_change": "apply minimal compile fix",
                            "code_locations": [],
                            "change_direction": ["apply minimal compile fix around first diagnostic location"]
                        }

                        if llm_triage_enabled:
                            try:
                                with open(test_path, 'r', encoding='utf-8') as f:
                                    current_test_code = f.read()

                                compile_output = (compile_result.stdout or "") + "\n" + (compile_result.stderr or "")
                                navigation_context = self.compile_analyzer.build_ordered_navigation_context(
                                    compiler_output=compile_output,
                                    key_symbols=[],
                                    max_locations=8
                                )

                                triage_result = self.test_generator.analyze_compile_error(
                                    current_test_code=current_test_code,
                                    compile_error=compile_output,
                                    function_name=test_name.replace("_llm_test", ""),
                                    navigation_context=navigation_context
                                )

                                enriched_navigation = self.compile_analyzer.build_ordered_navigation_context(
                                    compiler_output=compile_output,
                                    key_symbols=triage_result.get("key_symbols", []),
                                    max_locations=8
                                )
                                triage_result["code_locations"] = enriched_navigation.get("code_locations", [])
                                triage_result["ordered_navigation"] = enriched_navigation.get("ordered_navigation", [])
                                triage_result["scope"] = enriched_navigation.get("scope", {})

                                if web_research_enabled:
                                    try:
                                        web_research = self.test_generator.research_root_cause_online(
                                            root_cause=str(triage_result.get("root_cause", "")),
                                            error_type=str(triage_result.get("error_type", "unknown")),
                                            key_symbols=triage_result.get("key_symbols", []),
                                            max_results=web_research_max_results
                                        )
                                        triage_result["web_research"] = web_research
                                        print(
                                            f"  [Research] query='{web_research.get('query', '')}', "
                                            f"refs={web_research.get('count', 0)}"
                                        )
                                    except Exception as research_error:
                                        print(f"  ⚠ Web research failed (compile triage): {research_error}")

                                if experience_learning_enabled and self.experience_store:
                                    try:
                                        memory_refs = self.experience_store.query_experiences(
                                            root_cause=str(triage_result.get("root_cause", "")),
                                            error_type=str(triage_result.get("error_type", "unknown")),
                                            phase="compile",
                                            key_symbols=triage_result.get("key_symbols", []),
                                            top_k=experience_top_k
                                        )
                                        if memory_refs:
                                            triage_result["experience_hints"] = memory_refs
                                            print(f"  [Memory] Retrieved {len(memory_refs)} compile experience(s)")
                                    except Exception as memory_error:
                                        print(f"  ⚠ Experience query failed (compile): {memory_error}")

                                triage_conf = float(triage_result.get("confidence", 0.0) or 0.0)
                                triage_type = str(triage_result.get("error_type", "unknown"))
                                triage_cause = str(triage_result.get("root_cause", ""))
                                print(
                                    f"  [Triage] type={triage_type}, confidence={triage_conf:.2f}, cause={triage_cause}"
                                )
                                if triage_result.get("code_locations"):
                                    first_loc = triage_result["code_locations"][0]
                                    print(
                                        f"  [Locate] {first_loc.get('file', '')}:{first_loc.get('line', 1)} "
                                        f"({first_loc.get('kind', 'location')})"
                                    )
                                if triage_result.get("change_direction"):
                                    print(f"  [Direction] {triage_result['change_direction'][0]}")
                                if triage_result.get("actionable_edits"):
                                    first_edit = triage_result["actionable_edits"][0]
                                    print(
                                        "  [Actionable] "
                                        f"{first_edit.get('file', '')}:{first_edit.get('line', 1)} -> "
                                        f"{first_edit.get('instruction', '')}"
                                    )

                                triage_log_path = os.path.join(
                                    log_dir,
                                    f"{test_name}_triage_attempt{llm_fix_count + 1}_{timestamp}.log"
                                )
                                with open(triage_log_path, 'w', encoding='utf-8') as triage_log:
                                    triage_log.write("LLM triage result:\n")
                                    triage_log.write(json.dumps(triage_result, ensure_ascii=False, indent=2))
                                print(f"  ↳ Triage log saved: {triage_log_path}")

                                triage_unavailable = str(triage_result.get("root_cause", "")) == "triage_unavailable"
                                if triage_unavailable:
                                    self._print_key_event(
                                        "[Triage] unavailable -> fallback to direct fix (ignore confidence gate)",
                                        bg_code="45"
                                    )
                                elif (not bool(triage_result.get("should_fix", True))) or triage_conf < triage_min_confidence:
                                    print(
                                        f"  ⚠ Triage decided to skip fix "
                                        f"(should_fix={bool(triage_result.get('should_fix', True))}, "
                                        f"confidence={triage_conf:.2f} < {triage_min_confidence:.2f})"
                                    )
                                    break
                            except Exception as triage_error:
                                print(f"  ⚠ Triage failed, fallback to direct fix: {triage_error}")

                        compile_output = (compile_result.stdout or "") + "\n" + (compile_result.stderr or "")
                        issue_fingerprint = self._build_issue_fingerprint(
                            error_type=str(triage_result.get("error_type", "unknown")),
                            root_cause=str(triage_result.get("root_cause", "")),
                            key_symbols=triage_result.get("key_symbols", []),
                            raw_output=compile_output
                        )
                        is_new_issue = issue_fingerprint not in compile_seen_issue_fingerprints
                        compile_issue_counts[issue_fingerprint] += 1
                        compile_repeat_count = compile_issue_counts[issue_fingerprint]
                        triage_result["issue_fingerprint"] = issue_fingerprint
                        triage_result["is_new_issue"] = bool(is_new_issue)
                        triage_result["repeat_count"] = int(compile_repeat_count)

                        if is_new_issue:
                            self._print_key_event(
                                "[RetryPolicy] New compile issue detected -> does not consume attempt budget",
                                bg_code="42"
                            )
                        else:
                            compile_consumed_attempts += 1
                            self._print_key_event(
                                f"[RetryPolicy] Repeated compile issue -> consume budget ({compile_consumed_attempts}/{max_fix_attempts})",
                                bg_code="43"
                            )

                        if compile_consumed_attempts > max_fix_attempts:
                            self._print_key_event(
                                "[RetryPolicy] Repeated compile issue budget exceeded -> stop",
                                bg_code="41"
                            )
                            break

                        compile_seen_issue_fingerprints.add(issue_fingerprint)

                        self._print_key_event(
                            f"[Fix] Compile auto-fix phase (repeat-budget {compile_consumed_attempts}/{max_fix_attempts}, total-fix {llm_fix_count + 1})",
                            bg_code="46"
                        )
                        try:
                            with open(test_path, 'r', encoding='utf-8') as f:
                                current_test_code = f.read()
                            before_fix_code = current_test_code

                            aggressive_compile_fix = compile_repeat_count >= 2
                            if aggressive_compile_fix:
                                self._print_key_event(
                                    "[Escalation] Compile issue repeated -> aggressive rewrite mode",
                                    bg_code="45"
                                )

                            fixed_test_code = self.test_generator.fix_test_from_compile_error(
                                current_test_code=current_test_code,
                                compile_error=compile_output,
                                function_name=test_name.replace("_llm_test", ""),
                                compile_analysis=triage_result if llm_triage_enabled else None,
                                aggressive=aggressive_compile_fix
                            )

                            first_change_preview = self._summarize_code_change(current_test_code, fixed_test_code)
                            if first_change_preview == "no_text_change" and not aggressive_compile_fix:
                                self._print_key_event(
                                    "[Escalation] No code change detected -> retry once with aggressive rewrite",
                                    bg_code="45"
                                )
                                fixed_test_code = self.test_generator.fix_test_from_compile_error(
                                    current_test_code=current_test_code,
                                    compile_error=compile_output,
                                    function_name=test_name.replace("_llm_test", ""),
                                    compile_analysis=triage_result if llm_triage_enabled else None,
                                    aggressive=True
                                )

                            if blocked_redefinition_symbols:
                                sanitized_code, stripped_symbols = self._remove_symbol_definitions_from_code(
                                    fixed_test_code,
                                    sorted(list(blocked_redefinition_symbols)),
                                    protected_symbols=[target_symbol]
                                )
                                if stripped_symbols:
                                    self._print_key_event(
                                        "[AntiOscillation] Stripped forbidden redefinitions from compile fix: "
                                        + ", ".join(stripped_symbols[:6])
                                        + (" ..." if len(stripped_symbols) > 6 else ""),
                                        bg_code="45"
                                    )
                                    fixed_test_code = sanitized_code

                            with open(test_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_test_code)

                            diff_log_path = self._emit_fix_diff(
                                before_code=before_fix_code,
                                after_code=fixed_test_code,
                                log_dir=log_dir,
                                test_name=test_name,
                                phase="compile",
                                attempt=llm_fix_count + 1,
                                timestamp=timestamp
                            )

                            fix_log_path = os.path.join(log_dir, f"{test_name}_autofix_attempt{llm_fix_count + 1}_{timestamp}.log")
                            with open(fix_log_path, 'w', encoding='utf-8') as log_file:
                                log_file.write("Auto-fix triggered by compile error.\n\n")
                                log_file.write("Original compile stderr (truncated to 8000 chars):\n")
                                log_file.write((compile_result.stderr or "")[:8000])
                                if diff_log_path:
                                    log_file.write("\n\nUnified diff patch log:\n")
                                    log_file.write(diff_log_path)
                                    log_file.write("\n")
                                log_file.write("\n\nUpdated test file:\n")
                                log_file.write(fixed_test_code)

                            print(f"  ↳ Auto-fix applied and saved: {test_path}")
                            print(f"  ↳ Auto-fix log saved: {fix_log_path}")

                            if experience_learning_enabled and self.experience_store:
                                try:
                                    self.experience_store.add_experience({
                                        "phase": "compile",
                                        "function_name": test_name.replace("_llm_test", ""),
                                        "test_file": test_file,
                                        "error_type": str(triage_result.get("error_type", "unknown")),
                                        "root_cause": str(triage_result.get("root_cause", "")),
                                        "key_symbols": triage_result.get("key_symbols", []),
                                        "fix_strategy": triage_result.get("fix_strategy", []),
                                        "summary": str(triage_result.get("minimal_change", "compile fix applied")),
                                        "code_locations": triage_result.get("code_locations", []),
                                        "change_direction": triage_result.get("change_direction", []),
                                        "analysis_layers": triage_result.get("analysis_layers", []),
                                        "actionable_edits": triage_result.get("actionable_edits", []),
                                        "verification_plan": triage_result.get("verification_plan", []),
                                        "change_preview": self._summarize_code_change(before_fix_code, fixed_test_code),
                                        "outcome": "fix_applied_pending_recompile",
                                        "attempt": llm_fix_count + 1
                                    })
                                except Exception as memory_write_error:
                                    print(f"  ⚠ Experience write failed (compile): {memory_write_error}")

                            llm_fix_count += 1
                            compile_round += 1
                        except Exception as fix_error:
                            print(f"  ✗ Auto-fix failed: {fix_error}")
                            break

                    if not compile_success:
                        all_passed = False
                        results.append((test_name, "COMPILE_FAILED"))
                        test_finished = True
                        continue

                    print(f"  ✓ Compiled successfully")
                    self._print_key_event("Compile succeeded, entering test run", bg_code="42")
                    print(f"Running: {test_name}...")
                    runtime_xml_path = os.path.join(
                        log_dir,
                        f"{test_name}_run_attempt{runtime_fix_count}_{timestamp}.xml"
                    )
                    if effective_run_template:
                        run_context = self._build_command_context(
                            test_name=test_name,
                            test_path=test_path,
                            exe_path=exe_path,
                            build_path=build_path,
                            runtime_xml_path=runtime_xml_path
                        )
                        run_cmd_display = self._render_command_template(
                            effective_run_template,
                            run_context
                        )
                        print(f"  [RunCmd] {run_cmd_display}")
                        run_result = self._run_custom_shell_command(
                            run_cmd_display,
                            cwd=effective_run_cwd,
                            timeout=120
                        )
                    else:
                        run_cmd = [exe_path, f"--gtest_output=xml:{runtime_xml_path}"]
                        run_cmd_display = ' '.join(run_cmd)
                        print(f"  [RunCmd] {run_cmd_display}")
                        run_result = subprocess.run(
                            run_cmd,
                            capture_output=True,
                            timeout=120,
                            text=True,
                            cwd=self.project_dir
                        )

                    if run_result.returncode == 0:
                        print(f"  ✓ All tests passed")
                        results.append((test_name, "PASSED"))

                        output_lines = run_result.stderr.split('\n')
                        for line in output_lines:
                            if 'passed' in line.lower() or 'ok' in line.lower():
                                print(f"    {line.strip()}")
                        test_finished = True
                        continue

                    print(f"  ✗ Some tests failed")
                    self._print_key_event("Runtime tests failed, preparing triage", bg_code="43")
                    if run_result.stderr:
                        error_lines = run_result.stderr.split('\n')
                        for line in error_lines:
                            if 'FAILED' in line or 'ERROR' in line or 'failed' in line:
                                print(f"    {line.strip()}")

                    run_log_path = os.path.join(
                        log_dir,
                        f"{test_name}_run_attempt{runtime_fix_count}_{timestamp}.log"
                    )
                    with open(run_log_path, 'w', encoding='utf-8') as log_file:
                        log_file.write("Command:\n")
                        log_file.write(exe_path + "\n\n")
                        log_file.write("STDOUT:\n")
                        log_file.write(run_result.stdout or "")
                        log_file.write("\nSTDERR:\n")
                        log_file.write(run_result.stderr or "")
                    print(f"  ↳ Run log saved: {run_log_path}")

                    if not auto_fix_test_failures:
                        results.append((test_name, "FAILED"))
                        all_passed = False
                        test_finished = True
                        continue

                    runtime_triage_result = {
                        "error_type": "unknown",
                        "root_cause": "triage_skipped",
                        "should_fix": True,
                        "confidence": 1.0,
                        "fix_strategy": ["direct_fix"],
                        "key_symbols": [],
                        "minimal_change": "apply minimal runtime fix",
                        "code_locations": [],
                        "change_direction": ["apply minimal runtime test fix near first failing assertion"]
                    }

                    run_output = (run_result.stdout or "") + "\n" + (run_result.stderr or "")
                    runtime_xml_summary = self._parse_gtest_xml_result(runtime_xml_path)
                    failed_tests = runtime_xml_summary.get("failed_tests", [])
                    if not failed_tests:
                        failed_tests = self._extract_failed_tests_from_output(run_output)

                    current_failed_set = {str(name).strip() for name in failed_tests if str(name).strip()}
                    if runtime_prev_failed_tests is not None:
                        resolved = runtime_prev_failed_tests - current_failed_set
                        if resolved:
                            runtime_consumed_attempts = 0
                            runtime_seen_issue_fingerprints.clear()
                            resolved_preview = ", ".join(sorted(list(resolved))[:4])
                            if len(resolved) > 4:
                                resolved_preview += " ..."
                            self._print_key_event(
                                f"[RuntimeProgress] {len(resolved)} previously failed case(s) now pass -> reset runtime budget ({resolved_preview})",
                                bg_code="42"
                            )
                    runtime_prev_failed_tests = current_failed_set

                    focus_case = failed_tests[0] if failed_tests else ""
                    focused_output = ""
                    focus_xml_summary = {}
                    if focus_case:
                        focus_xml_path = os.path.join(
                            log_dir,
                            f"{test_name}_focus_attempt{runtime_fix_count}_{timestamp}.xml"
                        )
                        try:
                            if effective_run_template:
                                focus_context = self._build_command_context(
                                    test_name=test_name,
                                    test_path=test_path,
                                    exe_path=exe_path,
                                    build_path=build_path,
                                    runtime_xml_path=focus_xml_path,
                                    gtest_filter=focus_case
                                )
                                focus_cmd_text = self._render_command_template(
                                    effective_run_template,
                                    focus_context
                                )
                                print(f"  [RunCmd:Focus] {focus_cmd_text}")
                                focus_result = self._run_custom_shell_command(
                                    focus_cmd_text,
                                    cwd=effective_run_cwd,
                                    timeout=60
                                )
                            else:
                                focus_cmd = [exe_path, f"--gtest_filter={focus_case}", f"--gtest_output=xml:{focus_xml_path}"]
                                print(f"  [RunCmd:Focus] {' '.join(focus_cmd)}")
                                focus_result = subprocess.run(
                                    focus_cmd,
                                    capture_output=True,
                                    timeout=60,
                                    text=True,
                                    cwd=self.project_dir
                                )
                            focused_output = (focus_result.stdout or "") + "\n" + (focus_result.stderr or "")
                            focus_xml_summary = self._parse_gtest_xml_result(focus_xml_path)
                            self._print_key_event(
                                f"[RuntimeFocus] solving case: {focus_case}",
                                bg_code="45"
                            )
                        except Exception as focus_error:
                            print(f"  ⚠ Focused rerun failed: {focus_error}")

                    rerun_summary = self._rerun_failed_tests_for_stability(
                        exe_path=exe_path,
                        failed_tests=failed_tests,
                        log_dir=log_dir,
                        test_name=test_name,
                        timestamp=timestamp,
                        reruns=2,
                        run_command_template=effective_run_template or None,
                        run_command_cwd=effective_run_cwd,
                        test_path=test_path,
                        build_path=build_path
                    )
                    evidence_output = focused_output or run_output
                    mock_violations = self._extract_mock_violations(evidence_output)
                    runtime_evidence = {
                        "xml_summary": runtime_xml_summary,
                        "focus_case": focus_case,
                        "focus_xml_summary": focus_xml_summary,
                        "failed_tests": failed_tests,
                        "stability": rerun_summary,
                        "mock_violations": mock_violations,
                        "first_violation": (mock_violations[0] if mock_violations else None)
                    }

                    if failed_tests:
                        self._print_key_event(
                            f"[RuntimeEvidence] failed_cases={len(failed_tests)}",
                            bg_code="45"
                        )
                    if rerun_summary.get("enabled"):
                        self._print_key_event(
                            f"[RuntimeEvidence] stability={rerun_summary.get('status', 'unknown')}",
                            bg_code="45"
                        )
                    if mock_violations:
                        self._print_key_event(
                            f"[RuntimeEvidence] mock_violations={len(mock_violations)}",
                            bg_code="45"
                        )

                    never_called_methods = self._extract_never_called_mock_methods(evidence_output)
                    if same_tu_unmockable_symbols and never_called_methods:
                        blocked_methods = sorted([
                            self._c_symbol_to_mock_method_name(sym)
                            for sym in same_tu_unmockable_symbols
                            if self._c_symbol_to_mock_method_name(sym) in never_called_methods
                        ])
                        if blocked_methods:
                            with open(test_path, 'r', encoding='utf-8') as f:
                                runtime_detfix_before_code = f.read()
                            removed_expect_calls = self._remove_expect_call_blocks_for_methods(
                                test_path=test_path,
                                method_names=blocked_methods
                            )
                            if removed_expect_calls:
                                with open(test_path, 'r', encoding='utf-8') as f:
                                    runtime_detfix_after_code = f.read()
                                self._emit_fix_diff(
                                    before_code=runtime_detfix_before_code,
                                    after_code=runtime_detfix_after_code,
                                    log_dir=log_dir,
                                    test_name=test_name,
                                    phase="runtime_detfix",
                                    attempt=runtime_fix_count + 1,
                                    timestamp=timestamp
                                )
                                self._print_key_event(
                                    "[DeterministicFix] Removed unreachable EXPECT_CALL blocks: "
                                    + ", ".join(removed_expect_calls),
                                    bg_code="45"
                                )
                                runtime_fix_count += 1
                                compile_round = 0
                                continue

                    if llm_triage_enabled:
                        try:
                            with open(test_path, 'r', encoding='utf-8') as f:
                                current_test_code = f.read()

                            navigation_context = self.compile_analyzer.build_ordered_navigation_context(
                                compiler_output=evidence_output,
                                key_symbols=[],
                                max_locations=8
                            )

                            runtime_triage_result = self.test_generator.analyze_test_failure(
                                current_test_code=current_test_code,
                                test_output=evidence_output,
                                function_name=test_name.replace("_llm_test", ""),
                                navigation_context=navigation_context,
                                runtime_evidence=runtime_evidence
                            )

                            enriched_navigation = self.compile_analyzer.build_ordered_navigation_context(
                                compiler_output=evidence_output,
                                key_symbols=runtime_triage_result.get("key_symbols", []),
                                max_locations=8
                            )
                            runtime_triage_result["code_locations"] = enriched_navigation.get("code_locations", [])
                            runtime_triage_result["ordered_navigation"] = enriched_navigation.get("ordered_navigation", [])
                            runtime_triage_result["scope"] = enriched_navigation.get("scope", {})
                            runtime_triage_result["runtime_evidence"] = runtime_evidence

                            if web_research_enabled:
                                try:
                                    web_research = self.test_generator.research_root_cause_online(
                                        root_cause=str(runtime_triage_result.get("root_cause", "")),
                                        error_type=str(runtime_triage_result.get("error_type", "unknown")),
                                        key_symbols=runtime_triage_result.get("key_symbols", []),
                                        max_results=web_research_max_results
                                    )
                                    runtime_triage_result["web_research"] = web_research
                                    print(
                                        f"  [Run-Research] query='{web_research.get('query', '')}', "
                                        f"refs={web_research.get('count', 0)}"
                                    )
                                except Exception as research_error:
                                    print(f"  ⚠ Web research failed (runtime triage): {research_error}")

                            if experience_learning_enabled and self.experience_store:
                                try:
                                    memory_refs = self.experience_store.query_experiences(
                                        root_cause=str(runtime_triage_result.get("root_cause", "")),
                                        error_type=str(runtime_triage_result.get("error_type", "unknown")),
                                        phase="runtime",
                                        key_symbols=runtime_triage_result.get("key_symbols", []),
                                        top_k=experience_top_k
                                    )
                                    if memory_refs:
                                        runtime_triage_result["experience_hints"] = memory_refs
                                        print(f"  [Memory] Retrieved {len(memory_refs)} runtime experience(s)")
                                except Exception as memory_error:
                                    print(f"  ⚠ Experience query failed (runtime): {memory_error}")

                            triage_conf = float(runtime_triage_result.get("confidence", 0.0) or 0.0)
                            triage_type = str(runtime_triage_result.get("error_type", "unknown"))
                            triage_cause = str(runtime_triage_result.get("root_cause", ""))
                            print(
                                f"  [Run-Triage] type={triage_type}, confidence={triage_conf:.2f}, cause={triage_cause}"
                            )
                            if runtime_triage_result.get("code_locations"):
                                first_loc = runtime_triage_result["code_locations"][0]
                                print(
                                    f"  [Run-Locate] {first_loc.get('file', '')}:{first_loc.get('line', 1)} "
                                    f"({first_loc.get('kind', 'location')})"
                                )
                            if runtime_triage_result.get("change_direction"):
                                print(f"  [Run-Direction] {runtime_triage_result['change_direction'][0]}")
                            if runtime_triage_result.get("actionable_edits"):
                                first_edit = runtime_triage_result["actionable_edits"][0]
                                print(
                                    "  [Run-Actionable] "
                                    f"{first_edit.get('file', '')}:{first_edit.get('line', 1)} -> "
                                    f"{first_edit.get('instruction', '')}"
                                )

                            triage_log_path = os.path.join(
                                log_dir,
                                f"{test_name}_run_triage_attempt{runtime_fix_count + 1}_{timestamp}.log"
                            )
                            with open(triage_log_path, 'w', encoding='utf-8') as triage_log:
                                triage_log.write("LLM runtime triage result:\n")
                                triage_log.write(json.dumps(runtime_triage_result, ensure_ascii=False, indent=2))
                            print(f"  ↳ Run triage log saved: {triage_log_path}")

                            triage_unavailable = str(runtime_triage_result.get("root_cause", "")) == "triage_unavailable"
                            if triage_unavailable:
                                self._print_key_event(
                                    "[Run-Triage] unavailable -> fallback to direct fix (ignore confidence gate)",
                                    bg_code="45"
                                )
                            elif (not bool(runtime_triage_result.get("should_fix", True))) or triage_conf < triage_min_confidence:
                                print(
                                    f"  ⚠ Runtime triage decided to skip fix "
                                    f"(should_fix={bool(runtime_triage_result.get('should_fix', True))}, "
                                    f"confidence={triage_conf:.2f} < {triage_min_confidence:.2f})"
                                )
                                results.append((test_name, "FAILED"))
                                all_passed = False
                                test_finished = True
                                continue
                        except Exception as triage_error:
                            print(f"  ⚠ Runtime triage failed, fallback to direct fix: {triage_error}")

                    runtime_issue_fingerprint = self._build_issue_fingerprint(
                        error_type=str(runtime_triage_result.get("error_type", "unknown")),
                        root_cause=str(runtime_triage_result.get("root_cause", "")),
                        key_symbols=runtime_triage_result.get("key_symbols", []),
                        raw_output=evidence_output
                    )
                    runtime_is_new_issue = runtime_issue_fingerprint not in runtime_seen_issue_fingerprints
                    runtime_issue_counts[runtime_issue_fingerprint] += 1
                    runtime_repeat_count = runtime_issue_counts[runtime_issue_fingerprint]
                    runtime_triage_result["issue_fingerprint"] = runtime_issue_fingerprint
                    runtime_triage_result["is_new_issue"] = bool(runtime_is_new_issue)
                    runtime_triage_result["repeat_count"] = int(runtime_repeat_count)

                    if runtime_is_new_issue:
                        self._print_key_event(
                            "[RetryPolicy] New runtime issue detected -> does not consume attempt budget",
                            bg_code="42"
                        )
                    else:
                        runtime_consumed_attempts += 1
                        self._print_key_event(
                            f"[RetryPolicy] Repeated runtime issue -> consume budget ({runtime_consumed_attempts}/{max_test_fix_attempts})",
                            bg_code="43"
                        )

                    if runtime_consumed_attempts > max_test_fix_attempts:
                        self._print_key_event(
                            "[RetryPolicy] Repeated runtime issue budget exceeded -> stop",
                            bg_code="41"
                        )
                        results.append((test_name, "FAILED"))
                        all_passed = False
                        test_finished = True
                        continue

                    runtime_seen_issue_fingerprints.add(runtime_issue_fingerprint)

                    self._print_key_event(
                        f"[Fix] Runtime auto-fix phase (repeat-budget {runtime_consumed_attempts}/{max_test_fix_attempts}, total-fix {runtime_fix_count + 1})",
                        bg_code="46"
                    )
                    try:
                        with open(test_path, 'r', encoding='utf-8') as f:
                            current_test_code = f.read()
                        before_fix_code = current_test_code

                        aggressive_runtime_fix = runtime_repeat_count >= 2
                        if aggressive_runtime_fix:
                            self._print_key_event(
                                "[Escalation] Runtime issue repeated -> aggressive rewrite mode",
                                bg_code="45"
                            )

                        fixed_test_code = self.test_generator.fix_test_from_test_failure(
                            current_test_code=current_test_code,
                            test_output=run_output,
                            function_name=test_name.replace("_llm_test", ""),
                            failure_analysis=runtime_triage_result if llm_triage_enabled else None,
                            aggressive=aggressive_runtime_fix
                        )

                        first_change_preview = self._summarize_code_change(current_test_code, fixed_test_code)
                        if first_change_preview == "no_text_change" and not aggressive_runtime_fix:
                            self._print_key_event(
                                "[Escalation] No code change detected -> retry once with aggressive rewrite",
                                bg_code="45"
                            )
                            fixed_test_code = self.test_generator.fix_test_from_test_failure(
                                current_test_code=current_test_code,
                                test_output=run_output,
                                function_name=test_name.replace("_llm_test", ""),
                                failure_analysis=runtime_triage_result if llm_triage_enabled else None,
                                aggressive=True
                            )

                        if blocked_redefinition_symbols:
                            sanitized_code, stripped_symbols = self._remove_symbol_definitions_from_code(
                                fixed_test_code,
                                sorted(list(blocked_redefinition_symbols)),
                                protected_symbols=[target_symbol]
                            )
                            if stripped_symbols:
                                self._print_key_event(
                                    "[AntiOscillation] Stripped forbidden redefinitions from runtime fix: "
                                    + ", ".join(stripped_symbols[:6])
                                    + (" ..." if len(stripped_symbols) > 6 else ""),
                                    bg_code="45"
                                )
                                fixed_test_code = sanitized_code

                        with open(test_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_test_code)

                        diff_log_path = self._emit_fix_diff(
                            before_code=before_fix_code,
                            after_code=fixed_test_code,
                            log_dir=log_dir,
                            test_name=test_name,
                            phase="runtime",
                            attempt=runtime_fix_count + 1,
                            timestamp=timestamp
                        )

                        fix_log_path = os.path.join(
                            log_dir,
                            f"{test_name}_run_autofix_attempt{runtime_fix_count + 1}_{timestamp}.log"
                        )
                        with open(fix_log_path, 'w', encoding='utf-8') as log_file:
                            log_file.write("Auto-fix triggered by test runtime failure.\n\n")
                            log_file.write("Original run output (truncated to 8000 chars):\n")
                            log_file.write(run_output[:8000])
                            if diff_log_path:
                                log_file.write("\n\nUnified diff patch log:\n")
                                log_file.write(diff_log_path)
                                log_file.write("\n")
                            log_file.write("\n\nUpdated test file:\n")
                            log_file.write(fixed_test_code)

                        print(f"  ↳ Runtime auto-fix applied and saved: {test_path}")
                        print(f"  ↳ Runtime auto-fix log saved: {fix_log_path}")

                        if experience_learning_enabled and self.experience_store:
                            try:
                                self.experience_store.add_experience({
                                    "phase": "runtime",
                                    "function_name": test_name.replace("_llm_test", ""),
                                    "test_file": test_file,
                                    "error_type": str(runtime_triage_result.get("error_type", "unknown")),
                                    "root_cause": str(runtime_triage_result.get("root_cause", "")),
                                    "key_symbols": runtime_triage_result.get("key_symbols", []),
                                    "fix_strategy": runtime_triage_result.get("fix_strategy", []),
                                    "summary": str(runtime_triage_result.get("minimal_change", "runtime fix applied")),
                                    "code_locations": runtime_triage_result.get("code_locations", []),
                                    "change_direction": runtime_triage_result.get("change_direction", []),
                                    "analysis_layers": runtime_triage_result.get("analysis_layers", []),
                                    "actionable_edits": runtime_triage_result.get("actionable_edits", []),
                                    "verification_plan": runtime_triage_result.get("verification_plan", []),
                                    "runtime_evidence": runtime_triage_result.get("runtime_evidence", runtime_evidence),
                                    "change_preview": self._summarize_code_change(before_fix_code, fixed_test_code),
                                    "outcome": "fix_applied_pending_rerun",
                                    "attempt": runtime_fix_count + 1
                                })
                            except Exception as memory_write_error:
                                print(f"  ⚠ Experience write failed (runtime): {memory_write_error}")

                        runtime_fix_count += 1
                        if compile_round >= max_compile_rounds - 1:
                            max_compile_rounds += 1
                        continue
                    except Exception as run_fix_error:
                        print(f"  ✗ Runtime auto-fix failed: {run_fix_error}")
                        results.append((test_name, "FAILED"))
                        all_passed = False
                        test_finished = True
                        continue
            
            except subprocess.TimeoutExpired:
                print(f"  ✗ Test execution timeout")
                results.append((test_name, "TIMEOUT"))
                all_passed = False
                log_path = os.path.join(log_dir, f"{test_name}_timeout_{timestamp}.log")
                with open(log_path, 'w', encoding='utf-8') as log_file:
                    log_file.write("Test execution timed out.\n")
                    log_file.write(f"Executable: {exe_path}\n")
                print(f"  ↳ Timeout log saved: {log_path}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append((test_name, "ERROR"))
                all_passed = False
                log_path = os.path.join(log_dir, f"{test_name}_error_{timestamp}.log")
                with open(log_path, 'w', encoding='utf-8') as log_file:
                    log_file.write("Unexpected error during test execution.\n")
                    log_file.write(str(e) + "\n")
                print(f"  ↳ Error log saved: {log_path}")
        
        # 显示总结
        print("\n" + "=" * 60)
        self._print_key_node("Test Execution Summary", bg_code="44")
        print("=" * 60)
        
        for test_name, status in results:
            status_symbol = "✓" if status == "PASSED" else "✗"
            print(f"{status_symbol} {test_name:<40} {status}")
        
        if all_passed:
            self._print_key_event("✓ All tests executed successfully", bg_code="42")
        else:
            self._print_key_event("⚠ Some tests failed or couldn't run", bg_code="43")

        status_updates: Dict[str, str] = {}
        for test_name, status in results:
            function_name = test_name.replace("_llm_test", "")
            status_updates[function_name] = status
        self._update_function_status_index(status_updates, log_dir=log_dir, timestamp=timestamp)
        self._current_target_functions_for_cmake_sync = None
        
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
    
    def run_full_workflow(self,
                          target_functions: Optional[List[str]] = None,
                          skip_run: bool = False,
                          auto_fix_compile_errors: bool = True,
                          max_fix_attempts: int = 2,
                          auto_fix_test_failures: bool = True,
                          max_test_fix_attempts: int = 2,
                          llm_triage_enabled: bool = True,
                          triage_min_confidence: float = 0.55,
                          web_research_enabled: bool = True,
                          web_research_max_results: int = 4,
                          experience_learning_enabled: bool = True,
                          experience_top_k: int = 3,
                          skip_quality_gates: bool = False,
                          quality_strict: bool = False,
                          compile_command_template: Optional[str] = None,
                          compile_command_cwd: Optional[str] = None,
                          run_command_template: Optional[str] = None,
                          run_command_cwd: Optional[str] = None) -> None:
        """
        运行完整工作流
        
        Args:
            target_functions: 目标函数列表
            skip_run: 是否跳过测试执行步骤
            auto_fix_compile_errors: 编译失败后是否自动进入LLM修复阶段
            max_fix_attempts: 最大自动修复重试次数
            auto_fix_test_failures: 测试运行失败后是否自动进入LLM修复阶段
            max_test_fix_attempts: 测试运行失败最大自动修复重试次数
            llm_triage_enabled: 是否启用“先分析再修复”诊断阶段
            triage_min_confidence: 诊断最低置信度阈值
            web_research_enabled: triage后是否进行在线检索增强
            web_research_max_results: 在线检索最大返回条数
            experience_learning_enabled: 是否启用经验积累与检索
            experience_top_k: 经验检索返回条数
            skip_quality_gates: 是否跳过clang-format/clang-tidy/cppcheck质量闸门
            quality_strict: 质量闸门严格模式（有问题即停止）
        """
        self.show_workflow_info()
        self.analyze_codebase()
        self.print_compile_info()
        self.generate_tests(target_functions)

        if self.cmakelists_autogen_enabled:
            try:
                pre_compile_cwd = self._resolve_custom_cwd(
                    compile_command_cwd if compile_command_cwd is not None else self.compile_command_cwd,
                    fallback=self.project_dir
                )
                self.ensure_cmakelists_for_tests(
                    test_dir=self.test_dir,
                    compile_cwd=pre_compile_cwd,
                    target_functions=target_functions
                )
            except Exception as cmake_sync_error:
                print(f"⚠ CMake sync skipped due to error: {cmake_sync_error}")
        else:
            print("[CMakeSync] Auto-generation disabled by config")

        verify_ok = self.verify_tests(target_functions=target_functions)

        if not verify_ok:
            print("\n⚠ Generated tests did not pass verification checks.")
            print("  Skipping compile/run phase to avoid noisy failures.")
            print("  Please review generated test files or improve prompt/model settings.")
            print("\n" + "=" * 60)
            print("✓ Workflow completed (generation only, verification failed).")
            return

        if not skip_quality_gates:
            quality_ok = self.run_quality_gates(strict=quality_strict, target_functions=target_functions)
            if not quality_ok:
                print("\n" + "=" * 60)
                print("✓ Workflow completed (stopped by quality gates).")
                return
        
        if not skip_run:
            self.run_tests(
                target_functions=target_functions,
                auto_fix_compile_errors=auto_fix_compile_errors,
                max_fix_attempts=max_fix_attempts,
                auto_fix_test_failures=auto_fix_test_failures,
                max_test_fix_attempts=max_test_fix_attempts,
                llm_triage_enabled=llm_triage_enabled,
                triage_min_confidence=triage_min_confidence
                ,web_research_enabled=web_research_enabled,
                web_research_max_results=web_research_max_results,
                experience_learning_enabled=experience_learning_enabled,
                experience_top_k=experience_top_k,
                compile_command_template=compile_command_template,
                compile_command_cwd=compile_command_cwd,
                run_command_template=run_command_template,
                run_command_cwd=run_command_cwd
            )
        
        print("\n" + "=" * 60)
        self._print_key_node("✓ Workflow completed", bg_code="42")


class CCodeAnalyzer:
    """扩展的代码分析器，添加文件查找功能"""
    
    def __init__(self, include_dir, src_dir):
        # 导入原始分析器
        from c_code_analyzer import CCodeAnalyzer as OrigAnalyzer
        self._analyzer = OrigAnalyzer(include_dir, src_dir)
    
    def _extract_c_files(self, directory: str) -> List[str]:
        """提取目录中的C/H文件"""
        files = []
        root = Path(directory)
        if not root.exists():
            return files

        for ext in ['*.c', '*.h']:
            for file in root.rglob(ext):
                if file.is_file():
                    files.append(str(file))
        return files

    def analyze_directory(self):
        """分析目录（委托原始分析器）"""
        return self._analyzer.analyze_directory()
    
    def get_all_functions(self):
        """获取所有函数"""
        return self._analyzer.get_all_functions()
    
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
        "--include-dir",
        default=None,
        help="Header directory relative to project-dir (覆盖默认include)"
    )

    parser.add_argument(
        "--src-dir",
        default=None,
        help="Source directory relative to project-dir (覆盖默认src)"
    )

    parser.add_argument(
        "--test-output-dir",
        default=None,
        help="Test output directory relative to project-dir (覆盖默认test)"
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

    parser.add_argument(
        "--no-auto-fix-compile",
        action="store_true",
        help="Disable auto-fix phase when test compilation fails"
    )

    parser.add_argument(
        "--max-fix-attempts",
        type=int,
        default=2,
        help="Max retry attempts for compile error auto-fix (default: 2)"
    )

    parser.add_argument(
        "--no-auto-fix-test-fail",
        action="store_true",
        help="Disable auto-fix phase when tests run but fail"
    )

    parser.add_argument(
        "--max-test-fix-attempts",
        type=int,
        default=2,
        help="Max retry attempts for runtime test-failure auto-fix (default: 2)"
    )

    parser.add_argument(
        "--disable-llm-triage",
        action="store_true",
        help="Disable analyze-then-fix triage stage before LLM patching"
    )

    parser.add_argument(
        "--triage-min-confidence",
        type=float,
        default=None,
        help="Minimum triage confidence [0.0,1.0] required to run LLM fix"
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
        help="Maximum web references to include for each triage"
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
        help="Top-K historical experiences to retrieve for each triage"
    )

    parser.add_argument(
        "--experience-store-path",
        default=None,
        help="Path to experience store jsonl file"
    )

    parser.add_argument(
        "--skip-quality-gates",
        action="store_true",
        help="Skip quality gates (clang-format / clang-tidy / cppcheck)"
    )

    parser.add_argument(
        "--quality-strict",
        action="store_true",
        help="Enable strict quality gates (stop workflow when any quality tool reports issues)"
    )

    parser.add_argument(
        "--compile-command-template",
        default=None,
        help="Custom compile command template (shell). Placeholders: {test_path},{exe_path},{build_dir},{project_dir},{include_flags},{source_files}"
    )

    parser.add_argument(
        "--compile-command-cwd",
        default=None,
        help="Working directory for custom compile command (absolute or relative to project_dir)"
    )

    parser.add_argument(
        "--run-command-template",
        default=None,
        help="Custom run command template (shell). Placeholders: {exe_path},{runtime_xml},{gtest_filter},{test_name}"
    )

    parser.add_argument(
        "--run-command-cwd",
        default=None,
        help="Working directory for custom run command (absolute or relative to project_dir)"
    )
    
    args = parser.parse_args()

    effective_skip_quality_gates = args.skip_quality_gates
    effective_quality_strict = args.quality_strict
    effective_max_fix_attempts = max(0, args.max_fix_attempts)
    effective_auto_fix_compile = not args.no_auto_fix_compile
    effective_max_test_fix_attempts = max(0, args.max_test_fix_attempts)
    effective_auto_fix_test_fail = not args.no_auto_fix_test_fail
    effective_llm_triage_enabled = not args.disable_llm_triage
    effective_triage_min_conf = args.triage_min_confidence if args.triage_min_confidence is not None else 0.55
    effective_web_research_enabled = not args.disable_web_research
    effective_web_research_max_results = args.web_research_max_results if args.web_research_max_results is not None else 4
    effective_experience_learning_enabled = not args.disable_experience_learning
    effective_experience_top_k = args.experience_top_k if args.experience_top_k is not None else 3
    effective_experience_store_path = args.experience_store_path
    effective_experience_track_in_git = True
    effective_compile_command_template = args.compile_command_template
    effective_compile_command_cwd = args.compile_command_cwd
    effective_run_command_template = args.run_command_template
    effective_run_command_cwd = args.run_command_cwd
    
    # 优先从配置文件加载
    if args.config:
        try:
            print(f"[Config] Loading from: {args.config}")
            workflow = LLMUTWorkflow.from_config(
                args.config,
                project_root_override=args.project_dir if args.project_dir != "." else None,
                compile_commands_override=args.compile_commands if args.compile_commands != "build/compile_commands.json" else None
            )

            if args.include_dir:
                workflow.include_dir = os.path.join(workflow.project_dir, args.include_dir)
            if args.src_dir:
                workflow.src_dir = os.path.join(workflow.project_dir, args.src_dir)
            if args.test_output_dir:
                workflow.test_dir = os.path.join(workflow.project_dir, args.test_output_dir)
            if args.include_dir or args.src_dir:
                workflow.code_analyzer = CCodeAnalyzer(workflow.include_dir, workflow.src_dir)

            # 从配置读取quality_gates默认值（命令行显式参数优先）
            with open(args.config, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            quality_cfg = cfg.get('test_generation', {}).get('quality_gates', {})
            compile_fix_cfg = cfg.get('test_generation', {}).get('compile_fix', {})
            execution_cfg = cfg.get('test_generation', {}).get('execution', {})
            compile_exec_cfg = execution_cfg.get('compile', {}) if isinstance(execution_cfg, dict) else {}
            run_exec_cfg = execution_cfg.get('run', {}) if isinstance(execution_cfg, dict) else {}
            if not args.skip_quality_gates and quality_cfg.get('enabled') is False:
                effective_skip_quality_gates = True
            if not args.quality_strict and quality_cfg.get('strict') is True:
                effective_quality_strict = True

            if args.max_fix_attempts == 2:
                try:
                    effective_max_fix_attempts = max(0, int(compile_fix_cfg.get('max_fix_attempts', 2)))
                except (TypeError, ValueError):
                    effective_max_fix_attempts = 2
            if args.max_test_fix_attempts == 2:
                try:
                    effective_max_test_fix_attempts = max(0, int(compile_fix_cfg.get('max_test_fix_attempts', 2)))
                except (TypeError, ValueError):
                    effective_max_test_fix_attempts = 2
            if not args.no_auto_fix_compile and compile_fix_cfg.get('auto_fix_compile_errors') is False:
                effective_auto_fix_compile = False
            if not args.no_auto_fix_test_fail and compile_fix_cfg.get('auto_fix_test_failures') is False:
                effective_auto_fix_test_fail = False
            if not args.disable_llm_triage and compile_fix_cfg.get('llm_triage_enabled') is False:
                effective_llm_triage_enabled = False
            if not args.disable_web_research and compile_fix_cfg.get('web_research_enabled') is False:
                effective_web_research_enabled = False
            if not args.disable_experience_learning and compile_fix_cfg.get('experience_learning_enabled') is False:
                effective_experience_learning_enabled = False
            effective_experience_track_in_git = bool(compile_fix_cfg.get('experience_track_in_git', True))
            if args.triage_min_confidence is None:
                try:
                    effective_triage_min_conf = float(compile_fix_cfg.get('triage_min_confidence', 0.55))
                except (TypeError, ValueError):
                    effective_triage_min_conf = 0.55
            if args.web_research_max_results is None:
                try:
                    effective_web_research_max_results = int(compile_fix_cfg.get('web_research_max_results', 4))
                except (TypeError, ValueError):
                    effective_web_research_max_results = 4
            if args.experience_top_k is None:
                try:
                    effective_experience_top_k = int(compile_fix_cfg.get('experience_top_k', 3))
                except (TypeError, ValueError):
                    effective_experience_top_k = 3
            if args.experience_store_path is None:
                cfg_exp_path = compile_fix_cfg.get('experience_store_path')
                if not effective_experience_track_in_git:
                    effective_experience_store_path = LLMUTWorkflow._default_external_experience_path()
                elif cfg_exp_path:
                    if os.path.isabs(str(cfg_exp_path)):
                        effective_experience_store_path = str(cfg_exp_path)
                    else:
                        effective_experience_store_path = os.path.abspath(
                            os.path.join(workflow.project_dir, str(cfg_exp_path))
                        )

            if args.compile_command_template is None:
                value = ''
                if isinstance(compile_exec_cfg, dict):
                    value = compile_exec_cfg.get('command', compile_exec_cfg.get('commands', ''))
                normalized = LLMUTWorkflow._normalize_command_template(value)
                effective_compile_command_template = normalized or None
            if args.compile_command_cwd is None:
                value = compile_exec_cfg.get('cwd', '') if isinstance(compile_exec_cfg, dict) else ''
                effective_compile_command_cwd = str(value or '').strip() or None
            if args.run_command_template is None:
                value = ''
                if isinstance(run_exec_cfg, dict):
                    value = run_exec_cfg.get('command', run_exec_cfg.get('commands', ''))
                normalized = LLMUTWorkflow._normalize_command_template(value)
                effective_run_command_template = normalized or None
            if args.run_command_cwd is None:
                value = run_exec_cfg.get('cwd', '') if isinstance(run_exec_cfg, dict) else ''
                effective_run_command_cwd = str(value or '').strip() or None
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
                test_output_dir=args.test_output_dir,
                include_dir=args.include_dir,
                src_dir=args.src_dir,
                llm_api_base=args.llm_api,
                llm_model=args.llm_model,
                compile_command_template=effective_compile_command_template,
                compile_command_cwd=effective_compile_command_cwd,
                run_command_template=effective_run_command_template,
                run_command_cwd=effective_run_command_cwd
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
        workflow.experience_learning_enabled = bool(effective_experience_learning_enabled)
        workflow.experience_top_k = max(1, effective_experience_top_k)
        if effective_experience_store_path and effective_experience_learning_enabled:
            workflow.experience_store = ExperienceStore(effective_experience_store_path)

        workflow.run_full_workflow(
            target_functions=args.functions,
            skip_run=args.skip_run,
            auto_fix_compile_errors=effective_auto_fix_compile,
            max_fix_attempts=effective_max_fix_attempts,
            auto_fix_test_failures=effective_auto_fix_test_fail,
            max_test_fix_attempts=effective_max_test_fix_attempts,
            llm_triage_enabled=effective_llm_triage_enabled,
            triage_min_confidence=max(0.0, min(1.0, effective_triage_min_conf)),
            web_research_enabled=effective_web_research_enabled,
            web_research_max_results=max(1, effective_web_research_max_results),
            experience_learning_enabled=effective_experience_learning_enabled,
            experience_top_k=max(1, effective_experience_top_k),
            skip_quality_gates=effective_skip_quality_gates,
            quality_strict=effective_quality_strict,
            compile_command_template=effective_compile_command_template,
            compile_command_cwd=effective_compile_command_cwd,
            run_command_template=effective_run_command_template,
            run_command_cwd=effective_run_command_cwd
        )


if __name__ == "__main__":
    main()
