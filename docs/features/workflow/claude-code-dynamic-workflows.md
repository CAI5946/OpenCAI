# Claude Code Dynamic Workflows

## 参考来源

- Official docs: https://code.claude.com/docs/en/workflows
- Local historical notes: `docs/archive/phases/phase-13-dynamic-workflows.md`

## 核心机制

Claude Code Dynamic Workflows 的核心是：workflow runtime 执行 orchestration script，由 script 持有计划、中间状态、循环、分支和调度逻辑；具体读文件、改文件、运行命令由 agent / subagent 执行。

关键特征：

- workflow script 由 Claude 为具体任务生成，并可保存后复用。
- workflow 适合代码库级审计、大规模迁移、跨来源研究、互相校验的多 agent 工作。
- workflow 把 orchestration 从主对话 context 中移出，避免所有中间结果进入同一个上下文窗口。
- workflow runtime 可在后台执行，用户可查看 phase / agent 进度。
- workflow 可以先展示 plan / phase list，再由用户决定是否执行。
- workflow 中间结果保存在 script variables / runtime state，而不是默认进入模型聊天上下文。
- workflow script 负责协调 agent；文件、命令和工具动作仍由 agent 执行。

## 对 OpenCAI 的借鉴

OpenCAI 应借鉴的是 control-plane 分层，而不是直接复制 Claude Code 的 JavaScript runtime：

```text
WorkflowScript
  -> 编排主体：流程、分支、循环、并发、聚合和 retry

WorkflowRunner
  -> 受限 runtime：执行 workflow control flow

Agent / Subagent Loop
  -> 单 task 执行单元

Tool Model + SafetyPolicy
  -> 真实动作和权限裁决
```

可直接吸收的设计：

- script-first 表达复杂 workflow。
- workflow state 与聊天 context 分离。
- subagent / task context 隔离。
- plan preview 和执行确认。
- phase / agent progress view。
- workflow script 可保存、复用、对比和重跑。
- runtime 对并发 agent、总 agent 数和 runaway loop 设置上限。

## 不直接采用

当前 OpenCAI 不直接采用：

- Claude Code 的 JavaScript workflow script 格式。
- Claude Code 的后台任务系统。
- Claude Code 的 saved workflow command 目录结构。
- 大规模并发 subagent。
- 自动为所有 substantive task 启动 workflow。

## OpenCAI 设计结论

OpenCAI 的对应形态：

```text
Constrained WorkflowScript
  -> 主表达层

WorkflowSpec / Manifest
  -> metadata / schema / permission / safety contract

WorkflowRunner
  -> 受限脚本运行时

Agent Loop
  -> task execution unit

Tool Model
  -> only action layer
```

脚本只能编排 agent，不能直接读写文件、运行 shell、访问网络、读取 secrets 或绕过 SafetyPolicy。
