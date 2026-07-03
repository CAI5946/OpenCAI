from __future__ import annotations

from OpenCAI.workflow import WorkflowSpec, build_inspect_handoff_workflow


def compile_workflow(task: str) -> WorkflowSpec:
    return build_inspect_handoff_workflow()
