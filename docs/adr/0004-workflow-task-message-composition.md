# WorkflowTask execution is driven by composed task messages

Each `WorkflowTask` starts one Agent Loop execution. The concrete behavior inside that loop is primarily shaped by the task message it receives, not by tool-level workflow scripting. The planner provides static task context, the workflow run provides dynamic context from prior results and runtime events, and `TaskContextComposer` combines them with the task instruction, policy, and acceptance criteria before the runner starts the Agent Loop.
