#!/usr/bin/env python3
"""
Test Build and Execution Manager
管理测试的编译和执行
"""

import os
import subprocess
import sys
import platform
import re
from pathlib import Path


class TestExecutor:
    """测试执行管理器"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.build_dir = os.path.join(project_dir, 'build')
        self.test_dir = os.path.join(project_dir, 'test')
    
    def build_tests(self) -> bool:
        """编译测试"""
        print("[3/4] Building tests with CMake...")
        
        # 创建build目录
        os.makedirs(self.build_dir, exist_ok=True)
        
        # 运行cmake
        try:
            print(f"  → Running cmake configuration...")
            if platform.system() == 'Windows':
                # Windows使用Visual Studio
                result = subprocess.run(
                    ['cmake', '..', '-G', 'Visual Studio 16 2019'],
                    cwd=self.build_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            else:
                # Linux/Mac使用Makefile
                result = subprocess.run(
                    ['cmake', '..'],
                    cwd=self.build_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            if result.returncode != 0:
                print(f"  ✗ CMake configuration failed:")
                print(result.stderr)
                return False
            
            print(f"  ✓ CMake configuration completed")
            
            # 编译
            print(f"  → Compiling...")
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['cmake', '--build', '.', '--config', 'Debug'],
                    cwd=self.build_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            else:
                result = subprocess.run(
                    ['make'],
                    cwd=self.build_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            
            if result.returncode != 0:
                print(f"  ✗ Build failed:")
                print(result.stderr)
                return False
            
            print(f"  ✓ Build completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            print("  ✗ Build timeout")
            return False
        except Exception as e:
            print(f"  ✗ Build error: {e}")
            return False
    
    def run_tests(self) -> dict:
        """运行所有测试"""
        print("\n[4/4] Running tests...")
        
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'tests': []
        }
        
        # 查找所有测试可执行文件
        test_executables = self._find_test_executables()
        
        if not test_executables:
            print("  ⚠ No test executables found")
            return results
        
        for test_exe in test_executables:
            print(f"\n  Running: {os.path.basename(test_exe)}")
            try:
                result = subprocess.run(
                    [test_exe],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # 解析测试输出
                test_result = self._parse_gtest_output(result.stdout, result.stderr)
                test_result['executable'] = os.path.basename(test_exe)
                results['tests'].append(test_result)
                
                results['total'] += test_result['total']
                results['passed'] += test_result['passed']
                results['failed'] += test_result['failed']
                
                # 打印测试结果摘要
                print(f"    Total: {test_result['total']}, "
                      f"Passed: {test_result['passed']}, "
                      f"Failed: {test_result['failed']}")
                
                if test_result['failed'] > 0 and test_result['failures']:
                    print(f"    Failures:")
                    for failure in test_result['failures']:
                        print(f"      - {failure}")
                
            except subprocess.TimeoutExpired:
                print(f"    ✗ Timeout")
            except Exception as e:
                print(f"    ✗ Error: {e}")
        
        return results
    
    def _find_test_executables(self) -> list:
        """查找测试可执行文件"""
        executables = []
        
        if not os.path.exists(self.build_dir):
            return executables
        
        # Windows下查找exe文件
        if platform.system() == 'Windows':
            for root, dirs, files in os.walk(self.build_dir):
                for file in files:
                    if file.endswith('_test.exe'):
                        executables.append(os.path.join(root, file))
        else:
            # Linux/Mac查找无扩展名的可执行文件
            for root, dirs, files in os.walk(self.build_dir):
                for file in files:
                    if file.endswith('_test'):
                        executables.append(os.path.join(root, file))
        
        return sorted(executables)
    
    def _parse_gtest_output(self, stdout: str, stderr: str) -> dict:
        """解析GTest输出"""
        result = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'failures': []
        }
        
        output = stdout + stderr
        
        # 查找测试统计行
        # 格式: [----------] 5 tests from ValidatorTest (0 ms total)
        match = re.search(r'\[\s*-+\s*\]\s+(\d+)\s+tests?', output)
        if match:
            result['total'] = int(match.group(1))
        
        # 查找通过/失败统计
        # 格式: [ PASSED ] 5 tests from ValidatorTest.
        match = re.search(r'\[\s*PASSED\s*\]\s+(\d+)\s+test', output)
        if match:
            result['passed'] = int(match.group(1))
        
        # 查找失败统计  
        # 格式: [ FAILED ] 1 test from ValidatorTest
        match = re.search(r'\[\s*FAILED\s*\]\s+(\d+)\s+test', output)
        if match:
            result['failed'] = int(match.group(1))
        
        # 自动计算
        if result['total'] > 0 and result['passed'] == 0 and result['failed'] == 0:
            # 从输出中查找PASS和FAIL关键字
            pass_count = output.count('[ OK ]')
            fail_count = len(re.findall(r'\[\s*FAILED\s*\]', output))
            result['passed'] = pass_count
            result['failed'] = fail_count
        
        # 提取失败详情
        failure_pattern = r'\[\s*FAILED\s*\].*?:\s*(.+?)(?=\[|$)'
        for match in re.finditer(failure_pattern, output, re.DOTALL):
            failure_text = match.group(1).strip().split('\n')[0]
            result['failures'].append(failure_text)
        
        return result
    
    def print_summary(self, results: dict) -> None:
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("TEST EXECUTION SUMMARY")
        print("=" * 60)
        
        total = results['total']
        passed = results['passed']
        failed = results['failed']
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} {'✓' if passed > 0 else ''}")
        print(f"Failed: {failed} {'✗' if failed > 0 else ''}")
        
        if total > 0:
            pass_rate = (passed / total) * 100
            print(f"Pass Rate: {pass_rate:.1f}%")
        
        if failed > 0:
            print("\nFailed Tests Details:")
            for test in results['tests']:
                if test['failed'] > 0:
                    print(f"\n  {test['executable']}:")
                    for failure in test['failures']:
                        print(f"    - {failure}")
        
        print("\n" + "=" * 60)
        
        return failed == 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test Build and Execution Manager'
    )
    parser.add_argument('--project', required=True,
                       help='Project root directory')
    parser.add_argument('--build', action='store_true',
                       help='Build tests')
    parser.add_argument('--run', action='store_true',
                       help='Run tests')
    parser.add_argument('--build-and-run', action='store_true',
                       help='Build and run tests')
    
    args = parser.parse_args()
    
    executor = TestExecutor(args.project)
    
    if args.build or args.build_and_run:
        if not executor.build_tests():
            sys.exit(1)
    
    if args.run or args.build_and_run:
        results = executor.run_tests()
        success = executor.print_summary(results)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
