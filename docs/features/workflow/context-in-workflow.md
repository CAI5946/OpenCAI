# Context in Workflow

```text
Workflow request
  -> Planner Context
     - original user task
     - workflow templates / phase ontology
     - available capabilities
     - policy constraints
     - output: WorkflowSpec / WorkflowScript

Workflow execution
  -> Task Context per WorkflowTask
     - base project/global/runtime context
     - workflow brief
     - phase contract
     - current task assignment
     - dependency result summaries only
     - relevant artifacts / files / risks
     - tool policy / permission scope
     - output contract
```
