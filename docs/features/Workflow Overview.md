# Workflow Overview

## 目标和边界

Workflow 是 OpenCAI 在 Agent Loop 之上的 runtime control plane，用来处理多阶段、高风险、需要验证、需要 humancheck 或需要失败恢复的开发任务。

核心边界：

- `/workflow TASK` 是 Runtime command，不经过 `run_command`。
- WorkflowRunner 负责编排 task，不直接执行工具。
- Agent Loop / subagent 负责执行单个 task。
- Tool Model + SafetyPolicy 负责真实动作，例如读文件、改文件、运行命令和调用 skill。
- WorkflowRun 保存事实账本，Context Composer 从账本中选择当前 task 需要的输入。

## 主流程

```text
/workflow TASK
  -> Runtime command parser
  -> Workflow command controller
  -> Workflow Planner / Compiler
  -> plan preview
  -> execute / cancel gate
  -> WorkflowRunner
      -> build task graph
      -> find ready tasks
      -> compose task context
      -> run Agent Loop / subagent
      -> save TaskResult
      -> aggregate group / phase result
      -> schedule next tasks
  -> final_task_id / final_phase_id
  -> final answer + workflow state
```

关键分支：

```text
review failed
  -> route back to execute task/group
  -> bounded by retry policy

verify failed
  -> route back to execute task/group
  -> preserve failed command evidence
```

## 核心架构

```text
WorkflowSpec
  -> metadata / schema / manifest / safety contract

WorkflowScript
  -> future orchestration body for branching, loops, parallelism and aggregation

WorkflowRunner
  -> constrained runtime that schedules tasks and handles workflow state

WorkflowTask
  -> real scheduling unit

Phase / kind / group
  -> semantic, policy, UI, context and retry grouping

Agent Loop / Subagent
  -> execution unit for one task

Tool Model
  -> action layer controlled by SafetyPolicy
```

## Task / Phase 模型

OpenCAI 的 Workflow 应采用 task-first 模型：

- `WorkflowTask` 是底层调度单位。
- `depends_on` 表达串行和并行关系。
- `Phase` / `kind` / `group` 不是唯一执行单位，而是语义和策略分组。
- 一个 phase 可以包含多个 tasks。
- `PhaseResult` 是多个 `TaskResult` 的聚合，不是最后一个 task 的 final answer。
- `final_task_id` 或 `final_phase_id` 显式指定最终收口，不硬编码只能叫 handoff。

短期并行策略：

- phase 串行为主。
- phase 内 tasks 先串行。
- read-only inspect / review tasks 后续可并行。
- write / edit tasks 暂不并行，等 file claim、merge policy 和冲突恢复成熟后再做。

## Context 策略

Workflow context 分成两层：

```text
Static Workflow Context
  -> workflow 启动前确定

Dynamic Task Context
  -> 每个 task 执行前按依赖关系即时组装
```

静态 context 包括用户原始任务、project/global instructions、runtime config、workflow spec、task graph、permission profile、工具和 skills 摘要。

动态 context 来自 WorkflowRun 账本：

- direct dependencies：注入较详细 summary。
- transitive dependencies：注入压缩 summary。
- unrelated tasks：默认不注入。
- verification：注入 command、exit code 和 concise output。
- review：注入 findings、severity 和 blocker status。
- failed task：注入 error、stop reason 和 partial artifacts。

原则：

- WorkflowRun 是事实账本。
- Context 是从事实账本中为当前 task 选择出来的输入。
- 不把完整 transcript 当默认上下文。
- 每个 task 的 context 必须可观察、可解释、可复现。

## 当前实现

已完成：

- `WorkflowSpec`
- `WorkflowPhase`
- `WorkflowRun`
- `PhaseResult`
- `SerialWorkflowRunner`
- 内置 `inspect -> handoff` workflow
- `/workflow TASK` runtime command
- `workflow_plan` tool
- deferred workflow tools：`workflow_execute`、`workflow_status`、`workflow_cancel`、`workflow_replay`

## 当前缺口

- `/workflow` execute / cancel confirmation gate。
- `workflow_commands.py` command flow 分离。
- `WorkflowTask` / `TaskResult`。
- task dependency graph。
- `PhaseResult` 对多个 `TaskResult` 的结构化聚合。
- dependency-aware `TaskContextComposer`。
- task / phase scoped tool policy。
- review / verify retry loop。
- workflow save / replay。
- 受限 WorkflowScript runtime。

## 下一步

1. 为 `/workflow TASK` 增加 execute / cancel confirmation gate。
2. 拆出 `workflow_commands.py`。
3. 引入 `WorkflowTask` / `TaskResult`。
4. 引入 task dependency graph，先串行执行，预留 read-only 并行。
5. 实现 dependency-aware `TaskContextComposer`。
6. 实现 `PhaseResult` 聚合多个 `TaskResult`。
7. 接入 task / phase scoped tool policy。
8. 实现 review / verify retry loop。

## 验证

修改 Workflow 代码后优先运行：

```powershell
python -m py_compile OpenCAI\workflow.py OpenCAI\runtime_commands.py tests\test_workflow.py tests\test_runtime_commands.py
python -m unittest tests.test_workflow tests.test_runtime_commands
cmd /c "(echo /workflow Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"
```

## 文档分工

- 本文是 Workflow feature 的精简入口页，保留稳定结论和主流程。
- `docs/features/Workflow.md` 保留更详细的设计草稿。
- `docs/phases/phase-13-dynamic-workflows.md` 保留 Phase 13 历史设计和学习日志。
- `docs/status.md` 只记录当前进度、阻塞、下一步和最近验证。
