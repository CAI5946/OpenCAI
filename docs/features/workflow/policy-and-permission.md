# Workflow Policy and Permission

## 目标

Workflow policy 用来约束每个 phase / task 能使用哪些工具、能执行哪些动作，以及失败后如何处理。它不替代 Runtime permission profile，也不绕过 SafetyPolicy。

## 合并规则

```text
effective_tool_policy =
  global permission profile
  + mode profile
  + workflow phase policy
  + workflow task policy
  + skill allowed-tools
  + subagent role policy
```

最终裁决仍由 Runtime / SafetyPolicy 负责。

## Phase Policy

常见默认策略：

- `clarify`：只读，必要时 ask user。
- `plan`：只读，允许 search / read / update_plan。
- `execute`：可写，但必须受 permission profile 和 path safety 限制。
- `review`：默认只读，不直接修改文件。
- `verify`：允许运行验证命令，记录 command、exit code 和 concise output。
- `handoff`：默认只读，要求汇总结果、验证和风险。

## Task Policy

每个 task 可以进一步收窄 phase policy：

- tool allowlist。
- command allowlist / timeout / cwd。
- write scope。
- required verification。
- retry budget。
- optional / required 标记。

Task policy 只能收窄或显式请求权限，不能自动提升 Runtime permission profile。

## Humancheck

需要 humancheck 的情况：

- 权限升级。
- 高风险写操作。
- 删除 / 移动 / 大范围修改。
- verification 多次失败。
- planner 需要修改剩余 workflow。
- 用户目标发生变化。

Humancheck 是 runtime control point，不是普通 prompt 文案。
