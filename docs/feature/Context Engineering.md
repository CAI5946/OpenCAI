# Context Engineering

## Feature 目标

Context Engineering 负责管理 OpenCAI 在不同执行点提供给模型的上下文。它不是传统 RAG 的同义词，也不是把所有历史、日志和文件内容直接塞进 prompt；它是 Runtime、Agent Loop、WorkflowRunner、Modes、Multi-agents 和 Memory 之间的输入合同。

核心目标：

- 让模型在每轮调用前看到必要、可信、可审计的上下文。
- 明确区分 session 初始化 context、session 内长期对话 context、workflow scoped context 和跨 session memory。
- 控制上下文体积，避免 tool output、完整 transcript 或陈旧事实污染后续推理。
- 保持 Agent Loop 简单：Agent Loop 消费组合后的 messages，不直接拥有项目规则加载、长期 memory 或 workflow state。

## 整体架构

当前设计分为五层：

1. Session 初始化 context

   一次 task 或 session 开始时采集 cwd、repo root、项目/全局规则、git 状态、runtime 配置和权限信息。

2. Session 内长期对话 context

   同一个交互式 RuntimeSession 内，跨多个 user turn 保存精简上下文。它只保留可继续推理的信息，例如最近任务摘要、final answer、工具调用名、验证结果和错误；不保留完整 tool payload 或完整 transcript。

3. Agent Loop 内 message 传递

   单个 task 执行中，Agent Loop 维护短期工作上下文：user task、assistant tool call、tool observation、verification、stop/error 和 final answer 如何进入或不进入下一轮 LLM call。这一层不负责读取 `AGENTS.md`，也不负责跨 task 保存 memory。

4. Workflow scoped context

   WorkflowRunner 未来为每个 phase 组合 scoped context。workflow state 不等于聊天上下文，phase 只应看到完成当前职责所需的信息。

5. 跨 session memory

   保存长期稳定的用户偏好、项目决策、常用命令和踩坑记录。memory 注入必须带来源、置信度和是否需要重新验证的边界。当前尚未实现。

当前普通 task 的 message 组合顺序：

```text
system prompt
project instructions
global instructions
environment context
session context
current user task
```

## 当前代码结构

- `OpenCAI/context.py`
  - `ContextSnapshot`：一次 context 采集结果。
  - `ContextProvider`：采集 cwd、repo root、git、runtime、global/project `AGENTS.md`。
  - `ContextComposer`：把 system prompt、项目规则、全局规则、环境信息、session context 和当前 task 组合成 LLM messages。

- `OpenCAI/session_context.py`
  - `SessionContext`：RuntimeSession 内的模型可见长期对话上下文。
  - `SessionTurnSummary`：单个 user turn 的精简摘要。
  - `summarize_turn_events()`：从 transcript events 提取 user task、final answer、tool calls、verification 和 error/stop 信息。

- `OpenCAI/agent_loop.py`
  - `iter_agent_loop()`：单个 task 内的 model -> tool -> observation 循环。
  - 内部 `messages` 是 in-turn 短期工作上下文，初始值来自 `ContextComposer`。
  - tool call 后追加 assistant tool-call message，tool 执行后追加 observation message，供下一轮模型调用使用。

- `OpenCAI/__main__.py`
  - `RuntimeSession.session_context` 保存当前交互式 session 的长期对话 context。
  - `run_once()` 接收可选 `session_context` 并传给 `ContextComposer`。
  - `run_interactive()` 每轮普通 task 完成后，将 events 摘要写回 `session.session_context`。

## 已完成工作

### Session 初始化 context

已完成：

- `ContextProvider` 采集 cwd、repo root、git branch、dirty status、short status。
- 采集 runtime 配置：adapter、permission profile、max steps。
- 记录 README 和 `docs/status.md` 是否存在。
- 读取 project/global `AGENTS.md` raw instructions。
- instruction 文件有字符上限，默认 `12000` chars，超出会截断并标记 warning。

已接入：

- 普通 task runtime 主路径默认使用 composed initial messages。
- Agent Loop 支持接收 `initial_messages`，兼容原始只传 task 的路径。

### Session 内长期对话 context

已完成第一刀：

- 新增 `SessionContext`。
- 每轮普通 task 完成后，从 events 生成 `SessionTurnSummary`。
- session context 保存最近 turn，默认 `recent_turns_max = 3`。
- 超过最近 turn 上限或总字符预算时，把旧 turn 合并进 `running_summary`。
- 默认 session context 字符预算为 `12000` chars，running summary 上限为 `4000` chars。
- session context 渲染为 `<session_context>` block，并插入当前 task 前。
- 不把完整 tool result payload、完整 transcript 或 `/process` 内容直接注入模型。

### Agent Loop 内 message 传递

已完成基础闭环：

- `iter_agent_loop()` 维护单个 task 内的 `messages`。
- `messages` 可从 `initial_messages` 启动，因此能消费 `ContextComposer` 生成的初始化 context。
- 模型选择工具后，Agent Loop 追加 assistant tool-call message。
- 工具执行后，Agent Loop 追加 tool observation message，供下一轮 LLM call 使用。
- `read_file` 等文本结果已有局部 preview 截断，避免单个 observation 过大。
- `run_command` 结果会格式化 command、exit code、stdout、stderr。

当前边界：

- Agent Loop 内 messages 是 task-local 短期工作上下文。
- 它不是 session 长期 context，也不是 persistent memory。
- task 完成后，只有 `SessionContext` 摘要会进入下一轮 task；完整 in-turn messages 不跨 task 复用。

### 测试

已覆盖：

- `ContextComposer` message 顺序。
- session context 注入位置。
- Runtime 第二轮 task 能携带前一轮 session context。
- `summarize_turn_events()` 只保留紧凑事实，不保留大段 tool payload。
- recent turn 超限时会 compact 到 `running_summary`。
- `iter_agent_loop()` 能使用传入的 `initial_messages`。

最近验证：

- `python -m unittest tests.test_session_context tests.test_context tests.test_runtime_session`
- `python -m py_compile OpenCAI\session_context.py OpenCAI\context.py OpenCAI\__main__.py tests\test_session_context.py tests\test_context.py tests\test_runtime_session.py`
- `python -m unittest discover tests`

## 待完成工作

### Context budget 和可观察性

当前只有基础字符预算，还缺完整 debug visibility。

需要补：

- 每个 context block 的 `name/source/chars/truncated` metadata。
- 本轮最终注入了哪些 block 的 debug summary。
- `/status` 或 `/process` 可查看 context 注入摘要。
- 明确单个 block 的硬上限，尤其是 README/status 摘要、tool result 摘要和 memory 候选。

### README / status 摘要

当前只记录 README 和 `docs/status.md` 是否存在，尚未读取或压缩其内容。

需要补：

- 读取 README 的项目入口摘要。
- 读取 `docs/status.md` 的 current-state 摘要。
- 给 README/status block 独立预算和截断标记。
- 易变事实仍以当前文件内容为准，不从旧 session summary 里直接当事实。

### Session context 质量提升

当前 `running_summary` 是本地拼接式压缩，不是 LLM summarization。

需要补：

- 更稳定的 summary schema，例如 current goal、files touched、decisions、verification、open risks。
- 区分 successful turn、failed turn、interrupted turn。
- 保留最近 N 轮 raw summary，同时避免重复保存无价值短 task。
- 支持手动清空或 compact session context。

### Agent Loop message flow 成熟化

当前 Agent Loop 内 message flow 仍是最小闭环。

需要补：

- 定义更强的 message schema，区分 assistant tool call、tool observation、verification observation、error/stop observation。
- 决定 verification result 是否以及如何进入下一轮 LLM call。
- 为不同工具提供独立 observation renderer，避免所有工具共享同一种文本拼接策略。
- 增加 in-turn message budget，防止单个 task 内 tool observation 持续膨胀。
- 增加每轮 LLM call 的 message debug summary，能看到本轮模型实际收到哪些 message block。
- 明确 stop/error 后哪些信息进入 transcript，哪些信息进入 messages。

### Workflow scoped context

当前普通 task 已接 context composer，workflow phase 级 context 尚未完成。

需要补：

- WorkflowRunner 为每个 phase 生成 scoped context。
- phase 只接收当前 phase 所需的 task、前置结果、权限和相关文件线索。
- workflow state、phase result 和 model-visible context 分离。
- review / verify / execute 等不同 phase 的 context 预算不同。

### 跨 session memory

当前未实现 persistent memory。

需要补：

- `search_memory` 工具协议。
- 返回 memory candidate、source、confidence、needs_verification。
- memory 注入前按当前文件或命令重新验证易变事实。
- memory 写入边界：哪些信息能自动保存，哪些必须用户确认。

### Modes 和 Multi-agents

Context Engineering 后续需要服务 Modes 和 Multi-agents。

需要补：

- Runtime-level `ModeProfile` 如何影响 prompt、context block、tool policy 和 workflow selection。
- Multi-agent worker 的 scoped context。
- subagent 输出 summary-only return，避免污染主 session context。
- 多 agent 并发写入前的 context 和 state 合并规则。

## 当前边界

- Context Engineering 不等于 RAG。
- 当前不引入 vector DB、embedding 或独立 retrieval layer。
- `task_history` 是 UI/input history，不是模型可见 context。
- `last_task_events` 是过程视图数据，不默认进入模型。
- `SessionContext` 是同一 RuntimeSession 内的长期对话 context，不是跨 session memory。
- Agent Loop 内 `messages` 是单 task 短期工作上下文，不跨 task 直接复用。
- Workflow state 不等于聊天上下文。

## 下一步建议

优先顺序：

1. 补 context block metadata 和 debug visibility。
2. 给 `/status` 或 `/process` 增加 context 注入摘要入口。
3. 增加 README/status 摘要 block。
4. 改进 session summary schema。
5. 成熟化 Agent Loop 内 message schema、observation renderer 和 in-turn budget。
6. 将 ContextComposer 接入 WorkflowRunner phase scoped context。
7. 设计并实现 `search_memory` 工具协议。
