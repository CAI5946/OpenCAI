# Phase 9: Tool Completion

## 组件边界

Phase 9 的目标是补齐 OpenCAI 的最小文件搜索能力，让模型在不知道目标文件路径时，可以先搜索候选位置，再读取文件并继续决策。

`search_files` 负责：

- 在指定路径下搜索 UTF-8 文本内容。
- 返回匹配文件、行号和匹配行文本。
- 把搜索结果整理成 `content` 摘要，供 Agent Loop 转成 observation。
- 区分工具失败和成功空结果。

`search_files` 不负责：

- 判断哪个文件应该修改。
- 执行 patch。
- 做权限控制。
- 提供完整 ripgrep wrapper。
- 支持复杂 glob、include/exclude 或大小写选项。

## Reference Pass

本轮参考问题：

```text
文件搜索工具应该返回什么，才能让 Agent Loop 的下一轮模型决策有用？
```

参考结论：

- 成熟搜索工具如 ripgrep 的核心可用信号是 `path + line number + matched text`。
- `--files` 更适合文件枚举，不等于内容搜索。
- `--json` 适合复杂结构化集成，但 Phase 9 不需要直接包装完整 ripgrep。

OpenCAI 采用：

- 内部 Python 最小实现。
- 返回 `matches[{path,line,text}]`。
- 额外返回 `content`，复用现有 `_format_observation(...)` 路径。
- 搜不到内容时返回 `ok=True` 和 `matches=[]`。

OpenCAI 暂不采用：

- 新增 ripgrep 运行时依赖。
- 完整 grep/glob 参数系统。
- 搜索结果排序或自动选择修改文件。

## 最小接口

```text
search_files(arguments, cwd) -> ToolResult
```

输入：

```text
pattern: str, required
path: str, optional, default "."
```

成功结果：

```text
{
  "path": "...",
  "content": "path:line: text",
  "pattern": "...",
  "matches": [
    {"path": "...", "line": 1, "text": "..."}
  ],
  "truncated": false,
  "skipped": []
}
```

失败结果：

```text
ToolResult.ok = false
error = 参数缺失或搜索路径不存在
```

## Agent Loop 接入

`search_files` 不需要修改 Agent Loop 主流程。现有路径仍是：

```text
ModelOutput(tool_call)
-> run_tool("search_files", ...)
-> tool_result event
-> _format_observation(...)
-> tool observation message
-> next model call
```

关键点是 `search_files` 的 `result["content"]` 必须足够可读，否则现有 `_format_observation(...)` 会把空内容传给模型。

## 命名修正

当前 Agent Loop 已不再只是 fake loop。正式入口从 `run_fake_loop(...)` 调整为：

```text
run_agent_loop(...)
```

`run_fake_loop(...)` 保留为兼容 wrapper，避免旧调用立即断裂。

`max_steps` 截断消息更新为：

```text
Agent loop stopped: max_steps reached.
```

当前它仍通过 `final_answer` event 表达；语义上后续可以细化为 stop/error 类 event。

## 已验证

- `python -m py_compile OpenCAI\agent_loop.py OpenCAI\__main__.py OpenCAI\tools.py`
  - exit code `0`
  - 验证改动文件语法可编译。

- `python -m OpenCAI --task "Read README"`
  - exit code `0`
  - 验证 Runtime 切到 `run_agent_loop(...)` 后一次性 task 路径仍正常。

- 直接调用 `search_files({"pattern": "OpenCAI", "path": "README.md"})`
  - `ok=True`
  - 返回 5 条匹配。

- 直接调用 `search_files({"pattern": "OpenCAI", "path": "missing-dir"})`
  - `ok=False`
  - 返回路径错误。

- 临时内联 adapter 验证：

```text
search_files -> read_file -> final_answer
```

  - exit code `0`
  - 搜索结果可进入 Agent Loop observation，并驱动下一轮工具调用。

- 强制 `max_steps=1`
  - 最后 event 为 `final_answer`
  - message 为 `Agent loop stopped: max_steps reached.`

## 下一步

Phase 10：用真实 Gemini 跑通更稳定的 toy project repair loop，让事件流包含：

```text
verification failed -> read/search -> apply_patch -> verification passed -> final_answer
```
