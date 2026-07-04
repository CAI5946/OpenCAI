# 开发状态

## 当前状态

OpenCAI 的目标是设计并开发完整成熟的 CLI Coding Agent：读上下文、调工具、改文件、运行验证、继续迭代，并逐步扩展到 workflow runtime、multi-agents、modes、streaming outputs、LLM council 和可审计状态。

当前主线是 Feature A: Workflow。WorkflowSpec / WorkflowRunner 已完成首个串行 runtime 切片和 `/workflow` CLI 入口；`/workflow TASK` 已从普通 runtime command 中分流为结构化 `WorkflowCommandInput`，并由 `workflow_commands.py` 承接 workflow command flow；RuntimeSession 已引入 `execution_mode`，支持 `/mode agent|workflow` 和 `Shift+Tab` 在输入框切换，workflow mode 下普通文本会自动进入 Workflow Planner / WorkflowRunner；`workflow_planner.py` 已提供 Planner / Compiler V1 边界；Workflow Core Model 已引入 `WorkflowTask` / `TaskResult`，当前内置 `inspect_handoff` workflow 是 2 个 phase / 3 个 task 的串行 task graph。

并行产品验收目标是 Small-Task Coding Agent Competence：用本地 micro benchmark 衡量 OpenCAI 在小型代码任务上的实际表现，再用失败分类决定优先补 Workflow、Agent Loop、Tool Model、Context Engineering 还是 Modes。

历史状态和验证记录已归档到 `docs/logs/2026-07-04-status-history.md`。

## 当前能力

- `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认进入交互式 runtime。
- 默认 agent mode 下普通 task 走 Agent Loop；workflow mode 下普通文本自动走当前内置 `inspect -> handoff` workflow；`/workflow TASK` 保留为显式 workflow 入口。
- `--task` 保留为一次性调试路径。
- 默认 adapter 是 `gemini`；`--adapter fake` 是本地确定性调试入口。
- Agent Loop 正式入口是 `run_agent_loop()`；`run_fake_loop()` 仅保留为兼容 wrapper。
- Agent Loop 已将 `max_steps` 降级为最大模型轮次兜底预算，并支持重复工具调用和连续工具失败 stop reason。
- 工具模型已从单文件 `OpenCAI/tools.py` 拆到 `OpenCAI/tooling/` 分类模块；`OpenCAI.tools` 保留为兼容门面。
- 当前已实现 File、Search、Edit、Command、Planning、Context、Workflow、Web、Skill 等工具分类的一组核心工具；Agent、External/MCP、IDE/LSP 等边界工具仍以 deferred 形式保留。
- SafetyPolicy 已接入工具执行前置检查，默认 permission profile 是 `approve-safe`，支持 `read-only` / `ask-approval` / `approve-safe` / `full-access`。
- TUI 已具备 slash command、`$skill` 显式 skill 调用入口、`!` shell mode、`/model` 二级选择、`/mode agent|workflow`、`/keymap`、prompt history、多行输入、状态栏、执行中 live process 和最近一次 task 过程视图；`Shift+Tab` 当前切换 execution mode，permission 通过 `/permission` 切换。
- 普通 task 路径已支持 event streaming 数据源；Runtime 执行中展示临时 live process，完成后默认折叠，完整过程可通过 `Ctrl+O` 或 `/process` 展开。
- Workflow Planner / Compiler V1 已拆为 `workflow_planner.py`，当前 `compile_workflow(task)` 返回内置 `inspect_handoff` `WorkflowSpec`。
- WorkflowRunner 当前支持串行 task 执行、task dependency 检查、prompt composition、`TaskResult` 聚合为 `PhaseResult`，并通过 final phase 生成 workflow final answer。
- 本地 benchmark harness 已能复制隔离 workspace、运行初始/最终验证、检查严格 changed-files policy，并输出带诊断状态的 JSON report。
- Context Engineering 已完成 `ContextSnapshot` / `ContextProvider` / `ContextComposer` 第一刀，并已接入 Agent Loop / Runtime 普通 task 主路径；显式 `$skill` 会通过 `invoke_skill` 将 `SKILL.md` 作为 meta message 注入后续模型上下文。

## 下一步

- Workflow：设计 dependency-aware task context composition。
- Workflow：设计 task / phase scoped tool allowlist 和 policy 合并。
- Workflow：实现内置 Nodeflow bugfix workflow：clarify / plan / execute / review / verify / handoff。
- Workflow：实现 review / verify 失败回到 execute 的 retry loop。
- Workflow：支持 workflow command / save / replay。
- Benchmark：围绕 Level 1B 新建文件失败信号，用同一组 15 个任务复测新增 `write_file` / patch grammar 后的 plain Agent Loop，再对比 Workflow-guided bugfix loop。
- Context Engineering：设计 context budget 和可观察性，至少能展示本轮注入了哪些 context block、是否截断、各 block 字符数，并为后续 memory / workflow context 留出边界。
- Modes：设计 Runtime-level `ModeProfile`，评估 learn / dev / debug / review mode 如何影响 prompt、workflow selection、strategy selection 和 tool policy。
- Multi-agents：Workflow 主干稳定后，先做只读 parallel inspect / review，不并行写文件。

## 最近一次验证

- `python -m py_compile OpenCAI\__main__.py OpenCAI\runtime_commands.py OpenCAI\tui.py OpenCAI\composer.py OpenCAI\workflow_commands.py`：exit code `0`。
- `cmd /c "(echo /mode workflow&echo Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认 workflow mode 下普通输入自动进入 Workflow Planner / WorkflowRunner。
- `python -m unittest discover tests`：exit code `0`，205 个测试通过，确认 execution mode、`/mode`、`Shift+Tab` mode 切换、workflow command 和现有 runtime / workflow / context / safety / tooling 路径全量未回归。
