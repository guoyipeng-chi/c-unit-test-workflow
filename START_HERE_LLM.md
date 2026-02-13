# 🚀 立即开始使用 (START HERE)

## 欢迎！👋

你有一个**完整的、生产就绪的C代码LLM测试生成系统**。

---

## ⚡ 30秒快速开始

### 选项1: 交互式菜单 (推荐) 🎯
```bash
python quickstart_llm.py --interactive
```
然后按菜单提示操作。最简单！

### 选项2: 快速检查 ✅
```bash
python quickstart_llm.py --check
```
检查环境是否配置好。

### 选项3: 完整工作流 ⚡
```bash
python quickstart_llm.py --generate
```
生成所有函数的测试。

---

## 📋 在你运行之前，你需要：

### ✅ 检查项清单

- [ ] **Python 3.8+** 已安装
  ```bash
  python --version
  ```

- [ ] **vLLM服务**已启动 (远程或本地)
  ```bash
  # 本地启动 (需要GPU)
  python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-Coder-32B-Instruct \
    --port 8000
  ```

- [ ] **compile_commands.json** 已生成 ✓
  ```
  ✓ 已存在于: build-ninja-msvc/compile_commands.json
  ```

---

## 🎯 我想要...

### 我想立即看效果
```bash
python quickstart_llm.py --interactive
# 选择: 1) Check Environment ✓
# 选择: 2) Setup vLLM Connection
# 选择: 5) Generate Tests for One Function
```
**预期时间**: 2-3分钟

---

### 我想理解这个系统怎么工作
阅读这些文件 (按顺序):
```
1. LLM_WORKFLOW_INDEX.md    (导航和概览)
2. QUICKREF_LLM.md          (快速参考)
3. SYSTEM_SUMMARY_LLM.md    (系统架构)
```
**预期时间**: 20分钟

---

### 我想生成完整的测试套件
```bash
python quickstart_llm.py --generate
```
或者命令行:
```bash
python tools/ut_workflow_llm.py \
  --project-dir . \
  --compile-commands build-ninja-msvc/compile_commands.json
```
**预期时间**: 5-30分钟 (取决于函数数量)

---

### 我想自定义配置
编辑这个文件:
```
llm_workflow_config.json
```
配置项包括:
- LLM API地址 (api_base)
- 模型名称 (model)
- 生成参数 (温度、max_tokens等)

**参考**: LLM_WORKFLOW_GUIDE.md → 配置部分

---

### 我遇到了问题
1. 运行诊断:
   ```bash
   python quickstart_llm.py --check
   ```

2. 查看故障排查:
   ```
   QUICKREF_LLM.md → 故障排查部分
   或
   LLM_WORKFLOW_GUIDE.md → 完整故障排除指南
   ```

---

## 📁 主要文件在哪

```
根目录:
├── quickstart_llm.py                 ← 交互式启动脚本 (使用这个!)
├── llm_workflow_config.json          ← 配置文件 (编辑这个)
│
├── 📚 文档:
│   ├── LLM_WORKFLOW_INDEX.md         ← 🌟 总导航
│   ├── QUICKREF_LLM.md               ← 快速参考
│   ├── SYSTEM_SUMMARY_LLM.md         ← 系统总结
│   ├── LLM_WORKFLOW_GUIDE.md         ← 完整指南
│   └── PROJECT_COMPLETION.md         ← 项目总结
│
├── tools/
│   ├── llm_client.py                 ← vLLM API客户端
│   ├── compile_commands_analyzer.py  ← 编译信息解析
│   ├── llm_test_generator.py         ← 测试生成引擎
│   └── ut_workflow_llm.py            ← 主工作流
│
├── build-ninja-msvc/
│   └── compile_commands.json         ← 编译数据库 ✓ 已有
│
└── test/
    └── *_llm_test.cpp                ← 生成的测试 (输出位置)
```

---

## 🔄 工作流示意图

```
你想要生成测试?
       │
       ↓
运行 quickstart_llm.py
       │
       ├─→ 环境检查 ✓
       ├─→ 连接vLLM ✓
       ├─→ 分析代码 ✓
       ├─→ 读取编译信息 ✓
       ├─→ 调用LLM生成 🧠
       ├─→ 保存结果 ✓
       └─→ 验证代码 ✓
            │
            ↓
    test/*_llm_test.cpp 生成! 🎉
```

---

## 💡 快速小贴士

### 小贴士1: 环境变量 (可选)
如果vLLM不在localhost:8000，设置环境变量:
```bash
set LLM_API_URL=http://your-remote-server:8000/v1
```

### 小贴士2: 精选函数生成
不需要生成所有函数的测试，可以只生成特定函数:
```bash
python tools/ut_workflow_llm.py \
  --functions validate_name db_init add_student
```

### 小贴士3: 输出位置自定义
```bash
python tools/ut_workflow_llm.py \
  --output-dir ./my_tests
```

### 小贴士4: 仅分析不生成
想先看看会生成什么，但不调用LLM:
```bash
python tools/ut_workflow_llm.py --analyze-only
```

### 小贴士5: 日志输出
运行时会看到详细输出:
```
[DEBUG] 加载编译命令...
[INFO]  找到9个编译条目
[INFO]  分析中...
[WARNING] 某些依赖未找到
[INFO]  生成测试中...
```

---

## ⚙️ 常用命令速查

```bash
# 交互式菜单 (新手推荐)
python quickstart_llm.py --interactive

# 检查环境状态
python quickstart_llm.py --check

# 一键生成所有测试
python quickstart_llm.py --generate

# 只分析代码，不生成
python tools/ut_workflow_llm.py --analyze-only

# 生成特定函数测试
python tools/ut_workflow_llm.py --functions validate_name db_init

# 自定义输出目录
python tools/ut_workflow_llm.py --output-dir ./output

# 显示所有选项
python quickstart_llm.py --help
python tools/ut_workflow_llm.py --help
```

---

## 🎯 预期结果

运行成功后，你会看到:

### 1️⃣ 控制台输出
```
[INFO] 检查环境... ✓
[INFO] 连接vLLM... ✓
[INFO] 分析代码... 找到 8 个函数
[INFO] 读取编译信息... ✓
[INFO] 为 database.c 生成测试...
[INFO] 为 validator.c 生成测试...
[INFO] 为 student_manager.c 生成测试...
[INFO] ✅ 完成! 生成的测试位置: test/
```

### 2️⃣ 生成的文件
```
test/database_llm_test.cpp
test/validator_llm_test.cpp
test/student_manager_llm_test.cpp
```

### 3️⃣ 测试内容示例
```cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "database.h"

TEST(DatabaseTest, InitializeDatabase) {
    EXPECT_EQ(db_init(), 0);
}

TEST(DatabaseTest, AddStudent) {
    Student s = {1, "Alice", 85.5};
    EXPECT_EQ(add_student(s), 0);
}

// ... 更多测试
```

---

## ❓ 常见问题

### Q: "Connection refused" 错误
**A**: vLLM服务没有运行。查看 LLM_WORKFLOW_GUIDE.md 的"vLLM部署"部分。

### Q: "No such file or directory: compile_commands.json"
**A**: 文件在 `build-ninja-msvc/compile_commands.json`，配置里应该指向这个路径 (已默认配置)。

### Q: 生成的测试代码质量不好
**A**: 这是正常的。可以调整 llm_workflow_config.json 中的参数:
- 降低 temperature (0.3-0.5) 获得更保守的结果
- 提高 temperature (0.8-1.0) 获得更创意的结果
- 增加 max_tokens 获得更详细的测试

### Q: 我可以修改生成的测试吗?
**A**: 完全可以！生成的文件是 `*_llm_test.cpp`，你可以随意编辑。

### Q: 怎么重新生成?
**A**: 再次运行脚本会覆盖旧的生成文件 (or 先备份)。

---

## 🎓 接下来学什么

### 初学者 (15分钟)
1. ✅ 运行 `python quickstart_llm.py --interactive`
2. ✅ 看看生成的测试文件
3. ✅ 尝试自定义参数

### 学习者 (1小时)
1. 阅读 QUICKREF_LLM.md
2. 研究 SYSTEM_SUMMARY_LLM.md
3. 尝试修改生成的测试

### 专家 (2小时+)
1. 阅读 LLM_WORKFLOW_GUIDE.md
2. 研究源代码 (tools/ 目录)
3. 自定义提示词或添加功能

---

## 📞 需要帮助？

### 快速检查
```bash
python quickstart_llm.py --check
```

### 查看文档
- 快速参考: [QUICKREF_LLM.md](QUICKREF_LLM.md)
- 完整导航: [LLM_WORKFLOW_INDEX.md](LLM_WORKFLOW_INDEX.md)
- 详细指南: [LLM_WORKFLOW_GUIDE.md](LLM_WORKFLOW_GUIDE.md)

### 常见问题
查看 QUICKREF_LLM.md 的"故障排查"部分或 LLM_WORKFLOW_GUIDE.md 的"完整故障排除指南"。

---

## ✅ 准备好了吗？

```bash
python quickstart_llm.py --interactive
```

**祝你使用愉快！🎉**

---

**如有问题，查阅 [LLM_WORKFLOW_INDEX.md](LLM_WORKFLOW_INDEX.md) 获取完整导航。**
