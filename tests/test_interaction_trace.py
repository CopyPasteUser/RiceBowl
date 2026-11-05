"""Opt-in Aqua pointer evidence is bounded, private and content-free."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from macrice.interaction_trace import InteractionTrace, MAX_BYTES, trace_path
from macrice.cli import main


class InteractionTraceTests(unittest.TestCase):
    def test_opt_in_and_fixed_fields_only(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "ricebowl" / "frutiger-interactions.jsonl"
            probe = InteractionTrace(path)
            probe.record("click", "network")
            self.assertFalse(path.exists())
            probe.start()
            probe.record("click", "network")
            probe.record("result", "network", True)
            probe.stop()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            entries = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([(item["event"], item["target"]) for item in entries],
                             [("begin", "session"), ("click", "network"),
                              ("result", "network"), ("end", "session")])
            self.assertEqual(entries[2]["visible"], True)
            self.assertTrue(all(set(item) <= {"time", "event", "target", "visible"}
                                for item in entries))

    def test_rejects_unknown_target_and_non_boolean_state(self):
        with tempfile.TemporaryDirectory() as root:
            probe = InteractionTrace(Path(root) / "ricebowl" / "trace.jsonl")
            with self.assertRaises(ValueError):
                probe._append("click", "my-secret-window-title", None)
            with self.assertRaises(ValueError):
                probe._append("result", "audio", "my-home-wifi-password")
            with self.assertRaises(ValueError):
                probe._append("incorrect", "audio", None)

    def test_capped_file_discards_old_records_without_growing_forever(self):
        with tempfile.TemporaryDirectory() as root:
            probe = InteractionTrace(Path(root) / "ricebowl" / "trace.jsonl")
            probe.start()
            for _ in range(1900):
                probe.record("result", "network", False)
            probe.stop()
            self.assertLessEqual(probe.path.stat().st_size, MAX_BYTES)
            self.assertTrue(probe.path.read_text().endswith('"target":"session"}\n'))

    def test_refuses_symlink_and_existing_public_file(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "ricebowl"
            directory.mkdir(mode=0o700)
            private = directory / "trace.jsonl"
            victim = Path(root) / "my-precious-data"
            victim.write_text("KEEP")
            private.symlink_to(victim)
            with self.assertRaises(OSError):
                InteractionTrace(private).start()
            self.assertEqual(victim.read_text(), "KEEP")
            private.unlink()
            private.write_text("DO NOT MODIFY")
            private.chmod(0o644)
            with self.assertRaises(OSError):
                InteractionTrace(private).start()
            self.assertEqual(private.read_text(), "DO NOT MODIFY")

    def test_xdg_cache_path_and_missing_relative_override(self):
        user_home = Path("/home/example")
        self.assertEqual(trace_path({"XDG_CACHE_HOME": "/tmp/example-cache"}, user_home=user_home),
                         Path("/tmp/example-cache/ricebowl/frutiger-interactions.jsonl"))
        self.assertEqual(trace_path({"XDG_CACHE_HOME": "relative/path"}, user_home=user_home),
                         user_home / ".cache/ricebowl/frutiger-interactions.jsonl")


class AquaTraceWiringTests(unittest.TestCase):
    def test_cli_commands_forward_to_the_existing_frutiger_application(self):
        with patch("macrice.aero_shell.run", return_value=0) as runner:
            self.assertEqual(main(["frutiger-shell", "--trace-actions"]), 0)
            runner.assert_called_with(["ricehub-frutiger-shell", "--trace-actions"], profile="frutiger")
            runner.reset_mock()
            self.assertEqual(main(["frutiger-shell", "--trace-stop"]), 0)
            runner.assert_called_with(["ricehub-frutiger-shell", "--trace-stop"], profile="frutiger")

    def test_path_lookup_does_not_start_shell_or_create_file(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict("os.environ", {"XDG_CACHE_HOME": root}):
                with patch("macrice.aero_shell.run") as runner:
                    with patch("builtins.print") as output:
                        self.assertEqual(main(["frutiger-shell", "--trace-path"]), 0)
                runner.assert_not_called()
                self.assertEqual(output.call_args.args[0], trace_path())
                self.assertFalse(trace_path().exists())

    def test_session_and_all_shell_targets_have_opt_in_diagnostic_contract(self):
        root = Path(__file__).resolve().parents[1]
        cli = (root / "macrice/cli.py").read_text()
        shell = (root / "macrice/aero_shell.py").read_text()
        for phrase in ("--trace-actions", "--trace-stop", "--trace-path"):
            self.assertTrue(phrase in cli, f"CLI missing {phrase}")
        self.assertTrue('"--trace-actions" in args:' in shell, "Aqua trace enable routing missing")
        self.assertTrue('"--trace-stop" in args:' in shell, "Aqua trace stop routing missing")
        for target in ("start", "network", "audio", "battery", "bluetooth",
                       "drives", "notifications", "calendar", "app-pin"):
            self.assertTrue(f'"{target}"' in shell, f"Aqua diagnostic target missing: {target}")


if __name__ == "__main__":
    unittest.main()
