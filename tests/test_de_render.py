"""Agent render-contract boundaries before any compositor processes run."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from macrice.cli import main as cli
from macrice.de import catalog, creator_contract, render


class HeadlessRenderTests(unittest.TestCase):
    def test_catalog_exposes_exact_headless_requirements(self):
        spec = catalog.describe()["authoring"]["render"]
        self.assertEqual(spec, creator_contract.describe_render())
        self.assertFalse(spec["requires_running_wayland_session"])
        self.assertTrue(spec["creates_temporary_compositor"])
        self.assertFalse(spec["mutates_active_desktop"])
        self.assertIn("riceplate-native", spec["requires_binaries"])

    def test_invalid_requests_rejected_before_process_spawn(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "new.png"
            existing = Path(folder) / "existing.png"
            existing.write_text("keep")
            symlink = Path(folder) / "link.png"
            symlink.symlink_to(existing)
            for output, width, height, scale in (
                (Path("relative.png"), 1366, 768, 1.0),
                (existing, 1366, 768, 1.0),
                (symlink, 1366, 768, 1.0),
                (dest, 300, 768, 1.0),
                (dest, 1366, 300, 1.0),
                (dest, 4096, 4096, 1.0),
                (dest, 1366, 768, 1.1),
            ):
                with self.subTest(output=output, width=width, height=height, scale=scale), \
                     mock.patch("macrice.de.render.subprocess.Popen") as spawn:
                    with self.assertRaises(render.RenderError) as error:
                        render.render("classic", output, width=width, height=height, scale=scale)
                    self.assertEqual(error.exception.code, "invalid_render_request")
                    spawn.assert_not_called()
            self.assertEqual(existing.read_text(), "keep")

    def test_missing_recipe_and_native_dependencies_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "new.png"
            with mock.patch("macrice.de.render.subprocess.Popen") as spawn:
                with self.assertRaises(render.RenderError) as raised:
                    render.render("../../../invalid", dest)
                self.assertEqual(raised.exception.code, "invalid_render_request")
                spawn.assert_not_called()
            with mock.patch("macrice.de.render.os.geteuid", return_value=1000), \
                 mock.patch("macrice.de.render.shutil.which", return_value=None), \
                 mock.patch("macrice.de.render.subprocess.Popen") as spawn:
                with self.assertRaises(render.RenderError) as raised:
                    render.render("classic", dest)
                self.assertEqual(raised.exception.code, "render_unavailable")
                spawn.assert_not_called()
            self.assertFalse(dest.exists())

    def test_output_detection_parses_only_one_safe_compositor_name(self):
        good = subprocess.CompletedProcess([], 0, stdout="HEADLESS-1 1920x1080\n  1920x1080\n")
        with mock.patch("macrice.de.render.subprocess.run", return_value=good):
            self.assertEqual(render._output_name("/usr/bin/wlr-randr", dict(os.environ)), "HEADLESS-1")
        bad = subprocess.CompletedProcess([], 0, stdout="bad/name\n")
        with mock.patch("macrice.de.render.subprocess.run", return_value=bad):
            with self.assertRaises(render.RenderError):
                render._output_name("/usr/bin/wlr-randr", dict(os.environ))

    def test_stop_terminates_owned_group_and_reaps(self):
        process = mock.Mock()
        process.pid = 12345
        process.poll.return_value = None
        process.wait.return_value = 0
        with mock.patch("macrice.de.render.os.killpg") as kill:
            render._stop(process)
        kill.assert_called_once_with(12345, render.signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=3)

    def test_stop_escalates_after_timeout(self):
        process = mock.Mock()
        process.pid = 12345
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("labwc", 3), 0]
        with mock.patch("macrice.de.render.os.killpg") as kill:
            render._stop(process)
        self.assertEqual(kill.call_args_list, [
            mock.call(12345, render.signal.SIGTERM),
            mock.call(12345, render.signal.SIGKILL),
        ])
        self.assertEqual(process.wait.call_count, 2)

    def test_cleanup_continues_after_child_failure(self):
        children = [mock.Mock(), mock.Mock(), mock.Mock()]
        with mock.patch("macrice.de.render._stop",
                        side_effect=[OSError("injected"), None, None]) as stop:
            with self.assertRaises(render.RenderError) as raised:
                render._cleanup_children(children)
        self.assertEqual(raised.exception.code, "render_failed")
        self.assertEqual([call.args[0] for call in stop.call_args_list],
                         list(reversed(children)))

    def test_stop_does_not_signal_reaped_pid(self):
        process = mock.Mock()
        process.poll.return_value = 0
        with mock.patch("macrice.de.render.os.killpg") as kill:
            render._stop(process)
        kill.assert_not_called()
        process.wait.assert_called_once_with()

    def test_json_cli_failure_is_stable_and_does_not_expose_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "private.png"
            with mock.patch("builtins.print") as printer:
                self.assertEqual(cli(["de", "render", "--recipe", "classic", "--output",
                                      str(target), "--width", "320", "--json"]), 2)
            error = json.loads(printer.call_args.args[0])
            self.assertFalse(error["ok"])
            self.assertEqual(error["error"]["code"], "invalid_render_request")
            self.assertNotIn(folder, json.dumps(error))
            self.assertFalse(target.exists())

    def test_geometry_flags_do_not_leak_to_other_commands(self):
        for arguments in (["de", "catalog", "--width", "1024"],
                          ["de", "capture", "--height", "768"],
                          ["de", "render", "--nested"],
                          ["de", "render", "--panel", "native"]):
            with self.subTest(arguments=arguments), mock.patch("sys.stderr"):
                self.assertEqual(cli(arguments), 1)


if __name__ == "__main__":
    unittest.main()
