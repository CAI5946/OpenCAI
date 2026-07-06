# TaskContextComposer uses planner requests and runner rules

The planner may declare a `Context Request` for each task, but it does not directly decide the final injected context. `TaskContextComposer`, under runner-owned rules, permissions, and context budget, decides which static and dynamic context blocks are included, omitted, or truncated. This preserves planner autonomy while keeping task context selection observable, testable, and bounded.
