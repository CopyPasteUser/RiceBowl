# Contributing

MacBar intentionally stays small: standard-library Python plus the system
GTK3/PyGObject bindings. Please do not add Electron, a web view, extra status
daemons or a task list. Keep third-party system controls in Control Center.

Run the checks before submitting changes:

```sh
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m py_compile macbar.py status.py measure.py
sh -n install.sh uninstall.sh
```

Describe any changes to XFCE session behavior, screen reservations, battery,
network or audio with a reproducible test. Changes to rendering need an
on-device X11 screenshot or a written manual verification note.
