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

/* Luna status and navigation: beveled, compact blue system tray. */
.rice-status { background-image: linear-gradient(#377be3, #1e54b8); border: 1px solid #80b5ff; border-radius: 3px; color: white; padding: 2px 4px; box-shadow: inset 0 1px rgba(255,255,255,.4); }
.rice-status:hover, .rice-status:focus { background: #5a9eee; border-color: #cceaff; }
.rice-status label { color: #fff; font-size: 11px; font-weight: bold; }
.aero-menu-app { background: #f9fbff; color: #184680; border-radius: 3px; }
.aero-menu-search { background: #fff; border: 1px solid #73a5d9; border-radius: 3px; }
.aero-menu-footer { background: #dae8ff; border-top: 2px solid #83ace0; }
.rice-status-summary { color: #225f91; font-size: 11px; }
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

/* Win9x: crisp 1-pixel borders and recessed status indicators. */
.rice-status { background: #c0c0c0; color: #111; border: 2px inset #f4f4f4; border-radius: 0; box-shadow: none; padding: 1px 3px; }
.rice-status:hover, .rice-status:focus { background: #d3d3d3; border: 2px outset #f4f4f4; }
.rice-status label { color: #111; font: 11px monospace; }
.aero-taskbar { padding: 0 3px; }
.aero-menu-app, .aero-menu-app button { border-radius: 0; box-shadow: none; }
.aero-menu-footer { border-top: 2px inset #eee; }
.rice-status-summary { color: #222; font-size: 11px; }
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

/* Chromebooks: a centered app launcher and white pill-shaped status shelf. */
.rice-status { background: #e4ecfa; color: #344e70; border: 1px solid transparent; border-radius: 22px; padding: 5px 7px; box-shadow: none; }
.rice-status:hover, .rice-status:focus { background: #c9dbf7; border: 1px solid #8dabe2; }
.rice-status label { color: #31466a; font-size: 11px; }
.chrome-launcher { background: #f8faff; border: 1px solid #c8d6ed; border-radius: 23px; color: #27364e; box-shadow: 0 8px 16px rgba(20,47,80,.12); }
.chrome-launcher .aero-menu-heading { font-size: 24px; color: #213d6f; }
.chrome-launcher .aero-menu-search { background: #eaf0fb; border: 1px solid #d5e0f0; border-radius: 21px; padding: 10px 15px; }
.chrome-launcher .ten-tile { border-radius: 18px; border: 1px solid transparent; background: #eef3ff; color: #2c4b76; box-shadow: none; padding: 8px 5px; }
.chrome-launcher .ten-tile:hover, .chrome-launcher .ten-tile:focus { background: #d9e6ff; border-color: #b0c8ee; }
.chrome-launcher .aero-menu-app { color: #3c557b; border-radius: 11px; padding: 8px 10px; }
.chrome-launcher-settings { background: #edf4ff; border: 0; border-radius: 18px; padding: 7px; box-shadow: none; }
.rice-status-summary { color: #486087; font-size: 11px; }
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

/* Frutiger Aero: high-key refractive glass, organically rounded controls. */
.rice-status { background-image: linear-gradient(#f8ffff, #c1f7e9 53%, #65d1d5); color: #07607d; border: 1px solid #86dadb; border-radius: 13px; box-shadow: inset 0 1px #fff; padding: 5px 7px; }
.rice-status:hover, .rice-status:focus { background-image: linear-gradient(#fff, #adfce1); border-color: #2f9fc1; }
.rice-status label { color: #07607d; font-size: 11px; font-weight: bold; }
.aero-menu-app { border-radius: 12px; }
.aero-menu-search { border-radius: 17px; border: 1px solid #71c8d2; background: #f6fffb; }
.aero-menu-power { background-image: linear-gradient(#fff, #78dfae); color: #096e7a; border-radius: 12px; border-color: #48bcad; }
.rice-status-summary { color: #076e83; font-size: 11px; font-weight: bold; }

.aqua-dashboard { background-image: linear-gradient(to bottom, #fafffe, #d4ffeb 55%, #b1eaf2); border: 2px solid #73cad8; border-radius: 22px; box-shadow: 0 4px 14px rgba(4,92,128,.22); }
.aqua-dashboard .aero-menu-heading { color: #087d93; font-size: 27px; font-weight: bold; }
.aqua-dashboard .aero-menu-sub { color: #118f9c; font-size: 12px; font-weight: bold; }
.aqua-dashboard .aero-menu-search { background: #faffff; border: 1px solid #87d6e0; border-radius: 20px; padding: 10px 12px; color: #0c627d; }
.aqua-dashboard .aero-menu-app { background: rgba(255,255,255,.45); border: 1px solid transparent; border-radius: 12px; color: #075a75; }
.aqua-dashboard .aero-menu-app:hover { background: #efffff; border-color: #72d3da; }
.aqua-shortcut { border-radius: 18px; border: 1px solid #a9ede7; background-image: linear-gradient(#fff, #d4fbec 55%, #a8e4eb); box-shadow: inset 0 1px #fff; color: #0d7283; padding: 9px; }
.aqua-shortcut:hover, .aqua-shortcut:focus { background-image: linear-gradient(#fff, #93e4cf); border-color: #27a8c4; }
.aqua-gear { border-radius: 18px; background: #d8fff4; border: 1px solid #8fdddf; padding: 5px; }
""",
}


# RiceBowl 0.9: these are complete profile-specific widget designs, rather
# than recolors of the common Aero shell. Keep the CSS local to each profile;
# macOS has its own unchanged implementation.
DETAIL_CSS = {
    "winxp": b"""
/* XP Luna Blue: molded plastic, tight 40px bar and one sky-blue tray. */
.aero-taskbar {
  background-image: linear-gradient(to bottom, #6daeff 0%, #3168db 12%,
    #2456cc 56%, #1944aa 89%, #1642a6 100%);
  border-top: 1px solid #93c7ff; border-bottom: 1px solid #102c78;
  color: white; padding: 0 2px; min-height: 32px;
}
.aero-start {
  background-image: linear-gradient(to bottom, #9fe985 0%, #4cae32 30%,
    #258c20 68%, #14771d 92%, #13721a 100%);
  border: 1px solid #a1ef7e; border-bottom: 2px solid #0a5b1c;
  border-radius: 0 16px 16px 0; color: white;
  font-size: 15px; font-weight: bold; font-style: italic;
  padding: 1px 16px 1px 5px;
  box-shadow: inset 0 1px rgba(255,255,255,.55), 1px 1px 2px #133581;
}
.aero-start:hover, .aero-start:focus { background-image: linear-gradient(#b7ffa1, #56bb40 40%, #1a8a23); }
.aero-start:active { background-image: linear-gradient(#125e15, #348f2e 80%, #78ce64); }
.aero-task {
  background-image: linear-gradient(#5c9dec, #2b70d9 49%, #1b5ac4);
  border: 1px solid #70a8f5; border-bottom: 1px solid #16459f;
  border-radius: 4px; color: white; padding: 3px 8px;
  box-shadow: inset 0 1px rgba(255,255,255,.22);
}
.aero-task-active {
  background-image: linear-gradient(#1750ba, #2c66ca 55%, #306ad3);
  border: 1px solid #0b3d99; border-top: 2px solid #0b347c;
}
.aero-pin { background: transparent; border: 1px solid transparent; box-shadow: none; padding: 2px; }
.aero-pin:hover, .aero-pin:focus { background: #528ae0; border-color: #89b7f7; }
.luna-tray {
  background-image: linear-gradient(#52b6f3 0%, #168bd5 24%, #0e7bca 68%, #1176c2);
  border-left: 1px solid #8ad3ff; border-top: 1px solid #8dd9ff;
  padding: 1px 4px 0 7px; min-height: 32px;
}
.luna-tray .rice-status, .luna-tray .aero-quick, .luna-tray .aero-desktop {
  background: transparent; border: 1px solid transparent; box-shadow: none;
  color: #fff; border-radius: 2px; padding: 2px 3px;
}
.luna-tray .rice-status:hover, .luna-tray .aero-quick:hover,
.luna-tray .aero-desktop:hover { background: #54b5ed; border-color: #93d8ff; }
.luna-tray .rice-status label { color: #fff; font-size: 10px; font-weight: normal; }
.aero-time { background: transparent; color: #fff; border: 0; box-shadow: none;
  font-size: 12px; font-weight: normal; padding: 2px 5px; }
.luna-menu { background: #fff; border: 2px solid #1b55bd;
  border-radius: 8px 8px 0 0; box-shadow: 1px 2px 7px rgba(11,35,98,.42); }
.luna-user {
  background-image: linear-gradient(#76aaff 0%, #3478dd 28%, #1555bd 74%, #1042a5);
  border-bottom: 2px solid #e6a34e; padding: 6px 10px; min-height: 53px;
}
.luna-user-name { color: #fff; font-size: 18px; font-weight: bold;
  text-shadow: 1px 1px #113d91; }
.luna-avatar { background: #fff; border: 2px solid #dfedff;
  border-radius: 4px; padding: 1px; box-shadow: 0 1px #164896; }
.luna-apps { background: #fff; padding: 4px 5px 5px; }
.luna-apps .aero-menu-search { border: 1px solid #7f9db9; border-radius: 0;
  min-height: 28px; padding: 4px 7px; }
.luna-program { background: transparent; color: #202020;
  border: 1px solid transparent; border-radius: 0; min-height: 28px;
  padding: 3px 5px; box-shadow: none; font-size: 12px; }
.luna-program:hover, .luna-program:focus { background: #316ac5; color: #fff;
  border-color: #316ac5; }
.luna-featured { min-height: 43px; padding: 4px 5px; }
.luna-program-category { font-size: 12px; font-weight: bold; color: #173a6e; }
.luna-program:hover .luna-program-category, .luna-program:focus .luna-program-category { color: #fff; }
.luna-empty { color: #56708b; font-size: 12px; }
.luna-apps separator { background: #a7bddb; min-height: 1px; }
.luna-all-programs {
  background: #fff; color: #1e3351; border: 1px solid transparent;
  border-top: 1px solid #b0c3da; border-radius: 0; min-height: 35px;
  font-weight: bold; padding: 5px; box-shadow: none;
}
.luna-all-programs:hover, .luna-all-programs:focus { background: #316ac5; color: #fff; }
.luna-places {
  background: #d3e5fa; border-left: 1px solid #91b3e4; padding: 5px 3px 5px 5px;
}
.luna-place {
  background: transparent; border: 1px solid transparent; box-shadow: none;
  color: #183e78; border-radius: 0; padding: 1px 5px;
  min-height: 25px; font-weight: bold; font-size: 11px;
}
.luna-place:hover, .luna-place:focus { background: #316ac5; color: #fff;
  border-color: #316ac5; }
.luna-place:disabled { color: #4d6b91; }
.luna-places separator { background: #9dbce6; min-height: 1px; }
.luna-footer {
  background-image: linear-gradient(#4186e2, #1254bf 44%, #1645a8);
  border-top: 1px solid #f6ad47; min-height: 43px; padding: 4px 8px;
}
.luna-power { border-radius: 3px; color: #fff; font-weight: bold;
  font-size: 11px; padding: 3px 6px; box-shadow: inset 0 1px rgba(255,255,255,.65); }
.luna-logoff { background-image: linear-gradient(#ffda6e, #c8861c);
  border: 1px solid #ffd47c; }
.luna-shutdown { background-image: linear-gradient(#ff856e, #c93d2c);
  border: 1px solid #ffae9a; }
.luna-power:hover, .luna-power:focus { border-color: #fff; color: #fff; }
.luna-logoff:hover { background: #e8aa38; }
.luna-shutdown:hover { background: #ed5944; }
.luna-power:disabled { opacity: .5; }
/* Gtk.Menu is a separate popup window, not a descendant of .luna-menu. */
menu.luna-popup { background: #f9fbff; color: #1a345b; border: 1px solid #2e65b0;
  border-radius: 0; padding: 3px; box-shadow: 2px 3px 7px rgba(9,38,91,.3); }
menu.luna-popup menuitem { background: transparent; border: 1px solid transparent;
  border-radius: 0; min-height: 25px; padding: 3px 9px; color: #1a345b; }
menu.luna-popup menuitem label { color: #1a345b; font-size: 12px; }
menu.luna-popup menuitem:hover, menu.luna-popup menuitem:selected,
menu.luna-popup menuitem:focus { background: #316ac5; border-color: #1a55a0; color: #fff; }
/* Direct children only: selected category labels must not recolor their submenu. */
menu.luna-popup menuitem:hover > box > label,
menu.luna-popup menuitem:selected > box > label,
menu.luna-popup menuitem:focus > box > label { color: #fff; }
menu.luna-popup menuitem:disabled label { color: #6c7e95; }
menu.luna-popup separator { background: #b6c9df; min-height: 1px; margin: 3px 5px; }
menu.luna-popup arrow { color: #315b94; }
menu.luna-popup menuitem:hover arrow, menu.luna-popup menuitem:selected arrow { color: #fff; }
""",
    "winclassic": b"""
/* 98/2000: no gradients, no glass, squared pixel-like geometry. */
.aero-taskbar { background: #c0c0c0; border-top: 2px solid #fff;
  border-bottom: 1px solid #4d4d4d; padding: 2px 4px; min-height: 34px; }
.aero-start { background: #c0c0c0; border: 2px outset #fff; border-radius: 0;
  color: #101010; box-shadow: none; font-weight: bold; padding: 2px 5px; }
.aero-task { background: #c0c0c0; border: 2px outset #fff; border-radius: 0;
  box-shadow: none; color: #151515; }
.aero-task-active { background: #b0b0b0; border: 2px inset #fff; }
.aero-pin, .rice-status, .aero-quick { border: 2px outset #fff; border-radius: 0;
  background: #c0c0c0; box-shadow: none; color: #111; padding: 2px; }
.aero-time { border: 2px inset #fff; border-radius: 0; background: #c0c0c0;
  color: #111; font-family: monospace; padding: 2px 6px; }
.classic-menu { background: #c0c0c0; border: 2px outset #fff; }
.classic-brand { background: #000080; border-right: 1px solid #6e6e6e; }
.classic-brand-label { color: white; font-size: 15px; font-weight: bold; }
.classic-menu-list { background: #c0c0c0; padding: 3px 2px; }
.classic-menu-item { color: #111; background: #c0c0c0; border: 0;
  border-radius: 0; box-shadow: none; min-height: 35px;
  padding: 5px 9px; }
.classic-menu-item:hover, .classic-menu-item:focus {
  background: #000080; color: white; border-radius: 0; }
.classic-menu-list separator { background: #7e7e7e; min-height: 2px; }
.classic-menu-list .aero-menu-search { background: #fff;
  border: 2px inset #fff; border-radius: 0; padding: 5px; }
.classic-menu-list .aero-menu-app { border-radius: 0; }
.classic-menu-list .aero-menu-app:hover { background: #000080; color: #fff; }
menu { background: #c0c0c0; border: 2px outset #fff; }
menu menuitem { color: #111; padding: 5px 11px; }
menu menuitem:hover { background: #000080; color: #fff; }
/* Win98 refinement: keyboard-accessible dense controls, 28px taskbar rhythm. */
.aero-taskbar { min-height: 34px; padding: 0 2px; border-top: 2px solid #ffffff; }
.aero-start { min-height: 26px; min-width: 74px; padding: 1px 5px;
  border-width: 2px; font: bold 12px Sans; }
.aero-start:active, .aero-start:checked, .aero-start:focus {
  border-style: inset; background: #b9b9b9; }
.aero-task, .aero-pin { min-height: 25px; padding: 1px 5px; font-size: 11px; }
.aero-pin:active, .aero-pin:focus, .aero-task:focus { border-style: inset; }
.aero-task-overflow, .aero-quick, .aero-desktop { background: #c0c0c0;
  border: 2px outset #fff; border-radius: 0; padding: 1px 3px; }
.aero-task-overflow:active, .aero-quick:active, .aero-desktop:active {
  border-style: inset; background: #b1b1b1; }
.aero-time { font: 11px Sans; min-height: 19px; padding: 2px 7px; }
.rice-status { border: 0; padding: 1px 2px; }
.rice-status:hover, .rice-status:focus { border: 1px dotted #000080; padding: 0 1px; }
.classic-menu { border-style: solid; border-width: 2px;
  border-top-color: #ffffff; border-left-color: #ffffff;
  border-bottom-color: #404040; border-right-color: #404040; }
.classic-brand { background: #000080; border: 0; min-width: 27px; }
.classic-brand-label { font: bold 16px Sans; color: #ffffff; }
.classic-menu-list { padding: 2px 3px; min-width: 225px; }
.classic-menu-item { min-height: 30px; padding: 3px 6px; font: 12px Sans;
  border: 1px solid transparent; border-radius: 0; box-shadow: none;
  text-shadow: none; }
.classic-menu-item:hover, .classic-menu-item:focus, .classic-menu-item:checked {
  background: #000080; color: #ffffff; border-color: #000080; }
.classic-menu-item:disabled { color: #777777; text-shadow: 1px 1px #fff; }
.classic-menu-item image { margin-right: 3px; }
.classic-chevron { font-size: 8px; }
.classic-menu-list separator { min-height: 1px; margin: 2px 4px;
  background: #808080; border-bottom: 1px solid #ffffff; }
.classic-menu .aero-menu-search { margin: 4px 5px; padding: 3px;
  border-style: inset; border-width: 2px; }
.classic-menu menuitem, menu menuitem { min-height: 23px; padding: 3px 8px; }
.classic-menu menuitem:focus, menu menuitem:focus { background: #000080; color: #fff; }
.aero-control-root { padding: 8px; border: 2px outset #ffffff; }
.classic-control-caption { background: #000080; color: #ffffff;
  min-height: 26px; padding: 2px 3px; font: bold 12px Sans; }
.classic-control-caption label { color: #ffffff; font-weight: bold; }
.classic-control-close { min-width: 20px; min-height: 20px; padding: 0 3px;
  background: #c0c0c0; color: #000; border: 2px outset #fff;
  border-radius: 0; font-weight: bold; box-shadow: none; }
.classic-control-close:active { border-style: inset; }
.classic-control-close label { color: #000; }
.aero-control-root .aero-menu-heading { color: #000; font: bold 14px Sans; }
.aero-control-root .aero-menu-sub { color: #333; font: 11px Sans; }
.aero-control-quick { font: 11px Sans; border: 2px outset #ffffff; }
.aero-control-quick:active { border-style: inset; background: #b6b6b6; }
.aero-control-quick:focus { outline: 1px dotted #000080; outline-offset: -4px; }
.classic-control-grid { background: #ffffff; border: 2px inset #ffffff;
  padding: 6px; }
.classic-control-grid .aero-control-quick { background: #ffffff; border: 1px solid transparent;
  padding: 7px 3px; min-height: 66px; min-width: 82px; }
.classic-control-grid .aero-control-quick label { color: #111111; font-size: 10px; }
.classic-control-grid .aero-control-quick:hover,
.classic-control-grid .aero-control-quick:focus { background: #000080; color: #ffffff;
  border: 1px dotted #ffffff; }
.classic-control-grid .aero-control-quick:hover label,
.classic-control-grid .aero-control-quick:focus label { color: #ffffff; }
""",
    "chromeos": b"""
/* Modern ChromeOS: separated launcher, centered app shelf and status capsule. */
.aero-taskbar { background: rgba(228,236,252,.94); border-top: 1px solid #e8edff;
  color: #283852; padding: 5px 13px; min-height: 48px; }
.aero-start { background: rgba(255,255,255,.78); border: 1px solid #c4d4f0;
  color: #4568b4; border-radius: 26px; box-shadow: 0 1px 3px rgba(35,64,115,.15);
  padding: 5px; }
.chrome-app-shelf { background: rgba(247,249,255,.88); border: 1px solid #c8d7ee;
  border-radius: 27px; padding: 3px 12px; }
.chrome-app-shelf .aero-pin, .chrome-app-shelf .aero-task {
  background: rgba(248,249,255,.6); border: 1px solid transparent;
  border-radius: 25px; padding: 5px; min-width: 33px; min-height: 30px;
  color: #3b4c71; box-shadow: none; }
.chrome-app-shelf .aero-task-active { border-color: #91a9eb;
  border-bottom: 3px solid #4b82e4; background: #e0e9ff; }
.chrome-status-pill { border: 1px solid #c3d1ea; border-radius: 25px;
  background: rgba(248,250,255,.90); padding: 3px 9px; }
.chrome-status-pill .rice-status, .chrome-status-pill .aero-quick,
.chrome-status-pill .aero-time, .chrome-status-pill .aero-desktop {
  background: transparent; border: 1px solid transparent; border-radius: 18px;
  color: #314365; box-shadow: none; padding: 5px 6px; }
.chrome-status-pill .rice-status:hover, .chrome-status-pill .aero-quick:hover {
  background: #d6e3f9; border-color: #bfd1ed; }
.chrome-status-pill .aero-time { font-size: 11px; font-weight: bold; }
.chrome-launcher {
  background-image: linear-gradient(to bottom, rgba(252,253,255,.98), rgba(236,242,255,.98));
  border: 1px solid #b9c8e9; border-radius: 24px; color: #273b62;
  box-shadow: 0 4px 16px rgba(40,68,120,.20); }
.chrome-launcher .aero-menu-heading { color: #2c4276; font-size: 20px; }
.chrome-launcher .aero-menu-search { background: rgba(248,250,255,.97);
  border: 2px solid #8caafa; border-radius: 24px; padding: 12px 15px; }
.chrome-launcher .ten-tile { background: transparent; color: #31456d;
  border: 1px solid transparent; border-radius: 20px; padding: 6px 3px;
  box-shadow: none; }
.chrome-launcher .ten-tile:hover, .chrome-launcher .ten-tile:focus {
  background: #dbe6ff; border-color: #adc6ef; }
.chrome-launcher .ten-tile-label { color: #2c3c61; font-size: 11px; }
.chrome-launcher-settings { background: #e9effd; color: #3453a4;
  border-radius: 22px; border: 1px solid #d3dff4; }
""",
    "frutiger": b"""
/* Aqua World: independent 2005-2012 eco-futurist lens/glass, never Win7 cobalt.
   These GTK-owned gradients retain their shape without a blur compositor. */
.aero-taskbar.frutiger-taskbar {
  background-image: linear-gradient(to bottom, #efffff 0%, #b3fff1 11%,
    #7fe5e5 43%, #2fbdcb 47%, #26abb8 81%, #0f87aa 100%);
  border-top: 2px solid #ffffff; border-bottom: 2px solid #0c86a8;
  color: #064e69; padding: 3px 9px; min-height: 49px;
  box-shadow: inset 0 1px #ffffff;
}
.aero-start.frutiger-start {
  background-image: linear-gradient(to bottom, #ffffff 0%, #f0ffff 26%,
    #92ffe0 45%, #42d1a3 53%, #1ba6ac 100%);
  color: #07526b; border: 2px solid #f7ffff; border-radius: 28px;
  box-shadow: inset 0 2px rgba(255,255,255,.95), 0 1px 5px rgba(8,91,118,.36);
  padding: 1px 15px 1px 4px; min-height: 40px; font-weight: bold;
}
.frutiger-start:hover, .frutiger-start:focus {
  background-image: linear-gradient(#ffffff, #cefff1 40%, #64e6d8 52%, #1ab3bf);
  border-color: #ffffff;
}
.frutiger-taskbar .aero-pin, .frutiger-taskbar .aero-task {
  background-image: linear-gradient(to bottom, #f7ffff, #c2fff1 35%,
    #8fe5e7 52%, #46c4d3);
  border: 1px solid #eaffff; border-bottom: 2px solid #1c94ac;
  border-radius: 15px; color: #074f6c; padding: 4px 9px;
  box-shadow: inset 0 1px #fff, 0 1px 3px rgba(6,81,116,.20);
}
.frutiger-taskbar .aero-pin:hover, .frutiger-taskbar .aero-task:hover,
.frutiger-taskbar .aero-pin:focus, .frutiger-taskbar .aero-task:focus {
  background-image: linear-gradient(#fff, #d9ffef 36%, #8cf5d1 52%, #3fd2c8);
  border-color: #fff; box-shadow: inset 0 1px #fff, 0 0 6px #d2fff7;
}
.frutiger-taskbar .aero-task-active {
  background-image: linear-gradient(#ffffee, #dfff92 41%, #a8ec49 53%, #53bb55);
  border-color: #faffcf; border-bottom-color: #388c5e;
}
.frutiger-tray {
  background-image: linear-gradient(to bottom, rgba(248,255,255,.95),
    rgba(175,250,230,.87) 48%, rgba(78,205,207,.91));
  border: 1px solid rgba(249,255,255,.98); border-radius: 23px;
  padding: 2px 5px; box-shadow: inset 0 1px #fff;
}
.frutiger-tray .rice-status, .frutiger-tray .aero-quick,
.frutiger-tray .aero-time, .frutiger-tray .aero-desktop {
  background: transparent; border: 1px solid transparent; border-radius: 15px;
  box-shadow: none; color: #075571; padding: 4px 6px;
}
.frutiger-tray .rice-status label { color: #075571; font-weight: bold; }
.frutiger-tray .rice-status:hover, .frutiger-tray .aero-quick:hover,
.frutiger-tray .aero-desktop:hover { background: #dbfff1; border-color: #6ccfc5; }
.aqua-dashboard {
  background-image: linear-gradient(to bottom, #fbffff 0%,
    #e9fff9 27%, #d5fcf3 49%, #a4e4e9 100%);
  border: 3px solid #f4ffff; border-radius: 27px;
  box-shadow: inset 0 2px #fff, inset 0 -2px #54b6cd,
    0 6px 18px rgba(5,86,112,.38);
  color: #08506c; padding: 10px;
}
.aqua-window { background: #b9f0eb; }
.aqua-hero {
  background-image: linear-gradient(to bottom, #ffffff, #e4fff9 45%, #b7efef 46%, #d2fff5);
  border: 1px solid #8bcedc; border-bottom-color: #56b7cf; border-radius: 21px;
  box-shadow: inset 0 2px #fff; padding: 7px 10px;
}
.aqua-hero-orb { background: #e8fff7; border: 1px solid #fcffff;
  border-radius: 28px; padding: 3px; box-shadow: 0 1px 4px rgba(4,99,132,.25); }
.aqua-dashboard .aero-menu-heading { color: #096588; font-size: 26px;
  font-weight: bold; text-shadow: 0 1px #fff; }
.aqua-dashboard .aero-menu-sub { color: #087d8a; font-size: 12px; font-weight: bold; }
.aqua-status-caption { color: #136b7b; font-size: 10px; }
.aqua-dashboard .aero-menu-search {
  border: 2px solid #69b9d0; color: #075878; background: #f9ffff;
  border-radius: 22px; padding: 9px 14px; box-shadow: inset 0 1px #fff;
}
.aqua-dashboard .aero-menu-search:focus { border-color: #1a8fc3;
  box-shadow: 0 0 4px rgba(23,155,202,.45); }
.aqua-shortcuts { background-image: linear-gradient(rgba(255,255,255,.89),
    rgba(207,251,235,.64)); border: 1px solid rgba(138,211,208,.62);
  border-radius: 19px; padding: 4px; }
.aqua-shortcut { background-image: linear-gradient(#fff 0%, #eefff9 30%,
  #bdf7ed 45%, #75dcd7 100%); border: 1px solid #83d8db;
  border-bottom-color: #42acc5; border-radius: 16px; color: #075779;
  min-height: 64px; padding: 3px 9px;
  box-shadow: inset 0 2px #fff, 0 1px 3px rgba(13,111,136,.20); }
.aqua-shortcut label { color: #075779; font-size: 12px; font-weight: bold; }
.aqua-shortcut:hover, .aqua-shortcut:focus {
  background-image: linear-gradient(#fff, #e8ffec 35%, #9ff2b4 53%, #56d2c3);
  border-color: #1b9cad; box-shadow: inset 0 1px #fff, 0 0 5px #cbfff1;
}
.aqua-tabs { background: rgba(244,255,250,.65); border: 1px solid #84d6db;
  border-radius: 20px; padding: 4px; }
.aqua-tab { background-image: linear-gradient(#faffff, #dcfff8 48%, #90dce1);
  border: 1px solid #93d6da; border-radius: 16px; color: #076584;
  padding: 9px 13px; box-shadow: inset 0 1px #fff; font-weight: bold; }
.aqua-tab:checked { background-image: linear-gradient(#f8ffcd 0%, #dfff8b 45%,
  #91e44a 51%, #65c936); color: #19506c; border-color: #75c449;
  box-shadow: inset 0 1px #ffffeb; }
.aqua-tab:hover, .aqua-tab:focus { border-color: #259ebd; }
.aqua-section {
  background-image: linear-gradient(to right, rgba(255,255,255,.86),
    rgba(219,255,244,.57)); border-top: 1px solid #faffff;
  border-bottom: 1px solid #86ccd5; border-radius: 6px;
  padding: 4px 9px;
}
.aqua-section-title { color: #08627f; font-size: 11px; font-weight: bold;
  letter-spacing: .5px; }
.aqua-section-hint { color: #417c87; font-size: 10px; }
.aqua-dashboard scrolledwindow, .aqua-dashboard viewport,
.aqua-dashboard flowbox, .aqua-dashboard flowboxchild { background: transparent; }
.aqua-app-grid { padding: 1px 3px 6px; }
.aqua-app-tile { background-image: linear-gradient(#ffffff, #f9ffff 39%,
  #e0fcf5 52%, #b1e8e9); border: 1px solid #88d0d8; border-radius: 15px;
  box-shadow: inset 0 1px #fff, 0 1px 3px rgba(8,96,130,.17);
  min-width: 125px; min-height: 84px; padding: 6px 5px; color: #075778; }
.aqua-app-tile label { color: #064b66; font-weight: bold; font-size: 12px; }
.aqua-app-tile:hover, .aqua-app-tile:focus {
  background-image: linear-gradient(#fff, #f0ffdf 40%, #bbf0ac 54%, #79d8be);
  border-color: #38acaf; box-shadow: inset 0 2px #fff, 0 0 6px #dcfff4; }
.aqua-app-tile:active { background-image: linear-gradient(#defdd2, #91df99);
  border-color: #429b83; }
.aqua-app-tile:disabled { opacity: .55; }
.aqua-empty { color: #11677b; padding: 16px; font-weight: bold; }
.aqua-place { background-image: linear-gradient(#fff, #d7fff4 42%, #a5e9e5);
  border: 1px solid #8bd5d8; border-radius: 15px; color: #075779;
  min-height: 39px; padding: 9px; box-shadow: inset 0 1px #fff; }
.aqua-place:hover, .aqua-place:focus { background-image: linear-gradient(#fff,
  #d0ffdc 45%, #92e9bf); border-color: #32abc5; color: #075479; }
.aqua-footer { background-image: linear-gradient(rgba(255,255,255,.81),
  rgba(167,240,224,.74)); border: 1px solid #8bd9d8;
  border-radius: 17px; padding: 5px 9px; box-shadow: inset 0 1px #fff; }
.aqua-caption { color: #08718a; font-weight: bold; font-size: 11px; }
.aqua-footer-action, .aqua-gear { background-image: linear-gradient(#fff, #dcfff4 42%, #97e4dd);
  border: 1px solid #83d8d6; border-radius: 17px; padding: 6px;
  box-shadow: inset 0 1px #fff; }
.aqua-footer-action:hover, .aqua-gear:hover,
.aqua-footer-action:focus, .aqua-gear:focus {
  background-image: linear-gradient(#fff, #d0ffe8 42%, #7ae7c8);
  border-color: #34a6b7; }
.aqua-footer-action:disabled, .aqua-place:disabled { color: #4f848c; opacity: .72; }
.aero-control-root.aqua-control-root {
  background-image: linear-gradient(#fbffff 0%, #ecfff7 39%, #c4f7ed 67%, #a6e8e7);
  border: 2px solid #b4eef0; border-radius: 23px; padding: 12px;
  box-shadow: inset 0 2px #fff, 0 4px 12px rgba(7,97,122,.3);
  color: #07536e;
}
.aqua-control-hero { background-image: linear-gradient(#ffffff, #d9fff4 54%, #9bdfeb);
  border: 1px solid #83ced8; border-radius: 18px; padding: 7px 10px;
  box-shadow: inset 0 1px #fff, 0 1px 3px rgba(6,95,132,.13); }
.aqua-control-root .aero-menu-heading { color: #08617e; font-size: 22px;
  font-weight: bold; text-shadow: 0 1px #fff; }
.aqua-control-root .aero-menu-sub { color: #1c697c; font-weight: bold;
  font-size: 12px; }
.aqua-control-root .aero-control-quick {
  background-image: linear-gradient(#fff, #d8fff5 43%, #8adfe4);
  border: 1px solid #84ccda; border-radius: 13px; padding: 9px 11px;
  color: #075775; box-shadow: inset 0 1px #fff;
}
.aqua-control-root .aero-control-quick:hover,
.aqua-control-root .aero-control-quick:focus {
  background-image: linear-gradient(#fff, #dfffdf 45%, #83e2c0);
  border-color: #239bb8;
}
.aqua-control-root .rice-hardware-panel {
  background-image: linear-gradient(#ffffff, #eafff8 34%, #d0fbf2);
  border: 1px solid #81c9d1; border-radius: 16px; padding: 10px;
  box-shadow: inset 0 1px #fff;
}
.aqua-control-root .rice-status-summary { color: #0c5d76; font-size: 12px;
  font-weight: bold; }
.aqua-control-root .rice-hardware-panel scale trough {
  background: #c1eeec; border: 1px solid #82cbd3; border-radius: 9px;
}
.aqua-control-root .rice-hardware-panel scale highlight,
.aqua-control-root .rice-hardware-panel levelbar block.filled {
  background-image: linear-gradient(#f7ffbb, #8cdd47); border-radius: 7px;
}
.aqua-control-root .aqua-control-close, .aqua-control-root .aqua-control-back {
  color: #075b70; border-radius: 12px; padding: 5px 12px;
  border: 1px solid #87cad4; background-image: linear-gradient(#ffffff, #d9fff4 48%, #9bdde7);
  box-shadow: inset 0 1px #ffffff;
}
.aqua-control-root .aqua-control-close { font-size: 19px; font-weight: bold; min-width: 32px; }
.aqua-control-root .aqua-control-breadcrumb { color: #075c7c; font-size: 12px; font-weight: bold; }
.aqua-control-root .aqua-control-search { color: #075371; background: #fbffff;
  border: 1px solid #85ced9; border-radius: 16px; padding: 7px 11px; }
.aqua-control-root scrolledwindow, .aqua-control-root viewport,
.aqua-control-root stack, .aqua-control-root grid { background: transparent; }
.aqua-control-root .aqua-control-grid { padding: 3px 1px 6px; }
.aqua-control-root .aqua-control-category {
  background-image: linear-gradient(to bottom, #ffffff, #f1fffa 36%, #caf7e4 75%, #a0dbdb);
  color: #07576d; border: 1px solid #8acbd4; border-radius: 17px;
  padding: 10px 6px; box-shadow: inset 0 2px #fff, 0 2px 4px rgba(12,90,119,.12);
  min-height: 102px;
}
.aqua-control-root .aqua-control-category-name { color: #076480;
  font-size: 12px; font-weight: bold; }
.aqua-control-root .aqua-control-task {
  background-image: linear-gradient(to bottom, #ffffff, #f4fffa 43%, #d4f8ed);
  border: 1px solid #9dcfd4; border-radius: 13px; color: #065a75;
  padding: 9px 11px; box-shadow: inset 0 1px #fff;
}
.aqua-control-root .aqua-control-task-title { color: #075b73; font-size: 12px; font-weight: bold; }
.aqua-control-root .aqua-control-task-note { color: #376d75; font-size: 10px; }
.aqua-control-root .aqua-control-intro { color: #236778; font-size: 12px; padding: 7px 4px; }
.aqua-control-root .aqua-control-detail-title { color: #066889; font-size: 19px;
  font-weight: bold; padding: 7px 4px 2px; }
.aqua-control-root .aqua-control-chevron { color: #0b8fab; font-size: 22px; font-weight: bold; }
.aqua-control-root .aqua-control-live { background-image: linear-gradient(to bottom, #faffff, #e8fff7 42%, #c8f1ed);
  border: 1px solid #90cdd4; border-radius: 14px; padding: 8px 12px;
  box-shadow: inset 0 1px #fff; }
.aqua-control-root .aqua-control-live .rice-control-detail { color: #175b72;
  font-weight: bold; font-size: 11px; }
.aqua-control-root .aqua-control-live scale trough { background: #c7eff0;
  border: 1px solid #8bcdd2; border-radius: 8px; min-height: 8px; }
.aqua-control-root .aqua-control-live scale highlight,
.aqua-control-root .aqua-control-live levelbar block.filled {
  background-image: linear-gradient(#f6ffc2, #9bde47); border-radius: 8px;
}
.aqua-control-root .aqua-control-launch, .aqua-control-root .rice-mute {
  color: #075371; background-image: linear-gradient(#ffffff, #c6fae6 57%, #83d9cc);
  border: 1px solid #69bfd1; border-radius: 12px; padding: 8px;
}
.aqua-control-root .rice-mute:checked { background-image: linear-gradient(#e7ffc4, #8fd469);
  border-color: #3f9e77; }
.aqua-control-root .aqua-control-unavailable { color: #924f2f; font-weight: bold;
  padding: 9px; border: 1px solid #eccdb3; border-radius: 10px; background: #fff6ea; }
.aqua-control-root .aqua-control-live-label { color: #075c7a; font-weight: bold; }
.aqua-control-root .aqua-control-probe-result {
  color: #185d6c; background: #f6fffc; border: 1px solid #acd9d7;
  border-radius: 11px; padding: 10px 12px; font-size: 12px;
}
.aqua-control-root .aqua-control-probe-error {
  color: #8b492e; background: #fff6e9; border-color: #eac7ad;
}
popover.aqua-flyout > contents {
  background-image: linear-gradient(to bottom, #faffff, #e8fff6 44%, #ace6e6);
  color: #07536e; border: 2px solid #94d4df; border-radius: 20px;
  box-shadow: inset 0 2px #fff, 0 4px 15px rgba(5,77,113,.26);
}
.aqua-flyout .aqua-flyout-root { padding: 12px; }
.aqua-flyout .aqua-flyout-heading {
  background-image: linear-gradient(#ffffff, #d8fff4 45%, #99e0e3);
  border-radius: 13px; border: 1px solid #a1dbe1; padding: 7px;
  box-shadow: inset 0 1px #fff;
}
.aqua-flyout .aqua-flyout-title { color: #076682; font-weight: bold; font-size: 15px; }
.aqua-flyout .aqua-flyout-status { color: #175e6d; font-size: 12px; padding: 4px 6px; }
.aqua-flyout .aqua-flyout-more, .aqua-flyout .aqua-flyout-mute {
  color: #075874; background-image: linear-gradient(#ffffff, #e2fff7 42%, #9ce3dc);
  border-radius: 12px; border: 1px solid #7dc7d2; padding: 8px;
  box-shadow: inset 0 1px #fff;
}
.aqua-flyout .aqua-flyout-mute:checked { background-image: linear-gradient(#f5ffc5, #9edb69);
  border-color: #569e76; }
.aqua-flyout .aqua-flyout-more:hover, .aqua-flyout .aqua-flyout-mute:hover,
.aqua-flyout .aqua-flyout-more:focus, .aqua-flyout .aqua-flyout-mute:focus {
  border-color: #158dbb; background-image: linear-gradient(#ffffff, #dcffdb, #87dcc2);
}
.aqua-flyout scale trough { background: #d7f3ef; border-radius: 7px;
  border: 1px solid #8dcbd3; min-height: 8px; }
.aqua-flyout scale highlight { background-image: linear-gradient(#e5ffb0, #75cd5c);
  border-radius: 7px; }
.aqua-control-root .aqua-control-close:hover, .aqua-control-root .aqua-control-back:hover,
.aqua-control-root .aqua-control-category:hover, .aqua-control-root .aqua-control-task:hover,
.aqua-control-root .aqua-control-launch:hover { border-color: #249cb8;
  background-image: linear-gradient(#ffffff, #dfffdb 50%, #9be5be); }
.aqua-control-root .aqua-control-close:focus, .aqua-control-root .aqua-control-back:focus,
.aqua-control-root .aqua-control-search:focus, .aqua-control-root .aqua-control-category:focus,
.aqua-control-root .aqua-control-task:focus, .aqua-control-root .aqua-control-launch:focus {
  border: 2px solid #1588be; box-shadow: 0 0 0 2px rgba(255,255,255,.86);
}
""",
}

for _profile, _details in DETAIL_CSS.items():
    CSS[_profile] += _details


# Functional device controls inherit the native design language, including
# scale/progress tracks and stateful mute, not the generic GTK button defaults.
CONTROL_DETAIL_CSS = {
    "winxp": b"""
.rice-hardware-panel { background-image: linear-gradient(#ffffff, #e2efff);
  border: 1px solid #9dbce5; border-radius: 5px; padding: 10px; }
.rice-control-detail { color: #174a94; font-weight: bold; font-size: 11px; }
.rice-hardware-panel scale trough { background: #fff; border: 1px solid #7d9cbd;
  border-radius: 3px; min-height: 9px; }
.rice-hardware-panel scale highlight, .rice-hardware-panel levelbar block.filled {
  background-image: linear-gradient(#bdff76, #57b92d); border-radius: 2px; }
.rice-mute { background-image: linear-gradient(#fff, #cfe0f9);
  color: #204d88; border-radius: 4px; }
.rice-mute:checked { background: #357bd1; color: white; }
/* A real, centered XP category-view window. Only the Luna profile uses it. */
.luna-control-window { background: #ffffff; border: 3px solid #1953b7;
  color: #202020; }
.luna-control-caption { background-image: linear-gradient(to bottom,
  #77b1ff, #2f7bd8 35%, #1557be 75%, #1046ab);
  border-bottom: 1px solid #073b99; padding: 2px 7px; min-height: 28px;
  color: #ffffff; font-size: 12px; font-weight: bold; }
.luna-control-caption label { color: #ffffff; }
.luna-control-close { background-image: linear-gradient(#ffb58c, #d7472b);
  border: 1px solid #fff4d3; border-radius: 4px; min-width: 24px;
  min-height: 22px; padding: 0; color: white; box-shadow: inset 0 1px #ffefc8; }
.luna-control-close label { color: white; font: bold 17px Sans; }
.luna-control-close:hover { background: #f15b38; border-color: white; }
.luna-control-sidebar { background-image: linear-gradient(to right, #6595d4, #c7dafa);
  padding: 15px 12px; border-right: 1px solid #8ba9d5; }
.luna-control-side-group { background: #d7e6fa; border: 1px solid #7b9dcd;
  border-radius: 5px; padding: 10px; color: #194785; }
.luna-control-side-heading { color: #184788; font-size: 12px; font-weight: bold;
  border-bottom: 1px solid #99b6d9; padding-bottom: 5px; }
.luna-control-nav { background: transparent; color: #164990; border: 0;
  border-radius: 0; padding: 4px 2px; box-shadow: none; }
.luna-control-nav:hover, .luna-control-nav:focus { background: #c3d9f7;
  color: #102f70; text-decoration: underline; }
.luna-control-main { background: #ffffff; padding: 18px 20px; color: #333333; }
.luna-control-heading { color: #164eae; font-size: 19px; font-weight: bold; }
.luna-control-intro { color: #515151; font-size: 11px; }
.luna-control-search { background: #fff; color: #203959; border: 1px solid #88a8ce;
  border-radius: 2px; padding: 4px 7px; min-height: 28px; }
.luna-control-search:focus { border-color: #316ac5; box-shadow: 0 0 0 1px #bad1f3; }
.luna-control-category, .luna-control-applet, .luna-control-task {
  background: transparent; border: 1px solid transparent; border-radius: 2px;
  box-shadow: none; padding: 6px 5px; color: #1b3e75; }
.luna-control-task { padding: 9px 8px; }
.luna-control-category:hover, .luna-control-applet:hover, .luna-control-task:hover,
.luna-control-category:focus, .luna-control-applet:focus, .luna-control-task:focus {
  background: #edf5ff; border-color: #91b9ec; }
.luna-control-category:active, .luna-control-applet:active, .luna-control-task:active {
  background: #d2e5ff; border-color: #316ac5; }
.luna-control-category:focus, .luna-control-applet:focus, .luna-control-task:focus {
  box-shadow: inset 0 0 0 1px #d4e8ff; }
.luna-control-category:hover .luna-control-link, .luna-control-category:focus .luna-control-link,
.luna-control-task:hover .luna-control-link, .luna-control-task:focus .luna-control-link {
  text-decoration: underline; }
.luna-control-applet:disabled, .luna-control-task:disabled {
  opacity: .82; background: #f7f8fa; border-color: #e9edf3; }
.luna-control-applet:disabled label, .luna-control-task:disabled label { color: #586574; }
.luna-control-detail-header { background: #e6f0fd; border: 1px solid #b2cbe9;
  border-radius: 4px; padding: 9px; }
.luna-control-details, .luna-control-results { padding: 3px 0 10px; }
.luna-control-result-heading { background: #eaf2fd; color: #1b4e91;
  font-weight: bold; font-size: 12px; padding: 5px 8px;
  border-bottom: 1px solid #aac6e7; }
.luna-control-empty { color: #536c8a; font-style: italic; font-size: 12px; }
.luna-control-link { color: #164eae; font-size: 12px; font-weight: bold; }
.luna-control-explanation { color: #4c4c4c; font-size: 10px; font-weight: normal; }
.luna-control-summary { color: #325b91; font-size: 10px; }
.luna-control-sidebar .rice-control-detail { color: #254f85; font-size: 11px;
  font-weight: normal; }
.luna-control-sidebar scale trough { background: white; border: 1px solid #7b9bbd;
  border-radius: 2px; min-height: 8px; }
.luna-control-sidebar scale highlight { background: #4fa52d; }
.luna-control-sidebar .rice-mute { padding: 4px; }
""",
    "winclassic": b"""
.rice-hardware-panel { background: #c0c0c0; border: 2px inset #fff; border-radius: 0;
  padding: 6px; }
.rice-control-detail { color: #111; font-family: monospace; font-size: 11px; }
.rice-hardware-panel scale trough { background: white; border: 2px inset #fff;
  border-radius: 0; min-height: 8px; }
.rice-hardware-panel scale slider { background: #c0c0c0; border: 2px outset #fff;
  border-radius: 0; }
.rice-hardware-panel scale highlight, .rice-hardware-panel levelbar block.filled {
  background: #000080; border-radius: 0; }
.rice-mute { background: #c0c0c0; border: 2px outset #fff; border-radius: 0; box-shadow: none; }
.rice-mute:checked { border: 2px inset #fff; background: #888; color: #111; }

/* Separate 1998 shell descendants share the original bevel and focus grammar. */
.classic98-quicklaunch { border-left: 2px groove #f0f0f0; padding: 1px 3px; }
.classic98-quicklaunch .aero-pin, .classic98-desktop-quick {
  background: #c0c0c0; border: 1px solid transparent; border-radius: 0;
  box-shadow: none; padding: 2px; min-width: 23px; min-height: 22px; }
.classic98-quicklaunch .aero-pin:hover, .classic98-desktop-quick:hover {
  background: #dedede; border: 1px outset #f5f5f5; }
.classic98-quicklaunch .aero-pin:active, .classic98-desktop-quick:active {
  border: 1px inset #f5f5f5; background: #a9a9a9; }
.classic98-clock-button { background: #c0c0c0; border: 2px inset #fff;
  border-radius: 0; padding: 0; box-shadow: none; }
.classic98-control { background: #ffffff; color: #111; font-size: 11px; }
.classic98-control menubar { background: #c0c0c0; border-bottom: 1px solid #808080;
  box-shadow: inset 0 1px #fff; padding: 1px 3px; }
.classic98-control menuitem { border-radius: 0; padding: 3px 9px; }
.classic98-control menuitem:hover { background: #000080; color: white; }
.classic98-cp-address { background: #c0c0c0; border-bottom: 2px groove #f5f5f5;
  padding: 4px 6px; }
.classic98-control flowbox, .classic98-control flowboxchild,
.classic98-control scrolledwindow, .classic98-control viewport {
  background: #fff; border-radius: 0; box-shadow: none; }
.classic98-cp-item { min-width: 110px; min-height: 86px; padding: 6px;
  color: #111; border: 1px solid transparent; }
.classic98-cp-item:selected, .classic98-cp-item:focus {
  background: #000080; color: white; border: 1px dotted white; }
.classic98-cp-item:disabled { opacity: .47; }
.classic98-cp-status { background: #c0c0c0; border: 2px inset #f5f5f5;
  padding: 3px 6px; color: #111; }
.classic98-tray-popup { background: #c0c0c0; border: 2px outset #fff;
  border-radius: 0; box-shadow: none; padding: 7px; color: #111; }
.classic98-tray-title { background: #000080; padding: 2px 4px; }
.classic98-tray-title label { color: #fff; font-weight: bold; font-size: 11px; }
.classic98-tray-title button { color: #111; background: #c0c0c0;
  border: 2px outset #fff; border-radius: 0; padding: 0 5px; }
.classic98-tray-popup button { border-radius: 0; }
.classic98-tray-popup scale trough { background: #fff; border: 2px inset #fff;
  border-radius: 0; min-height: 8px; }
.classic98-tray-popup scale slider { background: #c0c0c0; border: 2px outset #fff;
  border-radius: 0; }
.classic98-tray-popup scale highlight, .classic98-tray-popup levelbar block.filled {
  background: #000080; border-radius: 0; }
.classic98-flyout menuitem:hover { background: #000080; color: white; }
.classic98-window-menu { background: #c0c0c0; border: 2px outset #fff;
  border-radius: 0; padding: 2px; }
.classic98-window-menu menuitem { border-radius: 0; padding: 3px 15px; color: #111; }
.classic98-window-menu menuitem:hover { background: #000080; color: white; }
.classic98-window-menu menuitem:disabled { color: #888; }
""",
    "chromeos": b"""
.rice-hardware-panel { background: #edf2ff; border: 1px solid #d4ddf1;
  border-radius: 19px; padding: 13px; }
.rice-control-detail { color: #3c4f77; font-size: 12px; }
.rice-hardware-panel scale trough { background: #ced9f0; border-radius: 9px;
  min-height: 8px; }
.rice-hardware-panel scale highlight, .rice-hardware-panel levelbar block.filled {
  background: #5e8cea; border-radius: 9px; }
.rice-mute { background: #fff; border: 1px solid #d4ddf0;
  border-radius: 20px; color: #435987; padding: 8px; }
.rice-mute:checked { background: #dae3ff; border-color: #8ea8e5; }
""",
    "frutiger": b"""
.rice-hardware-panel { background-image: linear-gradient(#faffff, #c4fff0 50%, #9fe4e8);
  border: 1px solid #68c5d2; border-radius: 17px; padding: 12px;
  box-shadow: inset 0 1px #fff; }
.rice-control-detail { color: #076b83; font-size: 12px; font-weight: bold; }
.rice-hardware-panel scale trough { background: #efffff; border: 1px solid #7dd8d1;
  border-radius: 11px; min-height: 10px; }
.rice-hardware-panel scale highlight, .rice-hardware-panel levelbar block.filled {
  background-image: linear-gradient(#e9ff9d, #80e33f);
  border-radius: 10px; }
.rice-mute { background-image: linear-gradient(#fff, #b3f8e4);
  color: #0b6a86; border: 1px solid #71c9d5; border-radius: 16px; padding: 8px; }
.rice-mute:checked { background-image: linear-gradient(#dcffc0, #69d85d); }
""",
}
for _profile, _detail in CONTROL_DETAIL_CSS.items():
    CSS[_profile] += _detail
