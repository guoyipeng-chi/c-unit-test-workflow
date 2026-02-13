# 📖 文档和资源导航

## 🚀 我想要...

### 快速开始（5分钟内）
→ 查看 **QUICK_REFERENCE.txt**
- 最常用的5个命令
- 快速启动脚本
- 故障排除

### 一步步学习（30分钟）
→ 查看 **GETTING_STARTED.md**
- 30秒快速开始
- 详细的命令说明
- 常见问题答案
- 学习路径

### 完整了解工作流（1小时）
→ 查看 **README.md**
- 项目概述
- 前置要求
- 6步详细使用流程
- 生成的测试代码解析
- 实际示例展示
- 高级用法

### 深入理解架构（2小时）
→ 查看 **ARCHITECTURE.md**
- 系统架构总览
- 每个步骤的工作原理
- 数据流转
- 关键类和方法
- 扩展点说明

### 概览项目（10分钟）
→ 查看 **PROJECT_SUMMARY.md**
- 完成状态总结
- 代码行数统计
- 功能模块清单
- 项目成就

---

## 📚 按用途分类

### 我是新手
1. 运行快速启动脚本：`quickstart.bat` 或 `bash quickstart.sh`
2. 查看 **QUICK_REFERENCE.txt** （1分钟）
3. 查看 **GETTING_STARTED.md** （10分钟）

### 我想使用这个工作流
1. 查看 **README.md** 的"前置要求"
2. 运行 `python main.py --project . --full` 
3. 参考 **GETTING_STARTED.md** 中的命令

### 我想修改生成的测试代码
1. 查看生成的 `test/*_test.cpp` 文件
2. 修改 Mock 定义部分
3. 添加自定义测试用例
4. 重新运行 `python main.py --project . --build-and-run`

### 我想扩展工作流功能
1. 查看 **ARCHITECTURE.md** 中的"扩展点"
2. 学习关键Python模块的代码
3. 修改相应的生成器或分析器
4. 测试修改结果

### 我遇到了问题
1. 查看 **QUICK_REFERENCE.txt** 中的"故障排除"
2. 查看 **GETTING_STARTED.md** 中的"常见问题"
3. 查看 **README.md** 中的"故障排除"
4. 检查代码注释

---

## 📂 文件导航

### 📋 文档文件（必读）

| 文件 | 优先级 | 内容 |
|------|--------|------|
| QUICK_REFERENCE.txt | ⭐⭐⭐ | 快速命令参考（最常用） |
| GETTING_STARTED.md | ⭐⭐⭐ | 新手快速指南 |
| README.md | ⭐⭐ | 完整使用文档 |
| ARCHITECTURE.md | ⭐⭐ | 架构和扩展 |
| PROJECT_SUMMARY.md | ⭐ | 项目完成总结 |

### 🔧 工作流脚本

| 文件 | 用途 | 修改 |
|------|------|------|
| main.py | 主入口，统一接口 | ❌ 不修改 |
| quickstart.py | Python快速启动 | ❌ 不修改 |
| quickstart.sh | Linux/Mac快速启动 | ❌ 不修改 |
| quickstart.bat | Windows快速启动 | ❌ 不修改 |
| verify_structure.py | 项目结构验证 | ❌ 不修改 |

### 🎯 工具模块（tools/）

| 文件 | 功能 | 修改 |
|------|------|------|
| c_code_analyzer.py | C代码分析引擎 | ⚠️ 高级扩展 |
| gtest_generator.py | 测试代码生成器 | ⚠️ 可定制 |
| test_executor.py | 编译和执行管理 | ⚠️ 高级扩展 |
| ut_workflow.py | 工作流控制 | ❌ 不修改 |

### 📝 源代码（src/）

| 文件 | 说明 | 修改 |
|------|------|------|
| database.c | 示例：数据库模块 | ✅ 替换为你的代码 |
| validator.c | 示例：验证模块 | ✅ 替换为你的代码 |
| student_manager.c | 示例：业务逻辑 | ✅ 替换为你的代码 |

### 📌 头文件（include/）

| 文件 | 说明 | 修改 |
|------|------|------|
| database.h | 示例头文件 | ✅ 替换为你的代码 |
| validator.h | 示例头文件 | ✅ 替换为你的代码 |
| student_manager.h | 示例头文件 | ✅ 替换为你的代码 |

### 🧪 测试文件（test/）

| 文件 | 说明 | 修改 |
|------|------|------|
| validator_test.cpp | 生成的测试 | ✅ 修改Mock，添加用例 |
| database_test.cpp | 生成的测试 | ✅ 修改Mock，添加用例 |
| student_manager_test.cpp | 生成的测试 | ✅ 修改Mock，添加用例 |

### ⚙️ 配置文件

| 文件 | 用途 |
|------|------|
| CMakeLists.txt | CMake编译配置 |
| workflow.conf | 工作流配置 |
| requirements.txt | Python依赖 |

---

## 🗺️ 快速导航地图

```
START
  ↓
[选择你的情况]
  ├─ 我是新手
  │  └→ QUICK_REFERENCE.txt (1分钟)
  │     └→ GETTING_STARTED.md (10分钟)
  │
  ├─ 我想快速开始
  │  └→ 运行: python main.py --project . --full
  │
  ├─ 我想了解更多
  │  └→ README.md (30分钟)
  │
  ├─ 我想修改测试代码
  │  └→ 编辑 test/*_test.cpp
  │     └→ 重新运行工作流
  │
  ├─ 我想扩展工作流
  │  └→ ARCHITECTURE.md
  │     └→ 研究 tools/*.py
  │
  └─ 我遇到问题
     └→ 查看相应文档的"故障排除"
        └→ 检查代码注释
```

---

## 📖 按阅读时间排序

### ⚡ 1分钟快速看
→ QUICK_REFERENCE.txt
- 最常用命令
- 快速启动

### ⏱️ 5-10分钟速跑
→ GETTING_STARTED.md
- 快速开始指南
- 常见操作

### 📚 20-30分钟学习
→ README.md
- 完整使用说明
- 实际示例
- 高级用法

### 🔬 1小时深度学习
→ ARCHITECTURE.md
- 架构设计
- 实现原理
- 扩展方法

### 📊 10分钟总览
→ PROJECT_SUMMARY.md
- 完成成果
- 功能清单
- 项目统计

---

## 🎯 按学习目标分类

### 目标1: 立即使用（完全新手）
```
QUICK_REFERENCE.txt
  ↓ (运行命令)
python main.py --project . --full
  ↓ (查看结果)
test/*_test.cpp
```
**时间**: 5分钟

### 目标2: 理解工作原理（想要学习）
```
README.md (概览)
  ↓
GETTING_STARTED.md (详细步骤)
  ↓
ARCHITECTURE.md (原理)
```
**时间**: 1小时

### 目标3: 自定义配置（想要修改）
```
GETTING_STARTED.md (查看在哪修改)
  ↓
编辑 test/*_test.cpp
  ↓
重新运行工作流
```
**时间**: 10分钟

### 目标4: 扩展功能（想要增强）
```
ARCHITECTURE.md (扩展点)
  ↓
tools/*.py (源代码)
  ↓
代码注释 (实现细节)
```
**时间**: 2-4小时

---

## 💬 常见问题

### Q: 我应该从哪个文件开始?
A: 根据你的情况：
- 新手 → QUICK_REFERENCE.txt
- 想用 → GETTING_STARTED.md
- 想学 → README.md → ARCHITECTURE.md

### Q: 哪些文件我不应该修改?
A: ❌ 不要修改:
- main.py
- tools/*.py
- CMakeLists.txt
- 工作流脚本

✅ 可以修改:
- src/*.c
- include/*.h
- test/*_test.cpp (特别是Mock部分)

### Q: 我应该在哪里添加自定义测试?
A: 在生成的 test/*_test.cpp 文件中，在 GTest 宏之后添加你的自定义测试用例。

### Q: 生成的测试代码在哪里?
A: 在 test/ 目录下，文件名为 *_test.cpp

### Q: 如何修改Mock值?
A: 编辑 test/*_test.cpp 的最开始部分：
```cpp
/* ========== MOCK DEFINITIONS - MODIFY HERE ========== */
```

### Q: 我想使用自己的C代码怎么办?
A: 替换 src/ 和 include/ 目录下的文件，然后运行工作流。

---

## 🔍 快速搜索

### 我想...

| 操作 | 查看 |
|------|------|
| 快速开始 | QUICK_REFERENCE.txt |
| 了解步骤 | GETTING_STARTED.md |
| 完整文档 | README.md |
| 原理设计 | ARCHITECTURE.md |
| 命令参考 | QUICK_REFERENCE.txt |
| 常见问题 | GETTING_STARTED.md |
| 故障排除 | README.md + GETTING_STARTED.md |
| 扩展功能 | ARCHITECTURE.md |
| 查看示例 | test/*_test.cpp |
| 项目统计 | PROJECT_SUMMARY.md |

---

## 📞 获取帮助

### 方式1: 查看文档
- 根据需要选择相应文档
- 每个文档都有详细说明

### 方式2: 查看代码注释
- tools/*.py 中有详细的代码注释
- 了解实现细节

### 方式3: 运行帮助命令
```bash
python main.py --help          # 显示命令帮助
python main.py --project . --info  # 显示工作流信息
python verify_structure.py     # 验证项目结构
```

---

**最后更新**: 2026年2月13日
**版本**: 1.0.0
**状态**: ✅ 完成
