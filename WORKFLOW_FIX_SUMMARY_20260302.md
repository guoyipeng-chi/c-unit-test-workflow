# Workflow 修复总结（2026-03-02）

## 目标与结果
- 目标：按固定路径 `quickstart_llm.py -> 5 -> add_student -> 7`，让 LLM 生成测试从反复 `COMPILE_FAILED` 收敛到可编译、可执行。
- 最终结果：`add_student_llm_test` 已在该路径下完成 **编译通过 + 测试通过（PASSED）**。

## 关键修改

### 1) 编译/链接链路稳定性增强
文件：`tools/ut_workflow_llm.py`

- 在 GCC/Clang 风格编译命令中加入：
  - `-ffunction-sections`
  - `-fdata-sections`
  - `-Wno-deprecated`
  - `-Wno-deprecated-declarations`
- Windows 下追加链接优化：`-Wl,/OPT:REF`
- 作用：降低“同一 .c 中未测函数带出无关未解析符号”导致的链接噪声和失败概率。

### 2) gtest/gmock 链接输入补强
文件：`tools/ut_workflow_llm.py`

- `_resolve_gtest_link_inputs(...)` 增强为支持 gmock：
  - 源码模式可纳入 `gmock-all.cc + gtest-all.cc + gtest_main.cc`
  - 库模式可识别 `gmock + gtest_main + gtest`
- 作用：修复此前大量 gmock 相关 `LNK2019`。

### 3) unresolved symbol 自动注桩兜底
文件：`tools/ut_workflow_llm.py`

- 新增 `_extract_unresolved_symbols(...)`：从中英文 linker 输出提取未解析符号。
- 新增 `_inject_linker_stubs(...)`：自动在测试文件注入最小兼容 stub（基于 `code_analyzer` 签名信息），避免与声明冲突。
- 特殊处理 `g_next_id`：当检测到仅声明/使用、缺定义时自动注入兜底定义。
- 作用：把“工具链/链接层阻塞”从 LLM 代码修复路径中剥离，提升自动恢复能力。

### 4) 自动修复循环重构
文件：`tools/ut_workflow_llm.py`

- 将“编译重试轮次”与“LLM 修复次数”解耦。
- 允许在最后一轮注桩后扩展一轮重编译，确保技术性修复能真正生效。
- 作用：避免“最后一次才注桩但没有再编译机会”的死锁。

### 5) 生成约束与清洗强化
文件：`tools/llm_test_generator.py`

- Prompt 增加硬约束：
  - 不得重定义生产函数；
  - 必须保持头文件函数签名（含 `const`）；
  - 禁止依赖内部/静态全局（例如 `g_next_id`）。
- `fix_test_from_compile_error(...)` 增强：
  - 从编译错误中提取冲突符号与未解析符号，加入清洗黑名单。
- 作用：减少 `conflicting types`、重复定义、错误外部引用的反复出现。

### 6) 编译器发现与环境鲁棒性（本轮前后延续修复）
文件：`quickstart_llm.py`, `tools/ut_workflow_llm.py`

- 补充 Windows 常见 LLVM 路径兜底，提升 `clang++/clang-tidy/clang-format` 检出率。
- `quickstart` 运行时将解析出的编译器注入 `CXX` 环境，确保子流程一致。
- 作用：减少“可用编译器已安装但流程检测不到”的误判。

## 验证过程要点
- 多轮按固定菜单路径复跑，持续收集：
  - `log/add_student_llm_test_compile_attempt*.log`
  - `log/add_student_llm_test_autofix_attempt*.log`
  - `log/add_student_llm_test_run_*.log`
- 失败形态收敛过程：
  1. 生成代码签名冲突 / 重定义
  2. gmock 符号缺失
  3. 无关函数的 unresolved symbols
  4. 最终进入可执行并通过

## 当前状态
- `add_student` 场景：在指定 quickstart 路径下已达成 PASS。
- 质量闸门：`clang-tidy` 仍会报告问题（当前是 non-strict，流程可继续）。

## 建议的后续优化（可选）
- 将“链接注桩兜底”做成显式配置开关（如 `test_generation.linker_stub_fallback`），便于在严格模式禁用。
- 为通过后的测试做一次轻量语义回归（检查断言是否过度依赖桩行为）。
- 若要提升分析精度，可补齐 `libclang.dll` 环境，减少 fallback 解析误差。
