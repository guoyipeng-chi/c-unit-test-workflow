@echo off
REM Quick Start Script for Windows
REM 快速开始脚本

setlocal enabledelayedexpansion

echo.
echo ==========================================
echo   C Language Unit Test Workflow
echo   Quick Start Script - Windows
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Python not found. Please install Python 3.7+
    exit /b 1
)

REM 检查CMake
cmake --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ CMake not found. Please install CMake 3.10+
    exit /b 1
)

echo ✓ Environment check passed
echo.

REM 获取脚本目录
set SCRIPT_DIR=%~dp0

REM 运行主工作流
echo [1/1] Running C Unit Test Workflow...
python "%SCRIPT_DIR%main.py" --project "%SCRIPT_DIR%" --full

if %errorlevel% neq 0 (
    echo.
    echo ✗ Workflow failed!
    exit /b 1
)

echo.
echo ✓ Workflow completed!

pause
