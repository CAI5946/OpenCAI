# Claude_Learn Agent 规则

## 项目概览

- 本项目用于学习并复刻 Claude Code 类 Coding Agent 的开发工作流。
- 目标是理解并实现 Claude Code 式最小可验证闭环。
- `claude-code/` 仅作为架构和行为参考，不作为可复制实现来源。

## 技术栈

- 当前仓库主体：Markdown 学习文档和本地参考资料。
- Stage 0 计划：Python + Rich，用于 mock transcript 渲染。
- Stage 1 计划：Python + Gemini，用于最小 Agent Loop。
- 依赖管理、测试框架、CLI 入口：未确认；不要编造命令或配置。

## 目录结构

- `README.md`: 项目入口和学习边界。
- `AGENTS.md`: 稳定项目规则。
- `docs/`: 路线、架构、开发计划和状态记录。
- `docs/status.md`: 动态开发进度。
- `outputs/`: 可视化或生成输出，不是核心源码。
- `claude-code/`: Claude Code 本地参考快照，只用于架构和行为对照。
- `.agents/`、`.codex/`: 本项目局部 Agent/Codex 配置或产物目录，修改前先确认具体用途。

## 必读上下文

- 开始任务前先读 `README.md`。
- 涉及开发流程时读 `docs/claude-code-dev-workflow-plan.md`。
- 涉及当前进度时读 `docs/status.md`。

## 常用命令

- 安装依赖：未确认。
- 本地运行：未确认。
- 测试：未确认。
- Lint/格式化：未确认。
- 构建：未确认。

## 开发约定

- 保持最小改动；写文件前先确认范围。
- 不主动添加复杂 UI、MCP、插件、多 Agent、长期 memory。
- 不新增嵌套 `AGENTS.md`，除非子目录有明确不同的命令或规则。
- 不复制闭源、未授权或来源不明实现；复刻目标是工作流、交互行为和架构概念。

## 状态维护

- 开发进度不要写进本文件；进度维护在 `docs/status.md`。
- 阶段完成、下一步变化、出现阻塞或验证结果变化时，更新 `docs/status.md`。

## 验证

- 当前统一验证命令：未确认。
- 修改后应通过读取、diff 或可运行命令确认结果。
