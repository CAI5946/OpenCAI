# Workflow Spec and Script are the main workflow expression

OpenCAI Workflow keeps a stable development-flow backbone, but the runtime must preserve enough autonomy for the planner to adapt a workflow to the current task. We therefore treat `WorkflowSpec + WorkflowScript` as the main expression: `WorkflowSpec` is the auditable contract, `WorkflowScript` is the constrained orchestration expression, and `WorkflowTemplate` is only one source for producing them. The runner must validate and execute this pair rather than blindly running arbitrary model-generated control flow.
