# 开发状态

## 当前阶段

学习优先路线：Phase 5 准备中。

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
- 已新增 `OpenCAI/agent_loop.py`，定义 `Message`、`ModelOutput`、`run_fake_loop()`、`_fake_model_decide()` 和 `_format_observation()`。
- Phase 4 当前实现为不接真实 LLM 的 multi-step fake loop：第 1 轮模拟模型选择 `read_file README.md`，工具结果格式化为 message observation 后进入第 2 轮，第 2 轮模拟模型输出 `final_answer`。
- 已明确 Phase 4 的核心边界：Agent Loop 维护 `messages`、`events`、`step` 和停止条件；Tool Model 执行工具；Renderer 消费 events；Runtime 负责启动和配置；LLM Adapter 负责后续真实模型 API 细节。

## 正在做

- 准备进入 Phase 5：LLM Adapter。

## 下一步

- 先说明 LLM Adapter 的职责、输入、输出、失败情况和边界。
- 将当前 `_fake_model_decide(messages)` 抽象为 adapter 接口，例如 `call(messages, tools) -> ModelOutput`。
- 先实现 `FakeLLMAdapter`，暂不接 Gemini。
- 明确 `ToolSpec` 到模型 tool schema 的转换位置，保持 Agent Loop 不依赖具体模型供应商响应格式。

## 阻塞/待确认

- 统一验证命令未确认。
- `.env` 中的 Gemini API key 未填写。
- Stage 1 依赖尚未安装或验证；在学习优先路线下暂不阻塞 Phase 2。

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

## 当前路线文档

- 当前执行路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- 历史执行计划：`docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`，已暂停，仅作参考。
