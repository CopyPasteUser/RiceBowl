import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "macos-control-center-toggle"
VERSION = (ROOT / "VERSION").read_text(encoding="ascii").strip()


class FastToggleLauncherTests(unittest.TestCase):
    def test_ready_resident_uses_one_native_dbus_call(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            installed = base / "share" / "macos-control-center" / "app"
            installed.mkdir(parents=True)
            app = installed / "macos-control-center"
            app.write_text("# fake installed program\n", encoding="utf-8")
            (installed / "VERSION").write_text(VERSION + "\n", encoding="ascii")
            helper_dir = installed.parent / "scripts"
            helper_dir.mkdir()
            helper = helper_dir / "macos-control-center-toggle"
            shutil.copy2(LAUNCHER, helper)

            fake_bin = base / "bin"
            fake_bin.mkdir()
            calls = base / "calls"
            gdbus = fake_bin / "gdbus"
            gdbus.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$@" > "$CC_FAKE_CALLS"\nprintf "(true,)\\n"\n',
                encoding="utf-8",
            )
            gdbus.chmod(0o755)

            env = os.environ.copy()
            env.update(
                XDG_DATA_HOME=str(base / "share"),
                XDG_RUNTIME_DIR=str(base),
                PATH=str(fake_bin) + os.pathsep + env.get("PATH", ""),
                CC_FAKE_CALLS=str(calls),
            )
            result = subprocess.run(
                ["bash", str(helper)],
                env=env,
                capture_output=True,
                text=True,
                timeout=3,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            arguments = calls.read_text(encoding="utf-8")
            self.assertIn("ToggleIfCurrent", arguments)
            self.assertIn(str(app), arguments)
            self.assertIn(VERSION, arguments)
            self.assertFalse((base / "macos-control-center.pid").exists())


if __name__ == "__main__":
    unittest.main()
