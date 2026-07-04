# Workflow

## Feature 目标

Workflow 负责把标准开发流程提升为可确认、可观察、可恢复、可审计的 runtime control layer。

OpenCAI Workflow 的产品定位是稳定开发流程 runtime，不是通用流程引擎，也不是 Claude Code 重型 workflow 的复刻。固定基础流程是为了让系统能针对 Coding Agent 的日常开发任务做深度优化：phase policy、scoped context、验证证据、失败恢复、过程显示和规范化 handoff。

目标不是让用户或模型表达任意 DAG，也不是把复杂流程塞进 `agent_loop.py`。Workflow 的长期目标是支撑成熟 Coding Agent 的稳定开发能力：

- 小任务继续直接走普通 Agent Loop。
- 多阶段、高风险、需要验证或需要 humancheck 的开发任务进入 WorkflowRunner。
- Workflow Runtime 持有计划、中间状态、phase result、验证证据和 retry history。
- 每个 task 仍通过 Agent Loop 执行真实模型/工具闭环。
- 文件、命令、编辑、web、skill、MCP 和 subagent 动作继续通过 Tool Model 和 SafetyPolicy 管控。
- 后续优先扩展 Nodeflow-style bugfix workflow、review/verify retry loop、save/replay 和只读 multi-agent inspect / review；受限 WorkflowScript 属于后置能力，不是当前主线默认表达。

## 设计边界

Workflow 的成功标准是提高开发任务稳定性，而不是提高流程表达能力。

```text
稳定开发流程 runtime
  -> 让 Coding Agent 更少做错、更容易验证、更容易恢复

通用流程引擎
  -> 让用户或模型表达任意节点、任意分支、任意并发
```

OpenCAI 选择前者。Task graph、dependency 和 retry 是内部执行结构；用户主要心智应是稳定开发流程，而不是自定义流程平台。

固定基础 phase vocabulary：

```text
clarify / plan / execute / review / verify / handoff
```

这些 phase 可以按 workflow template 组合、跳过、重复和回环，但不允许随任务自由扩张成 diagnose、research、release、docs、benchmark 等新顶层 phase。具体差异应落在 task kind、phase prompt、tool policy、verification rule 或 workflow template。

## 参考设计映射

### Claude Code Dynamic Workflows

Claude Code Dynamic Workflows 的关键点是：workflow runtime 执行 orchestration script；script 持有计划、中间状态和调度逻辑；具体读文件、改文件、运行命令仍由 agent / subagent 执行。

OpenCAI 借鉴的原则：

- Workflow 是 control plane，不是工具执行层。
- Workflow state 不等于聊天上下文；phase result 应结构化保存。
- Agent / subagent 是执行单元，继续跑 `model -> tool_call -> observation -> model`。
- workflow 可以先展示计划，再由用户确认执行。
- workflow 可以保存、重放、暂停、恢复和后台运行，但这些能力分阶段实现。

当前不直接采用：

- JavaScript orchestration runtime。
- 后台任务系统。
- 自动生成复杂 workflow script。
- 并发写文件型 multi-agent。
- 完整 pause / resume / replay。

### NodeFlow

NodeFlow 的价值是把真实开发任务拆成风险自适应的节点图，而不是所有任务都走同一条线性流程。

OpenCAI 借鉴的原则：

- `clarify -> plan -> execute -> review -> verify -> handoff` 适合作为 bugfix / feature workflow 模板。
- review / verify 失败可以回到 execute。
- checkpoint 和 HITL 要区分：checkpoint 是阶段产物 review，HITL 是执行前或执行中必须由人判断/授权的事项。
- 文档和状态记录应按任务价值生成，不是每次 workflow 都创建大量文件。

NodeFlow 在 OpenCAI 里的定位不是 runtime dependency，而是 workflow template library 和 process policy source。

## 核心架构

Workflow 的最终形态按控制权分层：

```text
WorkflowSpec
  -> 静态合同：metadata、schema、权限、可审计 phase、安全边界

WorkflowScript
  -> 后置扩展：受限流程脚本，用于表达固定开发流程内的分支、循环、聚合和 retry

WorkflowRunner
  -> 稳定开发流程运行时：选择模板，调度 task / phase group，处理状态、失败和完成

WorkflowRun
  -> 执行账本：保存 task result、phase result、artifact、verification 和 retry history

Agent / Subagent Loop
  -> 单 task 执行单元：model -> tool_call -> observation -> model

Tool Model
  -> 真实动作层：read_file / edit_file / run_command / invoke_skill 等
```

## 主流程

```text
1. 用户显式输入 `/workflow TASK`。

2. Runtime command parser 识别 `/workflow`。
   - 进入 workflow command flow。
   - 不经过 `run_command`。

3. Workflow Intake 判断是否进入 workflow。
   - 当前显式 `/workflow` 直接进入。
   - 未来普通任务也可自动路由到 workflow。

4. Workflow Planner / Compiler 生成 workflow plan。
   - 选择内置开发 workflow template。
   - 输出 WorkflowSpec manifest + 模板函数。
   - 未来可在固定开发流程边界内生成受限 WorkflowScript。

5. 展示 workflow plan。
   - 当前直接执行。
   - 后续通过统一 human decision / control point 支持 execute / cancel / modify。

6. WorkflowRunner 执行 workflow。
   - 读取 task graph。
   - 当前按 `spec.tasks` 串行执行。
   - 检查 task `depends_on`。
   - 为每个 task 注入 scoped prompt / context / tool policy。

7. 每个 task 启动 Agent Loop 或未来 subagent。
   - task 内部仍是 `model -> tool_call -> observation -> model`。
   - 工具调用继续走 Tool Model + SafetyPolicy。

8. PhaseResult 结构化保存。
   - 保存 final answer、error、stop reason、events、artifacts 和 verification。
   - 汇总后传给后续 phase。

9. review / verify 可触发 retry。
   - 失败回到 execute。
   - 受 `max_retries` 和 policy 限制。

10. 最终 phase 收口。
    - 推荐命名为 handoff。
    - 架构上应由 `final_phase_id` 指定，不硬编码只能叫 handoff。

11. WorkflowRun 生成 final answer。
    - 返回给用户。
    - 同时保留 workflow process / state / replay 证据。
```

## Task Graph 与 Phase 分组

Workflow 的底层调度单位应是 task，而不是 phase。Phase 保留为语义、策略、展示、context 和 retry 的分组边界。

OpenCAI Workflow 采用固定 phase taxonomy，不允许每个 workflow 随意自定义 phase 名称。固定 phase 集合为：

```text
clarify / plan / execute / review / verify / handoff
```

不同 workflow 通过组合、跳过和重复进入这些 phase 来表达流程差异；具体任务差异由 `WorkflowTask`、skill、tool policy、prompt 和 dependency graph 表达，而不是通过新增 phase 表达。例如 release、debug、refactor、security scan、benchmark 和 docs update 都不应成为新 phase，而应成为 workflow template、task kind 或 skill selection。

最终原则：

- task 是唯一调度单位。
- task dependencies 构成唯一 DAG。
- phase 不参与 `depends_on`，不构成第二套执行图。
- phase membership 由 `task.phase_id` 派生。
- phase 是带语义和策略的 task group，不是普通 list container。
- 每个 phase 的 task 注入对应 phase prompt，例如 clarify / plan / execute / review / verify / handoff 的阶段执行原则。
- 每个 task 可绑定不同 skill、tool policy 和 task prompt，执行不同具体任务。
- `TaskResult` 先汇总为 `PhaseResult`，再汇总为 `WorkflowRun` final answer。

推荐模型：

```text
Workflow
  -> Task Graph
      -> WorkflowTask
      -> TaskResult
  -> Semantic Groups / Phases
      -> phase kind
      -> default policy
      -> aggregation policy
      -> display group
```

核心判断：

- `WorkflowTask` 是真实调度单位。
- `depends_on` 表达串行 / 并行关系。
- `Phase` / `kind` / `group` 表达任务属于 clarify、plan、execute、verify、review 还是 handoff。
- `PhaseResult` 是多个 `TaskResult` 的结构化聚合，不是最后一个 task 的 final answer。
- 当前最终收口由 `final_phase_id` 指定，且 final phase 第一版应只有一个 handoff task；如果未来 final phase 允许多个 task，再引入 optional `final_task_id` 指定 workflow final answer 来源。

### 串行与并行

串行 / 并行不应靠自然语言描述，而应由 dependency graph 表达：

```text
inspect_code -> edit_implementation -> run_tests
inspect_tests -> edit_implementation
```

调度规则：

- 没有未完成依赖的 task 可以调度。
- read-only inspect / review task 后续可以并行。
- write / edit task 默认不并行，除非已有 file claim、merge policy 和冲突恢复机制。
- review / verify 可以读取并行结果，但不应和 execute 写操作并行。
- task group 可以设置 `max_parallelism`。

短期实现策略：

```text
Workflow phases: 串行为主
Phase 内 tasks: 先串行
Read-only tasks: 后续允许并行
Write/edit tasks: 暂不并行
```

### 一个 Phase 多 Tasks

一个 phase 多 tasks 用来表达“同一阶段目标下，有多个具体执行单元”。

示例：

```text
phase: execute
goal: 完成实现改动

tasks:
  inspect_target_files
    tool_policy: read_only
    depends_on: none

  inspect_tests
    tool_policy: read_only
    depends_on: none

  edit_implementation
    tool_policy: write_allowed
    depends_on: inspect_target_files, inspect_tests

  update_tests
    tool_policy: write_allowed
    depends_on: inspect_tests, edit_implementation

  run_verification
    tool_policy: command_allowed
    depends_on: edit_implementation, update_tests
```

对应结果结构：

```text
PhaseResult(execute)
  status: passed
  task_results:
    - inspect_target_files: passed
    - inspect_tests: passed
    - edit_implementation: passed
    - update_tests: passed
    - run_verification: passed
  aggregate_summary:
    "已完成实现、测试更新和验证。"
  artifacts:
    changed_files:
      - OpenCAI/runtime_commands.py
      - tests/test_runtime_commands.py
  verification:
    commands:
      - python -m unittest tests.test_runtime_commands
  handoff_context:
    "review phase 重点检查 /workflow execute/cancel 的非 TTY 行为。"
```

### 聚合策略

Phase / group 需要声明 `aggregation_policy`：

```text
all_must_pass
any_can_pass
best_effort
collect_findings
human_decision
```

常见规则：

- `execute`：required tasks 默认 `all_must_pass`。
- `review`：默认 `collect_findings`，blocking finding 会让 phase failed。
- `verify`：默认 `all_must_pass`。
- optional task 失败可以产生 warning，不一定让 phase failed。
- review / verify failed 可以按 retry policy 路由回 execute。

## Workflow Context Engineering

Workflow context 不能只是启动时注入一份静态 prompt。每个 task 执行前都应根据 workflow state 和依赖关系动态组合 scoped context。

分层：

```text
Static Workflow Context
  -> workflow 启动前确定

Dynamic Task Context
  -> 每个 task 执行前，根据依赖关系即时组装
```

静态 context 包括：

- 用户原始任务。
- project / global instructions。
- cwd / repo / git 状态。
- runtime config。
- mode profile。
- workflow spec / script。
- task graph。
- permission profile。
- 可用工具和 skills 摘要。

动态 context 来自 `WorkflowRun` 事实账本：

- direct dependency task summaries。
- transitive dependency compressed summaries。
- phase aggregate summaries。
- artifacts / changed files / diff summary。
- verification command、exit code 和 concise output。
- review findings、severity 和 blocker status。
- open items、errors、stop reason。

推荐组件：

```text
WorkflowRunner
  -> TaskContextComposer
  -> Agent Loop
```

推荐数据结构：

```text
ContextBlock
  id
  kind
  source_type: static | task_result | phase_result | artifact | verification | finding
  source_id
  content
  priority
  token_cost
  visibility

TaskContextRequest
  workflow_id
  task_id
  dependencies
  allowed_sources
  budget
  purpose

TaskContext
  messages
  included_blocks
  omitted_blocks
  truncation_notes
```

依赖注入规则：

- direct dependencies 默认注入较详细 summary。
- transitive dependencies 默认注入压缩 summary。
- unrelated tasks 默认不注入。
- failed dependencies 注入 error / stop reason / partial artifacts。
- verification task 注入 command / exit code / concise output。
- review task 注入 findings / blocker status。
- 完整 events 留在 `WorkflowRun`，只在 `/process`、debug 或 replay 时展开。

核心原则：

- WorkflowRun 是事实账本。
- Context 是从事实账本里为当前 task 选择出来的输入。
- 不把 workflow state 等同于 prompt。
- 不把完整 transcript 当默认上下文。
- 每个 task 的 context 必须可观察、可解释、可复现。

## 模块边界

### A. Workflow Intake

```text
判断任务是否需要 workflow。

职责：

1. 区分小任务、复杂任务、高风险任务和需要验证的任务。
2. 选择普通 Agent Loop 或 WorkflowRunner。
3. 后续接入 mode、permission profile、benchmark failure type 和 user command。

不负责：

1. 执行 phase。
2. 直接调用 tools。
3. 直接修改文件。
```

### B. Workflow Planner / Compiler

```text
把用户任务、repo context、AGENTS.md、mode、workflow template 和可用 agent profile 编译成 workflow plan。

职责：

1. 选择内置 workflow template。
2. 生成或调整 WorkflowSpec。
3. 未来在固定开发流程边界内生成或调整受限 WorkflowScript。
4. 校验 workflow 只使用允许的 phase、agent profile 和 tool policy。

不负责：

1. 执行 workflow。
2. 直接启动 subagent。
3. 直接调用 tools。
```

### C. Workflow Core Model

```text
定义稳定数据结构。

核心对象：

1. WorkflowSpec
2. WorkflowScript
3. WorkflowPhase
4. WorkflowTask
5. WorkflowRun
6. TaskResult
7. PhaseResult
8. WorkflowStatus
9. PhaseStatus

当前已有 `WorkflowSpec`、`WorkflowPhase`、`WorkflowTask`、`WorkflowRun`、`TaskResult`、`PhaseResult` 和 `SerialWorkflowRunner`。Task 是唯一执行单位，phase 只作为语义、策略、展示和聚合分组。

后续应避免把 `WorkflowSpec` 做成过重的声明式 DSL，也不应把 OpenCAI 做成通用 WorkflowScript 平台。当前主表达是稳定开发流程 template + `WorkflowSpec` manifest；受限 `WorkflowScript` 只作为后置扩展，用于表达固定开发流程内确实需要的分支、循环和聚合。
```

### D. Workflow Runner

```text
执行 workflow control plane。

职责：

1. 校验 workflow。
2. 调度 task / phase group。
3. 为每个 task 组合 prompt / scoped context。
4. 调用 Agent Loop 或未来 subagent dispatcher。
5. 汇总 task result 和 phase result。
6. 处理 stop / error / retry / skipped / failed。
7. 决定 workflow final answer。

不负责：

1. 直接读写文件。
2. 直接运行命令。
3. 绕过 SafetyPolicy。
4. 持有 provider-specific LLM response 结构。
```

### E. Workflow Controller

```text
RuntimeSession 级 workflow 控制器。

职责：

1. 管理 /workflow 的 plan / execute / cancel / status / replay flow。
2. 为 workflow_execute、workflow_status、workflow_cancel、workflow_replay 等工具提供 runtime control integration。
3. 生成 workflow run id。
4. 持有当前 session 内 active / last workflow state。

不负责：

1. 定义 workflow 模板。
2. 执行真实工具。
3. 做模型决策。
```

### F. Workflow State Store

```text
保存 workflow run 的可审计状态。

目标状态：

1. task
2. workflow spec / script reference
3. task graph
4. phase input
5. task input
6. task events
7. task result
8. phase events
9. phase result
10. artifacts
11. verification evidence
12. retry history
13. stop reason
14. final handoff

第一版可以只保存在当前进程内；save/replay 阶段再落到 `.opencai/` 或明确的 runs 目录。
```

### G. Workflow Policy

```text
定义 phase-level 权限和失败处理策略。

职责：

1. phase tool allowlist。
2. task tool allowlist。
3. permission profile 合并。
4. read-only review phase。
5. write-enabled execute phase。
6. verification-required handoff。
7. humancheck gate。
8. retry budget。

最终规则：

effective_tool_policy =
  global permission profile
  + mode profile
  + workflow phase policy
  + workflow task policy
  + skill allowed-tools
  + subagent role policy

最终裁决仍由 Runtime / SafetyPolicy 负责。
```

### H. Workflow Rendering

```text
展示 workflow 可观察状态。

职责：

1. plan preview。
2. execute / cancel confirmation。
3. phase progress。
4. compact process summary。
5. expanded phase transcript。
6. final answer / handoff。

Renderer 只消费 event stream 和 workflow state，不拥有执行逻辑。
```

## WorkflowTemplate、WorkflowScript 与 WorkflowSpec

当前默认采用 template-first：

```text
WorkflowTemplate = 主表达，封装稳定开发流程
WorkflowSpec = metadata / schema / manifest / safety contract
WorkflowScript = 后置扩展，只表达固定开发流程内的受限动态控制流
WorkflowRunner = 稳定开发流程运行时
Agent Loop = task execution unit
Tool Model = action layer
```

受限 WorkflowScript 不是当前主线能力。未来如果引入，只能调用 runtime API，例如：

```text
run_phase()
run_agent()
run_subagents()
wait_all()
review()
verify()
set_state()
get_state()
handoff()
```

受限 WorkflowScript 不能：

- 直接读写文件。
- 直接运行 shell。
- 直接访问网络。
- 任意 import 本地库。
- 读取环境变量或 secrets。
- 绕过 Agent Loop、Tool Model 或 SafetyPolicy。

脚本的用途是表达开发流程内的少量动态控制，而不是让 OpenCAI 变成通用流程引擎。

## 当前实现

已完成第一组可运行切片：

- `OpenCAI/workflow.py`
  - 定义 `WorkflowSpec`、`WorkflowPhase`、`WorkflowTask`、`WorkflowRun`、`TaskResult` 和 `PhaseResult`。
  - 实现 `SerialWorkflowRunner`。
  - 实现内置 `inspect -> handoff` workflow；`inspect` phase 当前包含 `inspect_context` 和 `inspect_constraints` 两个 task，`handoff` phase 包含单个 `handoff_summary` task。
  - 支持 task dependency 检查。
  - 支持 `TaskResult` 聚合为 `PhaseResult`。
  - 支持 `final_phase_id` 显式收口。
  - 将 task `error` / `stop` / 缺少 final answer 映射为 failed。

- `OpenCAI/runtime_commands.py`
  - 保留 `/workflow TASK` 兼容入口，并委托 `workflow_commands.py` 执行 workflow command flow。

- `OpenCAI/composer.py`
  - `parse_user_input()` 已将 `/workflow TASK` 识别为结构化 `WorkflowCommandInput`。
  - 普通 slash command 继续识别为 `RuntimeCommandInput`。

- `OpenCAI/workflow_planner.py`
  - `compile_workflow(task)` 已作为 Planner / Compiler V1 边界。
  - 当前只返回内置 `inspect_handoff` `WorkflowSpec`，不做自动模板选择或 LLM 生成。

- `OpenCAI/workflow_commands.py`
  - 接入 `/workflow TASK` workflow command flow。
  - 空 task 输出 `No task for workflow. Usage: /workflow TASK`，不启动 WorkflowRunner。
  - 通过 `compile_workflow(task)` 获取 `WorkflowSpec`，再交给 `SerialWorkflowRunner` 执行。
  - 当前展示 plan 后直接执行内置 workflow。

- `OpenCAI/tooling/workflow_tools.py`
  - `workflow_plan` 已可渲染当前内置 workflow，并返回 phases / tasks 结构。
  - `workflow_execute`、`workflow_status`、`workflow_pause`、`workflow_resume`、`workflow_cancel`、`workflow_replay` 已作为 deferred tools 注册，等待 RuntimeSession workflow controller 接入。

## 当前边界

- `/workflow TASK` 当前仍是 plan 后直接执行，尚未加入 execute / cancel confirmation gate。
- 当前只有内置 `inspect -> handoff` workflow。
- 当前 task 是唯一执行单位，phase 只作为语义、策略、展示和聚合分组。
- 当前 task graph 只按 spec.tasks 串行执行；尚未支持并行调度。
- 没有 Nodeflow bugfix workflow。
- 没有 review / verify retry loop。
- 没有 humancheck phase。
- 没有 workflow save / replay。
- 没有受限 WorkflowScript runtime。
- 没有 LLM-generated WorkflowSpec / WorkflowScript。
- 没有 dependency-aware task context composer。
- 没有 workflow task / phase scoped tool allowlist。
- 没有 multi-agent dispatcher。
- workflow process renderer 仍是 compact summary，不是实时 phase progress view。

## 后续计划

优先顺序：

1. 实现 dependency-aware `TaskContextComposer`。
2. 实现 task / phase scoped tool allowlist 和 policy 合并。
3. 实现内置 Nodeflow bugfix workflow：`clarify -> plan -> execute -> review -> verify -> handoff`。
4. 实现 review / verify 失败回到 execute 的 retry loop。
5. 设计统一 human decision / control point，再为 `/workflow TASK` 增加 execute / cancel confirmation gate。
6. 引入 RuntimeSession workflow controller，接通 `workflow_execute` / `workflow_status` / `workflow_cancel` 的 runtime 边界。
7. 设计 WorkflowRun state store，支持 workflow save / replay。
8. 在 Workflow 主干稳定后，引入只读 parallel inspect / review subagents。
9. 评估受限 WorkflowScript 是否仍有必要；只有固定 template 无法表达常见开发流程时再设计。

## 验证

当前已有测试应覆盖：

- workflow plan 渲染。
- workflow process summary 渲染。
- 串行 phase 执行顺序。
- task dependency graph 调度。
- 多 task phase aggregation。
- dependency-aware task context composition。
- dependency 缺失时 skipped / failed。
- phase error event 映射为 failed。
- stop event 映射为 failed。
- 缺少 final answer 映射为 failed。
- invalid final phase 映射为 failed。
- `/workflow TASK` runtime command 路径。
- `workflow_plan` tool registration 和 deferred workflow tools exposure。

修改 Workflow 代码后优先运行：

```powershell
python -m py_compile OpenCAI\workflow.py OpenCAI\runtime_commands.py tests\test_workflow.py tests\test_runtime_commands.py
python -m unittest tests.test_workflow tests.test_runtime_commands
cmd /c "(echo /workflow Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"
```

实现 confirmation gate 后增加：

```powershell
cmd /c "(echo /workflow Read README&echo execute&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"
cmd /c "(echo /workflow Read README&echo cancel&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"
```

## 文档维护规则

- Workflow 的功能设计、边界和路线维护在本文档。
- `docs/archive/phases/phase-13-dynamic-workflows.md` 保留为 Phase 13 历史设计和学习日志。
- `docs/status.md` 只记录当前进度、阻塞、下一步和最近验证。
- `docs/features/Tools.md` 只保留 workflow tools 作为工具分类和 Tool Model 边界的一部分。
- Workflow context 的 workflow-specific 设计维护在本文档；通用 Context Engineering 合同维护在 `docs/features/Context Engineering.md`。
- 不把 workflow 编排塞进 `agent_loop.py`。
- 不把 NodeFlow 整套状态系统作为 OpenCAI runtime dependency。
