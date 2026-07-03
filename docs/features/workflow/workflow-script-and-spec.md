# WorkflowScript and WorkflowSpec

## 分工

最终默认采用 script-first：

```text
WorkflowScript = 主表达
WorkflowSpec = metadata / schema / manifest / safety contract
WorkflowRunner = 受限脚本运行时
Agent Loop = phase execution unit
Tool Model = action layer
```

## WorkflowScript

WorkflowScript 用来表达编排主体：流程、分支、循环、并发、聚合和 retry。它适合承载 Claude Code-style dynamic workflow 的层级结构。

受限 WorkflowScript 只能调用 runtime API，例如：

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

脚本的用途是编排 agent，而不是执行工具。

## WorkflowSpec / Manifest

WorkflowSpec 不应膨胀成完整声明式 DSL。它主要负责：

- workflow metadata。
- schema。
- permission / safety contract。
- 可审计 phase。
- budgets。
- final phase / final task contract。
- UI plan preview 所需的稳定结构。

## Planner 输出

推荐方向：

```text
Planner
  -> WorkflowScript
  -> WorkflowSpec / Manifest
  -> Compiler validation
  -> WorkflowRunner execution
```

近期可以先用内置 template / function 模拟 WorkflowScript，避免过早引入完整脚本 runtime。
