# OpenCAI

OpenCAI 是一个面向个人开发工作流的最小 CLI Coding Agent 原型。

## 当前锚点

- 目标：实现一个个人可用的产品化 CLI 版最小 Coding Agent。
- 当前能力：交互式任务输入、slash command、`!` shell mode、fake adapter、Gemini adapter、事件流 transcript、最小工具调用闭环。
- 后续路线：先完成单 Agent core，再探索 OpenCAI Dynamic Workflows。
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

使用 Gemini adapter：

```powershell
python -m OpenCAI --adapter gemini
```

Gemini 需要在项目根目录 `.env` 或当前 shell 中设置 `GEMINI_API_KEY`。默认 adapter 是 `fake`，不会发送真实模型请求。

## 交互式输入

- 普通文本：发送给 Agent Loop，例如 `Read README`。
- `/help`：显示 runtime command 和输入模式。
- `/status`：显示当前 session 的 cwd、model、max_steps 和权限状态。
- `/model`：进入二级选择，选择 `fake` 或 `gemini`。
- `/model fake`：直接切换到 fake adapter。
- `/max-steps N`：设置单个 task 的最大 model/tool loop 步数。
- `/allow-write on|off`：允许或关闭写文件工具，例如 `apply_patch`。
- `/allow-command on|off`：允许或关闭模型请求的命令执行工具。
- `!command`：直接执行用户 shell 命令，并在 transcript 中显示 stdout、stderr 和 exit code。
- `/exit`：退出交互式 runtime。

示例：

```text
/status
/model
!python --version
/allow-command on
/exit
```

## 边界

- 不追求一次性做完整 Agent
- 不加入无明确用途的目录、框架或抽象
- 不追求复杂 TUI、MCP、插件、多 Agent 或长期 memory 的第一版实现
- Dynamic Workflows 先实现 OpenCAI 的最小可控版本，不做后台任务 UI、成本追踪或大规模并发

## 文档

- [docs/roadmap.md](docs/roadmap.md)
- [docs/core-loop-architecture.md](docs/core-loop-architecture.md)
- [docs/status.md](docs/status.md)
- [docs/plans/2026-06-22-learning-first-agent-roadmap.md](docs/plans/2026-06-22-learning-first-agent-roadmap.md)
