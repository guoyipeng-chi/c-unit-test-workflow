#!/usr/bin/env python3
"""
C Unit Test Generator - Code Analyzer
分析C代码，提取函数依赖关系
"""

import re
import os
from dataclasses import dataclass
from typing import List, Dict, Set, Optional

@dataclass
class FunctionDependency:
    """函数依赖关系"""
    name: str
    return_type: str
    parameters: List[tuple]  # [(type, name), ...]
    external_calls: Set[str]  # 调用的其他函数
    source_file: str
    include_files: Set[str]  # 依赖的头文件


class CCodeAnalyzer:
    """C代码分析器"""
    
    def __init__(self, include_dir: str, src_dir: str):
        self.include_dir = include_dir
        self.src_dir = src_dir
        self.function_map: Dict[str, FunctionDependency] = {}
        self.header_content: Dict[str, str] = {}
        
    def analyze_file(self, filepath: str) -> None:
        """分析单个C/H文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取include
            includes = set(re.findall(r'#include\s+[<"]([^>"]+)[>"]', content))
            
            # 提取函数定义（不包含static）
            func_pattern = r'(\w+)\s+(\w+)\s*\(\s*([^)]*)\s*\)\s*\{'
            
            for match in re.finditer(func_pattern, content):
                return_type = match.group(1)
                func_name = match.group(2)
                params_str = match.group(3)
                
                # 跳过main和内部函数
                if func_name == 'main' or func_name.startswith('_'):
                    continue
                
                parameters = self._parse_parameters(params_str)
                external_calls = self._extract_calls(content, match.start(), match.end())
                
                if func_name not in self.function_map:
                    self.function_map[func_name] = FunctionDependency(
                        name=func_name,
                        return_type=return_type,
                        parameters=parameters,
                        external_calls=external_calls,
                        source_file=filepath,
                        include_files=includes
                    )
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
    
    def _parse_parameters(self, params_str: str) -> List[tuple]:
        """解析函数参数"""
        if not params_str or params_str.strip() == 'void':
            return []
        
        parameters = []
        for param in params_str.split(','):
            param = param.strip()
            if param:
                parts = param.rsplit(None, 1)
                if len(parts) == 2:
                    parameters.append((parts[0], parts[1]))
        return parameters
    
    def _extract_calls(self, content: str, start: int, end: int) -> Set[str]:
        """提取函数体内的函数调用"""
        func_body_start = content.find('{', end)
        if func_body_start == -1:
            return set()
        
        # 简单的模式匹配，找到匹配的括号
        brace_count = 1
        pos = func_body_start + 1
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        func_body = content[func_body_start:pos]
        
        # 查找函数调用
        call_pattern = r'(\w+)\s*\('
        calls = set(re.findall(call_pattern, func_body))
        
        # 过滤掉保留字和控制流关键字
        keywords = {'if', 'while', 'for', 'switch', 'return', 'sizeof', 'NULL'}
        return calls - keywords
    
    def analyze_directory(self) -> None:
        """分析整个目录"""
        # 分析头文件
        for root, dirs, files in os.walk(self.include_dir):
            for file in files:
                if file.endswith('.h'):
                    self.analyze_file(os.path.join(root, file))
        
        # 分析源文件
        for root, dirs, files in os.walk(self.src_dir):
            for file in files:
                if file.endswith('.c'):
                    self.analyze_file(os.path.join(root, file))
    
    def get_function_dependencies(self, func_name: str) -> Optional[FunctionDependency]:
        """获取函数依赖"""
        return self.function_map.get(func_name)
    
    def get_all_functions(self) -> Dict[str, FunctionDependency]:
        """获取所有函数"""
        return self.function_map
