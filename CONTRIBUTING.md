# Contributing to OpenCAI

OpenCAI is an Alpha-stage CLI Coding Agent prototype. Contributions should
preserve its observable permission, context, workflow, and verification
boundaries.

## Development setup

Requirements:

- Python 3.10 or newer;
- Git;
- no API key for the default `fake/fake` path.

```powershell
python -m pip install -r OpenCAI\requirements.txt
python -m OpenCAI --version
python -m unittest discover tests
```

## Contribution rules

- Keep changes small, scoped, and covered by relevant tests.
- Do not bypass `SafetyPolicy` or make a permissive profile the default.
- Do not commit `.env`, `.opencai/models.json`, local Agent configuration,
  credentials, benchmark runs, or generated outputs.
- Do not copy source code without a compatible redistribution license.
- Keep README, status, and feature documentation aligned with implemented
  behavior; planned features must not be presented as complete.
- New workflow control belongs under `OpenCAI/workflow/`, not in
  `agent_loop.py`.

Before opening a pull request, run:

```powershell
python -m unittest discover tests
python -m OpenCAI --help
python -m OpenCAI --dry-run --task "Read README"
```

By contributing, you agree that your contribution is licensed under the MIT
License included in this repository.
