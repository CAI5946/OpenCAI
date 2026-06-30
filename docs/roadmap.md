# OpenCAI Roadmap

## 目标

OpenCAI 的目标是成为面向个人开发工作流的完整成熟 CLI Coding Agent：能理解任务、读取上下文、调用工具、修改文件、运行验证、处理失败并继续迭代。

小切片只是开发和验证方式，不代表产品目标停留在玩具版或最小 MVP。

## 当前路线

当前主线是 Feature A: Workflow。先把单 Agent 的 `inspect -> handoff` workflow 做成可确认、可观察、可失败恢复的 workflow runtime，再逐步扩展到 Nodeflow-style bugfix workflow、retry loop、humancheck、save/replay 和 LLM-generated WorkflowSpec / WorkflowScript。

并行产品验收目标是 Small-Task Coding Agent Competence：用本地 micro benchmark 衡量 OpenCAI 在小型代码任务上的真实表现，避免只靠主观感觉推进架构。

## Feature Epics

### Feature A: Workflow

目标：把单次 Agent Loop 之上的多阶段控制流抽成 WorkflowRunner。

优先顺序：confirmation gate -> workflow command flow -> Nodeflow bugfix workflow -> retry loop -> save/replay -> LLM-generated WorkflowSpec / WorkflowScript。

### Feature B: Multi-agents

目标：在 Workflow 主干稳定后，引入受控的多 agent 协作。

第一步只做只读 parallel inspect / review，不并行写文件；写入型协作必须等 state、dispatcher、aggregator、scoped context 和权限边界清楚后再做。

### Feature C: Agent Loop Strategy

目标：在主流程稳定后，用 benchmark-driven experiment 比较不同 loop strategy。

该方向不打断 Workflow 主线；先保留 ReAct baseline，再对同一组 benchmark tasks 评估 plan-execute、verify-first、review-retry 等策略。

### Feature D: Modes

目标：引入 Runtime-level `ModeProfile`，让 learn / dev / debug / review 等模式影响 prompt、workflow selection、strategy selection 和 tool policy。

模式不应把 mode-specific 分支直接写进 `agent_loop.py`。

### Feature E: Streaming Outputs

目标：让 Agent Loop / WorkflowRunner / Renderer 支持更实时的事件交付。

优先评估 `EventSink` 或 generator-style Agent Loop，同时保留当前 `list[Event]` 测试路径。

### Feature F: LLM Council

目标：从 role-based model routing 开始，把 plan / review / execute 等角色映射到不同模型或 adapter。

暂不优先做多模型投票式 council，避免早期引入高噪声和高成本决策层。

### Feature G: Context Engineering

目标：补齐 Runtime / Agent Loop / Workflow prompt composition 的输入合同。

第一步设计 `ContextSnapshot` / `ContextProvider` / `ContextComposer`，解决普通 Agent Loop 只接收 `user_task`、缺少 Session 初始化 context 的缺口；暂不做传统 RAG、vector DB 或复杂长期 memory。

## 当前执行顺序

1. 收口 Workflow confirmation gate 和 command flow。
2. 用 benchmark runner 建立真实 Gemini baseline，按失败类型排序下一刀。
3. 补 Context Engineering 的最小 Session 初始化 context。
4. 在 Workflow 主干稳定后进入只读 Multi-agents。
5. 评估 Modes 对 prompt、workflow、strategy 和 policy 的配置注入方式。
6. 再处理 Streaming Outputs、LLM Council 和 Agent Loop Strategy 的实验化扩展。

## 非目标

- 不一次性交付完整系统。
- 不把 workflow 编排塞进 `agent_loop.py`。
- 不提前引入传统 RAG、vector DB 或复杂长期 memory。
- 不提前做并行写文件型 multi-agent。
- 不提前做多模型投票式 council。
- 不让 `status.md` 承担完整 changelog 职责。

## 文档索引

- 当前状态：`docs/status.md`。
- 长期执行计划：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- Small-task 产品验收路线：`docs/plans/small-task-coding-agent-competence.md`。
- 核心循环架构：`docs/core-loop-architecture.md`。
- 学习型开发流程：`docs/learning-mode.md`。
- 当前 workflow 设计：`docs/phase-13-dynamic-workflows.md`。
