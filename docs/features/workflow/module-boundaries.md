# Workflow Module Boundaries

## A. Workflow Intake

职责：

- 区分小任务、复杂任务、高风险任务和需要验证的任务。
- 选择普通 Agent Loop 或 WorkflowRunner。
- 后续接入 mode、permission profile、benchmark failure type 和 user command。

不负责：

- 执行 phase。
- 直接调用 tools。
- 直接修改文件。

## B. Workflow Planner / Compiler

职责：

- 选择内置 workflow template。
- 生成或调整 WorkflowSpec。
- 未来生成或调整受限 WorkflowScript。
- 校验 workflow 只使用允许的 phase、agent profile 和 tool policy。

不负责：

- 执行 workflow。
- 直接启动 subagent。
- 直接调用 tools。

## C. Workflow Core Model

核心对象：

- `WorkflowSpec`
- `WorkflowScript`
- `WorkflowPhase`
- `WorkflowTask`
- `WorkflowRun`
- `TaskResult`
- `PhaseResult`
- `WorkflowStatus`
- `PhaseStatus`

当前已有 `WorkflowSpec`、`WorkflowPhase`、`WorkflowTask`、`WorkflowRun`、`TaskResult`、`PhaseResult` 和 `SerialWorkflowRunner`。

## D. Workflow Runner

职责：

- 校验 workflow。
- 调度 task / phase group。
- 为每个 task 组合 prompt / scoped context。
- 调用 Agent Loop 或未来 subagent dispatcher。
- 汇总 task result 和 phase result。
- 处理 stop / error / retry / skipped / failed。
- 决定 workflow final answer。

不负责：

- 直接读写文件。
- 直接运行命令。
- 绕过 SafetyPolicy。
- 持有 provider-specific LLM response 结构。

## E. Workflow Controller

RuntimeSession 级 workflow 控制器。

职责：

- 管理 `/workflow` 的 plan / execute / cancel / status / replay flow。
- 为 workflow tools 提供 runtime control integration。
- 生成 workflow run id。
- 持有当前 session 内 active / last workflow state。

## F. Workflow State Store

保存 workflow run 的可审计状态。第一版可以只保存在当前进程内；save / replay 阶段再落到 `.opencai/` 或明确的 runs 目录。

## G. Workflow Policy

定义 phase-level 权限和失败处理策略。

职责：

- phase tool allowlist。
- task tool allowlist。
- permission profile 合并。
- read-only review phase。
- write-enabled execute phase。
- verification-required handoff。
- humancheck gate。
- retry budget。

最终裁决仍由 Runtime / SafetyPolicy 负责。

## H. Workflow Rendering

职责：

- plan preview。
- execute / cancel confirmation。
- phase progress。
- compact process summary。
- expanded phase transcript。
- final answer / handoff。

Renderer 只消费 event stream 和 workflow state，不拥有执行逻辑。
