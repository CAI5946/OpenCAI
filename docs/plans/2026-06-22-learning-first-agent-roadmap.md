# Plan: Learning-First Coding Agent Roadmap

## 背景

早期计划偏向交付一个可运行原型：先做 mock TUI，再接 Gemini loop、工具、toy project 和验证闭环。

这个方向可以推进代码，但不适合当前学习目标。用户需要理解每个部分为什么存在、如何设计、边界在哪里，而不是只看到文件逐步增加。

因此当前开发模式调整为学习优先：先理解组件，再做最小实现；先解释设计，再写代码；每次只聚焦一个 Agent 组件。

Phase 6 完成后，路线继续扩展为“交互式 CLI + Claude Code 学习对照”：OpenCAI 实现自己的最小 Coding Agent，Claude Code 只作为架构和行为参考，不作为代码来源。

## 决策

- 暂停以交付完整原型为主的推进方式。
- 保留已有代码，但以当前 Phase 路线作为唯一执行路线。
- 重新定义学习阶段，从 Agent 的结构和事件模型开始。
- 后续代码实现必须服务理解，不以补齐完整原型为第一目标。
- Phase 7 起采用双轨推进：每个阶段先做 Claude Code reference pass，再实现 OpenCAI 的最小本地版本。
- Phase 7 先把启动方式调整为交互式 Runtime / TUI Shell：`python -m OpenCAI` 启动后进入输入循环，用户输入 task，再由 Runtime 调用 Agent Loop；Renderer 仍只负责把 events 渲染成 transcript。
- `claude-code/` 是 source snapshot / security research 资料，只学习职责、边界、数据流和可观察行为，不复制代码或实现结构。

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

### Phase 7: Interactive Runtime / TUI Shell

目标：理解 `python -m OpenCAI` 启动后的交互式运行路径，把一次性 `--task` CLI 改为最小输入循环。

Reference pass：

- 参考 Claude Code 的交互入口、输入到 Runtime 的交接方式和 transcript 展示边界。
- 只抽象 TUI Shell、Runtime、Agent Loop、Renderer 的职责边界，不复刻复杂 UI。

产出：

- `python -m OpenCAI` 启动交互式输入循环。
- TUI Shell 负责接收用户输入，并把 task 交给 Runtime。
- Runtime 负责创建 adapter、调用 Agent Loop，并把 events 交给 Renderer。
- Renderer 继续只消费 events，不处理用户输入。
- 保留一次性 `--task` / `--dry-run` 作为可选路径或调试路径，具体保留方式在实现前确认。

验收：

- 启动后用户能输入一个 task。
- 输入 task 后能跑当前 fake Agent Loop，并渲染 transcript。
- 一轮结束后能回到输入提示或按明确命令退出。
- 不引入真实 Gemini 请求。

### Phase 8: Claude Code 主循环对照 + Real GeminiAdapter

目标：理解真实模型调用在 Agent Loop 中的位置，并接入真实 `GeminiAdapter`。

Reference pass：

- 参考 `claude-code/src/QueryEngine.ts` 和 `claude-code/src/query.ts`。
- 只抽象 loop 状态、tool result 回灌、停止条件和错误路径。

产出：

- 真实 `GeminiAdapter`。
- Gemini function calling schema 由 OpenCAI `ToolSpec` 转换而来。
- Agent Core 不依赖 Gemini response 结构。
- 交互式 Runtime 可显式选择 fake 或 Gemini adapter。

验收：

- 真实 Gemini 能完成 `read_file -> final_answer` 或 `run_command -> observation -> final_answer`。

### Phase 9: Claude Code 工具模型对照 + Tool Completion

目标：补齐 OpenCAI 最小工具能力。

Reference pass：

- 参考 `claude-code/src/Tool.ts`、`claude-code/src/tools.ts`。
- 参考 `FileReadTool`、`FileEditTool`、`BashTool`、`GrepTool`、`GlobTool` 的职责边界。
- 只抽象 schema、permission、execution、result 四层，不复制实现。

产出：

- 真实 `search_files`。
- 保留最小 `apply_patch(path, old, new)`，不做完整 diff parser。

验收：

- fake 或真实 loop 能搜索、读文件、补丁修改、运行命令。

### Phase 10: Claude Code 验证闭环对照 + Real Toy Repair

目标：让真实 Gemini 驱动 toy project 修复闭环。

Reference pass：

- 对照 Claude Code 如何把命令输出、失败结果和工具结果继续喂回模型。

产出：

- 真实 Gemini repair loop。
- transcript 包含完整 action / observation / verification。

验收：

- 事件流包含 `verification failed -> read/search -> apply_patch -> verification passed -> final_answer`。
- `python -m unittest discover examples/toy_project` exit code 为 `0`。

### Phase 11: Claude Code 权限对照 + Minimal Safety Layer

目标：实现最小安全边界，把“模型想做”和“系统允许执行”分开。

Reference pass：

- 参考 Claude Code tool permission 思想。
- 只抽象权限门槛，不实现复杂 permission mode。

产出：

- `--allow-write`。
- `--allow-command`。
- cwd/path 边界检查。
- 明显危险命令拦截。

验收：

- 未授权写文件或跑命令时，工具调用被拒绝并记录为可观察事件。

### Phase 12: Claude Code CLI 行为对照 + Productized CLI

目标：整理 OpenCAI 为可日常试用的最小 CLI。

Reference pass：

- 对照 Claude Code 的 CLI 可用性和 transcript 行为。
- 不复刻 Ink/React UI，不做复杂 TUI。

产出：

- `--adapter fake|gemini`。
- `--max-steps`。
- `--verify`。
- `--require-verification`。
- README、status 和最小使用说明。

验收：

- 新终端按 README 能跑通 fake demo。
- 配置 `GEMINI_API_KEY` 后能跑通 Gemini smoke demo。

## 每个阶段的学习流程

每个组件按同一节奏推进：

1. 说明这个组件解决什么问题。
2. 做 Claude Code reference pass，并记录 `学到什么 -> OpenCAI 采用什么 -> 暂不采用什么`。
3. 定义输入、输出、状态和失败情况。
4. 说明它和其他组件的边界。
5. 给出最小结构或数据样例。
6. 用户确认理解后，再做极小实现。
7. 用读取、diff、命令或可观察输出验证。
8. 总结这个设计为什么成立，以及下一阶段依赖它的哪一部分。

## 当前状态

- Phase 0：已完成 Component Map 学习。
- Phase 1：已完成 Event / Transcript Model 学习和最小 `OpenCAI/events.py` 实现。
- Phase 2：已完成 Renderer 学习和最小实现。
- Phase 3：已完成 Tool Model 学习和最小实现。
- Phase 4：已完成 Agent Loop 学习和最小 fake loop。
- Phase 5：已完成 LLM Adapter 基础边界学习和最小实现。
- Phase 6：已完成 Toy Project Closed Loop。
- 当前下一步：Phase 7，先做交互式 Runtime / TUI Shell reference pass，再把 `python -m OpenCAI` 调整为最小输入循环。

## 非目标

- 不在没有 reference pass 的情况下接入 Gemini。
- 不一次性补齐全部真实工具。
- 不让 Renderer 承担用户输入；交互输入属于 TUI Shell / Runtime 边界。
- 不新增 MCP、插件、多 Agent、长期 memory。
- 不复制 `claude-code/` 的闭源实现。
- 不把 `claude-code/` 当作可复用开源代码库。

## 验收标准

这条新路线的阶段完成标准不是“代码写完”，而是：

- 用户能说明当前组件的作用。
- 用户能说明当前组件的输入、输出和边界。
- 用户能说明为什么先做这个组件。
- 若有代码，代码必须最小、可观察、可运行或可检查。
