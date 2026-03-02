#!/usr/bin/env python3
"""
LLM-based Test Generator
使用Qwen3 Coder通过提示工程生成单元测试
支持使用libclang进行精确的include依赖分析
"""

import json
import logging
import os
import re
import requests
from urllib.parse import quote_plus
from typing import Optional, Dict, List, Set, Any
from dataclasses import dataclass
from llm_client import VLLMClient
from c_code_analyzer import FunctionDependency
from compile_commands_analyzer import CompileInfo, CompileCommandsAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMTestGenerator:
    """基于LLM的测试代码生成器"""
    
    def __init__(self, llm_client: VLLMClient, compile_analyzer: Optional[CompileCommandsAnalyzer] = None):
        """
        初始化LLM测试生成器
        
        Args:
            llm_client: VLLMClient实例
            compile_analyzer: 可选的CompileCommandsAnalyzer实例（用于提取完整的include列表）
        """
        self.llm = llm_client
        self.compile_analyzer = compile_analyzer
        self.system_prompt = self._build_system_prompt()

    @staticmethod
    def research_root_cause_online(root_cause: str,
                                   error_type: str = "unknown",
                                   key_symbols: Optional[List[str]] = None,
                                   max_results: int = 4) -> Dict[str, Any]:
        """基于triage根因做一次在线检索，返回可供修复参考的结果（失败自动降级）。"""
        key_symbols = key_symbols or []
        max_results = max(1, int(max_results or 4))

        query_parts = [root_cause or "", error_type or "", "c++ gtest"] + key_symbols[:3]
        query = " ".join([p for p in query_parts if p]).strip()
        if not query:
            query = "c++ gtest compile error"

        references: List[Dict[str, str]] = []

        try:
            so_url = (
                "https://api.stackexchange.com/2.3/search/advanced"
                f"?order=desc&sort=relevance&site=stackoverflow&accepted=True&pagesize={max_results}"
                f"&q={quote_plus(query)}"
            )
            so_resp = requests.get(so_url, timeout=8)
            if so_resp.ok:
                so_data = so_resp.json()
                for item in (so_data.get("items") or [])[:max_results]:
                    references.append({
                        "source": "stackoverflow",
                        "title": str(item.get("title", "")).strip(),
                        "url": str(item.get("link", "")).strip(),
                        "snippet": "Accepted/relevant StackOverflow thread"
                    })
        except Exception:
            pass

        try:
            ddg_url = (
                "https://api.duckduckgo.com/"
                f"?q={quote_plus(query)}&format=json&no_redirect=1&no_html=1"
            )
            ddg_resp = requests.get(ddg_url, timeout=8)
            if ddg_resp.ok:
                ddg = ddg_resp.json()
                abstract = str(ddg.get("AbstractText", "")).strip()
                abstract_url = str(ddg.get("AbstractURL", "")).strip()
                heading = str(ddg.get("Heading", "")).strip() or "DuckDuckGo abstract"
                if abstract:
                    references.append({
                        "source": "duckduckgo",
                        "title": heading,
                        "url": abstract_url,
                        "snippet": abstract[:280]
                    })

                related = ddg.get("RelatedTopics") or []
                for topic in related:
                    if len(references) >= max_results * 2:
                        break
                    if isinstance(topic, dict):
                        text = str(topic.get("Text", "")).strip()
                        url = str(topic.get("FirstURL", "")).strip()
                        if text and url:
                            references.append({
                                "source": "duckduckgo",
                                "title": "Related topic",
                                "url": url,
                                "snippet": text[:280]
                            })
        except Exception:
            pass

        dedup = []
        seen_urls = set()
        for ref in references:
            url = ref.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            dedup.append(ref)
            if len(dedup) >= max_results:
                break

        hints = []
        for ref in dedup:
            snippet = ref.get("snippet", "")
            if snippet:
                hints.append(snippet)

        return {
            "query": query,
            "count": len(dedup),
            "references": dedup,
            "hints": hints[:max_results]
        }
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        return """You are an expert C/C++ unit test engineer. Your task is to generate comprehensive, high-quality unit tests for C functions using Google Test (gtest) framework.

Guidelines:
1. Generate tests with multiple test cases covering:
   - Normal/valid inputs
   - Edge cases and boundary conditions
   - Invalid inputs and error handling
   - Special cases (null pointers, zero, empty strings, etc.)

2. Use appropriate mock objects (gmock) for external function dependencies
3. Use meaningful test names that describe what is being tested
4. Include setup and teardown code when needed
5. Add comments explaining complex test logic
6. Ensure tests are independent and can run in any order
7. NEVER define/re-implement production C functions in the test file.
8. If using extern "C", only place #include and declarations there; do not put function bodies in extern "C" blocks.
9. Use mocks/stubs declarations, not duplicate real function definitions from production sources.

Return ONLY the C++ test code, no explanations."""
    
    def generate_test_file(self, func_dep: FunctionDependency, 
                          compile_info: Optional[CompileInfo] = None,
                          extra_context: str = "",
                          project_root: str = ".") -> str:
        """
        使用LLM生成测试文件
        
        Args:
            func_dep: 函数依赖信息
            compile_info: 编译信息
            extra_context: 额外的上下文信息
            project_root: 项目根目录（用于读取源文件）
            
        Returns:
            生成的测试代码
        """
        prompt = self._build_prompt(func_dep, compile_info, extra_context, project_root)
        
        logger.info(f"Generating tests for {func_dep.name}...")
        
        # 调用LLM
        response = self.llm.generate(
            prompt,
            temperature=0.7,
            max_tokens=64000,
            top_p=0.95
        )
        
        if not response:
            logger.error(f"Failed to generate test for {func_dep.name}")
            return self._generate_fallback_test(func_dep)
        
        # 清理响应（移除markdown标记等）
        test_code = self._clean_response(response)
        test_code = self._sanitize_generated_test_code(
            test_code,
            forbidden_symbols=[func_dep.name] + sorted(list(func_dep.external_calls))
        )
        
        return test_code
    
    def _build_prompt(self, func_dep: FunctionDependency,
                     compile_info: Optional[CompileInfo] = None,
                     extra_context: str = "",
                     project_root: str = ".") -> str:
        """构建提示词"""
        
        # 读取被测函数的源代码
        function_source = self._read_function_source(func_dep, project_root)
        
        # 读取依赖的头文件内容
        header_contents = self._read_header_files(func_dep, project_root)
        
        # 使用libclang提取所有include（包括间接依赖）
        all_includes = self._extract_all_includes(func_dep, compile_info, project_root)
        
        # 基本信息
        prompt = f"""Generate comprehensive unit tests for this C function:

Function Name: {func_dep.name}
Return Type: {func_dep.return_type}
Source File: {func_dep.source_file}

Parameters:
"""
        
        if func_dep.parameters:
            for ptype, pname in func_dep.parameters:
                prompt += f"  - {ptype} {pname}\n"
        else:
            prompt += "  - void (no parameters)\n"
        
        # 添加函数实际源代码
        if function_source:
            prompt += f"\n=== FUNCTION SOURCE CODE ===\n```c\n{function_source}\n```\n"
        
        # 外部调用/依赖
        if func_dep.external_calls:
            prompt += f"\nExternal Function Calls (requires mocking):\n"
            for call in sorted(func_dep.external_calls):
                prompt += f"  - {call}()\n"
        else:
            prompt += f"\nExternal Function Calls: None\n"
        
        # 包含的头文件（直接依赖）
        if func_dep.include_files:
            prompt += f"\nDirect Include Files:\n"
            for inc in sorted(func_dep.include_files):
                prompt += f"  - {inc}\n"
        
        # 添加头文件内容
        if header_contents:
            for header_name, content in header_contents.items():
                prompt += f"\n=== HEADER FILE: {header_name} ===\n```c\n{content}\n```\n"
        
        # 所有include文件（包括间接依赖和系统库）
        if all_includes:
            prompt += f"\n=== ALL REQUIRED INCLUDES (extracted by libclang) ===\n"
            prompt += "These are ALL the include files that the test MUST include:\n"
            for inc in sorted(all_includes):
                prompt += f"#include <{inc}>\n" if '>' in inc or not '.' in inc else f'#include "{inc}"\n'
            prompt += "\n"
        
        # 编译信息
        if compile_info:
            prompt += f"\nCompilation Info:\n"
            prompt += f"  C Standard: {compile_info.c_standard or 'default'}\n"
            prompt += f"  C++ Standard: {compile_info.cxx_standard or 'c++14'}\n"
            
            if compile_info.defines:
                prompt += f"  Macros: {', '.join(compile_info.defines.keys())}\n"
        
        # 额外上下文
        if extra_context:
            prompt += f"\nAdditional Context:\n{extra_context}\n"
        
        # 生成要求
        prompt += """
Generate a complete test file with:
1. All necessary #include directives
2. Mock definitions for external calls
3. A test fixture class
4. Multiple test cases covering various scenarios
5. Proper error handling and assertions

Make sure the tests are:
- Comprehensive and cover edge cases
- Independent and isolated
- Using Google Test (gtest) framework
- Using Google Mock (gmock) for mocking

Critical constraints (must follow):
- Do NOT implement/define production C functions in this test file.
- The target function and other project C symbols must come from linked production object files.
- If you need C linkage, use extern "C" only for includes/declarations, never for function bodies.
- Preserve exact function signatures from headers (including const qualifiers); never change them in mocks/wrappers.
- Do NOT reference internal/static production globals (for example g_next_id). Validate behavior via return values and mocked call arguments instead.

Return ONLY the C++ code, no markdown wrappers."""
        
        return prompt
    
    def _clean_response(self, response: str) -> str:
        """清理LLM响应"""
        # 移除markdown代码块标记
        if response.startswith("```"):
            lines = response.split('\n')
            # 移除第一行的```cpp或```c++等
            if lines[0].startswith("```"):
                lines = lines[1:]
            # 移除最后的```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = '\n'.join(lines)
        
        # 移除开头和结尾的空白
        response = response.strip()
        
        return response

    @staticmethod
    def _remove_function_definitions(code: str, symbol_name: str) -> tuple[str, int]:
        """
        从代码中移除指定符号的函数定义（保留声明）。
        通过匹配 `symbol(...) { ... }` 并按花括号配对删除。
        """
        removed = 0
        search_pos = 0

        pattern = re.compile(
            rf'\b{re.escape(symbol_name)}\s*\([^;{{}}]*\)\s*\{{',
            re.MULTILINE
        )

        while True:
            match = pattern.search(code, search_pos)
            if not match:
                break

            brace_open = code.find('{', match.end() - 1)
            if brace_open == -1:
                break

            brace_count = 1
            end_pos = brace_open + 1
            while end_pos < len(code) and brace_count > 0:
                ch = code[end_pos]
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                end_pos += 1

            if brace_count != 0:
                # 花括号不平衡，避免误删
                search_pos = match.end()
                continue

            # 向前扩展到行首，尽量把返回类型一并删除
            line_start = code.rfind('\n', 0, match.start())
            line_start = 0 if line_start == -1 else line_start + 1

            # 删除函数定义及其后可能紧跟的一个换行
            delete_end = end_pos
            if delete_end < len(code) and code[delete_end:delete_end + 1] == '\n':
                delete_end += 1

            code = code[:line_start] + code[delete_end:]
            removed += 1
            search_pos = line_start

        return code, removed

    def _sanitize_generated_test_code(self, code: str, forbidden_symbols: List[str]) -> str:
        """移除模型误生成的生产函数定义，避免链接重复定义。"""
        sanitized = code
        total_removed = 0

        # 去重保持顺序
        seen = set()
        symbols = []
        for symbol in forbidden_symbols:
            if symbol and symbol not in seen:
                seen.add(symbol)
                symbols.append(symbol)

        for symbol in symbols:
            sanitized, removed = self._remove_function_definitions(sanitized, symbol)
            total_removed += removed

        if total_removed > 0:
            logger.warning(
                f"Sanitized generated test: removed {total_removed} duplicated function definition(s) "
                f"for symbols={symbols}"
            )

        return sanitized

    def fix_test_from_compile_error(self,
                                    current_test_code: str,
                                    compile_error: str,
                                    function_name: str = "unknown",
                                    compile_analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        根据编译错误修复测试代码

        Args:
            current_test_code: 当前测试代码
            compile_error: 编译器错误输出
            function_name: 目标函数名（用于日志）

        Returns:
            修复后的测试代码；若修复失败则返回原代码
        """
        prompt = f"""You are an expert C/C++ unit test engineer.
Fix the following Google Test file based on compiler errors.

Requirements:
1. Keep the same test intent and function target.
2. Fix include errors, type/signature mismatches, mock declarations, and syntax errors.
3. Keep using Google Test / Google Mock.
4. NEVER define/re-implement production C functions in test file.
5. Preserve exact production signatures from headers (const/ptr qualifiers).
6. Do NOT reference internal/static globals such as g_next_id.
7. Return ONLY the complete updated C++ test file.

Target Function: {function_name}

=== CURRENT TEST CODE ===
```cpp
{current_test_code}
```

=== COMPILER ERRORS ===
```
{compile_error}
```
"""

        if compile_analysis:
            prompt += f"""

=== DIAGNOSTIC ANALYSIS (from previous triage step) ===
```json
{json.dumps(compile_analysis, ensure_ascii=False, indent=2)}
```

Use this analysis as primary guidance and perform minimal, targeted changes.
"""

            if compile_analysis.get("experience_hints"):
                prompt += """

Apply relevant historical experience hints when they match the current failure pattern.
Prefer proven fixes from similar past cases before trying novel changes.
"""

        logger.info(f"Fixing test code from compile error for {function_name}...")
        response = self.llm.generate(
            prompt,
            temperature=0.2,
            max_tokens=64000,
            top_p=0.9
        )

        if not response:
            logger.warning(f"Failed to fix test for {function_name}, keep original code")
            return current_test_code

        fixed_code = self._clean_response(response)
        if not fixed_code.strip():
            logger.warning(f"Empty fixed code for {function_name}, keep original code")
            return current_test_code

        extra_forbidden = re.findall(r"conflicting types for '([A-Za-z_][A-Za-z0-9_]*)'", compile_error)
        unresolved_forbidden = re.findall(r"无法解析的外部符号\s+([A-Za-z_][A-Za-z0-9_]*)", compile_error)
        forbidden_symbols = [function_name] + extra_forbidden + unresolved_forbidden
        fixed_code = self._sanitize_generated_test_code(fixed_code, forbidden_symbols=forbidden_symbols)

        return fixed_code

    @staticmethod
    def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
        """从模型响应中提取首个JSON对象。"""
        if not text:
            return None

        raw = text.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw[start:end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return None

        return None

    def analyze_compile_error(self,
                              current_test_code: str,
                              compile_error: str,
                                                            function_name: str = "unknown",
                                                            navigation_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """先诊断编译错误，返回结构化分析结果。"""
        prompt = f"""You are a senior C/C++ build and test debugging assistant.
Analyze the compile/link errors and return a STRICT JSON object only.

Output schema (all fields required):
{{
  "error_type": "toolchain|linker|signature|include|mock|syntax|logic|unknown",
  "root_cause": "short cause summary",
  "should_fix": true,
  "confidence": 0.0,
  "fix_strategy": ["ordered actionable steps"],
  "key_symbols": ["symbol1", "symbol2"],
    "minimal_change": "short patch guidance",
    "code_locations": [
        {{"file": "path", "line": 1, "column": 1, "symbol": "name", "reason": "why relevant"}}
    ],
    "change_direction": ["high-level edit direction"]
}}

Rules:
- confidence is a float in [0,1]
- Prefer minimal edits and preserving test intent
- code_locations must prioritize provided navigation context and keep original order
- change_direction should be concise, implementation-oriented (where + what to adjust)
- Do NOT include markdown, comments, or extra text

Target Function: {function_name}

=== CURRENT TEST CODE ===
```cpp
{current_test_code}
```

=== COMPILER ERRORS ===
```
{compile_error}
```
"""

        if navigation_context:
            prompt += f"""

=== SCOPED NAVIGATION CONTEXT (compile_commands.json constrained) ===
```json
{json.dumps(navigation_context, ensure_ascii=False, indent=2)}
```

Use this context to produce deterministic code_locations and ordered change_direction.
Do not introduce file locations outside this scope.
"""

        logger.info(f"Triaging compile error for {function_name}...")
        response = self.llm.generate(
            prompt,
            temperature=0.1,
            max_tokens=5000,
            top_p=0.9
        )

        default_result: Dict[str, Any] = {
            "error_type": "unknown",
            "root_cause": "triage_unavailable",
            "should_fix": True,
            "confidence": 0.0,
            "fix_strategy": ["fallback_to_direct_fix"],
            "key_symbols": [],
            "minimal_change": "apply minimal compile fix",
            "code_locations": [],
            "change_direction": ["inspect compiler diagnostic location first, then adjust closest signature/include/mock mismatch"]
        }

        if not response:
            return default_result

        parsed = self._extract_json_object(response)
        if not parsed:
            return default_result

        result = default_result.copy()
        result.update(parsed)

        try:
            result["confidence"] = float(result.get("confidence", 0.0))
        except (TypeError, ValueError):
            result["confidence"] = 0.0
        result["confidence"] = max(0.0, min(1.0, result["confidence"]))
        result["should_fix"] = bool(result.get("should_fix", True))

        if not isinstance(result.get("fix_strategy"), list):
            result["fix_strategy"] = [str(result.get("fix_strategy", "fallback_to_direct_fix"))]
        if not isinstance(result.get("key_symbols"), list):
            result["key_symbols"] = []
        if not isinstance(result.get("code_locations"), list):
            result["code_locations"] = []
        if not isinstance(result.get("change_direction"), list):
            result["change_direction"] = [str(result.get("change_direction", "apply minimal compile fix"))]

        return result

    def analyze_test_failure(self,
                             current_test_code: str,
                             test_output: str,
                                                         function_name: str = "unknown",
                     navigation_context: Optional[Dict[str, Any]] = None,
                     runtime_evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """先诊断测试运行失败，返回结构化分析结果。"""
        prompt = f"""You are a senior C/C++ unit test debugging assistant.
Analyze the test execution failure output and return a STRICT JSON object only.

Output schema (all fields required):
{{
  "error_type": "assertion|expectation|mock|state|data|flaky|unknown",
  "root_cause": "short cause summary",
  "should_fix": true,
  "confidence": 0.0,
  "fix_strategy": ["ordered actionable steps"],
  "key_symbols": ["symbol1", "symbol2"],
    "minimal_change": "short patch guidance",
    "code_locations": [
        {{"file": "path", "line": 1, "column": 1, "symbol": "name", "reason": "why relevant"}}
    ],
    "change_direction": ["high-level edit direction"]
}}

Rules:
- confidence is a float in [0,1]
- Assume production code is correct; adjust test only
- Keep test intent, use minimal edits
- code_locations should prioritize provided navigation context and keep original order
- change_direction should point to test-side edits only
- If runtime evidence contains mock contract violations, prioritize the first violation as primary root cause
- Use stability evidence (stable_failure/flaky/not_reproducible) to adjust confidence
- Do NOT include markdown, comments, or extra text

Target Function: {function_name}

=== CURRENT TEST CODE ===
```cpp
{current_test_code}
```

=== TEST OUTPUT ===
```
{test_output}
```
"""

        if navigation_context:
            prompt += f"""

=== SCOPED NAVIGATION CONTEXT (compile_commands.json constrained) ===
```json
{json.dumps(navigation_context, ensure_ascii=False, indent=2)}
```

Use this context to produce deterministic code_locations and ordered change_direction.
Do not introduce file locations outside this scope.
"""

        if runtime_evidence:
            prompt += f"""

=== RUNTIME EVIDENCE (structured) ===
```json
{json.dumps(runtime_evidence, ensure_ascii=False, indent=2)}
```

Use this as high-priority evidence. Prefer first_violation for root cause when present.
"""

        logger.info(f"Triaging runtime test failure for {function_name}...")
        response = self.llm.generate(
            prompt,
            temperature=0.1,
            max_tokens=5000,
            top_p=0.9
        )

        default_result: Dict[str, Any] = {
            "error_type": "unknown",
            "root_cause": "triage_unavailable",
            "should_fix": True,
            "confidence": 0.0,
            "fix_strategy": ["fallback_to_direct_fix"],
            "key_symbols": [],
            "minimal_change": "apply minimal runtime fix",
            "code_locations": [],
            "change_direction": ["open failing assertion/expectation location first, then align expected values or mock behavior"]
        }

        if not response:
            return default_result

        parsed = self._extract_json_object(response)
        if not parsed:
            return default_result

        result = default_result.copy()
        result.update(parsed)

        try:
            result["confidence"] = float(result.get("confidence", 0.0))
        except (TypeError, ValueError):
            result["confidence"] = 0.0
        result["confidence"] = max(0.0, min(1.0, result["confidence"]))
        result["should_fix"] = bool(result.get("should_fix", True))

        if not isinstance(result.get("fix_strategy"), list):
            result["fix_strategy"] = [str(result.get("fix_strategy", "fallback_to_direct_fix"))]
        if not isinstance(result.get("key_symbols"), list):
            result["key_symbols"] = []
        if not isinstance(result.get("code_locations"), list):
            result["code_locations"] = []
        if not isinstance(result.get("change_direction"), list):
            result["change_direction"] = [str(result.get("change_direction", "apply minimal runtime fix"))]

        return result

    def fix_test_from_test_failure(self,
                                   current_test_code: str,
                                   test_output: str,
                                   function_name: str = "unknown",
                                   failure_analysis: Optional[Dict[str, Any]] = None) -> str:
        """根据测试运行失败输出修复测试代码（假设被测代码正确）。"""
        prompt = f"""You are an expert C/C++ unit test engineer.
Fix the following Google Test file based on TEST EXECUTION failures.

Requirements:
1. Assume production code is correct; only modify tests.
2. Keep test intent and target function unchanged.
3. Fix assertions, expected values, mock expectations, fixture setup/reset, and test data.
4. Keep using Google Test / Google Mock.
5. NEVER define/re-implement production C functions in test file.
6. Preserve exact production signatures from headers.
7. Return ONLY the complete updated C++ test file.

Target Function: {function_name}

=== CURRENT TEST CODE ===
```cpp
{current_test_code}
```

=== TEST OUTPUT ===
```
{test_output}
```
"""

        if failure_analysis:
            prompt += f"""

=== DIAGNOSTIC ANALYSIS (from previous triage step) ===
```json
{json.dumps(failure_analysis, ensure_ascii=False, indent=2)}
```

Use this analysis as primary guidance and perform minimal, targeted changes.
"""

            if failure_analysis.get("experience_hints"):
                prompt += """

Apply relevant historical experience hints when they match the current failure pattern.
Prefer proven fixes from similar past cases before trying novel changes.
"""

        logger.info(f"Fixing runtime test failure for {function_name}...")
        response = self.llm.generate(
            prompt,
            temperature=0.2,
            max_tokens=64000,
            top_p=0.9
        )

        if not response:
            logger.warning(f"Failed to fix runtime test for {function_name}, keep original code")
            return current_test_code

        fixed_code = self._clean_response(response)
        if not fixed_code.strip():
            logger.warning(f"Empty runtime fixed code for {function_name}, keep original code")
            return current_test_code

        fixed_code = self._sanitize_generated_test_code(fixed_code, forbidden_symbols=[function_name])
        return fixed_code
    
    def _generate_fallback_test(self, func_dep: FunctionDependency) -> str:
        """生成备选测试代码"""
        logger.warning(f"Generating fallback test for {func_dep.name}")
        
        # 根据函数签名生成一个基本的测试框架
        test_template = f"""#include <gtest/gtest.h>
#include <gmock/gmock.h>

// TODO: Generate proper tests for {func_dep.name}()
// This is a fallback template - please review and complete

class {func_dep.name.capitalize()}Test : public ::testing::Test {{
protected:
    void SetUp() override {{
        // Initialize test fixtures
    }}
    
    void TearDown() override {{
        // Cleanup
    }}
}};

TEST_F({func_dep.name.capitalize()}Test, BasicTest) {{
    // TODO: Implement test
    EXPECT_TRUE(true);
}}
"""
        return test_template
    
    def _extract_all_includes(self, func_dep: FunctionDependency, 
                             compile_info: Optional[CompileInfo],
                             project_root: str) -> Set[str]:
        """
        使用libclang提取源文件的所有include（包括间接依赖）
        
        这调用compile_analyzer的extract_all_includes方法
        """
        if not self.compile_analyzer:
            return set()
        
        try:
            source_file = os.path.join(project_root, func_dep.source_file)
            if not os.path.exists(source_file):
                logger.warning(f"Source file not found: {source_file}")
                return set()
            
            includes = self.compile_analyzer.extract_all_includes(source_file, compile_info)
            logger.info(f"Extracted {len(includes)} includes for {func_dep.name}")
            return includes
        except Exception as e:
            logger.error(f"Error extracting includes: {e}")
            return set()
    
    def _read_function_source(self, func_dep: FunctionDependency, project_root: str) -> str:
        """读取函数的源代码"""
        try:
            # 构建源文件的完整路径
            source_path = os.path.join(project_root, func_dep.source_file)
            if not os.path.exists(source_path):
                logger.warning(f"Source file not found: {source_path}")
                return ""
            
            with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 提取函数定义（从函数声明到 } 结束）
            # 更宽松的模式：允许返回类型和函数名之间有多个空格/换行
            # 例如: int32_t validate_name(...) { 或 int32_t\nvalidate_name(...)\n{
            pattern = rf'{re.escape(func_dep.return_type)}\s+{re.escape(func_dep.name)}\s*\('
            match = re.search(pattern, content)
            
            if match:
                # 从匹配位置开始，找到函数体的开始 {
                start_pos = match.start()
                open_brace_pos = content.find('{', match.end())
                
                if open_brace_pos == -1:
                    logger.warning(f"Could not find opening brace for {func_dep.name}")
                    return ""
                
                # 从 { 开始计数括号，找到对应的结束 }
                brace_count = 1  # 已经找到第一个 {
                end_pos = open_brace_pos + 1
                
                for i in range(open_brace_pos + 1, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                if brace_count == 0:
                    function_code = content[start_pos:end_pos]
                    return function_code.strip()
                else:
                    logger.warning(f"Unbalanced braces for function {func_dep.name}")
                    return ""
            
            logger.warning(f"Could not find function {func_dep.name} in {source_path}")
            return ""
            
        except Exception as e:
            logger.error(f"Error reading function source: {e}")
            return ""
    
    def _read_header_files(self, func_dep: FunctionDependency, project_root: str) -> Dict[str, str]:
        """读取依赖的头文件内容"""
        headers = {}
        
        for header_name in func_dep.include_files:
            # 尝试多个可能的路径
            possible_paths = [
                os.path.join(project_root, 'include', header_name),
                os.path.join(project_root, header_name),
                os.path.join(project_root, 'src', header_name),
            ]
            
            for header_path in possible_paths:
                if os.path.exists(header_path):
                    try:
                        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        # 清理内容（移除注释等，保留主要定义）
                        content = self._clean_header_content(content)
                        headers[header_name] = content
                        break
                    except Exception as e:
                        logger.error(f"Error reading header {header_path}: {e}")
        
        return headers
    
    def _clean_header_content(self, content: str) -> str:
        """清理头文件内容，保留关键部分"""
        # 移除多行注释
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # 移除单行注释
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        # 移除多余的空行
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        return content.strip()
    
    def generate_batch_tests(self, func_deps: List[FunctionDependency],
                            compile_info_map: Optional[Dict[str, CompileInfo]] = None,
                            project_root: str = ".") -> Dict[str, str]:
        """
        批量生成多个函数的测试
        
        Args:
            func_deps: 函数依赖列表
            compile_info_map: 编译信息映射
            project_root: 项目根目录
            
        Returns:
            {函数名: 测试代码}
        """
        results = {}
        
        for func_dep in func_deps:
            compile_info = None
            if compile_info_map and func_dep.source_file in compile_info_map:
                compile_info = compile_info_map[func_dep.source_file]
            
            test_code = self.generate_test_file(func_dep, compile_info, project_root=project_root)
            results[func_dep.name] = test_code
        
        return results


class PromptBuilder:
    """提示词构建工具"""
    
    @staticmethod
    def build_header_documentation(header_content: str) -> str:
        """从头文件内容构建文档"""
        # 提取函数声明、宏定义等
        lines = []
        
        # 查找struct/typedef定义
        if 'struct' in header_content or 'typedef' in header_content:
            lines.append("Data structures defined:")
            # 简单地包含相关行
            for line in header_content.split('\n'):
                if 'struct' in line or 'typedef' in line:
                    lines.append(f"  {line.strip()}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def build_source_context(source_code: str, func_name: str, lines_context: int = 5) -> str:
        """提取源代码上下文"""
        lines = source_code.split('\n')
        
        # 查找函数定义
        for i, line in enumerate(lines):
            if f'{func_name}(' in line:
                # 提取函数定义及其上下文
                start = max(0, i - lines_context)
                end = min(len(lines), i + 20)  # 包含函数体
                
                context = '\n'.join(lines[start:end])
                return f"Source context:\n```c\n{context}\n```"
        
        return ""


if __name__ == "__main__":
    # 简单测试
    from llm_client import create_client
    
    client = create_client("http://localhost:8000", "qwen-coder")
    generator = LLMTestGenerator(client)
    
    # 创建一个测试的FunctionDependency对象
    test_func = FunctionDependency(
        name="validate_name",
        return_type="int",
        parameters=[("const char*", "name")],
        external_calls=set(),
        source_file="validator.c",
        include_files={"validator.h"}
    )
    
    test_code = generator.generate_test_file(test_func)
    print("Generated Test Code:")
    print("=" * 60)
    print(test_code)
