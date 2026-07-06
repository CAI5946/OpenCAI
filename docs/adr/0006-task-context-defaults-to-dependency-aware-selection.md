# Task context defaults to dependency-aware selection

Workflow dynamic context should not default to injecting all previous task results. `TaskContextComposer` should include direct dependency context with useful detail, compress transitive dependency context, and omit unrelated task context unless the planner explicitly requests it and runner rules allow it. Failed dependencies, verification evidence, review findings, artifacts, errors, and retry history remain injectable context blocks, but their inclusion must be purpose-aware and budgeted.
