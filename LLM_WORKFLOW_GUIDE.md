# LLM-Based C Unit Test Generation Workflow

## 概述

这个工作流将以下组件结合在一起，实现一个 **AI驱动的完整UT生成系统**：

- **vLLM** + **Qwen3 Coder** 大模型：生成高质量的测试代码
- **clang/compile_commands.json**：提供精准的编译信息和代码上下文
- **Google Test (gtest)**：单元测试框架
- **自定义代码分析器**：提取函数签名和依赖关系

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        v                  v                  v
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│  Code Analyzer   │  │   Compile    │  │   LLM Client     │
│ (AST Parsing)    │  │  Commands    │  │ (vLLM + Qwen3)   │
│                  │  │   Parser     │  │                  │
└────────┬─────────┘  └────────┬─────┘  └─────────┬────────┘
         │                     │               │
         │ Functions           │ Compile       │
         │ Dependencies        │ Flags         │
         │                     │ Include Dirs  │
         │                     │ Macros        │ LLM Inference
         │                     │               │
         └─────────────────────┼───────────────┘
                               │
                    ┌──────────v──────────┐
                    │  LLM Test Generator │
                    │  (Prompt Builder)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────v──────────────┐
                    │ Generated Test Code     │
                    │ (C++ with gtest)        │
                    └─────────────────────────┘
```

## 前置环境设置

### 1. 安装依赖包

```bash
pip install requests  # 用于调用vLLM API
```

### 2. 部署vLLM & Qwen3 Coder

在远程服务器上启动vLLM服务：

```bash
# 安装vLLM
pip install vllm

# 启动服务（假设服务器地址为 192.168.1.100:8000）
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --tensor-parallel-size 2 \
  --port 8000
```

或使用Docker：

```bash
docker run --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --tensor-parallel-size 2
```

验证服务运行：

```bash
curl http://192.168.1.100:8000/v1/models
```

### 3. 生成compile_commands.json

```bash
# 在项目目录下运行
mkdir -p build
cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
# compile_commands.json 会生成在 build/ 目录
```

## 使用指南

### 基本用法

```bash
# 进入项目tools目录
cd tools

# 运行完整工作流
python ut_workflow_llm.py \
  --project-dir .. \
  --compile-commands ../build/compile_commands.json \
  --llm-api http://192.168.1.100:8000 \
  --llm-model qwen-coder
```

### 生成特定函数的测试

```bash
# 只为 validate_name 和 db_init 生成测试
python ut_workflow_llm.py \
  --project-dir .. \
  --compile-commands ../build/compile_commands.json \
  --functions validate_name db_init \
  --output-dir ../test/llm_generated
```

### 仅分析代码（不生成测试）

```bash
python ut_workflow_llm.py \
  --project-dir .. \
  --compile-commands ../build/compile_commands.json \
  --analyze-only
```

### 显示工作流信息

```bash
python ut_workflow_llm.py --info-only
```

## 文件结构

```
tools/
├── llm_client.py                    # vLLM API客户端
├── compile_commands_analyzer.py     # compile_commands.json解析器
├── llm_test_generator.py            # LLM测试代码生成器
├── ut_workflow_llm.py               # 主工作流脚本
├── c_code_analyzer.py               # 原始代码分析器
├── gtest_generator.py               # 模板化测试生成器（参考）
└── ut_workflow.py                   # 原始工作流（参考）
```

## 核心组件详解

### 1. LLM Client (`llm_client.py`)

**功能**：与vLLM服务通信

```python
from llm_client import VLLMClient

client = VLLMClient(api_base="http://192.168.1.100:8000", 
                   model="qwen-coder")

# 生成文本
response = client.generate(
    prompt="Generate a C function that validates names",
    temperature=0.7,
    max_tokens=2048
)
```

**关键参数**：
- `temperature`: 0.7（推荐）- 平衡创意和准确性
- `max_tokens`: 4096-8192 - 足以生成完整测试
- `top_p`: 0.95（推荐）- nucleus采样

### 2. Compile Commands Parser (`compile_commands_analyzer.py`)

**功能**：从compile_commands.json提取编译信息

```python
from compile_commands_analyzer import CompileCommandsAnalyzer

analyzer = CompileCommandsAnalyzer("build/compile_commands.json")
analyzer.analyze_all()

# 获取所有include目录
includes = analyzer.get_all_includes()

# 获取所有宏定义
defines = analyzer.get_all_defines()

# 获取特定文件的编译信息
info = analyzer.get_compile_info("src/validator.c")
```

### 3. LLM Test Generator (`llm_test_generator.py`)

**功能**：使用LLM生成测试代码

```python
from llm_test_generator import LLMTestGenerator
from c_code_analyzer import FunctionDependency

generator = LLMTestGenerator(llm_client)

# 为函数生成测试
func_dep = FunctionDependency(...)
test_code = generator.generate_test_file(
    func_dep,
    compile_info=compile_info,
    extra_context="Function validates student names..."
)
```

**提示词工程策略**：
- 提供完整的函数签名和参数信息
- 列出所有外部依赖和需要mock的函数
- 包含编译标志和宏定义
- 明确指定测试框架（gtest/gmock）
- 要求覆盖边界情况和错误处理

### 4. 工作流管理 (`ut_workflow_llm.py`)

**核心步骤**：

1. **代码分析阶段**
   - 解析所有源文件和头文件
   - 提取函数签名、参数、返回类型
   - 识别外部函数调用

2. **编译信息提取**
   - 解析compile_commands.json
   - 获取include路径
   - 收集宏定义和编译选项

3. **LLM测试生成**
   - 为每个函数构造精细化提示词
   - 调用vLLM获得测试代码
   - 后处理和清理响应

4. **验证和保存**
   - 基本的语法检查
   - 保存为.cpp文件
   - 生成测试报告

## 工作流示例

### 完整示例流程

```bash
# 1. 编译项目并生成compile_commands.json
cd /home/user/c-unit-test-workflow
mkdir -p build-llm && cd build-llm
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
cd ..

# 2. 运行LLM工作流
python tools/ut_workflow_llm.py \
  --project-dir . \
  --compile-commands build-llm/compile_commands.json \
  --llm-api http://192.168.1.100:8000 \
  --llm-model qwen-coder \
  --functions validate_name validate_score validate_student_id

# 3. 结果保存在 test/validate_name_llm_test.cpp 等
```

### 输出示例

```
[LLM-based Unit Test Generation Workflow]
============================================================

[Step 1/4] Analyzing C codebase...
============================================================
✓ Found 10 functions
  - int validate_student_name(...)
    Calls: strlen
  - int validate_score(...)
  - int db_init(...)
    Calls: memset, malloc

[Step 2/4] Extracting compile information...
============================================================

[Compile Commands Summary]
============================================================

Source files: 4
Include directories: 3
Macros defined: 5

[Step 3/4] Generating tests with LLM...
============================================================
Generating tests for 3 functions...

[1/3] validate_name() from src/validator.c
  ✓ Saved to test/validate_name_llm_test.cpp

[2/3] validate_score() from src/validator.c
  ✓ Saved to test/validate_score_llm_test.cpp

[3/3] validate_student_id() from src/validator.c
  ✓ Saved to test/validate_student_id_llm_test.cpp

[Step 4/4] Verifying generated tests...
============================================================
Found 3 test files
  ✓ validate_name_llm_test.cpp - Valid
  ✓ validate_score_llm_test.cpp - Valid
  ✓ validate_student_id_llm_test.cpp - Valid

✓ Workflow completed!
```

## 生成的测试示例

LLM生成的测试代码示例（针对validate_name函数）：

```cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "validator.h"

using ::testing::Return;
using ::testing::_;

class ValidateNameTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Initialize test fixtures
    }
};

// Test valid names
TEST_F(ValidateNameTest, ValidName_AlphabeticOnly) {
    const char* name = "John";
    EXPECT_EQ(0, validate_student_name(name));
}

TEST_F(ValidateNameTest, ValidName_WithSpaces) {
    const char* name = "John Smith";
    EXPECT_EQ(0, validate_student_name(name));
}

// Test edge cases
TEST_F(ValidateNameTest, EmptyString) {
    const char* name = "";
    EXPECT_EQ(-1, validate_student_name(name));
}

TEST_F(ValidateNameTest, NullPointer) {
    EXPECT_EQ(-1, validate_student_name(NULL));
}

// Test boundary conditions
TEST_F(ValidateNameTest, MaxLengthName) {
    char name[64];
    memset(name, 'A', 63);
    name[63] = '\0';
    EXPECT_EQ(0, validate_student_name(name));
}

TEST_F(ValidateNameTest, ExceedsMaxLength) {
    char name[65];
    memset(name, 'A', 64);
    name[64] = '\0';
    EXPECT_EQ(-1, validate_student_name(name));
}
```

## 故障排除

### 问题1：无法连接vLLM服务

```
✗ Cannot connect to vLLM: Connection refused
```

**解决方案**：
1. 检查vLLM服务是否正常运行
2. 检查API地址和端口是否正确
3. 检查防火墙设置

```bash
# 测试连接
curl http://192.168.1.100:8000/v1/models
```

### 问题2：compile_commands.json文件未找到

```
✗ compile_commands.json not found
```

**解决方案**：
```bash
# 重新生成compile_commands.json
cd project_directory
rm -rf build
mkdir build
cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
```

### 问题3：生成的测试代码不完整

**可能原因**：
- LLM超时或被中断
- max_tokens设置过小
- prompt过于复杂

**解决方案**：
- 增加max_tokens（例如8192）
- 减少single_functions数量
- 简化extra_context

### 问题4：mock定义错误

**解决方案**：
- 检查external_calls是否正确识别
- 在extra_context中补充额外说明
- 手动调整mock定义

## 性能优化建议

### 1. 批量处理

```bash
# 分批生成测试，避免超时
python ut_workflow_llm.py \
  --functions func1 func2 func3  # 一次3-5个函数
```

### 2. 调整LLM参数

```python
# 温度设置
# 较低温度 (0.3-0.5) - 更准确，更稳定
# 中等温度 (0.7) - 推荐
# 较高温度 (0.9-1.5) - 更创意，可能不稳定
```

### 3. 缓存编译信息

工作流会自动缓存compile_commands.json的解析结果。

## 集成到CI/CD

### GitHub Actions示例

```yaml
name: Generate Unit Tests with LLM

on: [push, pull_request]

jobs:
  generate-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Generate compile_commands.json
        run: |
          mkdir -p build
          cd build
          cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: Generate tests with LLM
        env:
          LLM_API: ${{ secrets.LLM_API_URL }}
        run: |
          python tools/ut_workflow_llm.py \
            --project-dir . \
            --compile-commands build/compile_commands.json \
            --llm-api $LLM_API
      
      - name: Commit and push tests
        run: |
          git add test/*_llm_test.cpp
          git commit -m "Generate unit tests with LLM"
          git push
```

## 最佳实践

1. **逐步验证**
   - 先对单个简单函数进行测试
   - 验证生成的测试质量
   - 再批量处理复杂函数

2. **人工审查**
   - 生成的测试需要人工审查
   - 补充缺失的边界情况
   - 验证mock定义的正确性

3. **版本控制**
   - 将生成的测试纳入版本控制
   - 保留原始template生成器作为参考
   - 定期审计和更新测试

4. **文档记录**
   - 在extra_context中记录特殊需求
   - 添加测试覆盖率注释
   - 保留更改日志

## 参参考资源

- vLLM 文档：https://docs.vllm.ai
- Qwen 模型：https://huggingface.co/Qwen
- Google Test 文档：https://google.github.io/googletest
- compile_commands.json 标准：https://clang.llvm.org/docs/JSONCompilationDatabase.html

## 许可证

MIT License

## 支持

如有问题，请提交Issue或参考项目文档。
