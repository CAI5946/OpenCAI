# OpenCAI

OpenCAI 是一个面向个人开发工作流的完整成熟 CLI Coding Agent 项目。

## 当前锚点

- 目标：设计并开发完整成熟的 Coding Agent，覆盖任务理解、上下文检索、工具执行、验证、交互式 CLI、workflow 编排、多 agent 协作和可审计状态。
- 当前能力：交互式任务输入、slash command、`!` shell mode、fake adapter、Gemini adapter、事件流 transcript、基础工具调用闭环和串行 workflow runtime。
- 后续路线：以完整成熟 Coding Agent 为终局，围绕 Workflow、Multi-agents、Modes、Streaming Outputs、LLM Council 和 Agent Loop Strategy 分阶段演进。
- 默认入口：`python -m OpenCAI`。

## 最小使用

安装依赖：

```powershell
python -m pip install -r OpenCAI\requirements.txt
```

启动交互式 runtime：

```powershell
python -m OpenCAI
```

运行一次性任务：

```powershell
python -m OpenCAI --task "Read README"
```

查看开发态版本：

```powershell
python -m OpenCAI --version
```

默认使用 Gemini adapter。Gemini 需要在项目根目录 `.env` 或当前 shell 中设置 `GEMINI_API_KEY`。
默认 permission profile 是 `approve-safe`。

显式使用 fake adapter：

```powershell
python -m OpenCAI --adapter fake
```

## 交互式输入

- 普通文本：发送给 Agent Loop，例如 `Read README`。
- `$skill args`：显式请求调用本地 skill，例如 `$learn-with-dev Continue workflow gate`；Runtime 会先要求模型调用 `invoke_skill`，再把 skill 指令作为 meta message 注入后续上下文。
- `/help`：显示 runtime command 和输入模式。
- `/status`：显示当前 session 的 cwd、model、max_steps 和权限状态。
- `/model`：进入二级选择，选择 `fake` 或 `gemini`。
- `/model gemini`：直接切换到 Gemini adapter。
- `/model fake`：直接切换到 fake adapter。
- `/keymap`：显示当前 TUI 快捷键；TTY 下打开只读弹窗，非 TTY 下打印列表。
- `/max-steps N`：设置单个 task 的最大模型轮次兜底预算；Agent Loop 仍会优先因 final answer、重复动作或连续工具失败等语义条件停止。
- `/permission`：进入二级选择，设置模型工具调用权限 profile。
- `/permission read-only|ask-approval|approve-safe|full-access`：直接设置模型工具调用权限 profile。
- `Ctrl+O`：TTY 交互下快速展开最近一次普通 task 的过程视图；在过程视图内再次按 `Ctrl+O` 可收起。
- `Shift+Enter` / `Ctrl+J`：在 TTY composer 中插入换行；`Shift+Enter` 仅在终端发送 `ESC[13;2u` 时可区分，若它直接提交则使用 `Ctrl+J`。
- `Ctrl+R` / `Up` / `Down`：搜索或浏览当前进程内 prompt history。
- `Alt+P`：打开 model 二级选择；`Shift+Tab`：直接循环 permission profile。
- `/process`：展开最近一次普通 task 的过程 transcript；TTY 交互下会打开临时过程视图，按 `Ctrl+O` / `Esc` / `Enter` / `q` 收起。
- `/workflow TASK`：运行当前内置 `inspect -> handoff` workflow，显示 plan、final answer 和过程摘要。
- `!command`：直接执行用户 shell 命令，并在 transcript 中显示 stdout、stderr 和 exit code。
- `/exit`：退出交互式 runtime。

示例：

```text
/status
$learn-with-dev Continue the next component
/model
/keymap
!python --version
/permission approve-safe
/process
/exit
```

## 边界

- 不一次性堆完全部能力，但设计时必须面向完整成熟 Coding Agent，而不是停留在玩具版或只验证概念
- 不加入无明确用途的目录、框架或抽象
- 复杂 TUI、MCP、插件、多 Agent、长期 memory 等能力需要先完成设计评估和边界确认，不能仅因“第一版”而永久排除
- Dynamic Workflows 以完整成熟 workflow runtime 为目标；当前切片先保证控制权、状态、权限和验证边界正确，再逐步补齐后台任务、保存/恢复、成本追踪和并发能力

## 文档

- [docs/roadmap.md](docs/roadmap.md)
- [docs/core-loop-architecture.md](docs/core-loop-architecture.md)
- [docs/status.md](docs/status.md)
- [docs/plans/2026-06-22-learning-first-agent-roadmap.md](docs/plans/2026-06-22-learning-first-agent-roadmap.md)
