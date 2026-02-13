# C语言单元测试自动生成工作流

## 📋 项目概述  

这是一个完整的C语言单元测试自动生成工作流系统，基于以下技术栈：
- **测试框架**: Google Test (gtest)
- **编译系统**: CMake
- **代码分析**: Python脚本自动化
- **示例项目**: 学生管理系统

## 🎯 核心特性

### 1. 自动代码分析
```
✓ 扫描C/H源文件
✓ 提取函数签名、参数、返回类型
✓ 分析函数间依赖关系（调用关系）
✓ 识别需要Mock的外部函数
```

### 2. 智能Mock管理
```
✓ 自动检测所有外部函数调用
✓ Mock定义集中在文件头部（易于修改）
✓ 宏定义形式便于参数调整
✓ 清晰的Mock注释标记
```

### 3. 自动测试生成
```
✓ 三类标准测试用例：
  - 正常情况测试
  - 边界条件测试  
  - 错误处理测试
✓ AAA测试框架（Arrange-Act-Assert）
✓ 基于函数签名自动生成测试数据
✓ 基于返回类型自动生成断言
```

### 4. 自动化执行
```
✓ CMake一键编译
✓ 自动运行所有测试用例
✓ 测试结果解析和汇总
✓ 失败用例详情报告
```

## 📁 项目结构

```
c-unit-test-workflow/
├── include/              # 头文件
│   ├── database.h
│   ├── validator.h
│   └── student_manager.h
├── src/                  # 源文件
│   ├── database.c
│   ├── validator.c
│   └── student_manager.c
├── test/                 # 测试文件
│   ├── validator_test.cpp
│   ├── database_test.cpp
│   └── student_manager_test.cpp
├── tools/                # 工作流工具
│   ├── c_code_analyzer.py      # 代码分析器
│   ├── gtest_generator.py      # 测试生成器
│   ├── test_executor.py        # 测试执行器
│   └── ut_workflow.py          # 主工作流脚本
├── cmake/                # CMake辅助文件
├── build/                # 编译输出目录
├── CMakeLists.txt        # CMake配置
└── README.md
```

## 🚀 快速开始

### 前置要求
```bash
# Windows
- CMake >= 3.10
- Visual Studio 2019或更新版本
- Python 3.7+

# Linux/Mac
- CMake >= 3.10
- GCC/Clang
- Python 3.7+
```

### 步骤1: 分析项目代码

查看所有函数和依赖关系：
```bash
cd tools
python ut_workflow.py --project .. --analyze --list
```

输出示例：
```
[1/4] Analyzing C code structure...
  ✓ Found 8 functions
    - int32_t validate_student_name(...)
      Calls: strlen
    - int32_t db_init(...)
    - int32_t db_add_student(...)
      Calls: memset
```

### 步骤2: 生成测试代码

#### 生成所有测试：
```bash
python ut_workflow.py --project .. --generate
```

#### 生成特定函数的测试：
```bash
python ut_workflow.py --project .. --generate --target validate_score
```

输出示例：
```
[2/4] Generating test code...
  ✓ Generated: validate_student_name_test.cpp
  ✓ Generated: db_init_test.cpp
  ✓ Generated: update_student_score_test.cpp
```

### 步骤3: 编译测试

```bash
python test_executor.py --project .. --build
```

输出示例：
```
[3/4] Building tests with CMake...
  → Running cmake configuration...
  ✓ CMake configuration completed
  → Compiling...
  ✓ Build completed successfully
```

### 步骤4: 执行测试

```bash
python test_executor.py --project .. --run
```

### 集成执行（编译+运行）

```bash
python test_executor.py --project .. --build-and-run
```

#### 测试执行输出示例：
```
[4/4] Running tests...

  Running: validator_test

    Total: 8, Passed: 8, Failed: 0
    
  Running: database_test

    Total: 7, Passed: 7, Failed: 0

============================================================
TEST EXECUTION SUMMARY
============================================================

Total Tests: 15
Passed: 15 ✓
Failed: 0
Pass Rate: 100.0%

============================================================
```

## 🔍 工作流组件详解

### 1. 代码分析器 (c_code_analyzer.py)

**功能**: 解析C代码文件，提取函数信息和依赖关系

**核心方法**:
- `analyze_directory()`: 扫描整个include和src目录
- `get_function_dependencies()`: 获取特定函数的依赖信息
- `get_all_functions()`: 获取所有分析的函数

**输出数据结构**:
```python
@dataclass
class FunctionDependency:
    name: str                    # 函数名
    return_type: str            # 返回类型
    parameters: List[tuple]     # 参数列表
    external_calls: Set[str]    # 调用的其他函数
    source_file: str            # 源文件路径
    include_files: Set[str]     # 依赖的头文件
```

### 2. 测试生成器 (gtest_generator.py)

**功能**: 根据函数信息自动生成gtest测试代码

**关键特性**:
- 自动生成Mock宏定义（文件头部高亮显示）
- 生成Test Fixture类
- 生成三类标准测试用例
- 基于参数类型生成测试数据
- 基于返回类型生成断言

**生成的Mock宏示例**:
```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

// Mock definition for: db_add_student
// #define MOCK_DB_ADD_STUDENT_RETURN_VALUE  [default_value]

// Mock definition for: validate_score
// #define MOCK_VALIDATE_SCORE_RETURN_VALUE  [default_value]

/* ================================================= */
```

### 3. 测试执行器 (test_executor.py)

**功能**: 编译和执行生成的测试用例

**核心方法**:
- `build_tests()`: 使用CMake编译测试
- `run_tests()`: 运行所有测试用例
- `print_summary()`: 输出测试报告

**支持的平台**:
- Windows: Visual Studio generator
- Linux/Mac: Make generator

## 💡 Mock管理示例

### 场景1: 简单Mock（测试目标函数不调用其他函数）

```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

// No external function calls to mock

/* ================================================= */

TEST_F(ValidatorTest, TestCase1_NormalCase) {
    // Arrange
    const char* valid_name = "John Doe";
    
    // Act
    int32_t result = validate_student_name(valid_name);
    
    // Assert
    EXPECT_EQ(result, 0);
}
```

### 场景2: 复杂Mock（测试目标函数调用其他函数）

```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

// Mock definition for: validate_student_name
// #define MOCK_VALIDATE_STUDENT_NAME_RETURN_VALUE  0

// Mock definition for: validate_score  
// #define MOCK_VALIDATE_SCORE_RETURN_VALUE  0

// Mock definition for: db_add_student
// #define MOCK_DB_ADD_STUDENT_RETURN_VALUE  0

/* ================================================= */

// 使用Mock的测试用例
class AddStudentWithMockTest : public ::testing::Test {
    // 可以使用GoogleMock来拦截函数调用
    // MOCK_METHOD(int32_t, validate_student_name, (const char*));
};
```

## 📝 生成的测试代码示例

### validator_test.cpp 样例

```cpp
#include <gtest/gtest.h>
#include "validator.h"

class ValidatorTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// Test Case 1: Normal case
TEST_F(ValidatorTest, TestCase1_NormalCase) {
    // Arrange
    const char* valid_name = "John Doe";
    
    // Act
    int32_t result = validate_student_name(valid_name);
    
    // Assert
    EXPECT_EQ(result, 0);  // 期望成功返回0
}

// Test Case 2: Boundary case  
TEST_F(ValidatorTest, TestCase2_BoundaryCase) {
    // Arrange
    const char* boundary_name = "A";
    
    // Act
    int32_t result = validate_student_name(boundary_name);
    
    // Assert
    EXPECT_EQ(result, 0);
}

// Test Case 3: Error case
TEST_F(ValidatorTest, TestCase3_ErrorCase_EmptyString) {
    // Arrange
    const char* empty_name = "";
    
    // Act
    int32_t result = validate_student_name(empty_name);
    
    // Assert
    EXPECT_NE(result, 0);  // 期望返回错误
}
```

## 🎬 实际示例演示

### 示例项目: 学生管理系统

项目包含3个模块和8个公共函数：

1. **database.c** - 数据库操作
   - `db_init()` - 初始化数据库
   - `db_add_student()` - 添加学生
   - `db_get_student()` - 获取学生
   - `db_update_score()` - 更新分数
   - `db_delete_student()` - 删除学生

2. **validator.c** - 验证函数
   - `validate_student_name()` - 验证学生名字
   - `validate_score()` - 验证分数
   - `validate_student_id()` - 验证学生ID

3. **student_manager.c** - 业务逻辑
   - `add_student()` - 添加学生（含验证）
   - `update_student_score()` - 更新分数（含验证）
   - `get_average_score()` - 计算平均分
   - `get_total_students()` - 获取总人数

### 调用关系图

```
add_student()
├── validate_student_name()
├── validate_score()
└── db_add_student()

update_student_score()
├── validate_student_id()
├── validate_score()
└── db_update_score()

get_average_score()
├── get_total_students()
├── db_get_student()
└── (累加求和)
```

## 🛠️ 高级用法

### 修改Mock值

当生成的测试代码中包含Mock定义时，可以直接修改宏值：

```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */

// 修改前：
// #define MOCK_VALIDATE_SCORE_RETURN_VALUE  0

// 修改后（期望验证失败）：
#define MOCK_VALIDATE_SCORE_RETURN_VALUE  -1

/* ================================================= */
```

### 添加自定义测试用例

在生成的测试文件中添加新的测试用例：

```cpp
// 自定义测试用例：测试特定场景
TEST_F(ValidatorTest, TestCase_CustomScenario) {
    // 你的测试代码
}
```

### 调整测试数据

修改`_generate_arrange()`方法中的数据生成逻辑更新后，重新生成测试。

## 📊 测试覆盖率

生成的测试覆盖以下场景：

- ✓ **正常路径**: 测试函数在正常输入下的行为
- ✓ **边界条件**: 测试最小值、最大值、长度限制等
- ✓ **错误处理**: 测试NULL指针、无效数据等错误情况
- ✓ **依赖函数**: 通过Mock隔离测试，仅测试目标函数逻辑

## 🔧 故障排除

### 问题1: CMake找不到googletest

**解决方案**: 
```bash
# 确保网络连接正常，CMake会自动下载googletest
# 或手动指定
cmake .. -DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=<path-to-googletest>
```

### 问题2: 编译失败

**检查**:
- 确保C/C++编译器已安装
- 确保所有头文件路径正确
- 查看CMakeLists.txt中的include_directories设置

### 问题3: 测试不执行

**检查**:
- 确保测试可执行文件生成成功
- 检查测试输出是否有编译错误
- 验证gtest链接是否成功

## 📚 参考资源

- [Google Test官方文档](https://google.github.io/googletest/)
- [CMake官方指南](https://cmake.org/cmake/help/latest/)
- [C语言编码标准](https://en.wikipedia.org/wiki/C_standard)

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交Issue和Pull Request改进此工作流！

---

**最后更新**: 2026年2月13日
