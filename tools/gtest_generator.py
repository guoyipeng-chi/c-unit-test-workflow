#!/usr/bin/env python3
"""
C Unit Test Generator - Test Code Generator
为C函数生成gtest测试代码
"""

from typing import List, Dict, Optional
from c_code_analyzer import FunctionDependency
import re


class GTestGenerator:
    """GTest测试代码生成器"""
    
    def __init__(self):
        self.mock_defines = []
        self.test_cases = []
    
    def generate_test_file(self, func_dep: FunctionDependency, 
                          output_file: str) -> str:
        """
        为函数生成完整的测试文件
        
        包括：
        - Mock定义宏
        - 测试Fixture类
        - 测试用例
        """
        
        test_code = self._generate_header(func_dep)
        test_code += self._generate_mock_defines(func_dep)
        test_code += self._generate_fixture_class(func_dep)
        test_code += self._generate_test_cases(func_dep)
        
        return test_code
    
    def _generate_header(self, func_dep: FunctionDependency) -> str:
        """生成文件头部"""
        includes = self._generate_includes(func_dep)
        
        header = f"""#include <gtest/gtest.h>
#include <gmock/gmock.h>
{includes}

using ::testing::Return;
using ::testing::_;
using ::testing::AtLeast;

"""
        return header
    
    def _generate_includes(self, func_dep: FunctionDependency) -> str:
        """生成include语句"""
        includes = set()
        
        # 添加源文件对应的头文件
        header_name = func_dep.source_file.replace('.c', '.h')
        if 'src' in func_dep.source_file:
            header_name = header_name.replace('src/', '')
        
        includes.add(f'#include "{header_name}"')
        
        # 添加依赖的所有头文件
        for inc in func_dep.include_files:
            includes.add(f'#include "{inc}"')
        
        return '\n'.join(sorted(includes))
    
    def _generate_mock_defines(self, func_dep: FunctionDependency) -> str:
        """生成Mock定义宏"""
        
        if not func_dep.external_calls:
            return "// No external function calls to mock\n\n"
        
        mock_section = """
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

"""
        
        for call in sorted(func_dep.external_calls):
            mock_section += f"// Mock definition for: {call}\n"
            mock_section += f"// #define MOCK_{call}_RETURN_VALUE  [default_value]\n\n"
        
        mock_section += "/* ================================================= */\n\n"
        
        return mock_section
    
    def _generate_fixture_class(self, func_dep: FunctionDependency) -> str:
        """生成Test Fixture类"""
        
        class_name = f"{func_dep.name.capitalize()}Test"
        
        fixture = f"""class {class_name} : public ::testing::Test {{
protected:
    void SetUp() override {{
        // 初始化测试前置条件
    }}
    
    void TearDown() override {{
        // 清理测试后续处理
    }}
}};

"""
        return fixture
    
    def _generate_test_cases(self, func_dep: FunctionDependency) -> str:
        """生成测试用例"""
        
        test_code = ""
        class_name = f"{func_dep.name.capitalize()}Test"
        
        # 生成基本测试用例
        test_cases = self._generate_basic_test_cases(func_dep)
        
        for i, test_case in enumerate(test_cases, 1):
            test_code += f"""// Test Case {i}: {test_case['description']}
TEST_F({class_name}, TestCase{i}_{test_case['name']}) {{
    // Arrange
{test_case['arrange']}
    
    // Act
{test_case['act']}
    
    // Assert
{test_case['assert']}
}}

"""
        
        return test_code
    
    def _generate_basic_test_cases(self, func_dep: FunctionDependency) -> List[Dict]:
        """生成基本的测试用例模板"""
        
        test_cases = []
        
        # 用例1: 正常情况
        arrange = self._generate_arrange(func_dep, "normal")
        act = f"auto result = {func_dep.name}({self._generate_call_params(func_dep)});"
        assert_stmt = self._generate_assert(func_dep, "normal")
        
        test_cases.append({
            'name': 'NormalCase',
            'description': 'Test normal execution path',
            'arrange': arrange,
            'act': act,
            'assert': assert_stmt
        })
        
        # 用例2: 边界情况
        arrange_boundary = self._generate_arrange(func_dep, "boundary")
        test_cases.append({
            'name': 'BoundaryCase',
            'description': 'Test boundary conditions',
            'arrange': arrange_boundary,
            'act': act,
            'assert': assert_stmt
        })
        
        # 用例3: 异常情况
        arrange_error = self._generate_arrange(func_dep, "error")
        test_cases.append({
            'name': 'ErrorCase',
            'description': 'Test error handling',
            'arrange': arrange_error,
            'act': act,
            'assert': self._generate_assert(func_dep, "error")
        })
        
        return test_cases
    
    def _generate_call_params(self, func_dep: FunctionDependency) -> str:
        """生成函数调用参数"""
        if not func_dep.parameters:
            return ""
        
        params = []
        for param_type, param_name in func_dep.parameters:
            if 'char*' in param_type or 'const char*' in param_type:
                params.append(f'"test_value"')
            elif 'int' in param_type or 'int32_t' in param_type:
                params.append('1')
            elif 'float' in param_type or 'double' in param_type:
                params.append('1.0f')
            elif '*' in param_type:
                params.append(f'&{param_name}_var')
            else:
                params.append('0')
        
        return ', '.join(params)
    
    def _generate_arrange(self, func_dep: FunctionDependency, case_type: str) -> str:
        """生成Arrange部分"""
        
        arrange = "        // Setup test data\n"
        
        for param_type, param_name in func_dep.parameters:
            if 'int' in param_type or 'int32_t' in param_type:
                if case_type == "normal":
                    arrange += f"        int32_t {param_name}_var = 42;\n"
                elif case_type == "boundary":
                    arrange += f"        int32_t {param_name}_var = 0;\n"
                else:
                    arrange += f"        int32_t {param_name}_var = -1;\n"
            elif 'float' in param_type or 'double' in param_type:
                if case_type == "normal":
                    arrange += f"        float {param_name}_var = 85.5f;\n"
                elif case_type == "boundary":
                    arrange += f"        float {param_name}_var = 0.0f;\n"
                else:
                    arrange += f"        float {param_name}_var = 101.0f;\n"
            elif 'char*' in param_type or 'const char*' in param_type:
                if case_type == "normal":
                    arrange += f"        const char* {param_name}_var = \"valid_input\";\n"
                else:
                    arrange += f"        const char* {param_name}_var = \"\";\n"
        
        return arrange
    
    def _generate_assert(self, func_dep: FunctionDependency, case_type: str) -> str:
        """生成Assert部分"""
        
        assert_stmt = ""
        
        if func_dep.return_type == 'void':
            assert_stmt = "        // Function returns void, just verify no crash\n        EXPECT_TRUE(true);"
        elif 'int' in func_dep.return_type or func_dep.return_type == 'int32_t':
            if case_type == "normal":
                assert_stmt = "        EXPECT_EQ(result, 0);  // 期望成功返回0"
            else:
                assert_stmt = "        EXPECT_NE(result, 0);  // 期望返回错误"
        elif 'float' in func_dep.return_type or 'double' in func_dep.return_type:
            assert_stmt = "        EXPECT_NEAR(result, 0.0f, 0.01f);  // 期望返回接近0"
        else:
            assert_stmt = "        EXPECT_TRUE(true);  // Add proper assertion"
        
        return assert_stmt
    
    def generate_mock_header(self, external_calls: set) -> str:
        """生成Mock头部（用于扩展）"""
        
        mock_header = """
#ifndef MOCK_DEFINITIONS_H
#define MOCK_DEFINITIONS_H

// 自动生成的Mock定义，可在此处添加自定义Mock类

"""
        
        for call in sorted(external_calls):
            mock_header += f"""class Mock{call.capitalize()} {{
public:
    MOCK_METHOD(int32_t, {call}, ());
}};

"""
        
        mock_header += "\n#endif"
        
        return mock_header
