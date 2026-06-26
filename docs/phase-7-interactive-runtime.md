# Phase 7: Interactive Runtime / TUI Shell

## 组件边界

- Runtime owns：启动配置、`.env` 加载、CLI 参数、adapter 创建、one-shot / interactive 路径分发、`RuntimeSession`。
- TUI Shell owns：用户输入提示。当前由 `ask_task()` 提供。
- Renderer owns：`events -> transcript`。不处理用户输入、不维护 session。
- Agent Loop owns：单个 task 内的 `messages`、tool call、observation、events、停止条件。
- LLMAdapter owns：`messages + tools -> ModelOutput`。

## 最小产物

- `python -m OpenCAI` 默认进入交互式输入循环。
- `--task` 保留为一次性调试路径。
- `exit` / `quit` / `:q` 退出交互循环。
- `RuntimeSession.turn_count` 显示为 `Task 1`、`Task 2` 等输入提示。
- `RuntimeSession.task_history` 记录当前进程内用户输入过的 tasks。

## 关键取舍

- `task_history` 是 Runtime state，不是 LLM messages。
- 当前不把 `task_history` 传给 `run_once()`、Agent Loop 或 LLM。
- 当前不实现 `/history`，避免引入命令系统。
- `tui.py` 可以包含 input helper，但不能直接执行 Agent Loop。
- Renderer 不渲染 TUI Shell 的输入提示，只渲染 Agent events。

## 验证

- `python -m py_compile OpenCAI\__main__.py OpenCAI\tui.py OpenCAI\agent_loop.py OpenCAI\llm_adapter.py OpenCAI\tools.py`：exit code `0`。
- `python -m OpenCAI --help`：exit code `0`。
- `python -m OpenCAI --dry-run`：exit code `0`。
- `python -m OpenCAI --task "Read README"`：exit code `0`。
- `cmd /c "(echo Read README&echo Read README&echo exit)|python -m OpenCAI"`：exit code `0`。
- `cmd /c "echo Read README|python OpenCAI\tui.py"`：exit code `0`。

## 下一阶段

Phase 8 继续验证真实 `GeminiAdapter`。Runtime 已有显式 `--adapter fake|gemini` 入口，但默认仍是 fake；真实请求前先核对当前 `google-genai` 官方 function calling API，并保持 Agent Loop 不依赖 Gemini response 结构。
