# Learning Mode

本项目采用学习型开发模式：先建立组件理解，再做最小实现。

## 目标

- 理解 CLI Coding Agent 的核心组件和边界。
- 每次只聚焦一个组件，例如 Runtime、Event / Transcript、Tool Model、LLM Adapter、Renderer / TUI。
- 代码实现服务理解，不以快速补齐完整原型为第一目标。
- Phase 7 起以 OpenCAI 自身 CLI 能力为主线推进；Phase 9 起每个 Phase 开始前加入轻量 Reference Pass，只参考公开资料、成熟工程惯例、项目内已有实现和本地 reference-only 开源仓库。

## 固定流程

### Phase 启动评估

每个新 Phase 开始前先做 3-5 分钟评估，不写代码，只确认这轮工作有多重。

评估内容：

1. 目标：本阶段要学会什么、做出什么。
2. 范围：涉及哪些模块或文件。
3. 难度：低 / 中 / 高。
4. 预计用时：
   - 讲解 + 提问。
   - 参考资料核对。
   - 最小实现。
   - 验证 + 收口。
5. 是否适合一个对话完成。
6. 本对话只做到哪里算成功。

如果预计超过 2 小时，先拆成多个 Slice，不强行一个对话完成整个 Phase。

### Reference Pass

Phase 9 起，每个 Phase 在实现前先做一次轻量 Reference Pass。

Reference Pass 只回答当前 Phase 的一个具体问题，例如：

- Phase 9：别人如何实现文件搜索工具和 tool result。
- Phase 10：真实模型调用工具后，message / observation 如何组织。
- Phase 11：写文件和运行命令前如何做权限控制。
- Phase 12：CLI 参数、配置和 help 文档如何设计。
- Phase 13+：workflow runtime 如何与 agent loop 分层。

规则：

1. 每次只看 1-2 个相关开源项目或项目内模块。
2. 不泛读整个仓库，不因参考资料扩大本 Phase 范围。
3. 不复制源码，只抽象设计原则和取舍。
4. Reference notes 只保留：`问题 -> 参考项目做法 -> OpenCAI 采用什么 -> OpenCAI 暂不采用什么`。
5. 创建或修改新 reference notes 文件前，先确认目标文件；优先更新已有文档。

### 执行步骤

1. 说明当前组件解决什么问题。
2. 定义输入、输出、状态、失败情况和职责边界。
3. 做 Reference Pass，除非本阶段是极小局部修改或用户明确要求跳过。
4. 记录可复用原则、OpenCAI 采用项和暂不采用项。
5. 提 2-4 个检查问题，确认用户是否理解。
6. 根据用户回答纠正误区。
7. 用户确认后，再设计最小接口。
8. 写文件前确认范围。
9. 每次只实现一个最小可观察点。
10. 运行最小验证。
11. 复盘这个组件负责什么、不负责什么、下一个组件依赖什么。
12. 阶段完成或路线变化时，更新 `docs/status.md` 或学习日志。

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
- 不复制闭源、未授权或来源不明实现。
- 本地 `codex/`、`claude-code/` 等外部源码目录只作为 reference-only，不进入 OpenCAI 源码或 git 追踪范围。
- Renderer / TUI 只负责展示，不承载 Agent 决策逻辑。
- Runtime、Tool Model、LLM Adapter、Event / Transcript 的边界先讲清楚，再实现。
