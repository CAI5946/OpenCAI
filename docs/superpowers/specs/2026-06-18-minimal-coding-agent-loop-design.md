# Minimal Coding Agent Loop Design

## Status

Draft for discussion. This document defines the first learning milestone and the path from a minimal loop toward a more complete Coding Agent. It is not an implementation plan.

## Goal

Build the smallest useful Coding Agent prototype that proves the full loop can run:

```text
user task
-> Gemini decides what tool to call
-> local tool executes
-> tool result returns to Gemini
-> Gemini continues
-> file is modified
-> verification command runs
-> final answer summarizes outcome
```

The purpose is learning the core mechanics, not competing with Claude Code or Codex. A motivating terminal interface is part of the learning experience, but it must remain a thin event renderer around the agent core.

## Learning Constraints

This is a learning project. The codebase should be built in small steps that the human owner can understand, explain, and modify.

Rules:

- Prefer Python because it is already familiar to the owner.
- Do not write large batches of code in one pass.
- Each implementation step should introduce one concept or one small module.
- Each step should be runnable or inspectable before moving on.
- Favor readable, explicit code over clever abstractions.
- Write notes when borrowing ideas from `claude-code/src`.
- Stop and discuss when a feature would hide core mechanics behind a framework.

## Non-Goals

- No complex terminal UI.
- No slash commands.
- No MCP.
- No plugin or skill system.
- No multi-agent orchestration.
- No long-term memory.
- No large-repo context compression.
- No automatic destructive filesystem operations.
- No attempt to process the `claude-code/` snapshot as a live target repo.

The first TUI is allowed only as a thin transcript shell. It should display user input, assistant text, tool calls, tool results, patch summaries, and verification status. It should not own agent logic.

## Reference Boundary

The local `claude-code/` directory is used only as an architectural reference. The prototype should extract concepts such as query loop, tool schema, permission boundary, and verification loop. It should not copy leaked or proprietary implementation details.

## Reference Study Method

Do not read `claude-code/src` by directory order. The source tree is too large and too product-specific for that to be useful. Study it by question and by prototype stage.

For each prototype stage, choose a small set of reference files and answer one design question:

```text
research question:
reference files:
observed design:
do we need it now:
Python MVP landing:
deferred parts:
```

Stage-to-reference mapping:

- Minimal loop: study `QueryEngine.ts` and `query.ts` for the model/tool/observation loop.
- Tool interface: study `Tool.ts` and `tools.ts` for schema, validation, and execution boundaries.
- Local execution safety: study `services/tools/`, `BashTool`, and `PowerShellTool` for permission checks and command risk classification.
- Context discipline: study `context.ts` and selected `memdir/` files for project rules, runtime context, and memory boundaries.
- Editing workflow: study `FileReadTool`, `FileEditTool`, and `FileWriteTool` for read/edit/write separation and failure feedback.
- Usability layer: study `commands.ts` and selected `commands/` files only after the core loop is stable.
- Extensibility: study `plugins/`, `skills/`, and `services/mcp/` only after repeated real needs appear.

Milestone one may borrow only four ideas:

- query loop
- tool schema
- permission boundary
- verification feedback

Milestone one should not borrow terminal UI, slash commands, plugins, skills, MCP, multi-agent coordination, remote sessions, IDE bridge, voice mode, or long-term memory.

## First Milestone

The first milestone is a Python prototype using Gemini, a toy repository, and a thin TUI transcript shell.

Example task:

```text
Fix the failing test in examples/toy_project and run the verification command.
```

Expected loop:

1. The user starts the agent with a task and working directory.
2. The TUI renders the task and an initial assistant status.
3. The agent builds a small prompt from system instructions, cwd, available tools, and recent messages.
4. Gemini requests a tool call such as `search_files` or `read_file`.
5. The local runtime validates and executes the tool.
6. The agent emits a tool event, and the TUI renders the event.
7. The result is appended to the conversation as an observation.
8. Gemini requests `apply_patch` when it has enough context.
9. The local runtime applies the patch and emits a patch summary event.
10. The agent runs the configured verification command.
11. Gemini receives verification output and produces the final response.
12. The TUI renders the final status.

Success means the loop closes at least once on a small controlled bug.

## Provider

Use Gemini first.

Default configuration:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
LLM_MODEL=gemini-2.5-flash
```

Provider code should be small and replaceable, but the first version only needs Gemini. A provider abstraction is useful only if it stays minimal:

```text
LLMClient.send(messages, tools) -> assistant message or tool calls
```

Do not add multi-provider routing in milestone one.

## Minimal Architecture

```text
TUI Shell
  -> Agent Core
     -> Session
     -> ContextBuilder
     -> GeminiClient
     -> ToolRegistry
     -> PermissionGuard
     -> ToolExecutor
     -> TranscriptLogger
```

The core rule is:

```text
Agent Core -> emits events -> TUI renders events
```

Do not let the TUI own agent logic.

### TUI Shell

The first TUI should be a transcript view, not a full app. It renders:

- user task
- assistant status text
- tool call name and compact input
- tool result summary
- patch summary
- verification exit code
- final answer

Recommended Python stack:

- `rich` for panels, colors, Markdown, and status output
- `prompt_toolkit` later for better input history and multiline input

Avoid `textual` in the first milestone unless the transcript shell becomes too limiting. It is powerful but can distract from the agent loop.

### CLI Adapter

Parses:

- task text
- working directory
- optional verification command
- max loop count

It should stay boring. The TUI can wrap this adapter, but the adapter should still be usable in tests without the TUI.

### Session

Owns:

- `cwd`
- `messages`
- `max_steps`
- `tool_results`
- final status

The session loop is the heart of the prototype:

```text
while steps remain:
  call Gemini with messages and tool schemas
  if final text: stop
  if tool call: execute tool and append observation
  if error: append error observation or stop
```

### ContextBuilder

Adds only the minimum context:

- current working directory
- platform information
- project rule files if present, such as `AGENTS.md`, `CLAUDE.md`, or `README.md`
- available tools and usage rules

It should not scan the whole repository. The model must learn to request files through tools.

### ToolRegistry

Defines the tools Gemini can request. Each tool has:

- name
- description
- JSON schema
- execution function
- read/write risk level

### PermissionGuard

Milestone one uses conservative rules:

- `read_file`: allowed inside cwd.
- `search_files`: allowed inside cwd.
- `run_command`: allow only configured verification command and simple read-only inspection commands.
- `apply_patch`: allowed only inside cwd.
- delete, move, recursive destructive commands: unsupported.

This keeps the prototype safe enough for learning without designing a full policy engine.

### TranscriptLogger

Writes a simple JSONL or Markdown transcript:

- user task
- model tool request
- tool input
- tool output summary
- patch result
- verification result
- final response

The transcript is part of the learning loop. It makes the invisible state machine inspectable.

## First Tools

### `read_file`

Input:

```json
{ "path": "relative/path" }
```

Behavior:

- resolve path under cwd
- reject paths outside cwd
- return text with size limit

### `search_files`

Input:

```json
{ "query": "text or regex", "path": "." }
```

Behavior:

- run `rg`
- cap output length
- return matching lines and file paths

### `run_command`

Input:

```json
{ "command": "python -m pytest" }
```

Behavior:

- allow the configured verification command
- optionally allow read-only commands
- capture exit code, stdout, and stderr
- cap output length

### `apply_patch`

Input:

```json
{ "patch": "unified patch text" }
```

Behavior:

- apply a structured patch
- reject paths outside cwd
- return changed files and errors

For the first implementation, patch format should be strict. This is easier to debug than asking the model to emit arbitrary file content.

## Toy Project

Create a tiny project under:

```text
examples/toy_project/
```

Recommended first toy:

```text
calculator.py
test_calculator.py
```

The bug should be obvious but require a real loop:

- test fails
- agent reads test
- agent reads source
- agent patches source
- agent runs test
- test passes

This avoids wasting effort on real project complexity before the agent loop exists.

## Error Handling

Milestone one only needs simple handling:

- invalid tool name: return an error observation
- invalid tool input: return an error observation
- command timeout: return exit failure observation
- patch failure: return error observation
- max steps reached: stop with incomplete status

Do not build retry frameworks yet. Let Gemini observe the error and decide the next action.

## Verification

Verification is explicit. The CLI accepts a command such as:

```powershell
python -m pytest examples/toy_project
```

If no verification command is provided, the agent can still modify files, but it must report that verification was not run.

For the first milestone, success requires:

- at least one tool call before editing
- at least one file patch
- verification command executed
- verification exits with code `0`
- final transcript records the full loop

## Evolution Path

### Stage 0: Motivating TUI Shell

Purpose: create a Claude Code-like feeling that makes the learning project enjoyable without hiding the core mechanics.

Capabilities:

- Python terminal transcript view
- visible user task
- visible assistant status
- visible tool call and tool result events
- visible patch and verification summaries
- no business logic in the UI layer

Stop condition:

- A mocked agent event stream can be rendered clearly in the terminal.

Stage 0 handoff for a new conversation:

```text
Project: D:\AI-Agent\Claude_Learn
Design doc: docs/superpowers/specs/2026-06-18-minimal-coding-agent-loop-design.md

Goal:
Implement Stage 0 only: a motivating Python TUI transcript shell for a learning Coding Agent project.

Constraints:
- This is a learning project. Do not write a large codebase in one pass.
- Use Python.
- Keep each step small, readable, and explainable.
- The TUI must be a thin renderer around events.
- Do not implement Gemini, tools, patching, or real agent logic yet.
- Do not add slash commands, MCP, plugins, skills, multi-agent logic, or memory.

Recommended first step:
Create a tiny mocked event stream and render it in the terminal using Rich.

Target behavior:
The terminal should show a Claude Code-like transcript with:
- user task
- assistant status
- tool call
- tool result summary
- patch summary
- verification status
- final answer

Acceptance:
A mocked agent event stream renders clearly in the terminal, and the rendering code is separate from future agent core logic.
```

### Stage 1: Minimal Loop

Purpose: prove the agent loop works end to end.

Capabilities:

- Gemini function calling
- four local tools
- toy project repair
- transcript logging
- TUI rendering of real agent events
- max-step guard

Stop condition:

- The toy project can be fixed from a natural language task without manually telling the agent which file to edit.

### Stage 2: Safer Local Coding Agent

Purpose: make the loop usable on small personal repos.

Add:

- project rule loading
- better path sandboxing
- explicit command allowlist
- diff preview before patch
- verification command presets
- clearer final status

Still avoid:

- multi-agent work
- plugins
- long-term memory
- complex UI

### Stage 3: Context Discipline

Purpose: handle larger repos without dumping everything into the prompt.

Add:

- file tree summary
- search-first behavior
- file read cache
- output truncation and summarization
- context budget accounting
- basic transcript compaction

Key lesson:

- Coding Agents succeed by gathering the right context incrementally, not by reading the whole repo.

### Stage 4: Real Editing Workflow

Purpose: make edits more reliable and reviewable.

Add:

- structured patch validation
- changed-file summary
- before/after diff
- automatic cleanup of only touched files
- test failure feedback loop
- optional user approval before write operations

Key lesson:

- File modification is not just "write text"; it is a controlled transaction with evidence.

### Stage 5: Command and Permission Model

Purpose: separate model intent from local authority.

Add:

- read-only command detection
- write command classification
- destructive command hard blocks
- per-project permission config
- command timeout and cancellation
- audit log

Key lesson:

- The LLM requests actions. The runtime decides whether actions are allowed.

### Stage 6: Usability Layer

Purpose: make the agent pleasant without changing the core loop.

Add:

- interactive CLI
- task resume
- `/status`, `/diff`, `/verify`
- colored transcript output
- better errors

Only add this after the core loop is stable.

### Stage 7: Extensibility

Purpose: support multiple workflows.

Add:

- provider interface for Groq, OpenRouter, Ollama, or OpenAI-compatible APIs
- tool plugins
- project-local skills
- MCP client
- optional LSP integration

Key lesson:

- Extensibility should grow from repeated real needs, not from imitating mature products too early.

### Stage 8: Advanced Agent Features

Purpose: explore mature Coding Agent ideas.

Possible additions:

- planning mode
- sub-agent tasks
- worktree isolation
- long-running background tasks
- memory extraction
- IDE bridge

These are intentionally late-stage. They are expensive and unnecessary until the single-agent loop is reliable.

## Main Risks

### Overbuilding

The biggest risk is copying the surface area of Claude Code before understanding the state machine. Avoid UI, commands, plugin systems, and multi-agent features until the minimal loop is boring.

### Weak Tool Calling

Some models may produce bad tool arguments or skip needed tools. The first version should log every tool request and error so failures are easy to study.

### Unsafe Local Execution

Even a learning agent can damage files. Keep all first tests inside `examples/toy_project/`, reject paths outside cwd, and avoid destructive commands.

### Poor Verification

Without a verification command, the agent can only claim it edited files. The first milestone must include a real test command and exit code.

## Open Questions

1. Should `apply_patch` call a local patch library, a git patch command, or a custom strict patch parser?
2. Should the first transcript shell use only `rich`, or combine `rich` with `prompt_toolkit` from the start?
3. Should the first user input be single-shot only, or allow one interactive follow-up after the final response?

## Recommendation

Use Python for the first milestone. Python keeps the prototype smaller and makes subprocess, file handling, and toy tests easy.

Use Gemini as the only provider in milestone one. Keep the provider boundary thin enough that it can be replaced later.

Start with a thin TUI transcript shell over a testable agent core. The first TUI can render mocked events before Gemini is connected. Add richer interactivity only after the transcript proves the loop is correct.
