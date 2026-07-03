# Workflow Docs

## 入口分工

- `../Workflow.md`：Workflow feature 的详细设计源，保留完整背景、边界、实现状态和后续计划。
- `../../phases/phase-13-dynamic-workflows.md`：Phase 13 历史设计和学习日志，不再作为当前实现 truth。
- `../../status.md`：当前进度、阻塞、下一步和最近验证的事实源。

## 专题页

- `main-flow.md`：Workflow 主流程。
- `context-in-workflow.md`：Workflow 中 Planner Context 和 Task Context 的分层。
- `planner-output-options.md`：Workflow Planner 输出结构候选项。
- `task-graph-phase-model.md`：Task Graph、Phase 分组、串行 / 并行和聚合策略。
- `workflow-script-and-spec.md`：WorkflowScript 与 WorkflowSpec / Manifest 的分工。
- `module-boundaries.md`：Workflow Intake、Planner、Runner、Controller、State、Policy、Rendering 等模块边界。
- `policy-and-permission.md`：Workflow task / phase scoped tool policy 和权限合并规则。
- `state-and-replay.md`：WorkflowRun 状态账本、artifacts、verification evidence 和 save / replay 边界。
- `claude-code-dynamic-workflows.md`：Claude Code Dynamic Workflows 参考设计。
- `nodeflow-reference.md`：Nodeflow 参考设计和 OpenCAI 映射。

## 维护规则

- 当前事实优先看 `../../status.md`。
- 架构设计优先看 `../Workflow.md`。
- 快速查找具体主题时优先看本目录专题页。
- Phase 文档只作历史背景，不把历史切片内容当作当前实现状态。
