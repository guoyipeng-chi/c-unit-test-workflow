# vLLM 配置脚本 - Windows PowerShell
# 使用方法: .\vllm_config.ps1

Write-Host "配置 vLLM 环境变量..." -ForegroundColor Cyan

# ============================================
# 选择配置方案（取消注释一个）
# ============================================

# 方案 1: 本地部署
# $env:VLLM_API_BASE = "http://localhost:8000"
# $env:VLLM_MODEL = "qwen-coder"

# 方案 2: 远程服务器（内网）
$env:VLLM_API_BASE = "http://192.168.1.100:8000"
$env:VLLM_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"

# 方案 3: 云服务器
# $env:VLLM_API_BASE = "http://your-server.com:8000"
# $env:VLLM_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"

# ============================================
# 其他配置
# ============================================
$env:VLLM_TIMEOUT = "120"
# $env:VLLM_API_KEY = "your-api-key"

# ============================================
# 显示当前配置
# ============================================
Write-Host "`n✓ 环境变量已设置:" -ForegroundColor Green
Write-Host "  VLLM_API_BASE: $env:VLLM_API_BASE"
Write-Host "  VLLM_MODEL: $env:VLLM_MODEL"
Write-Host "  VLLM_TIMEOUT: $env:VLLM_TIMEOUT"

Write-Host "`n使用示例:" -ForegroundColor Yellow
Write-Host "  python quickstart_llm.py --check"
Write-Host "  python quickstart_llm.py --generate"
Write-Host "  python tools/ut_workflow_llm.py --functions add_student"
