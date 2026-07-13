# OpenCAI

OpenCAI 是一个面向个人开发工作流的 Alpha 阶段 CLI Coding Agent 产品原型。

## 当前锚点

- 状态：可运行、可测试的 Alpha 产品原型，尚未作为生产级工具发布。
- 长期目标：覆盖任务理解、上下文检索、工具执行、验证、交互式 CLI、workflow 编排、多 agent 协作和可审计状态。
- 当前能力：交互式任务输入、slash command、`!` shell mode、fake adapter、多 provider LLM profile setup、事件流 transcript、基础工具调用闭环和串行 workflow runtime。
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

查看版本：

```powershell
python -m OpenCAI --version
```

默认使用本地确定性的 `fake/fake` model profile，不需要 API key。
默认 permission profile 是 `approve-safe`。

配置真实 provider：

```text
/model-add
/model
/model-test
```

`/model-add` 会选择 provider、配置 API key、动态拉取可用 model，并把 profile 写入 `.opencai/models.json`；API key 写入项目根目录 `.env`。当前支持 `google`、`openai`、`anthropic`、`ollama`、`deepseek`、`glm` 和 `openai-compatible`。

`.env` 和 `.opencai/models.json` 都是本地配置，不进入版本控制。仓库仅提供 `.env.example` 和 `.opencai/models.example.json` 作为结构示例。项目默认使用 `fake/fake`，无需复制示例文件即可运行。

## 交互式输入

- 普通文本：发送给当前 execution mode。默认 `agent` mode 走 Agent Loop；`guided` mode 先运行 Clarify，生成 session-level pending `DemandBrief` review，再通过选择弹窗确认后注入普通 Agent Loop；`workflow` mode 走 Workflow Clarify / Planner / WorkflowRunner。
- `$skill args`：显式请求调用本地 skill，例如 `$learn-with-dev Continue workflow gate`；Runtime 会先要求模型调用 `invoke_skill`，再把 skill 指令作为 meta message 注入后续上下文。
- `/help`：显示 runtime command 和输入模式。
- `/status`：显示当前 session 的 cwd、model、max_steps 和权限状态。
- `/model-add`：配置真实 provider，选择或输入 model，并注册为 `provider/model` profile。
- `/model`：进入二级选择，只显示当前已注册的 model profiles。
- `/model provider/model`：切换到已注册的 model profile。
- `/model-test`：对当前 model profile 做 no-tool smoke check。
- `/mode`：进入二级选择，选择 `agent`、`guided` 或 `workflow`。
- `/mode agent`：普通文本直接走 Agent Loop。
- `/mode guided`：切换到 guided mode，普通文本会先经过 Clarify 和 `DemandBrief` review gate；TTY 下 Clarify 问题可选择 Stop Clarify，review gate 可通过选择弹窗执行、停止或选择修改后输入反馈，非 TTY 下默认执行以避免 smoke/test 卡住。
- `/mode workflow`：普通文本自动走当前 Workflow Clarify / Planner / WorkflowRunner。
- `/keymap`：显示当前 TUI 快捷键；TTY 下打开只读弹窗，非 TTY 下打印列表。
- `/max-steps N`：设置单个 task 的最大模型轮次兜底预算；Agent Loop 仍会优先因 final answer、重复动作或连续工具失败等语义条件停止。
- `/permission`：进入二级选择，设置模型工具调用权限 profile。
- `/permission read-only|ask-approval|approve-safe|full-access`：直接设置模型工具调用权限 profile。
- `Ctrl+O`：TTY 交互下快速展开最近一次普通 task 的过程视图；在过程视图内再次按 `Ctrl+O` 可收起。
- `Shift+Enter` / `Ctrl+J`：在 TTY composer 中插入换行；OpenCAI 兼容 Windows console Shift+Enter 事件和常见的 `ESC[13;2u` / `ESC[27;2;13~` Shift+Enter 序列，若终端无法区分 Shift+Enter 则使用 `Ctrl+J`。
- `Ctrl+R` / `Up` / `Down`：搜索或浏览当前进程内 prompt history。
- `Alt+P`：打开 model 二级选择；`Shift+Tab`：直接循环 execution mode。
- `/process`：展开最近一次普通 task 的过程 transcript；TTY 交互下会打开临时过程视图，按 `Ctrl+O` / `Esc` / `Enter` / `q` 收起。
- `/workflow TASK`：先运行 clarify gate，再运行当前内置 `inspect -> handoff` workflow，显示 plan、final answer 和过程摘要。
- `!command`：直接执行用户 shell 命令，并在 transcript 中显示 stdout、stderr 和 exit code。
- `/exit`：退出交互式 runtime。

示例：

```text
/status
$learn-with-dev Continue the next component
/model-add
/model
/model-test
/mode guided
/mode workflow
/keymap
!python --version
/permission approve-safe
/process
/exit
```

## 边界

- 当前是 Alpha 产品原型；长期面向完整 Coding Agent 演进，但不把规划中的能力描述为已完成
- 不加入无明确用途的目录、框架或抽象
- 复杂 TUI、MCP、插件、多 Agent、长期 memory 等能力需要先完成设计评估和边界确认，不能仅因“第一版”而永久排除
- Dynamic Workflows 以完整成熟 workflow runtime 为目标；当前切片先保证控制权、状态、权限和验证边界正确，再逐步补齐后台任务、保存/恢复、成本追踪和并发能力

## 开源与安全

- 许可证：[MIT License](LICENSE)
- 贡献指南：[CONTRIBUTING.md](CONTRIBUTING.md)
- 安全问题：[SECURITY.md](SECURITY.md)
- 默认权限 profile 是 `approve-safe`；使用更高权限前应先理解工具执行边界
- 本仓库不接受没有兼容再分发许可证的外部源码

## 文档

- [docs/roadmap.md](docs/roadmap.md)
- [docs/archive/phases/core-loop-architecture.md](docs/archive/phases/core-loop-architecture.md)
- [docs/status.md](docs/status.md)
- [docs/plans/2026-06-22-learning-first-agent-roadmap.md](docs/plans/2026-06-22-learning-first-agent-roadmap.md)
