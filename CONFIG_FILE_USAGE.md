# 📝 配置文件使用指南

现在你可以在 `llm_workflow_config.json` 中直接配置**被测试代码根路径**和**生成的测试用例存放位置**了！

## 🎯 核心配置项

新增的 `paths` 配置部分：

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

| 配置项 | 说明 | 示例 |
|------|------|------|
| `project_root` | 被测试代码的根路径 | `"."` 或 `"/home/user/my-project"` |
| `test_output_dir` | 生成的测试用例存放目录<br/>（相对于project_root） | `"test"` 或 `"unit_tests"` |
| `include_dir` | 头文件目录<br/>（相对于project_root） | `"include"` 或 `"inc"` |
| `src_dir` | 源文件目录<br/>（相对于project_root） | `"src"` 或 `"source"` |

---

## 📖 使用方式

### 方式1️⃣：修改配置文件后直接运行

编辑 `llm_workflow_config.json`：

```json
{
  "paths": {
    "project_root": "/home/user/my-c-project",
    "test_output_dir": "ut",
    "include_dir": "include",
    "src_dir": "src"
  }
}
```

然后运行：

```bash
python generate_ut_for_repo.py
# 或
python tools/ut_workflow_llm.py --config llm_workflow_config.json
```

### 方式2️⃣：使用快速菜单

```bash
cd /path/to/c-unit-test-workflow
python generate_ut_for_repo.py

# 如果配置文件中有project_root，会自动从配置加载
# 否则要求输入项目路径
```

### 方式3️⃣：命令行覆盖

使用命令行参数覆盖配置文件中的设置：

```bash
# 覆盖项目路径
python tools/ut_workflow_llm.py \
  --config llm_workflow_config.json \
  --project-dir /another/project

# 或直接使用不同的配置文件
python tools/ut_workflow_llm.py --config my-custom-config.json
```

---

## 💡 实际示例

### 场景1：多个项目，使用同一份配置

创建多个配置文件：

**config_project_a.json:**
```json
{
  "paths": {
    "project_root": "/home/user/project-a",
    "test_output_dir": "tests",
    "include_dir": "headers",
    "src_dir": "algorithms"
  },
  "llm": {
    "api_base": "http://localhost:8000",
    "model": "qwen2.5-coder-32b"
  }
}
```

**config_project_b.json:**
```json
{
  "paths": {
    "project_root": "/home/user/project-b",
    "test_output_dir": "test",
    "include_dir": "include",
    "src_dir": "src"
  },
  "llm": {
    "api_base": "http://localhost:8000",
    "model": "qwen2.5-coder-32b"
  }
}
```

使用各自的配置：

```bash
# 为项目A生成UT
python tools/ut_workflow_llm.py --config config_project_a.json

# 为项目B生成UT
python tools/ut_workflow_llm.py --config config_project_b.json
```

### 场景2：本地路径（相对于配置文件）

如果你的配置文件和项目在同一个目录：

**目录结构:**
```
c-unit-test-workflow/
├── llm_workflow_config.json
├── my-project/
│   ├── CMakeLists.txt
│   ├── include/
│   ├── src/
│   └── build/
```

**配置:**
```json
{
  "paths": {
    "project_root": "my-project",
    "test_output_dir": "test"
  },
  "compile_commands": {
    "search_paths": [
      "my-project/build/compile_commands.json",
      "./build/compile_commands.json"
    ]
  }
}
```

**运行:**
```bash
python generate_ut_for_repo.py
# 或
python tools/ut_workflow_llm.py --config llm_workflow_config.json
```

### 场景3：绝对路径

**Windows:**
```json
{
  "paths": {
    "project_root": "C:\\Users\\YourName\\Documents\\my-c-project",
    "test_output_dir": "test"
  }
}
```

**Linux/macOS:**
```json
{
  "paths": {
    "project_root": "/home/user/projects/my-c-project",
    "test_output_dir": "test"
  }
}
```

---

## 🔄 配置优先级

系统加载配置的优先级如下：

```
命令行参数 > 环境变量 > 配置文件 > 默认值
```

具体说：

1. **命令行参数** - 最高优先级
   ```bash
   python tools/ut_workflow_llm.py \
     --config config.json \
     --project-dir /override/path  # ← 覆盖config中的project_root
   ```

2. **环境变量** - 对于LLM配置
   ```bash
   export VLLM_API_BASE=http://my-server:8000
   python tools/ut_workflow_llm.py --config config.json
   # ← 使用环境变量中的API地址，而不是config中的
   ```

3. **配置文件** - 次优先级
   ```json
   {
     "paths": {
       "project_root": "/from/config/file",
       "test_output_dir": "ut"
     }
   }
   ```

4. **默认值** - 最低优先级
   ```
   project_root: .
   test_output_dir: test
   include_dir: include
   src_dir: src
   ```

---

## 📋 完整配置示例

这是一份完整的配置示例，包含所有可能的选项：

```json
{
  "project": {
    "name": "My C Project",
    "version": "1.0",
    "description": "My awesome C project"
  },

  "llm": {
    "api_base": "http://localhost:8000",
    "model": "qwen2.5-coder-32b",
    "temperature": 0.7,
    "max_tokens": 4096,
    "top_p": 0.95,
    "timeout": 120
  },

  "code_analysis": {
    "include_patterns": ["*.h"],
    "source_patterns": ["*.c"],
    "exclude": [
      "**/third_party/**",
      "**/build/**",
      "**/.git/**"
    ]
  },

  "test_generation": {
    "framework": "gtest",
    "output_suffix": "_llm_test.cpp",
    "include_mocks": true,
    "coverage_goal": 80
  },

  "compile_commands": {
    "search_paths": [
      "./build/compile_commands.json",
      "./build-ninja-msvc/compile_commands.json",
      "./cmake-build-debug/compile_commands.json"
    ]
  },

  "paths": {
    "project_root": ".",
    "test_output_dir": "test",
    "include_dir": "include",
    "src_dir": "src"
  }
}
```

---

## 🛠️ 常见场景

### Q1：项目在外部，如何配置？

**项目结构：**
```
C:/Projects/my-c-lib/
  ├── CMakeLists.txt
  ├── include/
  ├── src/
  └── build/

C:/tools/c-unit-test-workflow/
  ├── llm_workflow_config.json
  ├── tools/
  └── ...
```

**配置：**
```json
{
  "paths": {
    "project_root": "C:/Projects/my-c-lib",
    "test_output_dir": "test"
  },
  "compile_commands": {
    "search_paths": [
      "C:/Projects/my-c-lib/build/compile_commands.json"
    ]
  }
}
```

### Q2：测试文件要输出到项目外的目录？

```json
{
  "paths": {
    "project_root": "/home/user/my-project",
    "test_output_dir": "/home/user/generated-tests"
  }
}
```

> 注意：`test_output_dir` 也支持绝对路径！

### Q3：项目使用非标准的目录结构？

```
my-project/
├── CMakeLists.txt
├── headers/      ← 不是include
├── src/
│   ├── core/
│   └── utils/
└── build/
```

**配置：**
```json
{
  "paths": {
    "project_root": ".",
    "include_dir": "headers",    ← 自定义头文件目录
    "src_dir": "src",
    "test_output_dir": "generated_tests"
  }
}
```

### Q4：多项目批处理脚本

创建 `batch_generate.py`：

```python
import subprocess
import json

configs = [
    "config_libA.json",
    "config_libB.json",
    "config_libC.json"
]

for config in configs:
    print(f"\n{'='*60}")
    print(f"Processing: {config}")
    print('='*60)
    
    result = subprocess.run(
        ["python", "tools/ut_workflow_llm.py", "--config", config],
        timeout=3600
    )
    
    if result.returncode == 0:
        print(f"✓ {config} generated successfully")
    else:
        print(f"✗ {config} failed")
```

运行：
```bash
python batch_generate.py
```

---

## ✨ 工作流

使用配置文件后的标准工作流：

```bash
# 1️⃣ 编辑配置文件
vim llm_workflow_config.json

# 2️⃣ 生成编译数据库（如果还没有）
cd /path/to/my-project
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B build

# 3️⃣ 运行生成工具
cd /path/to/c-unit-test-workflow
python generate_ut_for_repo.py
# 或
python tools/ut_workflow_llm.py --config llm_workflow_config.json

# 4️⃣ 检查生成的测试
ls /path/to/my-project/test/*_llm_test.cpp
```

---

## 🔍 验证配置

检查配置是否正确：

```bash
# 方式1：直接运行，如果有问题会报错
python generate_ut_for_repo.py

# 方式2：只分析不生成
python tools/ut_workflow_llm.py \
  --config llm_workflow_config.json \
  --analyze-only
```

---

## 📚 相关文件

- `llm_workflow_config.json` - 主配置文件
- `generate_ut_for_repo.py` - 便捷工具（支持配置）
- `tools/ut_workflow_llm.py` - 核心工作流（支持 `--config` 参数）
- `quickstart_llm.py` - 交互式启动脚本

---

## ✅ 检查清单

设置前确保：

- [ ] 项目根目录存在
- [ ] 项目有 `CMakeLists.txt`
- [ ] `compile_commands.json` 已存在或可以生成
- [ ] 配置文件路径正确（绝对或相对）
- [ ] 输出目录权限可写

现在配置好后直接运行：

```bash
python generate_ut_for_repo.py
```

就这么简单！🚀
