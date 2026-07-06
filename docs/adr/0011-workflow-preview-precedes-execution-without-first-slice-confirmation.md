# Workflow preview precedes execution without first-slice confirmation

The first `WorkflowSpec + WorkflowScript` implementation should keep a human-readable preview before execution but should not require an execute/cancel confirmation gate yet. `/workflow TASK` can compile the spec and script, render the preview, and execute immediately. This preserves the future entry point for confirmation, modification, and humancheck while keeping the first implementation slice focused on the execution model.
