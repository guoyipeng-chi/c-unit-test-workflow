@echo off
REM vLLM 配置脚本 - Windows CMD
REM 使用方法: vllm_config.bat

echo 配置 vLLM 环境变量...

REM ============================================
REM 选择配置方案（取消注释一个）
REM ============================================

REM 方案 1: 本地部署
REM set VLLM_API_BASE=http://localhost:8000
REM set VLLM_MODEL=qwen-coder

REM 方案 2: 远程服务器（内网）
set VLLM_API_BASE=http://192.168.1.100:8000
set VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

REM 方案 3: 云服务器
REM set VLLM_API_BASE=http://your-server.com:8000
REM set VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

REM ============================================
REM 其他配置
REM ============================================
set VLLM_TIMEOUT=120
REM set VLLM_API_KEY=your-api-key

REM ============================================
REM 显示当前配置
REM ============================================
echo.
echo ✓ 环境变量已设置:
echo   VLLM_API_BASE: %VLLM_API_BASE%
echo   VLLM_MODEL: %VLLM_MODEL%
echo   VLLM_TIMEOUT: %VLLM_TIMEOUT%
echo.
echo 使用示例:
echo   python quickstart_llm.py --check
echo   python quickstart_llm.py --generate
echo   python tools\ut_workflow_llm.py --functions add_student
