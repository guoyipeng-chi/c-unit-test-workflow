# ⚡ 快速5分钟上手指南

针对真实项目生成UT的最快方式。

## 🎯 三个核心步骤

### 步骤1️⃣：检查项目结构

你的项目必须有这样的结构：

```
your-project/
├── CMakeLists.txt         ← 必需 (确保含有: set(CMAKE_EXPORT_COMPILE_COMMANDS ON))
├── include/               ← 必需 (头文件) 
├── src/                   ← 必需 (源文件)
└── test/                  ← 可选 (会自动创建)
```

**检查CMakeLists.txt：**
```bash
grep CMAKE_EXPORT_COMPILE_COMMANDS your-project/CMakeLists.txt
```

如果没有输出，添加这一行到CMakeLists.txt：
```cmake
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

### 步骤2️⃣：生成 compile_commands.json

这个文件告诉LLM如何编译你的代码。

```bash
cd your-project
mkdir -p build && cd build

# 生成编译数据库
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# Windows用户 (MSVC):
cmake -G "Visual Studio 17 2022" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# 检查是否成功
ls compile_commands.json    # 应该存在
```

**结果:** `build/compile_commands.json` 已生成

### 步骤3️⃣：运行UT生成工具

```bash
# 进入工作流目录
cd /path/to/c-unit-test-workflow

# 运行生成工具（指向你的项目）
python generate_ut_for_repo.py /path/to/your-project

# 或者当前目录
python generate_ut_for_repo.py .
```

**交互式菜单会出现：**

```
[1] 生成所有函数的UT
[2] 为特定函数生成UT  
[3] 分析函数依赖关系
[4] 预览LLM Prompt
```

选择 `1` 一次生成所有，或 `2` 选择特定函数。

**输出:** 测试文件保存到 `your-project/test/*_llm_test.cpp`

---

## 🚀 完整命令（复制即用）

### Linux/macOS:

```bash
# 1. 配置vLLM地址
export VLLM_API_BASE=http://localhost:8000

# 2. 生成编译数据库
cd ~/my-project
mkdir -p build && cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# 3. 运行UT生成器
cd /path/to/c-unit-test-workflow
python generate_ut_for_repo.py ~/my-project
```

### Windows (PowerShell):

```powershell
# 1. 配置vLLM地址
$env:VLLM_API_BASE = "http://localhost:8000"

# 2. 生成编译数据库
cd C:\Users\YourName\my-project
mkdir build -Force | cd
cmake -G "Visual Studio 17 2022" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# 3. 运行UT生成器
cd C:\path\to\c-unit-test-workflow
python generate_ut_for_repo.py C:\Users\YourName\my-project
```

---

## 📋 前置检查清单

运行前确保：

- [ ] **vLLM已启动** - 测试连接:
  ```bash
  curl http://localhost:8000/v1/models
  ```
  如果失败，启动vLLM:
  ```bash
  python -m vllm.entrypoints.openai.api_server \
    --model qwen/Qwen2.5-Coder-32B --port 8000
  ```

- [ ] **CMake已安装** - 测试:
  ```bash
  cmake --version
  ```

- [ ] **Python 3.8+** - 测试:
  ```bash
  python --version
  ```

- [ ] **项目有CMakeLists.txt** - 检查:
  ```bash
  ls your-project/CMakeLists.txt
  ```

---

## 🎬 示例：为一个实际项目生成UT

假设你有这样的项目结构：

```
~/workspace/student-mgmt/
├── CMakeLists.txt
├── include/
│   ├── student.h
│   └── database.h
├── src/
│   ├── student.c
│   └── database.c
└── test/
```

**完整命令：**

```bash
# 1️⃣ 进入项目目录
cd ~/workspace/student-mgmt

# 2️⃣ 生成编译数据库
mkdir -p build && cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..

# 3️⃣ 运行UT生成器
cd /path/to/c-unit-test-workflow
python generate_ut_for_repo.py ~/workspace/student-mgmt
```

**输出示例：**

```
===============================
【UT生成工具】
===============================

✓ 项目结构验证完成
✓ compile_commands.json 已生成
✓ 找到 8 个函数：
   1. init_db
   2. add_student
   3. validate_name
   4. validate_age
   5. update_student
   6. delete_student
   7. query_student
   8. close_db

【选择一个选项】
[1] 生成所有函数的UT
[2] 为特定函数生成UT
[q] 退出

请选择 (1-2, q退出): 1
```

**选择1后，系统会：**
1. ✅ 分析每个函数
2. ✅ 读取函数源代码
3. ✅ 读取相关头文件
4. ✅ 调用LLM生成测试
5. ✅ 保存到 `test/` 目录

**最终结果：**

```
✓ 生成成功!

生成的测试文件已保存到: ~/workspace/student-mgmt/test

找到 8 个测试文件：
  - init_db_llm_test.cpp
  - add_student_llm_test.cpp
  - validate_name_llm_test.cpp
  - validate_age_llm_test.cpp
  - update_student_llm_test.cpp
  - delete_student_llm_test.cpp
  - query_student_llm_test.cpp
  - close_db_llm_test.cpp
```

现在你可以：

```bash
# 查看生成的测试代码
cat ~/workspace/student-mgmt/test/validate_name_llm_test.cpp

# 编译测试（需要GTest）
cd ~/workspace/student-mgmt/build
cmake ..
make

# 运行测试
./bin/validate_name_llm_test
```

---

## 🔧 常见问题

### Q1: "CMake not found"
```bash
# 安装CMake
# Windows: choco install cmake
# macOS: brew install cmake
# Linux: sudo apt install cmake
```

### Q2: "vLLM连接失败"
```bash
# 启动vLLM服务
python -m vllm.entrypoints.openai.api_server \
  --model qwen/Qwen2.5-Coder-32B --port 8000
```

### Q3: "compile_commands.json not found"
```bash
# 确保CMakeLists.txt中有这一行
grep "CMAKE_EXPORT_COMPILE_COMMANDS ON" CMakeLists.txt

# 如果没有，添加它，然后重新运行cmake
```

### Q4: 生成太慢
```bash
# 只为一个函数生成
python generate_ut_for_repo.py your-project
# 选择 [2]，输入函数名

# 或使用更快的模型
export VLLM_MODEL=Qwen2.5-Coder-14B
```

### Q5: 生成的测试代码质量不好
1. 检查是否用了正确的API endpoint:
   ```bash
   grep "chat/completions" tools/llm_client.py
   ```

2. 调整LLM参数（编辑 `llm_workflow_config.json`）:
   ```json
   {
     "llm": {
       "temperature": 0.5,    // 降低随机性
       "max_tokens": 2048     // 足够长
     }
   }
   ```

---

## ⏱️ 预计时间

| 任务 | 时间 |
|------|------|
| 首次设置（CMake + compile_commands.json） | 5-10分钟 |
| 为3个函数生成UT | 2-3分钟 |
| 为10个函数生成UT | 5-10分钟 |
| 为50个函数生成UT | 30-60分钟 |

---

## 📚 了解更多

- **详细指南**: [HOW_TO_GENERATE_UT_FOR_REAL_REPO.md](HOW_TO_GENERATE_UT_FOR_REAL_REPO.md)
- **工作流原理**: [SYSTEM_SUMMARY_LLM.md](SYSTEM_SUMMARY_LLM.md)
- **API文档**: [LLM_WORKFLOW_GUIDE.md](LLM_WORKFLOW_GUIDE.md)

---

## ✨ 下一步

现在你已经知道如何使用这个系统了！

1. **选择一个真实项目** - 准备好的项目
2. **运行 `python generate_ut_for_repo.py your-project`** - 一键生成
3. **检查生成的测试** - 查看 `test/` 目录
4. **编译并运行** - 验证测试质量
5. **迭代改进** - 调整参数获得更好的结果

祝你使用愉快！🚀
