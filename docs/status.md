# 开发状态

## 当前阶段

OpenCAI 的目标已调整为设计并开发完整成熟的 Coding Agent。后续路线继续采用 Feature Epic + 小切片，但小切片只是交付和验证方式，不再代表产品目标只能停留在最小方案。Workflow、Multi-agents、Agent Loop Strategy 是三条主 feature；Modes、Streaming Outputs、LLM Council 是新增候选 feature，按架构影响和依赖逐步评估。

当前主线是 Feature A: Workflow。WorkflowSpec / WorkflowRunner 已完成首个串行 runtime 切片和 `/workflow` CLI 入口；下一步继续补 workflow confirmation gate、命令层拆分和 humancheck 设计。并发、后台 UI、保存/恢复和成本追踪暂不一次性实现，但设计时必须保留成熟 workflow runtime 的扩展边界。

后续 feature 依赖关系：Multi-agents 依赖 Workflow 的 state、dispatcher 和 aggregator；Agent Loop Strategy 属于 benchmark-driven experiment，不应打断 Workflow 主线；Modes 应先作为 Runtime-level `ModeProfile`；Streaming Outputs 需要 event iterator / sink 兼容现有 list-return 路径；LLM Council 应先做 role-based model routing，不急着做投票型 council。

当前 `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认进入交互式输入循环：普通 task 仍走 Agent Loop，`/workflow TASK` 走当前内置 `inspect -> handoff` workflow，展示 workflow plan、执行结果和过程摘要；输入 `/exit` 退出。`--task` 保留为一次性调试路径。默认 adapter 仍是 `fake`；`--adapter gemini` 是显式真实模型入口，已验证真实 Gemini text smoke、`read_file -> function_response -> final_answer`、toy project repair loop 和 `/workflow Read README.md` 路径。Agent Loop 正式入口已改为 `run_agent_loop()`，`run_fake_loop()` 仅保留为兼容 wrapper。

## 已完成

- 已建立学习项目说明。
- 已完善项目级 `AGENTS.md`，加入技术栈、目录结构、命令和状态维护规则。
- 已加入 `.env` + `.gitignore` 配置，启动时会读取项目根目录 `.env`，真实 key 不进入 git。
- 已写入学习优先路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- 已在项目级 `AGENTS.md` 中加入学习优先模式约束。
- 已完成 Phase 0：Component Map 学习，明确 Runtime、Event / Transcript、Tool Model、LLM Adapter、Renderer / TUI、Verification 的职责和边界。
- 已创建用户级 skill `learn-with-dev`，并在 `docs/learning-mode.md` 中记录新对话复用方式。
- 已完成 Phase 1：Event / Transcript Model 学习和最小实现。
- 已新增 `OpenCAI/events.py`，定义最小 event type、公共字段、event helper 和 `mock_transcript()`。
- 已完成 Phase 2：Renderer 学习和最小实现。
- 已改造 `OpenCAI/tui.py`，消费 `OpenCAI/events.py` 的正式 event 协议并渲染 transcript。
- 已完成 Phase 3：Tool Model 学习和最小实现。
- 已新增 `OpenCAI/tools.py`，定义 `ToolSpec`、`ToolCall`、`ToolResult`、四个工具 spec 和 `run_tool()` 入口；当前只真实实现 `read_file`。
- 已更新 `OpenCAI/events.py`，让 `tool_result(...)` 支持保存 `ToolResult.error`，避免工具失败原因在 transcript 中丢失。
- 已完成 Phase 4：Agent Loop 学习和最小实现。
- 已新增 `OpenCAI/agent_loop.py`，定义 `run_fake_loop()` 和 `_format_observation()`。
- Phase 4 当前实现为不接真实 LLM 的 multi-step fake loop：第 1 轮模拟模型选择 `read_file README.md`，工具结果格式化为 message observation 后进入第 2 轮，第 2 轮模拟模型输出 `final_answer`。
- 已明确 Phase 4 的核心边界：Agent Loop 维护 `messages`、`events`、`step` 和停止条件；Tool Model 执行工具；Renderer 消费 events；Runtime 负责启动和配置；LLM Adapter 负责后续真实模型 API 细节。
- 已完成 Phase 5：LLM Adapter 基础边界学习和最小实现。
- 已新增 `OpenCAI/llm_adapter.py`，定义 `Message`、`ModelOutput`、`ProviderToolSchema`、`LLMAdapter`、`LLMAdapterError`、`FakeLLMAdapter`。
- 已实现 `validate_model_output()`，将模型输出限制为内部统一协议：`tool_call` 或 `final_answer`。
- 已实现 `to_provider_tool_schema()` / `to_provider_tool_schemas()`，将内部 `ToolSpec` 转换为 provider-neutral 工具声明；只暴露 `name`、`description`、`parameters`，不暴露本地 `function` 或 `read_only`。
- 已实现 `parse_provider_response()`，将 fake provider response 转换为内部 `ModelOutput`；当前策略为 tool call 优先，普通 text 转为 final answer，异常格式抛出 `LLMAdapterError`。
- 已改造 `FakeLLMAdapter`，让 fake provider response 也走 `parse_provider_response()`，与未来真实 adapter 的响应解析路径保持一致。
- 已改造 `OpenCAI/agent_loop.py`，移除 `_fake_model_decide()`，改为通过可注入的 `LLMAdapter` 获取 `ModelOutput`，并在 adapter 错误时产出 `error` event。
- 已在 `OpenCAI/__main__.py` 增加 `build_adapter()`，把 adapter 选择点放到 Runtime；当前仍返回 `FakeLLMAdapter`，尚未接真实 Gemini。
- 已将 `OpenCAI/__main__.py` 切换为 Phase 0-5 runtime：默认调用 `run_fake_loop()` 并复用 `OpenCAI/tui.py` 的 transcript renderer。
- 已将 `OpenCAI/tui.py` 切换为当前 fake Agent Loop transcript。
- 已完成 Phase 6：Toy Project Closed Loop 核心闭环学习和最小实现。
- 已实现真实 `run_command` 工具，返回 `command`、`exit_code`、`stdout`、`stderr`；`ToolResult.ok` 表示工具是否成功拿到命令结果，不等于命令是否通过。
- 已在 Agent Loop 中将成功的 `run_command` 结果映射为 `verification` event，并将 `run_command` 结果格式化为下一轮 LLM observation。
- 已实现最小 `apply_patch` 工具，使用 `path`、`old`、`new` 对 UTF-8 文件做一次文本替换。
- 已新增 `examples/toy_project/`，包含故意可失败、可修复、可验证的 `calculator.py` 和 `test_calculator.py`。
- 已新增 `FakeRepairLLMAdapter`，固定模拟 `run_command -> read_file -> apply_patch -> run_command -> final_answer` 的 toy repair loop。
- 已在 `run_fake_loop()` 中加入 `require_verification` stop guard：要求验证时，未出现 `verification passed` 前拒绝 `final_answer`。
- 已确认 Phase 6 最小闭环成立：失败测试 -> 读文件 -> 修改文件 -> 再验证 -> 验证通过后才允许结束。
- 已确认后续交互式 CLI 路线：Phase 7 先重学并改造 Runtime / TUI Shell，让 `python -m OpenCAI` 进入用户输入循环；真实 `GeminiAdapter` 后移到 Phase 8，工具补齐、真实 toy repair、最小权限层和 CLI 产品化顺延。
- 已确认后续每个 Phase 以 OpenCAI 自身能力为主线推进；需要参考时只使用公开资料、成熟工程惯例和项目内已有实现。
- Phase 7 前已完成一个真实 `GeminiAdapter` 的最小学习切片：新增 adapter 类、保持 API key 注入、不让 Gemini response 结构泄漏到 Agent Loop。
- 已完成 Phase 7 第一刀：将 `python -m OpenCAI` 默认路径改为最小交互式输入循环；`OpenCAI/tui.py` 不再直接调用 Agent Loop，只提供 `ask_task()` 和 transcript renderer；`OpenCAI/__main__.py` 负责输入循环、退出命令、调用 fake loop 和渲染 events。
- 已完成 Phase 7 第二刀：`OpenCAI/__main__.py` 拆出 `RuntimeSession`、`run_once()` 和 `run_interactive()`；当前 session state 只记录 Runtime 层 turn count，不改变 Agent Loop 协议，也不把历史喂给模型。
- 已完成 Phase 7 第三刀：`OpenCAI/tui.py` 的 `ask_task()` 支持自定义 label，`OpenCAI/__main__.py` 使用 `RuntimeSession.turn_count` 在交互提示中显示 `Task 1`、`Task 2` 等 turn 编号；session state 现在可观察，但仍不影响 Agent Loop。
- 已完成 Phase 7 第四刀：`RuntimeSession` 增加 `task_history`，记录当前交互式会话内用户输入过的 tasks；该 history 只保留在 Runtime 内部，暂不传给 `run_once()`、Agent Loop 或 LLM。
- 已同步 Notion 学习日志：`Phase 7` 页面记录 Interactive Runtime / TUI Shell 边界、取舍、验证和下一阶段。
- 已开始 Phase 8 第一刀：`OpenCAI/__main__.py` 增加 `--adapter fake|gemini`，Runtime 可显式选择 fake 或 Gemini adapter；默认仍是 fake。
- 已安装并验证 `google-genai`，真实 Gemini text smoke 可通过 `--adapter gemini` 运行。
- 已完成 Phase 8 第二刀：`OpenCAI/llm_adapter.py` 的内部 `Message` 支持 provider-neutral tool call / tool result 字段，`GeminiAdapter` 将其翻译为 `types.Part.from_function_call(...)` 和 `types.Part.from_function_response(...)`。
- 已更新 `OpenCAI/agent_loop.py`，模型选择工具后将 assistant tool-call message 写入内部 `messages`，工具执行后将结构化 tool result 写回，保持 Agent Loop 不依赖 Gemini SDK 对象。
- 已确认真实 Gemini 可完成 `read_file -> function_response -> final_answer`。
- 用户已回报真实 Gemini patch smoke passed：Gemini 使用 `run_command`、`read_file`、`apply_patch` 和再次 `run_command` 完成 toy project 修复验证。
- Phase 9 当时目标是补齐 OpenCAI 基础 `search_files`，不扩展复杂 grep/glob、permission 或 UI。
- 已确认学习开发流程调整：Phase 9 起每个 Phase 先定义一个具体问题，做 1-2 个相关项目或模块的 Reference Pass，记录采用项和暂不采用项，再进入最小实现。
- 已完成 Phase 9：Tool Completion。
- 已实现真实 `search_files` 工具，支持 `pattern` 必填、`path` 可选，返回 `matches[{path,line,text}]`、`truncated`、`skipped` 和用于 observation 的 `content` 摘要。
- 已确认 `search_files` 搜不到内容时属于工具成功空结果：`ToolResult.ok=True` 且 `matches=[]`；参数缺失或路径不存在才是工具失败。
- 已确认 `search_files -> read_file` 可通过现有 Agent Loop 串联：Tool Model 执行搜索，Agent Loop 记录 event 并把搜索结果作为 observation 传回下一轮模型决策。
- 已将 Agent Loop 正式入口从 `run_fake_loop()` 调整为 `run_agent_loop()`；`run_fake_loop()` 保留为兼容 wrapper，Runtime 已切到新入口。
- 已将 `max_steps` 截断消息从 `Fake loop stopped: max_steps reached.` 更新为 `Agent loop stopped: max_steps reached.`。
- 已确认 OpenCAI 后续采用“workflow 编排独立于 Agent Loop”的架构边界。
- 已确认后续特色方向：把 Nodeflow 的 `clarify -> plan -> execute -> review -> verification -> handoff` 提炼为 WorkflowRunner 上层编排，而不是写死进 `agent_loop.py`。
- 已完成 Phase 10：Real Toy Repair。
- 已在 Runtime 中加入 `--max-steps`，让真实模型修复闭环可以通过 CLI 获得足够 step budget；默认仍是 `3`，保持既有行为。
- 已由 Codex 当前回合直接验证真实 Gemini repair loop：临时将 toy project 改成失败态，Gemini 依次执行 `run_command -> read_file -> apply_patch -> run_command -> final_answer`，事件流包含 `verification failed` 和 `verification passed`，并将 `examples/toy_project/calculator.py` 修回正确实现。
- 已完成 Phase 11：Minimal Safety Layer。
- 已新增 `OpenCAI/safety.py`，定义 `SafetyPolicy` / `PolicyDecision`，在工具执行前区分模型意图和系统权限。
- 已实现默认拒绝写入和命令执行：`apply_patch` 需要 `--allow-write`，`run_command` 需要 `--allow-command`。
- 已实现文件工具 cwd/path 边界检查：`read_file`、`search_files`、`apply_patch` 的路径会先 resolve，再确认没有逃出工作区。
- 已加入最小危险命令 blocklist；即使开启 `--allow-command`，明显破坏性命令仍会被拒绝。
- 已将 policy 接入 Agent Loop：policy deny 会返回失败 `ToolResult`，并继续进入 transcript / observation，不新增事件类型。
- 已在 Runtime 中加入 `--allow-write` 和 `--allow-command`，权限只在当前进程/interactive session 内有效，不持久化。
- 已同步 Notion 学习日志：`Phase 11` 页面记录 Minimal Safety Layer 边界、接口变化、验证证据和下一阶段。
- 已完成 Phase 12：Productized CLI。
- 已完成最小 Command Registry 和带描述的 slash command completer。
- 已完成 Composer 输入分流和 `!` shell mode：`/` 进入 runtime command，`!cmd` 直接执行用户 shell command，普通文本进入 Agent Loop，空输入不提交。
- 已完成 ComposerState 纯逻辑层，并让 prompt_toolkit completer 复用同一套 suggestion 计算逻辑。
- 已接入 Tab / Enter / Esc / Up / Down 的最小 suggestion key binding。
- 已将 `/model` 从输入栏 inline 参数补全改为二级选择流程；`/model fake` 仍保留为直接命令路径。
- 已完成 README 最小使用说明和 `/help` 描述。
- 已确认产品化 CLI 不公开 `--require-verification`，并移除未生效的 `--verify` 参数；强制验证后续放到 WorkflowRunner 或 hook 机制中设计。
- 已新增 Phase 12 本地学习日志：`docs/phase-12-productized-cli.md`。
- 已同步 Notion 学习日志：`Phase 12` 页面记录 Productized CLI 边界、验证证据、验证 flag 取舍和 Phase 13 下一步。
- 已完成 Phase 13 第一组最小切片：新增 `OpenCAI/workflow.py`，实现 `WorkflowSpec`、`WorkflowPhase`、`WorkflowRun`、`PhaseResult` 和 `SerialWorkflowRunner`。
- 已确认 Phase 13 核心边界：WorkflowRunner 是 control plane，只负责 phase 顺序、depends_on、prompt composition、PhaseResult 和 final phase 收口；真实工具调用仍由 Agent Loop / Tool Model / SafetyPolicy 执行。
- 已新增内置 `inspect -> handoff` workflow factory：`build_inspect_handoff_workflow()`。
- 已新增 `render_workflow_plan()` 和 `render_workflow_process()`，分别用于 workflow plan preview 和完成后的过程摘要。
- 已接入 `/workflow TASK` runtime command：当前会运行内置 `inspect -> handoff` workflow，并输出 plan、`Workflow final answer` 和 phase process summary。
- 已修正 `max_steps` 截断语义：Agent Loop 现在产出 `stop` event，不再伪装成 `final_answer`；WorkflowRunner 遇到 `stop` 会将 phase 判为 failed。
- 已验证 `/workflow Read README.md` 可通过 fake adapter 和 Gemini adapter 运行；Gemini 路径建议使用明确文件名并适当提高 `--max-steps`。
- 已新增开发态版本源 `OpenCAI.__version__ = "0.0.0-dev"`，并接入 `python -m OpenCAI --version`。
- 已新增最小 TUI 状态栏：交互式 prompt bottom toolbar 显示版本号、model、当前目录和 permission；状态栏字段通过 `DEFAULT_STATUS_BAR_ITEMS` 保持后续可配置扩展入口。
- 已完成输入框第一刀优化：交互式 prompt 从 turn 编号 `Task N` 改为轻量 composer 输入区；输入框有上下分界线，状态线贴在输入框下方，placeholder 使用低对比灰色浮层且不挤占光标位置，左侧统一显示 `>` 并按普通输入、`/` runtime command 和 `!` shell mode 变色；statusline 格式为 `<mode> mode · <version> · <model> · <cwd-name> · <permission> · step <N>`。
- 已更新项目目标口径：OpenCAI 不再以“最小可行第一版”为终局，而是以完整成熟 Coding Agent 为目标；后续设计必须区分“单次小切片”和“长期成熟架构”。

## 正在做

- Feature A: Workflow 收口：围绕 `/workflow` 增加 confirmation gate，拆分 workflow command flow，并为后续 humancheck phase 保留清晰边界。

## 下一步

- Feature A / Workflow：补 `/workflow` execute / cancel confirmation gate；再考虑拆出 `workflow_commands.py`，避免 `runtime_commands.py` 继续变重。
- Feature A / Workflow：实现内置 Nodeflow bugfix workflow：clarify / plan / execute / review / verify / handoff。
- Feature A / Workflow：实现 review / verify 失败回到 execute 的 retry loop。
- Feature A / Workflow：支持 workflow command / save / replay。
- Feature A / Workflow：探索 LLM-generated WorkflowSpec / WorkflowScript，执行前必须展示并确认。
- Feature D / Modes：设计 Runtime-level `ModeProfile`，先评估 learn / dev / debug / review mode 如何影响 prompt、workflow selection、strategy selection 和 tool policy。
- Feature E / Streaming Outputs：评估 `EventSink` 或 generator-style Agent Loop，保持现有 list-return 路径兼容。
- Feature B / Multi-agents：Workflow 主干稳定后，先做只读 parallel inspect / review，不并行写文件。
- Feature F / LLM Council：先做 role-based model routing，例如 plan/review 用强模型、execute 用默认模型；暂不做投票型 council。
- Feature C / Agent Loop Strategy：主流程稳定后再抽象最小 strategy 接口，对同一组 benchmark tasks 对比不同 loop strategy 效果。

## 阻塞/待确认

- 统一验证命令不作为 Phase 12 CLI 参数处理；后续在 WorkflowRunner 或 hook 机制中重新设计。
- Phase 6 当前仍保留 `FakeRepairLLMAdapter` 脚本式模拟 LLM 决策；Phase 10 已直接验证真实 Gemini repair loop，Phase 11 已加入最小权限层。
- `apply_patch` 是学习用最小 `path/old/new` 文本替换，不是完整 diff parser。
- `--repair-demo` Runtime 入口本次明确跳过。
- 产品化 CLI 的最终默认 adapter 仍待后续切片确认：先保持 fake 默认更稳，真实 Gemini 通过显式参数进入。
- `search_files` 目前是最小 UTF-8 文本搜索，不支持 glob/include/exclude、大小写选项或完整 ripgrep wrapper。
- `/workflow TASK` 当前会在展示 plan 后直接执行，尚未加入 execute / cancel / modify / write in confirmation gate。
- 当前只有内置 `inspect -> handoff` workflow；尚未接 NodeFlow bugfix workflow、retry loop、humancheck、save/replay 或 LLM-generated WorkflowSpec / WorkflowScript。
- Workflow 过程摘要是完成后渲染，不是实时 phase progress renderer，也没有折叠 UI。
- Dynamic Workflows 当前只落地串行 runtime 切片；后台任务、暂停恢复、并发 subagents、持久化和成本追踪暂不一次性实现，但不能在架构上排除。
- 多架构实验现在归入 Feature C: Agent Loop Strategy；当前不提前引入 strategy 抽象，避免打断 Workflow 主线。
- Modes 会改变 Runtime 到 Workflow / Agent Loop 的配置注入方式，但不应把 mode-specific 分支直接写进 `agent_loop.py`。
- Streaming Outputs 会改变 Agent Loop / WorkflowRunner / Renderer 的事件交付方式；需要保留当前 `list[Event]` 测试路径。
- LLM Council 会把当前单 adapter runtime 扩展成 model registry / adapter pool；先从 role-based routing 进入，后续再评估 council voting / critique，避免早期多模型投票噪声。

## 最近验证

- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\agent_loop.py OpenCAI\llm_adapter.py OpenCAI\tools.py`：exit code `0`。
- `python -m OpenCAI --help`：exit code `0`，确认 help 显示 interactive runtime 和 `--adapter fake|gemini`。
- `python -m OpenCAI --dry-run`：exit code `0`，确认 dry-run 显示 task 为 `(interactive)`。
- `python -m OpenCAI --task "Read README"`：exit code `0`，确认一次性 task 路径仍能运行 fake loop 并渲染 transcript。
- `python -m OpenCAI --adapter gemini --task "Reply with exactly: Gemini adapter smoke ok. Do not call tools."`：exit code `0`，确认真实 Gemini text response 可解析为 `final_answer`。
- `python -m OpenCAI --adapter gemini --task "Use the read_file tool to read README.md, then summarize the project in exactly one short sentence."`：exit code `0`，确认真实 Gemini `function_call -> function_response -> final_answer` 工具闭环可运行。
- 用户回报 `python -m OpenCAI --adapter gemini --task "...run unittest, read calculator.py, apply_patch, rerun unittest..."` patch smoke passed；具体终端输出未由 Codex 当前回合直接捕获。
- `cmd /c "(echo Read README&echo Read README&echo /exit)|python -m OpenCAI"`：exit code `0`，确认多轮交互提示显示 `Task 1`、`Task 2`，并在第二轮后显示 `Task 3`。
- `cmd /c "echo Read README|python OpenCAI\tui.py"`：exit code `0`，确认 `ask_task()` 默认 label 仍为 `Task`。
- `2026-06-26`：开始仓库定位同步，目标为 repo 命名 OpenCAI、取消追踪外部参考快照和历史输出、保留 OpenCAI core/docs/examples。
- `python -m py_compile OpenCAI\agent_loop.py OpenCAI\__main__.py OpenCAI\tools.py`：exit code `0`。
- `python -m OpenCAI --task "Read README"`：exit code `0`，确认 Runtime 调用 `run_agent_loop()` 后一次性 task 路径仍正常。
- 直接调用 `search_files({"pattern": "OpenCAI", "path": "README.md"})`：`ok=True`，返回 5 条匹配。
- 直接调用 `search_files({"pattern": "OpenCAI", "path": "missing-dir"})`：`ok=False`，返回路径错误。
- 临时内联 adapter 验证 `search_files -> read_file -> final_answer`：exit code `0`，确认搜索结果可进入 Agent Loop observation 并驱动下一轮工具调用。
- 历史强制 `max_steps=1` 曾返回 `final_answer`；Phase 13 已修正为 `stop` event。
- `python -m py_compile OpenCAI\__main__.py`：exit code `0`，确认 Runtime 新增 `--max-steps` 后语法可编译。
- `python -m OpenCAI --dry-run --max-steps 8`：exit code `0`，确认 dry-run 显示 `max_steps: 8`。
- 临时失败态下运行 `python -m unittest discover examples/toy_project`：exit code `1`，确认 toy project 可复现 `AssertionError: -1 != 3`。
- `python -m OpenCAI --adapter gemini --max-steps 8 --task "Fix the failing unittest in examples/toy_project. First run: python -m unittest discover examples/toy_project. Then inspect the relevant file with read_file or search_files, apply the smallest patch, rerun the same unittest command, and only give a final answer after the unittest passes."`：exit code `0`，事件流为 `verification failed -> read_file -> apply_patch -> verification passed -> final_answer`。
- `python -m unittest discover examples/toy_project`：exit code `0`，确认 toy project 修复后测试通过。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\agent_loop.py OpenCAI\safety.py tests\test_safety.py tests\test_agent_loop_safety.py`：exit code `0`。
- `python -m unittest tests.test_safety tests.test_agent_loop_safety`：exit code `0`，确认 policy 规则和 Agent Loop 拒绝/允许路径。
- `python -m OpenCAI --dry-run --allow-command --allow-write --max-steps 8`：exit code `0`，确认 Runtime 可解析并显示权限状态。
- `python -m OpenCAI --help`：exit code `0`，确认 CLI 暴露 `--allow-write` 和 `--allow-command`。
- `python -m OpenCAI --task "Read README"`：exit code `0`，确认默认安全策略下只读工具仍可运行。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\runtime_commands.py tests\test_runtime_commands.py tests\test_tui_completer.py`：exit code `0`，确认 TUI command registry 和 completer 语法可编译。
- `python -m unittest tests.test_runtime_commands tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety`：exit code `0`，15 个测试通过，确认 slash command 抽取、completer、policy 现有行为正常。
- `cmd /c "(echo /status&echo /max-steps 5&echo /status&echo /exit)|python -m OpenCAI"`：exit code `0`，确认交互式 runtime command 路径仍可运行。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\composer.py OpenCAI\shell_mode.py OpenCAI\safety.py OpenCAI\events.py tests\test_composer.py tests\test_shell_mode.py`：exit code `0`，确认 Composer 和 shell mode 语法可编译。
- `python -m unittest tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety`：exit code `0`，21 个测试通过，确认输入分流、用户 shell command、slash command 和安全策略正常。
- `cmd /c "(echo !python -c ""print(456)""&echo !git reset --hard&echo /exit)|python -m OpenCAI"`：exit code `0`，确认 `!` shell mode 可执行普通命令并拦截危险命令。
- `python -m py_compile OpenCAI\composer.py tests\test_composer.py`：exit code `0`，确认 ComposerState 纯逻辑层语法可编译。
- `python -m unittest tests.test_composer`：exit code `0`，11 个测试通过，确认 slash suggestions、choice suggestions、accept/dismiss/submit 行为。
- `python -m unittest tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety`：exit code `0`，28 个测试通过，确认 ComposerState 没有破坏现有输入、shell、command 和 safety 路径。
- `cmd /c "(echo /status&echo !python -c ""print(789)""&echo /exit)|python -m OpenCAI"`：exit code `0`，确认 runtime command 与 shell mode 仍可在交互循环中连续运行。
- `python -m py_compile OpenCAI\tui.py tests\test_tui_completer.py`：exit code `0`，确认 TUI completer 复用 Composer suggestions 后语法可编译。
- `python -m unittest tests.test_tui_completer tests.test_composer`：exit code `0`，15 个测试通过，确认 TUI completer 和 Composer suggestion 逻辑一致。
- `python -m unittest tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety`：exit code `0`，29 个测试通过，确认 completer 改动未破坏输入分流、shell mode、runtime command 和 safety 路径。
- `cmd /c "(echo /status&echo !python -c ""print(101)""&echo /exit)|python -m OpenCAI"`：exit code `0`，确认交互 runtime command 与 shell mode 仍正常。
- `python -m py_compile OpenCAI\tui.py tests\test_tui_completer.py`：exit code `0`，确认 Tab key binding 接入后语法可编译。
- `python -m unittest tests.test_tui_completer tests.test_composer`：exit code `0`，18 个测试通过，确认 Tab 接受 command/choice suggestion 的文本行为。
- `python -m unittest tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety`：exit code `0`，32 个测试通过，确认 Tab key binding 未破坏输入分流、shell mode、runtime command 和 safety 路径。
- `cmd /c "(echo /status&echo !python -c ""print(202)""&echo /exit)|python -m OpenCAI"`：exit code `0`，确认非交互 stdin 路径仍正常。
- `python -m py_compile OpenCAI\tui.py tests\test_tui_completer.py`：exit code `0`，确认 Enter/Esc/Up/Down key binding 接入后语法可编译。
- `python -m unittest tests.test_tui_completer tests.test_composer`：exit code `0`，19 个测试通过，确认 TUI suggestion 判断和 Composer 逻辑正常。
- `python -m unittest tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety`：exit code `0`，33 个测试通过，确认新增按键绑定未破坏输入分流、shell mode、runtime command 和 safety 路径。
- `cmd /c "(echo /status&echo !python -c ""print(303)""&echo /exit)|python -m OpenCAI"`：exit code `0`，确认非 TTY 交互路径仍正常。
- `python -m py_compile OpenCAI\runtime_commands.py OpenCAI\composer.py OpenCAI\tui.py OpenCAI\__main__.py tests\test_runtime_commands.py tests\test_composer.py tests\test_tui_completer.py`：exit code `0`，确认 `/model` 二级选择改动后相关文件语法可编译。
- `python -m unittest tests.test_runtime_commands tests.test_composer tests.test_tui_completer tests.test_shell_mode tests.test_safety tests.test_agent_loop_safety`：exit code `0`，36 个测试通过，确认 `/model` 不再 inline 补全 adapter choices，`/allow-*` 仍支持 inline on/off。
- `cmd /c "(echo /model&echo fake&echo /status&echo /exit)|python -m OpenCAI"`：exit code `0`，确认 `/model` 会进入 `Model (fake/gemini):` 二级选择，选择结果更新 runtime session。
- `python -m py_compile OpenCAI\runtime_commands.py tests\test_runtime_commands.py`：exit code `0`，确认 runtime help 增强后语法可编译。
- `python -m unittest tests.test_runtime_commands tests.test_composer tests.test_tui_completer tests.test_shell_mode tests.test_safety tests.test_agent_loop_safety`：exit code `0`，37 个测试通过，确认 `/help` 描述、`/exit` 和现有输入分流正常。
- `cmd /c "(echo /help&echo /exit)|python -m OpenCAI"`：exit code `0`，确认 `/help` 显示 runtime commands、普通文本输入和 `!command` 输入模式。
- `cmd /c "(echo /status&echo /exit)|python -m OpenCAI"`：exit code `0`，确认当前退出语义为 `/exit`。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\runtime_commands.py OpenCAI\composer.py OpenCAI\tui.py`：exit code `0`，确认移除无效 `--verify` 后 CLI 相关文件仍可编译。
- `python -m unittest tests.test_runtime_commands tests.test_composer tests.test_tui_completer tests.test_shell_mode tests.test_safety tests.test_agent_loop_safety`：exit code `0`，确认 37 个测试通过。
- `python -m OpenCAI --help`：exit code `0`，确认 help 不再显示无效 `--verify` 参数。
- `python -m OpenCAI --dry-run --max-steps 4`：exit code `0`，确认 dry-run 不再显示未使用的 verify 字段。
- `cmd /c "(echo /help&echo /status&echo /exit)|python -m OpenCAI"`：exit code `0`，确认 Phase 12 收口后交互式 help/status/exit 路径仍正常。
- `python -m py_compile OpenCAI\events.py OpenCAI\agent_loop.py OpenCAI\workflow.py OpenCAI\tui.py tests\test_agent_loop_safety.py tests\test_workflow.py`：exit code `0`，确认 `stop` event、WorkflowRunner 和 TUI 渲染语法可编译。
- `python -m unittest tests.test_workflow tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_tui_completer tests.test_safety tests.test_agent_loop_safety`：exit code `0`，51 个相关测试通过。
- `cmd /c "(echo /workflow Read README.md&echo /exit)|python -m OpenCAI"`：exit code `0`，确认 fake adapter 下 `/workflow` 可显示 plan、执行内置 workflow、输出 final answer 和过程摘要。
- `python -m OpenCAI --task "Read README.md" --max-steps 1`：exit code `0`，确认 max_steps 截断现在渲染为 `Stop` event。
- `cmd /c "(echo /workflow Read README.md&echo /exit)|python -m OpenCAI --adapter gemini --max-steps 6"`：exit code `0`，确认 Gemini adapter 可运行内置 workflow 并生成 README.md 摘要。
- `python -m py_compile OpenCAI\__init__.py OpenCAI\tui.py OpenCAI\__main__.py tests\test_tui_status_bar.py`：exit code `0`，确认版本源、状态栏和 Runtime 接入语法可编译。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_runtime_commands tests.test_composer tests.test_shell_mode tests.test_safety tests.test_agent_loop_safety`：exit code `0`，44 个测试通过，确认状态栏、输入补全、runtime command、shell mode 和 safety 路径正常。
- `python -m OpenCAI --version`：exit code `0`，输出 `OpenCAI 0.0.0-dev`。
- `cmd /c "(echo /status&echo /exit)|python -m OpenCAI"`：exit code `0`，确认非 TTY 交互 runtime command 路径仍正常。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py tests\test_tui_status_bar.py tests\test_tui_completer.py`：exit code `0`，确认输入框分界线、placeholder 和状态栏改动语法可编译。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，45 个测试通过，确认输入框、补全、composer、runtime command、shell mode 和 safety 路径正常。
- `cmd /c "(echo /status&echo !python -c ""print(321)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认 runtime command 与 shell mode 连续运行正常。
- `cmd /c "(echo Read README.md&echo /exit)|python -m OpenCAI --max-steps 2"`：exit code `0`，确认普通 task 路径在新 prompt label 下仍正常。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer`：exit code `0`，28 个测试通过，确认输入框左侧 label 为空、上下分界线 helper 和 placeholder 契约正常。
- `cmd /c "(echo /status&echo !python -c ""print(654)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认非 TTY prompt 不再显示 `OpenCAI`。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py tests\test_tui_status_bar.py tests\test_tui_completer.py`：exit code `0`，确认自定义输入布局语法可编译。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer`：exit code `0`，29 个测试通过，确认 statusline 不再依赖窗口级 bottom toolbar，普通/command/shell marker 规则正常。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，48 个测试通过，确认输入框改动未破坏补全、composer、runtime command、shell mode 和 safety 路径。
- `cmd /c "(echo /status&echo !python -c ""print(987)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认非 TTY runtime command 与 shell mode 连续运行正常。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer`：exit code `0`，30 个测试通过，确认自定义输入布局可通过 Enter 提交。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，49 个测试通过，确认输入框布局测试加入后相关路径仍正常。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py tests\test_tui_status_bar.py tests\test_tui_completer.py`：exit code `0`，确认输入 marker 和 mode status 改动语法可编译。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer`：exit code `0`，32 个测试通过，确认左侧 marker 统一为 `>`，并通过颜色和 statusline mode 区分 task / command / shell。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，51 个测试通过，确认 marker 改动未破坏补全、composer、runtime command、shell mode 和 safety 路径。
- `cmd /c "(echo /status&echo !python -c ""print(432)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认非 TTY runtime command 与 shell mode 仍正常。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py tests\test_tui_status_bar.py tests\test_tui_completer.py`：exit code `0`，确认 placeholder 浮层和新增输入框下分界线语法可编译。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer`：exit code `0`，32 个测试通过，确认输入框布局、statusline、marker 和 Enter 提交路径正常。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，51 个测试通过，确认 placeholder/layout 改动未破坏补全、composer、runtime command、shell mode 和 safety 路径。
- `cmd /c "(echo /status&echo !python -c ""print(765)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认非 TTY runtime command 与 shell mode 仍正常。
- `cmd /c "(echo Read README.md&echo /exit)|python -m OpenCAI --max-steps 2"`：exit code `0`，确认普通 task 路径仍正常。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py tests\test_tui_status_bar.py tests\test_tui_completer.py`：exit code `0`，确认压缩 statusline 格式改动语法可编译。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer`：exit code `0`，32 个测试通过，确认 statusline 格式为 `<mode> mode · <version> · <model> · <cwd-name> · <permission> · step <N>`。
- `python -m unittest tests.test_tui_status_bar tests.test_tui_completer tests.test_composer tests.test_shell_mode tests.test_runtime_commands tests.test_safety tests.test_agent_loop_safety`：exit code `0`，51 个测试通过，确认 statusline 改动未破坏相关路径。
- `cmd /c "(echo /status&echo !python -c ""print(246)""&echo /exit)|python -m OpenCAI --max-steps 5"`：exit code `0`，确认非 TTY runtime command 与 shell mode 仍正常。

## 当前路线文档

- 当前执行路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`，已改为 Feature Epic + 小切片。
- Phase 9 学习日志：`docs/phase-9-tool-completion.md`。
- Phase 10 学习日志：`docs/phase-10-real-toy-repair.md`。
- Phase 12 学习日志：`docs/phase-12-productized-cli.md`。
- Phase 13 设计文档：`docs/phase-13-dynamic-workflows.md`。
- Phase 12 Notion 学习日志：https://app.notion.com/p/38d1f9a0b01281a994cbc9240e07a88e。
