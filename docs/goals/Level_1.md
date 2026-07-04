# Goal: Small-Task Coding Agent Competence

## 目标

让 OpenCAI 在小型真实开发任务上接近主流 Coding Agent 的基础执行效果：读上下文、定位问题、改文件、运行验证、根据失败继续迭代，并留下可审计结果。

这个目标是产品验收目标，不是单一 feature。Workflow、Tool Model、Agent Loop Strategy、Modes 和后续 Multi-agent 都只作为提高通过率的手段。

## 评测分层

### Level 1: Local Micro Tasks

本地小任务，专门测试 OpenCAI 自身闭环。

- bugfix：先复现失败测试，再最小修改并重跑测试。
- CLI feature：给已有小 CLI 增加一个参数并保持旧行为。
- docs-code sync：根据文档修正代码默认行为，并运行检查脚本。

Level 1 当前分两层：

- Level 1A smoke baseline：10 个微型回归任务，用于确认基础 coding loop、验证命令、changed-files policy 和报告链路没有退化。
- Level 1B diagnostic tasks：5 个更有区分度的微型任务，用于暴露自然指令理解、多文件 patch、嵌套上下文定位和新建文件能力缺口。

当前入口：

```powershell
python -m benchmarks.runner --task all
```

默认使用 `fake` adapter，因此当前 baseline 预期不会通过这些任务；它的价值是验证 harness、报告和失败分类路径。真实能力评测使用：

```powershell
python -m benchmarks.runner --task all --adapter gemini
```

### Level 2: Aider-style Editing Tasks

借鉴 Aider polyglot / Exercism 风格任务，重点测试代码编辑、测试失败后修正和跨语言基础能力。

进入条件：Level 1 至少能稳定跑完并生成报告，且任务失败原因可以归类。

### Level 3: SWE-bench Lite Subset

接入真实 repo issue 修复任务。先选择 5 个 SWE-bench Lite 小子集，不直接上完整 Verified。

进入条件：Level 1/2 的 runner、workspace 隔离、验证结果和 changed files 报告稳定。

## 当前切片

当前 Level 1 已完成：

- `BenchmarkTask` JSON contract。
- `benchmarks.runner`。
- 15 个本地 micro task fixture。
- 初始验证、最终验证、strict changed-files policy 和 JSON result report。

## 评分

- `passed`：初始验证失败，OpenCAI 进程退出码为 0，最终验证命令退出码为 0，且改动文件精确匹配 `expected_changed_files`。
- `invalid_task`：初始验证已经通过，说明 fixture 没有暴露待修问题。
- `failed_agent`：OpenCAI 进程失败。
- `failed_verification`：Agent 运行结束后最终验证仍失败。
- `failed_changed_files`：最终验证通过，但实际改动文件不符合 task contract。

后续再扩展 `partial`，例如验证失败但 diff 方向正确、或任务完成但未运行推荐验证命令。

## 后续开发顺序

1. 跑当前 baseline，记录失败原因。
2. 若失败集中在未先验证，优先做 debug / verify-first workflow。
3. 若失败集中在无法正确 patch，优先增强 `apply_patch`。
4. 若失败集中在定位上下文，优先增强 `search_files` 和 task prompt composition。
5. 若失败集中在验证失败后停止，优先做 workflow retry loop。
6. 只有当失败分析证明需要 planner/reviewer 时，再引入 Multi-agent。
