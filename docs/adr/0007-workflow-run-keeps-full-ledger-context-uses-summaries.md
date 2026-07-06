# WorkflowRun keeps the full ledger while task context uses summaries

`WorkflowRun` should preserve the full execution ledger for audit, debugging, process views, and future replay, including task events, tool calls, outputs, errors, artifacts, verification evidence, retry history, and final handoff. `TaskContextComposer` should not inject the full ledger into later tasks by default; it should select concise summaries and evidence blocks according to dependency, purpose, policy, and budget.
