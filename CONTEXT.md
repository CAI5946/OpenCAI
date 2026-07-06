# OpenCAI Domain Language

OpenCAI 的领域语言用于约束 Coding Agent runtime、workflow control plane 和开发流程语义，避免把流程、状态、工具执行和提示词混成一层。

## Language

**Workflow**:
面向 Coding Agent 开发任务的 runtime control layer，用于持有计划、状态、权限边界、验证证据、失败恢复和 handoff。
_Avoid_: generic workflow engine, arbitrary process engine

**Stable Development Flow**:
Workflow 的稳定流程骨架，默认 phase vocabulary 是 `clarify / plan / execute / review / verify / handoff`，允许跳过、条件回边、retry 和 humancheck。
_Avoid_: linear checklist, arbitrary DAG

**WorkflowSpec**:
一次 workflow run 的可审计合同，描述 phase、task、依赖、权限、最终收口和验证要求。
_Avoid_: full DSL, implementation script

**WorkflowScript**:
结构化受限 IR，用于在 `WorkflowSpec` 和 policy 约束内表达粗粒度 control-plane 操作，例如 run phase、branch、retry、humancheck、handoff 和 stop。它由固定 op 和字段组成，由 Runner 解释执行，不表达 read file、edit file 或 run command 等 tool-level 操作。
_Avoid_: unrestricted script, general-purpose automation, Python script, JavaScript script, tool script

**WorkflowTemplate**:
可复用的开发流程经验来源，用于帮助 Planner 生成 `WorkflowSpec` 和 `WorkflowScript`，但不是唯一主表达。
_Avoid_: only workflow representation

**WorkflowRunner**:
执行 workflow control plane 的 runtime 组件，负责校验并执行 `WorkflowSpec + WorkflowScript`，但不直接读写文件或绕过工具安全策略。
_Avoid_: tool executor, agent loop

**WorkflowRun**:
一次 workflow 执行的事实账本，保存 task events、tool calls、outputs、errors、artifacts、verification evidence、retry history 和 final handoff。它不是默认注入后续 task 的完整 prompt。
_Avoid_: prompt context

**Structured Workflow Condition**:
WorkflowScript 用于 branch、retry 和 stop 的可复现判断条件，只能基于 task status、phase status、verification status、review finding、retry count 或 humancheck decision 等结构化状态。
_Avoid_: natural-language quality guess

**Workflow Status**:
Workflow、phase 或 task 的少量通用执行状态，例如 pending、running、passed、failed、skipped、cancelled、blocked 和 waiting_for_human。
_Avoid_: failure-specific status

**Workflow Status Reason**:
解释 status 的结构化原因，例如 dependency_failed、policy_denied、humancheck_required、verification_failed、review_blocking_findings、max_retries_reached 或 user_cancelled。
_Avoid_: status

**Humancheck**:
后置预留的 runtime control point，用于在权限升级、高风险操作、workflow 修改、scope 变化或预算超限等真实需要人决策时暂停 workflow。第一版不实现 humancheck 执行流。
_Avoid_: model uncertainty prompt, first-version requirement

**Workflow Preview**:
执行 workflow 前展示 `WorkflowSpec + WorkflowScript` 的人类可读预览，用于理解即将运行的 phase、task、依赖、policy 和控制流。第一版保留 preview 但不强制等待用户确认。
_Avoid_: mandatory first-version confirmation gate

**WorkflowTask**:
Workflow 的真实调度单位，属于某个 phase，并通过依赖关系表达执行顺序、并行可能性和失败传播。
_Avoid_: phase step

**Task Message**:
单个 `WorkflowTask` 启动 Agent Loop 时接收的输入包，由 static task context、dynamic task context、task instruction、policy 和 acceptance criteria 组成。
_Avoid_: raw prompt

**Static Task Context**:
Planner 在 workflow 编译时为 task 分配的上下文，例如用户原始任务、repo 摘要、AGENTS 规则、task 目标、权限和验收要求。
_Avoid_: runtime result

**Dynamic Task Context**:
Workflow 运行过程中产生并注入 task message 的上下文，例如 dependency task result、phase summary、artifacts、verification output、review finding、error、retry history 和 humancheck decision。
_Avoid_: startup context

**Direct Dependency Context**:
来自当前 task 直接依赖 task 的动态上下文，默认以较详细摘要注入 task message。
_Avoid_: all previous context

**Transitive Dependency Context**:
来自当前 task 间接依赖 task 的动态上下文，默认只以压缩摘要注入 task message。
_Avoid_: full dependency transcript

**TaskContextComposer**:
Runner 在启动每个 Agent Loop 前调用的 context composition 组件，负责把 static task context 和 dynamic task context 合成为可观察、可审计、可复现的 task message。
_Avoid_: planner, agent loop

**Context Request**:
Planner 为 task 声明的上下文需求，例如需要 direct dependencies、changed files、verification evidence 或 review findings。它是请求，不是最终注入决定。
_Avoid_: context injection decision

**Task Kind**:
描述 task 的具体动作类型，例如 inspect、edit、test、summarize；它不是 phase。
_Avoid_: phase
