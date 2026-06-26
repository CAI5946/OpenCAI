# OpenCAI

OpenCAI 是一个面向个人开发工作流的最小 CLI Coding Agent 原型。

## 当前锚点

- 目标：实现一个个人可用的产品化 CLI 版最小 Coding Agent。
- 当前能力：交互式任务输入、fake adapter、Gemini adapter、事件流 transcript、最小工具调用闭环。
- 后续路线：先完成单 Agent core，再探索 OpenCAI Dynamic Workflows。
- 默认入口：`python -m OpenCAI`。

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
