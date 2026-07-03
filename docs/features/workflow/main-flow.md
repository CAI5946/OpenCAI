# Workflow Main Flow

## 主流程

```text
1. 用户显式输入 `/workflow TASK`。

2. Runtime command parser 识别 `/workflow`。
   - 进入 workflow command flow。
   - 不经过 `run_command`。

3. Workflow Intake 判断是否进入 workflow。
   - 当前显式 `/workflow` 直接进入。
   - 未来普通任务也可自动路由到 workflow。

4. Workflow Planner / Compiler 生成 workflow plan。
   - 选择内置模板，或未来生成 WorkflowScript。
   - 输出 WorkflowSpec manifest + WorkflowScript / 模板函数。

5. 展示 workflow plan。
   - 当前直接执行。
   - 后续通过统一 human decision / control point 支持 execute / cancel / modify。

6. WorkflowRunner 执行 workflow。
   - 读取 task graph。
   - 当前按 `spec.tasks` 串行执行。
   - 检查 task `depends_on`。
   - 为每个 task 注入 scoped prompt / context / tool policy。

7. 每个 task 启动 Agent Loop 或未来 subagent。
   - task 内部仍是 `model -> tool_call -> observation -> model`。
   - 工具调用继续走 Tool Model + SafetyPolicy。

8. PhaseResult 结构化保存。
   - 保存 final answer、error、stop reason、events、artifacts 和 verification。
   - 汇总后传给后续 phase。

9. review / verify 可触发 retry。
   - 失败回到 execute。
   - 受 `max_retries` 和 policy 限制。

10. 最终 phase 收口。
    - 推荐命名为 handoff。
    - 架构上应由 `final_phase_id` 指定，不硬编码只能叫 handoff。

11. WorkflowRun 生成 final answer。
    - 返回给用户。
    - 同时保留 workflow process / state / replay 证据。
```
