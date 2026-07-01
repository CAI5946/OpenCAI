# AGENTS.md

## 项目概览

- 本项目是 OpenCAI：面向个人开发工作流的完整成熟 CLI Coding Agent。
- 当前目标是设计并开发完整成熟的 Coding Agent：读上下文、调工具、改文件、运行验证、继续迭代，并通过 workflow runtime 编排多阶段自动化，后续继续演进 Multi-agents、Modes、Streaming Outputs、LLM Council 和可审计状态。

## 技术栈

- 当前仓库主体：Markdown 学习文档和本地参考资料。
- 原型语言：Python。
- 当前路线：Phase 0-12 已完成基础组件、交互式 runtime、Gemini adapter、tool closed loop、Minimal Safety Layer、单 Agent core 和产品化 CLI；Phase 13 已完成 WorkflowRunner 第一组切片。
- 后续路线：当前主线是 Feature A: Workflow，继续补 `/workflow` confirmation gate、Nodeflow-style workflow、retry loop、humancheck、save/replay 和后续 subagent 编排。
- Runtime / Renderer：`python -m OpenCAI`、`OpenCAI/opencai.cmd` 默认进入交互式 runtime；普通 task 走 Agent Loop，`/workflow TASK` 走 WorkflowRunner，`--task` 保留为一次性调试路径；Rich transcript renderer 展示事件流和折叠/展开的 process view。
- LLM：当前默认使用 `GeminiAdapter`；`FakeLLMAdapter` 保留为本地确定性调试入口，可通过 Runtime 的 `--adapter fake` 显式选择。真实 Gemini 已完成 text smoke 与 `read_file -> function_response -> final_answer` 核心验证。
- 依赖文件：`OpenCAI/requirements.txt`。
- CLI 入口：`python -m OpenCAI`、`OpenCAI/opencai.cmd`。
- 测试框架：Python 标准库 `unittest`；本地 benchmark harness 位于 `benchmarks/`。

## 目录结构

- `README.md`: 项目入口和学习边界。
- `AGENTS.md`: 稳定项目规则。
- `OpenCAI/`: 当前 Python 原型代码。
- `tests/`: `unittest` 测试。
- `benchmarks/`: small-task coding agent benchmark harness、fixtures、tasks、results 和 runs。
- `docs/`: 路线、架构、开发计划、状态记录。
- `docs/features/`: Feature 设计文档。
- `docs/goals/`: 产品验收目标文档。
- `docs/plans/`: 已确认或待执行的阶段计划。
- `docs/phases/`: Phase 学习日志和阶段架构记录。
- `docs/learning-mode.md`: 学习型开发模式说明，新对话继续学习阶段时优先读取。
- `docs/status.md`: 动态开发进度。
- `outputs/`: 可视化或生成输出，不是核心源码。
- `.agents/`、`.codex/`: 本项目局部 Agent/Codex 配置或产物目录，修改前先确认具体用途。

## 必读上下文

- 开始任务前先读 `README.md`。
- 涉及学习型开发模式、阶段推进或新对话续接时读 `docs/learning-mode.md`。
- 涉及当前进度、阻塞或验证结果时读 `docs/status.md`。
- 涉及开发流程和阶段边界时读 `docs/plans/2026-06-22-learning-first-agent-roadmap.md`。
- 涉及 OpenCAI 主循环理解时读 `docs/phases/core-loop-architecture.md`。
- 涉及 Workflow 主线时读 `docs/phases/phase-13-dynamic-workflows.md`。
- 涉及 Context Engineering 时读 `docs/features/Context Engineering.md`。
- 涉及 benchmark 和产品验收时读 `docs/goals/small-task-coding-agent-competence.md`。

## 常用命令

- 安装依赖：`python -m pip install -r OpenCAI/requirements.txt`。
- Phase runtime：`python -m OpenCAI`。
- 一次性 task：`python -m OpenCAI --task "Read README"`。
- Windows 入口：`OpenCAI\opencai.cmd`。
- 查看开发态版本：`python -m OpenCAI --version`。
- 显式 fake adapter：`python -m OpenCAI --adapter fake`。
- Dry run：`python -m OpenCAI --dry-run --task "Read README"`。
- Workflow smoke：`cmd /c "(echo /workflow Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"`。
- Permission smoke：`cmd /c "(echo /status&echo /permission full-access&echo /status&echo /exit)|python -m OpenCAI --adapter fake --max-steps 5"`。
- TUI input helper smoke：`cmd /c "echo Read README|python OpenCAI\tui.py"`。
- Python 语法检查：`python -m py_compile OpenCAI\__main__.py OpenCAI\__init__.py OpenCAI\tui.py OpenCAI\agent_loop.py OpenCAI\llm_adapter.py`。
- 测试：`python -m unittest discover tests`。
- Benchmark fake baseline：`python -m benchmarks.runner --task all --timeout 30`。
- Benchmark Gemini baseline：`python -m benchmarks.runner --task all --adapter gemini --timeout 180`。
- Lint/格式化：未确认。
- 构建：未确认。

## 开发约定

- 保持最小改动；写文件前先确认范围。
- 项目目标不是“最小可行玩具版”，而是完整成熟 Coding Agent；“最小”只表示单次实现切片要小、可验证，不表示架构目标、功能边界或用户体验可以缩水。
- KISS 用于避免无效复杂度，不用于省略成熟 Agent 必需的状态、权限、验证、可观察性、恢复路径、用户确认和长期演进接口。
- 当前采用学习优先模式：默认先解释设计意图、输入输出、状态、失败情况和取舍，再进入实现。
- 后续阶段以 OpenCAI 自身需求为主线推进；需要参考外部资料时优先使用公开文档、成熟工程惯例和项目内已有实现。
- 可显式使用用户级 skill `$learn-with-dev` 复用学习型开发模式：先讲解、再提问检查、纠正误区、确认范围、最小实现、验证和复盘。
- 不再以一次性交付完整系统为推进方式；除非用户明确要求，否则不要连续补齐多个组件。
- 每次只聚焦一个 Agent 组件，例如 event stream、tool schema、agent loop、tool adapter、transcript 或 TUI。
- 代码必须服务理解；每次可以只落一个小的、可观察的实现点，但该实现点必须放在完整成熟 Agent 的最终设计边界里，避免为了“最小”制造后续难以扩展的临时结构。
- 进入下一个组件前，先帮助用户确认当前组件的职责、边界和为什么这样设计。
- 复杂 UI、MCP、插件、多 Agent、长期 memory 等能力需要先完成设计评估和阶段边界确认；Dynamic Workflows 当前从单 Agent、串行 phase 和可观察状态开始，但最终设计必须为成熟 workflow runtime 留出保存/恢复、并发、审计和 humancheck 扩展点。
- 不新增嵌套 `AGENTS.md`，除非子目录有明确不同的命令或规则。
- 不复制闭源、未授权或来源不明实现；实现必须来自 OpenCAI 自身需求和可验证的公开资料。
- `OpenCAI/tui.py` 当前只负责 input helper 和 transcript renderer，不承载 Agent 决策逻辑；必须明确区分 TUI Shell 和 Renderer。
- 当前工具模型包含 `read_file`、`search_files`、`apply_patch`、`run_command` 四个基础工具 spec；`read_file`、`run_command`、`apply_patch` 和 `search_files` 已实现，后续按成熟 Coding Agent 需要继续补齐能力和安全边界。
- SafetyPolicy 已接入工具执行前置检查；默认 permission profile 是 `approve-safe`，支持 `read-only` / `ask-approval` / `approve-safe` / `full-access`。
- 后续 Dynamic Workflows 不应塞进 `agent_loop.py`；`Agent Loop` 继续负责单个 agent 的 model/tool/observation 循环，workflow 编排应放到独立 runtime / runner 层。
- Context Engineering 不等于传统 RAG；当前从 Session 初始化 context、AGENTS.md entry points 和 provider-independent messages 开始，不默认引入 vector DB 或长期 memory。

## 状态维护

- 开发进度不要写进本文件；进度维护在 `docs/status.md`。
- 阶段完成、下一步变化、出现阻塞或验证结果变化时，更新 `docs/status.md`。
- Phase 完成时按 `docs/learning-mode.md` 的 Phase 收口模板执行，检查 `docs/status.md`、本地学习日志、Notion 学习日志、验证命令和 git checkpoint。
- 稳定计划写入 `docs/plans/`；不要用临时聊天结论替代项目文档。

## 验证

- 修改文档：至少读取目标文件并检查 diff。
- 修改 Python 原型：运行相关入口命令，并至少运行 `python -m py_compile` 覆盖改动文件。
- 修改 Runtime 交互路径：运行 `cmd /c "(echo Read README&echo /exit)|python -m OpenCAI"` 确认输入循环、fake loop 和 transcript 可运行。
- 修改 Renderer：运行 `python -m OpenCAI --task "Read README"` 确认 transcript 可渲染。
- 修改 Runtime 入口：运行 `python -m OpenCAI --help`、dry run 和一次 fake loop。
- 修改 Workflow：优先运行 `python -m unittest tests.test_runtime_commands tests.test_workflow`，并用 fake adapter 跑 `/workflow` smoke。
- 修改 Context Engineering：优先运行 `python -m unittest tests.test_context tests.test_llm_adapter tests.test_runtime_session tests.test_agent_loop_streaming`。
- 全量回归：`python -m unittest discover tests`；只在该命令通过后声称当前测试全量通过。

## 注意事项

- `.env` 用于本地 `GEMINI_API_KEY`，不得提交真实 key。
- `.env.example` 只保留变量名示例。
- 当前默认 runtime 使用 Gemini adapter；缺少 `GEMINI_API_KEY` 时启动 adapter 会失败。需要本地确定性调试时显式使用 `--adapter fake`。
- 默认 permission profile 是 `approve-safe`；当前 ask gate 尚未实现，需确认的模型工具调用会作为 deny observation 返回。
- 真实 Gemini 接入继续使用当前 `google-genai` function calling API；不要使用 deprecated Gemini SDK，不要让 Agent Loop 依赖 Gemini response 结构。
- `outputs/` 是生成产物目录，不是核心源码。
- `benchmarks/runs/` 和 `benchmarks/results/` 是 benchmark 运行产物；更新规则前先确认是否需要保留证据。
- `.agents/`、`.codex/` 是项目局部 Agent/Codex 配置或产物目录，修改前先确认具体用途。
