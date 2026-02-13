# LLM UT Generation - 文档索引与导航

## 📍 你在这里

这是一个完整且功能丰富的 **AI驱动C单元测试生成系统**。

---

## 🗺️ 快速导航

### 🚀 想立即开始？

```bash
python quickstart_llm.py --interactive
```
→ 查看 [QUICKREF_LLM.md](QUICKREF_LLM.md) (5分钟快速指南)

---

### 📚 想了解详细信息？

选择你感兴趣的主题：

| 主题 | 文档 | 描述 |
|------|------|------|
| **系统架构** | [SYSTEM_SUMMARY_LLM.md](SYSTEM_SUMMARY_LLM.md) | 完整系统设计和组件说明 |
| **快速开始** | [QUICKREF_LLM.md](QUICKREF_LLM.md) | 5分钟快速入门指南 |
| **详细文档** | [LLM_WORKFLOW_GUIDE.md](LLM_WORKFLOW_GUIDE.md) | 完整技术文档（32KB） |
| **项目README** | [README.md](README.md) | 原始项目说明 |
| **配置** | [llm_workflow_config.json](llm_workflow_config.json) | 工作流配置文件 |

---

## 🎯 按使用场景选择

### 场景1: "我是第一次使用"
```
✓ 阅读: QUICKREF_LLM.md
✓ 视频: 看系统架构图 (SYSTEM_SUMMARY_LLM.md)
✓ 行动: 运行 quickstart_llm.py --interactive
```

### 场景2: "我想自定义配置"
```
✓ 阅读: LLM_WORKFLOW_GUIDE.md → 配置部分
✓ 修改: llm_workflow_config.json
✓ 参考: SYSTEM_SUMMARY_LLM.md → 核心模块说明
```

### 场景3: "我想集成到CI/CD"
```
✓ 阅读: LLM_WORKFLOW_GUIDE.md → CI/CD集成部分
✓ 查看: GitHub Actions示例
✓ 自定义: ut_workflow_llm.py 命令行参数
```

### 场景4: "我想理解代码实现"
```
✓ 学习: SYSTEM_SUMMARY_LLM.md → 核心模块详解
✓ 查看: tools/llm_client.py (150行)
✓ 查看: tools/compile_commands_analyzer.py (270行)
✓ 查看: tools/llm_test_generator.py (320行)
✓ 查看: tools/ut_workflow_llm.py (380行)
```

### 场景5: "我遇到问题"
```
✓ 查看: QUICKREF_LLM.md → 故障排查部分
✓ 查看: LLM_WORKFLOW_GUIDE.md → 故障排除指南
✓ 运行: python quickstart_llm.py --check
```

---

## 📁 文件结构

```
c-unit-test-workflow/
│
├── 📄 README.md                    ← 原始项目说明
├── 📄 QUICKREF_LLM.md             ← ⭐ 快速参考 (5分钟)
├── 📄 SYSTEM_SUMMARY_LLM.md       ← 完整系统总结
├── 📄 LLM_WORKFLOW_GUIDE.md       ← 详细技术文档 (32KB)
├── 📄 LLM_WORKFLOW_INDEX.md       ← 本文件 (导航)
│
├── 🐍 quickstart_llm.py           ← 交互式启动脚本
├── ⚙️ llm_workflow_config.json    ← 配置文件
│
├── tools/
│   ├── 🔗 llm_client.py                    ← vLLM客户端 (150行)
│   ├── 📊 compile_commands_analyzer.py    ← 编译信息解析 (270行)
│   ├── 🧪 llm_test_generator.py           ← LLM测试生成 (320行)
│   ├── ⚡ ut_workflow_llm.py              ← 主工作流 (380行)
│   ├── 📝 ut_workflow.py                  ← 原始工作流 (参考)
│   ├── 📊 c_code_analyzer.py              ← 代码分析器 (参考)
│   └── 🧬 gtest_generator.py              ← 模板生成器 (参考)
│
├── build-ninja-msvc/
│   └── compile_commands.json      ← 编译命令数据库 ✓ 已生成
│
└── test/
    └── *_llm_test.cpp             ← 生成的测试文件 (输出)
```

---

## 🔄 工作流流程图

```
START
  │
  ├─→ [1] 检查环境 (quickstart_llm.py --check)
  │     ├─ Python 3.8+
  │     ├─ vLLM服务
  │     └─ compile_commands.json
  │
  ├─→ [2] 生成编译信息 (quickstart_llm.py --generate-compile-commands)
  │     └─ cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
  │
  ├─→ [3] 分析代码 (ut_workflow_llm.py --analyze-only)
  │     ├─ c_code_analyzer.py
  │     └─ 提取函数和依赖
  │
  ├─→ [4] 提取编译信息 (compile_commands_analyzer.py)
  │     ├─ Include路径
  │     ├─ 宏定义
  │     └─ 编译标志
  │
  ├─→ [5] 生成测试 (ut_workflow_llm.py)
  │     ├─ 构造提示词 (PromptBuilder)
  │     ├─ 调用vLLM (LLMClient)
  │     └─ 保存测试 (llm_test_generator.py)
  │
  └─→ [6] 验证和使用
        ├─ 编译测试: cmake --build . --target database_test
        └─ 运行测试: ./database_test_llm_test.exe
END
```

---

## 💾 主要文件说明

### 📄 QUICKREF_LLM.md ⭐ (推荐首先阅读)
- ✅ 5分钟快速开始
- ✅ 常用命令一览
- ✅ 故障排查速查表
- ✅ 最佳实践清单

**阅读时间**: 5-10分钟

---

### 📄 SYSTEM_SUMMARY_LLM.md (理解整体架构)
- ✅ 完整系统架构图
- ✅ 每个模块详细说明 (1000+字)
- ✅ 工作流执行示例
- ✅ 系统优势和创新点

**阅读时间**: 15-20分钟

---

### 📄 LLM_WORKFLOW_GUIDE.md (深入学习)
- ✅ 前置环境设置详解
- ✅ 完整使用指南
- ✅ API详细文档
- ✅ CI/CD集成示例
- ✅ 性能优化建议
- ✅ 故障排除指南

**阅读时间**: 30-45分钟

---

## 🚀 快速命令参考

```bash
# 交互式菜单
python quickstart_llm.py --interactive

# 检查环境
python quickstart_llm.py --check

# 生成compile_commands.json
python quickstart_llm.py --generate-compile-commands

# 仅分析代码
python quickstart_llm.py --analyze

# 生成所有函数的测试
python quickstart_llm.py --generate

# 生成特定函数的测试
python tools/ut_workflow_llm.py \
  --project-dir . \
  --compile-commands build-ninja-msvc/compile_commands.json \
  --functions validate_name db_init add_student

# 显示帮助
python tools/ut_workflow_llm.py --help
```

---

## 🎓 学习路线

### 🟢 初级 (15分钟)
1. 阅读本文件导航部分
2. 运行 `python quickstart_llm.py --interactive`
3. 查看生成的测试文件示例

### 🟡 中级 (1小时)
1. 阅读 QUICKREF_LLM.md
2. 阅读 SYSTEM_SUMMARY_LLM.md
3. 尝试自定义参数配置

### 🔴 高级 (2-3小时)
1. 阅读 LLM_WORKFLOW_GUIDE.md
2. 研究核心源码（tools目录）
3. 自定义提示词或编译器支持

---

## 🔗 相关资源

### vLLM & Qwen
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [vLLM 文档](https://docs.vllm.ai)
- [Qwen 模型库](https://huggingface.co/Qwen)
- [Qwen2.5-Coder-32B](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct)

### 测试框架
- [Google Test](https://github.com/google/googletest)
- [Google Mock](https://github.com/google/googlemock)
- [gtest 官方文档](https://google.github.io/googletest/)

### CMake & 编译
- [CMake 官方文档](https://cmake.org/documentation/)
- [compile_commands.json 标准](https://clang.llvm.org/docs/JSONCompilationDatabase.html)

---

## ❓ 常见问题速查

| 问题 | 查看文档 | 快速答案 |
|------|----------|---------|
| 如何开始？ | QUICKREF_LLM.md | `python quickstart_llm.py` |
| vLLM怎么部署？ | LLM_WORKFLOW_GUIDE.md | 见"前置环境设置" |
| 生成的文件在哪？ | QUICKREF_LLM.md | `test/*_llm_test.cpp` |
| 如何自定义参数？ | llm_workflow_config.json | 修改JSON文件 |
| 测试生成失败？ | QUICKREF_LLM.md → 故障排查 | 检查vLLM连接 |
| 支持哪些编译器？ | SYSTEM_SUMMARY_LLM.md | MSVC, GCC, Clang |
| 如何集成CI/CD？ | LLM_WORKFLOW_GUIDE.md | GitHub Actions示例 |

---

## 📊 系统要求一览

```
✓ Python:           3.8+
✓ vLLM服务:        运行中 (8000端口)
✓ Qwen3 Coder:     32B参数模型
✓ 内存:            4GB+ (本地), GPU推荐
✓ CMake:           3.10+
✓ C/C++编译器:     MSVC/GCC/Clang
✓ compile_commands.json: 已生成 ✓
```

---

## ✅ 你现在应该...

### 如果这是你第一次：
→ **立即运行**: `python quickstart_llm.py --interactive`

### 如果你想学习：
→ **阅读**: [QUICKREF_LLM.md](QUICKREF_LLM.md) (5分钟)

### 如果你想深入：
→ **研究**: [SYSTEM_SUMMARY_LLM.md](SYSTEM_SUMMARY_LLM.md) (20分钟)

### 如果你需要完整参考：
→ **查看**: [LLM_WORKFLOW_GUIDE.md](LLM_WORKFLOW_GUIDE.md) (详细文档)

### 如果你遇到问题：
→ **检查**: [故障排查](#常见问题速查) 或 QUICKREF_LLM.md

---

## 📞 获取帮助

```bash
# 显示帮助信息
python quickstart_llm.py --help
python tools/ut_workflow_llm.py --help

# 检查环境状态
python quickstart_llm.py --check

# 查看日志
# 查看输出中的 DEBUG/INFO/WARNING/ERROR 消息
```

---

**最后更新**: 2026-02-13  
**版本**: 1.0  
**状态**: ✅ 完整且可用

**祝你使用愉快！🎉**
