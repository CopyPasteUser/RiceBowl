"""Windows 10 shell skin for RiceBowl's shared event-driven XFCE taskbar."""

from __future__ import annotations

import unicodedata


APP_ID = "io.github.copypasteuser.RiceHub.TenShell"


def app_letter(app) -> str:
    """Windows 10 A-Z groups; accented Latin names sort into their base letter."""
    title = app.get_display_name() or app.get_name() or ""
    first = unicodedata.normalize("NFKD", title[:1]).upper()[:1]
    return first if "A" <= first <= "Z" else "#"


def letter_positions(apps) -> dict[str, int]:
    """First visible real app per letter, in the Gio catalog's existing order."""
    result = {}
    for index, app in enumerate(apps):
        result.setdefault(app_letter(app), index)
    return result


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
.ten-search.ten-search-box { background: #eeeeee; color: #242424;
  border: 1px solid #b7b7b7; min-height: 31px; padding: 4px 12px;
  margin: 2px 3px; }
.ten-search.ten-search-box label, .ten-search.ten-search-box image {
  color: #303030; }
.ten-search.ten-search-box:hover, .ten-search.ten-search-box:focus {
  background: white; border-color: #4d96c7; }
.ten-jumplist, .ten-jumplist menuitem { background: #282828; color: white;
  border-radius: 0; }
.ten-jumplist menuitem:hover { background: #414141; }

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
.ten-letters-picker { background: #252525; border: 1px solid #555;
  padding: 11px; color: white; }
.ten-letters-popover, .ten-letters-popover > contents {
  background: #252525; border-color: #555; color: white; }
.ten-letters-button { background: transparent; color: white; border: 0;
  border-radius: 0; box-shadow: none; min-width: 33px; min-height: 33px;
  font-size: 13px; }
.ten-letters-button:hover, .ten-letters-button:focus {
  background: @ten-blue; color: white; }
.ten-letters-button:disabled { color: #757575; background: transparent; }
.ten-letters-trigger { background: transparent; border: 0; border-radius: 0;
  box-shadow: none; color: #d1e7fa; padding: 2px 7px; font-size: 11px; }
.ten-letters-trigger:hover, .ten-letters-trigger:focus { background: #454545; }
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
.ten-tiles-panel { border-left: 1px solid #3e3e3e; padding-left: 12px;
  padding-right: 5px; }
.ten-tile { background: @ten-blue; color: white; border: 1px solid transparent;
  border-radius: 0; box-shadow: none; padding: 7px; min-width: 0;
  min-height: 0; }
.ten-tile:hover, .ten-tile:focus { background: #168ce2; border-color: #a8ddff; }
.ten-tile:active { background: #005a9e; }
.ten-tile-small { padding: 4px; }
.ten-tile-large { background: #0764aa; }
.ten-tile-alt { background: #145a96; }
.ten-tile-alt:hover { background: #216fae; }
.ten-tile-wide { background: #005a9e; }
.ten-tile-wide:hover { background: #137abf; }
.ten-tile-label { color: white; font-size: 11px; }
.ten-group-edit { background: transparent; border: 0; border-radius: 0;
  box-shadow: none; padding: 3px; min-width: 22px; min-height: 22px; }
.ten-group-edit:hover, .ten-group-edit:focus { background: #454545; }
.ten-group-entry { background: #292929; color: white; border-radius: 0;
  border: 1px solid @ten-blue; padding: 4px; }
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
.ten-notification-group { color: white; font-size: 12px; font-weight: 600;
                          padding: 8px 0 2px; }
.ten-notification-time { color: #b9b9b9; font-size: 10px; }
.ten-notification-confirm { background: #363636; border-left: 3px solid #d69a42;
                            padding: 10px; color: white; }
.ten-notification-danger { background: #a12622; color: white; border: 1px solid #d6544e;
                           border-radius: 0; box-shadow: none; padding: 5px 9px; }
.ten-notification-danger:hover, .ten-notification-danger:focus {
  background: #bb3630; border-color: white; }
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
.ten-action-expand { background: transparent; border: 0; border-radius: 0;
  box-shadow: none; color: #bedfff; padding: 2px 8px; font-size: 11px; }
.ten-action-expand:hover, .ten-action-expand:focus {
  background: #363636; color: white; }
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
/* Independent Windows 10 Settings, network and Task View windows. Settings
   uses 22H2-era dark Fluent: open canvas, rectangular controls, Segoe-like
   typography, cobalt links and a real Win10 category home (not Win11 cards). */
.ten-settings-root, .ten-network-root, .ten-taskview-root {
  background: #202020; color: #f4f4f4; border: 1px solid #414141;
  border-radius: 0; font-family: "Segoe UI", "Noto Sans", sans-serif;
}
.ten-settings-toolbar { background: #202020; padding: 0 2px 0 12px;
  min-height: 37px; border-bottom: 1px solid #383838; }
.ten-settings-caption { color: #f6f6f6; font-size: 11px; }
.ten-settings-back, .ten-settings-chrome, .ten-settings-close {
  color: #f4f4f4; background: transparent; border: 0; border-radius: 0;
  box-shadow: none; padding: 4px 11px; min-width: 36px; min-height: 32px;
  font-size: 17px; }
.ten-settings-back:hover, .ten-settings-chrome:hover,
.ten-settings-close:hover { background: #373737; }
.ten-settings-close:hover { background: #c42b1c; }
.ten-settings-back:disabled { color: #666666; background: transparent; }
.ten-settings-back:focus, .ten-settings-chrome:focus,
.ten-settings-close:focus { outline: 1px solid #9dd9ff; outline-offset: -2px; }
.ten-settings-sidebar { background: #202020; border-right: 1px solid #393939;
  padding: 14px 6px 10px 13px; }
.ten-settings-sidebar entry, .ten-settings-home entry {
  background: #333333; color: #fafafa; border: 1px solid #6b6b6b;
  border-radius: 0; padding: 9px 10px; min-height: 22px;
  box-shadow: none; caret-color: white; }
.ten-settings-sidebar entry:focus, .ten-settings-home entry:focus {
  border-color: @ten-blue; box-shadow: inset 0 -2px @ten-blue; }
.ten-settings-sidebar entry image, .ten-settings-home entry image { color: #c7c7c7; }
.ten-settings-home-link, .ten-settings-nav {
  color: #ededed; background: transparent; border: 0;
  border-left: 3px solid transparent; border-radius: 0;
  padding: 6px 10px; min-height: 22px; box-shadow: none;
  font-size: 12px; }
.ten-settings-home-link:hover, .ten-settings-nav:hover,
.ten-settings-home-link:focus, .ten-settings-nav:focus { background: #323232; }
.ten-settings-nav-selected { border-left-color: @ten-blue; background: #2e2e2e; }
.ten-settings-page { background: #202020; padding: 29px 39px 35px; }
.ten-settings-heading { color: #ffffff; font-size: 27px; font-weight: 400; }
.ten-settings-home { padding: 22px 33px 16px; }
.ten-settings-home .ten-settings-heading { font-size: 30px; }
.ten-settings-home .ten-muted { font-size: 12px; }
.ten-settings-tile { background: transparent; color: white;
  border: 1px solid transparent; border-radius: 0; box-shadow: none;
  padding: 7px 10px; min-height: 68px; }
.ten-settings-tile:hover, .ten-settings-tile:focus {
  background: #343434; border-color: #606060; }
.ten-settings-tile:active { background: #454545; }
.ten-settings-tile image { color: #f0f0f0; }
.ten-settings-tile-title { color: #f6f6f6; font-size: 13px; font-weight: 600; }
.ten-settings-section { color: #f8f8f8; font-size: 18px; font-weight: 400;
  padding: 12px 0 6px; }
.ten-settings-row { background: transparent; color: #f4f4f4;
  border: 1px solid transparent; border-bottom-color: #424242;
  border-radius: 0; box-shadow: none; padding: 12px 9px; min-height: 40px; }
.ten-settings-row:hover, .ten-settings-row:focus {
  background: #303030; border-color: #525252; }
.ten-settings-row:active { background: #404040; }
.ten-settings-row:disabled { color: #858585; background: transparent; }
.ten-settings-row:disabled label { color: #999999; }
.ten-settings-row-title { color: #f3f3f3; font-size: 13px; }
.ten-settings-chevron { color: #a4d4fa; font-size: 20px; }
.ten-settings-empty { color: #c9c9c9; padding: 24px 4px; font-size: 13px; }
.ten-settings-feedback { color: #b7b7b7; font-size: 11px; padding-bottom: 8px; }
.ten-settings-switch { background: transparent; min-width: 47px; min-height: 22px; }
.ten-settings-switch trough { background: #494949; border: 2px solid #d1d1d1;
  border-radius: 12px; min-width: 43px; min-height: 18px; }
.ten-settings-switch:checked trough { background: @ten-blue; border-color: @ten-blue; }
.ten-settings-switch slider { background: #f5f5f5; border: 0;
  border-radius: 100%; min-height: 14px; min-width: 14px; }
.ten-settings-switch:disabled { opacity: .5; }
.ten-settings-action { background: #333333; color: white; border: 1px solid #757575;
  border-radius: 0; padding: 7px 12px; min-height: 26px; box-shadow: none; }
.ten-settings-action:hover, .ten-settings-action:focus { background: #444444;
  border-color: #9bcfff; }
.ten-settings-action:disabled { background: #292929; color: #919191; }
.ten-settings-page scale trough { background: #575757; min-height: 4px; }
.ten-settings-page scale highlight { background: @ten-blue; }
.ten-settings-page scale slider { background: #f4f4f4;
  min-width: 14px; min-height: 14px; }
.ten-network-root { padding: 16px 15px; }
.ten-network-item { background: #2b2b2b; border-left: 2px solid #565656;
  padding: 9px 7px; }
.ten-network-item:hover { background: #333333; border-left-color: @ten-blue; }
.ten-network-name { color: white; font-size: 12px; }
/* Compact Windows 10 notification-area flyouts, using the established Linux
   device adapters; no XP glass, icon sheets or separate resident service. */
.ten-tray-popup { background: #232323; color: #f5f5f5;
  border: 1px solid #494949; border-radius: 0;
  font-family: "Segoe UI", "Noto Sans", sans-serif; }
.ten-tray-popup .luna-tray-card { background: #232323; color: #f2f2f2;
  padding: 17px 18px 19px; min-width: 292px; }
.ten-tray-title { color: #ffffff; font-size: 16px; font-weight: 600; }
.ten-tray-section { color: #eaeaea; font-size: 12px; font-weight: 600;
  padding-top: 7px; }
.ten-tray-caption { color: #d6d6d6; font-size: 12px; }
.ten-tray-link, .ten-tray-popup .luna-tray-switch,
.ten-tray-popup .luna-tray-mute { color: #f6f6f6; background: #363636;
  border: 1px solid #696969; border-radius: 0; box-shadow: none;
  padding: 8px 11px; min-height: 25px; }
.ten-tray-link:hover, .ten-tray-popup .luna-tray-switch:hover,
.ten-tray-popup .luna-tray-mute:hover { background: #484848; border-color: #9bd5ff; }
.ten-tray-link:focus, .ten-tray-popup .luna-tray-switch:focus,
.ten-tray-popup .luna-tray-mute:focus { border-color: #9bd5ff; outline: 1px solid #9bd5ff; }
.ten-tray-link:disabled, .ten-tray-popup .luna-tray-switch:disabled,
.ten-tray-popup .luna-tray-mute:disabled { color: #969696; background: #2a2a2a;
  border-color: #454545; }
.ten-tray-popup .luna-tray-mute:checked { background: @ten-blue; border-color: #68beff; }
.ten-tray-popup scale trough { background: #515151; min-height: 4px; }
.ten-tray-popup scale highlight { background: @ten-blue; }
.ten-tray-popup scale slider { background: white; border: 0; box-shadow: none;
  min-width: 15px; min-height: 15px; }
.ten-tray-popup levelbar block.filled { background: @ten-blue; }
.ten-tray-popup calendar { background: #232323; color: #f1f1f1;
  border: 1px solid #494949; }
.ten-tray-popup calendar:selected { background: @ten-blue; color: white; }
.ten-clock-button { background: transparent; color: white; border: 0;
  border-radius: 0; box-shadow: none; padding: 2px 6px; }
.ten-clock-button:hover, .ten-clock-button:focus { background: #343434; }
.ten-taskview-root { padding: 16px 18px; }
.ten-taskview-desktop { color: #f8f8f8; background: #333333;
  border: 1px solid #535353; border-radius: 0; padding: 11px 18px; }
.ten-taskview-desktop:hover { background: #434343; }
.ten-taskview-active { background: #145b92; border-color: #79c7ff; }
.ten-taskview-window { background: #303030; color: white;
  border: 1px solid #474747; padding: 12px 13px; min-height: 86px; }
.ten-taskview-window-active { border-color: #65b5f6; background: #243b4e; }
.ten-taskview-close { background: transparent; color: #eee;
  border: 0; border-radius: 0; box-shadow: none; min-width: 28px;
  min-height: 28px; padding: 2px; }
.ten-taskview-close:hover { background: #b52d2d; color: white; }
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
