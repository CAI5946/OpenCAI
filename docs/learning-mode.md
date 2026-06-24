# Learning Mode

本项目采用学习型开发模式：先建立组件理解，再做最小实现。

## 目标

- 理解 Claude Code 类 Coding Agent 的核心组件和边界。
- 每次只聚焦一个组件，例如 Runtime、Event / Transcript、Tool Model、LLM Adapter、Renderer / TUI。
- 代码实现服务理解，不以快速补齐完整原型为第一目标。

## 固定流程

1. 说明当前组件解决什么问题。
2. 定义输入、输出、状态、失败情况和职责边界。
3. 提 2-4 个检查问题，确认用户是否理解。
4. 根据用户回答纠正误区。
5. 用户确认后，再设计最小接口。
6. 写文件前确认范围。
7. 每次只实现一个最小可观察点。
8. 运行最小验证。
9. 复盘这个组件负责什么、不负责什么、下一个组件依赖什么。
10. 阶段完成或路线变化时，更新 `docs/status.md` 或学习日志。

## Phase 收口模板

每个 Phase 完成前检查并处理：

1. 更新 `docs/status.md`
   - 当前阶段。
   - 已完成内容。
   - 下一步。
   - 阻塞/待确认。
   - 最近验证。

2. 更新学习日志
   - 组件边界。
   - 最小接口或产物。
   - 纠正过的关键误区。
   - 验证证据。
   - 下一阶段。

3. 记录验证命令
   - 命令原文。
   - exit code。
   - 关键输出或观察结果。
   - 不要声称未运行的测试已通过。

4. 创建 git checkpoint
   - 如有文件改动且阶段完成，提交一次小 commit。
   - commit message 聚焦本 Phase 产物。
   - 如果不提交，说明原因。

5. 最终交接
   - Owns。
   - Does not own。
   - Verified。
   - Next depends on。
   - Open risk。

## 新对话启动方式

在新对话中可以直接说：

```text
读取 AGENTS.md 和 docs/learning-mode.md，按学习型开发模式继续 Phase X。
```

如果可用，也可以显式调用用户级 skill：

```text
Use $learn-with-dev to teach and implement the next component in small verified steps.
```

## 实现约束

- 不连续补齐多个组件。
- 不主动添加复杂 UI、MCP、插件、多 Agent、长期 memory。
- 不复制 `claude-code/` 的闭源或来源不明实现。
- Renderer / TUI 只负责展示，不承载 Agent 决策逻辑。
- Runtime、Tool Model、LLM Adapter、Event / Transcript 的边界先讲清楚，再实现。
