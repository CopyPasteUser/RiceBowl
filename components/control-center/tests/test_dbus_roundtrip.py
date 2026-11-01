"""Headless integration check for the real session-bus toggle protocol."""

import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = (ROOT / "VERSION").read_text(encoding="ascii").strip()


def run_probe():
    from gi.repository import GLib
    from toggle_ipc import BUS_NAME, OBJECT_PATH, ToggleService
    METHOD = BUS_NAME + ".ToggleIfCurrent"

    loop = GLib.MainLoop()
    changes = []
    results = []
    times_ms = []
    temporary = tempfile.TemporaryDirectory(prefix="maccc-ipc-")
    data = Path(temporary.name) / "data"
    installed_app = data / "macos-control-center" / "app"
    installed_app.mkdir(parents=True)
    script = str(installed_app / "macos-control-center")
    Path(script).write_text("# resident identity for test\n", encoding="ascii")
    (installed_app / "VERSION").write_text(VERSION + "\n", encoding="ascii")
    helper_dir = installed_app.parent / "scripts"
    helper_dir.mkdir()
    helper = helper_dir / "macos-control-center-toggle"
    shutil.copy2(ROOT / "macos-control-center-toggle", helper)

    def toggle():
        changes.append(not changes[-1] if changes else True)

    service = ToggleService(toggle, script, VERSION)
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data)

    def launcher_call():
        start = time.monotonic()
        response = subprocess.run(
            ["bash", str(helper)],
            env=env, capture_output=True, text=True, timeout=3,
        )
        times_ms.append((time.monotonic() - start) * 1000)
        return "(true,)" if response.returncode == 0 else "error: " + response.stderr

    def call(expected_script, expected_version):
        return subprocess.run(
            [
                "gdbus", "call", "--session", "--timeout", "1",
                "--dest", BUS_NAME, "--object-path", OBJECT_PATH,
                "--method", METHOD, expected_script, expected_version,
            ],
            text=True, capture_output=True, timeout=3,
        )

    def client():
        try:
            deadline = time.monotonic() + 3
            while True:
                ready = call(script, VERSION)
                if ready.returncode == 0:
                    results.append(ready.stdout.strip())
                    break
                if time.monotonic() >= deadline:
                    results.append("unavailable: " + ready.stderr.strip())
                    return
                time.sleep(0.03)
            for args in [
                (script, "0.0.0"),  # Stale release must not toggle
                ("/tmp/other/macos-control-center", VERSION),  # Wrong app
            ]:
                response = call(*args)
                results.append(response.stdout.strip() if response.returncode == 0
                               else "error: " + response.stderr.strip())
            for _ in range(6):
                results.append(launcher_call())
        finally:
            GLib.idle_add(loop.quit)

    thread = threading.Thread(target=client, daemon=True)
    thread.start()
    GLib.timeout_add_seconds(6, loop.quit)
    loop.run()
    thread.join(timeout=1)
    service.close()
    temporary.cleanup()

    if results != ["(true,)", "(false,)", "(false,)"] + ["(true,)"] * 6:
        print("Unexpected responses: " + repr(results), file=sys.stderr)
        return 1
    if changes != [True, False, True, False, True, False, True]:
        print("Unexpected toggles: " + repr(changes), file=sys.stderr)
        return 1
    print("Warm shell-to-GTK-IPC median: %.1f ms" % statistics.median(times_ms))
    return 0


class RealDBusTests(unittest.TestCase):
    def test_atomic_roundtrip_without_a_gtk_display(self):
        if not Path("/usr/bin/python3").exists():
            self.skipTest("System Python is required for PyGObject")
        if not subprocess.run(
            ["/usr/bin/python3", "-c", "import gi"], capture_output=True
        ).returncode == 0:
            self.skipTest("PyGObject is not installed")
        if not all(shutil.which(x) for x in ("dbus-run-session", "gdbus")):
            self.skipTest("A session bus and native gdbus client are required")
        run = subprocess.run(
            ["dbus-run-session", "--", "/usr/bin/python3", str(__file__), "_child"],
            capture_output=True, text=True, timeout=12,
        )
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_child":
        raise SystemExit(run_probe())
    unittest.main()
