# Skills

## Feature 目标

Skills 负责把本地可复用的 agent 能力包接入 OpenCAI。它不是普通工具数量扩展，也不是 MCP/plugin 的同义词，而是一层面向规则、模板、脚本、资产和 workflow 经验复用的本地能力系统。

目标是让 OpenCAI 支持成熟 Coding Agent 常见的 skill 工作流：

- 用户可以通过 `$skill args` 显式调用 skill。
- 模型可以在看到 `<available_skills>` 后主动调用 skill。
- skill 的完整 `SKILL.md` 只在需要时加载，而不是常驻塞进初始上下文。
- skill 加载后通过结构化 message / context delta 进入后续 LLM 调用。
- TUI 只展示调用摘要，不把完整 skill prompt 刷到过程视图。
- 后续可扩展到 frontmatter、allowed tools、模板、脚本、资产、权限、审计、workflow 和 subagent。

## 参考设计映射

### Claude 参考点

本地 Claude Code 的关键设计不是“slash command 直接执行 skill”，而是：

- skill 列表和 skill 全文加载分离。
- 显式调用先转成“请模型调用 Skill tool”的提示。
- Skill tool 读取 skill 指令后，把 skill prompt 作为新的 user/meta message 注入上下文。
- 后续流程继续走普通 model -> tool call -> observation -> model loop。
- 已调用 skill 会进入状态，供压缩、恢复和后续上下文管理使用。

OpenCAI 的 `$skill` 采用同一类语义：显式入口只请求模型调用 `invoke_skill`，实际加载和 message 注入由 skill tool 完成。

### OpenCAI 本地落点

当前 OpenCAI 的 Skill flow：

```text
user input: $skill args
-> Composer 解析 SkillInvocationInput
-> Runtime 组合 task + skill_invocation_request
-> LLM 看到请求后调用 invoke_skill
-> invoke_skill 读取 SKILL.md
-> Agent Loop 追加 tool observation 和 invoked_skill meta user message
-> 下一轮 LLM 使用 skill 指令继续完成 task
-> TUI / SessionContext 只记录摘要
```

## 概念边界

- Tool：模型可调用的真实动作接口。`invoke_skill` 是 tool。
- Skill：本地能力包，入口通常是 `SKILL.md`，可附带模板、脚本、资产和参考资料。
- MCP：外部工具协议和资源读取边界。
- Plugin：能力分发和动态安装边界，可包含 skills、MCP servers 或 apps。
- Workflow：多阶段编排边界，可选择在哪个 phase 暴露或要求使用哪些 skills。

`invoke_skill` 的语义是加载 skill 指令并注入 messages / context，不等同于直接执行任意脚本。未来如果支持脚本或模板执行，应通过单独的权限、审计和 output contract 建模。

## 目标能力

1. Skill Registry
   - 统一发现 project skill roots、global skill roots 和后续 plugin-provided skills。
   - 负责去重、排序、metadata 解析、source 标记和可见性策略。

2. Discovery / Suggestion
   - `<available_skills>` 只注入 name 和 description 等摘要。
   - TUI `$` suggestion 使用同一 registry，避免 composer 和 context discovery 分叉。
   - 后续可接入 deferred discovery / `tool_search`。

3. Explicit Invocation
   - `$skill args` 是显式用户意图。
   - Runtime 注入 `skill_invocation_request`，要求模型先调用 `invoke_skill`。
   - 后续应增加更强的 gate，避免模型忽略显式调用请求。

4. Model-invoked Skill
   - 模型也可以根据 `<available_skills>` 主动调用 `invoke_skill`。
   - 主动调用应和显式调用复用同一 tool path。

5. Skill Message Injection
   - `invoke_skill` 返回 `invoked_skill` meta user message。
   - Agent Loop 将该 message 加入后续 LLM messages。
   - Transcript / TUI 不展示完整 skill prompt，只展示摘要。

6. Context Budget / Truncation
   - Skill 全文、引用文件和模板都需要预算。
   - 超预算要有截断标记、debug visibility 和可复现的摘要策略。

7. Frontmatter / Metadata
   - 后续支持 `description`、`allowed-tools`、`when_to_use`、`userInvocable`、`context`、`model/effort` 等字段。
   - metadata 只影响 discovery、权限、context 和 tool exposure，不应绕过 SafetyPolicy。

8. Permissions / Allowed Tools
   - skill 可以建议或限制工具集，但最终执行仍由 Runtime / SafetyPolicy 决定。
   - `allowed-tools` 应和 mode、workflow phase、permission profile 合并计算。

9. Templates / Scripts / Assets
   - `SKILL.md` 可以引用相对路径下的模板、脚本或资产。
   - 读取和执行必须分开建模；读取是 context 能力，执行是权限敏感动作。

10. Session / Compaction / Replay
   - 已调用 skill 的 name、source、path、description、content hash 和注入摘要应进入 session state。
   - save/replay 和 compaction 需要能恢复“这个 skill 已被调用过”的事实。

11. Workflow / Subagent Integration
   - Workflow phase 可以要求或推荐特定 skills。
   - Subagent 可以继承或收窄可用 skills。
   - 并发 agent 不应共享可变 skill execution 状态，除非有明确审计和锁。

## 当前实现

已完成 V1 闭环：

- `OpenCAI/composer.py`
  - 支持 `$skill args` 解析为 `SkillInvocationInput`。
  - 支持 `$` skill suggestion。
  - 当前 suggestion 默认扫描 `<cwd>/.opencai/skills` 和 `~/AgentSkills`。

- `OpenCAI/context.py`
  - 注入 `<available_skills>` 摘要。
  - 支持 `skill_invocation_request` message，显式 `$skill` 时要求模型先调用 `invoke_skill`。

- `OpenCAI/tools.py`
  - 已注册 `list_skills`、`read_skill`、`invoke_skill`。
  - `invoke_skill` 从 project `.opencai/skills` 和 `~/AgentSkills` 读取 `SKILL.md`。
  - 返回 `invoked_skill` meta user message。

- `OpenCAI/agent_loop.py`
  - 对 `invoke_skill` 的 tool result 做摘要化 observation。
  - 成功后追加 `invoked_skill` message 到后续模型上下文。
  - event payload 不携带完整 `SKILL.md`，避免过程视图泄漏大段 prompt。

- `OpenCAI/tui.py`
  - `invoke_skill` 结果渲染为 `Skill invoked` 摘要。
  - live process / process view 只显示 skill name、ok、path 等调试摘要。

- `OpenCAI/session_context.py`
  - `SessionTurnSummary` 记录 invoked skill 摘要。

## 当前边界

- 显式 `$skill` 目前是 prompt-level enforcement；Runtime 还不会强制拦截“模型未调用 `invoke_skill` 就直接回答”的情况。
- Skill discovery 尚未抽成统一 `SkillRegistry`；composer suggestion、context summary、`list_skills/read_skill/invoke_skill` 的 roots 和 metadata 语义仍需合并。
- `list_skills/read_skill` 仍偏 workspace-local inspection；`invoke_skill` 已覆盖 project `.opencai/skills` 和 `~/AgentSkills` 的只读加载第一版。
- 没有 context budget、截断策略和 debug visibility。
- 没有完整 frontmatter schema。
- 没有 `allowed-tools`、hooks、脚本执行、模板展开或资产读取合同。
- 没有 skill-level permission model；当前仍完全依赖工具自身 read_only 和 SafetyPolicy。
- 没有 compaction / save / replay 的完整 skill state 恢复。
- 没有 workflow phase 或 subagent scoped skill exposure。

## 后续计划

优先顺序：

1. 抽出 `SkillRegistry`，统一 discovery、suggestion、summary、read 和 invoke 的 roots、去重、metadata 和 source。
2. 给 `invoke_skill` 增加 context budget、截断标记和 debug visibility。
3. 增加强 explicit invocation gate：当用户输入 `$skill` 时，如果模型未先调用 `invoke_skill`，Runtime 应能继续追问或触发失败。
4. 设计 skill frontmatter schema，先覆盖 `description`、`allowed-tools`、`when_to_use`、`userInvocable`。
5. 设计 skill allowed-tools 与 mode / workflow phase / permission profile 的合并规则。
6. 支持 skill 相对引用文件的按需读取，明确模板、脚本、资产的读取和执行边界。
7. 把 invoked skill state 纳入 compaction、save/replay 和 session debug output。
8. 将 Skill exposure 接入 WorkflowRunner 和未来 subagent role。

## 验证

当前已有测试覆盖：

- `$skill` parser 和 suggestion。
- `list_skills` / `read_skill` / `invoke_skill` 基础行为。
- `invoke_skill` meta message 注入。
- Agent Loop streaming 中的 skill observation 摘要。
- TUI 中的 skill 摘要渲染。
- SessionContext 中的 invoked skill 摘要。

文档维护规则：

- Skill 的功能设计、边界和路线维护在本文档。
- `docs/features/Tools.md` 只保留 Skill 作为工具系统分类的一行概览和跳转。
