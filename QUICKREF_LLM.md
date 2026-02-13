# LLM-Based UT Generation - Quick Reference

## 🚀 快速开始（5分钟）

### 前置条件
- ✅ compile_commands.json 已生成（本项目已有）
- ✅ vLLM服务已启动（默认 http://localhost:8000）

### 一句话启动

```bash
# 方式1：交互式菜单
python quickstart_llm.py --interactive

# 方式2：直接运行完整工作流
python tools/ut_workflow_llm.py \
  --project-dir . \
  --compile-commands build-ninja-msvc/compile_commands.json

# 方式3：仅分析代码
python tools/ut_workflow_llm.py --analyze-only

# 方式4：为特定函数生成测试
python tools/ut_workflow_llm.py \
  --functions validate_name db_init add_student
```

## 📁 新增文件说明

### 核心组件

| 文件 | 功能 | 说明 |
|------|------|------|
| `llm_client.py` | vLLM API客户端 | 与远程Qwen3 Coder通信 |
| `compile_commands_analyzer.py` | 编译命令解析器 | 从compile_commands.json提取编译信息 |
| `llm_test_generator.py` | LLM测试生成器 | 使用提示工程生成测试代码 |
| `ut_workflow_llm.py` | 主工作流脚本 | 协调所有组件 |

### 辅助文件

| 文件 | 功能 |
|------|------|
| `quickstart_llm.py` | 快速启动脚本 |
| `llm_workflow_config.json` | 配置文件 |
| `LLM_WORKFLOW_GUIDE.md` | 详细文档 |
| `QUICKREF_LLM.md` | 本文档 |

## 🔧 工作流架构

```
代码分析 → 编译信息提取 → LLM调用 → 测试生成 → 验证保存
```

**关键特性**：
- 🤖 使用Qwen3 Coder大模型生成高质量测试
- 🔍 从compile_commands.json提取完整的编译上下文
- 📦 支持gmock自动mock外部函数
- ✅ 智能识别边界情况和错误处理
- 🚀 批量处理多个函数

## 💡 使用示例

### 示例1：生成单个函数的测试

```bash
python tools/ut_workflow_llm.py \
  --project-dir . \
  --compile-commands build-ninja-msvc/compile_commands.json \
  --functions validate_name \
  --output-dir test/llm_generated
```

**输出**：`test/llm_generated/validate_name_llm_test.cpp`

### 示例2：分析代码不生成测试

```bash
python tools/ut_workflow_llm.py --analyze-only
```

### 示例3：配置远程vLLM服务

```bash
# 修改 llm_workflow_config.json
{
  "llm": {
    "api_base": "http://remote-server.com:8000",
    "model": "qwen-coder"
  }
}

# 或使用命令行参数
python tools/ut_workflow_llm.py \
  --llm-api http://remote-server.com:8000
```

## 📊 工作流输出

### 生成的测试文件结构

```cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "validator.h"

// Mock定义（自动生成）
class MockDatabase {
public:
    MOCK_METHOD(int, query, (int), ());
};

// 测试Fixture类
class ValidateNameTest : public ::testing::Test {
protected:
    void SetUp() override { ... }
};

// 多个测试用例
TEST_F(ValidateNameTest, ValidName) { ... }
TEST_F(ValidateNameTest, NullPointer) { ... }
TEST_F(ValidateNameTest, EmptyString) { ... }
TEST_F(ValidateNameTest, MaxLength) { ... }
```

## 🔌 API配置

### vLLM本地部署

```bash
# 安装vLLM
pip install vllm

# 启动服务
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --tensor-parallel-size 2 \
  --port 8000

# 验证
curl http://localhost:8000/v1/models
```

### 参数调优

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| temperature | 0.7 | 平衡创意和准确 |
| max_tokens | 4096-8192 | 足以生成完整测试 |
| top_p | 0.95 | nucleus采样 |
| timeout | 120s | 请求超时 |

## 🎯 测试生成策略

### 提示词工程（Prompt Engineering）

工作流自动构造的提示词包含：

1. **函数签名信息**
   - 函数名、返回类型、参数列表
   
2. **依赖关系**
   - 外部函数调用（需要mock）
   - Include文件
   
3. **编译信息**
   - C/C++标准版本
   - 宏定义
   - 优化级别

4. **生成要求**
   - 使用Google Test框架
   - 创建多个测试用例
   - 覆盖边界情况

## 📈 质量控制

### 自动验证

```bash
# 检查生成的测试文件
python tools/ut_workflow_llm.py --verify
```

验证项目：
- ✅ 包含gtest头文件
- ✅ 定义了TEST或TEST_F
- ✅ 包含EXPECT或ASSERT

### 人工审查清单

- [ ] 所有测试用例都有明确的函数和输入
- [ ] Mock定义与实际函数签名匹配
- [ ] 边界情况都被覆盖（NULL、空、最大值等）
- [ ] 异常处理和错误路径都有测试
- [ ] 变量名和测试名称是否有意义
- [ ] 是否有多余或不必要的依赖

## ⚙️ 故障排查

### 常见问题

**Q: "Cannot connect to vLLM"**
```
A: 检查vLLM服务是否运行：
   curl http://localhost:8000/v1/models
```

**Q: "compile_commands.json not found"**
```
A: 重新生成编译命令：
   cd build-ninja-msvc && cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
```

**Q: 生成的测试代码不完整**
```
A: 增加max_tokens或减少functions数量
```

**Q: timeout错误**
```
A: 增加timeout值或检查网络连接
```

## 📚 相关文档

| 文档 | 内容 |
|------|------|
| [LLM_WORKFLOW_GUIDE.md](LLM_WORKFLOW_GUIDE.md) | 详细技术文档（32KB） |
| [quickstart_llm.py](quickstart_llm.py) | 交互式启动脚本 |
| [llm_workflow_config.json](llm_workflow_config.json) | 配置文件示例 |

## 🔗 相关链接

- **vLLM**: https://github.com/vllm-project/vllm
- **Qwen Models**: https://huggingface.co/Qwen
- **Google Test**: https://github.com/google/googletest
- **Project README**: [README.md](README.md)

## 💻 系统要求

- Python 3.8+
- 4GB+ RAM
- vLLM服务可访问
- CMake + 编译器（用于生成compile_commands.json）

## ⏱️ 性能对标

| 操作 | 时间 | 说明 |
|------|------|------|
| 代码分析 | < 1s | 解析源代码 |
| 编译信息提取 | < 0.5s | 解析JSON |
| 单个函数测试生成 | 10-30s | vLLM推理 |
| 5个函数批量生成 | 60-120s | 並行度低 |

## 🎓 学习资源

1. **提示词工程**：查看 `llm_test_generator.py` 中的 `_build_prompt()` 方法
2. **编译命令解析**：查看 `compile_commands_analyzer.py`
3. **工作流整合**：查看 `ut_workflow_llm.py`

## 🤝 最佳实践

✅ **推荐**
- 为基础函数先生成测试验证效果
- 保留原始生成的代码用于评估
- 定期更新LLM模型版本
- 在CI/CD中自动化测试生成

❌ **禁忌**
- 不要盲目相信生成的所有代码
- 不要跳过人工审查环节
- 不要在生产中使用未验证的测试
- 不要忽略编译或执行错误

## 📞 获取帮助

```bash
# 查看完整帮助
python tools/ut_workflow_llm.py --help

# 查看快速启动帮助
python quickstart_llm.py --help

# 交互式指引
python quickstart_llm.py --interactive
```

---

**最后更新**: 2026-02-13  
**版本**: 1.0  
**许可**: MIT
