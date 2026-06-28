# 开发状态

## 当前阶段

OpenCAI 路线：Phase 11 Minimal Safety Layer 已完成最小权限层；下一步进入 Phase 12 Productized CLI，整理交互式 CLI 参数、README 和最小使用说明。

后续路线已确认调整为“单 Agent core + OpenCAI Dynamic Workflows”：Phase 9-12 继续完成最小 Coding Agent core，Phase 13 起探索 WorkflowSpec / WorkflowRunner、Nodeflow-style workflow、失败重试和后续 subagent 编排。

潜在实验方向：主流程完成后可加入 `AgentLoopStrategy` 实验阶段，在不替换 Runtime、LLMAdapter、Tool Model、Event / Transcript 和 Verification 协议的前提下，对比 ReAct、Plan-and-Execute、Verify-first、Review-retry 和 WorkflowRunner 等 loop strategy。

当前 `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认进入交互式输入循环：启动后等待用户输入 task，Runtime 调用当前 Agent Loop，Renderer 渲染 transcript，然后回到输入提示；输入 `exit` / `quit` / `:q` 退出。`--task` 保留为一次性调试路径。默认 adapter 仍是 `fake`；`--adapter gemini` 是显式真实模型入口，已验证真实 Gemini text smoke、`read_file -> function_response -> final_answer` 和 toy project repair loop。Agent Loop 正式入口已改为 `run_agent_loop()`，`run_fake_loop()` 仅保留为兼容 wrapper。

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
- Phase 9 当前目标是补齐 OpenCAI 最小 `search_files`，不扩展复杂 grep/glob、permission 或 UI。
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

## 正在做

- Phase 12 准备：整理产品化 CLI 参数、README 和最小使用说明。
- TUI 优化路线已转向参考 Claude Code / Codex 的 Composer + Command Registry + Suggestion Popup 结构；当前已完成最小 Command Registry 和带描述的 slash command completer。
- 已完成最小 Composer 输入分流和 `!` shell mode：`/` 进入 runtime command，`!cmd` 直接执行用户 shell command，普通文本进入 Agent Loop，空输入不提交。
- 已完成 ComposerState 纯逻辑层：支持根据输入实时生成 slash suggestions、选择上一项/下一项、接受 suggestion、关闭 suggestions，并复用输入分类提交。
- 已将 prompt_toolkit 的真实 completer 改为复用 `composer.build_suggestions()`，让 TUI 菜单和 ComposerState 使用同一套 suggestion 计算逻辑；自定义 Tab/Esc/Up/Down key binding 仍未接入。
- 已接入最小 Tab key binding：Tab 会优先调用 ComposerState 接受当前 suggestion；没有 Composer suggestion 时回退 prompt_toolkit 默认 completion cycling。Esc/Up/Down/Enter 自定义行为仍未接入。
- 已接入 Enter/Esc/Up/Down 的最小 suggestion key binding：仅在 Composer suggestions 存在时生效；Enter 接受 suggestion，Esc 关闭 completion，Up/Down 切换 completion，普通输入保留 prompt_toolkit 默认行为。
- 已将 `/model` 从输入栏 inline 参数补全改为二级选择流程：主输入框只补全 `/model` command，按 Enter 后由 TUI choice prompt 选择 `fake` 或 `gemini`；`/model fake` 仍保留为直接命令路径。
- 当前不继续加交互命令；`/history` 暂缓。

## 下一步

- Phase 12：整理交互式 CLI 参数、README 和最小使用说明。
- Phase 13：实现最小 `WorkflowSpec` / `WorkflowRunner`，先串行执行 phase。
- Phase 14：实现内置 Nodeflow bugfix workflow：clarify / plan / execute / review / verify / handoff。
- Phase 15：实现 review / verify 失败回到 execute 的最小 retry loop。
- Phase 16：支持 workflow command / save / replay。
- Phase 17：探索 LLM-generated workflow spec。
- Phase 18：探索 parallel subagents。
- 潜在 Phase 19：Agent Loop Strategy Experiments；主流程完成后再抽象最小 strategy 接口，对同一组 benchmark tasks 对比不同 loop strategy 效果。

## 阻塞/待确认

- 统一验证命令未确认。
- Phase 6 当前仍保留 `FakeRepairLLMAdapter` 脚本式模拟 LLM 决策；Phase 10 已直接验证真实 Gemini repair loop，Phase 11 已加入最小权限层。
- `apply_patch` 是学习用最小 `path/old/new` 文本替换，不是完整 diff parser。
- `--repair-demo` Runtime 入口本次明确跳过。
- 产品化 CLI 的最终默认 adapter 仍待后续阶段确认：先保持 fake 默认更稳，真实 Gemini 通过显式参数进入。
- `search_files` 目前是最小 UTF-8 文本搜索，不支持 glob/include/exclude、大小写选项或完整 ripgrep wrapper。
- `max_steps` 截断当前仍以 `final_answer` event 表达，语义上更像 stop/error event，后续可在事件模型中细化。
- Dynamic Workflows 目前只是路线决策，尚未实现；第一版不做 JS runtime、不做后台任务、不做并发 subagents。
- 多架构实验只作为主流程后的潜在 Phase；当前不提前引入 strategy 抽象，避免打断 Phase 11-18 的产品化和 workflow 主线。

## 最近验证

- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\agent_loop.py OpenCAI\llm_adapter.py OpenCAI\tools.py`：exit code `0`。
- `python -m OpenCAI --help`：exit code `0`，确认 help 显示 interactive runtime 和 `--adapter fake|gemini`。
- `python -m OpenCAI --dry-run`：exit code `0`，确认 dry-run 显示 task 为 `(interactive)`。
- `python -m OpenCAI --task "Read README"`：exit code `0`，确认一次性 task 路径仍能运行 fake loop 并渲染 transcript。
- `python -m OpenCAI --adapter gemini --task "Reply with exactly: Gemini adapter smoke ok. Do not call tools."`：exit code `0`，确认真实 Gemini text response 可解析为 `final_answer`。
- `python -m OpenCAI --adapter gemini --task "Use the read_file tool to read README.md, then summarize the project in exactly one short sentence."`：exit code `0`，确认真实 Gemini `function_call -> function_response -> final_answer` 工具闭环可运行。
- 用户回报 `python -m OpenCAI --adapter gemini --task "...run unittest, read calculator.py, apply_patch, rerun unittest..."` patch smoke passed；具体终端输出未由 Codex 当前回合直接捕获。
- `cmd /c "(echo Read README&echo Read README&echo exit)|python -m OpenCAI"`：exit code `0`，确认多轮交互提示显示 `Task 1`、`Task 2`，并在第二轮后显示 `Task 3`。
- `cmd /c "echo Read README|python OpenCAI\tui.py"`：exit code `0`，确认 `ask_task()` 默认 label 仍为 `Task`。
- `2026-06-26`：开始仓库定位同步，目标为 repo 命名 OpenCAI、取消追踪外部参考快照和历史输出、保留 OpenCAI core/docs/examples。
- `python -m py_compile OpenCAI\agent_loop.py OpenCAI\__main__.py OpenCAI\tools.py`：exit code `0`。
- `python -m OpenCAI --task "Read README"`：exit code `0`，确认 Runtime 调用 `run_agent_loop()` 后一次性 task 路径仍正常。
- 直接调用 `search_files({"pattern": "OpenCAI", "path": "README.md"})`：`ok=True`，返回 5 条匹配。
- 直接调用 `search_files({"pattern": "OpenCAI", "path": "missing-dir"})`：`ok=False`，返回路径错误。
- 临时内联 adapter 验证 `search_files -> read_file -> final_answer`：exit code `0`，确认搜索结果可进入 Agent Loop observation 并驱动下一轮工具调用。
- 强制 `max_steps=1`：最后 event 为 `final_answer`，message 为 `Agent loop stopped: max_steps reached.`。
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

## 当前路线文档

- 当前执行路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- Phase 9 学习日志：`docs/phase-9-tool-completion.md`。
- Phase 10 学习日志：`docs/phase-10-real-toy-repair.md`。
