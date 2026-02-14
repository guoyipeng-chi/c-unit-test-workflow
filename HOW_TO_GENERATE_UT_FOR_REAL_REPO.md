# 🎯 如何针对真实代码仓生成UT用例

这个工作流系统已经能够自动为C项目生成单元测试。现在让你了解如何对真实的代码仓库使用它。

## 📋 前置要求

- ✅ CMake 3.0+ 或 Ninja 1.10+
- ✅ C编译器（gcc/clang/MSVC）
- ✅ Python 3.8+
- ✅ vLLM服务已启动（带Qwen2.5-Coder模型）

## ⚙️ 第1步：准备目标代码仓

### 1.1 代码结构要求

你的项目应该有这样的结构：

```
your-project/
├── CMakeLists.txt          # 必需
├── include/                # 头文件
│   ├── module1.h
│   └── module2.h
├── src/                    # 源文件
│   ├── module1.c
│   └── module2.c
└── test/                   # 测试文件输出目录
    └── (可选，会自动创建)
```

### 1.2 检查CMakeLists.txt

确保CMakeLists.txt配置了编译选项：

```cmake
cmake_minimum_required(VERSION 3.10)
project(your_project C CXX)

# 导出编译命令数据库
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# 添加include目录和源文件
file(GLOB SOURCES "src/*.c")
file(GLOB HEADERS "include/*.h")

# 创建库或可执行文件
add_library(${PROJECT_NAME} ${SOURCES})
target_include_directories(${PROJECT_NAME} PUBLIC include)
```

**关键：** `set(CMAKE_EXPORT_COMPILE_COMMANDS ON)` 这一行必不可少！

## 📦 第2步：生成 compile_commands.json

这个文件包含所有编译信息，LLM需要它来理解你的代码。

### 2.1 使用CMake生成

在你的项目目录中：

```bash
# 创建build目录
mkdir build
cd build

# 使用CMake生成build文件和compile_commands.json
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# 在Windows用MSVC
cmake -G "Visual Studio 17 2022" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# 使用Ninja（推荐，快速）
cmake -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
```

生成完毕后，在 `build/` 目录中会出现 `compile_commands.json`：

```
your-project/
├── CMakeLists.txt
├── build/
│   └── compile_commands.json    # ← 这就是它！
├── include/
├── src/
└── test/
```

### 2.2 检查compile_commands.json

验证文件内容：

```bash
# 查看条目数
cat build/compile_commands.json | grep -c '"file"'

# 查看第一个条目
cat build/compile_commands.json | head -30
```

应该看到像这样的内容：

```json
[
  {
    "directory": "/path/to/your-project/build",
    "command": "cc -I/path/to/include -c /path/to/src/module1.c",
    "file": "/path/to/src/module1.c"
  },
  ...
]
```

## 🚀 第3步：配置LLM工作流

### 3.1 配置vLLM服务地址

**方式A：环境变量（推荐，最灵活）**

```bash
# Linux/macOS
export VLLM_API_BASE=http://localhost:8000
export VLLM_MODEL=qwen2.5-coder-32b
export VLLM_API_KEY=your-api-key  # 如果需要

# Windows PowerShell
$env:VLLM_API_BASE = "http://localhost:8000"
$env:VLLM_MODEL = "qwen2.5-coder-32b"

# Windows CMD
set VLLM_API_BASE=http://localhost:8000
set VLLM_MODEL=qwen2.5-coder-32b
```

**方式B：配置文件**

编辑 `llm_workflow_config.json`：

```json
{
  "llm": {
    "api_base": "http://localhost:8000",
    "model": "qwen2.5-coder-32b",
    "timeout": 300
  },
  "compile_commands": {
    "search_paths": [
      "build/compile_commands.json",
      "compile_commands.json"
    ]
  }
}
```

### 3.2 调试连接

```bash
python check_vllm_config.py
```

输出应该是：

```
✓ vLLM服务可用
✓ API基址: http://localhost:8000
✓ 模型: qwen2.5-coder-32b
✓ 超时: 300秒
```

## 🎬 第4步：运行UT生成工作流

有两种方式运行：

### 4.1 交互式菜单（推荐新手）

```bash
cd /path/to/c-unit-test-workflow
python quickstart_llm.py
```

会出现菜单：

```
========== LLM UT Generator Quick Start ==========

[1] Check environment
[2] Analyze codebase
[3] Configure LLM settings
[4] Generate tests for all functions
[5] Generate tests for specific function
[6] View generated tests
[7] Run generated tests with GTest

Please select (1-7, 'q' to quit): _
```

#### 工作流步骤：

```
Step 1: 选项 [1] - 检查环境
   ✓ 验证Python版本
   ✓ 验证compile_commands.json
   ✓ 验证vLLM连接

Step 2: 选项 [2] - 分析代码库
   ✓ 解析所有.c和.h文件
   ✓ 提取函数定义
   ✓ 分析函数依赖
   ✓ 显示找到的函数列表

Step 3: 选项 [3] - 配置LLM
   ✓ 设置API地址
   ✓ 设置模型名称
   ✓ 设置timeout

Step 4: 选项 [4] 或 [5] - 生成测试
   选项[4]: 一次性生成所有函数的测试
   选项[5]: 选择性生成某个函数的测试
   
   等待LLM生成...
   └─ 输出会显示进度：
      Generated 2345 chars from qwen2.5-coder-32b

Step 5: 选项 [6] - 查看生成的测试
   ✓ 显示test/目录中的所有测试文件

Step 6: 选项 [7] - 运行测试
   ✓ 用GTest编译和运行生成的测试
```

### 4.2 命令行直接使用（自动化）

```bash
# 基本使用
python ut_workflow_llm.py \
  --project /path/to/your-project \
  --compile-commands /path/to/compile_commands.json

# 只生成特定源文件的测试
python ut_workflow_llm.py \
  --project /path/to/your-project \
  --compile-commands /path/to/compile_commands.json \
  --source src/module1.c

# 保存到特定目录
python ut_workflow_llm.py \
  --project /path/to/your-project \
  --compile-commands /path/to/compile_commands.json \
  --output ./my_tests
```

## 📊 第5步：检查生成的测试

生成完后，查看测试文件：

```bash
# 列出所有生成的测试
ls test/*_llm_test.cpp

# 查看某个测试
cat test/module1_llm_test.cpp
```

典型的生成测试看起来像：

```cpp
#include <gtest/gtest.h>
#include "../include/module1.h"

// 测试用例1：正常情况
TEST(Module1Test, ValidInputTest) {
    // Arrange
    int input = 42;
    
    // Act
    int result = my_function(input);
    
    // Assert
    EXPECT_EQ(result, expected_value);
}

// 测试用例2：边界条件
TEST(Module1Test, BoundaryTest) {
    EXPECT_EQ(my_function(NULL), -1);
    EXPECT_EQ(my_function(-1), error_code);
}

// ... 更多测试用例
```

## 🔄 完整工作流示例

假设你要为一个真实项目生成UT：

```bash
# 1️⃣ 进入这个工作流系统
cd /path/to/c-unit-test-workflow

# 2️⃣ 设置环境变量指向你的vLLM
export VLLM_API_BASE=http://localhost:8000

# 3️⃣ 运行快速启动菜单
python quickstart_llm.py

# 4️⃣ 选择 [1] 检查环境
# 4️⃣ 选择 [2] 分析代码库（指定你的项目）
# 4️⃣ 选择 [4] 生成所有函数的测试
# 4️⃣ 选择 [6] 查看生成的测试
# 4️⃣ 选择 [7] 编译并运行测试
```

## 🛠️ 调试和问题排查

### 问题1：找不到compile_commands.json

```bash
# 检查是否生成了
find . -name "compile_commands.json" -type f

# 确保CMakeLists.txt中有这一行
grep "CMAKE_EXPORT_COMPILE_COMMANDS" CMakeLists.txt

# 重新生成
rm -rf build && mkdir build && cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
```

### 问题2：vLLM连接失败

```bash
# 检查vLLM服务是否运行
curl http://localhost:8000/v1/models

# 如果失败，启动vLLM
python -m vllm.entrypoints.openai.api_server \
  --model qwen/Qwen2.5-Coder-32B \
  --port 8000
```

### 问题3：LLM生成的测试代码不完整

这可能是API问题。检查文件 `tools/llm_client.py` 第95行是否使用了正确的API：

```python
url = f"{self.api_base}/v1/chat/completions"  # ✓ 正确
# 不要使用: url = f"{self.api_base}/v1/completions"  # ✗ 错误
```

### 问题4：超时错误

```bash
# 增加timeout设置
export VLLM_TIMEOUT=600  # 增加到10分钟

# 或在config文件中修改
{
  "llm": {
    "timeout": 600
  }
}
```

## 📈 性能优化建议

### 1. 按模块生成测试

与其一次生成所有测试，不如按照功能模块分批生成：

```bash
# 只生成src/validator.c的测试
python ut_workflow_llm.py \
  --project . \
  --compile-commands build/compile_commands.json \
  --source src/validator.c

# 这样更快，也更容易管理
```

### 2. 调整LLM参数

编辑 `llm_workflow_config.json`：

```json
{
  "llm": {
    "temperature": 0.5,    // 降低以获得更稳定的输出
    "max_tokens": 2048,    // 减少token数可以加速（但可能影响完整性）
    "top_p": 0.9
  }
}
```

### 3. 使用更小的模型

如果速度是主要问题，可以试试：

```bash
export VLLM_MODEL=Qwen2.5-Coder-7B  # 快速但精度略低
# 或
export VLLM_MODEL=Qwen2.5-Coder-14B  # 平衡
```

## 📝 实用技巧

### 技巧1：生成特定函数的测试

```bash
python quickstart_llm.py
# 选择 [5]
# 输入函数名：validate_name
# 系统会只为这个函数生成测试
```

### 技巧2：重新生成（覆盖）

```bash
# 删除旧测试
rm test/*_llm_test.cpp

# 重新生成新的
python quickstart_llm.py
# 选择 [4]
```

### 技巧3：与手写测试混合

```
test/
├── validate_name_llm_test.cpp      # LLM生成
├── validate_student_llm_test.cpp   # LLM生成
└── custom_test.cpp                 # 手写
```

两种测试可以共存，用不同的命名规范区分。

### 技巧4：导出测试覆盖率报告

```bash
# 集成到CI/CD后，可以生成覆盖率报告
# 先配置CMake支持覆盖率...
```

## 🎓 学习路径

1. **了解你的代码结构**
   - 知道有哪些函数需要测试
   - 理解函数之间的依赖关系

2. **配置好vLLM服务**
   - 选择合适的模型
   - 调整参数以平衡速度和质量

3. **先从小项目开始**
   - 只有3-5个函数
   - 检查生成的测试质量
   - 迭代优化prompt

4. **逐步扩大规模**
   - 测试更大的项目
   - 调整LLM参数

5. **集成到CI/CD**
   - 自动生成新代码的测试
   - 维护测试覆盖率

## 📚 相关文件和命令

```bash
# 核心文件
tools/llm_client.py              # LLM客户端
tools/llm_test_generator.py       # 测试生成逻辑
tools/compile_commands_analyzer.py  # 编译信息分析
tools/ut_workflow_llm.py          # 完整工作流

# 运行脚本
quickstart_llm.py                 # 交互式菜单
check_vllm_config.py              # 配置检查

# 配置文件
llm_workflow_config.json          # 工作流配置
vllm_config.env                   # 环境变量示例
```

## ✅ 检查清单

在开始之前，确保：

- [ ] 项目有`CMakeLists.txt`且包含`CMAKE_EXPORT_COMPILE_COMMANDS`
- [ ] 项目结构包含`include/`和`src/`目录
- [ ] `compile_commands.json`已生成
- [ ] vLLM服务已启动并可访问
- [ ] Python和必要的库已安装
- [ ] `VLLM_API_BASE`环境变量已设置（或config文件已更新）

现在你已经准备好了！🚀

开始使用：

```bash
python quickstart_llm.py
```

有任何问题，检查对应章节的"调试和问题排查"部分。
