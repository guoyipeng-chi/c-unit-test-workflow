# 🚀 START HERE - 从这里开始

## ✅ 项目已完成！

这是一个**完整的C语言单元测试自动化工作流系统**，包含：

✓ 代码分析引擎（自动识别函数依赖）  
✓ 测试代码生成器（自动生成GTest测试）  
✓ 编译管理系统（自动编译和链接）  
✓ 测试执行器（自动运行并报告结果）  
✓ 完整文档和示例代码  

---

## ⚡ 30秒快速开始

### Windows
```bash
python main.py --project . --full
```

### Linux/Mac
```bash
python3 main.py --project . --full
```

或直接运行快速启动脚本：
- Windows: `quickstart.bat`
- Linux/Mac: `bash quickstart.sh`

---

## 📚 根据需要选择

### 🎯 我是新手，想快速上手（5分钟）
1. 运行上面的命令
2. 查看 **QUICK_REFERENCE.txt**
3. 完成！

### 📖 我想详细了解（30分钟）
1. 查看 **GETTING_STARTED.md** - 快速指南
2. 查看 **README.md** - 完整文档
3. 查看生成的 `test/*_test.cpp` 文件

### 🔬 我想深入学习架构（1小时）
1. 查看 **ARCHITECTURE.md** - 架构设计
2. 研究 `tools/*.py` 源代码
3. 阅读代码注释

### 🗺️ 我需要导航帮助
查看 **INDEX.md** - 完整的文档导航地图

---

## 📁 项目结构一览

```
c-unit-test-workflow/
├── 📄 README.md              ← 完整使用文档
├── 📄 GETTING_STARTED.md     ← 快速开始指南
├── 📄 QUICK_REFERENCE.txt    ← 命令参考卡片
├── 📄 INDEX.md               ← 文档导航
├── 📄 ARCHITECTURE.md        ← 架构设计
│
├── 🔧 main.py                ← 主入口脚本
├── src/                       ← C源代码
├── include/                   ← C头文件
├── test/                      ← 生成的测试代码
├── tools/                     ← 工作流脚本
└── CMakeLists.txt            ← CMake配置
```

---

## 🎬 工作流演示

```
输入: C源代码 (src/ 和 include/)
   ↓
[自动分析] → 提取函数信息和依赖关系
   ↓
[自动生成] → 生成GTest测试代码 (test/)
   ↓
[自动编译] → 编译和链接 (build/)
   ↓
[自动执行] → 运行测试并报告结果
   ↓
输出: 测试报告 (✅ 通过 / ❌ 失败)
```

---

## 🎯 最常用的5个命令

| # | 命令 | 说明 |
|----|------|------|
| 1️⃣ | `python main.py --project . --full` | 完整工作流（推荐） |
| 2️⃣ | `python main.py --project . --analyze --list` | 分析代码并列表 |
| 3️⃣ | `python main.py --project . --generate` | 生成测试代码 |
| 4️⃣ | `python main.py --project . --build-and-run` | 编译并运行 |
| 5️⃣ | `python main.py --project . --info` | 显示详细信息 |

---

## 💡 关键特性

### 🔍 自动代码分析
自动识别你的C代码中的所有函数，分析它们的：
- 函数签名（返回类型、参数）
- 外部函数调用
- 依赖关系

### 🧪 智能测试生成
为每个函数自动生成三类测试用例：
- ✅ 正常情况测试
- ✅ 边界条件测试
- ✅ 错误处理测试

### 📌 Mock管理
所有Mock定义集中在文件头部，用清晰的分界线标记：
```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */
// 修改这里的Mock值
/* ================================================= */
```

### 🚀 一键运行
```bash
python main.py --project . --full
```
自动完成所有步骤（分析→生成→编译→执行）

---

## ✨ 什么是Mock？

Mock是一种测试技术，用来模拟函数的行为。比如：

```c
// 原始函数
int validate_score(float score) {
    if (score < 0 || score > 100) return -1;
    return 0;
}

// Mock的作用：在测试时，如果这个函数返回-1，
// 就能测试调用者如何处理错误
```

生成的测试代码会为你自动做这些！

---

## 📌 下一步

### 选项1: 立即使用（推荐新手）
```bash
python main.py --project . --full
```
然后查看 `test/` 目录下生成的 `*_test.cpp` 文件

### 选项2: 分步了解
1. 运行分析: `python main.py --project . --analyze --list`
2. 查看结果，然后生成: `python main.py --project . --generate`
3. 编译运行: `python main.py --project . --build-and-run`

### 选项3: 替换成自己的代码
1. 把你的C源文件复制到 `src/` 目录
2. 把你的头文件复制到 `include/` 目录
3. 运行: `python main.py --project . --full`

---

## ❓ 常见问题

**Q: 我需要安装什么?**
A: Python 3.7+, CMake 3.10+, C编译器
   详见 README.md

**Q: 生成的测试代码在哪里?**
A: `test/` 目录下，文件名为 `*_test.cpp`

**Q: 如何修改Mock值?**
A: 编辑 `test/*_test.cpp` 的最开始部分

**Q: 我想使用自己的C代码怎么办?**
A: 替换 `src/` 和 `include/` 下的文件，然后运行工作流

**Q: 生成的代码有什么问题吗?**
A: 可能没有，但你可以修改Mock值和添加自定义测试用例

---

## 📞 获取帮助

### 阅读文档
按优先级：
1. **QUICK_REFERENCE.txt** - 1分钟速查
2. **GETTING_STARTED.md** - 10分钟快速指南
3. **README.md** - 30分钟完整文档
4. **ARCHITECTURE.md** - 深入学习

### 运行命令获取帮助
```bash
python main.py --help              # 显示所有命令
python main.py --project . --info  # 显示工作流信息
```

### 查看示例代码
```bash
cat test/validator_test.cpp        # 查看生成的测试代码
```

---

## 🎓 学习路线图

```
START HERE (你在这里)
    ↓
[运行命令] → python main.py --project . --full
    ↓
[查看结果] → cat test/*_test.cpp
    ↓
[了解更多] → 阅读 README.md
    ↓
[深入学习] → 阅读 ARCHITECTURE.md
    ↓
[扩展功能] → 修改 tools/*.py
```

---

## ✅ 系统检查（运行前请确认）

```bash
# 检查Python版本
python --version                    # 应该是 3.7+

# 检查CMake
cmake --version                     # 应该是 3.10+

# 检查编译器
gcc --version                       # 或 clang --version
```

---

## 🏁 现在就开始吧！

```bash
# Windows 用户
python main.py --project . --full

# Linux/Mac 用户
python3 main.py --project . --full

# 或者使用快速启动脚本
# Windows: quickstart.bat
# Linux/Mac: bash quickstart.sh
```

**预期输出**:
- 代码分析完成 ✓
- 测试代码生成 ✓
- 编译成功 ✓
- 测试通过 ✓

---

## 📖 命令参考速查

| 目标 | 命令 |
|------|------|
| 完整工作流 | `python main.py --project . --full` |
| 分析代码 | `python main.py --project . --analyze --list` |
| 生成测试 | `python main.py --project . --generate` |
| 编译+运行 | `python main.py --project . --build-and-run` |
| 查看帮助 | `python main.py --help` |
| 验证项目 | `python verify_structure.py` |

---

## 🎉 完成！

现在你已经拥有：
- ✅ 完整的C测试工作流系统
- ✅ 自动代码分析工具
- ✅ 自动测试生成器
- ✅ 完整的文档和示例

**立即使用这个系统为你的C代码自动生成单元测试！**

---

**更多信息**: 
- 查看 **INDEX.md** 获得完整的文档导航
- 查看 **README.md** 获得详细的使用说明
- 查看 **ARCHITECTURE.md** 理解系统设计

**现在开始**: `python main.py --project . --full` 🚀
