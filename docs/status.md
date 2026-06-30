# 开发状态

## 当前阶段

OpenCAI 的目标是设计并开发完整成熟的 CLI Coding Agent：读上下文、调工具、改文件、运行验证、继续迭代，并逐步扩展到 workflow runtime、multi-agents、modes、streaming outputs、LLM council 和可审计状态。

当前主线是 Feature A: Workflow。WorkflowSpec / WorkflowRunner 已完成首个串行 runtime 切片和 `/workflow` CLI 入口；下一步围绕 `/workflow` 增加 execute / cancel confirmation gate，拆分 workflow command flow，并为后续 humancheck phase 保留清晰边界。

并行产品验收目标是 Small-Task Coding Agent Competence：用本地 micro benchmark 衡量 OpenCAI 在小型代码任务上的实际表现，再用失败分类决定优先补 Workflow、Agent Loop、Tool Model、Context Engineering 还是 Modes。

## 当前能力

- `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认进入交互式 runtime。
- 普通 task 走 Agent Loop；`/workflow TASK` 走当前内置 `inspect -> handoff` workflow。
- `--task` 保留为一次性调试路径。
- 默认 adapter 是 `fake`；`--adapter gemini` 是显式真实模型入口。
- Agent Loop 正式入口是 `run_agent_loop()`；`run_fake_loop()` 仅保留为兼容 wrapper。
- 工具模型包含 `read_file`、`search_files`、`apply_patch`、`run_command`。
- SafetyPolicy 已接入工具执行前置检查，默认拒绝模型发起的写入和命令执行，除非 Runtime 显式开启权限。
- TUI 已具备 slash command、`!` shell mode、`/model` 二级选择、suggestion key binding、状态栏和轻量 composer 输入区。
- WorkflowRunner 当前支持串行 phase、depends_on、prompt composition、PhaseResult 和 final phase 收口。
- 本地 benchmark harness 已能复制隔离 workspace、运行 OpenCAI、执行验证命令并输出 JSON report。

## 已完成里程碑

- Phase 0-5：完成 Runtime、Event / Transcript、Renderer / TUI、Tool Model、Agent Loop、LLM Adapter 的基础边界和最小实现。
- Phase 6：完成 toy project closed loop，验证失败测试 -> 读文件 -> 修改文件 -> 再验证 -> final answer 的基本闭环。
- Phase 7：完成交互式 Runtime / TUI Shell，`python -m OpenCAI` 默认进入输入循环。
- Phase 8：完成真实 GeminiAdapter 最小接入，并验证 text smoke 与 `read_file -> function_response -> final_answer`。
- Phase 9：完成 `search_files`，并将 Agent Loop 正式入口调整为 `run_agent_loop()`。
- Phase 10：完成真实 Gemini toy repair loop 验证。
- Phase 11：完成 Minimal Safety Layer，加入 path 边界、权限开关和危险命令 blocklist。
- Phase 12：完成 Productized CLI，包含 slash command registry、Composer、shell mode、`/model` 二级选择和 README 最小使用说明。
- Phase 13：完成 WorkflowRunner 第一组切片，接入 `/workflow TASK`，并修正 `max_steps` 截断语义为 `stop` event。
- 已新增开发态版本源 `OpenCAI.__version__ = "0.0.0-dev"`，并接入 `python -m OpenCAI --version`。
- 已新增 Small-Task Coding Agent Competence 计划文档和本地 benchmark harness 第一刀。

## 正在做

- Feature A / Workflow：为 `/workflow` 增加 execute / cancel confirmation gate。
- Feature A / Workflow：评估是否拆出 `workflow_commands.py`，避免 `runtime_commands.py` 继续变重。
- Product Goal / Benchmark：用 Level 1 本地 micro benchmark 建立稳定评测入口，并用真实 Gemini baseline 的失败原因指导下一刀。

## 下一步

- Workflow：补 `/workflow` execute / cancel confirmation gate。
- Workflow：实现内置 Nodeflow bugfix workflow：clarify / plan / execute / review / verify / handoff。
- Workflow：实现 review / verify 失败回到 execute 的 retry loop。
- Workflow：支持 workflow command / save / replay。
- Benchmark：运行 `python -m benchmarks.runner --task all --adapter gemini` 建立真实 baseline。
- Context Engineering：设计 `ContextSnapshot` / `ContextProvider` / `ContextComposer`，先补 Session 初始化 context，不做传统 RAG。
- Modes：设计 Runtime-level `ModeProfile`，评估 learn / dev / debug / review mode 如何影响 prompt、workflow selection、strategy selection 和 tool policy。
- Multi-agents：Workflow 主干稳定后，先做只读 parallel inspect / review，不并行写文件。

## 阻塞/待确认

- `/workflow TASK` 当前展示 plan 后直接执行，尚未加入 execute / cancel / modify / write in confirmation gate。
- 当前只有内置 `inspect -> handoff` workflow；尚未接 Nodeflow bugfix workflow、retry loop、humancheck、save/replay 或 LLM-generated WorkflowSpec / WorkflowScript。
- `apply_patch` 仍是学习用最小 `path/old/new` 文本替换，不是完整 diff parser。
- `search_files` 仍是最小 UTF-8 文本搜索，不支持 glob/include/exclude、大小写选项或完整 ripgrep wrapper。
- 统一验证命令不作为 CLI flag 处理；后续在 WorkflowRunner 或 hook 机制中重新设计。
- 产品化 CLI 的最终默认 adapter 仍待后续切片确认；当前先保持 fake 默认，真实 Gemini 通过显式参数进入。
- Streaming Outputs 会改变 Agent Loop / WorkflowRunner / Renderer 的事件交付方式，需要保留当前 `list[Event]` 测试路径。
- LLM Council 先从 role-based model routing 进入，不急着做多模型投票。

## 最近验证

- `python -m unittest discover tests`：exit code `0`，70 个测试通过，确认 benchmark harness 未破坏现有 workflow、runtime command、composer、TUI、shell mode 和 safety 测试。
- `python -m py_compile benchmarks\__init__.py benchmarks\runner.py tests\test_benchmark_runner.py`：exit code `0`，确认新增 benchmark harness 语法可编译。
- `python -m unittest tests.test_benchmark_runner`：exit code `0`，7 个测试通过，确认 benchmark task 读取、workspace 隔离、验证命令、命令超时、agent cwd 和结果状态契约。
- `python -m benchmarks.runner --task all --timeout 30`：exit code `1`，fake adapter baseline 为 `0/3 passed`；失败发生在隔离 fixture workspace 中，是预期 baseline 失败，不是 harness 崩溃。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，51 个测试通过，确认 statusline 改动未破坏相关路径。
- `cmd /c "(echo /status&echo !python -c ""print(246)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认非 TTY runtime command 与 shell mode 仍正常。

## 相关文档

- 当前路线索引：`docs/roadmap.md`。
- 当前执行计划：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- Small-task 产品验收路线：`docs/plans/small-task-coding-agent-competence.md`。
- 核心循环架构：`docs/core-loop-architecture.md`。
- 学习型开发流程：`docs/learning-mode.md`。
- Phase 9 学习日志：`docs/phase-9-tool-completion.md`。
- Phase 10 学习日志：`docs/phase-10-real-toy-repair.md`。
- Phase 12 学习日志：`docs/phase-12-productized-cli.md`。
- Phase 13 设计文档：`docs/phase-13-dynamic-workflows.md`。
