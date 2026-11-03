"""Visual skins for four independent profiles of RiceBowl's live GTK taskbar.

The shared GTK/Gio/Wnck lifecycle stays in aero_shell: no parallel window
trackers, subprocess pollers, or duplicate launchers are introduced here.
"""

CSS = {
    "winxp": b"""
.aero-taskbar { background-image: linear-gradient(#4294f1, #1f5fd2 36%, #1440a7); border-top: 2px solid #89baff; color: #fff; }
.aero-start { background-image: linear-gradient(#98db66, #4dae29 42%, #238119); border: 2px solid #d4ffb4; border-radius: 24px 8px 8px 24px; color: white; font-weight: bold; padding: 4px 14px; }
.aero-start:hover { background-image: linear-gradient(#b9ef8c, #62bc35, #2b901c); }
.aero-task, .aero-pin { background: #2e72d1; color: white; border: 1px solid #8dbafb; border-radius: 6px; }
.aero-task:hover, .aero-pin:hover, .aero-task-active { background: #579bee; border: 1px solid #d6eaff; }
.aero-time, .aero-quick, .aero-desktop, .aero-task-overflow { color: white; }
.aero-menu-root { background: #f9fcff; border: 2px solid #2c72c8; border-radius: 9px 9px 5px 5px; }
.aero-menu-heading { color: #144c96; }
.aero-menu-side { background-image: linear-gradient(#d7e8ff, #aacbf4); border-left: 1px solid #8db1e5; }
.aero-menu-app:hover { background: #c3dcff; }
.aero-control-root { background-image: linear-gradient(#fff, #d7e9ff); border: 2px solid #4284ce; }

.aero-control-root { background: #f5f5ec; color: #173a70; border: 3px solid #2e69b7; border-radius: 7px; padding: 14px; }
.aero-control-root .aero-menu-heading { color: #16417e; font-size: 19px; }
.aero-control-root .aero-menu-sub { color: #38668c; font-weight: bold; }
.aero-control-quick { background-image: linear-gradient(#fff, #e3eef9); color: #14467a; border: 1px solid #a3bdd7; border-radius: 4px; padding: 9px; }
.aero-control-quick:hover { background: #d3e8ff; border-color: #4d88c6; }
""",
    "winclassic": b"""
.aero-taskbar { background: #c0c0c0; color: #111; border-top: 2px solid #fff; border-bottom: 1px solid #666; padding: 2px 4px; }
.aero-start { background: #c0c0c0; border: 2px outset #eee; border-radius: 0; box-shadow: none; color: #111; padding: 4px 8px; font-weight: bold; }
.aero-start:hover { background: #d8d8d8; }
.aero-task, .aero-pin { background: #c0c0c0; color: #111; border: 2px outset #f5f5f5; border-radius: 0; box-shadow: none; }
.aero-task:hover, .aero-task-active { background: #aaa; border: 2px inset #f5f5f5; }
.aero-time { color: #111; background: #c0c0c0; padding: 2px 8px; border: 2px inset #efefef; }
.aero-quick, .aero-desktop, .aero-task-overflow { color: #111; border: 1px outset #fff; border-radius: 0; }
.aero-menu-root { background: #c0c0c0; border: 2px outset #fff; border-radius: 0; }
.classic-brand { background-image: linear-gradient(to bottom, #071d60, #215d99); border-right: 2px solid #909090; }
.classic-brand-label { color: white; font-size: 16px; font-weight: bold; }
.aero-menu-heading { color: #000080; }
.aero-menu-side { background: #d6d6d6; border-left: 1px solid #808080; }
.aero-menu-search { border: 2px inset #eeeeee; border-radius: 0; padding: 4px; }
.aero-menu-app { color: #111; border-radius: 0; }
.aero-menu-app:hover { background: #000080; color: #fff; }
.aero-menu-power { background: #c0c0c0; color: #111; border: 2px outset #fff; border-radius: 0; }
.aero-control-root { background: #c0c0c0; border: 2px outset #fff; border-radius: 0; }
.aero-control-quick { background: #c0c0c0; color: #111; border-radius: 0; border: 2px outset #fff; box-shadow: none; }
.aero-control-quick:hover, .aero-control-quick:focus { background: #d7d7d7; border: 2px inset #fff; }
.aero-control-root { padding: 9px; color: #111; }
.aero-control-root .aero-menu-heading { font-size: 15px; color: #000080; }
.aero-control-root .aero-menu-sub { color: #333; font-size: 11px; }
.aero-control-quick { padding: 6px; font-size: 12px; }
""",
    "chromeos": b"""
.aero-taskbar { background: rgba(242,246,255,.97); color: #26364e; border-top: 1px solid #c4d1e7; padding: 4px 12px; }
.aero-start { background: #dae7ff; color: #2752a0; border: 1px solid #c0d5f8; border-radius: 24px; box-shadow: none; padding: 4px 12px; }
.aero-start:hover { background: #c7dbff; }
.aero-task, .aero-pin { background: transparent; color: #2a3c58; border: 1px solid transparent; border-radius: 12px; box-shadow: none; }
.aero-task:hover, .aero-pin:hover, .aero-task-active { background: #d7e6ff; border: 1px solid #b6cced; }
.aero-time, .aero-quick, .aero-desktop, .aero-task-overflow { color: #293e62; }
.aero-menu-root { background: #f7faff; border: 1px solid #c9d8ee; border-radius: 17px; color: #293c56; }
.aero-menu-heading { color: #304e7a; }
.aero-menu-sub { color: #627799; }
.aero-menu-app { color: #293e62; border-radius: 9px; }
.aero-menu-app:hover { background: #d9e8ff; }
.aero-menu-search { background: white; border: 1px solid #9db9e8; border-radius: 20px; }
.ten-rail { background: #edf2fc; border-right: 1px solid #dae2f1; border-radius: 16px; }
.ten-tile { background: #e3ebfd; color: #324b76; border: 1px solid #cddbf3; border-radius: 12px; }
.ten-tile:hover { background: #d3e3ff; }
.ten-tile-label, .ten-muted { color: #344f76; }
.ten-action-root { background: #f8fbff; color: #263b57; border: 1px solid #bed1eb; border-radius: 18px; padding: 14px; }
.ten-quick { background: #e7effd; color: #2b4771; border: 1px solid #cbddf4; border-radius: 12px; }

.ten-action-root { background: #f8faff; border: 1px solid #b9cce8; border-radius: 24px; padding: 17px; }
.ten-action-root .aero-menu-heading { color: #1e3559; font-size: 20px; }
.ten-action-root .aero-menu-sub { color: #577193; }
.ten-quick { padding: 10px; border-radius: 15px; background: #e6efff; color: #263e63; }
.ten-quick:hover { background: #d0e1fc; }
""",
    "frutiger": b"""
.aero-taskbar { background-image: linear-gradient(rgba(206,255,248,.96), rgba(82,208,222,.94) 40%, rgba(18,137,179,.96)); border-top: 2px solid #f2ffff; color: #053e5c; }
.aero-start { background-image: linear-gradient(#faffff, #8df9d7 50%, #26b5bf); border: 2px solid #f5ffff; border-radius: 26px; color: #065074; box-shadow: 0 1px 4px #247b94; padding: 3px 13px; }
.aero-task, .aero-pin { color: #084866; background: rgba(237,255,252,.32); border: 1px solid rgba(243,255,255,.72); border-radius: 12px; }
.aero-task:hover, .aero-pin:hover, .aero-task-active { background: rgba(244,255,254,.75); border-color: white; }
.aero-time, .aero-quick, .aero-desktop, .aero-task-overflow { color: #063e59; }
.aero-menu-root { background: #e7fff9; border: 2px solid #70cfd3; border-radius: 17px; }
.aero-menu-heading { color: #086a91; }
.aero-menu-side { background-image: linear-gradient(#e1ffed, #7cdad0); border-left: 1px solid #8ccfd0; }
.aero-menu-app:hover { background: #a9efe9; }
.aero-control-root { background-image: linear-gradient(#f8fffe, #b1ece6); border: 2px solid #8acfcf; border-radius: 15px; }

.aero-control-root { background-image: linear-gradient(#f7ffff, #d0fff0 55%, #b2e8f7); color: #07516a; border: 2px solid #7bd5e4; border-radius: 18px; padding: 16px; }
.aero-control-root .aero-menu-heading { color: #086f8a; font-size: 20px; }
.aero-control-root .aero-menu-sub { color: #277f85; }
.aero-control-quick { background-image: linear-gradient(#fff, #c2f4f0); color: #07546a; border: 1px solid #78cad2; border-radius: 12px; padding: 9px; }
.aero-control-quick:hover { background: #f4ffff; border-color: #20a7c1; }
""",
}
