"""Skill tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from OpenCAI.tooling.contracts import ToolResult, ToolSpec, tool_result
from OpenCAI.tooling.path_utils import display_path, resolve_child_path


DEFAULT_SKILL_ROOT = "skills"
PROJECT_SKILL_ROOT = ".opencai/skills"


def _skill_root(arguments: dict[str, Any], cwd: Path) -> Path | None:
    root = arguments.get("root", DEFAULT_SKILL_ROOT)
    if not isinstance(root, str) or not root:
        return None
    return resolve_child_path(cwd, root)


def _find_project_root(cwd: Path) -> Path:
    resolved = cwd.resolve()
    for candidate in [resolved, *resolved.parents]:
        if (candidate / PROJECT_SKILL_ROOT).is_dir() or (candidate / ".git").exists():
            return candidate
    return resolved


def _default_invoke_skill_roots(cwd: Path) -> list[Path]:
    project_root = _find_project_root(cwd)
    roots = [project_root / PROJECT_SKILL_ROOT, Path.home() / "AgentSkills"]
    return [root.resolve() for root in roots]


def _is_valid_skill_name(name: str) -> bool:
    path = Path(name)
    return bool(name) and not path.is_absolute() and len(path.parts) == 1 and name not in {".", ".."}


def _extract_frontmatter_description(content: str) -> str:
    if not content.startswith("---\n"):
        return ""

    end = content.find("\n---", 4)
    if end == -1:
        return ""

    frontmatter = content[4:end].splitlines()
    for line in frontmatter:
        key, separator, value = line.partition(":")
        if separator and key.strip() == "description":
            return value.strip().strip('"')
    return ""


def list_skills(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    root = _skill_root(arguments, cwd)
    if root is None:
        return tool_result("list_skills", False, error="Invalid skill root")
    if not root.exists():
        return tool_result(
            "list_skills",
            True,
            {
                "root": display_path(root, cwd),
                "skills": [],
            },
        )
    if not root.is_dir():
        return tool_result("list_skills", False, error="Skill root is not a directory")

    skills: list[dict[str, str]] = []
    for entry in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        skill_file = entry / "SKILL.md"
        if not entry.is_dir() or not skill_file.is_file():
            continue

        description = ""
        try:
            description = _extract_frontmatter_description(
                skill_file.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError):
            pass

        skills.append(
            {
                "name": entry.name,
                "path": display_path(entry, cwd),
                "description": description,
            }
        )

    return tool_result(
        "list_skills",
        True,
        {
            "root": display_path(root, cwd),
            "skills": skills,
        },
    )


def read_skill(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    name = arguments.get("name")
    if not isinstance(name, str) or not _is_valid_skill_name(name):
        return tool_result("read_skill", False, error="Invalid skill name")

    root = _skill_root(arguments, cwd)
    if root is None:
        return tool_result("read_skill", False, error="Invalid skill root")

    skill_file = root / name / "SKILL.md"
    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return tool_result("read_skill", False, error=f"Read failed: {exc}")

    return tool_result(
        "read_skill",
        True,
        {
            "name": name,
            "path": display_path(skill_file, cwd),
            "content": content,
        },
    )


def invoke_skill(arguments: dict[str, Any], cwd: Path) -> ToolResult:
    name = arguments.get("skill")
    if not isinstance(name, str) or not _is_valid_skill_name(name):
        return tool_result("invoke_skill", False, error="Invalid skill name")

    args = arguments.get("args", "")
    if not isinstance(args, str):
        return tool_result("invoke_skill", False, error="Invalid skill args")

    skill_file: Path | None = None
    for root in _default_invoke_skill_roots(cwd):
        candidate = root / name / "SKILL.md"
        if candidate.is_file():
            skill_file = candidate
            break

    if skill_file is None:
        return tool_result("invoke_skill", False, error=f"Skill not found: {name}")

    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return tool_result("invoke_skill", False, error=f"Read failed: {exc}")

    rendered = _format_invoked_skill_message(name, args, skill_file, content, cwd)
    return tool_result(
        "invoke_skill",
        True,
        {
            "skill": name,
            "args": args,
            "path": display_path(skill_file, cwd),
            "content": content,
            "messages": [
                {
                    "role": "user",
                    "kind": "invoked_skill",
                    "content": rendered,
                }
            ],
        },
    )


def _format_invoked_skill_message(
    name: str,
    args: str,
    skill_file: Path,
    content: str,
    cwd: Path,
) -> str:
    args_block = f"\n<skill_args>\n{args}\n</skill_args>" if args else ""
    return (
        f"<invoked_skill name=\"{name}\" path=\"{display_path(skill_file, cwd)}\">"
        f"{args_block}\n"
        "<skill_content>\n"
        f"{content.rstrip()}\n"
        "</skill_content>\n"
        "</invoked_skill>"
    )


SKILL_TOOLS: dict[str, ToolSpec] = {
    "list_skills": ToolSpec(
        name="list_skills",
        description="List local OpenCAI skills under a workspace skill root.",
        input_schema={
            "type": "object",
            "properties": {
                "root": {"type": "string"},
            },
        },
        read_only=True,
        function=list_skills,
    ),
    "read_skill": ToolSpec(
        name="read_skill",
        description="Read the SKILL.md entrypoint for a local OpenCAI skill.",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "root": {"type": "string"},
            },
            "required": ["name"],
        },
        read_only=True,
        function=read_skill,
    ),
    "invoke_skill": ToolSpec(
        name="invoke_skill",
        description=(
            "Load a local OpenCAI skill and return model-visible skill instructions. "
            "Use this when the user explicitly invokes $skill or when a listed skill matches the task."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "skill": {"type": "string"},
                "args": {"type": "string"},
            },
            "required": ["skill"],
        },
        read_only=True,
        function=invoke_skill,
    ),
}

