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
   - `delete_file`
   - `move_file`
   - `copy_file`

2. Search tools

   - `list_files`
   - `glob_files`
   - `search_files` / `grep_files`
   - `search_symbols`
   - `inspect_tree`

3. Command tools

   - `run_command`
   - `start_command`
   - `read_command`
   - `write_stdin`
   - `stop_command`

4. Planning tools

   - `update_plan`
   - `create_task`
   - `update_task`
   - `list_tasks`
   - `complete_task`

5. Context tools

   - `context_status`
   - `read_context_block`
   - `summarize_context`
   - `search_memory`

6. Workflow tools

   - `workflow_plan`
   - `workflow_execute`
   - `workflow_status`
   - `workflow_pause`
   - `workflow_resume`
   - `workflow_cancel`
   - `workflow_replay`

7. Agent tools

   - `spawn_agent`
   - `send_agent_message`
   - `wait_agent`
   - `list_agents`
   - `stop_agent`
   - `merge_agent_result`

8. Skill tools

   - `list_skills`
   - `read_skill`
   - `invoke_skill`
   - `run_skill`
   - `validate_skill`

   Skill tools 是本地可复用能力包入口，详细设计、当前实现和后续路线维护在 [Skills](Skills.md)。Tools 文档只保留它作为工具分类和 Tool Model 边界的一部分。

9. External / MCP / Plugin tools

   - `tool_search`
   - `call_external_tool`
   - `list_mcp_resources`
   - `read_mcp_resource`
   - `call_mcp_tool`
   - MCP tools。
   - dynamic tools。
   - plugin tools。

10. Web / Research tools

   - `web_search`
   - `web_fetch`
   - `web_extract`

   Web / Research tools 采用 search -> fetch -> extract 分层：

   - `web_search` 只返回标题、URL、snippet 和来源列表，不把网页全文塞进上下文。
   - `web_fetch` 负责抓取模型明确选择的公开 `http/https` URL，并返回状态码、content type、最终 URL、截断状态和有界正文。
   - `web_extract` 负责从 HTML 或 URL 中提取 title、可读正文和链接，供 research / docs lookup 使用。

   设计原则：

   - Web 内容默认是不可信输入，不能覆盖 system / project instructions。
   - Web 工具只读，但属于外部网络访问能力，应保留独立工具分类，后续可按 mode / workflow phase 控制暴露。
   - 搜索和抓取必须拆开，避免 search observation 直接污染 context budget。
   - 第一版只允许公开 `http/https` URL，拒绝 `file://`、localhost、`.local` 和 private / loopback / link-local / reserved IP。
   - 第一版使用标准库和公开 HTML 搜索页，不引入 API key 或外部依赖；后续可以替换为 provider-native web search、专用 search API 或 MCP server。

11. IDE / Code Intelligence tools

   - `get_diagnostics`
   - `go_to_definition`
   - `find_references`
   - `rename_symbol`
   - `format_file`

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
  - 兼容门面，继续导出 `ToolSpec`、`ToolResult`、`TOOLS`、`run_tool()` 和既有工具函数。
  - 保持旧导入路径稳定，避免拆分工具实现时连带修改 Agent Loop、LLM Adapter、Safety 和测试。

- `OpenCAI/tooling/contracts.py`
  - `ToolCall`、`ToolSpec`、`ToolResult`、`ToolFunction`。
  - `tool_result()`：统一构造工具结果。

- `OpenCAI/tooling/registry.py`
  - 聚合各分类模块导出的工具 spec。
  - `TOOLS`：当前静态工具注册表。
  - `run_tool()`：按工具名分发执行。

- `OpenCAI/tooling/file_tools.py`
  - `read_file()`：读取 UTF-8 文本文件，支持 `max_chars` 预算。
  - `write_file()`：创建或覆盖完整 UTF-8 文件。
  - `delete_file()` / `copy_file()` / `move_file()`：结构化文件删除、复制和移动。

- `OpenCAI/tooling/search_tools.py`
  - `list_files()`：结构化列目录。
  - `glob_files()`：按 glob 查找文件路径。
  - `search_files()`：优先封装 `rg`，支持 include / exclude / case sensitivity / max_results / max_bytes；无 `rg` 时回退 Python 搜索。

- `OpenCAI/tooling/skill_tools.py`
  - `list_skills()` / `read_skill()` / `invoke_skill()`：Skill 工具第一版；详细设计见 [Skills](Skills.md)。

- `OpenCAI/tooling/web_tools.py`
  - `web_search()` / `web_fetch()` / `web_extract()`：Web / Research 工具第一版。

- `OpenCAI/tooling/edit_tools.py`
  - `edit_file()`：单文件局部替换。
  - `apply_patch()`：支持 `*** Begin Patch` add / update / delete multi-file grammar，并保留旧 `path/old/new` 兼容 schema。

- `OpenCAI/tooling/planning_tools.py`
  - `update_plan()`：维护多步骤 plan，最多一个 `in_progress`。
  - `create_task()` / `update_task()` / `list_tasks()` / `complete_task()`：当前 Python 进程内的轻量 task lifecycle。

- `OpenCAI/tooling/context_tools.py`
  - `context_status()` / `read_context_block()` / `summarize_context()`：只读检查当前 repo / AGENTS / README / status / skill 摘要。
  - `search_memory()`：deferred persistent memory 边界，当前未配置 memory backend 时明确失败。

- `OpenCAI/tooling/workflow_tools.py`
  - `workflow_plan()`：只读渲染当前内置 workflow plan。
  - `workflow_execute()` / `workflow_status()` / `workflow_pause()` / `workflow_resume()` / `workflow_cancel()` / `workflow_replay()`：deferred workflow control 边界，等待 RuntimeSession workflow controller 接入。

- `OpenCAI/tooling/agent_tools.py`
  - `spawn_agent()` / `send_agent_message()` / `wait_agent()` / `list_agents()` / `stop_agent()` / `merge_agent_result()`：deferred subagent runtime 边界。

- `OpenCAI/tooling/code_intelligence_tools.py`
  - `get_diagnostics()` / `go_to_definition()` / `find_references()` / `rename_symbol()` / `format_file()`：deferred IDE/LSP backend 边界。

- `OpenCAI/tooling/command_tools.py`
  - `run_command()`：运行 shell 命令并返回 exit code、stdout、stderr。

- `OpenCAI/tooling/external_tools.py`
  - `tool_search()` / `call_external_tool()` / `list_mcp_resources()` / `read_mcp_resource()`：deferred external/MCP 边界。当前注册为延迟暴露，并在未配置 runtime 时返回明确失败。

- `OpenCAI/tooling/path_utils.py` / `OpenCAI/tooling/common.py`
  - 分类工具共享的轻量 helper。

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
- `ToolRegistry` class：支持注册、查找和按 `direct` / `deferred` / `hidden` exposure、category、read_only 过滤。
- `OpenCAI.tools` 兼容门面。
- `OpenCAI.tooling` 分类模块：contracts / registry / file / search / web / skill / edit / planning / command / external。
- `OpenCAI.tooling` 也包含 context / workflow / agent / code_intelligence 边界模块，确保 Tools.md taxonomy 中的成熟工具面都有注册点。
- `ToolSpec` 包含 name、description、input_schema、read_only、function、category、exposure。
- `ToolResult` 包含 tool_name、ok、result、error。
- LLM Adapter 可把 `ToolSpec` 转成 provider tool schema。
- Agent Loop 可处理 unknown tool、tool execution、tool observation。

### 当前工具

已完成：

- `read_file`
  - 读取当前工作目录下的 UTF-8 文本文件。
  - 支持 `max_chars` 并返回 truncated / chars 元数据。

- `write_file`
  - 创建或覆盖 UTF-8 文本文件。
  - 支持 `overwrite` 和 `create_dirs`。
  - 返回 bytes_written、created、overwritten。

- `delete_file` / `copy_file` / `move_file`
  - 作为一等文件工具处理删除、复制和移动，不再要求模型通过 shell 拼命令。
  - 工具内部也做 workspace path containment，不能只依赖 Agent Loop 的 SafetyPolicy。

- `list_files`
  - 结构化列出目录直接子项，返回 name、path、is_dir、is_file、size。

- `glob_files`
  - 按 glob 查找路径，默认跳过 `.git`、`.venv`、`__pycache__`、`node_modules`、`venv`。

- `search_files`
  - 优先使用 `rg` 搜索文件内容。
  - 支持 include / exclude、case_sensitive、max_results、max_bytes。
  - 返回 path、line、column、text、truncated、skipped、backend。
  - 无 `rg` 时回退标准库 Python 搜索。

- `list_skills`
  - 列出 workspace-local skill root 下包含 `SKILL.md` 的 skill。
  - 当前默认 root 是 `skills`，也支持 cwd 内的显式 `root` 参数。
  - 返回 name、path、description。

- `read_skill`
  - 读取指定 workspace-local skill 的 `SKILL.md`。
  - 当前只允许单段 skill name，拒绝 `..` 或绝对路径逃逸。
  - 这是 skill discovery / inspection 的只读第一刀，不执行 skill 脚本。

- `invoke_skill`
  - 读取 project `.opencai/skills` 或 `~/AgentSkills` 中的 `SKILL.md`。
  - 返回摘要化 observation，并把完整 skill prompt 作为 `invoked_skill` meta user message 注入后续模型上下文。
  - 详细设计、边界和后续路线见 [Skills](Skills.md)。

- `web_search`
  - 搜索公开 Web，返回紧凑结果列表。
  - 返回 query、search URL、content 摘要、results 和 truncated。
  - 当前使用 DuckDuckGo HTML 搜索页解析，不需要 API key；这是可替换实现，不是长期 provider 绑定。

- `web_fetch`
  - 抓取公开 `http/https` URL。
  - 返回 final_url、status、content_type、content、bytes_read 和 truncated。
  - 默认限制读取字节数和模型可见字符数。
  - 拒绝 `file://`、localhost、`.local` 和 private / loopback / link-local / reserved IP。

- `web_extract`
  - 从传入 HTML 或公开 URL 提取 title、可读正文和最多 25 个链接。
  - 跳过 script / style / noscript / svg。
  - 输出同样受 `max_chars` 限制。

- `apply_patch`
  - 支持 `*** Begin Patch` / `*** End Patch` 多文件 patch。
  - 当前支持 `Add File`、`Update File` 和 `Delete File`。
  - 保留旧 `path/old/new` 兼容 schema。

- `edit_file`
  - 对单个 UTF-8 文件执行局部替换。
  - 支持默认替换一次或 `replace_all`。

- `update_plan`
  - 更新当前多步骤计划。
  - 状态为 `pending` / `in_progress` / `completed`，最多一个 `in_progress`。

- `create_task` / `update_task` / `list_tasks` / `complete_task`
  - 当前 Python 进程内 task lifecycle 第一版。
  - 目标是对应 Claude `TodoWrite` / task workflow 的结构化计划能力；持久化和 workflow save/replay 后续再接。

- `context_status` / `read_context_block` / `summarize_context`
  - 提供 repo / AGENTS / README / status / git / skills 摘要的只读工具入口。

- `workflow_plan`
  - 渲染当前内置 workflow plan，不执行 workflow。

- deferred boundary tools
  - Workflow control、Agent、MCP/external、IDE/LSP 和 persistent memory search 已注册为 deferred tools。
  - 当前 runtime 未配置时返回明确失败，不伪装成已接入真实 subagent / MCP / LSP。

- `run_command`
  - 运行同步 shell 命令。
  - 支持 `cwd`、`timeout` 和 `max_output_chars`。
  - 返回 command、cwd、exit_code、stdout、stderr、timeout 和截断元数据。
  - 默认超时为 30 秒，最大 600 秒。

- `start_command`
  - 启动长运行 shell 命令。
  - 返回 command_id、command、cwd、pid 和 running 状态。

- `read_command`
  - 读取后台 command session 的新增 stdout / stderr。
  - 返回 running、exit_code、stdout、stderr 和截断元数据。
  - 命令完成后自动清理 session。

- `write_stdin`
  - 向后台 command session 写入 stdin。
  - 返回 command_id 和 chars_written。

- `stop_command`
  - 停止后台 command session。
  - 优先 terminate，超时后 kill。

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

已完成第一版：

- `write_file`
- `edit_file`
- `delete_file`
- `move_file`
- `copy_file`
- `apply_patch` add / update / delete multi-file grammar。

后续补：

- `apply_patch` 支持 rename / move hunk、复杂上下文匹配和冲突诊断。
- 大文件读写预算与二进制文件检测。

设计判断：

- `write_file` 和 `apply_patch` 都需要存在。
- `write_file` 负责完整文件写入。
- `apply_patch` 负责精确增删改。
- 不要让一个工具承担所有写入场景。

### Search tools

已完成第一版：

- `list_files`
- `glob_files`
- `search_files`
  - 优先 ripgrep-backed search，无 `rg` 时 Python fallback。
  - 支持 include / exclude、case sensitive、max_results、max_bytes。
  - 返回 path、line、column、text、truncated、skipped、backend。

设计判断：

- `search_files` 底层优先封装 `rg`。
- 不能长期让模型通过 `run_command rg ...` 自己拼参数。

### Command tools

已完成第一版：

- `run_command` 支持 timeout 参数。
- `run_command` / `read_command` 支持 output char budget 和截断元数据。
- `run_command` / `start_command` 支持 `cwd` 参数，并由 SafetyPolicy 和工具执行层双重限制在 workspace 内。
- `start_command` / `read_command` / `write_stdin` / `stop_command` 支持长运行 command session。

后续补：

- Windows shell safety rules 更细分，例如 PowerShell AST / cmdlet 级危险操作识别。
- command observation renderer 进一步压缩大输出，并把 stdout / stderr 摘要、tail 和原始大小分离。
- command session 持久化 / replay；当前 session 只在当前 Python 进程内有效。

设计判断：

- `run_command` 是必要能力，但不是 tools 体系的中心。
- command observation 要比当前 stdout/stderr 直出更紧凑。

### Planning tools

已完成第一版：

- `update_plan`
  - 用于多步骤任务的 TODO / checklist。
  - 状态包括 pending / in_progress / completed。
  - 计划事件应进入 transcript，但只把必要摘要进入模型上下文。

- task lifecycle tools
  - `create_task`
  - `update_task`
  - `list_tasks`
  - `complete_task`

后续补：

- 计划和 task 状态接入 RuntimeSession / save-replay，而不是只保存在当前 Python 进程内。
- 计划事件进入 transcript / observation renderer。

### Observation renderer

需要补：

- 每个工具独立 observation renderer。
- 大输出统一截断并标记原始长度。
- 失败结果保留 error type / reason / retry hint。
- 验证命令输出生成紧凑 model-visible summary。
- tool result payload、transcript 展示和 model observation 分离。

### Web / Research tools

已完成第一版：

- `web_search`
- `web_fetch`
- `web_extract`

后续补：

- provider-native / API-backed search adapter，替代 HTML 搜索页解析。
- robots / rate limit / retry / cache 边界。
- 引文和来源可信度结构，例如 source title、publisher、published date、retrieved_at。
- PDF / Markdown / structured data extraction。
- prompt-injection 标记，把网页正文显式包进 untrusted content block。
- workflow-scoped exposure：research phase 可用，execute / write phase 默认不把 Web 结果当作项目事实。

### ToolRegistry 和 ToolExposure

已完成第一版：

- `ToolRegistry` class 抽象，`registry.py` 继续导出兼容 `TOOLS` dict。
- direct tools：默认直接暴露给模型。
- deferred tools：通过 `tool_search` 或 workflow 决定后再暴露。
- hidden / dispatch-only tools：可被 runtime 调用，但不直接给模型看。
- Agent Loop 当前只把 direct tools 传给模型，deferred tools 留给后续 runtime / workflow / MCP discovery 调度。

后续补：

- read-only / write / command / external / agent 分组接入实际 exposure policy。
- workflow-scoped tools：review phase 默认只读，execute phase 可写。
- subagent-scoped tools：只读 review subagent 不拿写工具。

### MCP / dynamic tools

后续补：

- Skill 后续路线已拆到 [Skills](Skills.md)。
- MCP tool spec 到 OpenCAI `ToolSpec` 的 adapter。
- MCP resource list / read。
- dynamic tool loading 的来源、权限、审计和禁用机制。
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
- `OpenCAI.tools` 是兼容门面；新增工具默认应放到 `OpenCAI/tooling/<category>_tools.py`，不要继续把实现塞回门面文件。
- `!command` 是用户直连 shell mode，不等于模型工具调用。
- `run_command` 是 escape hatch，不是文件、搜索、编辑工具的长期替代品。
- `apply_patch` 已支持 add / update / delete multi-file grammar，但还不是完整 Codex freeform patch parser，不支持 rename/move hunk、复杂上下文定位或冲突恢复。
- `search_files` 已优先封装 `rg`，无 `rg` 时回退 Python UTF-8 搜索；搜索仍只面向本地文本，不处理二进制索引或 LSP symbol。
- `web_search` 当前是标准库 HTML 解析实现，不是稳定搜索 API；搜索结果应作为发现入口，不作为最终事实。
- `web_fetch` / `web_extract` 当前只处理文本 / HTML 的第一版，不处理 JS 渲染、PDF、认证页面或复杂反爬页面。
- Skill 已有独立 feature 文档：[Skills](Skills.md)。
- `invoke_skill` 已完成只读加载和 `invoked_skill` meta user message 注入第一版；SkillRegistry、frontmatter、context budget、permission、模板/脚本/资产和 compaction/replay 仍在 Skills 后续路线中。
- 当前不默认启用 MCP、插件系统或外部工具 marketplace；`external_tools.py` 只注册 deferred 边界，未配置 runtime 时返回明确失败。

## 下一步建议

优先顺序：

1. 抽出 tool-specific `ObservationRenderer`，把 model-visible observation、transcript payload 和 raw result 分离。
2. 将 `ToolRegistry.visible_tools()` 接入 Agent Loop，按 mode / workflow phase / subagent role 暴露不同工具集。
3. 将 `update_plan` 和 task lifecycle 状态接入 RuntimeSession / transcript / save-replay。
4. 增强 `apply_patch`：rename / move hunk、复杂上下文匹配、冲突诊断。
5. 增强 command safety：PowerShell AST / cmdlet 级危险操作识别，减少字符串 blocklist 的误判和漏判。
6. 进入 MCP / dynamic tools runtime adapter；Skill 后续路线见 [Skills](Skills.md)。
