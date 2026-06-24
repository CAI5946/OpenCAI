# 开发状态

## 当前阶段

学习优先路线：Phase 3 准备中。

旧 Stage 1 最小 Agent Loop 暂停。当前不继续直接实现 Gemini 工具调用循环，先按学习优先路线推进组件理解。

旧 Stage 0：观察式 TUI 已存在，并已完成一次命令行验证，作为早期实验保留。

## 已完成

- 已建立学习项目说明。
- 已写入 `docs/claude-code-dev-workflow-plan.md`。
- 已完善项目级 `AGENTS.md`，加入技术栈、目录结构、命令占位和状态维护规则。
- 已实现 `OpenCAI/tui.py` 的 Stage 0 mock transcript 渲染。
- 已确认 Stage 0 可运行：`cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"` exit code 为 `0`。
- 已写入 Stage 1 最小执行计划：`docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`。
- 已完成 Stage 1 Task 1 启动骨架：`python -m OpenCAI` / `OpenCAI\opencai.cmd`、`GEMINI_API_KEY` 缺失提示、`OpenCAI/requirements.txt`。
- 已加入 `.env` + `.gitignore` 配置，启动时会读取项目根目录 `.env`，真实 key 不进入 git。
- 已写入学习优先路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- 已在项目级 `AGENTS.md` 中加入学习优先模式约束。
- 已完成 Phase 0：Component Map 学习，明确 Runtime、Event / Transcript、Tool Model、LLM Adapter、Renderer / TUI、Verification 的职责和边界。
- 已将 Phase 0 学习总结写入 Notion 学习日志 `Stage 0`。
- 已创建用户级 skill `learn-with-dev`，并在 `docs/learning-mode.md` 中记录新对话复用方式。
- 已完成 Phase 1：Event / Transcript Model 学习和最小实现。
- 已新增 `OpenCAI/events.py`，定义最小 event type、公共字段、event helper 和 `mock_transcript()`。
- 已完成 Phase 2：Renderer 学习和最小实现。
- 已改造 `OpenCAI/tui.py`，删除旧 mock event 格式，改为消费 `OpenCAI/events.py` 的正式 event 协议并渲染 transcript。

## 正在做

- 准备进入 Phase 3：Tool Model。

## 下一步

- 先说明 Tool Model 的职责、输入、输出、失败情况和边界。
- 区分 tool schema、tool call、真实工具函数和 tool result。
- 设计 `read_file`、`search_files`、`apply_patch`、`run_command` 的最小接口。
- 在用户确认理解后，再做最小工具模型实现。

## 阻塞/待确认

- 统一验证命令未确认。
- `.env` 中的 Gemini API key 未填写。
- Stage 1 依赖尚未安装或验证；在学习优先路线下暂不阻塞 Phase 2。

## 最近验证

- `cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"`：exit code `0`。
- `python -m OpenCAI --help`：exit code `0`。
- `OpenCAI\opencai.cmd --help`：exit code `0`。
- `python -m OpenCAI --dry-run --task "Fix the failing toy project test" --cwd . --verify "python -m unittest discover ."`：exit code `0`。
- `$env:GEMINI_API_KEY=$null; python -m OpenCAI`：exit code `2`，按预期提示缺少 `GEMINI_API_KEY` 且未发送请求。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\__init__.py OpenCAI\tui.py`：exit code `0`。
- `git check-ignore -v .env`：exit code `0`，确认 `.env` 被 `.gitignore` 忽略。
- `python -m py_compile OpenCAI\events.py`：exit code `0`。
- `python -c "from OpenCAI.events import mock_transcript; ..."`：exit code `0`，确认 mock transcript 包含 6 个事件，且 verification 以 `exit_code=1` 表达 `ok=false`。
- `python -m py_compile OpenCAI\tui.py`：exit code `0`。
- `cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"`：exit code `0`，确认 TUI 能渲染 `events.py` 里的正式 event transcript。

## 当前路线文档

- 当前执行路线：`docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- 历史执行计划：`docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`，已暂停，仅作参考。
