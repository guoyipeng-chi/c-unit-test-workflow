# ✨ 配置文件功能总结

你现在可以在 `llm_workflow_config.json` 中直接配置被测试代码路径和测试输出目录了！

## 🎉 新增功能

### 在 `llm_workflow_config.json` 中添加了 `paths` 配置部分：

```json
{
  "paths": {
    "project_root": ".",
    "test_output_dir": "test",
    "include_dir": "include",
    "src_dir": "src"
  }
}
```

## 📝 核心配置项

| 配置项 | 说明 | 示例 |
|------|------|------|
| `project_root` | **被测试代码的根路径** | `"."` / `"../my-project"` / `"/abs/path"` |
| `test_output_dir` | **生成的测试放置目录** | `"test"` / `"ut"` / `"/tmp/output"` |
| `include_dir` | 头文件目录（相对于project_root） | `"include"` / `"headers"` |
| `src_dir` | 源文件目录（相对于project_root） | `"src"` / `"source"` |

## 🚀 使用方式

### 方式1️⃣：修改配置后直接运行（最简单）

```bash
# 1. 编辑 llm_workflow_config.json
#    修改 project_root 和 test_output_dir

# 2. 运行
python generate_ut_for_repo.py
```

### 方式2️⃣：从配置文件启动工作流

```bash
# 使用配置文件运行完整工作流
python tools/ut_workflow_llm.py --config llm_workflow_config.json

# 或只分析不生成
python tools/ut_workflow_llm.py --config llm_workflow_config.json --analyze-only
```

### 方式3️⃣：多个配置文件（多项目）

创建 `config_projectA.json` 和 `config_projectB.json`：

```bash
python tools/ut_workflow_llm.py --config config_projectA.json
python tools/ut_workflow_llm.py --config config_projectB.json
```

## 💡 实际例子

### 例子1：项目在相对路径

```json
{
  "paths": {
    "project_root": "../my-c-project",
    "test_output_dir": "generated_tests"
  }
}
```

### 例子2：项目使用绝对路径

```json
{
  "paths": {
    "project_root": "/home/user/my-c-project",
    "test_output_dir": "/tmp/ut_output"
  }
}
```

### 例子3：自定义目录结构

```json
{
  "paths": {
    "project_root": ".",
    "include_dir": "headers",
    "src_dir": "lib/source", 
    "test_output_dir": "test/generated"
  }
}
```

## ✅ 完整工作流

```
1️⃣ 在llm_workflow_config.json中配置paths
   ↓
2️⃣ 运行 python generate_ut_for_repo.py
   ↓
3️⃣ 选择菜单选项
   [1] 生成所有函数UT
   [2] 为特定函数生成UT
   ↓
4️⃣ 测试生成到配置的test_output_dir
   ✓ 完成！
```

## 🔧 已修改的文件

1. **llm_workflow_config.json** - 已扩展 paths 配置项
2. **tools/ut_workflow_llm.py** - 已添加 from_config() 类方法和 --config 参数
3. **generate_ut_for_repo.py** - 已添加 setup_from_config() 方法

## 📚 帮助文档

- **快速上手** → [CONFIG_QUICK_START.md](CONFIG_QUICK_START.md) （2分钟）
- **完整指南** → [CONFIG_FILE_USAGE.md](CONFIG_FILE_USAGE.md) （深度指南）
- **配置示例** → [llm_workflow_config.example.json](llm_workflow_config.example.json)

## 🎯 关键特性

✅ **绝对路径支持** - 完全支持绝对路径  
✅ **相对路径支持** - 相对于配置文件位置  
✅ **命令行覆盖** - CLI参数可覆盖配置文件  
✅ **环境变量优先** - VLLM_API_BASE等优先级最高  
✅ **多配置支持** - 为不同项目创建多个配置文件  
✅ **默认值** - 不设置也有合理默认值  

## 🔄 优先级顺序

```
命令行参数 > 环境变量 > 配置文件 > 默认值
```

例如：
```bash
# 命令行覆盖配置文件
python tools/ut_workflow_llm.py \
  --config llm_workflow_config.json \
  --project-dir /override/path

# 环境变量优先
export VLLM_API_BASE=http://my-server:8000
python tools/ut_workflow_llm.py --config config.json
```

## 💡 使用建议

1. **第一次使用** - 按照 [CONFIG_QUICK_START.md](CONFIG_QUICK_START.md) 操作
2. **多个项目** - 创建多个配置文件，方便批处理
3. **持续使用** - 配置一次，重复使用，提高效率
4. **团队共享** - 把配置文件纳入版本控制

## 🎓 下一步

现在你可以：

```bash
# 1. 编辑配置
vim llm_workflow_config.json

# 2. 运行一行命令生成UT
python generate_ut_for_repo.py
```

不需要再输入项目路径了，一切尽在配置文件中！🎉

---

**需要帮助？** 查看 [CONFIG_FILE_USAGE.md](CONFIG_FILE_USAGE.md) 了解更多细节。
