# Phase 12: Productized CLI

## 组件边界

Phase 12 收口的是 OpenCAI 的最小日常 CLI 体验，不改变 Agent Loop 的核心协议。

- Runtime 负责 CLI 参数、交互式 session state、adapter 选择和权限状态。
- Composer 负责把原始输入分流为 task、runtime command 或 shell command。
- Runtime Command Registry 负责 slash command 元数据、help 文本和命令执行。
- TUI 负责 prompt_toolkit 输入体验、suggestion 和 choice prompt。
- Agent Loop 继续只负责单个 task 内的 `model -> tool_call -> observation -> model` 循环。

## 最小产物

- `python -m OpenCAI` 默认进入交互式输入循环。
- `--task` 保留一次性调试路径。
- `--adapter fake|gemini` 和 `/model` 支持 adapter 选择。
- `--max-steps` 和 `/max-steps` 控制单个 task 的 loop budget。
- `--allow-write` / `--allow-command` 和对应 slash command 控制当前进程或 session 权限。
- `/help` 输出 runtime commands 和输入模式。
- 普通文本进入 Agent Loop，`/` 进入 runtime command，`!command` 进入用户 shell mode。

## 关键取舍

本阶段不公开 `--require-verification`，也不保留无效的 `--verify` 参数。

原因：

- `require_verification` 是 Agent Loop 内部停止条件，不是用户容易理解的 CLI 能力。
- 单独的 `--verify` 如果没有完整 workflow/hook 语义，会变成“看起来可用但实际不生效”的参数。
- Claude Code 的参考做法是默认要求 agent 完成前验证，并把自动化拦截交给 hooks / workflow，而不是暴露两个验证 flag。

后续如果要做强制验证，应放到 WorkflowRunner 或 hook 机制中，例如 `PostToolUse(Edit|Write)` 后运行验证，或 `Stop` 前检查验证结果。

## 验证证据

- `python -m py_compile OpenCAI\__main__.py OpenCAI\runtime_commands.py OpenCAI\composer.py OpenCAI\tui.py`
- `python -m unittest tests.test_runtime_commands tests.test_composer tests.test_tui_completer tests.test_shell_mode tests.test_safety tests.test_agent_loop_safety`
- `python -m OpenCAI --help`
- `python -m OpenCAI --dry-run --max-steps 4`
- `cmd /c "(echo /help&echo /status&echo /exit)|python -m OpenCAI"`

## 下一阶段

Phase 13 进入 `WorkflowSpec` / `WorkflowRunner`：先实现串行 phase runtime，不做并发、不做后台任务、不把 workflow 编排塞进 `agent_loop.py`。

## 同步记录

- Notion 学习日志：https://app.notion.com/p/38d1f9a0b01281a994cbc9240e07a88e。
