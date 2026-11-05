"""Windows 10 shell skin for RiceBowl's shared event-driven XFCE taskbar."""

from __future__ import annotations


APP_ID = "io.github.copypasteuser.RiceHub.TenShell"


def start_tiles(apps, pinned_ids: tuple[str, ...], *, limit: int = 6):
    """Real Gio apps only; prefer pins, then familiar desktop app categories.

    No fabricated Windows Store, mail or weather tiles. The same selection is
    stable across restarts and does not mutate the user's saved taskbar pins.
    """
    available = tuple(apps)
    selected = []
    ids = set()

    def add(app):
        identifier = app.get_id()
        if identifier and identifier not in ids:
            selected.append(app)
            ids.add(identifier)

    for identifier in pinned_ids:
        for app in available:
            if app.get_id() == identifier:
                add(app)
                break
    for keyword in ("file manager", "browser", "settings", "terminal",
                    "editor", "calculator", "music", "image"):
        for app in available:
            label = (app.get_display_name() or app.get_name() or "").casefold()
            if keyword in label:
                add(app)
                break
    for app in available:
        if len(selected) >= limit:
            break
        add(app)
    return tuple(selected[:limit])


CSS = b"""
/* Windows 10 22H2, interpreted for Linux: edge-to-edge charcoal, square
   geometry, Segoe-like typography and restrained #0078d7 selection. */
@define-color ten-panel #101014;
@define-color ten-surface #242424;
@define-color ten-rail #171717;
@define-color ten-hover #383838;
@define-color ten-blue #0078d7;
@define-color ten-text #f5f5f5;
@define-color ten-muted #c8c8c8;

.aero-taskbar {
  background: @ten-panel; border-top: 1px solid #38383b;
  color: @ten-text; padding: 0 3px; font-family: "Segoe UI", "Noto Sans", sans-serif;
}
.aero-start { background: transparent; border: 0; border-radius: 0;
  box-shadow: none; padding: 1px 8px; min-width: 40px; min-height: 37px; }
.aero-start:hover, .aero-start:focus { background: #313136; }
.aero-pin, .aero-task {
  background: transparent; border: 0; border-bottom: 2px solid transparent;
  border-radius: 0; box-shadow: none; padding: 2px 8px; min-height: 36px;
  color: @ten-text;
}
.aero-pin { min-width: 39px; }
.aero-pin:hover, .aero-task:hover { background: #333338; }
.aero-task { border-bottom-color: #636c72; }
.aero-task-active { background: #36363a; border-bottom-color: @ten-blue; }
.aero-task-overflow, .aero-quick, .aero-desktop {
  background: transparent; color: @ten-text; border: 0; border-radius: 0;
  box-shadow: none; padding: 3px 5px;
}
.aero-task-overflow:hover, .aero-quick:hover, .aero-desktop:hover { background: #333338; }
.aero-desktop { border-left: 1px solid #717175; min-width: 5px; padding: 0; }
.aero-time { color: #f6f6f6; font-size: 10px; font-weight: normal; }
.aero-tray-icon { background: transparent; border: 0; border-radius: 0; }
.aero-tray-icon:hover { background: #333338; }
.ten-search {
  background: transparent; color: #f1f1f1; border: 0;
  border-radius: 0; box-shadow: none; padding: 6px 10px; min-width: 36px;
  font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 12px;
}
.ten-search:hover, .ten-search:focus { background: #333338; }

.aero-menu-root, .ten-action-root {
  background: @ten-surface; color: @ten-text; border: 1px solid #424242;
  border-radius: 0; font-family: "Segoe UI", "Noto Sans", sans-serif;
}
.ten-menu-main { background: @ten-surface; padding: 14px 14px 12px 13px; }
.ten-rail { background: @ten-rail; border-right: 1px solid #353535; padding: 8px 3px; }
.ten-rail-button { background: transparent; color: white; border: 0; border-radius: 0;
  box-shadow: none; padding: 9px; min-width: 40px; min-height: 40px; }
.ten-rail-button:hover, .ten-rail-button:focus { background: #474747; }
.ten-user { color: white; font-size: 11px; font-weight: bold; }
.aero-menu-heading { color: #fff; font-size: 17px; font-weight: 600; }
.aero-menu-sub { color: #dedede; font-size: 11px; }
.ten-section-heading { color: #f2f2f2; font-size: 11px; font-weight: 600; }
.ten-letter { background: #2c2c2c; color: #93cfff; font-size: 12px;
  font-weight: bold; padding: 4px 7px; }
.ten-app-list { background: transparent; }
.aero-menu-search {
  background: #f8f8f8; border: 1px solid #686868; color: #191919;
  border-radius: 0; padding: 6px 9px; font-size: 12px;
}
.aero-menu-search:focus { border-color: @ten-blue; box-shadow: 0 0 0 1px @ten-blue; }
.aero-menu-app {
  background: transparent; color: #fafafa; border: 0; border-radius: 0;
  box-shadow: none; padding: 5px 8px; min-height: 29px;
}
.aero-menu-app:hover, .aero-menu-app:focus { background: #414141; }
.ten-app-label { color: #f5f5f5; font-size: 12px; }
.ten-tiles-panel { border-left: 1px solid #3e3e3e; padding-left: 14px; }
.ten-tile { background: @ten-blue; color: white; border: 1px solid transparent;
  border-radius: 0; box-shadow: none; padding: 9px; min-width: 130px; }
.ten-tile:hover, .ten-tile:focus { background: #168ce2; border-color: #a8ddff; }
.ten-tile:active { background: #005a9e; }
.ten-tile-alt { background: #145a96; }
.ten-tile-alt:hover { background: #216fae; }
.ten-tile-wide { background: #005a9e; }
.ten-tile-wide:hover { background: #137abf; }
.ten-tile-label { color: white; font-size: 11px; }
.ten-muted { color: @ten-muted; font-size: 11px; }
.ten-separator { background: #4d4d4d; min-height: 1px; }

/* Action Center is a tall right-edge flyout, NOT a settings dialog. */
.ten-action-root { background: #242424; padding: 0; }
.ten-action-header { padding: 16px 17px 12px; background: #242424; }
.ten-action-notifications { background: #242424; padding: 13px 17px; }
.ten-action-title { color: #f8f8f8; font-size: 16px; font-weight: 600; }
.ten-notification-empty { color: #d8d8d8; font-size: 12px; }
.ten-notification-card { background: #303030; border: 1px solid #444444;
                         border-left: 3px solid #666666; padding: 9px 11px; }
.ten-notification-unread { border-left-color: @ten-blue; }
.ten-notification-title { color: white; font-size: 12px; font-weight: 600; }
.ten-notification-dismiss { background: transparent; color: #bce4ff;
                            border: 1px solid #595959; padding: 3px 7px; font-size: 10px; }
.ten-notification-dismiss:hover { background: #484848; }
.ten-action-bottom { background: #1c1c1c; padding: 12px 12px 16px; border-top: 1px solid #474747; }
.ten-live-switch { background: #363636; color: white; border: 1px solid #666666;
                   padding: 9px 5px; font-size: 11px; }
.ten-live-switch:checked { background: @ten-blue; border-color: #68beff; }
.ten-live-switch:disabled { background: #282828; color: #909090; }
.ten-live-switch:focus { border-color: #a1dfff; }
.ten-action-feedback { color: #cbddec; font-size: 10px; }
.ten-quick { background: #444444; color: white; border: 1px solid #565656;
  border-radius: 0; box-shadow: none; padding: 7px 5px; min-height: 61px; }
.ten-quick:hover, .ten-quick:focus { background: #535353; border-color: #8ed1ff; }
.ten-quick:disabled { background: #2e2e2e; color: #8f8f8f; border-color: #414141; }
.ten-quick-icon { color: white; }
.ten-quick-label { color: white; font-size: 10px; }
.ten-action-detail { color: #d0d0d0; font-size: 11px; }
.ten-mute { background: #3b3b3b; color: white; border: 1px solid #545454;
  border-radius: 0; box-shadow: none; padding: 5px; }
.ten-mute:checked { background: @ten-blue; border-color: #5baef1; }
.ten-mute:disabled { color: #929292; background: #2a2a2a; }
.ten-volume { background: transparent; }
.ten-action-root scale trough { background: #575757; min-height: 3px; }
.ten-action-root scale highlight { background: @ten-blue; }
.ten-action-root scale slider { background: white; min-width: 13px; min-height: 13px; }
.ten-action-root levelbar block.filled { background: @ten-blue; }
/* Independent Windows 10 Settings, network and Task View windows. */
.ten-settings-root, .ten-network-root, .ten-taskview-root {
  background: #202020; color: #f4f4f4; border: 1px solid #484848;
  border-radius: 0; font-family: "Segoe UI", "Noto Sans", sans-serif;
}
.ten-settings-toolbar { background: #202020; padding: 9px 15px;
  border-bottom: 1px solid #383838; min-height: 32px; }
.ten-settings-sidebar { background: #191919; border-right: 1px solid #393939;
  padding: 19px 11px; }
.ten-settings-sidebar entry { background: #f5f5f5; color: #202020;
  border-radius: 0; padding: 9px; border: 1px solid #777; }
.ten-settings-sidebar entry:focus { border-color: @ten-blue; box-shadow: inset 0 -2px @ten-blue; }
.ten-settings-nav { background: transparent; color: #eeeeee; border: 0;
  border-radius: 0; padding: 11px 13px; min-height: 36px; box-shadow: none;
  border-left: 3px solid transparent; text-align: left; }
.ten-settings-nav:hover { background: #303030; }
.ten-settings-nav:focus { background: #333; border-left-color: @ten-blue; }
.ten-settings-page { background: #242424; padding: 30px 31px; }
.ten-settings-heading { color: #ffffff; font-size: 28px; font-weight: 300; margin-bottom: 4px; }
.ten-settings-tile { background: #242424; color: white; border: 1px solid transparent;
  border-radius: 0; padding: 18px 13px; min-height: 116px; box-shadow: none; }
.ten-settings-tile-icon { color: @ten-blue; margin-bottom: 4px; }
.ten-settings-tile:hover, .ten-settings-tile:focus { background: #323232;
  border-color: #626262; box-shadow: inset 0 -2px @ten-blue; }
.ten-settings-action { background: #343434; color: white; border: 1px solid #636363;
  border-radius: 0; padding: 9px 12px; min-height: 32px; }
.ten-settings-action:hover, .ten-settings-action:focus { background: #414141;
  border-color: @ten-blue; }
.ten-settings-action:disabled { background: #292929; color: #9e9e9e; border-color: #3c3c3c; }
.ten-settings-page scale trough { background: #575757; min-height: 4px; }
.ten-settings-page scale highlight { background: @ten-blue; }
.ten-settings-page scale slider { background: #f4f4f4;
  min-width: 14px; min-height: 14px; }
.ten-network-root { padding: 16px 15px; }
.ten-network-item { background: #2b2b2b; border-left: 2px solid #565656;
  padding: 9px 7px; }
.ten-network-item:hover { background: #333333; border-left-color: @ten-blue; }
.ten-network-name { color: white; font-size: 12px; }
.ten-taskview-root { padding: 16px 18px; }
.ten-taskview-desktop { color: #f8f8f8; background: #333333;
  border: 1px solid #535353; border-radius: 0; padding: 11px 18px; }
.ten-taskview-desktop:hover { background: #434343; }
.ten-taskview-active { background: #145b92; border-color: #79c7ff; }
.ten-taskview-window { background: #303030; color: white;
  border: 1px solid #474747; padding: 9px 11px; }
.rice-status { background: transparent; border: 0; border-radius: 0;
  color: white; box-shadow: none; padding: 5px 3px; }
.rice-status:hover, .rice-status:focus { background: #333338; }
.rice-status label { color: white; font-size: 10px; }
.rice-status-summary { color: #cfcfcf; font-size: 11px; }
button:focus { outline: 1px solid #7ec8ff; outline-offset: -1px; }
"""


def run(argv: list[str] | None = None) -> int:
    from .aero_shell import run as shared_run

    return shared_run(argv or ["ricehub-ten-shell"], profile="windows10")
