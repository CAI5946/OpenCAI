from __future__ import annotations

import unittest
from unittest.mock import patch

from OpenCAI.events import final_answer, user_task
from OpenCAI.tui import render_event_stream


class TuiStreamingTests(unittest.TestCase):
    def test_render_event_stream_consumes_events_in_iteration_order(self) -> None:
        consumed_types: list[str] = []

        def event_source():
            yield user_task(1, "Read README")
            yield final_answer(2, "done")

        with patch("OpenCAI.tui.console.rule"), patch("OpenCAI.tui.render_event") as render_event:
            render_event.side_effect = lambda event: consumed_types.append(event["type"])
            render_event_stream(event_source())

        self.assertEqual(consumed_types, ["user_task", "final_answer"])


if __name__ == "__main__":
    unittest.main()
