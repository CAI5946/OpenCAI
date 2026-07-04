# AGENTS.md

## 项目概览

- 本项目是 OpenCAI：面向个人开发工作流的 CLI Coding Agent 原型。
- 当前主线是 Workflow：在单 Agent Loop 之上演进可确认、可观察、可恢复的 workflow runtime。
- 当前状态以 `docs/status.md` 为准，长期路线以 `docs/roadmap.md` 为准。

## 技术栈

- 语言：Python。
- 测试：标准库 `unittest`。
- LLM：默认 `GeminiAdapter`；本地确定性调试用 `--adapter fake`。
- 依赖文件：`OpenCAI/requirements.txt`。
- CLI 入口：`python -m OpenCAI`、`OpenCAI\opencai.cmd`。

## 目录结构

- `OpenCAI/`: Python 原型源码。
- `OpenCAI/tooling/`: 工具系统分类模块；`OpenCAI/tools.py` 是兼容门面。
- `tests/`: 单元测试。
- `benchmarks/`: small-task coding agent benchmark harness、fixtures 和 tasks。
- `docs/`: 项目路线、设计文档、状态和日志。
- `docs/status.md`: 当前状态、当前能力、下一步和最近一次验证。
- `docs/logs/`: 开发日志、历史状态和验证记录归档。
- `docs/maps/`: 可视化结构图和 mind map HTML。
- `references/`: 本地 reference-only 外部源码或资料，默认不提交。

## 必读上下文

- 开始任务前先读 `README.md`。
- 涉及当前进度、阻塞、下一步或验证结果时读 `docs/status.md` 和 `docs/roadmap.md`。
- 涉及学习型开发模式或阶段推进时读 `docs/learning-mode.md`。
- 涉及 Workflow 主线时读 `docs/archive/phases/phase-13-dynamic-workflows.md` 和 `docs/features/Workflow.md`。
- 涉及 Context Engineering 时读 `docs/features/Context Engineering.md`。
- 涉及工具系统时读 `docs/features/Tools.md`、`OpenCAI/tooling/` 和 `OpenCAI/tools.py`。

## 常用命令

- 安装依赖：`python -m pip install -r OpenCAI/requirements.txt`。
- 启动 runtime：`python -m OpenCAI`。
- 一次性 task：`python -m OpenCAI --task "Read README"`。
- 显式 fake adapter：`python -m OpenCAI --adapter fake`。
- 查看版本：`python -m OpenCAI --version`。
- Workflow smoke：`cmd /c "(echo /workflow Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`。
- Python 语法检查：`python -m py_compile OpenCAI\__main__.py OpenCAI\__init__.py OpenCAI\tui.py OpenCAI\agent_loop.py OpenCAI\llm_adapter.py`。
- 全量测试：`python -m unittest discover tests`。
- Benchmark fake baseline：`python -m benchmarks.runner --task all --timeout 30`。
- Benchmark Gemini baseline：`python -m benchmarks.runner --task all --adapter gemini --timeout 180`。

## 开发约定

- 保持小切片、可验证；不要把 workflow 编排塞进 `agent_loop.py`。
- `OpenCAI/tui.py` 只负责 input helper 和 transcript renderer，不承载 Agent 决策逻辑。
- 新工具默认进入 `OpenCAI/tooling/<category>_tools.py`；不要继续堆回 `OpenCAI/tools.py`。
- SafetyPolicy 已接入工具执行前置检查；默认 permission profile 是 `approve-safe`。
- Context Engineering 当前从 Session 初始化 context、AGENTS.md entry points 和 provider-independent messages 开始，不默认引入 vector DB 或长期 memory。
- 不新增嵌套 `AGENTS.md`，除非子目录有明确不同的命令或规则。
- 不复制闭源、未授权或来源不明实现；参考资料只用于抽象设计原则和取舍。

## Reference-first

- 用户要求参考 Claude Code 或 Codex 设计时，优先查看本地 `references/claude-code/` 和 `references/codex/`。
- `references/` 是 reference-only 目录，默认被 `.gitignore` 忽略，不作为 OpenCAI 源码提交。
- 参考本地源码时，只提炼模块边界、交互流程、数据结构和工程取舍；不要复制实现代码。
- 如果本地参考不足，再查公开文档、成熟工程惯例或其他开源实现。

## 状态维护

- 开发进度不要写进本文件；当前状态维护在 `docs/status.md`。
- 阶段完成、下一步变化、出现阻塞或验证结果变化时，更新 `docs/status.md`。
- 长历史、验证流水和开发日志归档到 `docs/logs/`，不要堆进 `docs/status.md`。
- 稳定计划写入 `docs/plans/`。

## 验证

- 修改文档：至少读取目标文件并检查 diff。
- 修改 Python 原型：运行相关入口命令，并至少运行 `python -m py_compile` 覆盖改动文件。
- 修改 Runtime 入口：运行 `python -m OpenCAI --help`、dry run 和一次 fake loop。
- 修改 Workflow：优先运行 `python -m unittest tests.test_runtime_commands tests.test_workflow`，并跑 `/workflow` smoke。
- 修改 Context Engineering：优先运行 `python -m unittest tests.test_context tests.test_llm_adapter tests.test_runtime_session tests.test_agent_loop_streaming`。
- 只有 `python -m unittest discover tests` 通过后，才能声称全量测试通过。

## 注意事项

- `.env` 用于本地 `GEMINI_API_KEY`，不得提交真实 key。
- 缺少 `GEMINI_API_KEY` 时，默认 Gemini adapter 会启动失败；本地调试用 `--adapter fake`。
- 真实 Gemini 接入继续使用当前 `google-genai` function calling API；不要使用 deprecated Gemini SDK。
- `benchmarks/runs/` 和 `benchmarks/results/` 是 benchmark 运行产物。
- `.agents/`、`.codex/` 是项目局部 Agent/Codex 配置或产物目录，修改前先确认具体用途。
