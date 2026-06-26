# Phase 8: Real GeminiAdapter

## 组件边界

Phase 8 的目标是把真实 Gemini 调用接入 OpenCAI，但不让 Agent Loop 依赖 Gemini SDK 对象或 response 结构。

`GeminiAdapter` 负责：

- 构造 `google-genai` client。
- 将 OpenCAI `ToolSpec` 转成 Gemini function declarations。
- 将 OpenCAI 内部 `Message` 转成 Gemini `Content`。
- 将 Gemini `function_calls` 或 text response 转成 OpenCAI `ModelOutput`。
- 将 provider 请求失败包装为 `LLMAdapterError`。

`GeminiAdapter` 不负责：

- 执行工具。
- 决定工具是否允许执行。
- 判断验证是否通过。
- 保存 Runtime session history。
- 渲染 transcript。

## 最小接口

OpenCAI 内部仍以 provider-neutral 协议连接 Agent Loop 和 LLM Adapter：

```text
LLMAdapter.call(messages, TOOLS) -> ModelOutput
```

`ModelOutput` 只有两类：

```text
tool_call(tool_name, arguments)
final_answer(answer)
```

为了支持 Gemini function calling，内部 `Message` 现在可以携带结构化工具语义：

```text
assistant tool-call message:
  role="assistant"
  tool_name
  arguments

tool result message:
  role="tool"
  tool_name
  tool_result
  tool_error
```

这不是 Gemini 专用结构；它表达的是 OpenCAI 自己的工具调用和工具结果语义。Gemini 专用转换只发生在 `GeminiAdapter` 内部。

## Function Calling 映射

OpenCAI 到 Gemini 的映射：

```text
ToolSpec
  -> types.FunctionDeclaration(parameters_json_schema=...)
  -> types.Tool(function_declarations=[...])

assistant tool-call Message
  -> types.Part.from_function_call(name=..., args=...)

tool result Message
  -> types.Part.from_function_response(name=..., response={"result": ...})

tool error Message
  -> types.Part.from_function_response(name=..., response={"error": ...})
```

Agent Loop 看到的仍然只是：

```text
model_output -> run_tool -> observation -> next model call
```

## 已验证

- `python -m OpenCAI --adapter gemini --task "Reply with exactly: Gemini adapter smoke ok. Do not call tools."`
  - exit code `0`
  - 验证真实 Gemini text response 可解析为 `final_answer`。

- `python -m OpenCAI --adapter gemini --task "Use the read_file tool to read README.md, then summarize the project in exactly one short sentence."`
  - exit code `0`
  - 验证真实 Gemini 可完成 `read_file -> function_response -> final_answer`。

- 用户回报真实 Gemini patch smoke passed：
  - Gemini 运行 toy project unittest。
  - 读取 `examples/toy_project/calculator.py`。
  - 使用 `apply_patch` 做最小修复。
  - 再次运行 unittest 并通过。
  - 当前 Codex 回合未直接捕获该终端输出。

## 关键取舍

- 默认 adapter 仍是 `fake`，真实 Gemini 必须显式使用 `--adapter gemini`。
- `RuntimeSession.task_history` 仍只保留在 Runtime 内部，不传给 Gemini。
- Agent Loop 仍不保存 Gemini SDK 对象，只保存 OpenCAI 内部消息语义。
- 暂不支持多 tool call 并发。
- 暂不加入权限层。
- 暂不把 `apply_patch` 升级为完整 diff parser。

## 下一步

Phase 9 补齐 OpenCAI 最小工具能力，优先实现真实 `search_files`。

Phase 10 再把真实 Gemini repair loop 做成更稳定的项目内 demo。
