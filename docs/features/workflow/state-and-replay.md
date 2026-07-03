# Workflow State and Replay

## WorkflowRun

`WorkflowRun` 是 workflow 的事实账本，不等于聊天上下文，也不等于 prompt。

目标状态：

```text
task
workflow spec / script reference
task graph
phase input
task input
task events
task result
phase events
phase result
artifacts
verification evidence
retry history
stop reason
final handoff
```

## TaskResult

TaskResult 应保存：

- task id。
- phase id。
- status。
- final answer。
- error。
- stop reason。
- events。
- artifacts。
- verification evidence。

## PhaseResult

PhaseResult 是多个 TaskResult 的结构化聚合，不是最后一个 task 的 final answer。

应保存：

- phase id。
- status。
- task results。
- aggregate summary。
- final answer。
- errors。
- artifacts。
- verification evidence。

## Artifacts

Artifacts 用来记录 workflow 产生或使用的重要证据：

- changed files。
- diff summary。
- created files。
- deleted files。
- verification commands。
- review findings。
- open risks。

## Save / Replay

第一版 state 可以只保存在当前进程内。后续 save / replay 需要：

- 稳定 run id。
- 持久化 WorkflowRun。
- 记录 workflow spec / script reference。
- 记录 task inputs / outputs。
- 记录 tool observations 的摘要和必要证据。
- replay 时复用 event history，避免把已执行副作用重复执行。

## 边界

- 完整 events 默认留在 WorkflowRun，不默认进入模型上下文。
- ContextComposer 只从 WorkflowRun 中选择当前 task 需要的输入。
- save / replay 不是普通 session history。
- replay 需要区分“重放状态”和“重新执行工具”。
