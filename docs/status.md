# 开发状态

## 当前状态

OpenCAI 的目标是设计并开发完整成熟的 CLI Coding Agent：读上下文、调工具、改文件、运行验证、继续迭代，并逐步扩展到 workflow runtime、multi-agents、modes、streaming outputs、LLM council 和可审计状态。

当前主线是 Feature A: Workflow。Workflow 的定位已收紧为面向 Coding Agent 的稳定开发流程 runtime，而不是通用流程引擎；固定基础流程用于支持 phase policy、scoped context、验证证据、失败恢复、过程显示和规范化 handoff 等深度优化。最新设计决策已确认 `WorkflowSpec + WorkflowScript` 是 workflow 主表达：Spec 是可审计合同，Script 是结构化受限 IR，只表达 run phase、branch、retry、humancheck、handoff、stop 等 control-plane op，不表达 read/edit/command 等 tool-level op；第一版预留 humancheck 和 preview，但不实现 humancheck 执行流，也不强制 execute/cancel confirmation gate。WorkflowSpec / WorkflowRunner 已完成首个串行 runtime 切片和 `/workflow` CLI 入口；Workflow 子系统已收拢到 `OpenCAI/workflow/` package，`workflow_planner.py` / `workflow_commands.py` / `workflow_clarify.py` 保留为兼容入口；`/workflow TASK` 已从普通 runtime command 中分流为结构化 `WorkflowCommandInput`，并由 `workflow.commands` 承接 workflow command flow；RuntimeSession 已引入 `execution_mode`，支持 `/mode agent|guided|workflow` 和 `Shift+Tab` 在输入框切换，workflow mode 下普通文本会自动进入 Workflow Clarify / Planner / WorkflowRunner；guided mode 当前会复用 `workflow/clarify.py` 的 Clarify gate，将同源 session context summary 提供给 ClarifyAgent，将 `ClarifyResult` 转为 `DemandBrief`，并保存为 `RuntimeSession.pending_guided_review`；Runtime 层处理 pending guided review 的执行、停止或修改反馈，再把确认后的 `<original_user_task>` 和 `<demand_brief>` 注入普通 Agent Loop；`workflow/clarify.py` 已提供 runtime-owned clarify gate，默认最多 8 轮用户澄清，LLM clarify agent 只暴露 read-only repo + public web research tools，可产出带 options 的结构化 `ClarifyQuestion` 和带 `research_notes` / `sources` 的结构化 `ClarifyResult`；`workflow/planner.py` 现在返回 `WorkflowPlan(spec, script)`，并能接收 `ClarifyResult` 作为后续编译输入；WorkflowRunner 已能解释 WorkflowScript IR V1 的 `run_phase` / `handoff` / `stop`，并保留 `runner.run(spec, task)` 兼容路径；当前内置 `inspect_handoff` workflow 是 2 个 phase / 3 个 task 的串行 task graph。

并行产品验收目标是 Small-Task Coding Agent Competence：用本地 micro benchmark 衡量 OpenCAI 在小型代码任务上的实际表现，再用失败分类决定优先补 Workflow、Agent Loop、Tool Model、Context Engineering 还是 Modes。

历史状态和验证记录已归档到 `docs/logs/2026-07-04-status-history.md`。

## 当前能力

- `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认进入交互式 runtime。
- 默认 agent mode 下普通 task 走 Agent Loop；guided mode 下普通 task 先走 Clarify / session-level DemandBrief review gate，再进入 Agent Loop；workflow mode 下普通文本自动走当前内置 `inspect -> handoff` workflow；`/workflow TASK` 保留为显式 workflow 入口。
- `--task` 保留为一次性调试路径。
- 默认 model profile 是 `fake/fake`，不需要 API key；真实 provider 不再内置硬编码 model，必须通过 `/model-add` 或 `.opencai/models.json` 配置后才能使用。
- Agent Loop 正式入口是 `run_agent_loop()`；`run_fake_loop()` 仅保留为兼容 wrapper。
- Agent Loop 已将 `max_steps` 降级为最大模型轮次兜底预算，并支持重复工具调用和连续工具失败 stop reason。
- 工具模型已从单文件 `OpenCAI/tools.py` 拆到 `OpenCAI/tooling/` 分类模块；`OpenCAI.tools` 保留为兼容门面。
- 当前已实现 File、Search、Edit、Command、Planning、Context、Workflow、Web、Skill 等工具分类的一组核心工具；Agent、External/MCP、IDE/LSP 等边界工具仍以 deferred 形式保留。
- SafetyPolicy 已接入工具执行前置检查，默认 permission profile 是 `approve-safe`，支持 `read-only` / `ask-approval` / `approve-safe` / `full-access`。
- TUI 已具备 slash command、`$skill` 显式 skill 调用入口、`!` shell mode、`/model-add` provider/model setup、`/model` 已注册 profile 二级选择、`/model-test`、`/mode agent|guided|workflow`、`/keymap`、prompt history、多行输入、状态栏、执行中 live process、最近一次 task 过程视图和通用 `UserPromptRequest` 选择弹窗；Custom answer 使用 UserPrompt 专用输入视图，不再回落到主任务输入框；`Shift+Tab` 当前切换 execution mode，permission 通过 `/permission` 切换。
- LLM Provider runtime 已支持 `provider/model` model ref、`.opencai/models.json` profile 配置、`.env` API key 写入、动态 model discovery 和 lazy adapter cache；当前 provider 包括 `google`、`openai`、`anthropic`、`ollama`、`deepseek`、`glm`、`openai-compatible`，其中 `google` 使用 `GeminiAdapter`，`openai` / `deepseek` / `glm` / `openai-compatible` 复用 `OpenAICompatibleAdapter`。
- `OpenCAI/demand.py` 已定义 guided / workflow 可复用的 `DemandBrief` 执行合同和 `<demand_brief>` 渲染格式；`ContextComposer.compose(..., demand_brief=...)` 已能在 session context 后、当前 task 前注入 `<original_user_task>` 和 `<demand_brief>`，并要求冲突时保留更限制性的原始约束；`OpenCAI/guided.py` 当前负责 `ClarifyResult -> DemandBrief` 转换、DemandBrief preview 和 pending guided review 的业务规则，RuntimeSession 持有 `pending_guided_review` 状态并负责确认阶段路由。
- 普通 task 路径已支持 event streaming 数据源；Runtime 执行中展示临时 live process，完成后默认折叠，完整过程可通过 `Ctrl+O` 或 `/process` 展开。
- Workflow Planner / Compiler V1 已拆到 `OpenCAI/workflow/planner.py`；当前 `WorkflowPlanningAgent` 输出 `WorkflowPlanDraft`，`LLMWorkflowPlanningAgent` 可通过真实 `LLMAdapter` 生成 planner draft，`python -m OpenCAI.workflow.planner --task "..." --adapter gemini|fake` 可单独测试 planner，不经过 WorkflowRunner；旧 `python -m OpenCAI.workflow_planner ...` 仍作为兼容入口可用；`compile_workflow(task)` 先调用 planner draft，再按 `selected_template` 返回内置 `inspect_handoff` `WorkflowPlan(spec, script)`。
- Workflow Clarify V1 已拆到 `OpenCAI/workflow/clarify.py`；`ClarifyPhaseRunner` 每次只处理一个 clarify question，默认最多 8 轮；`LLMClarifyAgent` 可通过 read-only `read_file` / `list_files` / `glob_files` / `search_files` / `web_search` / `web_fetch` / `web_extract` 检查 repo 和公开网络资料后返回 `ask_question` / `complete` / `blocked` JSON；`ask_question` 支持 2-4 个选项并在 TTY 下通过选择弹窗返回 option value，用户可选择 Stop Clarify 或 Esc/Ctrl+C 取消，取消会 blocked 且不会进入后续执行；fake adapter workflow 路径使用 deterministic clarify，避免非 TTY smoke 卡在交互提问。
- `/workflow TASK` 当前先运行 clarify gate，blocked 时不会进入 planner 或 runner；complete 时把 `ClarifyResult` 传给 `compile_workflow()`。
- WorkflowRunner 当前支持串行 task 执行、task dependency 检查、prompt composition、`TaskResult` 聚合为 `PhaseResult`，并通过 final phase 生成 workflow final answer。
- 本地 benchmark harness 已能复制隔离 workspace、运行初始/最终验证、检查严格 changed-files policy，并输出带诊断状态的 JSON report。
- Context Engineering 已完成 `ContextSnapshot` / `ContextProvider` / `ContextComposer` 第一刀，并已接入 Agent Loop / Runtime 普通 task 主路径；显式 `$skill` 会通过 `invoke_skill` 将 `SKILL.md` 作为 meta message 注入后续模型上下文。

## 已知问题

- TUI command suggestion 已修复方向键移动时修改输入框、`/model` 精确匹配后建议栏消失、`/` 自动补全 `/help` 且难以清除等问题；当前仍有一个未解决交互问题：建议栏首次出现时第一项应默认视觉高亮，但真实 TTY 中初始高亮不显示，按方向键移动后高亮显示正常，且 `Tab` 会接受第一项。这说明候选状态和确认语义基本有效，但 prompt_toolkit completion menu 的初始渲染/刷新路径仍需继续排查；后续修复应优先验证真实终端渲染路径，必要时改为自定义 suggestion renderer，而不是再依赖 `start_completion(select_first=True)`。

## 下一步

- TUI：修复 command suggestion 首次显示时第一项默认视觉高亮缺失的问题，保持输入框不被自动补全，并用真实 TTY replay 或等价渲染测试覆盖初始显示、方向键移动、Tab/Enter 确认和 Esc dismiss。
- Workflow：实现 deterministic `WorkflowDraftCompiler`，把 `WorkflowPlanDraft` 和 `ClarifyResult` 校验、规范化并转换成 `WorkflowPlan`，替代当前按 `selected_template` 直接返回内置 plan 的桥接实现。
- Workflow：实现 dependency-aware `TaskContextComposer` V1：static + dynamic context block、direct dependency detail、transitive dependency compressed、included / omitted 可观察。
- Workflow：收口 phase taxonomy：固定 `clarify / plan / execute / review / verify / handoff`，把 `inspect` 降级为 task kind。
- Workflow：实现 task / phase scoped policy placeholders，先落结构，不做复杂强制执行。
- Workflow：实现内置 Nodeflow-style bugfix workflow：clarify / plan / execute / review / verify / handoff。
- Workflow：实现 review / verify 失败回到 execute 的 retry loop。
- Workflow：支持 workflow command / save / replay。
- Benchmark：围绕 Level 1B 新建文件失败信号，用同一组 15 个任务复测新增 `write_file` / patch grammar 后的 plain Agent Loop，再对比 Workflow-guided bugfix loop。
- Context Engineering：设计 context budget 和可观察性，至少能展示本轮注入了哪些 context block、是否截断、各 block 字符数，并为后续 memory / workflow context 留出边界。
- Modes：完善 guided mode 的 blocked 行为、pending review 可观察性和 `/status` 展示；之后再设计 Runtime-level `ModeProfile`，评估 learn / dev / debug / review mode 如何影响 prompt、workflow selection、strategy selection 和 tool policy。
- LLM Providers：做真实 provider smoke 验证，改进 `/model-add` 长列表搜索和 label 展示，并设计 provider alias；暂缓 model options / effort。
- Multi-agents：Workflow 主干稳定后，先做只读 parallel inspect / review，不并行写文件。

## 最近一次验证

- `python -m py_compile OpenCAI\workflow\__init__.py OpenCAI\workflow\core.py OpenCAI\workflow\clarify.py OpenCAI\workflow\planner.py OpenCAI\workflow\commands.py OpenCAI\workflow\runner.py OpenCAI\workflow_planner.py OpenCAI\workflow_commands.py OpenCAI\workflow_clarify.py`：exit code `0`。
- `python -m unittest tests.test_workflow_clarify`：exit code `0`，7 个测试通过，确认 clarify 默认 8 轮、单问题循环、read-only repo tools、read-only web tools、blocked parser fallback 和结构化结果。
- `python -m unittest tests.test_workflow_package tests.test_workflow_clarify tests.test_workflow_planner tests.test_workflow tests.test_workflow_commands tests.test_runtime_commands tests.test_runtime_session tests.test_tui_status_bar`：exit code `0`，93 个测试通过，确认 workflow package import、clarify、planner、command flow、runtime mode 和 TUI status 未回归。
- `python -m OpenCAI.workflow_planner --task "Read README" --adapter fake`：exit code `0`，确认旧 planner 兼容入口仍可用。
- `python -m OpenCAI.workflow.planner --task "Read README" --adapter fake --json`：exit code `0`，确认 planner 可单独输出 `WorkflowPlanDraft` JSON。
- `cmd /c "(echo /workflow Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认原 `/workflow` runtime 入口未回归。
- `python -m py_compile OpenCAI\runtime_commands.py OpenCAI\tui.py tests\test_runtime_commands.py tests\test_tui_status_bar.py tests\test_tui_completer.py`：exit code `0`。
- `python -m unittest tests.test_runtime_commands tests.test_tui_status_bar tests.test_tui_completer`：exit code `0`，64 个测试通过，确认 `/mode guided`、状态栏、输入标记和 `Shift+Tab` mode 循环。
- `python -m py_compile OpenCAI\demand.py tests\test_demand.py`：exit code `0`。
- `python -m unittest tests.test_demand`：exit code `0`，5 个测试通过，确认 `DemandBrief` 字段清洗、默认 success criteria fallback 和 `<demand_brief>` 渲染。
- `python -m py_compile OpenCAI\context.py OpenCAI\demand.py tests\test_context.py tests\test_demand.py`：exit code `0`。
- `python -m unittest tests.test_context tests.test_runtime_session`：exit code `0`，23 个测试通过，确认 DemandBrief 执行路径会在 refined goal 前保留 `<original_user_task>` 及其限制性约束。
- `python -m py_compile OpenCAI\guided.py OpenCAI\__main__.py OpenCAI\context.py tests\test_guided.py tests\test_runtime_session.py tests\test_context.py`：exit code `0`。
- `python -m py_compile OpenCAI\user_prompt.py OpenCAI\tui.py OpenCAI\workflow\clarify.py OpenCAI\guided.py tests\test_user_prompt.py tests\test_workflow_clarify.py tests\test_guided.py`：exit code `0`。
- `python -m unittest tests.test_user_prompt tests.test_workflow_clarify tests.test_guided tests.test_context tests.test_runtime_session`：exit code `0`，53 个测试通过，确认 UserPrompt cancel、Custom answer 专用输入视图、Clarify cancelled blocked flow、guided review cancel 和 DemandBrief context preservation。
- `python -m unittest tests.test_user_prompt tests.test_guided tests.test_runtime_session tests.test_workflow_clarify tests.test_workflow_commands tests.test_tui_status_bar tests.test_tui_completer`：exit code `0`，87 个测试通过，确认通用 user prompt popup、session-level pending guided review、Clarify 选择题、runtime guided flow 和 TUI status 未回归。
- `cmd /c "(echo /mode guided&echo Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`：exit code `0`，确认 guided mode 在 fake adapter 下 clarify complete、预览 `Guided demand brief` 后进入普通 Agent Loop。
- `python -m unittest discover tests`：exit code `0`，325 个测试通过，确认 Workflow、Runtime、TUI、LLM provider setup、model discovery 和 adapter factory 路径未回归。
- `python -m py_compile OpenCAI\tui.py tests\test_tui_status_bar.py tests\test_tui_completer.py`：exit code `0`。
- `python -m unittest tests.test_tui_completer tests.test_tui_status_bar -v`：exit code `0`，54 个测试通过，确认 command suggestion 方向键不再修改输入框、Tab/Enter 确认当前候选、Esc dismiss 当前建议、`/` 不再自动补全为 `/help`。
- `python -m unittest discover tests`：exit code `0`，334 个测试通过，确认当前 TUI command suggestion 修复未引入全量回归。
