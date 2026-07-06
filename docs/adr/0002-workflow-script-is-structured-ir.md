# WorkflowScript is structured IR, not a general script language

OpenCAI needs planner autonomy without turning Workflow into a general automation runtime. `WorkflowScript` is therefore a structured, schema-validated IR with a small set of allowed operations such as running phases, branching on status, retrying, humancheck, handoff, and stop. It is not Python, JavaScript, shell, or any unrestricted code form, so the runner can preview, validate, audit, save, and replay it safely.
