# WorkflowScript branches on structured state

`WorkflowScript` branch, retry, and stop decisions must be based on structured workflow state such as task status, phase status, verification status, blocking review findings, retry count, or humancheck decisions. It must not branch on natural-language impressions such as whether an answer feels incomplete. If quality judgment is needed, a review task should produce structured findings first, and the script can branch on those findings.
