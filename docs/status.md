# 开发状态

## 当前阶段

学习优先路线：Phase 6 Toy Project Closed Loop 已完成并收口。

后续路线已确认调整为产品化 CLI + Claude Code 学习对照双轨推进：OpenCAI 继续实现自己的最小 Coding Agent，`claude-code/` 只作为架构和行为参考，不复制实现。

当前 `python -m OpenCAI` / `OpenCAI\opencai.cmd` 默认仍运行 Phase 0-5 fake loop，并通过 Rich transcript renderer 展示事件流。Phase 6 闭环通过可注入的 `FakeRepairLLMAdapter` 验证，未新增 `--repair-demo` Runtime 入口。

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
- 已确认后续产品化 CLI 路线：Phase 7-11 依次推进真实 `GeminiAdapter`、工具补齐、真实 toy repair、最小权限层和 CLI 产品化。
- 已确认后续每个 Phase 先做 Claude Code reference pass，记录 `学到什么 -> OpenCAI 采用什么 -> 暂不采用什么`。

## 正在做

- 产品化 CLI + Claude Code 学习对照路线已同步到项目文档。
- 当前不做代码实现，等待后续按 Phase 7 开始分阶段开发。

## 下一步

- Phase 7：先做 Claude Code 主循环 reference pass，再实现真实 `GeminiAdapter`。
- 进入真实 `GeminiAdapter` 前，先核对当前 `google-genai` 官方 function calling 格式。
- 保持 Agent Loop 不依赖 Gemini response 结构。
- Phase 8：对照 Claude Code 工具模型，补齐 `search_files`。
- Phase 9：用真实 Gemini 跑通 toy project repair loop。
- Phase 10：加入最小权限层，包括 `--allow-write`、`--allow-command`、cwd/path 边界和危险命令拦截。
- Phase 11：整理产品化 CLI 参数、README 和最小使用说明。

## 阻塞/待确认

- 统一验证命令未确认。
- 真实 `GeminiAdapter` 尚未实现和验证。
- Phase 6 当前使用 `FakeRepairLLMAdapter` 脚本式模拟 LLM 决策，不代表真实模型已经能自主修复。
- `apply_patch` 是学习用最小 `path/old/new` 文本替换，不是完整 diff parser。
- `--repair-demo` Runtime 入口本次明确跳过。
- 产品化 CLI 的最终默认 adapter 仍待后续阶段确认：先保持 fake 默认更稳，真实 Gemini 通过显式参数进入。

## 最近验证

- `python -m py_compile OpenCAI\agent_loop.py OpenCAI\llm_adapter.py OpenCAI\tools.py`：exit code `0`。
- `run_fake_loop(..., adapter=FakeRepairLLMAdapter(), require_verification=True)`：exit code `0`，事件流包含 `verification failed -> read_file -> apply_patch -> verification passed -> final_answer`。
- `run_fake_loop(..., adapter=BadAdapter(), require_verification=True)`：exit code `0`，确认未验证通过前的 `final_answer` 被拒绝并产出 `error` event。
- `python -m unittest discover examples/toy_project`：exit code `0`，确认 toy project 修复后测试通过。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\agent_loop.py OpenCAI\llm_adapter.py`：exit code `0`。
- `opencai --help`：exit code `0`，确认 help 显示 `Phase 0-5 runtime`。
- `opencai --dry-run --task "Read README"`：exit code `0`，确认 dry-run 输出 `OpenCAI Phase runtime`。
- `opencai --task "Read README"`：exit code `0`，确认默认入口渲染 Phase 0-5 fake loop transcript。
- `cmd /c "echo Read README|python OpenCAI\tui.py"`：exit code `0`，确认 TUI 脚本入口能渲染当前 fake loop transcript。

## 当前路线文档

- 当前执行路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
