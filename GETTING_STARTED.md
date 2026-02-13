# C语言单元测试工作流 - 快速参考指南

## ⚡ 30秒快速开始

### Windows
```bash
cd c-unit-test-workflow
python main.py --project . --full
```

### Linux/Mac
```bash
cd c-unit-test-workflow
bash quickstart.sh
```

或直接用Python:
```bash
python3 main.py --project . --full
```

---

## 📚 关键命令速查表

### 工作流相关

| 命令 | 说明 |
|------|------|
| `python main.py --project . --full` | 完整流程 (分析→生成→编译→测试) |
| `python main.py --project . --info` | 显示系统信息 |
| `python main.py --project . --help` | 显示所有命令 |

### 步骤化操作

| 步骤 | 命令 |
|------|------|
| 1️⃣ 分析代码 | `python main.py --project . --analyze --list` |
| 2️⃣ 生成测试 | `python main.py --project . --generate` |
| 3️⃣ 编译代码 | `python main.py --project . --build` |
| 4️⃣ 运行测试 | `python main.py --project . --run` |

### 高级操作

| 操作 | 命令 |
|------|------|
| 生成特定函数的测试 | `python main.py --project . --generate --target validate_score` |
| 只编译不运行 | `python main.py --project . --build` |
| 编译并运行 | `python main.py --project . --build-and-run` |

---

## 📁 项目文件导览

### 核心目录

```
src/               → C源代码 (.c文件)
include/           → 头文件 (.h文件)
test/              → 生成的测试代码 (.cpp文件)
tools/             → 工作流脚本 (Python脚本)
```

### 关键脚本

```
main.py            → 主集成脚本 (入口)
quickstart.py      → Python快速开始
quickstart.sh      → Linux/Mac快速开始
quickstart.bat     → Windows快速开始
```

### 配置文件

```
CMakeLists.txt     → CMake编译配置
workflow.conf      → 工作流配置
requirements.txt   → Python依赖
```

### 文档

```
README.md          → 完整使用文档
ARCHITECTURE.md    → 架构设计文档
GETTING_STARTED.md → 本文件 (快速参考)
```

---

## 🔍 生成的测试代码位置

分析完成后，会在 `test/` 目录生成测试文件：

```
test/
├── database_test.cpp           # 数据库函数测试
├── validator_test.cpp          # 验证函数测试
└── student_manager_test.cpp    # 学生管理函数测试
```

### 每个测试文件包含

```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */
// 修改这里的Mock值
/* ================================================= */

class XxxxTest : public ::testing::Test { ... }

TEST_F(XxxxTest, TestCase1_Normal) { ... }
TEST_F(XxxxTest, TestCase2_Boundary) { ... }
TEST_F(XxxxTest, TestCase3_Error) { ... }
```

---

## 🛠️ 常见操作流程

### 流程1: 新项目从头开始

```bash
# 1. 创建项目副本
cp -r example-project my-project
cd my-project

# 2. 替换你自己的C代码
# - 修改 src/*.c
# - 修改 include/*.h

# 3. 运行工作流
python main.py --project . --full
```

### 流程2: 修改Mock并重新测试

```bash
# 1. 修改生成的测试文件中的Mock值
vim test/my_function_test.cpp

# 2. 重新编译和测试
python main.py --project . --build-and-run
```

### 流程3: 只分析不生成

```bash
# 查看项目中分析出来的所有函数
python main.py --project . --analyze --list
```

### 流程4: 查看同一个函数的Mock和调用

```bash
# 分析显示函数调用关系
python main.py --project . --analyze --list

# 输出示例:
# Function: add_student
#   External Calls (需要Mock):
#     - validate_student_name()
#     - validate_score()
#     - db_add_student()
```

---

## 📊 测试执行示例

```
$ python main.py --project . --full

======================================================================
  C Language Unit Test Generation Workflow - Full Pipeline
======================================================================

[Step 1/4] Code Analysis
----------------------------------------------------------------------
[1/4] Analyzing C code structure...
  ✓ Found 8 functions
    - int32_t validate_student_name(...)
    - float validate_score(...)
    ...

[Step 2/4] Test Code Generation
----------------------------------------------------------------------
[2/4] Generating test code...
  ✓ Generated: database_test.cpp
  ✓ Generated: validator_test.cpp
  ✓ Generated: student_manager_test.cpp

[Step 3/4] Building Tests
----------------------------------------------------------------------
[3/4] Building tests with CMake...
  → Running cmake configuration...
  ✓ CMake configuration completed
  → Compiling...
  ✓ Build completed successfully

[Step 4/4] Running Tests
----------------------------------------------------------------------
[4/4] Running tests...

  Running: database_test
    Total: 7, Passed: 7, Failed: 0 ✓

  Running: validator_test
    Total: 15, Passed: 15, Failed: 0 ✓

  Running: student_manager_test
    Total: 8, Passed: 8, Failed: 0 ✓

======================================================================
TEST EXECUTION SUMMARY
======================================================================

Total Tests: 30
Passed: 30 ✓
Failed: 0
Pass Rate: 100.0%

======================================================================
```

---

## ❓ 常见问题

### Q: 如何查看生成的测试代码?
```bash
cat test/validator_test.cpp
```

### Q: 如何修改Mock值?
编辑测试文件中的:
```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */
#define MOCK_VALIDATE_SCORE_RETURN_VALUE  0
/* ================================================= */
```

### Q: 如何添加自定义测试用例?
在生成的测试文件中添加:
```cpp
TEST_F(MyFunctionTest, CustomTestCase) {
    // 你的测试代码
}
```

### Q: 如何只测试一个函数?
```bash
python main.py --project . --generate --target validate_score
```

### Q: 如何查看所有支持的函数?
```bash
python main.py --project . --analyze --list
```

### Q: 编译失败怎么办?
检查:
1. CMake是否已安装 (`cmake --version`)
2. C/C++编译器是否已安装 (`gcc --version` 或 `cl.exe /?`)
3. Python版本是否>=3.7 (`python --version`)
4. 查看build/目录下的编译日志

### Q: 测试失败怎么办?
1. 查看测试错误信息
2. 检查Mock值是否正确
3. 检查测试数据是否符合实际
4. 修改测试代码，重新编译运行

---

## 🎓 学习路径

### 初级: 了解工作流
1. 阅读本文件 ✓ (你在这里)
2. 运行 `python main.py --project . --info`
3. 查看 `test/*_test.cpp` 中的生成代码

### 中级: 自定义测试
1. 修改Mock定义值
2. 添加自定义测试用例
3. 修改测试数据
4. 重新编译和运行

### 高级: 扩展工作流
1. 研究 `tools/c_code_analyzer.py`
2. 研究 `tools/gtest_generator.py`
3. 修改代码生成逻辑
4. 支持新的函数签名模式

### 深入: 架构和原理
1. 阅读 `ARCHITECTURE.md`
2. 研究每个Python模块
3. 理解数据流和依赖关系
4. 扩展新功能

---

## 🚀 性能提示

| 操作 | 时间 |
|------|------|
| 代码分析 | < 100ms |
| 生成测试 | < 500ms |
| 编译 | 5-60秒 |
| 执行测试 | < 10秒 |

**优化建议**:
- 首次运行会下载GTest，请确保网络连接
- 编译时间与源代码量成正比
- 使用 `--analyze` 快速预览函数

---

## 📞 获取帮助

### 查看所有命令
```bash
python main.py --help
```

### 查看工作流信息
```bash
python main.py --project . --info
```

### 查看详细文档
- README.md - 完整使用文档
- ARCHITECTURE.md - 架构设计
- 代码注释 - 各个Python脚本中

---

## ✅ 检查清单

在使用工作流前，请确认:

- [ ] Python 3.7+ 已安装
- [ ] CMake 3.10+ 已安装
- [ ] C/C++ 编译器已安装 (GCC/Clang/MSVC)
- [ ] 网络连接正常 (首次下载GTest)
- [ ] 项目目录结构正确 (include/, src/, test/)

---

## 🎯 下一步

1. **首次使用**:
   ```bash
   python main.py --project . --full
   ```

2. **查看结果**:
   ```bash
   cat test/validator_test.cpp
   ```

3. **修改和重新运行**:
   编辑测试文件后，执行:
   ```bash
   python main.py --project . --build-and-run
   ```

4. **深入学习**:
   阅读 README.md 和 ARCHITECTURE.md

---

**祝你使用愉快！** 🎉

如有问题，请参考完整文档或查看代码注释。
