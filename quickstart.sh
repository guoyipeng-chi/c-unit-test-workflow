#!/bin/bash
# Quick Start Script for Linux/Mac
# 快速开始脚本

set -e

echo "=========================================="
echo "  C Language Unit Test Workflow"
echo "  Quick Start Script"
echo "=========================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python3 not found. Please install Python 3.7+"
    exit 1
fi

# 检查CMake
if ! command -v cmake &> /dev/null; then
    echo "✗ CMake not found. Please install CMake 3.10+"
    exit 1
fi

# 检查编译器
if ! command -v gcc &> /dev/null && ! command -v clang &> /dev/null; then
    echo "✗ No C/C++ compiler found. Please install GCC or Clang"
    exit 1
fi

echo "✓ Environment check passed"
echo ""

# 确定脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 运行主工作流
echo "[1/1] Running C Unit Test Workflow..."
python3 "$SCRIPT_DIR/main.py" --project "$SCRIPT_DIR" --full

echo ""
echo "✓ Workflow completed!"
