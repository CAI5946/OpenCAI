import unittest
from pathlib import Path
import tempfile

from OpenCAI.agent_loop import run_agent_loop
from OpenCAI.llm_adapter import LLMAdapter, Message, ModelOutput
from OpenCAI.safety import PermissionProfile, SafetyPolicy
from OpenCAI.tools import ToolSpec


class SingleToolCallAdapter:
    def __init__(self, tool_name: str, arguments: dict[str, object]) -> None:
        self.tool_name = tool_name
        self.arguments = arguments

    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        return {
            "type": "tool_call",
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }


class RepeatedToolCallAdapter:
    def __init__(self, tool_name: str, arguments: dict[str, object]) -> None:
        self.tool_name = tool_name
        self.arguments = arguments

    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        return {
            "type": "tool_call",
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }


class AgentLoopSafetyTest(unittest.TestCase):
    def test_denied_command_is_reported_as_tool_result(self) -> None:
        events = run_agent_loop(
            "Run tests",
            adapter=SingleToolCallAdapter(
                "run_command",
                {"command": "python -m unittest discover examples/toy_project"},
            ),
            max_steps=1,
            policy=SafetyPolicy(profile=PermissionProfile.READ_ONLY),
        )

        denied = [event for event in events if event["type"] == "tool_result"][0]
        self.assertFalse(denied["data"]["ok"])
        self.assertEqual("run_command", denied["data"]["tool_name"])
        self.assertIn("Approval required for command execution", denied["data"]["error"])

    def test_unknown_tool_is_reported_without_policy_check(self) -> None:
        events = run_agent_loop(
            "Delete a file",
            adapter=SingleToolCallAdapter("remove_file", {"path": "README.md"}),
            max_steps=1,
        )

        result = [event for event in events if event["type"] == "tool_result"][0]
        self.assertFalse(result["data"]["ok"])
        self.assertEqual("remove_file", result["data"]["tool_name"])
        self.assertIn("Unknown tool", result["data"]["error"])

    def test_max_steps_reached_is_stop_event_not_final_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "README.md").write_text("demo", encoding="utf-8")
            events = run_agent_loop(
                "Keep calling a tool",
                cwd=cwd,
                adapter=SingleToolCallAdapter("read_file", {"path": "README.md"}),
                max_steps=1,
            )

        self.assertEqual("stop", events[-1]["type"])
        self.assertEqual("max_steps_reached", events[-1]["data"]["reason"])
        self.assertEqual(1, events[-1]["data"]["max_model_turns"])
        self.assertNotIn("final_answer", [event["type"] for event in events])

    def test_repeated_tool_call_stops_before_hard_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "README.md").write_text("demo", encoding="utf-8")
            events = run_agent_loop(
                "Keep reading the same file",
                cwd=cwd,
                adapter=RepeatedToolCallAdapter("read_file", {"path": "README.md"}),
                max_steps=5,
            )

        self.assertEqual("stop", events[-1]["type"])
        self.assertEqual("repeated_action", events[-1]["data"]["reason"])
        self.assertEqual("read_file", events[-1]["data"]["tool_name"])
        self.assertEqual(3, events[-1]["data"]["repeated_tool_calls"])

    def test_consecutive_tool_failures_stop_before_hard_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            events = run_agent_loop(
                "Keep using a failing tool",
                cwd=cwd,
                adapter=RepeatedToolCallAdapter("delete_file", {"path": "missing.txt"}),
                max_steps=5,
            )

        self.assertEqual("stop", events[-1]["type"])
        self.assertEqual("consecutive_tool_failures", events[-1]["data"]["reason"])
        self.assertEqual(3, events[-1]["data"]["consecutive_tool_failures"])

    def test_command_runs_when_policy_allows_it(self) -> None:
        events = run_agent_loop(
            "Run a harmless command",
            adapter=SingleToolCallAdapter("run_command", {"command": "python --version"}),
            max_steps=1,
            policy=SafetyPolicy(profile=PermissionProfile.APPROVE_SAFE),
        )

        result = [event for event in events if event["type"] == "tool_result"][0]
        self.assertTrue(result["data"]["ok"])
        self.assertEqual(0, result["data"]["result"]["exit_code"])


if __name__ == "__main__":
    unittest.main()
