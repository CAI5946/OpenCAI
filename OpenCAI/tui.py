from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table


console = Console()


def mock_events(task: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "user_task",
            "title": "User task",
            "body": task,
        },
        {
            "type": "assistant_status",
            "title": "Assistant",
            "body": "Planning the smallest observable coding-agent loop.",
        },
        {
            "type": "tool_call",
            "title": "Tool call",
            "name": "search_files",
            "input": {"query": "failing test", "path": "."},
        },
        {
            "type": "tool_result",
            "title": "Tool result",
            "body": "Found one likely failing test in examples/toy_project.",
        },
        {
            "type": "patch_summary",
            "title": "Patch summary",
            "body": "Would update one source file. No real file changes were made.",
        },
        {
            "type": "verification",
            "title": "Verification",
            "body": "Mock verification passed with exit code 0.",
        },
        {
            "type": "final",
            "title": "Final answer",
            "body": "Stage 0 transcript rendering is visible. Agent core is not connected yet.",
        },
    ]


def render_startup() -> None:
    cwd = Path.cwd()
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("Project", "OpenCAI")
    table.add_row("Mode", "Stage 0 / Mock TUI")
    table.add_row("CWD", str(cwd))
    table.add_row("Status", "No LLM, no real tools, no file writes")

    console.print()
    console.print(
        Panel(
            table,
            title="OpenCAI Coding Agent",
            subtitle="thin transcript renderer",
            border_style="cyan",
        ),
    )
    console.print()


def render_event(event: dict[str, Any]) -> None:
    event_type = event["type"]
    title = event["title"]

    if event_type == "tool_call":
        body = Table.grid(padding=(0, 1))
        body.add_column(style="bold")
        body.add_column()
        body.add_row("name", event["name"])
        body.add_row("input", repr(event["input"]))
        console.print(Panel(body, title=title, border_style="magenta"))
        return

    border_styles = {
        "user_task": "green",
        "assistant_status": "blue",
        "tool_result": "yellow",
        "patch_summary": "cyan",
        "verification": "green",
        "final": "white",
    }
    body = Markdown(event["body"])
    console.print(Panel(body, title=title, border_style=border_styles[event_type]))


def render_transcript(task: str) -> None:
    console.rule("[bold]Transcript")
    for event in mock_events(task):
        render_event(event)
    console.rule()


def main() -> None:
    render_startup()
    task = Prompt.ask("Task", default="Fix the failing toy project test")
    render_transcript(task)


if __name__ == "__main__":
    main()
