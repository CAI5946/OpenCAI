from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from OpenCAI.tooling.registry import ToolExposure
from OpenCAI.agent_loop import run_agent_loop
from OpenCAI.llm_adapter import Message, ModelOutput
from OpenCAI.tools import ToolSpec
from OpenCAI.tools import TOOLS, run_tool


class CaptureToolsAdapter:
    def __init__(self) -> None:
        self.tools: dict[str, ToolSpec] = {}

    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        self.tools = tools
        return {"type": "final_answer", "answer": "done"}


class ToolTaxonomyTests(unittest.TestCase):
    def test_tools_md_taxonomy_names_are_registered(self) -> None:
        expected = {
            "read_file",
            "write_file",
            "edit_file",
            "apply_patch",
            "delete_file",
            "move_file",
            "copy_file",
            "list_files",
            "glob_files",
            "search_files",
            "run_command",
            "start_command",
            "read_command",
            "write_stdin",
            "stop_command",
            "update_plan",
            "create_task",
            "update_task",
            "list_tasks",
            "complete_task",
            "context_status",
            "read_context_block",
            "summarize_context",
            "search_memory",
            "workflow_plan",
            "workflow_execute",
            "workflow_status",
            "workflow_pause",
            "workflow_resume",
            "workflow_cancel",
            "workflow_replay",
            "spawn_agent",
            "send_agent_message",
            "wait_agent",
            "list_agents",
            "stop_agent",
            "merge_agent_result",
            "list_skills",
            "read_skill",
            "invoke_skill",
            "tool_search",
            "call_external_tool",
            "list_mcp_resources",
            "read_mcp_resource",
            "web_search",
            "web_fetch",
            "web_extract",
            "get_diagnostics",
            "go_to_definition",
            "find_references",
            "rename_symbol",
            "format_file",
        }

        self.assertTrue(expected.issubset(TOOLS))

    def test_future_runtime_tools_are_deferred_not_direct(self) -> None:
        for tool_name in ["workflow_execute", "spawn_agent", "get_diagnostics", "call_external_tool"]:
            self.assertEqual(TOOLS[tool_name].exposure, ToolExposure.DEFERRED)

    def test_agent_loop_exposes_only_direct_tools_to_model(self) -> None:
        adapter = CaptureToolsAdapter()

        run_agent_loop("check tools", adapter=adapter, max_steps=1)

        self.assertIn("read_file", adapter.tools)
        self.assertIn("workflow_plan", adapter.tools)
        self.assertNotIn("workflow_execute", adapter.tools)
        self.assertNotIn("spawn_agent", adapter.tools)

    def test_context_status_and_workflow_plan_have_read_only_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "README.md").write_text("demo", encoding="utf-8")
            (cwd / "docs").mkdir()
            (cwd / "docs" / "status.md").write_text("status", encoding="utf-8")

            context = run_tool("context_status", {}, cwd)
            workflow = run_tool("workflow_plan", {}, cwd)

        self.assertTrue(context["ok"])
        self.assertTrue(context["result"]["readme_exists"])
        self.assertTrue(workflow["ok"])
        self.assertEqual(workflow["result"]["name"], "inspect_handoff")
        self.assertEqual(
            ["inspect_context", "inspect_constraints", "handoff_summary"],
            [task["id"] for task in workflow["result"]["tasks"]],
        )
        self.assertEqual(
            [("run_phase", "inspect"), ("run_phase", "handoff"), ("handoff", "handoff")],
            [(op["type"], op.get("phase_id")) for op in workflow["result"]["script"]],
        )


if __name__ == "__main__":
    unittest.main()
