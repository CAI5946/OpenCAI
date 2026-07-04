# Phase 13: Dynamic Workflows

## 目标

Phase 13 的目标不是停留在最小 workflow demo，也不是立刻复刻 Claude Code Dynamic Workflows 或把 NodeFlow 整套 skill graph 搬进 OpenCAI。

本阶段先设计 OpenCAI 的 workflow 架构边界：

- 最终形态：结合 Claude Code Dynamic Workflows 和 NodeFlow，形成脚本式动态编排 + multi-agent workflow runtime。
- 当前切片范围：实现串行 `WorkflowRunner` 和 manifest，先用内置 workflow function 模拟脚本式编排，验证 workflow 层可以稳定编排多个 phase。

设计口径：OpenCAI 的长期目标是完整成熟 Coding Agent。小切片只用于降低一次性实现风险，不能把“最小”当成最终能力边界；Workflow 的状态、权限、审计、保存/恢复、humancheck、retry、multi-agent 和后台执行都需要在架构上留出位置。

后续路线已经从线性 Phase 列表切换为 Feature Epic + 小切片。本文仍作为 Workflow feature 的设计文档保留，不再承担全量 phase roadmap。

## 参考样板

### Claude Code Dynamic Workflows

Claude Code Dynamic Workflows 的关键设计是：workflow runtime 执行 orchestration script，由 script 持有计划、中间状态和调度逻辑；具体读文件、改文件、运行命令仍由 agent / subagent 执行。

可借鉴点：

- 编排层在 Agent Loop 外部。
- workflow 持有计划和中间状态，不把所有状态塞进模型上下文。
- subagents 是执行单元，workflow runtime 是 control plane。
- workflow 可以后台运行、保存、复用、暂停、恢复。
- 大任务适合 workflow，小任务仍可直接走普通 Agent Loop。

当前切片暂不采用：

- JavaScript orchestration script。
- 后台 runtime。
- 自动生成 workflow script。
- 大规模并发 subagents。
- pause / resume。
- workflow command 保存系统。

参考：

- https://code.claude.com/docs/en/workflows
- https://claude.com/blog/introducing-dynamic-workflows-in-claude-code

### NodeFlow

NodeFlow 的关键价值是把真实开发过程拆成风险自适应的节点图，而不是固定线性 checklist。

可借鉴点：

- `clarify / risk -> spec / plan -> execute -> review -> verify -> handoff` 的阶段模型。
- risk assessment 决定流程重量，而不是所有任务一律走重流程。
- review / verify 失败可以回到 execute。
- checkpoint 和 HITL 区分：checkpoint 是阶段产物 review，HITL 是执行前必须由人判断的事项。
- document budget 思想：不是每个任务都创建文档，只有跨任务、跨 agent、跨 session 或 handoff 有价值时才保留。

暂不采用：

- 完整 `docs/.nodeflow/` 状态系统。
- 完整 DAG 和 file-claim 机制。
- 完整 document cleanup policy。
- 完整 review matrix。
- 全部 nodeflow skill 作为 OpenCAI runtime 依赖。

## 最终形态

OpenCAI Dynamic Workflows 的最终形态应先按控制权分层，而不是按文件或类名分层：

```text
WorkflowSpec
  -> 静态合同：描述 metadata、schema、权限、可审计 phase 和安全边界

WorkflowScript
  -> 编排主体：用受限脚本表达流程、分支、循环、并发和聚合

WorkflowRunner
  -> 受限脚本运行时：解释 script，调度 phase，处理重试、阻塞和完成状态

WorkflowRun
  -> 执行账本：保存 phase result、artifact、finding、verification 和 retry history

Agent / Subagent Loop
  -> 单 phase 执行单元：负责 model -> tool_call -> observation -> model

Tool Model
  -> 真实动作层：负责 read_file / search_files / apply_patch / run_command
```

完整运行路径：

```text
User Task
  -> Workflow Intake
  -> Workflow Planner / Compiler
  -> WorkflowScript + WorkflowSpec manifest
  -> WorkflowRunner
      -> Phase Scheduler
      -> Prompt / Context Composer
      -> Agent / Subagent Dispatcher
      -> Result Aggregator
      -> Review / Verify / Retry Policy
  -> Handoff
  -> Workflow State / Artifacts
```

### 最终能力

- Workflow 可以由固定模板、用户命令或模型生成。
- WorkflowScript 可以表达动态流程、条件分支、循环、并发和结果聚合。
- WorkflowSpec / manifest 可以描述 metadata、输入输出 schema、权限、安全边界和可审计 phase。
- WorkflowRunner 可以串行或并行调度 phase。
- 每个 phase 可以启动一个 agent 或多个 subagents。
- phase 结果进入 workflow state，而不是只留在聊天上下文里。
- review / verify 失败时可以回到 execute。
- workflow 可以保存、重放、恢复。
- workflow 可以暴露为 CLI command。
- workflow 可以记录审计信息：phase 输入、输出、状态、验证证据和失败原因。

### 脚本式和声明式

最终形态允许两种 workflow 表达方式，但默认以受限脚本式 workflow 为主：

```text
Constrained WorkflowScript
  -> 主表达，适合循环、条件分支、并发、动态分组和复杂聚合。

WorkflowSpec / Manifest
  -> 辅助表达，适合保存 metadata、schema、权限、安全约束、展示、验证和审计。
```

脚本式 workflow 的核心原则：

```text
WorkflowScript = 主体
WorkflowSpec = metadata / schema / manifest / safety contract
WorkflowRunner = 受限脚本运行时
Agent Loop = 阶段执行单元
Tool Model = 唯一真实动作层
```

受限脚本只能调用 workflow runtime API，例如：

```text
run_agent()
run_subagents()
wait_all()
summarize()
set_state()
get_state()
handoff()
```

受限脚本不能：

- 直接读写文件。
- 直接运行 shell。
- 直接访问网络。
- 任意 import 本地库。
- 访问环境变量或 secrets。
- 绕过 Agent Loop、Tool Model 或 SafetyPolicy。

脚本的用途是编排 agent，而不是执行工具。脚本可以决定“何时启动哪个 agent、等待哪些结果、失败后回到哪里”，但不能自己改文件或跑命令。

当前切片不做完整脚本 runtime，但实现方向要靠近脚本 runtime：先抽出 Runner API 和 `run_phase` 思维，避免把声明式 schema 设计得过重。

### 最终模块

#### A. Workflow Intake

判断任务是否需要 workflow。

职责：

- 区分小任务和复杂任务。
- 判断风险、范围和是否需要 checkpoint。
- 选择普通 Agent Loop 或 WorkflowRunner。

不负责：

- 写 spec。
- 执行 phase。
- 修改文件。

#### B. Workflow Planner / Compiler

把用户任务、repo context、AGENTS.md、NodeFlow template 和可用 agent profile 编译成 `WorkflowScript + WorkflowSpec manifest`。

职责：

- 选择 workflow template。
- 生成或调整 WorkflowScript。
- 生成或调整 WorkflowSpec / manifest。
- 保证 workflow 只使用受控 phase、agent profile 和 tool policy。

不负责：

- 执行 workflow。
- 直接调用 tools。
- 直接启动 subagents。

#### C. Workflow Core Model

定义 workflow 的稳定数据结构。

候选对象：

- `WorkflowSpec`
- `WorkflowScript`
- `WorkflowPhase`
- `WorkflowRun`
- `PhaseResult`
- `WorkflowStatus`
- `PhaseStatus`

职责：

- 表达 workflow 的静态合同和运行态。
- 表达 phase 顺序和依赖。
- 表达 phase 结果和 workflow 状态。

不负责：

- 调模型。
- 执行工具。
- 渲染 transcript。

#### D. Workflow Runner

执行 workflow。

职责：

- 校验 phase 顺序。
- 构造 phase prompt。
- 调用 Agent Loop 或 subagent。
- 保存 phase result。
- 根据 success_check、review、verify 结果决定继续、停止或重试。

不负责：

- 直接读写文件。
- 直接运行 shell。
- 绕过 SafetyPolicy。
- 替代 Agent Loop。

#### E. Workflow State

保存 workflow 运行态。

职责：

- 保存原始 task。
- 保存每个 phase 的输入、输出、events、status、error。
- 保存 retry history。
- 支持后续 resume / replay。

第一版可以只保存在内存中；持久化放到后续 Workflow 切片。

#### F. Prompt / Context Composer

把 workflow state 转成当前 phase 的 prompt。

职责：

- 注入原始用户任务。
- 注入当前 phase role 和 instruction。
- 注入前置 phase 的摘要或结果。
- 控制 context 不被无关中间日志污染。

#### G. Agent / Subagent Dispatcher

启动单 agent 或多个 subagents。

职责：

- 根据 phase 选择 agent profile。
- 控制并发数。
- 给每个 subagent 分配 scope。
- 收集 subagent summary。

不负责：

- 合并文件冲突。
- 直接执行工具。
- 替代 Runner 判断下一阶段。

#### H. Result Aggregator

把 agent / subagent 输出转成 phase result。

职责：

- 提取 final answer。
- 提取 verification evidence。
- 汇总 findings。
- 压缩 subagent 输出，避免污染主 workflow context。

#### I. Workflow Templates

把常见工作流固化成可复用模板。

第一批候选：

- `minimal_bugfix`
- `nodeflow_bugfix`
- `review_then_verify`
- `research_then_plan`

NodeFlow 应先作为 script template / manifest 来源，而不是 runtime 依赖。

#### J. Review / Verify / Retry Policy

处理失败路径。

职责：

- review 失败回到 execute。
- verify 失败回到 execute。
- retry 次数有上限。
- 失败原因写入 handoff。

当前切片只保留基础失败停止；retry 放到 Workflow feature 的后续切片。

#### K. Artifact Store

保存 workflow 产物。

职责：

- 保存 phase summaries。
- 保存 plan、review findings、verification results。
- 保存必要的审计信息。

不负责：

- 无条件创建 task-level docs。
- 静默归档或删除文档。

#### L. Workflow CLI / Persistence

让 workflow 可被用户调用和复用。

职责：

- 通过 CLI command 运行 workflow。
- 保存 workflow spec。
- 保存 workflow run。
- 支持 replay / resume。

第一版不做。

### Multi-Agent 边界

multi-agent 的目标不是简单增加 agent 数量，而是解决两个问题：

- 并行探索，提高速度。
- 隔离上下文，减少主线程污染。

适合 multi-agent：

- 代码库探索。
- review 多视角检查。
- 测试失败分析。
- 日志分析。
- 大型文档拆分总结。
- 多方案比较。

不适合直接 multi-agent：

- 多个 agent 同时修改同一核心文件。
- 没有 file ownership 的重构。
- 强一致状态迁移。
- 需要连续单线推理的局部 bugfix。

后续需要补：

- file claims。
- agent scopes。
- merge policy。
- conflict detection。
- summary-only return。

## NodeFlow 到 OpenCAI 的映射

NodeFlow 不应直接成为 OpenCAI 的内部 runtime。更稳的关系是：

```text
NodeFlow skill graph
  -> 提供 workflow template 和 phase 语义

Workflow Planner / Compiler
  -> 把 NodeFlow template 编译成 WorkflowScript + WorkflowSpec manifest

OpenCAI Workflow Runtime
  -> 执行受限 workflow script

Agent Loop
  -> 执行单个 phase
```

映射示例：

| NodeFlow 概念 | OpenCAI workflow 概念 |
| --- | --- |
| `nodeflow` entry / router | workflow template selection / script selection |
| `nodeflow-brainstorming` / `nodeflow-change-spec` | clarify / spec phase |
| `nodeflow-risk-assessment` | risk phase 或 phase metadata |
| `nodeflow-plan` | plan phase |
| `nodeflow-execute` | execute phase |
| `nodeflow-review` | review phase |
| `nodeflow-verify` | verify phase |
| `nodeflow-handoff` | handoff phase |
| checkpoint | phase gate |
| HITL | human-required phase or stop reason |
| document_budget | workflow manifest / template policy |
| retry_count / retry_history | WorkflowRun retry state |

NodeFlow 的长期定位：

```text
NodeFlow = workflow script template library + process policy source
不是 OpenCAI runtime 的底层依赖
```

## 当前切片范围

Phase 13 当前切片只落地串行 workflow runtime，但方向上靠近脚本式 runtime，并保留成熟 workflow 所需的状态、权限、审计、humancheck、retry、保存/恢复和 multi-agent 扩展边界。

### 当前切片目标

证明 OpenCAI 可以在 Agent Loop 外面增加一层 workflow control plane，并为后续脚本式 workflow 保留正确接口：

```text
user task
  -> workflow function / template
  -> runner.run_phase(...)
  -> save PhaseResult
  -> runner.run_phase(...)
  -> save PhaseResult
  -> workflow result
```

当前切片不需要解析外部脚本文件，可以先用内置 workflow function 或 template 模拟脚本控制流。

### 当前切片模块

#### A. Core Data Model

基础对象：

```text
WorkflowSpec
- name
- description
- required_permissions
- audit_phases

WorkflowPhase
- id
- role
- prompt_template
- depends_on
- success_check

WorkflowRun
- task
- status
- phase_results

PhaseResult
- phase_id
- status
- events
- final_answer
- error
```

当前切片状态：

```text
pending | running | passed | failed | skipped
```

#### B. Serial WorkflowRunner

基础行为：

- 暴露 `run_phase(...)` 或等价内部 API。
- 允许内置 workflow function 按顺序调用多个 phase。
- 检查 `depends_on` 是否已 passed。
- 为每个 phase 构造 prompt。
- 调用现有 `run_agent_loop(...)`。
- 从 events 提取 final answer 或 error。
- 保存 `PhaseResult`。
- phase failed 时停止 workflow。

#### C. Phase Prompt Composer

基础 prompt 结构：

```text
Original task:
<user task>

Current phase:
<phase id / role>

Instruction:
<prompt_template>

Previous phase results:
<summaries>
```

当前切片不做复杂 memory、不做上下文压缩算法，但 prompt composer 的边界要允许后续接入 workflow state、artifacts 和压缩结果。

#### D. Toy Workflow Demo

当前切片只需要一个可运行 demo workflow，例如：

```text
inspect -> summarize
```

或：

```text
plan -> execute
```

当前 demo 的目标不是完整 bugfix，而是证明 workflow 层能串联多个 Agent Loop 调用并保留阶段结果；完整 bugfix workflow 已作为后续 Feature A 切片保留。

### 当前切片非目标

- 不做 multi-agent。
- 不做并发。
- 不做 NodeFlow 完整 bugfix workflow。
- 不做 review / verify retry loop。
- 不做持久化 state。
- 不做 CLI workflow command。
- 不做 workflow spec 文件保存。
- 不做模型自动生成 WorkflowSpec。
- 不做后台运行、暂停、恢复。
- 不解析外部 JS / Python orchestration script。
- 不允许 workflow function 直接读写文件或运行命令。

## 后续 Feature 拆分

### Feature A: Workflow

Workflow 是当前主线，目标是把 OpenCAI 的多阶段任务编排做稳。原 Phase 14-17 的内容都归入这个 feature。

下一批切片：

- `/workflow` execute / cancel confirmation gate。
- workflow command flow 拆分。
- humancheck phase。
- NodeFlow bugfix workflow。
- review / verify retry loop。
- workflow command / save / replay。
- LLM-generated WorkflowSpec / WorkflowScript。

NodeFlow 的核心 bugfix 链应落成第一个真实内置 workflow：

```text
clarify -> plan -> execute -> review -> verify -> handoff
```

失败回路：

```text
review failed -> execute
verify failed -> execute
```

并记录 retry history。

### Feature B: Multi-agents

Multi-agents 依赖 Workflow 的 state、dispatcher 和 aggregator，目标是在 workflow runtime 中引入多个 worker。

第一版只做只读并行 inspect / review，不做并行写文件。

- phase 可以启动多个 workers。
- runner 控制并发。
- phase 汇总 subagent summaries。
- worker 必须有明确 scope。
- 结果应 summary-only return，避免污染主 workflow context。

后续再补 file claims、merge policy 和 conflict detection。

### Feature C: Agent Loop Strategy

Agent Loop Strategy 是后置实验，不应打断 Workflow 主线。

目标是在不替换 Runtime、LLMAdapter、Tool Model、Event / Transcript 和 Verification 协议的前提下，抽象 strategy 接口，对比：

- ReAct baseline。
- Plan-and-Execute。
- Verify-first。
- Review-retry。
- WorkflowRunner-backed strategy。

### Feature D: Modes

Modes 从 Runtime 层加载，例如 `learn`、`dev`、`debug`、`review`。Mode 会影响 prompt、默认 workflow、默认 strategy、tool policy、max_steps、verification 要求和 handoff 格式。

原则：

- 先定义 Runtime-level `ModeProfile`。
- Agent Loop 只接收组合后的 task / context / policy，不直接知道 mode 名。
- Mode 不应和 Workflow 形成两套互相竞争的编排系统。

### Feature E: Streaming Outputs

Streaming Outputs 让模型输出、tool events 和 workflow phase progress 可以增量渲染。

原则：

- 引入 `EventSink` 或 generator-style loop。
- 保留当前 `list[Event]` 返回路径，避免一次性破坏测试。
- Renderer 只消费 event stream，不拥有执行逻辑。

### Feature F: LLM Council

LLM Council 支持配置多个模型，并按任务角色分配，例如强模型负责 planning / review，默认模型负责 execute。

第一版只做 role-based model routing：

- Runtime 从单 `adapter` 扩展为 `ModelRegistry` / `AdapterPool`。
- WorkflowPhase 或 ModeProfile 选择 model role。
- plan / review 可用强模型，execute 可用默认模型。
- 暂不做多模型投票或辩论式 council。

### Feature G: Context Engineering

Context Engineering 负责管理 LLM 在不同时间点能看到什么。它不是传统 RAG 的同义词，也不是把所有历史和项目文件塞进 prompt；它是 Runtime、Agent Loop、WorkflowRunner、Modes、Multi-agents 和 memory 之间的 context 合同。

三个模块：

- Session 初始化 context：一次会话或 task 开始时注入 cwd、repo root、项目规则、README/status 摘要、git status、runtime 配置、tool policy 和可用工具说明。
- Session 内持续对话 context：Agent Loop 持续维护 `messages`，让 tool call、tool result / observation、verification result、stop/final 状态进入下一轮 LLM 调用。
- 跨对话 memory：保存长期稳定的用户偏好、项目决策、常用命令和踩坑记录；任务开始或中途按需检索，作为候选线索注入，并对易变事实重新读文件或运行命令验证。

边界：

- Context Provider 只负责收集、筛选、压缩和标注 context。
- Agent Loop 只消费组合后的 messages，不直接拥有 memory 系统。
- WorkflowRunner 可以为每个 phase 组合 scoped context，但不能把 workflow state 等同于聊天上下文。
- Memory 不能直接覆盖当前文件事实；它只提示应该去哪里验证。

学习路线：

```text
Agent Loop messages 增长
  -> Session 初始化 context
  -> Session 内 context 预算和压缩
  -> search_memory 工具协议
  -> 跨对话 memory 验证边界
```

开发路线：

1. 定义最小 `ContextSnapshot`，只覆盖 cwd、repo root、项目规则文件存在性、git status 摘要和 runtime 配置。
2. 定义 `ContextProvider.collect(cwd, task, session)`，先不做 embedding / RAG。
3. 定义 `ContextComposer`，把 system prompt、project context、mode/workflow context 和 user task 组合成初始 messages。
4. 让 Agent Loop 接收可选 initial messages，同时保留当前 `task` 字符串入口。
5. 设计 `search_memory` 工具返回格式：候选 memory、source、confidence、needs_verification。

## 架构原则

- Workflow 是 control plane，Agent Loop 是 execution unit。
- 最终 workflow 主表达是受限 WorkflowScript，WorkflowSpec 是 manifest / safety contract。
- Workflow 不直接执行工具，工具执行仍由 Agent Loop 和 Tool Model 负责。
- Workflow state 不等于聊天上下文；阶段结果要结构化保存。
- Context Engineering 是 Runtime / Workflow / Agent Loop 的输入合同；context 选择发生在执行单元外部，执行单元只消费组合后的 messages。
- NodeFlow 是 workflow script template 来源，不是 OpenCAI runtime 依赖。
- 小任务继续走普通 Agent Loop，大任务才进入 WorkflowRunner。
- 当前切片必须可观察、可测试、可删减；长期设计必须服务完整成熟 Coding Agent，不能用“最小”否定必要的成熟能力。

## 当前切片验收标准

- 新增 workflow core model。
- 新增 serial WorkflowRunner。
- runner 能执行至少两个 phase。
- 每个 phase 都调用现有 Agent Loop。
- 每个 phase 都保存 `PhaseResult`。
- workflow 失败时能明确标记 failed。
- 不修改 `agent_loop.py` 的核心协议。
- 不引入新依赖。
- 有测试或可运行 demo。

## 当前实现状态

截至 2026-06-29，Phase 13 已完成首个可运行切片：

- 新增 `OpenCAI/workflow.py`。
- 已实现 `WorkflowSpec`、`WorkflowPhase`、`WorkflowRun`、`PhaseResult` 和 `SerialWorkflowRunner`。
- `WorkflowSpec.final_phase_id` 作为显式最终收口合同；当前串行 runner 要求 final phase 是最后一个 phase。
- 已新增内置 `inspect -> handoff` workflow：`build_inspect_handoff_workflow()`。
- 已新增 `render_workflow_plan()`，用于 CLI 展示 workflow plan。
- 已新增 `render_workflow_process()`，用于 workflow 完成后展示 final answer 和 phase process summary。
- 已接入 `/workflow TASK`，当前直接运行内置 workflow，不再停留在 preview。
- Agent Loop 的 `max_steps` 截断已改为 `stop` event；WorkflowRunner 遇到 `stop` 会将 phase 标记为 failed。
- 已验证 fake adapter 和 Gemini adapter 均可运行 `/workflow Read README.md`。

当前仍未实现：

- execute / cancel / modify / write in confirmation gate。
- humancheck phase。
- NodeFlow bugfix workflow。
- review / verify retry loop。
- workflow save / replay。
- LLM-generated WorkflowSpec。
- 实时 phase progress renderer 和折叠 UI。

## 新对话交接

新对话继续 Phase 13 时，先读取：

- `AGENTS.md`
- `docs/learning-mode.md`
- `docs/status.md`
- `docs/archive/phases/phase-13-dynamic-workflows.md`
- `OpenCAI/agent_loop.py`
- `OpenCAI/events.py`
- `OpenCAI/llm_adapter.py`

下一刀目标：

```text
为 /workflow 增加 execute / cancel confirmation gate。
保持 /workflow 先展示 plan，再由用户确认是否执行。
不接 LLM-generated WorkflowSpec。
不做 NodeFlow 完整 bugfix workflow。
不做 multi-agent 或后台任务。
```

当前路线口径：

```text
继续 Feature A: Workflow。
不再新增 Phase 14/15/16 作为路线单位。
Modes / Streaming Outputs / LLM Council 先作为候选 feature 评估，不抢 Workflow 主线。
```

建议最小文件范围：

- `OpenCAI/runtime_commands.py`
- `tests/test_runtime_commands.py`
- 必要时复用 `OpenCAI/tui.py` 的 `ask_choice`

建议验证：

- `python -m py_compile OpenCAI\runtime_commands.py OpenCAI\workflow.py tests\test_runtime_commands.py tests\test_workflow.py`
- `python -m unittest tests.test_runtime_commands tests.test_workflow`
- `cmd /c "(echo /workflow Read README.md&echo execute&echo /exit)|python -m OpenCAI"`
- `cmd /c "(echo /workflow Read README.md&echo cancel&echo /exit)|python -m OpenCAI"`
