# Workflow Planner Output Options

## 问题

Workflow Planner 的输出应该采用什么结构：Manifest、Script、LangGraph，还是其他形式？

## 候选项

1. Manifest
   - 用声明式元数据记录 workflow 名称、phase、task、依赖、权限、预算和安全边界。

2. WorkflowScript
   - 用脚本式 DSL 表达 phase、task、retry、if/else、humancheck 和 handoff，层级结构更清楚。

3. LangGraph
   - Planner 直接或间接生成可执行 graph，由节点、边、条件路由和循环组成。

4. Template + Parameters
   - Planner 选择已有 workflow 模板，并只填充任务参数、目标、约束和验证要求。

5. State Machine / Statechart
   - 用状态、转移、choice、fail、final 表达控制流，适合分支、循环和重试。

6. Behavior Tree
   - 用 Sequence、Selector、Retry、Condition、Action 表达执行和失败回退逻辑。

7. HTN / Task Decomposition Tree
   - 用层级任务网络把高层目标递归拆成子任务，适合表达任务分解关系。

8. Typed AST / IR
   - Planner 输出结构化抽象语法树或中间表示，由 Runner 或 Compiler 校验后执行。
