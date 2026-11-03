"""Windows 10 shell skin for RiceBowl's shared event-driven XFCE taskbar."""

from __future__ import annotations


APP_ID = "io.github.copypasteuser.RiceHub.TenShell"

CSS = b"""
/* RiceBowl Ten: flat Windows 10-inspired shell, no compositor blur required. */
@define-color ten-panel #15191f;
@define-color ten-surface #20252d;
@define-color ten-hover #343d49;
@define-color ten-blue #0879cb;
@define-color ten-line #4b5664;
@define-color ten-text #f5f8fc;

.aero-taskbar { background: @ten-panel; border-top: 1px solid #394451; color: @ten-text;
  padding: 3px 6px; }
.aero-start { background: transparent; border: 1px solid transparent; border-radius: 0;
  color: @ten-text; box-shadow: none; padding: 5px 8px; }
.aero-start:hover, .aero-start:focus { background: @ten-hover; border: 1px solid @ten-line; }
.aero-pin { background: transparent; border-radius: 0; border: 1px solid transparent;
  padding: 5px 10px; }
.aero-pin:hover { background: @ten-hover; border-color: @ten-line; }
.aero-task { background: transparent; color: @ten-text; border: 1px solid transparent;
  border-bottom: 2px solid @ten-blue; border-radius: 0; box-shadow: none; }
.aero-task:hover, .aero-task-active { background: @ten-hover; border-color: @ten-line;
  border-bottom-color: #33a5f4; }
.aero-task-overflow, .aero-quick, .aero-desktop { background: transparent; color: @ten-text;
  border: 1px solid transparent; border-radius: 0; box-shadow: none; }
.aero-task-overflow:hover, .aero-quick:hover, .aero-desktop:hover { background: @ten-hover; }
.aero-time { font-size: 11px; color: @ten-text; font-weight: normal; }
.aero-tray-icon { background: transparent; border: 1px solid transparent; border-radius: 0; }
.aero-tray-icon:hover { background: @ten-hover; }
.ten-search { background: #edf2f7; border: 1px solid #72889e; color: #182938;
  border-radius: 0; box-shadow: none; padding: 7px 11px; }
.ten-search:hover, .ten-search:focus { border-color: #51b0f2; background: #ffffff; }
.aero-menu-root, .ten-action-root { background: @ten-surface; border: 1px solid @ten-line;
  border-radius: 0; color: @ten-text; }
.aero-menu-heading, .aero-menu-sub { color: @ten-text; }
.aero-menu-search { background: #f6faff; border: 2px solid #168bd9; color: #192b39;
  border-radius: 0; padding: 7px; }
.aero-menu-app { background: transparent; color: @ten-text; border: 1px solid transparent;
  border-radius: 0; box-shadow: none; padding: 6px 9px; }
.aero-menu-app:hover, .aero-menu-app:focus { background: @ten-hover; border-color: @ten-line; }
.ten-rail { background: #171c23; border-right: 1px solid #354252; padding: 10px 5px; }
.ten-tile { background: @ten-blue; color: @ten-text; border: 1px solid #248cda;
  border-radius: 0; box-shadow: none; padding: 8px; }
.ten-tile:hover, .ten-tile:focus { background: #2597e9; border-color: #80ceff; }
.ten-tile-label { color: @ten-text; font-size: 11px; }
.ten-action-root { padding: 15px; }
.ten-quick { background: #354251; color: @ten-text; border: 1px solid @ten-line;
  border-radius: 0; box-shadow: none; padding: 12px 7px; }
.ten-quick:hover, .ten-quick:focus { background: @ten-blue; border-color: #7acbff; }
.ten-muted { color: #b6c5d6; font-size: 11px; }
button:focus { outline: 2px solid #6ec4fb; outline-offset: -2px; }

/* Windows 10: flat system tray with rectangular hover targets. */
.rice-status { background: transparent; border: 1px solid transparent; border-radius: 0; color: #f5f8fc; box-shadow: none; padding: 5px 4px; }
.rice-status:hover, .rice-status:focus { background: #344352; border: 1px solid #5b7188; }
.rice-status label { font-size: 11px; color: #f5f8fc; }
.rice-status-summary { color: #d2deed; font-size: 11px; }
"""


def run(argv: list[str] | None = None) -> int:
    from .aero_shell import run as shared_run

    return shared_run(argv or ["ricehub-ten-shell"], profile="windows10")
