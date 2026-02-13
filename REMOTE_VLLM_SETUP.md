# 🌐 vLLM 远程部署配置指南

## 快速开始

### 方式 1️⃣: 使用环境变量（推荐） ⭐

**Linux/macOS:**
```bash
# 临时设置（当前终端有效）
export VLLM_API_BASE=http://192.168.1.100:8000
export VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

# 或使用配置文件
source vllm_config.env

# 验证配置
python quickstart_llm.py --check
```

**Windows PowerShell:**
```powershell
# 临时设置
$env:VLLM_API_BASE = "http://192.168.1.100:8000"
$env:VLLM_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"

# 或使用配置脚本
.\vllm_config.ps1

# 验证配置
python quickstart_llm.py --check
```

**Windows CMD:**
```cmd
REM 临时设置
set VLLM_API_BASE=http://192.168.1.100:8000
set VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

REM 或使用批处理脚本
vllm_config.bat

REM 验证配置
python quickstart_llm.py --check
```

---

### 方式 2️⃣: 命令行参数

```bash
# 直接在命令行指定
python tools/ut_workflow_llm.py \
  --llm-api http://192.168.1.100:8000 \
  --llm-model Qwen/Qwen2.5-Coder-32B-Instruct \
  --functions validate_student_name
```

---

### 方式 3️⃣: 修改配置文件

编辑 `llm_workflow_config.json`:
```json
{
  "llm": {
    "api_base": "http://192.168.1.100:8000",
    "model": "Qwen/Qwen2.5-Coder-32B-Instruct"
  }
}
```

---

## 配置优先级

```
环境变量 > 命令行参数 > 配置文件 > 默认值
```

**示例：**
```bash
# 假设配置文件中: "api_base": "http://localhost:8000"
# 设置环境变量
export VLLM_API_BASE=http://192.168.1.100:8000

# 运行（将使用环境变量的地址）
python quickstart_llm.py --generate
# → 实际连接: http://192.168.1.100:8000 ✓
```

---

## 常见部署场景

### 场景 1: 本地开发（默认）
```bash
# 不设置任何配置，使用默认值
python quickstart_llm.py --generate
# → 连接: http://localhost:8000
```

---

### 场景 2: 内网服务器
```bash
# 服务器IP: 192.168.1.100
export VLLM_API_BASE=http://192.168.1.100:8000
python quickstart_llm.py --generate
```

**vLLM服务器端启动命令：**
```bash
# 在服务器上启动vLLM
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --host 0.0.0.0 \
  --port 8000
```

---

### 场景 3: 云服务器（公网）
```bash
# 使用域名
export VLLM_API_BASE=http://vllm.yourcompany.com:8000
python quickstart_llm.py --generate
```

或使用IP:
```bash
export VLLM_API_BASE=http://123.45.67.89:8000
python quickstart_llm.py --generate
```

---

### 场景 4: SSH 端口转发
如果服务器防火墙限制，使用SSH隧道：

```bash
# 本地终端1: 建立隧道
ssh -L 8000:localhost:8000 user@remote-server

# 本地终端2: 使用本地地址
export VLLM_API_BASE=http://localhost:8000
python quickstart_llm.py --generate
# → 实际通过SSH转发到远程服务器
```

---

### 场景 5: Docker容器
```bash
# 启动vLLM容器（服务器端）
docker run -d --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-Coder-32B-Instruct

# 客户端连接
export VLLM_API_BASE=http://server-ip:8000
python quickstart_llm.py --generate
```

---

## 验证连接

### 方法 1: 使用工具自带检查
```bash
python quickstart_llm.py --check
```

输出示例：
```
✓ Python version: 3.12.0
✓ vLLM service: Connected to http://192.168.1.100:8000
✓ compile_commands.json: Found
...
```

---

### 方法 2: 手动测试API
```bash
# 测试 /v1/models 端点
curl http://192.168.1.100:8000/v1/models

# 预期输出:
# {"object":"list","data":[{"id":"Qwen/Qwen2.5-Coder-32B-Instruct",...}]}
```

---

### 方法 3: Python脚本测试
```python
import os
from tools.llm_client import VLLMClient

# 测试连接
client = VLLMClient()  # 自动读取环境变量
print(f"连接到: {client.api_base}")
print(f"模型: {client.model}")
```

---

## 环境变量列表

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `VLLM_API_BASE` | vLLM服务地址 | `http://localhost:8000` | `http://192.168.1.100:8000` |
| `VLLM_MODEL` | 模型名称 | `qwen-coder` | `Qwen/Qwen2.5-Coder-32B-Instruct` |
| `VLLM_API_KEY` | API密钥（如需要） | `dummy` | `sk-xxxxx` |
| `VLLM_TIMEOUT` | 请求超时（秒） | `120` | `180` |

---

## 常见问题

### Q1: 连接被拒绝 (Connection refused)
**排查步骤：**
```bash
# 1. 检查服务器是否运行
curl http://server-ip:8000/v1/models

# 2. 检查防火墙
# 服务器端：
sudo ufw allow 8000/tcp

# 3. 检查vLLM是否绑定0.0.0.0
# vLLM启动时必须：--host 0.0.0.0
```

---

### Q2: 超时 (Timeout)
**解决方法：**
```bash
# 增加超时时间
export VLLM_TIMEOUT=300

# 或命令行
python tools/ut_workflow_llm.py --llm-timeout 300
```

---

### Q3: 模型找不到 (Model not found)
**检查：**
```bash
# 1. 查看服务器支持的模型
curl http://server-ip:8000/v1/models | jq

# 2. 确保模型名称完全匹配
export VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct  # 精确名称
```

---

### Q4: 环境变量不生效
**检查：**
```bash
# Linux/macOS
echo $VLLM_API_BASE

# Windows PowerShell
echo $env:VLLM_API_BASE

# Windows CMD
echo %VLLM_API_BASE%

# 如果为空，说明没有正确设置
```

---

## 性能优化

### 网络延迟优化
```bash
# 1. 使用内网地址（比公网快）
export VLLM_API_BASE=http://192.168.1.100:8000  # ✓ 内网
# 而不是:
# export VLLM_API_BASE=http://123.45.67.89:8000  # ✗ 公网

# 2. 减少max_tokens
# 编辑 llm_workflow_config.json:
"max_tokens": 2048  # 从4096减少到2048
```

---

### 批量生成优化
```bash
# 生成多个函数时，在服务器附近运行
# 如果延迟高，考虑：
# 1. 在远程服务器上clone项目并运行
# 2. 使用SSH端口转发减少延迟
```

---

## 安全建议

### 1. 使用API Key
```bash
# 服务器端启动vLLM时设置密钥
python -m vllm.entrypoints.openai.api_server \
  --api-key your-secret-key \
  ...

# 客户端配置
export VLLM_API_KEY=your-secret-key
```

---

### 2. 网络隔离
- ✅ 内网部署最安全
- ⚠️ 公网部署必须加API Key
- ⚠️ 使用HTTPS代替HTTP（nginx反向代理）

---

### 3. 防火墙配置
```bash
# 服务器端：仅允许特定IP
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

---

## 完整示例

### 从零开始配置远程vLLM

**服务器端（192.168.1.100）：**
```bash
# 1. 安装vLLM
pip install vllm

# 2. 启动服务
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1

# 3. 验证
curl http://localhost:8000/v1/models
```

**客户端（你的开发机）：**
```bash
# 1. 配置环境变量
export VLLM_API_BASE=http://192.168.1.100:8000
export VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

# 2. 验证连接
python quickstart_llm.py --check

# 3. 生成测试
python quickstart_llm.py --generate
```

---

## 配置文件模板

项目提供了3个配置文件模板：

| 文件 | 平台 | 使用方法 |
|------|------|----------|
| `vllm_config.env` | Linux/macOS | `source vllm_config.env` |
| `vllm_config.ps1` | Windows PowerShell | `.\vllm_config.ps1` |
| `vllm_config.bat` | Windows CMD | `vllm_config.bat` |

根据需要编辑这些文件，然后运行即可！

---

**更多帮助：**
- 查看 `LLM_WORKFLOW_GUIDE.md` - vLLM部署详解
- 查看 `QUICKREF_LLM.md` - 快速参考
- 运行 `python quickstart_llm.py --help` - 命令帮助
