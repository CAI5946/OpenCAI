from __future__ import annotations

from pathlib import Path

from OpenCAI import events
from OpenCAI.safety import SafetyPolicy
from OpenCAI.tools import TOOLS


def run_user_shell_command(command: str, cwd: Path, policy: SafetyPolicy) -> list[events.Event]:
    transcript: list[events.Event] = [events.shell_command(1, command)]

    decision = policy.check_user_command(command)
    if not decision.allowed:
        transcript.append(
            events.make_event(
                "error",
                2,
                decision.reason or "Shell command blocked.",
                {"command": command},
            )
        )
        return transcript

    result = TOOLS["run_command"].function({"command": command}, cwd)
    if not result["ok"]:
        transcript.append(
            events.tool_result(
                2,
                "run_command",
                False,
                result=result["result"],
                error=result["error"],
            )
        )
        return transcript

    data = result["result"]
    transcript.append(
        events.verification(
            2,
            command,
            data.get("exit_code", 1),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
        )
    )
    return transcript
