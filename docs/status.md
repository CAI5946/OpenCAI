# 开发状态

## 当前阶段

Stage 1 准备中。

Stage 0：观察式 TUI 已存在，并已完成一次命令行验证。

## 已完成

- 已建立学习项目说明。
- 已写入 `docs/claude-code-dev-workflow-plan.md`。
- 已完善项目级 `AGENTS.md`，加入技术栈、目录结构、命令占位和状态维护规则。
- 已实现 `OpenCAI/tui.py` 的 Stage 0 mock transcript 渲染。
- 已确认 Stage 0 可运行：`cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"` exit code 为 `0`。
- 已写入 Stage 1 最小执行计划：`docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`。
- 已完成 Stage 1 Task 1 启动骨架：`python -m OpenCAI` / `OpenCAI\opencai.cmd`、`GEMINI_API_KEY` 缺失提示、`OpenCAI/requirements.txt`。
- 已加入 `.env` + `.gitignore` 配置，启动时会读取项目根目录 `.env`，真实 key 不进入 git。

## 正在做

- 准备进入 Stage 1：最小 Agent Loop。

## 下一步

- 进入 Stage 1 Task 2：实现 Gemini 最小工具调用循环。
- 确认本机是否已经设置 `GEMINI_API_KEY`。

## 阻塞/待确认

- 统一验证命令未确认。
- `.env` 中的 Gemini API key 未填写。
- Stage 1 依赖尚未安装或验证。

## 最近验证

- `cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"`：exit code `0`。
- `python -m OpenCAI --help`：exit code `0`。
- `OpenCAI\opencai.cmd --help`：exit code `0`。
- `python -m OpenCAI --dry-run --task "Fix the failing toy project test" --cwd . --verify "python -m unittest discover ."`：exit code `0`。
- `$env:GEMINI_API_KEY=$null; python -m OpenCAI`：exit code `2`，按预期提示缺少 `GEMINI_API_KEY` 且未发送请求。
- `python -m py_compile OpenCAI\__main__.py OpenCAI\__init__.py OpenCAI\tui.py`：exit code `0`。
- `git check-ignore -v .env`：exit code `0`，确认 `.env` 被 `.gitignore` 忽略。
