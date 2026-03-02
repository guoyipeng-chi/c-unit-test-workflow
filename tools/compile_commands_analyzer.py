#!/usr/bin/env python3
"""
Compile Commands Analyzer
解析compile_commands.json，提取编译信息（include路径、宏定义等）
支持使用libclang进行精确的include依赖分析
"""

import json
import re
import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# 尝试导入libclang
try:
    from clang.cindex import Index, TranslationUnit, conf
    LIBCLANG_AVAILABLE = True
    logger.info("libclang is available - will use for precise include analysis")
except ImportError:
    LIBCLANG_AVAILABLE = False
    logger.warning("libclang not available - will use fallback include extraction")


@dataclass
class CompileInfo:
    """编译信息"""
    file: str  # 源文件路径
    directory: str  # 工作目录
    command: str  # 完整编译命令
    include_dirs: List[str]  # Include目录列表
    defines: Dict[str, Optional[str]]  # 宏定义 {name: value}
    c_standard: Optional[str]  # C标准版本
    cxx_standard: Optional[str]  # C++标准版本
    optimization: str  # 优化级别
    warnings: List[str]  # 警告标志


class CompileCommandsAnalyzer:
    """compile_commands.json分析器，支持libclang进行精确的include分析"""
    
    def __init__(self, compile_commands_file: str):
        """
        初始化分析器
        
        Args:
            compile_commands_file: compile_commands.json文件路径
        """
        self.file = compile_commands_file
        self.commands: List[Dict] = []
        self.compile_info: Dict[str, CompileInfo] = {}
        self.project_root = os.path.dirname(compile_commands_file)
        
        # 初始化libclang（如果可用）
        self.clang_index = None
        self.use_clang = LIBCLANG_AVAILABLE
        if self.use_clang:
            try:
                self.clang_index = Index.create()
                logger.info("✓ libclang initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize libclang: {e}")
                self.use_clang = False
        
        self._load_commands()
    
    def _load_commands(self) -> None:
        """从JSON文件加载编译命令"""
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                self.commands = json.load(f)
            print(f"✓ Loaded {len(self.commands)} compile commands")
        except FileNotFoundError:
            print(f"✗ File not found: {self.file}")
            self.commands = []
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}")
            self.commands = []
    
    def analyze_all(self) -> None:
        """分析所有编译命令"""
        for cmd_entry in self.commands:
            file = cmd_entry.get("file", "")
            if file:
                self.compile_info[file] = self._analyze_command(cmd_entry)

    def _to_abs_path(self, path: str, base_dir: Optional[str] = None) -> str:
        """将路径转换为绝对规范路径。"""
        if not path:
            return ""

        normalized = os.path.normpath(path)
        if os.path.isabs(normalized):
            return os.path.abspath(normalized)

        base = base_dir or self.project_root or os.getcwd()
        return os.path.abspath(os.path.join(base, normalized))

    def get_compile_scope_files(self) -> List[str]:
        """返回compile_commands.json覆盖的源文件绝对路径集合。"""
        files: Set[str] = set()
        for info in self.compile_info.values():
            abs_file = self._to_abs_path(info.file, info.directory)
            if abs_file:
                files.add(abs_file)
        return sorted(files)

    @staticmethod
    def _relativize(path: str, root: str) -> str:
        """将绝对路径转换为相对项目路径（失败时回退原路径）。"""
        try:
            rel = os.path.relpath(path, root)
            if not rel.startswith(".."):
                return rel.replace('\\', '/')
        except Exception:
            pass
        return path.replace('\\', '/')

    def _extract_error_locations(self,
                                 compiler_output: str,
                                 scope_files: Set[str],
                                 max_hits: int = 6) -> List[Dict[str, Any]]:
        """从编译器输出中提取定位点，仅保留compile scope内文件。"""
        if not compiler_output:
            return []

        results: List[Dict[str, Any]] = []
        seen = set()

        patterns = [
            # clang/gcc: path:line:col:
            r'([A-Za-z]:[^:\n]+|[^:\n]+):(\d+):(\d+):',
            # msvc: path(line,col)
            r'([A-Za-z]:[^\(\n]+|[^\(\n]+)\((\d+),(\d+)\)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, compiler_output):
                raw_path = (match.group(1) or "").strip().strip('"')
                line_no = int(match.group(2)) if match.group(2) else 1
                col_no = int(match.group(3)) if match.group(3) else 1

                abs_path = self._to_abs_path(raw_path)
                if abs_path not in scope_files:
                    continue

                key = (abs_path, line_no, col_no)
                if key in seen:
                    continue
                seen.add(key)

                results.append({
                    "kind": "compiler_diagnostic",
                    "symbol": "",
                    "file": self._relativize(abs_path, self.project_root),
                    "line": line_no,
                    "column": col_no,
                    "reason": "compile diagnostic location"
                })

                if len(results) >= max_hits:
                    return results

        return results

    def _find_symbol_locations_with_clang(self,
                                          symbol: str,
                                          scope_files: List[str],
                                          max_hits_per_symbol: int = 2) -> List[Dict[str, Any]]:
        """使用libclang在compile scope中查找符号声明/定义位置。"""
        if (not symbol) or (not self.use_clang) or (not self.clang_index):
            return []

        results: List[Dict[str, Any]] = []

        for source_file in scope_files:
            info = None
            # compile_info的key可能是相对路径，逐一比对绝对路径
            for compile_info in self.compile_info.values():
                compile_file_abs = self._to_abs_path(compile_info.file, compile_info.directory)
                if compile_file_abs == source_file:
                    info = compile_info
                    break

            if not info:
                continue

            args: List[str] = []
            for inc_dir in info.include_dirs:
                args.append(f"-I{inc_dir}")
            for name, value in info.defines.items():
                if value:
                    args.append(f"-D{name}={value}")
                else:
                    args.append(f"-D{name}")
            if info.c_standard:
                args.append(f"-std={info.c_standard}")

            try:
                tu = self.clang_index.parse(source_file, args=args)
            except Exception:
                continue

            found_for_file = 0
            for cursor in tu.cursor.walk_preorder():
                spelling = (cursor.spelling or "").strip()
                if spelling != symbol:
                    continue

                location = cursor.location
                if not location or not location.file:
                    continue

                loc_file_abs = self._to_abs_path(str(location.file.name))
                if loc_file_abs not in scope_files:
                    continue

                is_definition = bool(getattr(cursor, "is_definition", lambda: False)())
                results.append({
                    "kind": "symbol_definition" if is_definition else "symbol_declaration",
                    "symbol": symbol,
                    "file": self._relativize(loc_file_abs, self.project_root),
                    "line": int(location.line or 1),
                    "column": int(location.column or 1),
                    "reason": "clang navigation in compile_commands scope"
                })
                found_for_file += 1
                if found_for_file >= max_hits_per_symbol:
                    break

            if len(results) >= max_hits_per_symbol:
                break

        return results

    def _find_symbol_locations_fallback(self,
                                        symbol: str,
                                        scope_files: List[str],
                                        max_hits_per_symbol: int = 2) -> List[Dict[str, Any]]:
        """在clang不可用时，按compile scope做有限正则定位。"""
        if not symbol:
            return []

        results: List[Dict[str, Any]] = []
        pattern = re.compile(rf'\b{re.escape(symbol)}\b')

        for source_file in scope_files:
            if not os.path.exists(source_file):
                continue
            try:
                with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for idx, line in enumerate(f, start=1):
                        if pattern.search(line):
                            col = max(1, line.find(symbol) + 1)
                            results.append({
                                "kind": "symbol_reference",
                                "symbol": symbol,
                                "file": self._relativize(source_file, self.project_root),
                                "line": idx,
                                "column": col,
                                "reason": "fallback scoped regex location"
                            })
                            if len(results) >= max_hits_per_symbol:
                                return results
            except Exception:
                continue

        return results

    def build_ordered_navigation_context(self,
                                         compiler_output: str,
                                         key_symbols: Optional[List[str]] = None,
                                         max_locations: int = 8) -> Dict[str, Any]:
        """
        构建受compile_commands约束的定位上下文：
        1) 先诊断点
        2) 再符号声明/定义点（优先clang）
        """
        key_symbols = [s for s in (key_symbols or []) if isinstance(s, str) and s.strip()]
        max_locations = max(1, int(max_locations or 8))

        scope_list = self.get_compile_scope_files()
        scope_set = set(scope_list)

        locations: List[Dict[str, Any]] = []
        locations.extend(self._extract_error_locations(compiler_output, scope_set, max_hits=max_locations))

        for symbol in key_symbols[:6]:
            symbol = symbol.strip()
            if not symbol:
                continue

            if self.use_clang and self.clang_index:
                sym_locs = self._find_symbol_locations_with_clang(
                    symbol=symbol,
                    scope_files=scope_list,
                    max_hits_per_symbol=2
                )
            else:
                sym_locs = self._find_symbol_locations_fallback(
                    symbol=symbol,
                    scope_files=scope_list,
                    max_hits_per_symbol=2
                )

            for loc in sym_locs:
                duplicate = any(
                    loc["file"] == existing.get("file")
                    and int(loc["line"]) == int(existing.get("line", 0))
                    and (loc.get("symbol", "") == existing.get("symbol", ""))
                    for existing in locations
                )
                if not duplicate:
                    locations.append(loc)
                if len(locations) >= max_locations:
                    break
            if len(locations) >= max_locations:
                break

        ordered_navigation: List[Dict[str, Any]] = []
        for index, loc in enumerate(locations, start=1):
            ordered_navigation.append({
                "step": index,
                "action": "open_file_at",
                "file": loc.get("file", ""),
                "line": int(loc.get("line", 1) or 1),
                "column": int(loc.get("column", 1) or 1),
                "focus": loc.get("symbol") or loc.get("kind", "location"),
                "reason": loc.get("reason", "")
            })

        return {
            "scope": {
                "source": "compile_commands.json",
                "total_files": len(scope_list),
                "clang_navigation": bool(self.use_clang and self.clang_index)
            },
            "code_locations": locations[:max_locations],
            "ordered_navigation": ordered_navigation[:max_locations]
        }
    
    def extract_all_includes(self, source_file: str, compile_info: Optional[CompileInfo] = None) -> Set[str]:
        """
        提取源文件的所有include文件（包括间接依赖）
        
        使用libclang进行精确分析，或降级到递归扫描
        
        Args:
            source_file: 源文件路径
            compile_info: 编译信息（用于获取include目录等）
            
        Returns:
            所有include文件的集合（包括system headers）
        """
        if self.use_clang and self.clang_index:
            return self._extract_includes_with_clang(source_file, compile_info)
        else:
            return self._extract_includes_fallback(source_file)
    
    def _extract_includes_with_clang(self, source_file: str, compile_info: Optional[CompileInfo]) -> Set[str]:
        """
        使用libclang精确提取所有include
        
        这是最准确的方法，能处理：
        - 条件编译 (#ifdef)
        - 宏展开
        - 系统headers
        - 嵌套依赖
        """
        includes = set()
        
        try:
            # 构建编译参数
            compile_args = []
            
            if compile_info:
                # 添加include目录
                for inc_dir in compile_info.include_dirs:
                    compile_args.append(f"-I{inc_dir}")
                
                # 添加宏定义
                for name, value in compile_info.defines.items():
                    if value:
                        compile_args.append(f"-D{name}={value}")
                    else:
                        compile_args.append(f"-D{name}")
                
                # 添加C标准
                if compile_info.c_standard:
                    if 'c99' in compile_info.c_standard or 'c11' in compile_info.c_standard:
                        compile_args.append(f"-std={compile_info.c_standard}")
            
            # 使用libclang解析
            tu = self.clang_index.parse(
                source_file,
                args=compile_args,
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            )
            
            # 收集所有include的文件
            for included_file in tu.get_includes():
                inc_name = included_file.name
                if inc_name:
                    includes.add(inc_name)
            
            logger.info(f"✓ Extracted {len(includes)} includes for {os.path.basename(source_file)} using libclang")
            
        except Exception as e:
            logger.warning(f"Failed to extract includes with libclang: {e}")
            logger.info("Falling back to regex-based extraction")
            return self._extract_includes_fallback(source_file)
        
        return includes
    
    def _extract_includes_fallback(self, source_file: str) -> Set[str]:
        """
        降级方案：使用正则和递归扫描提取include
        
        这是libclang不可用时的fallback方案
        处理较为简单的场景
        """
        includes = set()
        visited = set()
        
        def process_file(filepath: str):
            """递归处理文件"""
            if filepath in visited:
                return
            visited.add(filepath)
            
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # 匹配 #include "file.h" 或 #include <file.h>
                        if match := re.match(r'#include\s+"([^"]+)"|#include\s+<([^>]+)>', line.strip()):
                            inc_file = match.group(1) or match.group(2)
                            includes.add(inc_file)
                            
                            # 如果是本地include（用双引号），尝试递归处理
                            if match.group(1):  # 双引号表示本地include
                                inc_path = self._resolve_include_path(filepath, inc_file)
                                if inc_path and os.path.exists(inc_path) and inc_path not in visited:
                                    process_file(inc_path)
            except Exception as e:
                logger.debug(f"Error processing file {filepath}: {e}")
        
        process_file(source_file)
        logger.info(f"Extracted {len(includes)} includes for {os.path.basename(source_file)} using fallback method")
        return includes
    
    def _resolve_include_path(self, source_file: str, include_name: str) -> Optional[str]:
        """
        解析include文件的完整路径
        
        对于本地include（双引号），优先在源文件所在目录查找
        """
        # 1. 在源文件所在目录查找
        source_dir = os.path.dirname(source_file)
        candidate = os.path.join(source_dir, include_name)
        if os.path.exists(candidate):
            return candidate
        
        # 2. 在项目根目录查找
        candidate = os.path.join(self.project_root, include_name)
        if os.path.exists(candidate):
            return candidate
        
        return None
    
    def _analyze_command(self, cmd_entry: Dict) -> CompileInfo:
        """
        分析单个编译命令
        
        Args:
            cmd_entry: 编译命令条目（包含file, directory, command）
            
        Returns:
            CompileInfo对象
        """
        file = cmd_entry.get("file", "")
        directory = cmd_entry.get("directory", "")
        command = cmd_entry.get("command", "")
        
        include_dirs = self._extract_includes(command)
        defines = self._extract_defines(command)
        c_standard = self._extract_c_standard(command)
        cxx_standard = self._extract_cxx_standard(command)
        optimization = self._extract_optimization(command)
        warnings = self._extract_warnings(command)
        
        return CompileInfo(
            file=file,
            directory=directory,
            command=command,
            include_dirs=include_dirs,
            defines=defines,
            c_standard=c_standard,
            cxx_standard=cxx_standard,
            optimization=optimization,
            warnings=warnings
        )
    
    def _extract_includes(self, command: str) -> List[str]:
        """提取include目录 (-I 或 /I)"""
        # MSVC风格: /I, GCC风格: -I
        includes = []
        
        # MSVC风格
        for match in re.finditer(r'/I([^\s]+)', command):
            includes.append(match.group(1))
        
        # MSVC external include
        for match in re.finditer(r'-external:I([^\s]+)', command):
            includes.append(match.group(1))
        
        # GCC风格
        for match in re.finditer(r'-I([^\s]+)', command):
            includes.append(match.group(1))
        
        # 去重并规范化路径
        includes = list(set(includes))
        includes = [self._normalize_path(inc) for inc in includes]
        
        return includes
    
    def _extract_defines(self, command: str) -> Dict[str, Optional[str]]:
        """提取宏定义 (-D 或 /D)"""
        defines = {}
        
        # MSVC风格: /DNAME 或 /DNAME=VALUE
        for match in re.finditer(r'/D([A-Za-z_]\w*)(?:=([^\s]*)?)?', command):
            name = match.group(1)
            value = match.group(2) if match.group(2) else None
            defines[name] = value
        
        # GCC风格: -DNAME 或 -DNAME=VALUE
        for match in re.finditer(r'-D([A-Za-z_]\w*)(?:=([^\s]*)?)?', command):
            name = match.group(1)
            value = match.group(2) if match.group(2) else None
            defines[name] = value
        
        return defines
    
    def _extract_c_standard(self, command: str) -> Optional[str]:
        """提取C标准版本"""
        # GCC/Clang风格
        if match := re.search(r'-std=c(\d+)', command):
            return f"c{match.group(1)}"
        
        # MSVC风格 (通常在编译器标志中)
        if '/std:c' in command:
            if match := re.search(r'/std:c(\w+)', command):
                return f"c{match.group(1)}"
        
        return None
    
    def _extract_cxx_standard(self, command: str) -> Optional[str]:
        """提取C++标准版本"""
        # GCC/Clang风格
        if match := re.search(r'-std:c\+\+(\d+)', command):
            return f"c++{match.group(1)}"
        if match := re.search(r'-std=c\+\+(\d+)', command):
            return f"c++{match.group(1)}"
        
        # MSVC风格
        if match := re.search(r'/std:c\+\+(\d+)', command):
            return f"c++{match.group(1)}"
        
        return None
    
    def _extract_optimization(self, command: str) -> str:
        """提取优化级别"""
        # MSVC风格
        if '/Od' in command:
            return "O0"  # 无优化
        if '/Ox' in command or '/O2' in command:
            return "O2"
        if '/O1' in command:
            return "O1"
        
        # GCC风格
        for opt in ['-O3', '-O2', '-O1', '-O0', '-Os']:
            if opt in command:
                return opt[1:]
        
        return "O2"  # 默认值
    
    def _extract_warnings(self, command: str) -> List[str]:
        """提取警告标志"""
        warnings = []
        
        # MSVC风格
        if '/W3' in command:
            warnings.append("W3")
        elif '/W4' in command:
            warnings.append("W4")
        
        # GCC风格
        if '-Wall' in command:
            warnings.append("Wall")
        if '-Wextra' in command:
            warnings.append("Wextra")
        
        return warnings
    
    def _normalize_path(self, path: str) -> str:
        """规范化路径"""
        # 移除引号
        path = path.strip('"\'')
        # 转换反斜杠为正斜杠
        path = path.replace('\\', '/')
        return path
    
    def get_source_files(self) -> List[str]:
        """获取所有源文件"""
        files = [info.file for info in self.compile_info.values()]
        # 去重并排序
        return sorted(set(files))
    
    def get_all_includes(self) -> Set[str]:
        """获取所有include目录"""
        includes = set()
        for info in self.compile_info.values():
            includes.update(info.include_dirs)
        return includes
    
    def get_all_defines(self) -> Dict[str, Optional[str]]:
        """获取所有宏定义"""
        all_defines = {}
        for info in self.compile_info.values():
            all_defines.update(info.defines)
        return all_defines
    
    def get_compile_info(self, file: str) -> Optional[CompileInfo]:
        """获取指定文件的编译信息"""
        return self.compile_info.get(file)
    
    def print_summary(self) -> None:
        """打印分析摘要"""
        print("\n[Compile Commands Summary]")
        print("=" * 60)
        
        if not self.commands:
            print("No compile commands found!")
            return
        
        sources = self.get_source_files()
        includes = self.get_all_includes()
        defines = self.get_all_defines()
        
        print(f"\nSource files: {len(sources)}")
        for src in sources[:5]:
            print(f"  - {src}")
        if len(sources) > 5:
            print(f"  ... and {len(sources) - 5} more")
        
        print(f"\nInclude directories: {len(includes)}")
        for inc in sorted(includes)[:5]:
            print(f"  - {inc}")
        if len(includes) > 5:
            print(f"  ... and {len(includes) - 5} more")
        
        print(f"\nMacros defined: {len(defines)}")
        for name, value in list(defines.items())[:5]:
            if value:
                print(f"  - {name}={value}")
            else:
                print(f"  - {name}")
        if len(defines) > 5:
            print(f"  ... and {len(defines) - 5} more")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        analyzer = CompileCommandsAnalyzer(sys.argv[1])
        analyzer.analyze_all()
        analyzer.print_summary()
    else:
        print("Usage: python compile_commands_analyzer.py <compile_commands.json>")
