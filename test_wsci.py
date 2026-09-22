"""Offline checks for retrieval, isolation, validation and state persistence."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import smarter_wsci as app
from wsci_common import QUESTION

ANSWER = {"likely_cause": "Cached old credentials", "steps": ["Forget eduroam and reconnect"], "explanation": "Other signed-in devices may keep working temporarily."}


def response(content):
    return SimpleNamespace(message=SimpleNamespace(content=content))


class WSCITests(unittest.TestCase):
    def test_retrieval_topics(self):
        cases = {"Wi-Fi password changed": {"wifi_setup.txt", "password_changes.txt", "service_status.txt"},
                 "PRINTER": {"printing.txt", "service_status.txt"},
                 "VPN credentials": {"vpn.txt", "password_changes.txt", "service_status.txt"},
                 "email": {"email_setup.txt", "service_status.txt"},
                 "projector HDMI": {"classroom_projectors.txt", "service_status.txt"},
                 "blueprint": set(), "": set()}
        for question, expected in cases.items():
            with self.subTest(question=question):
                files = app.select_context(question)
                self.assertEqual({file.name for file in files}, expected)
                self.assertTrue(all(file.is_file() for file in files))

    def test_isolation(self):
        state = {"diagnostic_context": {"problem": QUESTION, "last_response": ANSWER, "irrelevant": "secret"},
                 "report_context": {"completed_runs": 37}}
        selected = app.isolate_state(state, QUESTION)
        self.assertEqual(set(selected), {"problem", "last_response"})
        self.assertEqual(app.isolate_state(state, "different problem"), {})
        self.assertEqual(app.isolate_state(state, QUESTION, "report"), {"completed_runs": 37})
        with self.assertRaises(ValueError):
            app.isolate_state(state, QUESTION, "unknown")

    def test_compression_fallback(self):
        for output in ("", "longer than input"):
            with patch.object(app, "ask_qwen", return_value=response(output)):
                self.assertEqual(app.compress_context("input", "q"), "input")
        with patch.object(app, "ask_qwen", return_value=response("short")):
            self.assertEqual(app.compress_context("long original context", "q"), "short")
        with patch.object(app, "ask_qwen") as model:
            self.assertEqual(app.compress_context("", "q"), "")
            model.assert_not_called()

    def test_invalid_answers(self):
        for answer in ([], {}, {**ANSWER, "extra": 1}, {**ANSWER, "steps": []},
                       {**ANSWER, "steps": "not a list"}, {**ANSWER, "likely_cause": ""}):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                app.validate_answer(answer)

    def test_state_roundtrip_and_no_clobber_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            with patch.object(app, "ask_qwen", side_effect=[response("short facts"), response(json.dumps(ANSWER))]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(app.main(state_path=path), ANSWER)
            state = app.load_state(path)
            self.assertEqual(state["report_context"]["completed_runs"], 1)
            original = path.read_bytes()
            with patch.object(app, "ask_qwen", side_effect=[response("short facts"), response("invalid json")]), self.assertRaises(ValueError):
                app.main(state_path=path)
            self.assertEqual(path.read_bytes(), original)
            with patch.object(app, "ask_qwen", side_effect=[response("short facts"), response(json.dumps(ANSWER))]) as model, contextlib.redirect_stdout(io.StringIO()):
                app.main(state_path=path)
            supplied = json.loads(model.call_args.args[2])
            self.assertEqual(supplied["previous_advice_not_verified_outcome"]["last_response"], ANSWER)
            self.assertNotIn("report_context", supplied)
            self.assertEqual(app.load_state(path)["report_context"]["completed_runs"], 2)

    def test_corrupt_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            for content in ('{', '[]', '{"diagnostic_context":{},"report_context":{"completed_runs":-1}}'):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    app.load_state(path)


if __name__ == "__main__":
    unittest.main()
