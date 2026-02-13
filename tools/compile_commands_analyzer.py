#!/usr/bin/env python3
"""
Compile Commands Analyzer
解析compile_commands.json，提取编译信息（include路径、宏定义等）
"""

import json
import re
import os
from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from pathlib import Path


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
    """compile_commands.json分析器"""
    
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
