# WorkflowScript uses control-plane operations only

`WorkflowScript` must remain above the tool execution layer. It can express coarse control-plane operations such as running phases, branching, retrying, humancheck, handoff, and stop, but it cannot express tool-level operations such as reading files, editing files, running shell commands, or calling external tools directly. Those actions remain inside Agent Loop, Tool Model, and SafetyPolicy so workflow orchestration does not bypass existing safety and execution boundaries.
