# Task Graph and Phase Model

## 核心原则

Workflow 的底层调度单位是 task，不是 phase。Phase 是语义、策略、展示、context 和 retry 的分组边界。

固定 phase 集合：

```text
clarify / plan / execute / verify / review / handoff
```

不同 workflow 通过组合、跳过和重复进入这些 phase 表达流程差异；具体任务差异由 `WorkflowTask`、skill、tool policy、prompt 和 dependency graph 表达。

## 调度模型

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

规则：

- `WorkflowTask` 是真实调度单位。
- `depends_on` 表达串行 / 并行关系。
- phase 不参与 `depends_on`，不构成第二套执行图。
- phase membership 由 `task.phase_id` 派生。
- `TaskResult` 先汇总为 `PhaseResult`，再汇总为 `WorkflowRun` final answer。
- 当前最终收口由 `final_phase_id` 指定；如果未来 final phase 允许多个 task，再引入 `final_task_id`。

## 串行与并行

串行 / 并行由 dependency graph 表达：

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

短期策略：

```text
Workflow phases: 串行为主
Phase 内 tasks: 先串行
Read-only tasks: 后续允许并行
Write/edit tasks: 暂不并行
```

## 一个 Phase 多 Tasks

一个 phase 多 tasks 用来表达同一阶段目标下的多个具体执行单元。

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

## 聚合策略

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
