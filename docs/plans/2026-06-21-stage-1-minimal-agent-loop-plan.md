# Plan: Stage 1 Minimal Agent Loop

## Status

Paused. This plan is retained as a historical implementation plan. The current execution route is `docs/plans/2026-06-22-learning-first-agent-roadmap.md`, which switches the project to learning-first phases before continuing implementation.

## Scope

进入 Stage 1，但只实现最小可验证闭环：Gemini 触发工具调用，工具返回 observation，Agent 应用一次补丁，运行验证命令，并把完整过程记录到 transcript。先不做 Stage 2 的权限框架、复杂 TUI、MCP、插件、多 Agent 或长期 memory。

## Requirement Anchor

- goal：跑通一次 Claude Code 式最小模型-工具-观察-补丁-验证闭环。
- must_have：
  - R1: 使用 Python 实现 Agent Core，并只接 Gemini。
  - R2: 支持 `read_file`、`search_files`、`apply_patch`、`run_command` 四个工具。
  - R3: 使用 toy project 触发失败测试，并由 Agent 定位、补丁、验证。
  - R4: transcript 记录完整循环，并能通过现有 TUI 渲染真实事件。
- must_not：
  - N1: 不做 Stage 2 权限框架。
  - N2: 不引入 MCP、插件、多 Agent、长期 memory 或复杂 TUI。
  - N3: 不复制 `claude-code/` 的闭源实现。
- acceptance_criteria：
  - A1: 至少发生一次 Gemini 工具调用。
  - A2: 至少发生一次文件补丁。
  - A3: 验证命令被执行且 exit code 为 `0`。
  - A4: transcript 中能看到 user task、assistant 状态、tool call、tool result、patch summary、verification、final answer。
- output：Stage 1 可运行原型和验证记录。

## Document Budget

plan-only。本文档作为执行边界；稳定阶段结论同步到 `docs/status.md`。

## Execution Mode

planned-sequential。文件之间有顺序依赖，不做并行。

## Worktree Policy

not-needed。当前是学习项目，改动集中在小型原型文件和 toy project。

## Capability Skills

[]

## Reference-First Notes

- Google 官方 Gemini quickstart 当前建议 Python 使用 `google-genai` 包，并要求 API key。
- Google 官方 function calling 文档说明 Gemini API 支持通过 function declarations 控制工具调用；Stage 1 应使用自定义 function calling，而不是内置 code execution。
- Interactions API 仍处于 beta/preview；Stage 1 不使用它，避免把预览接口作为学习项目核心依赖。

Sources:

- https://ai.google.dev/gemini-api/docs/quickstart
- https://ai.google.dev/gemini-api/docs/function-calling
- https://ai.google.dev/gemini-api/docs/interactions/interactions-overview

## Document Transfer

- transfer_docs:
  - `docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`
  - `docs/claude-code-dev-workflow-plan.md`
  - `docs/status.md`
- stable_docs_to_update:
  - `docs/status.md`
- cleanup_candidates:
  - none
- cleanup_rule: ask before archive/delete

## Assumptions

- 用户会在执行前提供或确认 Gemini API key 的环境变量名称，推荐 `GEMINI_API_KEY`。
- 第一版允许新增极少依赖：`google-genai` 用于 Gemini，`rich` 继续用于 transcript 渲染。
- 第一版只支持单轮任务输入加有限步循环，不做交互式多轮聊天。

## Tasks

### Task 1: 固定 Stage 1 运行入口和依赖

- 任务目标：让 Stage 1 有明确入口、依赖和环境变量约定。
- requirement_refs：[R1]
- 修改文件路径：
  - `OpenCAI/opencai.cmd`
  - `docs/status.md`
- 新建文件路径：
  - `OpenCAI/__main__.py`
  - `OpenCAI/requirements.txt`
- 输入：
  - Stage 0 入口 `OpenCAI/tui.py`
  - Gemini 官方 quickstart
- 输出：
  - `python -m OpenCAI` 或 `OpenCAI\opencai.cmd` 可启动 Stage 1
  - 依赖文件只包含 Stage 1 需要的最小依赖
- 依赖任务：无
- 是否可并行：N
- 类型：HITL
- capability_skills：[]
- 验收标准：
  - 缺少 `GEMINI_API_KEY` 时给出明确错误，不发送请求。
  - 不新增全局配置或复杂 CLI 参数。
- 验证命令：
  - `python -m OpenCAI --help`
  - `OpenCAI\opencai.cmd --help`
- 预期输出：
  - 命令 exit code 为 `0`
  - 输出包含 task、cwd、verify command 或等价最小参数说明

### Task 2: 实现 Gemini 最小工具调用循环

- 任务目标：让 Gemini 可以请求四个本地工具，并接收结构化 observation。
- requirement_refs：[R1, R2]
- 修改文件路径：
  - `OpenCAI/tui.py`
- 新建文件路径：
  - `OpenCAI/agent_core.py`
  - `OpenCAI/gemini_client.py`
  - `OpenCAI/tools.py`
  - `OpenCAI/events.py`
- 输入：
  - 用户 task
  - cwd
  - tool schemas
- 输出：
  - 最大步数受控的 agent loop
  - 工具结果统一为结构化 event
- 依赖任务：Task 1
- 是否可并行：N
- 类型：AFK
- capability_skills：[]
- 验收标准：
  - Gemini 至少能调用 `read_file` 或 `search_files`。
  - 每次 tool call 和 tool result 都进入 event stream。
  - 达到 max steps 时停止并输出失败状态。
- 验证命令：
  - `python -m OpenCAI --dry-run "Fix the failing toy project test"`
- 预期输出：
  - 命令 exit code 为 `0`
  - transcript 中出现至少一个 `tool_call` event

### Task 3: 增加 toy project 和失败测试

- 任务目标：提供一个足够小、可重复失败的修复对象。
- requirement_refs：[R3]
- 修改文件路径：无
- 新建文件路径：
  - `examples/toy_project/calculator.py`
  - `examples/toy_project/test_calculator.py`
- 输入：
  - Stage 1 验收目标
- 输出：
  - 一个初始失败、修复后通过的 unittest toy project
- 依赖任务：Task 1
- 是否可并行：N
- 类型：AFK
- capability_skills：[]
- 验收标准：
  - 初始验证命令失败。
  - 问题足够简单，模型可通过读取文件定位。
- 验证命令：
  - `python -m unittest discover examples/toy_project`
- 预期输出：
  - 初始状态 exit code 非 `0`
  - Agent 修复后 exit code 为 `0`

### Task 4: 接入补丁和验证执行

- 任务目标：让 Agent 能应用一次补丁并运行验证命令。
- requirement_refs：[R2, R3]
- 修改文件路径：
  - `OpenCAI/tools.py`
  - `OpenCAI/agent_core.py`
- 新建文件路径：无
- 输入：
  - Gemini tool call
  - toy project 文件
  - 验证命令
- 输出：
  - 应用补丁后的 toy project
  - 验证命令执行结果 event
- 依赖任务：Task 2, Task 3
- 是否可并行：N
- 类型：AFK
- capability_skills：[]
- 验收标准：
  - 至少一次 `apply_patch` 修改 toy project 文件。
  - `run_command` 执行 unittest 命令。
  - 验证结果包含 exit code、stdout、stderr 摘要。
- 验证命令：
  - `python -m OpenCAI --task "Fix the failing toy project test" --cwd examples/toy_project --verify "python -m unittest discover ."`
- 预期输出：
  - 命令 exit code 为 `0`
  - transcript 中出现 patch summary 和 verification event

### Task 5: 写入并渲染真实 transcript

- 任务目标：把 Stage 0 的 mock transcript 替换为真实 event stream 渲染路径。
- requirement_refs：[R4]
- 修改文件路径：
  - `OpenCAI/tui.py`
  - `OpenCAI/agent_core.py`
- 新建文件路径：
  - `OpenCAI/transcript.py`
- 输入：
  - Agent event stream
- 输出：
  - JSONL transcript 文件
  - Rich TUI 渲染真实事件
- 依赖任务：Task 2, Task 4
- 是否可并行：N
- 类型：AFK
- capability_skills：[]
- 验收标准：
  - transcript 文件包含完整闭环事件。
  - TUI 不拥有 Agent 决策逻辑，只渲染事件。
- 验证命令：
  - `python -m OpenCAI --task "Fix the failing toy project test" --cwd examples/toy_project --verify "python -m unittest discover ."`
- 预期输出：
  - 命令 exit code 为 `0`
  - 输出显示真实 tool call、tool result、patch summary、verification、final answer

## 覆盖度矩阵

| Requirement | Task(s) | 状态 |
|-------------|---------|------|
| R1: Python Agent Core，只接 Gemini | Task 1, Task 2 | 已覆盖 |
| R2: 四个本地工具 | Task 2, Task 4 | 已覆盖 |
| R3: toy project 失败测试和修复 | Task 3, Task 4 | 已覆盖 |
| R4: transcript 记录并渲染完整循环 | Task 5 | 已覆盖 |
| N1: 不做 Stage 2 权限框架 | 无 | 未触及 |
| N2: 不引入 MCP、插件、多 Agent、长期 memory 或复杂 TUI | 无 | 未触及 |
| N3: 不复制 `claude-code/` 闭源实现 | 无 | 未触及 |

## Checkpoints

- 执行前 HITL：确认是否使用 `GEMINI_API_KEY`，以及是否允许新增 `OpenCAI/requirements.txt`。
- Task 3 后 checkpoint：确认 toy project 的失败用例是否足够代表 Stage 1。
- 最终 checkpoint：确认 Stage 1 验证命令、transcript 和状态文档是否满足验收。

## Risks

- Gemini function calling 当前文档更新较快，执行前需要再次核对官方 API 形态。
- 如果本机没有 Gemini API key，Task 2 之后只能验证 dry-run 或失败路径。
- `apply_patch` 第一版如果做得太通用会膨胀；Stage 1 应限制为小文本补丁，复杂安全边界留到 Stage 2。
- 当前工作区已有未提交改动；执行前需要避免覆盖用户已有内容。
