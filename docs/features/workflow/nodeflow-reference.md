# Nodeflow Reference

## 参考来源

- Local historical notes: `docs/archive/phases/phase-13-dynamic-workflows.md`
- Local Nodeflow map: `D:\APP_please\Nodeflow\docs\NODE_MAP.md`

## 核心机制

Nodeflow 的价值是把真实开发任务拆成风险自适应的节点图，而不是所有任务都走同一条线性 checklist。

关键特征：

- `nodeflow` 是复杂任务 workflow controller / misfire guard，不是默认 selector。
- 简单、低风险、范围清楚的任务应交回默认 Agent 或直接调用对应能力 skill。
- `nodeflow-*` 节点支持 standalone / direct invocation，不强制依赖完整 state。
- risk assessment 决定流程重量、document budget、execution mode、checkpoint 和验证要求。
- checkpoint 是阶段产物后的人工确认门；HITL 是执行前或执行中的人工决策需求。
- review / verify / validate 可以按 fixability 回到 execute，Nodeflow 是带受控回边的 directed graph。
- 文档按传递价值生成，不是每个任务都创建文档。

## 默认节点链路

典型复杂开发链路：

```text
nodeflow
  -> request-router / brief / brainstorming / bug-diagnose / release-prep
  -> risk-assessment
  -> change-spec / plan
  -> execute
  -> review
  -> verify / validate
  -> handoff
```

常见 phase 映射：

| Nodeflow 概念 | OpenCAI Workflow 概念 |
| --- | --- |
| `nodeflow` entry / router | workflow template selection / script selection |
| `nodeflow-brainstorming` / `nodeflow-change-spec` | clarify / spec phase |
| `nodeflow-risk-assessment` | risk metadata / policy decision |
| `nodeflow-plan` | plan phase |
| `nodeflow-execute` | execute phase |
| `nodeflow-review` | review phase |
| `nodeflow-verify` / `nodeflow-validate` | verify phase |
| `nodeflow-handoff` | handoff phase |
| checkpoint | phase gate |
| HITL | human-required control point |
| document_budget | workflow manifest / template policy |
| retry_count / retry_history | WorkflowRun retry state |

## 对 OpenCAI 的借鉴

可直接吸收的设计：

- complex-only routing，避免所有任务强制进入重 workflow。
- risk-based workflow selection。
- clarify / plan / execute / review / verify / handoff 的阶段语义。
- review / verify 失败回到 execute 的受控 retry loop。
- checkpoint 和 HITL 分离。
- document budget。
- task DAG 和失败传播。
- handoff 输出验证证据、风险和人工检查项。

## 不直接采用

OpenCAI 不应把 Nodeflow 作为 runtime dependency。

不直接采用：

- 完整 `docs/.nodeflow/` 状态系统。
- 完整 Nodeflow skill graph。
- 完整 document cleanup policy。
- 完整 review matrix。
- Nodeflow 的所有节点命名作为 OpenCAI phase。

## OpenCAI 设计结论

Nodeflow 在 OpenCAI 中的定位：

```text
Nodeflow
  -> workflow template library
  -> process policy source

Workflow Planner / Compiler
  -> 把 Nodeflow-style template 编译成 WorkflowScript + WorkflowSpec manifest

OpenCAI Workflow Runtime
  -> 执行受限 workflow script

Agent Loop
  -> 执行单个 task
```

Nodeflow 提供流程经验和阶段策略，不成为 OpenCAI 的底层 runtime。
