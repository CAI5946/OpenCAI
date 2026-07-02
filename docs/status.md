# 开发状态

## 当前阶段

OpenCAI 的目标是设计并开发完整成熟的 CLI Coding Agent：读上下文、调工具、改文件、运行验证、继续迭代，并逐步扩展到 workflow runtime、multi-agents、modes、streaming outputs、LLM council 和可审计状态。

当前主线是 Feature A: Workflow。WorkflowSpec / WorkflowRunner 已完成首个串行 runtime 切片和 `/workflow` CLI 入口；下一步围绕 `/workflow` 增加 execute / cancel confirmation gate，拆分 workflow command flow，并为后续 humancheck phase 保留清晰边界。

并行产品验收目标是 Small-Task Coding Agent Competence：用本地 micro benchmark 衡量 OpenCAI 在小型代码任务上的实际表现，再用失败分类决定优先补 Workflow、Agent Loop、Tool Model、Context Engineering 还是 Modes。

## 当前能力

- `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认进入交互式 runtime。
- 普通 task 走 Agent Loop；`/workflow TASK` 走当前内置 `inspect -> handoff` workflow。
- `--task` 保留为一次性调试路径。
- 默认 adapter 是 `gemini`；`--adapter fake` 是本地确定性调试入口。
- Agent Loop 正式入口是 `run_agent_loop()`；`run_fake_loop()` 仅保留为兼容 wrapper。
- Agent Loop 已将 `max_steps` 降级为最大模型轮次兜底预算，新增重复工具调用和连续工具失败 stop reason；默认兜底预算为 `8`。
- 工具模型包含 `read_file`、`search_files`、`list_skills`、`read_skill`、`apply_patch`、`run_command`。
- SafetyPolicy 已接入工具执行前置检查，默认 permission profile 是 `approve-safe`，并支持 `read-only` / `ask-approval` / `approve-safe` / `full-access` 四类 profile；`/permission` 已使用二级选择器，旧 `/allow-write` / `/allow-command` 和对应 CLI flag 已移除；当前 ask gate 尚未实现，需确认的模型工具调用会作为 deny observation 返回。
- TUI 已具备 slash command、`!` shell mode、`/model` 二级选择、suggestion key binding、状态栏、轻量 composer 输入区、执行中 live process 和最近一次 task 临时过程视图。
- 普通 task 路径已支持 event streaming 数据源：Agent Loop 通过 `iter_agent_loop()` 产生 transcript events；Runtime 执行中用临时 live process 显示过程，完成后自动收起并只保留 final answer 摘要，完整过程保存在 session 中并可通过 `Ctrl+O` 或 `/process` 展开；TTY composer 中 `Ctrl+O` 通过退出当前 input app 并返回 `/process` 做安全 handoff，不在 key handler 内嵌套启动新的 prompt_toolkit app；过程视图按 `Ctrl+O` / `Esc` / `Enter` / `q` 收起；`run_agent_loop()` 继续保留 `list[Event]` 兼容测试、workflow 和 benchmark。
- WorkflowRunner 当前支持串行 phase、depends_on、prompt composition、PhaseResult 和 final phase 收口。
- 本地 benchmark harness 已能复制隔离 workspace、运行初始/最终验证、检查严格 changed-files policy，并输出带诊断状态的 JSON report。
- Context Engineering 已新增第一组 Session 初始化上下文组件：`ContextProvider` 采集 cwd / repo root / git / runtime / AGENTS.md entry points，并读取 project/global AGENTS.md raw instruction 内容；当前还会从 `<repo>/.opencai/skills` 和 `~/AgentSkills` 收集 skill registry 摘要，`ContextComposer` 可按 `system > project instructions > global instructions > available skills > environment > task` 组装 provider-independent messages；普通 task runtime 路径已默认使用 composed initial messages。

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
- Agent Loop 停止条件第一刀：保留 `max_steps` 兼容入口，内部引入 LoopBudget / LoopState / StopReason，并新增 `repeated_action` 与 `consecutive_tool_failures`。
- 已新增开发态版本源 `OpenCAI.__version__ = "0.0.0-dev"`，并接入 `python -m OpenCAI --version`。
- 已新增 Small-Task Coding Agent Competence 目标文档和本地 benchmark harness 第一刀。

## 正在做

- Feature A / Workflow：为 `/workflow` 增加 execute / cancel confirmation gate。
- Feature A / Workflow：评估是否拆出 `workflow_commands.py`，避免 `runtime_commands.py` 继续变重。
- Product Goal / Benchmark：Level 1 本地 micro benchmark 已分为 10 个 Level 1A smoke baseline 和 5 个 Level 1B diagnostic tasks；最新 Gemini 全量结果为 `14/15 passed`，唯一失败是 `level1b_create_slug_module` 创建了空 `slug.py`，暴露新建文件实现质量缺口。
- Context Engineering：已完成 `ContextSnapshot` / `ContextProvider` / `ContextComposer` 第一刀，并已接入 Agent Loop / Runtime 普通 task 主路径；skill registry context 已完成摘要注入，但尚未实现 `invoke_skill` / skill message injection；当前重点是补 context budget / rendering / debug visibility，避免初始 context 变成不可观察噪声。

## 下一步

- Workflow：补 `/workflow` execute / cancel confirmation gate。
- Workflow：实现内置 Nodeflow bugfix workflow：clarify / plan / execute / review / verify / handoff。
- Workflow：实现 review / verify 失败回到 execute 的 retry loop。
- Workflow：支持 workflow command / save / replay。
- Benchmark：围绕 Level 1B 失败信号，优先补 create-file/write-file 工具能力或 benchmark mode 参数，用同一组 15 个任务对比 plain Agent Loop 与 Workflow-guided bugfix loop。
- Context Engineering：设计 context budget 和可观察性，至少能展示本轮注入了哪些 context block、是否截断、各 block 字符数，并为后续 memory / workflow context 留出边界。
- Modes：设计 Runtime-level `ModeProfile`，评估 learn / dev / debug / review mode 如何影响 prompt、workflow selection、strategy selection 和 tool policy。
- Multi-agents：Workflow 主干稳定后，先做只读 parallel inspect / review，不并行写文件。

## 阻塞/待确认

- `/workflow TASK` 当前展示 plan 后直接执行，尚未加入 execute / cancel / modify / write in confirmation gate。
- 当前只有内置 `inspect -> handoff` workflow；尚未接 Nodeflow bugfix workflow、retry loop、humancheck、save/replay 或 LLM-generated WorkflowSpec / WorkflowScript。
- `apply_patch` 仍是学习用最小 `path/old/new` 文本替换，不是完整 diff parser。
- `search_files` 仍是最小 UTF-8 文本搜索，不支持 glob/include/exclude、大小写选项或完整 ripgrep wrapper。
- 统一验证命令不作为 CLI flag 处理；后续在 WorkflowRunner 或 hook 机制中重新设计。
- 默认 Gemini 依赖 `.env` 或当前 shell 中的 `GEMINI_API_KEY`；缺少 key 时 runtime 会在启动 adapter 阶段失败并提示缺 key。
- Streaming Outputs 已完成普通 task 的 event streaming 第一刀；Gemini token-level streaming、workflow phase streaming 和 provider delta 聚合尚未实现。
- LLM Council 先从 role-based model routing 进入，不急着做多模型投票。

## 最近验证

- `python -m unittest discover tests`：exit code `0`，130 个测试通过，确认 skill registry context 接入后现有 runtime / workflow / context / safety / TUI / benchmark 测试未回归。
- `python -m unittest tests.test_context tests.test_runtime_session tests.test_agent_loop_streaming`：exit code `0`，15 个测试通过，确认 `<available_skills>` message 注入顺序、runtime initial messages 接线和 Agent Loop streaming 路径正常。
- `python -m py_compile OpenCAI\context.py tests\test_context.py tests\test_runtime_session.py`：exit code `0`，确认 Context 层 skill registry 相关代码和测试语法可编译。
- `python -m unittest discover tests`：exit code `0`，128 个测试通过，确认只读 Skill Tools 接入后现有 runtime / workflow / context / safety / TUI / benchmark 测试未回归。
- `python -m unittest tests.test_skill_tools tests.test_safety tests.test_agent_loop_safety`：exit code `0`，19 个测试通过，确认 `list_skills` / `read_skill` 注册为只读工具，路径边界和既有 SafetyPolicy 行为正常。
- `python -m py_compile OpenCAI\tools.py tests\test_skill_tools.py`：exit code `0`，确认 Skill Tools 实现和测试语法可编译。
- `python -m unittest tests.test_skill_tools`：exit code `0`，4 个测试通过，确认 `list_skills` / `read_skill` 可从 workspace-local skill root 发现和读取 `SKILL.md`，并拒绝 skill name 路径逃逸。
- `python -m unittest discover tests`：exit code `0`，120 个测试通过，确认 ContextComposer 已接入 Agent Loop / Runtime 普通 task 主路径，且现有 runtime / workflow / benchmark / TUI 测试未回归。
- `python -m unittest tests.test_runtime_session tests.test_agent_loop_streaming`：exit code `0`，7 个测试通过，确认 `initial_messages` 可传入 Agent Loop，`run_once()` 会组合 system/project/global/environment/task 初始 messages。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\agent_loop.py tests\test_runtime_session.py tests\test_agent_loop_streaming.py`：exit code `0`，确认 Runtime 接线和 Agent Loop 初始 messages 参数语法可编译。
- `python -m OpenCAI --adapter fake --task "Read README"`：exit code `0`，确认普通 fake task 入口在默认 context 初始化后仍可运行并输出 final answer。
- `python -m unittest discover tests`：exit code `0`，118 个测试通过，确认 Context Engineering 第一刀、`system` role 类型扩展和现有 runtime / workflow / benchmark / TUI 测试未回归。
- `python -m unittest tests.test_context tests.test_llm_adapter`：exit code `0`，5 个测试通过，确认 AGENTS raw instruction 读取、截断、ContextComposer message 顺序和 Gemini system instruction 拆分。
- `python -m py_compile OpenCAI\context.py OpenCAI\llm_adapter.py tests\test_context.py tests\test_llm_adapter.py`：exit code `0`，确认 Context Engineering 与 adapter role 映射相关代码语法可编译。
- `python -m unittest discover tests`：exit code `0`，113 个测试通过，确认 TUI output 标题 bullet 前缀已覆盖普通 task 摘要、runtime command、workflow plan/process、dry-run、过程视图和空 divider 契约。
- `python -m unittest tests.test_tui_streaming tests.test_tui_status_bar tests.test_runtime_commands tests.test_workflow`：exit code `0`，57 个测试通过，确认 submitted task、final answer、runtime status/help、workflow 和 `/process` 标题均使用 `• ` 前缀。
- `python -m py_compile OpenCAI\tui.py OpenCAI\runtime_commands.py OpenCAI\workflow.py OpenCAI\__main__.py OpenCAI\output_format.py tests\test_tui_streaming.py tests\test_tui_status_bar.py tests\test_runtime_commands.py tests\test_workflow.py`：exit code `0`，确认 output title 格式化相关代码和测试语法可编译。
- `python -m OpenCAI --adapter fake --task "Read README"`：exit code `0`，确认普通 task 输出显示 `• Submitted task:` 和 `• Final answer:`。
- `cmd /c "(echo /status&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认 `/status` 输出显示 `• Runtime status`。
- `cmd /c "(echo /workflow Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认 `/workflow` 输出显示 `• Workflow task`、`• Workflow`、`• Workflow status`、`• Workflow final answer` 和 `• Workflow process`。
- `python -m OpenCAI --dry-run --adapter fake --task "Read README"`：exit code `0`，确认 dry-run 输出显示 `• OpenCAI runtime`。
- `python -m unittest discover tests`：exit code `0`，112 个测试通过，确认 TUI output 标题 bullet 前缀、空 divider、过程视图、workflow、runtime command、composer、shell mode、safety 和 benchmark 相关测试未回归。
- `python -m unittest tests.test_tui_streaming`：exit code `0`，16 个测试通过，确认 output 模块标题统一显示 `• ` 前缀，且空分隔线不生成标题。
- `python -m py_compile OpenCAI\tui.py tests\test_tui_streaming.py`：exit code `0`，确认 TUI 标题格式化和相关测试语法可编译。
- `cmd /c "(echo Read README&echo /process&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认非 TTY `/process` 展开后显示 `• Process`、`• 2 Assistant`、`• 3 Tool call` 等模块标题。
- `python -m unittest discover tests`：exit code `0`，111 个测试通过，确认 live process、`Ctrl+O` 过程视图 toggle、`/process` fallback、task 摘要折叠、workflow、runtime command、composer、TUI、shell mode、safety 和 benchmark 相关测试未回归。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\runtime_commands.py tests\test_runtime_session.py tests\test_tui_streaming.py tests\test_tui_status_bar.py`：exit code `0`，确认 live process、process view key binding 和 runtime 接线相关代码语法可编译。
- `rg -n "on_process_shortcut|show_process_view\(|PROCESS_SHORTCUT_COMMAND|c-o|create_task_key_bindings" OpenCAI tests -S`：exit code `0`，确认 composer `Ctrl+O` 只返回 `/process` handoff，`show_process_view()` 只从 runtime command 路径调用。
- `python -m OpenCAI --adapter fake --task "Read README"`：exit code `0`，确认一次性 task 输出 submitted task、final answer 和 `Ctrl+O` / `/process` 折叠提示。
- `cmd /c "(echo Read README&echo /process&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认非 TTY 交互式 task 完成后默认折叠，随后 `/process` 可展开最近一次过程。
- `python -m unittest discover tests`：exit code `0`，102 个测试通过，确认 `/process` 临时过程视图、无彩色分界线、task 摘要折叠、workflow、runtime command、composer、TUI、shell mode、safety 和 benchmark 相关测试未回归。
- `python -m unittest tests.test_runtime_session tests.test_runtime_commands tests.test_composer tests.test_tui_completer tests.test_tui_streaming tests.test_tui_status_bar tests.test_shell_mode tests.test_agent_loop_streaming`：exit code `0`，66 个测试通过，确认 task 摘要、`/process` 临时过程视图、runtime command、composer、TUI 和 shell mode 相关路径未回归。
- `python -m unittest tests.test_tui_streaming tests.test_runtime_commands`：exit code `0`，21 个测试通过，确认 `/process` 使用临时过程视图、非 TTY fallback 和无彩色分界线契约。
- `python -m py_compile OpenCAI\tui.py OpenCAI\runtime_commands.py tests\test_tui_streaming.py tests\test_runtime_commands.py`：exit code `0`，确认 `/process` 临时视图和 divider 样式相关代码语法可编译。
- `cmd /c "(echo Read README&echo /process&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认非 TTY fallback 可展开最近过程且 divider 使用默认终端色。
- `python -m OpenCAI --adapter fake --task "Read README"`：exit code `0`，确认一次性 task 摘要仍只显示 submitted task、final answer 和 process collapsed 提示。
- `python -m unittest discover tests`：exit code `0`，98 个测试通过，确认 task 摘要折叠、`/process` 展开、workflow、runtime command、composer、TUI、shell mode、safety 和 benchmark 相关测试未回归。
- `python -m unittest tests.test_runtime_session tests.test_runtime_commands tests.test_composer tests.test_tui_completer tests.test_tui_streaming tests.test_tui_status_bar tests.test_shell_mode tests.test_agent_loop_streaming`：exit code `0`，62 个测试通过，确认 task 摘要、`/process` 展开、runtime command、composer、TUI 和 shell mode 相关路径未回归。
- `python -m py_compile OpenCAI\tui.py OpenCAI\__main__.py OpenCAI\runtime_commands.py tests\test_tui_streaming.py tests\test_runtime_commands.py tests\test_runtime_session.py`：exit code `0`，确认 TUI 摘要、runtime session 缓存和 `/process` 命令相关代码语法可编译。
- `python -m OpenCAI --adapter fake --task "Read README"`：exit code `0`，确认一次性 task 默认输出 submitted task、final answer 和 process collapsed 提示。
- `cmd /c "(echo Read README&echo /process&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认交互式普通 task 完成后默认折叠，随后 `/process` 可展开最近一次过程。
- `python -m unittest discover tests`：exit code `0`，90 个测试通过，确认 event streaming、workflow、runtime command、composer、TUI、shell mode、safety 和 benchmark 相关测试未回归。
- `python -m py_compile OpenCAI\agent_loop.py OpenCAI\tui.py OpenCAI\__main__.py tests\test_agent_loop_streaming.py tests\test_tui_streaming.py`：exit code `0`，确认 event streaming 相关代码和测试语法可编译。
- `python -m OpenCAI --adapter fake --task "Read README"`：exit code `0`，确认一次性 task 入口可通过 `iter_agent_loop() -> render_event_stream()` 渲染 transcript。
- `python -m unittest discover tests`：exit code `0`，74 个测试通过，确认 benchmark diagnostic contract 未破坏现有 workflow、runtime command、composer、TUI、shell mode 和 safety 测试。
- `python -m py_compile benchmarks\runner.py tests\test_benchmark_runner.py`：exit code `0`，确认 benchmark runner 诊断字段与测试语法可编译。
- `python -m unittest tests.test_benchmark_runner`：exit code `0`，11 个测试通过，确认 task 诊断字段、initial verification、strict changed-files policy、POSIX path normalization、runtime cache ignore 和 result status 契约。
- `python -m benchmarks.runner --task all --timeout 30`：exit code `1`，fake adapter baseline 为 `0/15 passed`；15 个任务均为有效初始失败样本，全部输出 `failed_verification`。
- `python -m benchmarks.runner --task all --adapter gemini --timeout 180`：exit code `1`，最新 Gemini baseline 为 `14/15 passed`；唯一失败项 `level1b_create_slug_module` 创建了 `slug.py` 但未定义 `slugify`，最终验证失败。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，51 个测试通过，确认 statusline 改动未破坏相关路径。
- `python -m unittest tests.test_runtime_commands tests.test_composer tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety tests.test_shell_mode tests.test_tui_status_bar`：exit code `0`，59 个测试通过，确认旧 allow 入口移除、`/permission` 二级选择器、permission profile、status bar 和 Agent Loop deny path 正常。
- `python -m unittest discover tests`：exit code `0`，80 个测试通过，确认 permission profile 改动未破坏现有 workflow、runtime command、composer、TUI、shell mode、safety 和 benchmark 相关测试。
- `python -m OpenCAI --dry-run --adapter fake --task "Read README"`：exit code `0`，确认未显式传 `--permission` 时默认 profile 为 `approve-safe`。
- `cmd /c "(echo /status&echo /exit)|python -m OpenCAI --adapter fake --max-steps 5"`：exit code `0`，确认交互式 runtime 默认显示 `permission: approve-safe`。
- `cmd /c "(echo /status&echo /permission full-access&echo /status&echo /exit)|python -m OpenCAI --adapter fake --max-steps 5"`：exit code `0`，确认非 TTY runtime 可查看并切换 permission profile，状态输出不再包含 `allow_write` / `allow_command`。
- `cmd /c "(echo /status&echo !python -c ""print(246)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认非 TTY runtime command 与 shell mode 仍正常。

## 相关文档

- 当前路线索引：`docs/roadmap.md`。
- 当前执行计划：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- Small-task 产品验收目标：`docs/goals/small-task-coding-agent-competence.md`。
- 核心循环架构：`docs/core-loop-architecture.md`。
- 学习型开发流程：`docs/learning-mode.md`。
- Phase 9 学习日志：`docs/phases/phase-9-tool-completion.md`。
- Phase 10 学习日志：`docs/phases/phase-10-real-toy-repair.md`。
- Phase 12 学习日志：`docs/phases/phase-12-productized-cli.md`。
- Phase 13 设计文档：`docs/phase-13-dynamic-workflows.md`。
