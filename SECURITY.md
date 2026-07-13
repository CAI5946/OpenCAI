# Security Policy

OpenCAI is an Alpha-stage local CLI Coding Agent prototype. It can read files,
run commands, and modify a workspace according to the active permission
profile. Do not use it on sensitive repositories without reviewing the tool
and permission configuration first.

## Supported versions

Security fixes are provided on a best-effort basis for the current `main`
branch. No stable release or support SLA is available yet.

## Reporting a vulnerability

Use GitHub private vulnerability reporting from the repository's **Security**
tab. Do not publish credentials, private repository contents, or a working
exploit in a public issue.

Useful reports include:

- a minimal reproduction;
- the active permission profile and operating system;
- the expected and actual security boundary;
- whether the issue bypasses `SafetyPolicy`, workspace scope, or user
  confirmation;
- suggested mitigations, if known.

Expected behavior under an explicitly selected permissive profile is not by
itself a vulnerability. Permission bypasses, secret exposure, and operations
outside the declared workspace are in scope.
