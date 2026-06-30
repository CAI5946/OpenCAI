# Plan: OpenCAI Roadmap

## 背景

OpenCAI 已从学习型最小闭环升级为个人可用的 CLI Coding Agent 原型。后续路线不再按线性 Phase 推进，而是围绕核心 Feature Epic 迭代：Workflow、Multi-agents、Agent Loop Strategy，以及几个会影响 runtime 架构的候选 feature。

## 决策

- 仓库对外定位统一为 `OpenCAI`。
- `OpenCAI/` 是核心 Python 原型代码。
- `docs/` 保留 OpenCAI 架构、路线、状态和 feature roadmap。
- `examples/` 保留 toy project，用于验证修复闭环。
- 后续开发以 OpenCAI 自身需求为主线；需要参考时只使用公开资料、成熟工程惯例和项目内已有实现。
- 后续开发采用 Feature Epic + 小切片，不再继续新增 Phase 14/15/16 这类线性阶段。
- Dynamic Workflows 不塞进 `agent_loop.py`。Agent Loop 继续负责单个 agent 的 `model -> tool_call -> observation -> model` 循环；WorkflowRunner 负责 phase 顺序、phase 状态、结果汇总和重试。
- 跨 feature 的核心边界保持稳定：Runtime 负责配置和入口，LLMAdapter 负责 provider 翻译，Agent Loop 负责单 agent 循环，Tool Model 负责真实动作，Event / Transcript 负责可观察记录。

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
- Phase 10：Real Toy Repair。
- Phase 11：Minimal Safety Layer。
- Phase 12：Productized CLI。
- Phase 13 第一版：WorkflowSpec / WorkflowRunner 最小串行 runtime、内置 `inspect -> handoff` workflow、`/workflow TASK` 入口和 `stop` event 截断语义。

## 后续开发方式

后续不再按 Phase 排队，而是按 Feature Epic 管理。每个 feature 仍然拆成小切片，每个切片必须有清楚的输入、输出、状态、失败路径和验证方式。

推荐优先级：

```text
Feature A: Workflow
  -> Feature B: Multi-agents
  -> Feature C: Agent Loop Strategy
```

新增候选 feature 按架构影响排序：

```text
Feature D: Modes
Feature E: Streaming Outputs
Feature F: LLM Council
```

## Feature Epics

### Feature A: Workflow

目标：让 OpenCAI 能稳定编排多阶段任务。Workflow 是后续 Multi-agents、LLM-generated workflow 和复杂开发流程的主干。

当前状态：第一版已能通过 `/workflow TASK` 执行内置 `inspect -> handoff` 串行 workflow。

产出：

- `WorkflowSpec`：定义 name、description、phases、final_phase_id、max_retries。
- `WorkflowPhase`：定义 id、role、prompt_template、depends_on。
- `WorkflowRun` / `PhaseResult`：保存 task、status、phase results、events、final answer 和 error。
- `SerialWorkflowRunner`：串行执行 phase，每个 phase 调用一次现有 Agent Loop，并保存 phase result。
- `/workflow TASK`：当前运行内置 `inspect -> handoff` workflow，显示 plan、final answer 和过程摘要。
- `stop` event：用于表达 max_steps 等正常停止条件，不再伪装成 final answer。

下一步切片：

- `/workflow` execute / cancel confirmation gate。
- 拆出 workflow command flow，避免 `runtime_commands.py` 继续变重。
- humancheck phase：明确哪些步骤必须等用户确认。
- 内置 Nodeflow bugfix workflow：`clarify -> plan -> execute -> review -> verify -> handoff`。
- review / verify retry loop：失败回到 execute，并记录 retry history。
- workflow command / save / replay：让 workflow 可复用。
- LLM-generated WorkflowSpec / WorkflowScript：执行前展示并确认，不允许生成任意 Python / shell 编排代码。

评估：

- 优先级：最高。
- 架构影响：中到高，主要影响 WorkflowRunner、runtime command、workflow state 和 prompt composer。
- 依赖：现有 Agent Loop、Tool Model、SafetyPolicy。
- 风险：如果 WorkflowSpec 设计过重，会拖慢迭代；如果脚本能力过早开放，会绕开安全边界。
- 推荐策略：继续保持 script-first 方向，但每次只落一个可运行切片。

### Feature B: Multi-agents

目标：在 WorkflowRunner 中支持多个 agent worker，用于并行探索、隔离上下文和多视角 review。

候选能力：

- subagent profile：为不同 worker 定义 role、scope、tool policy 和 model。
- scoped context：每个 worker 只拿到必要任务、文件范围和前置结果。
- result aggregator：把 worker 输出压缩成 phase result。
- parallel inspect / review：先从只读探索和 review 场景开始。
- file claim / conflict policy：避免多个 worker 同时修改同一核心文件。

评估：

- 优先级：高，但必须排在 Workflow 主干之后。
- 架构影响：高，影响 WorkflowRunner、Agent/Subagent Dispatcher、Result Aggregator、WorkflowRun state。
- 依赖：Workflow state、phase result、dispatcher/aggregator 边界。
- 风险：过早允许并发写文件会制造冲突；没有 summary-only return 会污染主上下文。
- 推荐策略：第一版只做只读并行 inspect/review，不允许并行写入。

### Feature C: Agent Loop Strategy

目标：把当前 ReAct-like loop 抽象成可替换策略，并用同一组 benchmark 比较不同策略效果。

候选 strategy：

- `ReActLoop`：当前默认 `model -> tool_call -> observation -> model` 主循环。
- `PlanExecuteLoop`：先生成 plan，再按步骤执行。
- `VerifyFirstLoop`：bugfix 任务先运行验证，再读取和修改。
- `ReviewRetryLoop`：执行后自审，失败时回到执行。
- `WorkflowRunner`：固定阶段编排，每个执行阶段内部仍可使用 ReAct loop。

评估：

- 优先级：中，属于架构实验，不应阻塞 Workflow 主线。
- 架构影响：中到高，影响 `agent_loop.py` 的封装方式，但不应重写 Runtime、Tool Model 或 LLMAdapter。
- 依赖：稳定的 benchmark tasks、事件指标和 verification 口径。
- 风险：如果太早抽象，会把还没稳定的 loop 固化成复杂接口。
- 推荐策略：保留当前 loop 为 baseline；等 Workflow 主干稳定后，再抽最小 `AgentLoopStrategy` 接口。

### Feature D: Modes

目标：从 Runtime 层加载 mode profile，例如 `learn mode`、`dev mode`、`debug mode`，让同一套 OpenCAI 可以按任务类型调整行为。

模式可能影响：

- system / task prompt。
- 默认 workflow。
- 默认 Agent Loop Strategy。
- 默认 tool policy。
- max_steps、verification 要求和 handoff 格式。
- UI statusline 和 runtime command。

候选模式：

- `learn`：解释边界、慢速小切片、用户先做设计判断。
- `dev`：默认执行开发任务，强调最小修改和验证。
- `debug`：先复现、读日志、定位原因，再修改。
- `review`：只读优先，先输出 findings，不主动修改。

评估：

- 优先级：高，但应作为 Runtime 配置层，不应直接把 mode 逻辑散进 Agent Loop。
- 架构影响：高，会改变 Runtime -> Workflow/Agent Loop 的配置注入方式。
- 依赖：需要先定义 `ModeProfile` 数据结构，至少包含 prompt policy、workflow selection、strategy selection 和 tool policy。
- 风险：如果 mode 直接改 Agent Loop 内部逻辑，会让 loop 变成条件分支堆积；如果 mode 和 workflow 重叠不清，会出现两套编排系统。
- 推荐策略：先做 Runtime-level `ModeProfile`，Agent Loop 只接收已经组合好的 task/context/policy，不知道具体 mode 名。

### Feature E: Streaming Outputs

目标：让模型输出、tool events、workflow phase progress 可以边生成边渲染，而不是等一次 Agent Loop 或 workflow 完成后再显示。

候选能力：

- streaming model text。
- streaming event transcript。
- workflow phase progress。
- long-running command stdout/stderr streaming。
- 可中断执行和更清楚的 stop/cancel 状态。

评估：

- 优先级：中高，能显著改善 CLI 体验，但对核心能力不是前置依赖。
- 架构影响：高，当前 Agent Loop 返回 `list[Event]`，streaming 需要改为 event iterator / callback / sink。
- 依赖：Event / Transcript 协议要稳定；Renderer 要支持增量消费。
- 风险：如果直接把 streaming 逻辑写进 Renderer，会破坏 Event Model 的可测试性；如果一次性改全链路，回归面大。
- 推荐策略：先引入 `EventSink` 或 generator-style loop，让现有 list-return 路径保持兼容。

### Feature F: LLM Council

目标：支持配置多个 LLM，并把不同模型分配给不同任务，例如强模型负责 planning / review，便宜模型负责搜索、摘要或重复执行。

候选能力：

- model profiles：定义 provider、model、用途、成本偏好和能力标签。
- role-based routing：planner / executor / reviewer / verifier 使用不同 adapter。
- council voting / critique：多个模型对 plan 或 review 给出独立意见，再聚合。
- fallback：某个模型失败时切换到备用模型。

评估：

- 优先级：中，价值高但应晚于 Workflow 和 Modes 的基础配置层。
- 架构影响：高，当前 Runtime 只有一个 `adapter`，需要扩展为 `ModelRegistry` / `AdapterPool`，WorkflowPhase 或 ModeProfile 决定用哪个模型。
- 依赖：Workflow phase role、ModeProfile、LLMAdapter provider-neutral 协议。
- 风险：成本、延迟、输出冲突和上下文一致性都会上升；如果没有 aggregator，会变成多模型噪声。
- 推荐策略：第一版只做 role-based model routing，不做投票型 council；例如 plan/review 用强模型，execute 仍用默认模型。

## 已完成阶段细节

### Phase 12: Productized CLI

目标：整理 OpenCAI 为可日常试用的最小 CLI。

产出：

- `--adapter fake|gemini`。
- `--max-steps`。
- `--allow-write` / `--allow-command`。
- slash command registry 和 `/help`。
- Composer 输入分流、slash suggestion 和 `!` shell mode。
- `/model` 二级选择流程。
- README、status 和最小使用说明。

### Phase 10: Real Toy Repair

目标：让真实 Gemini 驱动 toy project 修复闭环。

验收：

- 事件流包含 `verification failed -> read/search -> apply_patch -> verification passed -> final_answer`。
- `python -m unittest discover examples/toy_project` exit code 为 `0`。

### Phase 11: Minimal Safety Layer

目标：实现最小安全边界，把“模型想做”和“系统允许执行”分开。

产出：

- `--allow-write`。
- `--allow-command`。
- cwd/path 边界检查。
- 明显危险命令拦截。

## Feature 依赖关系

```text
Workflow
  -> Multi-agents
  -> LLM Council

Modes
  -> Workflow selection
  -> Agent Loop Strategy selection
  -> LLM Council model routing

Streaming Outputs
  -> Runtime / Renderer experience
  -> Workflow phase progress
  -> Long-running command visibility

Agent Loop Strategy
  -> Requires stable benchmark and event metrics
```

当前推荐主线：

1. 继续收口 Workflow 的 confirmation gate 和 command split。
2. 设计 `ModeProfile`，但只落最小 runtime 配置，不急着改 Agent Loop。
3. Workflow 稳定后做 Nodeflow bugfix template 和 retry。
4. 再进入只读 Multi-agents。
5. Streaming Outputs 可作为 CLI 体验专项穿插，但必须保持旧 list-return 测试路径。
6. LLM Council 等 ModeProfile + WorkflowPhase model routing 稳定后再做。
7. Agent Loop Strategy 最后做 benchmark-driven experiment。

## 执行原则

- 每次只聚焦一个 feature 的一个可观察切片。
- 先定义输入、输出、状态、失败路径和边界，再实现。
- 若有代码，代码必须最小、可观察、可运行或可检查。
- Feature 切片完成、下一步变化、出现阻塞或验证结果变化时，更新 `docs/status.md`。

## 非目标

- 不一次性补齐全部真实工具。
- 不让 Renderer 承担用户输入；交互输入属于 TUI Shell / Runtime 边界。
- 不新增 MCP、插件或长期 memory，除非某个 feature 明确需要且先完成设计评估。
- 不把 Nodeflow 阶段流程写死进 Agent Loop。
- 不在第一版 Dynamic Workflows 中实现任意代码执行型 workflow script、后台任务 UI、暂停恢复、成本追踪或大规模 subagent 并发。
- 不把 mode、model routing、streaming 或 council 逻辑直接散落进 `agent_loop.py`；它们应由 Runtime / WorkflowRunner 组合配置，再传入执行单元。
