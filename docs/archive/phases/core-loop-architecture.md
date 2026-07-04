# OpenCAI Core Loop Architecture

## 核心问题

OpenCAI 的核心循环是：

```text
user task -> runtime -> agent loop -> model output -> tool call -> observation -> model output -> final answer
```

这个循环的关键不是一次性生成答案，而是让模型在工具结果和验证结果反馈后继续迭代。

## 组件边界

### Runtime

Runtime 负责启动和编排一次任务：

- 读取 `.env`。
- 解析 CLI 参数。
- 创建 adapter。
- 决定 one-shot 或 interactive 路径。
- 调用 Agent Loop。
- 把 events 交给 Renderer。

Runtime 不负责模型决策，也不直接执行工具。

### Agent Loop

Agent Loop 负责单个 task 内的循环状态：

- 保存 messages。
- 调用 LLMAdapter。
- 接收 `tool_call` 或 `final_answer`。
- 调用 Tool Model 执行工具。
- 把 tool result 格式化为下一轮 observation。
- 维护 max steps 和验证类停止条件。

Agent Loop 不依赖具体模型 SDK，也不处理 terminal UI。

### LLM Adapter

LLM Adapter 负责把 OpenCAI 内部协议翻译成 provider 请求，再把 provider response 解析回 `ModelOutput`。

当前 adapter：

- `FakeLLMAdapter`
- `FakeRepairLLMAdapter`
- `GeminiAdapter`

Agent Loop 只接收统一的 `ModelOutput`，不保存 Gemini SDK 对象。

### Tool Model

Tool Model 负责定义工具 schema 和执行工具。

当前最小工具：

- `read_file`
- `search_files`，待补齐
- `apply_patch`
- `run_command`

工具返回 `ToolResult`，由 Agent Loop 转成 observation。

### Event / Transcript

Event 是 OpenCAI 的可观察过程记录，Renderer 只消费 events：

- task start
- model output
- tool call
- tool result
- verification
- error
- final answer

Renderer 不做决策，不读取用户输入，不调用工具。

## 最小验证闭环

OpenCAI 的最小 coding loop 应能完成：

1. 接收用户任务。
2. 搜索或读取相关文件。
3. 执行验证命令。
4. 根据失败结果定位修改点。
5. 应用最小 patch。
6. 再次运行验证。
7. 验证通过后输出 final answer。

## 后续演进

Dynamic Workflows 不进入 `agent_loop.py`。

Agent Loop 继续负责单个 agent 的 model/tool/observation 循环；WorkflowRunner 负责阶段顺序、阶段状态、结果汇总和失败重试。
