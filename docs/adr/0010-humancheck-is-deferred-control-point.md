# Humancheck is a deferred runtime control point

Humancheck should be modeled as a future runtime control point for cases that genuinely require human judgment, such as permission escalation, high-risk operations, workflow revision, scope changes, repeated verification failure, blocking review findings, or budget overruns. The first implementation slice should not build the humancheck execution flow, but the workflow status, reason, spec, script, and policy model should leave room for `waiting_for_human` and `humancheck_required`.
