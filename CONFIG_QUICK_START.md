# ⚡ 配置文件快速上手（2分钟）

现在你可以在 `llm_workflow_config.json` 中直接配置项目路径和输出目录！

## 🎯 最简单的方式

### 第1步：编辑配置文件

打开 `llm_workflow_config.json`，修改 `paths` 部分：

```json
{
  "paths": {
    "project_root": "/path/to/your-c-project",
    "test_output_dir": "test"
  }
}
```

就这两个配置！其他可以用默认值。

### 第2步：运行

```bash
python generate_ut_for_repo.py
```

完成！🎉

---

## 📝 配置示例

### 示例1：本地项目（当前目录）

```json
{
  "paths": {
    "project_root": ".",
    "test_output_dir": "test"
  }
}
```

### 示例2：外部项目（相对路径）

项目在上层目录：

```json
{
  "paths": {
    "project_root": "../my-c-project",
    "test_output_dir": "ut"
  }
}
```

### 示例3：绝对路径（Windows）

```json
{
  "paths": {
    "project_root": "C:\\Users\\YourName\\projects\\my-code",
    "test_output_dir": "C:\\tmp\\generated-tests"
  }
}
```

### 示例4：绝对路径（Linux/macOS）

```json
{
  "paths": {
    "project_root": "/home/user/projects/my-code",
    "test_output_dir": "/tmp/generated-tests"
  }
}
```

### 示例5：自定义目录结构

如果你的项目不是标准的 `include/src` 结构：

```json
{
  "paths": {
    "project_root": ".",
    "include_dir": "headers",      ← 自定义头文件目录
    "src_dir": "source",           ← 自定义源文件目录  
    "test_output_dir": "test"
  }
}
```

---

## 🚀 三种使用方式

### 方式A：从配置直接运行（推荐）

```bash
cd /path/to/c-unit-test-workflow

# 编辑llm_workflow_config.json设置project_root
# 然后运行
python generate_ut_for_repo.py
```

### 方式B：指定配置文件

```bash
python tools/ut_workflow_llm.py --config llm_workflow_config.json
```

### 方式C：多个配置文件

为不同项目创建不同配置：

```bash
# config_projectA.json
# config_projectB.json
# config_projectC.json

# 分别运行
python tools/ut_workflow_llm.py --config config_projectA.json
python tools/ut_workflow_llm.py --config config_projectB.json
python tools/ut_workflow_llm.py --config config_projectC.json
```

---

## 📊 配置项说明

| 配置项 | 说明 | 必需 | 默认值 |
|------|------|------|-------|
| `project_root` | 被测代码根路径 | ✅ | `.` |
| `test_output_dir` | 生成的测试放置目录 | ❌ | `test` |
| `include_dir` | 头文件目录 | ❌ | `include` |
| `src_dir` | 源文件目录 | ❌ | `src` |

---

## ✨ 工作流

```
1️⃣ 编辑 llm_workflow_config.json
   └─ 配置 project_root 和 test_output_dir

2️⃣ 运行
   python generate_ut_for_repo.py

3️⃣ 选择菜单选项
   [1] 生成所有函数的UT
   [2] 为特定函数生成UT
   ...

4️⃣ 完成！
   测试文件保存到配置的 test_output_dir
```

---

## 💡 常见问题

**Q: 相对路径是相对于什么的？**

A: 相对于配置文件所在的目录。例如：
```json
{
  "project_root": "../my-project"
}
```
这表示：配置文件所在目录的上级目录中的 `my-project`

**Q: 可以用绝对路径吗？**

A: 可以！完全支持：
```json
{
  "project_root": "/home/user/my-project",
  "test_output_dir": "/tmp/output"
}
```

**Q: 如果不设置会怎么样？**

A: 使用默认值：
- `project_root` → `.`（当前目录）
- `test_output_dir` → `test`
- `include_dir` → `include`
- `src_dir` → `src`

**Q: 命令行能覆盖配置吗？**

A: 可以！命令行参数的优先级更高：
```bash
python tools/ut_workflow_llm.py \
  --config llm_workflow_config.json \
  --project-dir /override/path
```

---

## 📁 完整例子

创建以下文件结构：

```
workspace/
├── c-unit-test-workflow/          ← 工作流工具
│   ├── llm_workflow_config.json   ← 配置，指向下面的项目
│   ├── tools/
│   └── generate_ut_for_repo.py
│
└── my-c-project/                  ← 你的项目
    ├── CMakeLists.txt
    ├── include/
    ├── src/
    └── build/
        └── compile_commands.json
```

**配置 `llm_workflow_config.json`：**

```json
{
  "paths": {
    "project_root": "../my-c-project",
    "test_output_dir": "test"
  }
}
```

**运行：**

```bash
cd workspace/c-unit-test-workflow
python generate_ut_for_repo.py
```

输出会自动保存到 `workspace/my-c-project/test/`

---

## 🎓 学习路径

1. **快速上手** ← 你在这里
   - 只需设置 `project_root` 和 `test_output_dir`
   
2. **进阶配置**
   - 自定义目录结构
   - 多项目配置
   - 见 [CONFIG_FILE_USAGE.md](CONFIG_FILE_USAGE.md)

3. **完整参考**
   - 所有可能的配置选项
   - 见 [llm_workflow_config.json](llm_workflow_config.json)

---

## 📚 相关文件

- **[CONFIG_FILE_USAGE.md](CONFIG_FILE_USAGE.md)** - 完整详细指南
- **[llm_workflow_config.json](llm_workflow_config.json)** - 默认配置文件
- **[llm_workflow_config.example.json](llm_workflow_config.example.json)** - 配置示例

---

现在试试吧！🚀

```bash
# 1. 编辑配置
vim llm_workflow_config.json

# 2. 运行
python generate_ut_for_repo.py
```
