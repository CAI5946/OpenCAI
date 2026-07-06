# Workflow status uses generic status plus structured reason

Workflow task, phase, and run state should keep a small generic status set such as pending, running, passed, failed, skipped, cancelled, blocked, and waiting_for_human. Specific causes belong in a structured status reason, not in separate status values. This keeps the state machine small while still letting scripts, renderers, and replay logic branch on dependency failures, policy denials, humancheck requirements, verification failures, blocking review findings, retry exhaustion, or user cancellation.
