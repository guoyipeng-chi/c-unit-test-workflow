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
from typing import List, Dict, Set, Optional
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
