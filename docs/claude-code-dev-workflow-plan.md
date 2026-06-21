# 复刻 Claude Code 开发流程计划

## 目标

复刻 Claude Code 类 Coding Agent 的开发工作流闭环。

核心闭环：

```text
用户任务
-> 读取规则和上下文
-> 制定或更新计划
-> 搜索和读取相关文件
-> 调用本地工具
-> 生成并应用补丁
-> 运行验证命令
-> 根据失败结果继续迭代
-> 输出最终结果
```

成功标准不是“模型能回答”，而是“模型能在受控权限下完成一次 Claude Code 式的可验证代码修改循环”。

## 边界

- 本项目是学习项目，优先理解核心机制。
- `claude-code/` 仅作为架构和行为对照，不作为可复制实现来源。
- 第一阶段不做完整产品、不追求功能覆盖。
- 每个阶段必须小步推进、可运行、可解释。

暂不做：

- 复杂 TUI 或完整交互式应用
- slash command 系统
- MCP、插件、skill marketplace
- 多 Agent 协作
- 长期记忆自动同步
- 远程会话、IDE bridge、语音模式
- 大型权限策略框架

## 阶段计划

### Stage 0：观察式 TUI

目标：先做一个薄的 transcript 渲染层，让开发流程可观察。

能力：

- 显示用户任务
- 显示 assistant 状态
- 显示 tool call 和 tool result
- 显示 patch summary
- 显示 verification status
- 显示 final answer

限制：

- 不接 LLM
- 不实现真实工具
- 不改真实文件
- 不把业务逻辑写进 UI 层

验收：

- mock event stream 能在终端中清楚渲染完整任务过程。
- 渲染代码和未来 Agent Core 逻辑分离。

### Stage 1：最小 Agent Loop

目标：证明一次真实的模型-工具-观察循环能闭合。

能力：

- 使用 Python 实现 Agent Core。
- 第一版只接 Gemini。
- 支持四个工具：
  - `read_file`
  - `search_files`
  - `apply_patch`
  - `run_command`
- 使用一个 toy project 触发失败测试。
- Agent 自己读取文件、定位问题、应用补丁、运行验证。

验收：

- 至少发生一次工具调用。
- 至少发生一次文件补丁。
- 验证命令被执行。
- 验证命令 exit code 为 `0`。
- transcript 记录完整循环。

### Stage 2：安全执行边界

目标：把“模型想做”和“本地允许运行”分开。

能力：

- 所有路径限制在 cwd 内。
- `read_file` 和 `search_files` 默认允许。
- `apply_patch` 只允许修改 cwd 内文件。
- `run_command` 默认只允许验证命令和明确只读命令。
- 删除、移动、递归破坏性命令直接拒绝。

验收：

- 越界路径被拒绝。
- 危险命令被拒绝。
- 工具失败会作为 observation 返回给模型。

### Stage 3：上下文系统

目标：让 Agent 通过增量读取上下文工作，而不是一次性塞满 prompt。

能力：

- 启动时读取项目规则文件：
  - `AGENTS.md`
  - `CLAUDE.md`
  - `README.md`
- 记录当前 cwd、平台、日期、可用工具。
- 搜索优先，按需读取文件。
- 工具输出有长度限制。
- 长输出先摘要或截断。

验收：

- 面对小型真实 repo 时，Agent 能先搜索定位相关文件。
- 不扫描或读取整个仓库。
- 最终回答能说明关键上下文来源。

### Stage 4：验证驱动修复

目标：把验证结果作为下一轮推理输入。

能力：

- 用户可传入验证命令。
- 修改后自动运行验证命令。
- 验证失败时，把 exit code、stdout、stderr 摘要写回 messages。
- 模型根据失败结果继续修复。

验收：

- 至少能处理一次“修改后验证失败 -> 二次修复 -> 验证通过”的循环。
- 最终回答必须包含实际运行的验证命令和结果。

### Stage 5：开发工作流能力

目标：在核心循环稳定后，补少量真正影响开发体验的功能。

候选能力：

- `/plan`
- `/diff`
- `/verify`
- `/resume`
- git diff 摘要
- transcript 持久化
- 任务中断和恢复

验收：

- 每个命令都对应真实开发需求。
- 没有重复造 Claude Code 的表层功能。
- 新能力不破坏 Agent Core 和 UI 分层。

## 推荐实现顺序

1. 先实现 Stage 0 的 mock transcript。
2. 再实现 Stage 1 的最小 loop。
3. Stage 1 跑通 toy project 后，再补安全边界。
4. 安全边界稳定后，再让它处理小型真实仓库。
5. 只有当真实任务反复需要时，才增加命令、memory、MCP 或插件能力。

## 设计原则

- 先闭环，再扩展。
- 先观察，再抽象。
- 先固定 toy project，再碰真实项目。
- 工具必须返回结构化结果。
- 写操作必须可审计。
- 验证失败不是结束，而是下一轮 observation。
- UI 只能渲染事件，不能拥有 Agent 决策逻辑。

## 当前下一步

推荐从 Stage 0 开始：

```text
实现一个 Python mock event stream
-> 用 Rich 渲染 transcript
-> 确认事件结构
-> 再接入真实 Agent Core
```

在本学习项目中，任何文件修改都应保持最小步长，并在写入前确认范围。
