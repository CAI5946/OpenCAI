# AGENTS.md

## 项目概览

- 本项目用于学习 Claude Code 类 Coding Agent 的开发工作流，并逐步实现个人可用的最小 Coding Agent。
- 当前目标是跑通 Claude Code 式最小可验证闭环：读上下文、调工具、改文件、运行验证、继续迭代。
- `claude-code/` 仅作为架构和行为参考，不作为可复制实现来源。

## 技术栈

- 当前仓库主体：Markdown 学习文档和本地参考资料。
- 原型语言：Python。
- Stage 0：Python + Rich，用于 mock transcript 渲染。
- Stage 1：Python + Gemini API，用于最小 Agent Loop。
- 依赖文件：`OpenCAI/requirements.txt`。
- CLI 入口：`python -m OpenCAI`、`OpenCAI/opencai.cmd`。
- 测试框架：未确认；当前计划优先使用 Python 标准库 `unittest` 做 toy project 验证。

## 目录结构

- `README.md`: 项目入口和学习边界。
- `AGENTS.md`: 稳定项目规则。
- `OpenCAI/`: 当前 Python 原型代码。
- `docs/`: 路线、架构、开发计划、状态记录。
- `docs/plans/`: 已确认或待执行的阶段计划。
- `docs/learning-mode.md`: 学习型开发模式说明，新对话继续学习阶段时优先读取。
- `docs/status.md`: 动态开发进度。
- `outputs/`: 可视化或生成输出，不是核心源码。
- `claude-code/`: Claude Code 本地参考快照，只用于架构和行为对照。
- `.agents/`、`.codex/`: 本项目局部 Agent/Codex 配置或产物目录，修改前先确认具体用途。

## 必读上下文

- 开始任务前先读 `README.md`。
- 涉及学习型开发模式、阶段推进或新对话续接时读 `docs/learning-mode.md`。
- 涉及当前进度、阻塞或验证结果时读 `docs/status.md`。
- 涉及开发流程和阶段边界时读 `docs/claude-code-dev-workflow-plan.md`。
- 涉及 Stage 1 执行时读 `docs/plans/2026-06-21-stage-1-minimal-agent-loop-plan.md`。
- 涉及 Claude Code 主循环理解时读 `docs/core-loop-architecture.md`。

## 常用命令

- 安装依赖：`python -m pip install -r OpenCAI/requirements.txt`。
- Stage 0 TUI：`cmd /c "echo Fix the failing toy project test|python OpenCAI\tui.py"`。
- Stage 1 help：`python -m OpenCAI --help`。
- Stage 1 Windows 入口：`OpenCAI\opencai.cmd --help`。
- Stage 1 dry run：`python -m OpenCAI --dry-run --task "Fix the failing toy project test" --cwd . --verify "python -m unittest discover ."`。
- Python 语法检查：`python -m py_compile OpenCAI\__main__.py OpenCAI\__init__.py OpenCAI\tui.py`。
- 测试：统一测试命令未确认。
- Lint/格式化：未确认。
- 构建：未确认。

## 开发约定

- 保持最小改动；写文件前先确认范围。
- 当前采用学习优先模式：默认先解释设计意图、输入输出、状态、失败情况和取舍，再进入实现。
- 可显式使用用户级 skill `$learn-with-dev` 复用学习型开发模式：先讲解、再提问检查、纠正误区、确认范围、最小实现、验证和复盘。
- 暂停以交付完整原型为主的推进方式；除非用户明确要求，否则不要连续补齐多个组件。
- 每次只聚焦一个 Agent 组件，例如 event stream、tool schema、agent loop、tool adapter、transcript 或 TUI。
- 代码必须服务理解；每次最多做一个小的、可观察的实现点，并配合可运行或可检查的例子。
- 进入下一个组件前，先帮助用户确认当前组件的职责、边界和为什么这样设计。
- 不主动添加复杂 UI、MCP、插件、多 Agent、长期 memory。
- 不新增嵌套 `AGENTS.md`，除非子目录有明确不同的命令或规则。
- 不复制闭源、未授权或来源不明实现；复刻目标是工作流、交互行为和架构概念。
- `OpenCAI/tui.py` 只负责 transcript 渲染，不承载 Agent 决策逻辑。
- Stage 1 先实现 `read_file`、`search_files`、`apply_patch`、`run_command` 四个最小工具；权限框架留到 Stage 2。

## 状态维护

- 开发进度不要写进本文件；进度维护在 `docs/status.md`。
- 阶段完成、下一步变化、出现阻塞或验证结果变化时，更新 `docs/status.md`。
- 稳定计划写入 `docs/plans/`；不要用临时聊天结论替代项目文档。

## 验证

- 修改文档：至少读取目标文件并检查 diff。
- 修改 Python 原型：运行相关入口命令，并至少运行 `python -m py_compile` 覆盖改动文件。
- 修改 Stage 0 TUI：运行 Stage 0 TUI 命令确认 transcript 可渲染。
- 修改 Stage 1 启动入口：运行 `python -m OpenCAI --help` 和 dry-run。
- 当前统一测试命令未确认；不要声称完整测试通过。

## 注意事项

- `.env` 用于本地 `GEMINI_API_KEY`，不得提交真实 key。
- `.env.example` 只保留变量名示例。
- 缺少 `GEMINI_API_KEY` 时，`python -m OpenCAI` 应提示缺失并且不发送请求。
- `outputs/` 是生成产物目录，不是核心源码。
- `.agents/`、`.codex/` 是项目局部 Agent/Codex 配置或产物目录，修改前先确认具体用途。
