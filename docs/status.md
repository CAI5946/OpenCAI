# 开发状态

## 当前阶段

学习优先路线：Phase 7 Interactive Runtime / TUI Shell 已完成最小收口。

后续路线已确认调整为交互式 CLI + Claude Code 学习对照双轨推进：OpenCAI 继续实现自己的最小 Coding Agent，`claude-code/` 只作为架构和行为参考，不复制实现。

当前 `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认进入交互式输入循环：启动后等待用户输入 task，Runtime 调用当前 Agent Loop，Renderer 渲染 transcript，然后回到输入提示；输入 `exit` / `quit` / `:q` 退出。`--task` 保留为一次性调试路径。默认 adapter 仍是 `fake`；`--adapter gemini` 是 Phase 8 的显式入口，真实 Gemini smoke test 尚未完成。

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
- 已确认后续每个 Phase 先做 Claude Code reference pass，记录 `学到什么 -> OpenCAI 采用什么 -> 暂不采用什么`。
- Phase 7 前已完成一个真实 `GeminiAdapter` 的最小学习切片：新增 adapter 类、保持 API key 注入、不让 Gemini response 结构泄漏到 Agent Loop。
- 已完成 Phase 7 第一刀：将 `python -m OpenCAI` 默认路径改为最小交互式输入循环；`OpenCAI/tui.py` 不再直接调用 Agent Loop，只提供 `ask_task()` 和 transcript renderer；`OpenCAI/__main__.py` 负责输入循环、退出命令、调用 fake loop 和渲染 events。
- 已完成 Phase 7 第二刀：`OpenCAI/__main__.py` 拆出 `RuntimeSession`、`run_once()` 和 `run_interactive()`；当前 session state 只记录 Runtime 层 turn count，不改变 Agent Loop 协议，也不把历史喂给模型。
- 已完成 Phase 7 第三刀：`OpenCAI/tui.py` 的 `ask_task()` 支持自定义 label，`OpenCAI/__main__.py` 使用 `RuntimeSession.turn_count` 在交互提示中显示 `Task 1`、`Task 2` 等 turn 编号；session state 现在可观察，但仍不影响 Agent Loop。
- 已完成 Phase 7 第四刀：`RuntimeSession` 增加 `task_history`，记录当前交互式会话内用户输入过的 tasks；该 history 只保留在 Runtime 内部，暂不传给 `run_once()`、Agent Loop 或 LLM。
- 已同步 Notion 学习日志：`Phase 7` 页面记录 Interactive Runtime / TUI Shell 边界、取舍、验证和下一阶段。
- 已开始 Phase 8 第一刀：`OpenCAI/__main__.py` 增加 `--adapter fake|gemini`，Runtime 可显式选择 fake 或 Gemini adapter；默认仍是 fake。

## 正在做

- Phase 7 已完成最小收口。
- 当前不继续加交互命令；`/history` 暂缓。

## 下一步

- Phase 8：继续验证真实 `GeminiAdapter`，进入真实请求前先核对当前 `google-genai` 官方 function calling 格式，并保持 Agent Loop 不依赖 Gemini response 结构。
- Phase 8 起要明确真实 LLM 只接收 Agent Loop 内部 `messages` + `TOOLS`，不要默认接收 `RuntimeSession.task_history`。
- Phase 9：对照 Claude Code 工具模型，补齐 `search_files`。
- Phase 10：用真实 Gemini 跑通 toy project repair loop。
- Phase 11：加入最小权限层，包括 `--allow-write`、`--allow-command`、cwd/path 边界和危险命令拦截。
- Phase 12：整理交互式 CLI 参数、README 和最小使用说明。

## 阻塞/待确认

- 统一验证命令未确认。
- 真实 `GeminiAdapter` 已有最小类实现，并已接入 Runtime 显式 adapter 选择；但尚未安装 `google-genai` 验证 SDK 对象构造，也尚未真实请求 Gemini。
- Phase 6 当前使用 `FakeRepairLLMAdapter` 脚本式模拟 LLM 决策，不代表真实模型已经能自主修复。
- `apply_patch` 是学习用最小 `path/old/new` 文本替换，不是完整 diff parser。
- `--repair-demo` Runtime 入口本次明确跳过。
- 产品化 CLI 的最终默认 adapter 仍待后续阶段确认：先保持 fake 默认更稳，真实 Gemini 通过显式参数进入。

## 最近验证

- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\agent_loop.py OpenCAI\llm_adapter.py OpenCAI\tools.py`：exit code `0`。
- `python -m OpenCAI --help`：exit code `0`，确认 help 显示 interactive runtime 和 `--adapter fake|gemini`。
- `python -m OpenCAI --dry-run`：exit code `0`，确认 dry-run 显示 task 为 `(interactive)`。
- `python -m OpenCAI --task "Read README"`：exit code `0`，确认一次性 task 路径仍能运行 fake loop 并渲染 transcript。
- `cmd /c "(echo Read README&echo Read README&echo exit)|python -m OpenCAI"`：exit code `0`，确认多轮交互提示显示 `Task 1`、`Task 2`，并在第二轮后显示 `Task 3`。
- `cmd /c "echo Read README|python OpenCAI\tui.py"`：exit code `0`，确认 `ask_task()` 默认 label 仍为 `Task`。

## 当前路线文档

- 当前执行路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
