"""Session-start context collection for OpenCAI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from OpenCAI.composer import SkillInvocationInput
from OpenCAI.llm_adapter import Message
from OpenCAI.session_context import SessionContext


DEFAULT_MAX_INSTRUCTION_CHARS = 12000
DEFAULT_MAX_SKILLS = 50
DEFAULT_MAX_SKILL_DESCRIPTION_CHARS = 180

OPENCAI_SYSTEM_PROMPT = """You are OpenCAI, a CLI coding agent for real software work.

Identity and mission:
- Help the user understand, edit, verify, and iterate on local projects.
- Prefer correct, observable progress over broad claims.
- Keep the current repository's rules and facts central to every action.

Instruction priority:
- Follow this system prompt first.
- Then follow project instructions.
- Then follow global instructions.
- Then use environment context.
- Then execute the current user task.
- If instructions conflict, prefer the higher-priority instruction and mention the conflict when it affects the work.

Task execution:
- Read the necessary context before changing files.
- Keep changes scoped to the requested outcome and the surrounding code.
- Preserve user changes you did not make.
- Do not invent results, tests, files, commands, or external state.
- If the task is unclear and a wrong assumption would be risky, ask one concise question.
- If the user explicitly invokes a skill with $skill, call invoke_skill with that skill before answering or taking task actions.
- You may call invoke_skill yourself only for skills listed in available_skills. Do not guess skill names.

Tool and file behavior:
- Use tools to inspect files, edit code, run commands, and verify outcomes.
- Treat tool outputs as current project facts.
- Do not claim a file was changed unless it was actually written.
- Do not run destructive actions unless the user explicitly requested them.

Verification:
- After code or configuration changes, run the smallest meaningful verification available.
- Report verification commands and whether they passed or failed.
- If verification cannot be run, say why and state the residual risk.

Communication:
- Match the user's language.
- Be concise, factual, and action-oriented.
- Lead with the result, then the important evidence or next step.
"""


@dataclass(frozen=True)
class ContextFileRef:
    path: Path
    exists: bool


@dataclass(frozen=True)
class InstructionFile:
    path: Path
    exists: bool
    content: str
    truncated: bool = False
    warning: str | None = None


@dataclass(frozen=True)
class RuntimeContext:
    adapter_name: str
    permission_profile: str
    max_steps: int


@dataclass(frozen=True)
class GitContext:
    branch: str | None
    dirty: bool
    short_status: str
    warning: str | None = None


@dataclass(frozen=True)
class SkillSummary:
    name: str
    description: str
    truncated: bool = False


@dataclass(frozen=True)
class SkillsContext:
    summaries: tuple[SkillSummary, ...]
    total_count: int
    truncated: bool = False


@dataclass(frozen=True)
class ContextSnapshot:
    cwd: Path
    repo_root: Path
    global_agents: ContextFileRef
    project_agents: ContextFileRef
    global_instructions: InstructionFile
    project_instructions: InstructionFile
    readme: ContextFileRef
    status_doc: ContextFileRef
    git: GitContext
    runtime: RuntimeContext
    skills: SkillsContext


@dataclass(frozen=True)
class ContextProvider:
    global_agents_path: Path | None = None
    user_skills_path: Path | None = None
    max_instruction_chars: int = DEFAULT_MAX_INSTRUCTION_CHARS
    max_skills: int = DEFAULT_MAX_SKILLS
    max_skill_description_chars: int = DEFAULT_MAX_SKILL_DESCRIPTION_CHARS

    def collect(
        self,
        *,
        cwd: Path,
        adapter_name: str,
        permission_profile: str,
        max_steps: int,
    ) -> ContextSnapshot:
        resolved_cwd = cwd.resolve()
        repo_root, repo_warning = _detect_repo_root(resolved_cwd)
        git = _collect_git_context(resolved_cwd, repo_warning)
        global_agents_path = self._global_agents_path()
        project_agents_path = repo_root / "AGENTS.md"
        skills = _collect_skills(
            repo_root,
            self._user_skills_path(),
            self.max_skills,
            self.max_skill_description_chars,
        )

        return ContextSnapshot(
            cwd=resolved_cwd,
            repo_root=repo_root,
            global_agents=_file_ref(global_agents_path),
            project_agents=_file_ref(project_agents_path),
            global_instructions=_read_instruction_file(
                global_agents_path,
                self.max_instruction_chars,
            ),
            project_instructions=_read_instruction_file(
                project_agents_path,
                self.max_instruction_chars,
            ),
            readme=_file_ref(repo_root / "README.md"),
            status_doc=_file_ref(repo_root / "docs" / "status.md"),
            git=git,
            runtime=RuntimeContext(
                adapter_name=adapter_name,
                permission_profile=permission_profile,
                max_steps=max_steps,
            ),
            skills=skills,
        )

    def _global_agents_path(self) -> Path:
        return self.global_agents_path or Path.home() / ".codex" / "AGENTS.md"

    def _user_skills_path(self) -> Path:
        return self.user_skills_path or Path.home() / "AgentSkills"


@dataclass(frozen=True)
class ContextComposer:
    system_prompt: str = OPENCAI_SYSTEM_PROMPT

    def compose(
        self,
        snapshot: ContextSnapshot,
        task: str,
        *,
        invoked_skill: SkillInvocationInput | None = None,
        session_context: SessionContext | None = None,
    ) -> list[Message]:
        messages: list[Message] = [
            {
                "role": "system",
                "kind": "system_prompt",
                "content": self.system_prompt.strip(),
            },
            {
                "role": "user",
                "kind": "project_instructions",
                "content": _format_instruction_context(
                    "project_instructions",
                    "Project instructions override global instructions.",
                    snapshot.project_instructions,
                ),
            },
            {
                "role": "user",
                "kind": "global_instructions",
                "content": _format_instruction_context(
                    "global_instructions",
                    "Global instructions apply only when they do not conflict with project instructions.",
                    snapshot.global_instructions,
                ),
            },
            {
                "role": "user",
                "kind": "available_skills",
                "content": _format_available_skills(snapshot.skills),
            },
        ]
        if invoked_skill is not None:
            messages.append(
                {
                    "role": "user",
                    "kind": "skill_invocation_request",
                    "content": _format_skill_invocation_request(invoked_skill),
                }
            )
        messages.append(
            {
                "role": "user",
                "kind": "environment_context",
                "content": _format_environment_context(snapshot),
            }
        )
        rendered_session_context = session_context.render() if session_context else ""
        if rendered_session_context:
            messages.append(
                {
                    "role": "user",
                    "kind": "session_context",
                    "content": rendered_session_context,
                }
            )
        messages.append({"role": "user", "kind": "user_task", "content": task})
        return messages


def _file_ref(path: Path) -> ContextFileRef:
    resolved = path.resolve()
    return ContextFileRef(path=resolved, exists=resolved.exists())


def _read_instruction_file(path: Path, max_chars: int) -> InstructionFile:
    resolved = path.resolve()
    if not resolved.exists():
        return InstructionFile(path=resolved, exists=False, content="")

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        return InstructionFile(
            path=resolved,
            exists=True,
            content="",
            warning=f"Could not read instruction file: {exc}",
        )

    if len(content) <= max_chars:
        return InstructionFile(path=resolved, exists=True, content=content)

    return InstructionFile(
        path=resolved,
        exists=True,
        content=content[:max_chars].rstrip(),
        truncated=True,
        warning=f"Instruction file truncated to {max_chars} characters.",
    )


def _collect_skills(
    repo_root: Path,
    user_skills_path: Path,
    max_skills: int,
    max_description_chars: int,
) -> SkillsContext:
    candidates = [
        repo_root / ".opencai" / "skills",
        user_skills_path,
    ]
    summaries: list[SkillSummary] = []

    for root in candidates:
        summaries.extend(_collect_skills_from_root(root, max_description_chars))

    summaries = _dedupe_skill_summaries(summaries)
    total_count = len(summaries)
    limited = tuple(summaries[:max_skills])
    return SkillsContext(
        summaries=limited,
        total_count=total_count,
        truncated=total_count > len(limited),
    )


def _collect_skills_from_root(
    root: Path,
    max_description_chars: int,
) -> list[SkillSummary]:
    if not root.exists() or not root.is_dir():
        return []

    summaries: list[SkillSummary] = []
    for entry in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        skill_file = entry / "SKILL.md"
        if not entry.is_dir() or not skill_file.is_file():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        fields = _parse_frontmatter_fields(content)
        description, truncated = _truncate_text(
            fields.get("description", ""),
            max_description_chars,
        )
        summaries.append(
            SkillSummary(
                name=fields.get("name") or entry.name,
                description=description,
                truncated=truncated,
            )
        )

    return summaries


def _dedupe_skill_summaries(summaries: list[SkillSummary]) -> list[SkillSummary]:
    seen: set[str] = set()
    deduped: list[SkillSummary] = []
    for summary in summaries:
        if summary.name in seen:
            continue
        seen.add(summary.name)
        deduped.append(summary)
    return deduped


def _parse_frontmatter_fields(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}

    end = content.find("\n---", 4)
    if end == -1:
        return {}

    fields: dict[str, str] = {}
    for line in content[4:end].splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        normalized_key = key.strip()
        if normalized_key in {"name", "description"}:
            fields[normalized_key] = value.strip().strip('"')
    return fields


def _truncate_text(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    if max_chars <= 1:
        return value[:max_chars], True
    return value[: max_chars - 1].rstrip() + "…", True


def _format_instruction_context(name: str, priority_note: str, instruction: InstructionFile) -> str:
    if not instruction.exists:
        return (
            f"<{name} path=\"{instruction.path}\" exists=\"false\">\n"
            f"{priority_note}\n"
            f"</{name}>"
        )

    metadata = f"path=\"{instruction.path}\" exists=\"true\" truncated=\"{str(instruction.truncated).lower()}\""
    warning = f"\nWarning: {instruction.warning}" if instruction.warning else ""
    return (
        f"<{name} {metadata}>\n"
        f"{priority_note}{warning}\n\n"
        f"{instruction.content.rstrip()}\n"
        f"</{name}>"
    )


def _format_available_skills(skills: SkillsContext) -> str:
    metadata = (
        f"total=\"{skills.total_count}\" included=\"{len(skills.summaries)}\" "
        f"truncated=\"{str(skills.truncated).lower()}\""
    )
    if not skills.summaries:
        return (
            f"<available_skills {metadata}>\n"
            "No skills are currently available. Do not guess skill names.\n"
            "</available_skills>"
        )

    lines = [
        f"<available_skills {metadata}>",
        "Use invoke_skill only for skills listed here. Do not guess skill names.",
    ]
    for summary in skills.summaries:
        suffix = " [truncated]" if summary.truncated else ""
        description = summary.description or "(no description)"
        lines.append(f"- {summary.name}: {description}{suffix}")

    lines.append("</available_skills>")
    return "\n".join(lines)


def _format_skill_invocation_request(invocation: SkillInvocationInput) -> str:
    args_block = f"\n<skill_args>\n{invocation.args}\n</skill_args>" if invocation.args else ""
    return (
        f"<skill_invocation_request skill=\"{invocation.skill_name}\">\n"
        "The user explicitly invoked this skill with $ syntax.\n"
        "Before answering or taking task actions, call invoke_skill with this exact skill name and args.\n"
        "Do not treat this request as the full skill content; invoke_skill loads the skill instructions."
        f"{args_block}\n"
        "</skill_invocation_request>"
    )


def _format_environment_context(snapshot: ContextSnapshot) -> str:
    git_status = snapshot.git.short_status or "(clean)"
    git_warning = f"\nGit warning: {snapshot.git.warning}" if snapshot.git.warning else ""
    return (
        "<environment_context>\n"
        f"cwd: {snapshot.cwd}\n"
        f"repo_root: {snapshot.repo_root}\n"
        f"git_branch: {snapshot.git.branch or '(unknown)'}\n"
        f"git_dirty: {snapshot.git.dirty}\n"
        f"git_status:\n{git_status}{git_warning}\n"
        f"adapter: {snapshot.runtime.adapter_name}\n"
        f"permission_profile: {snapshot.runtime.permission_profile}\n"
        f"max_steps: {snapshot.runtime.max_steps}\n"
        "</environment_context>"
    )


def _detect_repo_root(cwd: Path) -> tuple[Path, str | None]:
    result = _run_git(cwd, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return cwd, _git_warning("git rev-parse --show-toplevel", result)

    output = result.stdout.strip()
    if not output:
        return cwd, "git rev-parse --show-toplevel returned no repo root."

    return Path(output).resolve(), None


def _collect_git_context(cwd: Path, repo_warning: str | None) -> GitContext:
    branch_result = _run_git(cwd, "branch", "--show-current")
    status_result = _run_git(cwd, "status", "--short")

    if branch_result.returncode != 0 or status_result.returncode != 0:
        warning = repo_warning or _git_warning("git status", status_result)
        return GitContext(
            branch=None,
            dirty=False,
            short_status="",
            warning=warning,
        )

    short_status = status_result.stdout.strip()
    return GitContext(
        branch=branch_result.stdout.strip() or None,
        dirty=bool(short_status),
        short_status=short_status,
        warning=repo_warning,
    )


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )


def _git_warning(command: str, result: subprocess.CompletedProcess[str]) -> str:
    details = (result.stderr or result.stdout).strip()
    if details:
        return f"{command} failed: {details}"
    return f"{command} failed with exit code {result.returncode}."
