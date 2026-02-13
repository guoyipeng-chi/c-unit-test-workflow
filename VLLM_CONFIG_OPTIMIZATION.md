# 🌐 vLLM 远程配置优化总结

## 优化内容

### ✅ 1. 支持多种配置方式

**优先级（从高到低）：**
```
环境变量 > 命令行参数 > 配置文件 > 默认值
```

**示例：**
```bash
# 环境变量（优先级最高）
export VLLM_API_BASE=http://192.168.1.100:8000

# 命令行参数
python tools/ut_workflow_llm.py --llm-api http://server.com:8000

# 配置文件（llm_workflow_config.json）
{
  "llm": {
    "api_base": "http://localhost:8000"
  }
}

# 默认值
http://localhost:8000
```

---

### ✅ 2. 新增文件

| 文件 | 用途 | 平台 |
|------|------|------|
| `vllm_config.env` | 环境变量配置脚本 | Linux/macOS |
| `vllm_config.ps1` | 环境变量配置脚本 | Windows PowerShell |
| `vllm_config.bat` | 环境变量配置脚本 | Windows CMD |
| `REMOTE_VLLM_SETUP.md` | 远程配置完整指南 | 文档 |
| `check_vllm_config.py` | 配置验证工具 | 诊断工具 |

---

### ✅ 3. 支持的环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `VLLM_API_BASE` | vLLM服务地址 | `http://localhost:8000` |
| `VLLM_MODEL` | 模型名称 | `qwen-coder` |
| `VLLM_API_KEY` | API密钥 | `dummy` |
| `VLLM_TIMEOUT` | 超时时间（秒） | `120` |

---

### ✅ 4. 代码改进

**tools/llm_client.py:**
```python
# 新增环境变量支持
self.api_base = (os.getenv('VLLM_API_BASE') or 
                api_base or 
                "http://localhost:8000")
```

**tools/ut_workflow_llm.py:**
```python
# 更新参数说明
parser.add_argument(
    "--llm-api",
    help="vLLM API base URL (环境变量: VLLM_API_BASE)"
)
```

**llm_workflow_config.json:**
```json
{
  "llm": {
    "api_base": "http://localhost:8000",
    "api_base_comment": "可通过环境变量 VLLM_API_BASE 覆盖",
    "remote_examples": {
      "local": "http://localhost:8000",
      "remote_server": "http://192.168.1.100:8000",
      "cloud_server": "http://your-server.com:8000"
    }
  }
}
```

---

## 使用示例

### 场景 1: 本地开发（默认）

```bash
# 不设置任何配置
python quickstart_llm.py --generate
# → 使用默认 http://localhost:8000
```

---

### 场景 2: 内网服务器

**Linux/macOS:**
```bash
export VLLM_API_BASE=http://192.168.1.100:8000
export VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
python quickstart_llm.py --generate
```

**Windows PowerShell:**
```powershell
.\vllm_config.ps1  # 编辑此文件设置服务器地址
python quickstart_llm.py --generate
```

**Windows CMD:**
```cmd
vllm_config.bat  # 编辑此文件设置服务器地址
python quickstart_llm.py --generate
```

---

### 场景 3: 临时使用不同服务器

```bash
# 临时使用命令行参数（不影响环境变量）
python tools/ut_workflow_llm.py \
  --llm-api http://test-server:8000 \
  --functions validate_student_name
```

---

### 场景 4: CI/CD 集成

```bash
# 在CI/CD中设置环境变量
export VLLM_API_BASE=$CI_VLLM_SERVER
export VLLM_API_KEY=$CI_VLLM_TOKEN
python tools/ut_workflow_llm.py --generate
```

---

## 验证配置

### 方法 1: 使用检查工具
```bash
python check_vllm_config.py
```

**输出示例：**
```
============================================================
vLLM 配置检查
============================================================

[1] 环境变量:
  VLLM_API_BASE: http://192.168.1.100:8000
  VLLM_MODEL: Qwen/Qwen2.5-Coder-32B-Instruct
  VLLM_API_KEY: ***
  VLLM_TIMEOUT: 120

[2] 最终配置:
  API地址: http://192.168.1.100:8000
  模型名称: Qwen/Qwen2.5-Coder-32B-Instruct
  超时设置: 120秒

[3] 连接测试:
  ✓ 成功连接到 http://192.168.1.100:8000
  ✓ 可用模型:
    - Qwen/Qwen2.5-Coder-32B-Instruct ← 当前

============================================================
✓ 配置检查通过！可以开始生成测试了。
============================================================
```

---

### 方法 2: 使用工作流检查
```bash
python quickstart_llm.py --check
```

---

### 方法 3: 手动测试
```bash
# 测试API端点
curl http://192.168.1.100:8000/v1/models
```

---

## 配置文件使用

### Linux/macOS

**编辑配置文件：**
```bash
nano vllm_config.env
```

**内容示例：**
```bash
export VLLM_API_BASE=http://192.168.1.100:8000
export VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
```

**加载配置：**
```bash
source vllm_config.env
```

---

### Windows PowerShell

**编辑配置文件：**
```powershell
notepad vllm_config.ps1
```

**运行配置：**
```powershell
.\vllm_config.ps1
```

---

### Windows CMD

**编辑配置文件：**
```cmd
notepad vllm_config.bat
```

**运行配置：**
```cmd
vllm_config.bat
```

---

## 常见问题

### Q1: 环境变量不生效？

**检查：**
```bash
# Linux/macOS
echo $VLLM_API_BASE

# Windows PowerShell
echo $env:VLLM_API_BASE

# Windows CMD
echo %VLLM_API_BASE%
```

**解决：**
- 确保正确使用了 `export` (Linux/macOS)
- 确保在同一终端会话中
- 使用 `source vllm_config.env` 而不是 `bash vllm_config.env`

---

### Q2: 如何覆盖环境变量？

```bash
# 临时覆盖（仅当前命令）
VLLM_API_BASE=http://other-server:8000 python quickstart_llm.py

# 或使用命令行参数
python tools/ut_workflow_llm.py --llm-api http://other-server:8000
```

---

### Q3: 如何在不同项目中使用不同配置？

**方案 1: 使用项目级环境文件**
```bash
# 进入项目目录
cd /path/to/project1
source vllm_config.env  # 项目1的配置

cd /path/to/project2
source vllm_config.env  # 项目2的配置
```

**方案 2: 使用命令行参数**
```bash
# 项目1
python tools/ut_workflow_llm.py --llm-api http://server1:8000

# 项目2
python tools/ut_workflow_llm.py --llm-api http://server2:8000
```

---

## 文档更新

已更新的文档：

1. **REMOTE_VLLM_SETUP.md** - 完整的远程配置指南
2. **QUICKREF_LLM.md** - 添加快速配置说明
3. **llm_workflow_config.json** - 添加配置示例
4. **.gitignore** - 排除敏感配置文件

---

## 优化收益

### 1. 灵活性 ⬆️
- ✅ 支持本地和远程部署
- ✅ 支持多服务器切换
- ✅ 支持CI/CD集成

### 2. 便捷性 ⬆️
- ✅ 一个脚本完成配置
- ✅ 环境变量自动生效
- ✅ 多平台支持（Linux/macOS/Windows）

### 3. 安全性 ⬆️
- ✅ API密钥通过环境变量传递（不在代码中）
- ✅ .gitignore排除敏感配置
- ✅ 支持每个用户独立配置

### 4. 可维护性 ⬆️
- ✅ 配置集中管理
- ✅ 优先级清晰
- ✅ 验证工具帮助诊断

---

## 下一步

1. **配置远程服务器**
   ```bash
   # 编辑配置文件
   nano vllm_config.env  # 或 notepad vllm_config.ps1
   
   # 设置服务器地址
   export VLLM_API_BASE=http://your-server:8000
   ```

2. **验证配置**
   ```bash
   python check_vllm_config.py
   ```

3. **开始使用**
   ```bash
   python quickstart_llm.py --generate
   ```

---

**详细文档：** [REMOTE_VLLM_SETUP.md](REMOTE_VLLM_SETUP.md)
