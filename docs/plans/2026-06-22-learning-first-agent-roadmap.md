# Plan: Learning-First Coding Agent Roadmap

## 背景

早期计划偏向交付一个可运行原型：先做 mock TUI，再接 Gemini loop、工具、toy project 和验证闭环。

这个方向可以推进代码，但不适合当前学习目标。用户需要理解每个部分为什么存在、如何设计、边界在哪里，而不是只看到文件逐步增加。

因此当前开发模式调整为学习优先：先理解组件，再做最小实现；先解释设计，再写代码；每次只聚焦一个 Agent 组件。

## 决策

- 暂停以交付完整原型为主的推进方式。
- 保留已有代码，但以当前 Phase 路线作为唯一执行路线。
- 重新定义学习阶段，从 Agent 的结构和事件模型开始。
- 后续代码实现必须服务理解，不以补齐完整原型为第一目标。

## 新阶段

### Phase 0: Component Map

目标：理解一个最小 Coding Agent 由哪些核心部件组成，以及它们之间的依赖关系。

核心问题：

- Agent Runtime 是什么？
- Event / Transcript 是什么？
- Tool Model 是什么？
- LLM Adapter 是什么？
- Renderer / TUI 在系统里处于什么位置？

产出：

- 一份组件关系说明，必要时配一张结构图。
- 明确哪些组件是核心，哪些只是展示层或适配层。

不写代码。

### Phase 1: Event / Transcript Model

目标：理解 Agent 过程如何被事件化，并形成最小事件协议。

核心问题：

- 一次 Agent 工作流中有哪些关键事件？
- 每类 event 必须包含哪些字段？
- tool call、tool result、verification、final answer 如何表达？
- 失败事件应该如何记录？

产出：

- 最小 event type 列表。
- 每类 event 的字段设计。
- 一段 mock transcript。

可以写极少代码，但必须先完成设计解释。

### Phase 2: Renderer

目标：理解 event 如何变成人能读懂的输出。

核心问题：

- Renderer 为什么不应该拥有 Agent 决策逻辑？
- 事件类型如何映射到显示样式？
- 长输出、失败输出、补丁摘要如何展示？

产出：

- 最小 renderer 设计。
- 终端可读 transcript。

这时才讨论 TUI；TUI 只是 renderer 的承载方式。

### Phase 3: Tool Model

目标：理解工具在 Agent 系统中的职责、边界和返回结构。

核心问题：

- tool schema 和真实工具函数有什么区别？
- `read_file`、`search_files`、`apply_patch`、`run_command` 的输入输出是什么？
- 工具失败如何返回 observation？
- 哪些安全边界属于后续权限模型，而不是最小工具模型？

产出：

- 四个最小工具的接口设计。
- tool call / tool result 的样例。

先设计接口，不急于接真实模型。

### Phase 4: Agent Loop

目标：理解 Agent 为什么是循环，而不是一次模型调用。

核心问题：

- 为什么需要 model -> tool_call -> observation -> model？
- loop 的停止条件是什么？
- max steps、验证成功、模型给出 final answer 分别如何处理？
- 验证失败为什么应该进入下一轮 observation？

产出：

- 一个不接真实 LLM 的 fake loop。
- 能观察到至少一次 tool call 和 observation。

### Phase 5: LLM Adapter

目标：理解 Gemini 只是模型适配器，不是 Agent Core。

核心问题：

- Agent Core 应该知道多少 Gemini 细节？
- function calling schema 如何从 Tool Model 转换而来？
- 模型返回 tool call 和 final answer 时分别如何处理？
- 缺少 API key、请求失败、模型返回格式异常时如何表达？

产出：

- 最小 Gemini adapter。
- 失败路径可观察。

### Phase 6: Toy Project Closed Loop

目标：跑通一次完整、可验证的 Coding Agent 修复闭环。

核心问题：

- Agent 如何读取失败测试？
- 如何定位最小修改点？
- 如何应用 patch？
- 如何运行验证命令？
- 验证失败如何继续迭代？

产出：

- toy project。
- 一次完整 transcript。
- 验证命令 exit code 为 `0`。

## 每个阶段的学习流程

每个组件按同一节奏推进：

1. 说明这个组件解决什么问题。
2. 定义输入、输出、状态和失败情况。
3. 说明它和其他组件的边界。
4. 给出最小结构或数据样例。
5. 用户确认理解后，再做极小实现。
6. 用读取、diff、命令或可观察输出验证。
7. 总结这个设计为什么成立，以及下一阶段依赖它的哪一部分。

## 当前状态

- Phase 0：已完成 Component Map 学习。
- Phase 1：已完成 Event / Transcript Model 学习和最小 `OpenCAI/events.py` 实现。
- Phase 2：已完成 Renderer 学习和最小实现。
- Phase 3：已完成 Tool Model 学习和最小实现。
- Phase 4：已完成 Agent Loop 学习和最小 fake loop。
- Phase 5：已完成 LLM Adapter 基础边界学习和最小实现。
- 当前下一步：确认是否进入真实 `GeminiAdapter`。

## 非目标

- 不急于接入 Gemini。
- 不急于实现真实工具。
- 不急于扩展 TUI。
- 不新增 MCP、插件、多 Agent、长期 memory。
- 不复制 `claude-code/` 的闭源实现。

## 验收标准

这条新路线的阶段完成标准不是“代码写完”，而是：

- 用户能说明当前组件的作用。
- 用户能说明当前组件的输入、输出和边界。
- 用户能说明为什么先做这个组件。
- 若有代码，代码必须最小、可观察、可运行或可检查。
