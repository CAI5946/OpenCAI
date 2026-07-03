# Plan: Workflow Development Process

## 目的

本文定义 OpenCAI Workflow feature 的开发流程。它回答“下一刀怎么选、怎么实现、怎么验证、怎么收口”，不重复完整架构设计。

架构入口看 `docs/features/Workflow Overview.md`；详细设计草稿看 `docs/features/Workflow.md`；当前真实进度看 `docs/status.md`。

## 基本原则

- Workflow 是 runtime control plane，不进入 `agent_loop.py`。
- Agent Loop 继续负责单 task 的 `model -> tool_call -> observation -> model`。
- Tool Model + SafetyPolicy 继续负责真实动作和权限裁决。
- 每个切片必须小、可运行、可测试、可回滚。
- 每个切片只推进一个主要能力，不顺手补无关大功能。
- 设计时面向成熟 workflow runtime，但实现时只落当前可验证边界。
- 文档、测试和 smoke 要跟实现一起收口。

## 单个切片流程

每个 Workflow 切片按下面顺序推进：

```text
1. 选择切片
2. 确认边界
3. 检查现状
4. 设计最小接口
5. 实现代码
6. 增加或更新测试
7. 运行验证
8. 更新 docs/status.md
9. 记录后续风险
10. 需要时创建 git checkpoint
```

### 1. 选择切片

切片必须来自当前路线或明确的新决策。

当前推荐顺序：

1. `/workflow` execute / cancel confirmation gate。
2. 拆出 `workflow_commands.py`。
3. 引入 `WorkflowTask` / `TaskResult`。
4. 引入 task dependency graph，先串行执行，预留 read-only 并行。
5. 实现 dependency-aware `TaskContextComposer`。
6. 实现 `PhaseResult` 聚合多个 `TaskResult`。
7. 接入 task / phase scoped tool policy。
8. 实现 review / verify retry loop。
9. 设计 WorkflowRun state store 和 save / replay。
10. 设计受限 WorkflowScript runtime。

不要在一个切片里同时做 task graph、context composer、retry loop 和 save/replay。

### 2. 确认边界

开始实现前先明确：

- 本切片的用户可见行为是什么。
- 会改哪些模块。
- 不会改哪些模块。
- 成功条件是什么。
- 失败时如何表达。
- 需要哪些测试和 smoke。

边界模板：

```text
目标：
范围：
非目标：
输入：
输出：
状态变化：
失败路径：
验证方式：
```

### 3. 检查现状

实现前至少读取：

- `docs/status.md`
- `docs/features/Workflow Overview.md`
- 相关实现文件，例如 `OpenCAI/workflow.py`、`OpenCAI/runtime_commands.py`
- 相关测试，例如 `tests/test_workflow.py`、`tests/test_runtime_commands.py`

如果涉及 context，还要读取：

- `docs/features/Context Engineering.md`
- `OpenCAI/context.py`

如果涉及 tools / permission，还要读取：

- `docs/features/Tools.md`
- `OpenCAI/tooling/`
- `OpenCAI/safety.py`

### 4. 设计最小接口

优先扩展已有接口，不提前引入大框架。

接口设计要求：

- 能服务当前切片。
- 不堵死 task-first / phase-as-group 方向。
- 不让 WorkflowRunner 直接执行工具。
- 不让 runtime command 逻辑继续无限堆进 `runtime_commands.py`。
- 不暴露未完成的用户承诺。

### 5. 实现代码

实现顺序：

1. 更新数据模型或 command flow。
2. 接入 runner / runtime。
3. 更新 renderer 或输出文案。
4. 保持旧路径兼容。
5. 删除本次改动造成的无用代码。

不要在 workflow 切片中顺手重构 Agent Loop、Tool Model、TUI 或 Context，除非该切片明确依赖。

### 6. 测试

测试优先级：

- workflow core model 和 runner 行为：`tests/test_workflow.py`
- runtime command 行为：`tests/test_runtime_commands.py`
- context 组合行为：`tests/test_context.py`、`tests/test_runtime_session.py`
- tool exposure / permission 行为：`tests/test_tool_taxonomy.py`、`tests/test_safety.py`

每个切片至少覆盖：

- 成功路径。
- 失败路径。
- 非目标路径不回归。

### 7. 验证

修改 Workflow 代码后优先运行：

```powershell
python -m py_compile OpenCAI\workflow.py OpenCAI\runtime_commands.py tests\test_workflow.py tests\test_runtime_commands.py
python -m unittest tests.test_workflow tests.test_runtime_commands
cmd /c "(echo /workflow Read README&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"
```

实现 confirmation gate 后增加：

```powershell
cmd /c "(echo /workflow Read README&echo execute&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"
cmd /c "(echo /workflow Read README&echo cancel&echo /exit)|python -m OpenCAI --adapter fake --max-steps 3"
```

只有 `python -m unittest discover tests` 通过后，才能说“全量测试通过”。

### 8. 更新状态

切片完成、下一步变化、阻塞变化或验证结果变化时，更新 `docs/status.md`。

`docs/status.md` 只写当前事实：

- 当前阶段 / 当前主线。
- 已完成能力。
- 正在做。
- 下一步。
- 阻塞 / 待确认。
- 最近验证。

不要把长设计和历史推理写进 `docs/status.md`。

### 9. 收口

每个切片收口时输出：

```text
完成了什么：
改了哪些文件：
验证了什么：
没有做什么：
下一步是什么：
风险是什么：
```

如果切片完成且用户要求 checkpoint，再做 scoped commit。

## 当前第一刀

当前最合理的第一刀是：

```text
/workflow execute / cancel confirmation gate
```

原因：

- 它直接修正当前 `/workflow TASK` 展示 plan 后立刻执行的问题。
- 它强化 workflow control plane 的用户确认边界。
- 它不需要先引入 task graph、context composer、retry loop 或 save/replay。
- 它能用小范围测试和非 TTY smoke 验证。

建议文件范围：

- `OpenCAI/runtime_commands.py`
- `tests/test_runtime_commands.py`
- 必要时复用 `OpenCAI/tui.py` 的选择组件

非目标：

- 不实现 `WorkflowTask` / `TaskResult`。
- 不做 Nodeflow bugfix workflow。
- 不做 retry loop。
- 不做 LLM-generated WorkflowSpec。
- 不做 multi-agent。

## 文档分工

- `docs/features/Workflow Overview.md`：稳定架构入口和主流程。
- `docs/features/Workflow.md`：详细设计草稿和展开讨论。
- `docs/plans/workflow-development-process.md`：Workflow 开发流程。
- `docs/status.md`：当前进度、阻塞、下一步和验证事实。
- `docs/phases/phase-13-dynamic-workflows.md`：Phase 13 历史设计和学习日志。
