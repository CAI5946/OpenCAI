# Phase 13: Dynamic Workflows

## 目标

Phase 13 的目标不是立刻复刻 Claude Code Dynamic Workflows，也不是把 NodeFlow 整套 skill graph 搬进 OpenCAI。

本阶段先设计 OpenCAI 的 workflow 架构边界：

- 最终形态：结合 Claude Code Dynamic Workflows 和 NodeFlow，形成完整动态编排 + multi-agent workflow runtime。
- 第一版范围：实现最小串行 `WorkflowSpec` / `WorkflowRunner`，验证 workflow 层可以稳定编排多个 phase。

## 参考样板

### Claude Code Dynamic Workflows

Claude Code Dynamic Workflows 的关键设计是：workflow runtime 执行 orchestration script，由 script 持有计划、中间状态和调度逻辑；具体读文件、改文件、运行命令仍由 agent / subagent 执行。

可借鉴点：

- 编排层在 Agent Loop 外部。
- workflow 持有计划和中间状态，不把所有状态塞进模型上下文。
- subagents 是执行单元，workflow runtime 是 control plane。
- workflow 可以后台运行、保存、复用、暂停、恢复。
- 大任务适合 workflow，小任务仍可直接走普通 Agent Loop。

暂不采用：

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
  -> 流程合同：声明 phase、依赖、权限、成功条件、失败跳转和 checkpoint

WorkflowRunner
  -> 合同执行器：解释 spec，调度 phase，处理重试、阻塞和完成状态

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
  -> WorkflowSpec
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
- WorkflowSpec 可以描述 phase、依赖、角色、工具限制、成功条件和重试策略。
- WorkflowRunner 可以串行或并行调度 phase。
- 每个 phase 可以启动一个 agent 或多个 subagents。
- phase 结果进入 workflow state，而不是只留在聊天上下文里。
- review / verify 失败时可以回到 execute。
- workflow 可以保存、重放、恢复。
- workflow 可以暴露为 CLI command。
- workflow 可以记录最小审计信息：phase 输入、输出、状态、验证证据和失败原因。

### 声明式和脚本式

最终形态允许两种 workflow 表达方式，但默认优先声明式：

```text
Declarative WorkflowSpec
  -> 默认形态，适合保存、验证、审计、回放和从 NodeFlow template 编译。

Constrained WorkflowScript
  -> 后期高级形态，适合循环、条件分支、并发、动态分组和复杂聚合。
```

受限脚本只能调用 workflow runtime API：

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

第一版不做脚本 runtime。脚本式 workflow 只能作为最终形态设计保留。

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

把用户任务、repo context、AGENTS.md、NodeFlow template 和可用 agent profile 编译成 `WorkflowSpec`。

职责：

- 选择 workflow template。
- 生成或调整 WorkflowSpec。
- 保证 workflow 只使用受控 phase、agent profile 和 tool policy。

不负责：

- 执行 workflow。
- 直接调用 tools。
- 直接启动 subagents。

#### C. Workflow Core Model

定义 workflow 的稳定数据结构。

候选对象：

- `WorkflowSpec`
- `WorkflowPhase`
- `WorkflowRun`
- `PhaseResult`
- `WorkflowStatus`
- `PhaseStatus`

职责：

- 表达 workflow 是什么。
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

第一版可以只保存在内存中；持久化放到后续阶段。

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

NodeFlow 应先作为 template 来源，而不是 runtime 依赖。

#### J. Review / Verify / Retry Policy

处理失败路径。

职责：

- review 失败回到 execute。
- verify 失败回到 execute。
- retry 次数有上限。
- 失败原因写入 handoff。

第一版只保留最小失败停止；retry 放到 Phase 15。

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
  -> 把 NodeFlow template 编译成通用 WorkflowSpec

OpenCAI Workflow Runtime
  -> 执行通用 workflow spec

Agent Loop
  -> 执行单个 phase
```

映射示例：

| NodeFlow 概念 | OpenCAI workflow 概念 |
| --- | --- |
| `nodeflow` entry / router | workflow template selection |
| `nodeflow-brainstorming` / `nodeflow-change-spec` | clarify / spec phase |
| `nodeflow-risk-assessment` | risk phase 或 phase metadata |
| `nodeflow-plan` | plan phase |
| `nodeflow-execute` | execute phase |
| `nodeflow-review` | review phase |
| `nodeflow-verify` | verify phase |
| `nodeflow-handoff` | handoff phase |
| checkpoint | phase gate |
| HITL | human-required phase or stop reason |
| document_budget | workflow metadata / template policy |
| retry_count / retry_history | WorkflowRun retry state |

NodeFlow 的长期定位：

```text
NodeFlow = workflow template library + process policy source
不是 OpenCAI runtime 的底层依赖
```

## 第一版范围

Phase 13 第一版只做最小串行 workflow runtime。

### 第一版目标

证明 OpenCAI 可以在 Agent Loop 外面增加一层 workflow control plane：

```text
user task
  -> WorkflowRunner
  -> phase 1 calls run_agent_loop()
  -> save PhaseResult
  -> phase 2 calls run_agent_loop()
  -> save PhaseResult
  -> workflow result
```

### 第一版模块

#### A. Core Data Model

最小对象：

```text
WorkflowSpec
- name
- phases
- max_retries

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

第一版状态：

```text
pending | running | passed | failed | skipped
```

#### B. Serial WorkflowRunner

最小行为：

- 按 `phases` 顺序执行。
- 检查 `depends_on` 是否已 passed。
- 为每个 phase 构造 prompt。
- 调用现有 `run_agent_loop(...)`。
- 从 events 提取 final answer 或 error。
- 保存 `PhaseResult`。
- phase failed 时停止 workflow。

#### C. Phase Prompt Composer

最小 prompt 结构：

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

第一版不做复杂 memory、不做上下文压缩算法。

#### D. Toy Workflow Demo

第一版只需要一个最小 demo workflow，例如：

```text
inspect -> summarize
```

或：

```text
plan -> execute
```

第一版 demo 的目标不是完整 bugfix，而是证明 workflow 层能串联多个 Agent Loop 调用并保留阶段结果。

### 第一版非目标

- 不做 multi-agent。
- 不做并发。
- 不做 NodeFlow 完整 bugfix workflow。
- 不做 review / verify retry loop。
- 不做持久化 state。
- 不做 CLI workflow command。
- 不做 workflow spec 文件保存。
- 不做模型自动生成 WorkflowSpec。
- 不做后台运行、暂停、恢复。
- 不做 JS / Python orchestration script。

## 后续阶段拆分

### Phase 14: NodeFlow Bugfix Workflow

把 NodeFlow 的核心 bugfix 链落成第一个真实内置 workflow：

```text
clarify -> plan -> execute -> review -> verify -> handoff
```

### Phase 15: Review / Verify Retry Loop

实现失败回路：

```text
review failed -> execute
verify failed -> execute
```

并记录 retry history。

### Phase 16: Workflow Command / Save / Replay

让 workflow 可复用：

- CLI 运行 workflow。
- 保存 workflow spec。
- replay 同一个 workflow。

### Phase 17: LLM-generated WorkflowSpec

让模型生成受限 workflow spec，但执行前必须展示并确认。

### Phase 18: Parallel Subagents

引入 multi-agent：

- phase 可以启动多个 workers。
- runner 控制并发。
- phase 汇总 subagent summaries。

## 架构原则

- Workflow 是 control plane，Agent Loop 是 execution unit。
- Workflow 不直接执行工具，工具执行仍由 Agent Loop 和 Tool Model 负责。
- Workflow state 不等于聊天上下文；阶段结果要结构化保存。
- NodeFlow 是 workflow template 来源，不是 OpenCAI runtime 依赖。
- 小任务继续走普通 Agent Loop，大任务才进入 WorkflowRunner。
- 第一版必须可观察、可测试、可删减。

## 第一版验收标准

- 新增 workflow core model。
- 新增 serial WorkflowRunner。
- runner 能执行至少两个 phase。
- 每个 phase 都调用现有 Agent Loop。
- 每个 phase 都保存 `PhaseResult`。
- workflow 失败时能明确标记 failed。
- 不修改 `agent_loop.py` 的核心协议。
- 不引入新依赖。
- 有最小测试或可运行 demo。

## 新对话交接

新对话进入 Phase 13 第一版实现前，先读取：

- `AGENTS.md`
- `docs/learning-mode.md`
- `docs/status.md`
- `docs/phase-13-dynamic-workflows.md`
- `OpenCAI/agent_loop.py`
- `OpenCAI/events.py`
- `OpenCAI/llm_adapter.py`

第一刀目标：

```text
新增 workflow core model 和 serial runner。
不修改 agent_loop.py 的核心协议。
不接 NodeFlow 完整 bugfix workflow。
不做 multi-agent。
```

建议最小文件范围：

- 新增 `OpenCAI/workflow.py`
- 新增 `tests/test_workflow.py`
- 必要时更新 `docs/status.md`

建议验证：

- `python -m py_compile OpenCAI\workflow.py tests\test_workflow.py`
- `python -m unittest tests.test_workflow`

如果第一版接入 Runtime，再追加：

- `python -m py_compile OpenCAI\__main__.py OpenCAI\workflow.py`
- `python -m OpenCAI --help`
