# 开发状态

## 当前阶段

学习优先路线：Phase 5 LLM Adapter 基础边界已完成，准备进入真实 Gemini Adapter 设计/实现。

旧 Stage 1 最小 Agent Loop 暂停。当前不继续直接实现 Gemini 工具调用循环，先按学习优先路线推进组件理解。

旧 Stage 0：观察式 TUI 已存在，并已完成一次命令行验证，作为早期实验保留。

## 已完成

- 已建立学习项目说明。
- 已写入 `docs/claude-code-dev-workflow-plan.md`。
- 已完善项目级 `AGENTS.md`，加入技术栈、目录结构、命令占位和状态维护规则。
- 已实现 `OpenCAI/tui.py` 的 Stage 0 mock transcript 渲染。
- 已确认 Stage 0 可运行：`cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"` exit code 为 `0`。
- 已写入 Stage 1 最小执行计划：`docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`。
- 已完成 Stage 1 Task 1 启动骨架：`python -m OpenCAI` / `OpenCAI\opencai.cmd`、`GEMINI_API_KEY` 缺失提示、`OpenCAI/requirements.txt`。
- 已加入 `.env` + `.gitignore` 配置，启动时会读取项目根目录 `.env`，真实 key 不进入 git。
- 已写入学习优先路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- 已在项目级 `AGENTS.md` 中加入学习优先模式约束。
- 已完成 Phase 0：Component Map 学习，明确 Runtime、Event / Transcript、Tool Model、LLM Adapter、Renderer / TUI、Verification 的职责和边界。
- 已将 Phase 0 学习总结写入 Notion 学习日志 `Stage 0`。
- 已创建用户级 skill `learn-with-dev`，并在 `docs/learning-mode.md` 中记录新对话复用方式。
- 已完成 Phase 1：Event / Transcript Model 学习和最小实现。
- 已新增 `OpenCAI/events.py`，定义最小 event type、公共字段、event helper 和 `mock_transcript()`。
- 已完成 Phase 2：Renderer 学习和最小实现。
- 已改造 `OpenCAI/tui.py`，删除旧 mock event 格式，改为消费 `OpenCAI/events.py` 的正式 event 协议并渲染 transcript。
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

## 正在做

- Phase 5 收口：准备确认是否进入真实 `GeminiAdapter`。

## 下一步

- 先讲清真实 `GeminiAdapter` 的最小职责：读取 Runtime 传入的 API key、把 `Message` / `ToolSpec` 转成 Gemini 请求、把 Gemini response 转成 `ModelOutput`。
- 实现前先核对当前 Gemini SDK/API 的官方 function calling 格式。
- 保持 Agent Loop 不依赖 Gemini response 结构。

## 阻塞/待确认

- 统一验证命令未确认。
- 真实 `GeminiAdapter` 尚未实现和验证。
- Stage 1 依赖尚未完整安装或验证；在学习优先路线下暂不阻塞 Phase 5 基础边界。

## 最近验证

- `cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"`：exit code `0`。
- `python -m OpenCAI --help`：exit code `0`。
- `OpenCAI\opencai.cmd --help`：exit code `0`。
- `python -m OpenCAI --dry-run --task "Fix the failing toy project test" --cwd . --verify "python -m unittest discover ."`：exit code `0`。
- `$env:GEMINI_API_KEY=$null; python -m OpenCAI`：exit code `2`，按预期提示缺少 `GEMINI_API_KEY` 且未发送请求。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\__init__.py OpenCAI\tui.py`：exit code `0`。
- `git check-ignore -v .env`：exit code `0`，确认 `.env` 被 `.gitignore` 忽略。
- `python -m py_compile OpenCAI\events.py`：exit code `0`。
- `python -c "from OpenCAI.events import mock_transcript; ..."`：exit code `0`，确认 mock transcript 包含 6 个事件，且 verification 以 `exit_code=1` 表达 `ok=false`。
- `python -m py_compile OpenCAI\tui.py`：exit code `0`。
- `cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"`：exit code `0`，确认 TUI 能渲染 `events.py` 里的正式 event transcript。
- `python -m py_compile OpenCAI\tools.py`：exit code `0`。
- `python -c "from pathlib import Path; from OpenCAI.tools import run_tool; ..."`：exit code `0`，确认 `read_file` 成功读取 `README.md`，并能对缺失文件返回 `ok=false` 的结构化错误。
- `python -m py_compile OpenCAI\events.py OpenCAI\tools.py`：exit code `0`。
- `python -c "from OpenCAI.events import tool_result; ..."`：exit code `0`，确认 `tool_result` event 能保存 `error` 字段。
- `python -m py_compile OpenCAI\agent_loop.py`：exit code `0`。
- `python -c "from OpenCAI.agent_loop import run_fake_loop; events = run_fake_loop('Read project intro'); ..."`：exit code `0`，确认默认流程输出 `user_task -> assistant_step -> tool_call -> tool_result -> final_answer`，并在第 2 轮基于 observation 停止。
- `python -c "from OpenCAI.agent_loop import run_fake_loop; events = run_fake_loop('Read project intro', max_steps=1); ..."`：exit code `0`，确认达到 `max_steps` 后输出明确停止信息。
- `python -m py_compile OpenCAI\agent_loop.py OpenCAI\llm_adapter.py`：exit code `0`。
- `python -c "from OpenCAI.llm_adapter import to_provider_tool_schemas; from OpenCAI.tools import TOOLS; ..."`：exit code `0`，确认 4 个工具可转换为 provider-neutral schema，`read_file` 的 required 参数为 `path`。
- `python -c "from OpenCAI.llm_adapter import parse_provider_response; ..."`：exit code `0`，确认 fake provider response 可转换为 `tool_call` / `final_answer`，且 tool call 优先于 text。
- `python -c "from OpenCAI.llm_adapter import LLMAdapterError, parse_provider_response; ..."`：exit code `0`，确认异常 provider response 会抛出 `LLMAdapterError`。
- `python -c "from OpenCAI.agent_loop import run_fake_loop; from OpenCAI.llm_adapter import FakeLLMAdapter; ..."`：exit code `0`，确认显式注入 `FakeLLMAdapter` 后事件序列不变。
- `python -c "... BrokenAdapter ..."`：exit code `0`，确认 adapter 抛出 `LLMAdapterError` 时 Agent Loop 产出 `user_task -> error`。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\llm_adapter.py`：exit code `0`。
- `python -c "from OpenCAI.__main__ import build_adapter; ..."`：exit code `0`，确认 Runtime 当前选择 `FakeLLMAdapter`。
- `python -m OpenCAI --dry-run --task "Read README"`：exit code `0`，确认 dry-run 输出 `adapter: FakeLLMAdapter`。
- `$env:GEMINI_API_KEY=''; python -m OpenCAI; exit $LASTEXITCODE`：exit code `2`，确认缺 key 路径仍提示未发送请求。

## 当前路线文档

- 当前执行路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- 历史执行计划：`docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`，已暂停，仅作参考。
