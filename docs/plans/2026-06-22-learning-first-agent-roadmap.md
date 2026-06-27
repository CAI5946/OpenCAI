# Plan: OpenCAI Roadmap

## 背景

OpenCAI 已从学习型最小闭环升级为个人可用的 CLI Coding Agent 原型。后续路线不再围绕外部源码快照做对照，而是围绕 OpenCAI 自身能力推进：先完成单 Agent coding loop，再实现独立 WorkflowRunner。

## 决策

- 仓库对外定位统一为 `OpenCAI`。
- `OpenCAI/` 是核心 Python 原型代码。
- `docs/` 保留 OpenCAI 架构、路线、状态和阶段计划。
- `examples/` 保留 toy project，用于验证修复闭环。
- 后续开发以 OpenCAI 自身需求为主线；需要参考时只使用公开资料、成熟工程惯例和项目内已有实现。
- Dynamic Workflows 不塞进 `agent_loop.py`。Agent Loop 继续负责单个 agent 的 `model -> tool_call -> observation -> model` 循环；WorkflowRunner 负责 phase 顺序、phase 状态、结果汇总和重试。

## 已完成阶段

- Phase 0：Component Map。
- Phase 1：Event / Transcript Model。
- Phase 2：Renderer。
- Phase 3：Tool Model。
- Phase 4：Agent Loop。
- Phase 5：LLM Adapter。
- Phase 6：Toy Project Closed Loop。
- Phase 7：Interactive Runtime / TUI Shell。
- Phase 8：Real GeminiAdapter 核心验证。
- Phase 9：Tool Completion。

## 当前阶段

### Phase 10: Real Toy Repair

目标：让真实 Gemini 驱动 toy project 修复闭环。

验收：

- 事件流包含 `verification failed -> read/search -> apply_patch -> verification passed -> final_answer`。
- `python -m unittest discover examples/toy_project` exit code 为 `0`。

## 后续阶段

### Phase 11: Minimal Safety Layer

目标：实现最小安全边界，把“模型想做”和“系统允许执行”分开。

产出：

- `--allow-write`。
- `--allow-command`。
- cwd/path 边界检查。
- 明显危险命令拦截。

### Phase 12: Productized CLI

目标：整理 OpenCAI 为可日常试用的最小 CLI。

产出：

- `--adapter fake|gemini`。
- `--max-steps`。
- `--verify`。
- `--require-verification`。
- README、status 和最小使用说明。

### Phase 13: WorkflowSpec + WorkflowRunner

目标：实现 OpenCAI Dynamic Workflows 的最小 runtime，不做并发和后台 UI。

产出：

- `WorkflowSpec`：定义 name、phases、max_retries。
- `WorkflowPhase`：定义 id、role、prompt_template、tools_allowed、depends_on、success_check。
- `WorkflowRunner`：串行执行 phase，每个 phase 调用一次现有 Agent Loop，并保存 phase result。

### Phase 14: Nodeflow Bugfix Workflow

目标：把 Nodeflow-style bugfix 流程固化为第一个内置 coding workflow。

产出：

- 内置 workflow：`clarify -> plan -> execute -> review -> verify -> handoff`。
- 每个 phase 有明确职责和输出。
- `execute` phase 使用现有 Agent Loop 和工具；`review` / `verify` phase 只检查结果，不直接扩大修改范围。

### Phase 15: Review / Verify Retry Loop

目标：实现最小失败重试机制。

产出：

- review 发现 P1/P2 风险时回到 execute。
- verify 失败时回到 execute。
- retry 次数有上限，并在 handoff 中记录 retry history。

### Phase 16: Workflow Command / Save / Replay

目标：让 workflow 可复用，而不是只在代码里硬编码。

产出：

- CLI 支持按名称运行 workflow。
- workflow spec 可保存在项目目录或用户目录。
- 允许对同一个 workflow 用不同 task / args 重跑。

### Phase 17: LLM-generated WorkflowSpec

目标：让模型根据任务生成受限的 WorkflowSpec。

产出：

- LLM 只能生成受 schema 约束的 WorkflowSpec。
- Runtime 在执行前展示计划并允许用户确认。
- 不允许模型生成任意 Python / shell 编排代码。

### Phase 18: Parallel Subagents

目标：在 workflow runtime 中引入最小并行 worker 能力。

产出：

- WorkflowPhase 支持多个 worker agent。
- 并发数有上限。
- phase 汇总器合并 worker 结果。

## 执行原则

- 每次只聚焦一个 Agent 组件或一个 workflow 组件。
- 先定义输入、输出、状态、失败路径和边界，再实现。
- 若有代码，代码必须最小、可观察、可运行或可检查。
- 阶段完成、下一步变化、出现阻塞或验证结果变化时，更新 `docs/status.md`。

## 非目标

- 不一次性补齐全部真实工具。
- 不让 Renderer 承担用户输入；交互输入属于 TUI Shell / Runtime 边界。
- Phase 13 前不新增 MCP、插件、多 Agent、长期 memory。
- 不把 Nodeflow 阶段流程写死进 Agent Loop。
- 不在第一版 Dynamic Workflows 中实现任意代码执行型 workflow script、后台任务 UI、暂停恢复、成本追踪或大规模 subagent 并发。
