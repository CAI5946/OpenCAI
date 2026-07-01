# Tools

## Feature 目标

Tools 负责管理 OpenCAI 允许模型执行的真实动作。这个 feature 不从零发明工具体系，而是 reference-first：以 Claude Code 和 Codex 本地参考代码中的成熟工具设计为主要参考，再裁剪成 OpenCAI 当前阶段可以落地的版本。

目标不是单纯增加工具数量，而是把 OpenCAI 的动作层设计成接近成熟 Coding Agent 的工具系统：

- 模型通过稳定、结构化、可审计、可控权限的工具完成开发任务。
- 文件、搜索、编辑、命令、计划、workflow、MCP 和 subagent 能力都有清晰分类和扩展边界。
- `run_command` 保留为必要的通用 escape hatch，但不长期替代高频一等工具。
- Agent Loop 继续只负责 model -> tool call -> observation -> model，不承载具体工具实现、权限策略或工具暴露策略。
- WorkflowRunner、Modes 和 Multi-agents 可以按 phase / mode / agent role 收窄工具集。

## 参考设计映射

### Claude 参考点

Claude 的价值主要在工具分类和用户工作流覆盖面。

可借鉴的目标工具类别：

- Shell：`BashTool` / PowerShell 类工具。
- File：`FileReadTool`、`FileWriteTool`、`FileEditTool`。
- Search：`GlobTool`、`GrepTool`。
- Web：`WebFetchTool`、`WebSearchTool`。
- Notebook：`NotebookEditTool`。
- Planning / Task：`TodoWriteTool`、Task create / get / update / list / stop。
- Agent / Team：subagent、message、team management。
- Skill / MCP：skill execution、MCP tool invocation、MCP resources。
- IDE / LSP：language server integration。
- Modes：plan mode、worktree mode、proactive/scheduled tools。

OpenCAI 不需要一次性实现全部类别，但目标 taxonomy 应对齐这些成熟边界。

### Codex 参考点

Codex 的价值主要在工具架构机制。

可借鉴的架构机制：

- `ToolRegistry`：统一注册、查找、分发工具。
- handler/runtime 分离：tool spec 和执行逻辑分层。
- `apply_patch` freeform grammar：把复杂编辑作为专用结构化工具，而不是 shell 拼接。
- direct / deferred tool exposure：常用工具直接暴露，大量外部工具延迟发现。
- `tool_search`：按需发现 MCP、插件、动态工具。
- MCP / dynamic / extension tools：外部工具不是硬编码进核心工具列表。
- permission request：工具可以按需请求额外权限。
- observation / event 分层：工具输出给模型和展示给用户不是同一份原始数据。
- multi-agent tools：spawn、message、wait、list 等协作工具有单独边界。

OpenCAI 的 Tools 架构应优先复用这些机制的思想，而不是重新设计一套不同概念。

## OpenCAI 目标工具分类

成熟目标工具集按类别组织：

1. File tools

   - `read_file`
   - `write_file`
   - `edit_file`
   - `apply_patch`

2. Search tools

   - `list_files`
   - `glob_files`
   - `search_files` / `grep_files`

3. Command tools

   - `run_command`
   - 后续 long-running command session / stdin follow-up。

4. Planning tools

   - `update_plan`
   - 后续 task list / todo 状态工具。

5. Context tools

   - context debug / remaining budget / session summary visibility。
   - 后续 memory search。

6. Workflow tools

   - workflow execute / cancel / status / replay。
   - phase-scoped tool allowlist。

7. External tools

   - MCP tools。
   - dynamic tools。
   - plugin / skill tools。

8. Agent tools

   - spawn subagent。
   - send message。
   - wait / list / stop agent。

第一阶段不实现所有类别，但文档和代码边界应面向这个成熟目标。

## 整体架构

当前设计采用八层：

1. Tool Taxonomy

   定义工具类别和命名规则，避免后续把所有动作都塞进 `run_command` 或单个巨大工具。

2. ToolSpec

   模型可见合同：工具名、描述、输入 schema、输出 schema、是否只读、是否可并行、是否支持延迟暴露。

3. ToolRuntime / Handler

   工具执行层：负责解析参数、执行动作、处理异常并返回结构化 `ToolResult`。ToolRuntime 不直接决定模型下一步。

4. ToolResult

   工具结果合同：成功/失败、结构化 payload、错误类型、诊断信息、截断信息、可选 retry hint。

5. Safety / Permission Gate

   执行前检查路径、权限 profile、危险命令、只读边界和 workflow phase policy。deny 应作为失败 tool result 回到 Agent Loop。

6. Observation Renderer

   把 `ToolResult` 转成下一轮模型可读 observation。不同工具应有不同 renderer，避免大输出污染 in-turn messages。

7. Transcript / Event Stream

   把 tool call、tool result、verification、error 和 stop 记录成可观察事件。Transcript 面向用户和调试，不等于下一轮模型完整上下文。

8. ToolRegistry / Exposure

   注册工具，并按 mode、workflow phase、permission profile、subagent role、MCP/dynamic availability 决定直接暴露、延迟暴露或隐藏。

当前普通 task 的工具调用路径：

```text
model output
-> Agent Loop 解析 tool_call
-> ToolRegistry 查找工具
-> SafetyPolicy / phase policy 检查
-> ToolRuntime 执行
-> ToolResult
-> transcript event
-> ObservationRenderer
-> next model call
```

## 本阶段产出

本阶段产出不是只有 `ToolSpec`。

`ToolSpec` 只是模型可见 schema。如果只做 `ToolSpec`，会形成“schema 有了，但执行、安全、结果、观察、暴露策略都没设计”的半成品。

本阶段应确认以下 Tool Contract：

- `ToolSpec`
  - 模型看到的工具描述、参数、输出、只读属性、暴露属性。

- `ToolResult`
  - 工具执行结果的稳定结构。
  - 成功、失败、截断、诊断、retry hint 的表达。

- `ToolRuntime` / handler
  - 工具执行接口。
  - 参数解析、异常处理、结构化返回。

- `ToolRegistry`
  - 工具注册、查找、分发。
  - 后续支持 direct / deferred / hidden。

- `SafetyPolicy` integration
  - 工具执行前的权限检查合同。
  - policy deny 作为 tool result 回到模型。

- `ObservationRenderer`
  - tool result 到 model-visible observation 的转换合同。

- `ToolExposure`
  - 按 mode / workflow phase / subagent role / permission profile 控制工具可见性。

- Tool taxonomy
  - 先确认目标工具分类和第一批实现顺序。

## `run_command` 的定位

`run_command` 可以代替一部分低频工具，但不应代替核心高频工具。

适合由 `run_command` 承担：

- 测试、lint、build、脚本执行。
- `git status` / `git diff` / `git log` 等已有 CLI。
- 低频系统诊断。
- 临时探索项目依赖或工具链。
- 作为尚未实现专用工具时的 escape hatch。

不应长期由 `run_command` 代替：

- `read_file`
- `write_file`
- `edit_file` / `apply_patch`
- `list_files` / `glob_files`
- `search_files`
- `update_plan`
- MCP resource tools
- workflow control tools
- subagent control tools

原因：

- shell 参数不结构化，模型需要自己处理 quoting、路径和平台差异。
- Windows 下 PowerShell / cmd 混用风险高。
- SafetyPolicy 很难准确判断真实意图。
- 输出噪声大，容易污染 context。
- workflow phase 很难精确 allowlist，例如 review phase 可以读文件但不该写文件。
- transcript 和 benchmark 很难稳定归因。

因此 OpenCAI 的原则是：

```text
command tool = 执行外部程序、验证、构建、诊断的通用工具
file/search/edit tools = 一等工具，不靠 shell 长期兜底
```

## 当前代码结构

- `OpenCAI/tools.py`
  - `ToolSpec`：当前模型可见工具定义。
  - `ToolResult`：当前工具执行结果。
  - `TOOLS`：当前静态工具注册表。
  - `run_tool()`：按工具名分发执行。
  - `read_file()`：读取 UTF-8 文本文件。
  - `search_files()`：在路径下做最小文本搜索。
  - `apply_patch()`：用 `old/new` 做一次文本替换。
  - `run_command()`：运行 shell 命令并返回 exit code、stdout、stderr。

- `OpenCAI/safety.py`
  - `SafetyPolicy`：工具执行前置权限检查。
  - 当前覆盖 path containment、permission profile、危险命令和只读边界。

- `OpenCAI/agent_loop.py`
  - `iter_agent_loop()`：单个 task 内消费工具 spec，执行工具，写入 events 和 observation messages。
  - `_format_observation()`：当前集中式 observation renderer。
  - `_verification_event_from_result()`：从 `run_command` 结果生成验证事件。

- `OpenCAI/llm_adapter.py`
  - `to_provider_tool_schema()` / `to_provider_tool_schemas()`：把 OpenCAI `ToolSpec` 转成 provider tool schema。
  - `GeminiAdapter`：把 tool call / function response 映射到 provider-independent message contract。

- `OpenCAI/shell_mode.py`
  - `!command` 用户直连 shell mode。
  - 复用 `run_command` 的执行能力，但它不是模型发起的 tool call。

- `OpenCAI/workflow.py`
  - 当前 WorkflowRunner 不直接执行工具。
  - Workflow phase 仍通过 Agent Loop 使用 Tool Model。

## 已完成工作

### 基础工具闭环

已完成：

- 静态 `TOOLS` 注册表。
- `ToolSpec` 包含 name、description、input_schema、read_only、function。
- `ToolResult` 包含 tool_name、ok、result、error。
- LLM Adapter 可把 `ToolSpec` 转成 provider tool schema。
- Agent Loop 可处理 unknown tool、tool execution、tool observation。

### 当前四个工具

已完成：

- `read_file`
  - 读取当前工作目录下的 UTF-8 文本文件。

- `search_files`
  - 按字符串 pattern 搜索文件内容。
  - 跳过 `.git`、`.venv`、`__pycache__`、`node_modules`、`venv`。
  - 最多返回 50 条匹配并标记截断。

- `apply_patch`
  - 对已有 UTF-8 文件执行一次 `old -> new` 文本替换。

- `run_command`
  - 运行 shell 命令。
  - 返回 command、exit_code、stdout、stderr。
  - 当前超时为 30 秒。

### Safety 接入

已完成：

- Agent Loop 在 `run_tool(...)` 前调用 `SafetyPolicy.check_tool_call(...)`。
- 支持 `read-only` / `ask-approval` / `approve-safe` / `full-access` permission profile。
- deny path 作为失败 `ToolResult` 回到模型。
- unknown tool、policy deny、argument failure、execution failure 已分开处理。

### Transcript 和验证事件

已完成：

- tool call 进入 `tool_call` event。
- tool result 进入 `tool_result` event。
- `run_command` 可生成 verification event。
- `/process` 和 live process 能展示工具过程。

## 待完成工作

### File tools

优先补：

- `write_file`
  - 负责创建或覆盖完整文件。
  - 支持父目录策略。
  - 返回 path、bytes_written、created、overwritten。

- `edit_file`
  - 负责单文件局部替换。
  - 比当前 `apply_patch path/old/new` 有更清晰失败语义。

- `apply_patch`
  - 升级为 add / update / delete / multi-hunk patch grammar。
  - 对齐 Codex 的 freeform patch 思路。

设计判断：

- `write_file` 和 `apply_patch` 都需要存在。
- `write_file` 负责完整文件写入。
- `apply_patch` 负责精确增删改。
- 不要让一个工具承担所有写入场景。

### Search tools

优先补：

- `list_files`
  - 结构化列目录。

- `glob_files`
  - 按 glob 查文件路径。

- `search_files`
  - 升级为 ripgrep-backed search。
  - 支持 include / exclude、case sensitive、max_results、max_bytes。
  - 返回 path、line、column、preview、truncated、skipped。

设计判断：

- `search_files` 底层优先封装 `rg`。
- 不能长期让模型通过 `run_command rg ...` 自己拼参数。

### Command tools

优先补：

- timeout 参数。
- output token / char budget。
- cwd 参数和权限约束。
- long-running command session id。
- stdin follow-up / polling。
- Windows shell safety rules。

设计判断：

- `run_command` 是必要能力，但不是 tools 体系的中心。
- command observation 要比当前 stdout/stderr 直出更紧凑。

### Planning tools

优先补：

- `update_plan`
  - 用于多步骤任务的 TODO / checklist。
  - 状态包括 pending / in_progress / completed。
  - 计划事件应进入 transcript，但只把必要摘要进入模型上下文。

### Observation renderer

需要补：

- 每个工具独立 observation renderer。
- 大输出统一截断并标记原始长度。
- 失败结果保留 error type / reason / retry hint。
- 验证命令输出生成紧凑 model-visible summary。
- tool result payload、transcript 展示和 model observation 分离。

### ToolRegistry 和 ToolExposure

需要补：

- `ToolRegistry` 抽象，替代单一静态 `TOOLS` 的长期形态。
- direct tools：默认直接暴露给模型。
- deferred tools：通过 `tool_search` 或 workflow 决定后再暴露。
- hidden / dispatch-only tools：可被 runtime 调用，但不直接给模型看。
- read-only / write / command / external / agent 分组。
- workflow-scoped tools：review phase 默认只读，execute phase 可写。
- subagent-scoped tools：只读 review subagent 不拿写工具。

### MCP / dynamic / skill tools

后续补：

- MCP tool spec 到 OpenCAI `ToolSpec` 的 adapter。
- MCP resource list / read。
- dynamic tool loading 的来源、权限、审计和禁用机制。
- skill tool execution。
- `tool_search` 作为 deferred tool discovery 入口。

### Workflow 和 Multi-agents

后续补：

- WorkflowRunner 为不同 phase 配置 tool allowlist。
- execute phase 可写，review / inspect phase 默认只读。
- verify phase 优先使用 command tools，但不能隐式修改文件。
- multi-agent worker 继承或收窄主 agent 工具权限。
- 并发 subagent 写入必须依赖隔离 worktree、锁或 merge gate。

## 当前边界

- Tools 是 OpenCAI 唯一真实动作层。
- Agent Loop 不直接读写文件，不直接执行 shell，只通过 Tool Model。
- WorkflowRunner 不直接执行工具，只编排 phase。
- TUI / Renderer 不承载工具决策逻辑。
- `!command` 是用户直连 shell mode，不等于模型工具调用。
- `run_command` 是 escape hatch，不是文件、搜索、编辑工具的长期替代品。
- `apply_patch` 当前是学习用最小文本替换，不是完整 patch parser。
- `search_files` 当前不是 ripgrep wrapper。
- 当前不默认实现 MCP、插件系统或外部工具 marketplace，但架构必须为它们预留位置。

## 下一步建议

优先顺序：

1. 确认 Tool Contract：`ToolSpec`、`ToolResult`、`ToolRuntime`、`ToolRegistry`、`ObservationRenderer`、`ToolExposure`。
2. 新增 `write_file`，修复当前新建文件缺口。
3. 新增 `list_files` / `glob_files`，减少模型用 shell 探索目录。
4. 将 `search_files` 升级为 ripgrep-backed search。
5. 将 `apply_patch` 升级为 add / update / delete / multi-hunk patch grammar。
6. 抽出 tool-specific observation renderer。
7. 给 command tool 增加 timeout、output budget 和 long-running session 边界。
8. 引入 `ToolRegistry` 和按 mode / workflow phase 的 tool exposure。
9. 设计 `update_plan`。
10. 再进入 MCP、dynamic tools、skill tools 和 subagent tools。
