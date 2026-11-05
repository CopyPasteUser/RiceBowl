"""On-demand, event-driven Frutiger Aero taskbar and searchable Start menu.

Only runs when explicitly launched or on login after selecting an Aero rice.
Uses the installed Gio .desktop catalog; does not poll the process table.
"""

from __future__ import annotations

from pathlib import Path
import ctypes
import ctypes.util
import logging
import os
import shutil
import subprocess
import threading

from .aero_layout import PANEL_HEIGHT, bottom_strut, menu_geometry, select_windows, task_capacity
from .aero_pins import PIN_LIMIT, PinConfigError, load_pins, pin_file, save_pins
from .aero_superbar import group_windows, select_groups


APP_ID = "io.github.copypasteuser.RiceHub.AeroShell"

# Explicitly approved desktop utilities used by the six shell profiles and
# their Control Panels. A visible installed applet must never become a no-op.
LAUNCHABLE_TOOLS = frozenset((
    "xfce4-settings-manager", "xfce4-session-logout", "xfce4-session-settings",
    "nm-connection-editor", "pavucontrol", "xfce4-display-settings", "blueman-manager",
    "xfce4-appearance-settings", "xfce4-power-manager-settings", "system-config-printer",
    "xfce4-appfinder", "xfce4-about", "yelp", "xfhelp4", "xfce4-mouse-settings",
    "xfce4-keyboard-settings", "xfce4-notifyd-config", "xfce4-accessibility-settings",
    "xfdesktop-settings", "xfwm4-settings", "exo-preferred-applications", "xfce4-mixer",
    "mintinstall", "gnome-software", "synaptic", "xfce4-taskmanager",
    "gnome-system-monitor", "users-admin", "mate-user-admin", "time-admin",
    "gnome-control-center", "catfish",
))


def preferred_task_manager(which=shutil.which) -> str | None:
    """Pick a real installed GTK task manager; never substitute a fake UI."""
    return next((name for name in ("xfce4-taskmanager", "gnome-system-monitor")
                 if which(name)), None)


def app_catalog(Gio):
    """Keep only visible, distinct real application launchers."""
    candidates = (app for app in Gio.AppInfo.get_all() if app.should_show())
    result = {}
    for app in candidates:
        name = app.get_display_name() or app.get_name()
        if name and name.casefold() not in result:
            result[name.casefold()] = app
    return tuple(sorted(result.values(), key=lambda app: (app.get_display_name() or app.get_name()).casefold()))


def default_pins(apps) -> tuple[str, ...]:
    """Prefer the user's installed file manager, browser and terminal."""
    selected = []
    for keyword in ("file manager", "browser", "terminal"):
        for app in apps:
            identifier = app.get_id()
            label = (app.get_display_name() or app.get_name() or "").casefold()
            # XFCE ships "File Manager Settings" as a separate .desktop
            # launcher. It sorts before "Thunar File Manager", but it should
            # never become the default Files shortcut on a fresh desktop.
            if keyword == "file manager" and any(
                    term in label for term in ("settings", "preferences", "configuration")):
                continue
            if keyword in label and identifier and identifier not in selected:
                selected.append(identifier)
                break
    return tuple(selected)


def launch_app_checked(app) -> None:
    """Do not silently treat Gio's explicit launch failure as success."""
    if app.launch([], None) is False:
        raise RuntimeError("The installed desktop launcher reported failure")


def matching_apps(apps, query: str):
    needle = query.casefold().strip()
    return tuple(app for app in apps if needle in
                 (app.get_display_name() or app.get_name() or "").casefold())


def frutiger_apps(apps, pins: tuple[str, ...], query: str):
    """Put the user's real favorites first in Aqua World, not alphabetic tools.

    Search always covers the complete installed Gio catalog. The home view
    starts with pinned apps, followed by recognizable desktop applications;
    neither category introduces duplicate tiles or pretend launchers.
    """
    matches = matching_apps(apps, query)
    if query.strip():
        return matches
    order = {identifier: index for index, identifier in enumerate(pins)}
    categories = ("FileManager", "WebBrowser", "TerminalEmulator")

    def rank(app):
        identifier = app.get_id()
        if identifier in order:
            return (0, order[identifier], "")
        category_reader = getattr(app, "get_categories", None)
        app_categories = (category_reader() or "").split(";") if callable(category_reader) else ()
        for index, category in enumerate(categories):
            if category in app_categories:
                return (1, index, (app.get_display_name() or app.get_name() or "").casefold())
        return (2, 0, (app.get_display_name() or app.get_name() or "").casefold())

    return tuple(sorted(matches, key=rank))


def frutiger_select_page(stack, buttons, section, search, page: str,
                         settings_navigation=None):
    """Keep Aqua launcher pages and tab states synchronized in both directions.

    Used for clicks, searching, reopening the launcher and the explicit Back
    button. A deliberately small GTK-independent contract is regression-tested.
    """
    if page not in buttons:
        raise ValueError("Unknown Aqua launcher page: " + page)
    stack.set_visible_child_name(page)
    for name, button in buttons.items():
        active = name == page
        if button.get_active() != active:
            button.set_active(active)
    section.set_visible(page == "Apps")
    if settings_navigation is not None:
        settings_navigation.set_visible(page == "Settings")
    if page == "Apps":
        search.grab_focus()


def frutiger_tab_switcher(stack, buttons, section, search, settings_navigation=None):
    """Prevent GTK3 toggle-button state signals from re-entering tab changes."""
    switching = [False]

    def switch_to(page):
        if switching[0]:
            return
        switching[0] = True
        try:
            frutiger_select_page(stack, buttons, section, search, page,
                                 settings_navigation)
        finally:
            switching[0] = False

    return switch_to


def luna_programs(apps, pins: tuple[str, ...], query: str, limit: int = 8,
                  *, start_favorites=None, history=None):
    """Pick real installed apps for the XP pin band and the recent-program area."""
    if query.strip():
        return (), matching_apps(apps, query)[:limit]
    featured = []
    if start_favorites is not None:
        for identifier in start_favorites:
            featured.extend(app for app in apps if app.get_id() == identifier and
                            app not in featured)
    else:
        for category in ("WebBrowser", "Email"):
            for app in apps:
                classifier = getattr(app, "get_categories", None)
                categories = (classifier() or "").split(";") if callable(classifier) else ()
                if category in categories and app not in featured:
                    featured.append(app)
                    break
        for identifier in pins:
            if len(featured) >= 2:
                break
            for app in apps:
                if app.get_id() == identifier and app not in featured:
                    featured.append(app)
                    break
        featured = featured[:2]
    regular = tuple(app for app in apps if app not in featured)
    if history:
        positions = {app.get_id(): index for index, app in enumerate(regular)}
        regular = tuple(sorted(regular, key=lambda app: (
            -history.get(app.get_id(), (0, 0))[1],
            -history.get(app.get_id(), (0, 0))[0], positions[app.get_id()])))
    return tuple(featured), regular[:limit]


def luna_program_groups(apps):
    """Every installed app appears exactly once in the XP All Programs flyout."""
    categories = (
        ("Accessories", "accessories-text-editor", ("Utility", "Accessories", "TextEditor")),
        ("Games", "applications-games", ("Game",)),
        ("Graphics", "applications-graphics", ("Graphics", "Photography")),
        ("Internet", "web-browser", ("Network", "WebBrowser", "Email")),
        ("Multimedia", "applications-multimedia", ("Audio", "Video", "Player")),
        ("Office", "folder-documents", ("Office", "Spreadsheet", "WordProcessor")),
        ("System Tools", "preferences-system", ("System", "Settings", "FileManager", "TerminalEmulator")),
    )
    remaining = list(apps)
    grouped = []
    for title, icon, markers in categories:
        members = []
        for app in tuple(remaining):
            reader = getattr(app, "get_categories", None)
            names = (reader() or "").split(";") if callable(reader) else ()
            if any(marker in names for marker in markers):
                members.append(app)
                remaining.remove(app)
        if members:
            grouped.append((title, icon, tuple(members)))
    if remaining:
        grouped.append(("Other Programs", "applications-other", tuple(remaining)))
    return tuple(grouped)


def win7_programs(apps, pins: tuple[str, ...], query: str, *, all_programs: bool = False,
                  limit: int = 9):
    """Windows 7's recent-like list prefers real pinned apps, without duplicates."""
    if query.strip() or all_programs:
        return matching_apps(apps, query)[:limit]
    favorites = []
    ids = set(pins)
    for identifier in pins:
        favorites.extend(app for app in apps if app.get_id() == identifier and app not in favorites)
    favorites.extend(app for app in apps if app not in favorites and app.get_id() not in ids)
    return tuple(favorites[:limit])


def win7_explorer_command(binary: str, folder: Path) -> tuple[str, ...]:
    """Launch only the optional local Windows 7 renderer; preserve Thunar defaults."""
    return (binary, "--theme", "win7", str(folder))


def frutiger_status_summary(status) -> str:
    """Summarize real hardware state for the Aqua World header; no fake toggles."""
    if status is None:
        return "Checking network and sound…"
    network = {"wifi": "Wi-Fi", "ethernet": "Ethernet", "offline": "Offline"}.get(
        status.network, "Network unavailable")
    sound = status.sound
    audio = ("Audio unavailable" if sound.percent is None else
             "Muted" if sound.muted else f"Volume {sound.percent}%")
    battery = f"Battery {status.battery.percent}%" if status.battery else "No battery"
    return "  •  ".join((network, audio, battery))


CSS = b"""
.aero-taskbar {
  background-image: linear-gradient(to bottom, rgba(193,232,255,.95), rgba(91,161,211,.96) 48%, rgba(24,74,133,.98));
  border-top: 1px solid #d6f5ff; color: #fff; padding: 3px 12px;
}
.aero-start {
  background-image: linear-gradient(to bottom, #ddffff, #48b4e7 55%, #1474b8);
  border: 1px solid #e8ffff; border-radius: 23px;
  padding: 2px 14px 2px 4px; color: #fff; font-weight: bold;
  box-shadow: 0 1px 4px rgba(11,51,84,.55);
}
.aero-start:hover { background-image: linear-gradient(to bottom, #ffffff, #74d1f1 60%, #1985c5); }
.aero-start:focus { border: 2px solid #ffffff; }
.aero-pin { background: transparent; border: 1px solid transparent; padding: 5px 13px; border-radius: 3px; }
.aero-pin:hover { background: rgba(235,251,255,.25); border-color: rgba(255,255,255,.48); }
.aero-task { background: rgba(255,255,255,.10); border: 1px solid rgba(216,244,255,.36);
  border-bottom: 2px solid rgba(180,237,255,.65); border-radius: 4px;
  padding: 4px 6px; color: white; box-shadow: inset 0 1px rgba(255,255,255,.15); }
.aero-task:hover { background: rgba(224,250,255,.27); border-color: rgba(255,255,255,.75); }
.aero-task-active { background: rgba(221,247,255,.39); border-color: #e5faff;
  border-bottom: 2px solid #ffffff; }
.aero-task-overflow { background: transparent; color: #fff; border: 1px solid rgba(255,255,255,.30);
  border-radius: 4px; padding: 4px 8px; }
.aero-tray-icon { background: transparent; border: 0; padding: 3px; }
.aero-tray-icon:hover { background: rgba(255,255,255,.22); border-radius: 4px; }
.win7-taskbar .win7-tray-chevron {
  border: 1px solid transparent; background: transparent; padding: 2px 4px;
  color: #e4f5ff; font-size: 13px; border-radius: 3px; min-width: 21px;
}
.win7-taskbar .win7-tray-chevron:hover,
.win7-taskbar .win7-tray-chevron:focus {
  border-color: #9ad4f7; background: rgba(208,234,252,.26);
}
menu.win7-tray-overflow-menu {
  background: #eff6fb; border: 1px solid #6d92b5; color: #173c5a;
  padding: 4px; box-shadow: 0 3px 9px rgba(12,37,61,.3);
}
menu.win7-tray-overflow-menu menuitem {
  min-height: 28px; color: #173c5a; padding: 3px 8px;
}
menu.win7-tray-overflow-menu menuitem:hover,
menu.win7-tray-overflow-menu menuitem:focus {
  background: #c9e7fc; color: #0a3558;
}
window.win7-tray-customize {
  background: #f5f9fc; color: #173f61; border: 1px solid #8fadc4;
}
.win7-tray-customize-heading {
  color: #174c75; font-size: 14px; font-weight: bold;
}
window.win7-tray-customize combobox, window.win7-tray-customize button {
  border: 1px solid #9bb7cf; background: #eef6fb; color: #174365;
  border-radius: 3px; padding: 4px 8px;
}
window.win7-tray-customize button:hover, window.win7-tray-customize button:focus {
  background: #d6ebf9; border-color: #4387ba;
}
.aero-glass { background-image: linear-gradient(to bottom, rgba(205,242,255,.79), rgba(94,172,221,.83) 48%, rgba(26,81,139,.90)); }
.aero-time { color: #fff; font-size: 11px; font-weight: bold; }
.aero-quick { background: transparent; border: 1px solid transparent; color: white; border-radius: 4px; padding: 4px; }
.aero-quick:hover, .aero-quick:focus { border-color: #d0f4ff; background: rgba(255,255,255,.24); }
.aero-desktop { background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.5); border-radius: 2px; min-width: 11px; padding: 2px; }
.aero-desktop:hover, .aero-desktop:focus { background: rgba(255,255,255,.47); }
.aero-menu-footer { border-top: 1px solid #96c1dd; padding-top: 8px; }
.aero-menu-power { color: #fff; border-radius: 4px; border: 1px solid #f4b99e; background-image: linear-gradient(to bottom, #fa946c, #c65530); padding: 6px 10px; }
.aero-menu-root { background: #eaf4fb; border: 1px solid #5e9bcc; border-radius: 8px; }
.aero-menu-heading { color: #244e6e; font-size: 20px; font-weight: bold; }
.aero-menu-sub { color: #577d9c; font-size: 12px; }
.aero-menu-search { border: 1px solid #6badd8; background: #fff; color: #193f60; border-radius: 4px; padding: 8px; }
.aero-menu-app { background: transparent; border: 1px solid transparent; box-shadow: none; color: #1a415f; border-radius: 3px; padding: 7px; }
.aero-menu-app:hover, .aero-menu-app:focus { background: #c4e6f9; border-color: #91c7e7; }
.aero-menu-side {
  background-image: linear-gradient(to bottom, #dff5ff, #a8d5f1 52%, #71acd6);
  border-left: 1px solid #83b6db; padding: 12px;
}
.aero-control-root { background-image: linear-gradient(to bottom, #f6fcff, #d6eaf8);
  color: #244e6e; border: 1px solid #6eabd4; border-radius: 7px; padding: 14px; }
.aero-control-quick { background-image: linear-gradient(to bottom, #ffffff, #c0dff3);
  color: #244e6e; border: 1px solid #82b3d6; border-radius: 5px; padding: 10px 8px; }
.aero-control-quick:hover, .aero-control-quick:focus { background: #eefaff;
  border-color: #338cd0; }
.aero-menu-side button { background: transparent; border: 1px solid transparent; color: #194467; box-shadow: none; }
.aero-menu-side button:hover { background: rgba(255,255,255,.55); border-color: #74a7cb; }

/* Windows 7 Aero right notification cluster. */
.rice-status { background: rgba(255,255,255,.12); border: 1px solid rgba(245,254,255,.2); border-radius: 4px; color: #fff; padding: 4px 5px; box-shadow: inset 0 1px rgba(255,255,255,.18); }
.rice-status:hover, .rice-status:focus { background: rgba(230,250,255,.33); border-color: #e3faff; }
.rice-status label { color: #fff; font-size: 11px; }
.rice-status-summary { color: #315c7f; font-size: 11px; }

/* Windows 7 alone: the compact, icon-first Aero Superbar. The other rices
   deliberately retain their own proportions and status treatments. */
.aero-taskbar.win7-taskbar {
  background-image: linear-gradient(to bottom,
    rgba(230,242,250,.82) 0%, rgba(102,134,169,.78) 5%,
    rgba(59,91,129,.81) 44%, rgba(29,53,86,.92) 47%,
    rgba(31,58,97,.93) 83%, rgba(14,35,67,.97) 100%);
  border-top: 1px solid rgba(243,251,255,.95);
  border-bottom: 1px solid #102847;
  padding: 1px 5px;
  color: white;
}
.aero-start.win7-start {
  background: transparent;
  border: 0;
  box-shadow: none;
  border-radius: 24px;
  padding: 0 4px 0 2px;
  min-width: 44px;
  min-height: 42px;
}
.win7-start:hover { background: radial-gradient(ellipse at center, rgba(255,255,255,.37), rgba(130,212,253,.10) 75%, transparent); }
.win7-start:active, .win7-start:focus { background: radial-gradient(ellipse at center, rgba(207,247,255,.62), rgba(69,172,227,.14) 80%, transparent); }
.aero-pin.win7-pin, .aero-task.win7-task {
  min-width: 47px;
  min-height: 41px;
  background-image: linear-gradient(to bottom, rgba(230,247,255,.11), rgba(14,67,111,.05));
  border: 1px solid rgba(214,242,255,.17);
  border-bottom: 2px solid rgba(245,254,255,.37);
  border-radius: 3px;
  box-shadow: inset 0 1px rgba(255,255,255,.15);
  padding: 2px 4px;
}
.win7-pin:hover, .win7-task:hover {
  background-image: linear-gradient(to bottom, rgba(235,252,255,.55), rgba(92,173,218,.38));
  border-color: rgba(247,255,255,.75);
  box-shadow: inset 0 1px rgba(255,255,255,.56), 0 0 4px rgba(106,207,255,.48);
}
.aero-task-active.win7-task {
  background-image: linear-gradient(to bottom, rgba(243,255,255,.49), rgba(75,165,208,.42) 48%, rgba(92,175,219,.58));
  border-color: rgba(251,255,255,.74);
  border-bottom: 2px solid #d0f5ff;
  box-shadow: inset 0 1px rgba(255,255,255,.63), 0 0 4px rgba(145,227,255,.37);
}
.win7-task-attention.win7-task {
  background-image: linear-gradient(to bottom, rgba(255,232,158,.76), rgba(236,151,39,.5) 54%, rgba(155,87,27,.7));
  border: 1px solid rgba(255,236,181,.91);
  border-bottom: 2px solid #ffd16a;
  box-shadow: inset 0 1px rgba(255,255,255,.65), 0 0 5px rgba(255,179,52,.56);
}
.aero-desktop.win7-desktop {
  background-image: linear-gradient(to right, rgba(255,255,255,.1), rgba(207,247,255,.34));
  border: 1px solid rgba(220,245,255,.55);
  border-radius: 0;
  min-width: 10px;
  padding: 0;
}
.win7-menu-root {
  background-image: linear-gradient(to bottom, rgba(218,232,244,.98), rgba(77,114,153,.97) 58%, rgba(25,57,94,.98));
  border: 1px solid #244b74;
  border-radius: 8px 8px 5px 5px;
  padding: 6px;
  box-shadow: inset 0 1px rgba(255,255,255,.94), inset 0 -1px rgba(12,44,86,.8);
}
.win7-menu-body { background: transparent; }
.win7-programs {
  background: #fffefa;
  border: 1px solid #7497b4;
  border-radius: 3px;
  padding: 7px 5px 6px;
}
/* RiceHub-Aero's shared GTK theme tints every viewport blue for Thunar.
   The Windows 7 Start program list is an intentionally distinct ivory pane. */
.win7-programs scrolledwindow, .win7-programs viewport {
  background-color: #fffefa;
}
.win7-program { color: #1b2937; background: transparent; border: 1px solid transparent;
  border-radius: 2px; box-shadow: none; padding: 5px 7px; }
.win7-program:hover, .win7-program:focus { background-image: linear-gradient(to bottom, #eaf7ff, #b9dff7); border-color: #73b0d8; }
.win7-program-label { color: #20272d; font-size: 12px; }
.win7-programs-separator { background: #dde5ed; min-height: 1px; }
.win7-all-programs { color: #223b4c; background: transparent; border: 1px solid transparent;
  border-radius: 2px; padding: 7px; box-shadow: none; }
.win7-all-programs:hover, .win7-all-programs:focus { background: #d4eaf8; border-color: #8dbfdc; }
.win7-search { background: #fff; color: #1c3c52; border: 1px solid #798c9c;
  border-radius: 2px; padding: 6px; margin-top: 5px; }
.win7-search:focus { border-color: #3697d3; box-shadow: 0 0 2px rgba(20,115,182,.55); }
.win7-side { background: transparent; padding: 0 5px 1px 11px; }
.win7-user-orb { background: rgba(255,255,255,.34); border: 2px solid rgba(255,255,255,.78);
  border-radius: 5px; padding: 2px; margin-bottom: 3px; }
.win7-user-name { color: #fff; font-size: 12px; font-weight: bold; text-shadow: 0 1px #315a83; }
.win7-place { color: white; background: transparent; border: 1px solid transparent;
  border-radius: 3px; box-shadow: none; padding: 6px 3px; }
.win7-place label { color: #fff; font-weight: normal; font-size: 12px; }
.win7-place:hover, .win7-place:focus { background: rgba(235,250,255,.33); border-color: rgba(255,255,255,.6); }
.win7-place:disabled label { color: #e1ebf5; }
.win7-side-separator { background: rgba(227,248,255,.36); min-height: 1px; margin: 6px 3px; }
.win7-power { color: #fff; border: 1px solid #9f622e; border-radius: 3px;
  background-image: linear-gradient(to bottom, #ffba7e, #e38942 48%, #ad5721 52%, #c77632);
  padding: 7px 14px; font-weight: bold; box-shadow: inset 0 1px rgba(255,255,255,.43); }
.win7-power:hover { background-image: linear-gradient(to bottom, #ffdbaf, #f5a85f 48%, #c66a29 52%, #e28c48); }
.win7-power:disabled { background: #6c8290; color: #dfebf2; }
.win7-control-search { background: #fff; color: #1f4059;
  border: 1px solid #91b8d4; border-radius: 2px; padding: 5px 8px; }
.win7-control-search:focus { border-color: #328dca; }
/* Windows 7 Control Panel: a full navigable Explorer-era application window.
   The separate Linux hardware controls sit behind an explicit disclosure. */
.win7-cp-root { background: #fff; color: #202a35; }
.win7-cp-toolbar {
  background-image: linear-gradient(to bottom, #f4fbff 0%, #d5e9f7 100%);
  border-bottom: 1px solid #a7c8db; padding: 7px 12px;
}
.win7-cp-back { background-image: linear-gradient(to bottom, #fff, #bfdaf0);
  border: 1px solid #7aa9c8; border-radius: 15px; min-width: 30px; min-height: 28px;
  padding: 1px 4px; }
.win7-cp-back:hover, .win7-cp-back:focus { border-color: #2989c5; background: #d1edff; }
.win7-cp-breadcrumb { background: #fff; border: 1px solid #a5becd;
  border-radius: 2px; box-shadow: inset 0 1px #fff; color: #2a4a5f;
  font-size: 12px; padding: 6px 12px; }
.win7-cp-breadcrumb:hover, .win7-cp-breadcrumb:focus { background: #effaff; border-color: #4b9cd1; }
.win7-cp-content { background: #fff; padding: 24px 29px 20px; }
.win7-cp-heading { color: #175483; font-size: 22px; }
.win7-cp-viewby { color: #616f7c; font-size: 11px; }
.win7-cp-view-select { color: #244966; background: #fff; border: 1px solid #a5bfd0;
  border-radius: 2px; min-width: 112px; }
.win7-cp-category { padding: 2px 4px 7px; min-width: 275px; }
.win7-cp-category-title, .win7-cp-link {
  background: transparent; background-image: none; box-shadow: none;
  border: 1px solid transparent; border-radius: 2px; color: #155b93;
  text-shadow: none; padding: 2px 3px; font-size: 12px;
}
.win7-cp-category-title { font-size: 14px; font-weight: bold; }
.win7-cp-category-title:hover, .win7-cp-category-title:focus,
.win7-cp-link:hover, .win7-cp-link:focus {
  color: #084879; background: #e6f4ff; border-color: #b2d9f2;
}
.win7-cp-link:disabled { color: #667987; background: transparent; border-color: transparent; }
.win7-cp-icon-tile { color: #204e73; background: transparent; border: 1px solid transparent;
  border-radius: 3px; padding: 9px 5px; min-width: 132px; min-height: 94px; }
.win7-cp-icon-tile:hover, .win7-cp-icon-tile:focus {
  background-image: linear-gradient(to bottom, #f5fcff, #d6edfa);
  border-color: #87b7d5;
}
.win7-cp-icon-tile label { color: #294f6b; font-size: 11px; }
.win7-cp-task-info { color: #455a69; font-size: 12px; }
.win7-cp-task-open { color: #155b93;
  background-image: linear-gradient(to bottom, #fff, #dbeaf3);
  border: 1px solid #93b3c7; border-radius: 3px; padding: 7px 11px; }
.win7-cp-task-open:hover, .win7-cp-task-open:focus {
  background-image: linear-gradient(to bottom, #f5fcff, #b5ddf5); border-color: #4d97c8;
}
.win7-cp-task-open:disabled { color: #788b97; background: #e8edf0; }
.win7-cp-empty { color: #647989; font-size: 13px; }
.win7-cp-status-expander { background: #eaf4fb; border-top: 1px solid #b0cfdf;
  padding: 5px 18px; color: #2f5c78; font-size: 11px; }
.win7-cp-hardware { background: #f4f9fd; padding: 7px 10px; }
.win7-cp-hardware .rice-control-detail { color: #274f66; }
.win7-group-count { color: #fff; font-size: 10px; font-weight: bold;
  background: #246da9; border: 1px solid #caefff; border-radius: 8px;
  min-width: 12px; padding: 0 2px; }
.win7-preview { background-image: linear-gradient(to bottom, #eaf8ff, #a3cfe9);
  border: 1px solid #548ebc; border-radius: 5px; padding: 9px;
  box-shadow: inset 0 1px #fff; }
.win7-preview-card { background: rgba(255,255,255,.7); border: 1px solid #9ebdd1;
  border-radius: 3px; padding: 5px; color: #174368; }
.win7-preview-card:hover, .win7-preview-card:focus { background: #d5f1ff;
  border-color: #4695d2; }
.win7-preview-name { font-size: 11px; color: #15446d; }
.win7-preview-fallback { background: #e7f1f8; min-width: 150px; min-height: 95px;
  border: 1px solid #b4cede; }
.win7-jumplist { background: #f5fbff; color: #19456b;
  border: 1px solid #729fbd; padding: 5px; }
.win7-jumplist menuitem:hover { background: #c4e8fb; }
/* Native Windows 7 notification flyouts. These are independent floating GTK
   windows; styling only the tiny 48px parent dock would clip their contents. */
window.win7-tray-popup {
  background: #f9fbfd; color: #23384c;
  border: 1px solid #557fa6; border-radius: 5px;
  box-shadow: 0 5px 15px rgba(9,31,60,.45), inset 0 1px #fff;
}
.win7-tray-scroll, .win7-tray-body { background: #f9fbfd; }
.win7-tray-body { padding: 0 10px 11px; min-width: 270px; }
.win7-tray-heading {
  background-image: linear-gradient(to bottom, #eaf6ff, #b4d4eb 51%, #8dbad9);
  border-bottom: 1px solid #749ab7; padding: 9px 10px;
  margin: 0 -10px 4px;
}
.win7-tray-title { color: #153f64; font-size: 13px; font-weight: bold; }
.win7-tray-caption { color: #3c5369; font-size: 11px; }
.win7-tray-section { color: #234f76; font-size: 12px; font-weight: bold; }
.win7-tray-popup button, .win7-tray-popup .win7-tray-link {
  color: #1d527f; border: 1px solid transparent; background: transparent;
  border-radius: 2px; box-shadow: none; padding: 5px 7px;
}
.win7-tray-popup button:hover, .win7-tray-popup button:focus {
  background-image: linear-gradient(to bottom, #f5fcff, #c0e3fb);
  border-color: #8ebcdd;
}
.win7-tray-popup button:disabled { color: #778a9b; background: transparent; }
.win7-tray-popup .win7-tray-toggle {
  border: 1px solid #8cabc4; background-image: linear-gradient(to bottom, #fff, #d5e8f4);
}
.win7-tray-popup .win7-tray-toggle:checked {
  background-image: linear-gradient(to bottom, #c9eafa, #86c3e5); color: #0f4369;
}
.win7-tray-volume-row { background: #fff; border: 1px solid #d6e4ee;
  border-radius: 3px; padding: 7px; }
.win7-tray-popup scale trough { background: #dae5ec; border: 1px solid #9fb4c5; }
.win7-tray-popup scale highlight { background: #62a8d5; }
.win7-tray-popup scale slider { background-image: linear-gradient(to bottom, #fff, #c4ddeb);
  border: 1px solid #6495b8; }
.win7-tray-popup .luna-tray-network-row,
.win7-tray-popup .luna-tray-device { border-bottom: 1px solid #d9e7f1; }
.win7-tray-popup .luna-tray-current { color: #195a89; font-weight: bold; }
.win7-tray-popup calendar { background: #fff; color: #1c415d; border: 1px solid #afc9d9; }
.win7-clock-button { color: white; background: transparent; border: 1px solid transparent;
  border-radius: 2px; padding: 2px 6px; }
.win7-clock-button:hover, .win7-clock-button:focus {
  background: rgba(239,250,255,.32); border-color: rgba(255,255,255,.65);
}
.win7-clock-button label { color: white; }
.win7-alert-button { color: #f2f8fd; background: transparent;
  border: 1px solid transparent; border-radius: 3px; padding: 3px 5px;
  font-size: 19px; }
.win7-alert-button:hover, .win7-alert-button:focus {
  background: rgba(220,240,255,.25); border-color: #b2daf5; }
.win7-alert-unread { color: #fff4a5; text-shadow: 0 0 3px #e3a84b; }
.win7-alert-item { background: #fff; color: #214966; border: 1px solid #dae4ed;
  border-radius: 2px; padding: 6px; }
.win7-alert-item-unread { border-left: 3px solid #e3a342; }
.win7-alert-summary { font-weight: bold; color: #1b4969; }
window.win7-balloon { background: #f3f9ff; color: #183955;
  border: 1px solid #6296c2; box-shadow: 0 3px 12px rgba(15,39,68,.45); }
.win7-balloon-body { background: #f5f9fd; color: #213e54; padding: 10px 13px; }
.win7-balloon-title { color: #153e65; font-weight: bold; font-size: 12px; }
.win7-balloon-dismiss { background: #e2eef9; color: #1a4767;
  border: 1px solid #93b2d0; border-radius: 3px; padding: 3px 9px; }
"""


def run(argv: list[str] | None = None, *, profile: str = "aero") -> int:
    from .heritage import PROFILES
    if profile not in ("aero", "windows10", *PROFILES):
        raise ValueError("Unknown RiceBowl shell profile")
    ten = profile == "windows10"
    heritage = PROFILES.get(profile)
    tiles = ten or profile == "chromeos"
    panel_height = (34 if profile == "winclassic" else
                    40 if profile in ("winxp", "windows10") else
                    56 if profile == "chromeos" else
                    48 if profile == "aero" else PANEL_HEIGHT)
    action_heights = {"winclassic": 570, "aero": 530,
                      "frutiger": 560, "chromeos": 608, "windows10": 680}
    if ten:
        from .ten_shell import APP_ID as TEN_APP_ID, CSS as TEN_CSS
    if heritage:
        from .heritage_shell import CSS as HERITAGE_CSS
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

    from .aero_layout import actual_popup_y
    from .aero_windows import (WindowSnapshot, WindowSnapController, closest_workarea,
                               create_window_tracker, is_task_window, toggle_window_id,
                               window_layout)
    from .installer import project_root

    class AeroShell(Gtk.Application):
        def __init__(self):
            app_id = (TEN_APP_ID if ten else
                      f"io.github.copypasteuser.RiceHub.{profile.title()}Shell" if heritage else APP_ID)
            super().__init__(application_id=app_id,
                             flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
            self.bar = None
            self.menu = None
            self.apps = ()
            self.window_buttons = {}
            self._visible_window_ids = ()
            self._overflow_windows = ()
            self._win7_visible_groups = ()
            self._win7_group_members = {}
            self._win7_group_signature = {}
            self._win7_group_buttons = {}
            self._win7_snap = None
            self._win7_preview = None
            self._win7_preview_group = None
            self._win7_preview_timer = 0
            self._win7_peek_timer = 0
            self._win7_peek_active = False
            self._menu_focused = False
            self._start_open_menus = set()
            self._tray = None
            self._status_pending = False
            self._status_widgets = {}
            self._last_status = None
            self.luna_tray = None
            self.luna_balloon = None
            self._luna_volume_monitor = None
            self._luna_volume_signals = ()
            self._luna_start_state = None
            self._luna_taskbar_options = None
            self._luna_taskbar_dialog = None
            self._luna_quick_launch = None
            self._luna_quick_separator = None
            self._luna_clock_button = None
            self._luna_grouped_mode = False
            self._luna_group_buttons = {}
            self._luna_group_members = {}
            self._volume_programmatic = False
            self._volume_write_source = 0
            self._volume_writing = False
            self._volume_queued = None
            self._mute_writing = False
            self._pin_count = 0
            self._pinned_ids = ()
            self._pin_config_path = pin_file("windows10" if ten else profile)
            self._task_capacity = 0
            self.show_desktop_button = None
            self._classic98_taskbar_options = None
            self._classic98_taskbar_dialog = None
            self.classic98_quick_launch = None
            self.classic98_clock_button = None
            self._app_page_size = 24
            self._smoke = False
            self._smoke_failed = False
            self._capture_gallery = False
            self._capture_variant = ""
            self._chrome_settings = None
            self._popup_hide_sources = {"menu": 0, "control": 0}

        def do_startup(self):
            Gtk.Application.do_startup(self)
            if profile in ("frutiger", "winclassic", "chromeos"):
                # GTK's default Gdk screen exists after application startup;
                # before it, IconTheme.get_default() may silently be None.
                # Install scoped search path to show original Aqua icons even
                # in preview Xvfb without changing global XFCE preferences.
                icon_theme = Gtk.IconTheme.get_default()
                if icon_theme is not None:
                    icon_theme.append_search_path(str(project_root() / "assets/icons"))
                settings = Gtk.Settings.get_default()
                if settings is not None:
                    settings.set_property("gtk-icon-theme-name", (
                        "RiceHub-Classic-Icons" if profile == "winclassic" else
                        "RiceHub-Chrome-Icons" if profile == "chromeos" else
                        "RiceHub-Frutiger-Icons"))
            for name in ("toggle-menu", "toggle-control"):
                action = Gio.SimpleAction.new(name, None)
                action.connect("activate", self._on_fast_action, name)
                self.add_action(action)

        def _on_fast_action(self, _action, _parameter, name):
            self._remote_toggle(name)

        def _remote_toggle(self, name):
            if self.bar is None:
                self.activate()
            if name == "toggle-control":
                self._toggle_actions()
            else:
                self._toggle_menu()

        def do_command_line(self, command_line):
            args = command_line.get_arguments()
            if "--quit" in args:
                if self.bar is not None:
                    self.quit()
                return 0
            if "--toggle-menu" in args or "--control" in args or (ten and "--actions" in args):
                self._remote_toggle("toggle-control" if "--control" in args or (ten and "--actions" in args)
                                    else "toggle-menu")
                return 0
            self._smoke = "--smoke-test" in args
            self._capture_gallery = "--capture-gallery" in args
            self._capture_workspace = "--capture-workspace" in args
            self._capture_variant = "-1024" if (
                profile in ("winxp", "aero", "frutiger", "winclassic", "windows10", "chromeos")
                and os.environ.get("RICEBOWL_CAPTURE_SIZE") == "1024") else ""
            self.activate()
            if self._smoke:
                GLib.timeout_add(850, self._smoke_check)
            if self._capture_gallery:
                GLib.timeout_add(950, self._capture_start)
            if self._capture_workspace:
                GLib.timeout_add(950, self._capture_workspace_start)
            return 0

        def do_activate(self):
            if self.bar is not None:
                self._toggle_menu()
                return
            provider = Gtk.CssProvider()
            extra_css = TEN_CSS if ten else HERITAGE_CSS[profile] if heritage else b""
            if profile == "chromeos":
                from .chrome_shell import CSS as CHROME_CSS
                extra_css += CHROME_CSS
            provider.load_from_data(CSS + extra_css)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self._provider = provider
            self.apps = app_catalog(Gio)
            try:
                saved = load_pins(self._pin_config_path)
            except (PinConfigError, OSError) as exc:
                logging.getLogger(__name__).warning("Aero pins are unavailable: %s", exc)
                saved = None
            self._pinned_ids = default_pins(self.apps) if saved is None else saved
            if profile == "winclassic":
                from .classic98_taskbar_settings import (
                    DEFAULT_OPTIONS, TaskbarSettingsError, load_options,
                )
                try:
                    self._classic98_taskbar_options = load_options()
                except (OSError, TaskbarSettingsError) as exc:
                    logging.getLogger(__name__).warning(
                        "Windows 98 taskbar settings unavailable: %s", exc)
                    self._classic98_taskbar_options = dict(DEFAULT_OPTIONS)
            if profile == "winxp":
                from .luna_start_state import StartState, load_start_state
                from .luna_taskbar_settings import (
                    DEFAULT_OPTIONS as LUNA_OPTIONS, LunaSettingsError, load_options as load_luna_options,
                )

                try:
                    self._luna_start_state = load_start_state()
                except (OSError, ValueError) as exc:
                    logging.getLogger(__name__).warning("XP Start preferences unavailable: %s", exc)
                    self._luna_start_state = StartState()
                try:
                    self._luna_taskbar_options = load_luna_options()
                except (OSError, LunaSettingsError) as exc:
                    logging.getLogger(__name__).warning("XP taskbar preferences unavailable: %s", exc)
                    self._luna_taskbar_options = dict(LUNA_OPTIONS)
            if self._capture_gallery or self._capture_workspace:
                self._capture_background()
            self._create_taskbar()
            self._create_menu()
            self._create_actions()
            self.connect("shutdown", self._shutdown)
            if profile in ("winxp", "aero"):
                self._luna_install_volume_notifications()
            self._window_tracker = create_window_tracker(GLib.idle_add, self._windows_changed)
            if profile == "aero" and self._window_tracker is not None:
                self._win7_snap = WindowSnapController(self._window_tracker.wnck)
            if self.show_desktop_button is not None:
                self.show_desktop_button.set_sensitive(self._window_tracker is not None)
            screen = Gdk.Screen.get_default()
            screen.connect("monitors-changed", self._screen_changed)
            screen.connect("size-changed", self._screen_changed)
            self._catalog_monitor = Gio.AppInfoMonitor.get()
            self._catalog_monitor.connect("changed", self._catalog_changed)

        def _publish_ready(self, *_args):
            """Expose readiness on D-Bus only when GTK maps the actual taskbar."""
            if self.lookup_action("ricebowl-ready") is None:
                self.add_action(Gio.SimpleAction.new("ricebowl-ready", None))
            return False

        def _smoke_check(self):
            """Exercise actual GTK construction, menu open/search and close under Xvfb."""
            try:
                assert self.bar is not None and self.bar.get_visible()
                assert self.menu is not None and not self.menu.get_visible()
                if profile in ("winclassic", "winxp", "aero", "windows10"):
                    context_menu = {
                        "winclassic": self._classic98_taskbar_menu,
                        "winxp": self._luna_taskbar_menu,
                        "aero": self._win7_taskbar_menu,
                        "windows10": self._ten_taskbar_menu,
                    }[profile]()
                    task_label = "Start Task Manager" if profile == "aero" else "Task Manager"
                    manager_item = next((item for item in context_menu.get_children()
                                         if isinstance(item, Gtk.MenuItem)
                                         and item.get_label() == task_label), None)
                    assert manager_item is not None, "Task Manager is missing from taskbar context menu"
                    assert manager_item.get_sensitive() == (preferred_task_manager() is not None), (
                        "Task Manager should be disabled if neither supported system utility exists")
                    context_menu.destroy()
                self._toggle_menu()
                assert self.menu.get_visible()
                self.search.set_text("unlikely-app-id-ricehub-smoke-39083")
                assert self.results.get_children()
                if profile == "winclassic":
                    # A Gtk.MenuButton's cascade grabs X11 focus. In the old
                    # shell this closed Start 650 ms after the pointer entered.
                    main = self.menu.get_child().get_children()[-1]
                    programs_button = next(child for child in main.get_children()
                                           if isinstance(child, Gtk.MenuButton))
                    programs_button.set_active(True)
                    for _ in range(20):
                        if not Gtk.events_pending():
                            break
                        Gtk.main_iteration_do(False)
                    assert self._start_open_menus, "Win98 Programs popup was not tracked"
                    self._menu_focus_out()
                    self._cancel_popup_hide("menu")
                    self._hide_if_unfocused("menu")
                    assert self.menu.get_visible(), "Win98 Start closed while Programs was open"
                    programs_button.set_active(False)
                if profile == "winxp":
                    self.search.set_text("")
                    self._reveal_luna_search()
                    self.search.grab_focus()
                    buttons = [child for child in self.results.get_children()
                               if isinstance(child, Gtk.Button) and child.get_visible()]
                    if buttons:
                        down = type("Key", (), {"keyval": Gdk.KEY_Down, "state": 0})()
                        assert self._search_key(down)
                        assert buttons[0].is_focus()
                        if len(buttons) > 1:
                            assert self._search_key(down)
                            assert buttons[1].is_focus()
                        letter = type("Key", (), {"keyval": Gdk.KEY_z, "state": 0})()
                        assert self._search_key(letter)
                        assert self.search.is_focus()
                        assert self.search.get_text() == "z"
                self._hide_menu()
                assert not self.menu.get_visible()
                assert self.lookup_action("toggle-menu") is not None
                assert self.lookup_action("toggle-control") is not None
                self.lookup_action("toggle-menu").activate(None)
                assert self.menu.get_visible()
                self.lookup_action("toggle-menu").activate(None)
                assert not self.menu.get_visible()
                self._toggle_actions()
                assert self.actions.get_visible()
                if profile == "windows10":
                    self._toggle_ten_network()
                    assert self.ten_network.window.get_visible()
                    assert self.ten_network.networks is not None
                    self.ten_network.hide()
                    self._open_ten_settings("network")
                    assert self.ten_settings.window.get_visible()
                    assert self.ten_settings.stack.get_visible_child_name() == "network"
                    self.ten_settings.navigate("sound")
                    assert self.ten_settings.stack.get_visible_child_name() == "sound"
                    self.ten_settings.hide()
                    self._toggle_ten_task_view()
                    assert self.ten_task_view.window.get_visible()
                    self.ten_task_view.hide()
                    self._toggle_actions()
                    assert self.actions.get_visible()
                if profile == "chromeos":
                    from .chrome_settings import ACTIONS
                    from .chrome_quick_settings import calendar_today
                    assert self.chrome_controller is not None
                    network_button = self._status_widgets["network"][0]
                    network_button.clicked()
                    assert self.chrome_quick_stack.get_visible_child_name() == "Network"
                    network_button.clicked()
                    assert not self.actions.get_visible()
                    network_button.clicked()
                    assert self.actions.get_visible()
                    assert self.chrome_quick_stack.get_visible_child_name() == "Network"
                    self._toggle_chrome_calendar()
                    assert self.chrome_quick_stack.get_visible_child_name() == "Calendar"
                    assert self.chrome_quick_calendar.get_date() == calendar_today()
                    self._action_key(type("Event", (), {"keyval": Gdk.KEY_Escape})())
                    assert self.chrome_quick_stack.get_visible_child_name() == "overview"
                    self._toggle_chrome_notifications()
                    assert self.chrome_quick_stack.get_visible_child_name() == "Notifications"
                    assert self.chrome_notifications is not None
                    assert self.chrome_notifications_badge is not None
                    self._action_key(type("Event", (), {"keyval": Gdk.KEY_Escape})())
                    assert self.chrome_quick_stack.get_visible_child_name() == "overview"
                    self.chrome_quick_show_page("Network")
                    assert self.chrome_quick_stack.get_visible_child_name() == "Network"
                    self.chrome_quick_show_page("Bluetooth")
                    assert self.chrome_quick_stack.get_visible_child_name() == "Bluetooth"
                    self._action_key(type("Event", (), {"keyval": Gdk.KEY_Escape})())
                    assert self.chrome_quick_stack.get_visible_child_name() == "overview"
                    self._open_chrome_settings(section="Device")
                    assert self._chrome_settings.active_section == "Device"
                    sound = next(action for action in ACTIONS if action.name == "Sound")
                    self._chrome_settings.show_detail(sound)
                    assert self._chrome_settings.active_action == sound
                    assert len(self._chrome_settings._native_panels) == 2
                    self._chrome_settings.back()
                    assert self._chrome_settings.active_section == "Device"
                    assert not self._chrome_settings._native_panels
                    wifi = next(action for action in ACTIONS if action.name == "Connections")
                    self._chrome_settings.show_detail(wifi)
                    assert len(self._chrome_settings._native_panels) == 1
                    self._chrome_settings.back()
                    self._chrome_settings.search.set_text("unlikely-ricebowl-setting")
                    assert self._chrome_settings.content.get_children()
                    self._chrome_settings.window.hide()
                    self._toggle_actions()
                self._toggle_actions()
                assert not self.actions.get_visible()
                if profile == "winclassic":
                    assert self.classic98_controller is not None
                    assert set(self.classic98_tray_popups) == {
                        "audio", "network", "battery", "clock", "bluetooth"}
                    for kind in self.classic98_tray_popups:
                        self.classic98_tray_show(kind)
                        assert self.classic98_tray_popups[kind].get_visible()
                        self.classic98_tray_show(kind)
                        assert not self.classic98_tray_popups[kind].get_visible()
                    from .classic98_desktop import Classic98Desktop
                    self.classic98_desktop = Classic98Desktop(self, Gtk)
                    self.classic98_desktop.show()
                    assert self.classic98_desktop.window.get_visible()
                    self.classic98_desktop.hide()
                if profile == "winxp":
                    if self._tray is not None:
                        assert self._tray.theme == "luna"
                        assert self._tray.preferences is not None
                        assert self._tray.overflow_button.get_style_context().has_class(
                            "luna-tray-chevron")
                        saved_dialog_run = Gtk.Dialog.run
                        def cancel_luna_tray_preferences(dialog):
                            assert dialog.get_style_context().has_class(
                                "luna-tray-customize")
                            return Gtk.ResponseType.CANCEL
                        try:
                            Gtk.Dialog.run = cancel_luna_tray_preferences
                            self._tray._open_preferences()
                        finally:
                            Gtk.Dialog.run = saved_dialog_run
                    self.luna_open_taskbar_properties()
                    assert self._luna_taskbar_dialog is not None
                    assert self._luna_taskbar_dialog.get_style_context().has_class(
                        "luna-taskbar-properties")
                    self._luna_taskbar_dialog.response(Gtk.ResponseType.CANCEL)
                    assert self._luna_taskbar_dialog is None
                    sample_windows = tuple(WindowSnapshot(
                        xid=10000 + index, title="Browser " + str(index),
                        minimized=False, mini_icon=None, group_id="xp-smoke-browser")
                        for index in range(self._task_capacity + 2))
                    self._luna_windows_grouped(sample_windows, sample_windows[-1])
                    assert len(self._luna_group_buttons) == 1
                    assert tuple(self._luna_group_members.values())[0].xids == tuple(
                        item.xid for item in sample_windows)
                    self._windows_changed((), None)
                    self._luna_open_help()
                    assert self._luna_help_dialog is not None
                    assert self._luna_help_dialog.get_style_context().has_class(
                        "luna-help-window")
                    from .luna_help import show_system
                    show_system(self, Gtk)
                    assert self._luna_system_dialog is not None
                    self._luna_system_dialog.response(Gtk.ResponseType.CLOSE)
                    assert self._luna_system_dialog is None
                    self._luna_help_dialog.response(Gtk.ResponseType.CLOSE)
                    assert self._luna_help_dialog is None
                    original_dialog_run = Gtk.Dialog.run
                    def cancel_luna_run(dialog):
                        assert dialog.get_title() == "Run"
                        assert dialog.get_style_context().has_class("luna-run-dialog")
                        return Gtk.ResponseType.CANCEL
                    try:
                        Gtk.Dialog.run = cancel_luna_run
                        self._luna_open_run()
                    finally:
                        Gtk.Dialog.run = original_dialog_run
                    assert self.luna_control_stack.get_visible_child_name() == "categories"
                    assert set(self.luna_tray.popovers) == {
                        "audio", "network", "battery", "clock", "bluetooth"}
                    for popup in self.luna_tray.popovers.values():
                        assert popup.get_style_context().has_class("luna-tray-popup")
                        # Native GTK windows escape the dock's 40px clipping
                        # region; Gtk.Popover cannot reliably do so on X11.
                        assert isinstance(popup, Gtk.Window)
                        assert popup.get_type_hint() == Gdk.WindowTypeHint.UTILITY
                    assert self.luna_programs_popup.get_style_context().has_class("luna-popup")
                    assert self.luna_recent_popup.get_style_context().has_class("luna-popup")
                    self.luna_control_show_category("Appearance and Themes")
                    assert self.luna_control_stack.get_visible_child_name() == "detail"
                    assert len(self.luna_control_stack.get_visible_child().get_children()) >= 4
                    self.luna_control_back.clicked()
                    assert self.luna_control_stack.get_visible_child_name() == "categories"
                    self.luna_control_search.set_text("keyboard")
                    self.luna_control_search.emit("search-changed")
                    assert self.luna_control_stack.get_visible_child_name() == "search"
                    self.luna_control_search.set_text("not-a-real-setting-39083")
                    self.luna_control_search.emit("search-changed")
                    assert self.luna_control_stack.get_visible_child_name() == "search"
                    self.luna_control_search.set_text("")
                    self.luna_control_search.emit("search-changed")
                    self.luna_control_switch.clicked()
                    assert self.luna_control_stack.get_visible_child_name() == "classic"
                    self.luna_control_switch.clicked()
                    assert self.luna_control_stack.get_visible_child_name() == "categories"
                    for name in ("audio", "network", "battery", "bluetooth", "clock"):
                        self.luna_tray.toggle(name)
                        assert self.luna_tray.popovers[name].get_visible()
                        self.luna_tray.toggle(name)
                        assert not self.luna_tray.popovers[name].get_visible()
                if profile == "aero":
                    if self._tray is not None:
                        assert 0 <= self._tray.visible_limit <= 8
                        assert self._tray.preferences is not None
                        assert self._tray.overflow_button is not None
                        assert self._tray.overflow_button.get_style_context().has_class(
                            "win7-tray-chevron")
                        # Construct the actual configuration dialog in virtual
                        # X11. Auto-cancel it; the smoke must not write any
                        # real user preferences or block on manual input.
                        saved_dialog_run = Gtk.Dialog.run
                        def cancel_preferences(dialog):
                            assert dialog.get_style_context().has_class(
                                "win7-tray-customize")
                            assert dialog.get_title() == "Customize Notification Area Icons"
                            return Gtk.ResponseType.CANCEL
                        try:
                            Gtk.Dialog.run = cancel_preferences
                            self._tray._open_preferences()
                        finally:
                            Gtk.Dialog.run = saved_dialog_run
                    assert set(self.luna_tray.popovers) == {
                        "audio", "network", "battery", "clock", "bluetooth", "alerts"}
                    for popup in self.luna_tray.popovers.values():
                        assert popup.get_style_context().has_class("win7-tray-popup")
                        assert isinstance(popup, Gtk.Window)
                    assert self.luna_tray._alerts_button is not None
                    assert self.luna_tray._alerts_button.get_style_context().has_class(
                        "win7-alert-button")
                    assert self.luna_balloon.css_prefix == "win7-balloon"
                    for name in ("audio", "network", "battery", "clock", "bluetooth", "alerts"):
                        self.luna_tray.toggle(name)
                        assert self.luna_tray.popovers[name].get_visible()
                        self.luna_tray.toggle(name)
                        assert not self.luna_tray.popovers[name].get_visible()
                    assert len(self.win7_panel_rows) == 8
                    self.win7_panel_search.set_text("power")
                    # Gtk.SearchEntry emits search-changed 150ms after edits.
                    # Drive the event explicitly in this synchronous Xvfb smoke.
                    self.win7_panel_search.emit("search-changed")
                    assert sum(row.get_visible() for _, row in self.win7_panel_rows) == 1
                    self.win7_panel_search.set_text("not-a-real-setting-39083")
                    self.win7_panel_search.emit("search-changed")
                    assert not any(row.get_visible() for _, row in self.win7_panel_rows)
                    self.win7_panel_search.set_text("")
                    self.win7_panel_search.emit("search-changed")
                    self.win7_panel_view_by.set_active(1)
                    assert self.win7_panel_view_by.get_active() == 1
                    assert self.win7_panel_icons_grid.get_visible(), (
                        "Win7 icon view container is hidden after selecting Large icons")
                    assert any(row.get_visible()
                               for row in self.win7_panel_icons_grid.get_children()), (
                        "Win7 icon view has no visible entries")
                    self.win7_panel_view_by.set_active(2)
                    assert self.win7_panel_view_by.get_active() == 2
                    assert self.win7_panel_icons_grid.get_visible(), (
                        "Win7 icon view container is hidden after selecting Small icons")
                    self.win7_panel_view_by.set_active(0)
                    self.win7_panel_show_category(self.win7_panel_rows[0][0])
                    assert self.win7_panel_back.get_sensitive()
                    assert self.win7_panel_details.get_visible(), (
                        "Win7 category page hidden despite populated task links")
                    assert any(child.get_visible()
                               for child in self.win7_panel_details.get_children())
                    category = self.win7_panel_rows[0][0]
                    self.win7_panel_show_task(category, category.tasks[0])
                    assert self.win7_panel_details.get_visible(), (
                        "Win7 task details invisible after navigating into a setting")
                    assert any(child.get_visible()
                               for child in self.win7_panel_details.get_children())
                    assert self.win7_panel_forward.get_sensitive() is False
                    self.win7_panel_back.clicked()
                    assert self.win7_panel_forward.get_sensitive()
                    self.win7_panel_back.clicked()
                    assert not self.win7_panel_back.get_sensitive()
                    self.win7_panel_forward.clicked()
                    assert self.win7_panel_back.get_sensitive()
                    # Run the native group button / preview construction path
                    # even if the CI virtual desktop has no ordinary app windows.
                    first = WindowSnapshot(987654, "First window", False, None, "ricebowl-ci",
                                           needs_attention=True)
                    second = WindowSnapshot(987655, "Second window", False, None, "ricebowl-ci")
                    self._win7_windows_changed((first, second), None)
                    assert self._win7_visible_groups == ("app:ricebowl-ci",)
                    button = self._win7_group_buttons["app:ricebowl-ci"][0]
                    assert button.get_visible()
                    assert button.get_style_context().has_class("win7-task-attention")
                    self._win7_windows_changed((first, second), second)
                    assert button.get_style_context().has_class("win7-task-attention")
                    self._win7_windows_changed((first, second), first)
                    assert not button.get_style_context().has_class("win7-task-attention")
                    menu = self._win7_group_menu("app:ricebowl-ci")
                    assert menu is not None
                    assert any(item.get_label() == "Arrange windows"
                               and item.get_submenu() is not None
                               for item in menu.get_children() if isinstance(item, Gtk.MenuItem))
                    menu.destroy()
                    taskbar_menu = self._win7_taskbar_menu()
                    taskbar_labels = {item.get_label() for item in taskbar_menu.get_children()
                                      if isinstance(item, Gtk.MenuItem)}
                    assert {"Cascade windows", "Show windows stacked",
                            "Show windows side by side", "Undo window arrangement",
                            "Start Task Manager"} <= taskbar_labels
                    taskbar_menu.destroy()
                    if self.pinned_box.get_children():
                        pinned_button = self.pinned_box.get_children()[0]
                        assert pinned_button.drag_source_get_target_list() is not None
                        assert pinned_button.drag_dest_get_target_list() is not None
                    self._win7_show_preview("app:ricebowl-ci", button)
                    assert self._win7_preview is not None
                    self._win7_stop_preview()
                    self._win7_windows_changed((), None)
                if profile == "frutiger":
                    # Reproduce the Settings dead-end under an actual GTK/Xvfb
                    # event environment, not only through mocked tab objects.
                    assert self.frutiger_controller is not None
                    assert self.aqua_notifications_button is not None
                    assert self.aqua_bluetooth_button is not None
                    self._toggle_menu()
                    assert self.menu.get_visible()
                    for name in ("Settings", "Places", "Settings", "Apps"):
                        self._frutiger_tab_buttons[name].clicked()
                        # GTK3 crossfade transitions can defer the visible-child
                        # property until the next main-context iteration. A
                        # synchronous artificial click sequence must give GTK
                        # the same event-loop opportunity as real user clicks.
                        for _step in range(20):
                            while Gtk.events_pending():
                                Gtk.main_iteration_do(False)
                            if self.aqua_stack.get_visible_child_name() == name:
                                break
                            GLib.usleep(15000)
                        assert self.aqua_stack.get_visible_child_name() == name, (
                            "Frutiger tab " + name + " selected but stack shows " +
                            str(self.aqua_stack.get_visible_child_name()))
                    self._frutiger_tab_buttons["Settings"].clicked()
                    self._frutiger_back_to_apps.clicked()
                    assert self.aqua_stack.get_visible_child_name() == "Apps"
                    if os.environ.get("RICEHUB_AQUA_NAV_NATIVE") == "1":
                        # Programmatic .clicked() alone cannot detect a page
                        # overlay intercepting real pointer input. Exercise
                        # the X11 hit regions at 1024x768 as a user would.
                        import subprocess

                        def pointer_click(widget):
                            while Gtk.events_pending():
                                Gtk.main_iteration_do(False)
                            surface = widget.get_toplevel()
                            offset = widget.translate_coordinates(surface, 0, 0)
                            origin = surface.get_window().get_root_origin()
                            assert offset is not None
                            point = (origin[0] + offset[0] + widget.get_allocated_width() // 2,
                                     origin[1] + offset[1] + widget.get_allocated_height() // 2)
                            subprocess.run(("xdotool", "mousemove", "--sync", str(point[0]),
                                            str(point[1]), "click", "1"),
                                           check=True, timeout=4, capture_output=True)
                            for _step in range(40):
                                while Gtk.events_pending():
                                    Gtk.main_iteration_do(False)
                                GLib.usleep(10000)
                            return point

                        for page in ("Settings", "Places", "Settings", "Apps", "Settings", "Apps"):
                            button = self._frutiger_tab_buttons[page]
                            point = pointer_click(button)
                            print(f"Aqua pointer nav: click {page} at {point}, "
                                  f"window={self.menu.get_position()} {self.menu.get_size()}",
                                  flush=True)
                            assert self.menu.get_visible() and self.aqua_stack.get_visible_child_name() == page, (
                                f"Real X11 click on {page} did not navigate: "
                                f"visible={self.menu.get_visible()}, "
                                f"page={self.aqua_stack.get_visible_child_name()}")
                        pointer_click(self._frutiger_tab_buttons["Settings"])
                        pointer_click(self._frutiger_back_to_apps)
                        assert self.aqua_stack.get_visible_child_name() == "Apps", (
                            "Pinned Settings exit to Apps does not receive pointer input")
                        pointer_click(self._frutiger_tab_buttons["Settings"])
                        pointer_click(self._frutiger_back_to_places)
                        assert self.aqua_stack.get_visible_child_name() == "Places", (
                            "Pinned Settings exit to Places does not receive pointer input")
                        # Selecting Settings is not enough: a real row must
                        # launch a WM-managed Control Center, close, then let
                        # the reopened launcher navigate to Places and Apps.
                        pointer_click(self._frutiger_tab_buttons["Settings"])
                        settings_content = self.aqua_stack.get_child_by_name("Settings")
                        settings_content = settings_content.get_child().get_child()
                        connection_row = settings_content.get_children()[0]
                        pointer_click(connection_row)
                        assert self.actions.get_visible() and not self.menu.get_visible(), (
                            "Aqua Settings selection must open the Control Center, not trap the launcher")
                        # The same Settings entry must behave when the
                        # independent Control Center is already open. The
                        # launcher has keep-above enabled and must not cover
                        # the window on a subsequent invocation.
                        self._toggle_menu()
                        pointer_click(self._frutiger_tab_buttons["Settings"])
                        pointer_click(connection_row)
                        assert self.actions.get_visible() and not self.menu.get_visible(), (
                            "Existing Aqua Control Center remains behind a stuck launcher")
                        # Do not depend on XFWM's deferred focus-out timer:
                        # the explicit open-Settings action must synchronously
                        # dismiss an already-visible Aqua launcher.
                        self._toggle_menu()
                        assert self.menu.get_visible()
                        self._show_aqua_control("connections")
                        assert not self.menu.get_visible(), (
                            "Aqua Settings reopened while already visible must dismiss the launcher")
                        self._hide_actions()
                        self._toggle_menu()
                        for page in ("Places", "Apps"):
                            pointer_click(self._frutiger_tab_buttons[page])
                            assert self.aqua_stack.get_visible_child_name() == page, (
                                f"Aqua {page} unresponsive after closing Settings")
                        self._hide_menu()
                        for kind in ("network", "audio", "battery", "bluetooth"):
                            trigger = (self.aqua_bluetooth_button if kind == "bluetooth"
                                       else self._status_widgets[kind][0])
                            pointer_click(trigger)
                            assert self._aqua_flyouts.popovers[kind].get_visible(), (
                                f"Real X11 click on Aqua {kind} tray icon opened no flyout")
                            self._aqua_flyouts.popovers[kind].popdown()
                        pointer_click(self.aqua_drives_button)
                        assert self._aqua_drives.popover.get_visible(), (
                            "Real X11 click on Aqua drives icon opened no flyout")
                        self._aqua_drives.popover.popdown()
                        pointer_click(self.aqua_notifications_button)
                        assert self._aqua_notifications.popover.get_visible(), (
                            "Real X11 click on Aqua notifications icon opened no flyout")
                        self._aqua_notifications.popover.popdown()
                        pointer_click(self.aqua_clock_button)
                        assert self._aqua_calendar.popover.get_visible(), (
                            "Real X11 click on Aqua calendar icon opened no flyout")
                        self._aqua_calendar.popover.popdown()
                        pointer_click(self.start_button)
                        assert self.menu.get_visible(), (
                            "Real X11 click on Aqua Start icon opened no launcher")
                        self._hide_menu()
                        pins = self.pinned_box.get_children()
                        if pins:
                            launched = []
                            original_launch = self._launch
                            try:
                                self._launch = lambda app: launched.append(app)
                                pointer_click(pins[0])
                            finally:
                                self._launch = original_launch
                            assert launched, "Real X11 click on Aqua app pin was ignored"
                    self._show_aqua_control("sound", "Input & output devices")
                    assert self.actions.get_visible()

                    def walk(widget):
                        yield widget
                        if isinstance(widget, Gtk.Container):
                            for child in widget.get_children():
                                yield from walk(child)

                    assert any(widget.get_style_context().has_class("aqua-native-panel")
                               for widget in walk(self.actions))
                    self._hide_actions()
                    self.aqua_notifications_button.clicked()
                    assert self._aqua_notifications.popover.get_visible()
                    self._aqua_notifications.popover.popdown()
                    self._apply_status(None)
                    assert self._status_widgets["network"][0].get_sensitive()
                    assert self._status_widgets["battery"][0].get_sensitive()
                    self.aqua_bluetooth_button.clicked()
                    assert self._aqua_flyouts.popovers["bluetooth"].get_visible()
                    self._status_widgets["network"][0].clicked()
                    assert self._aqua_flyouts.popovers["network"].get_visible()
                    self._aqua_flyouts.popovers["network"].popdown()
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_background(self):
            """A disposable wallpaper fixture for virtual-X11 screenshots only."""
            rect = self._desktop_rect()
            fixture = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            fixture.set_title("Virtual XFCE wallpaper fixture")
            fixture.set_decorated(False)
            fixture.set_skip_taskbar_hint(True)
            fixture.set_skip_pager_hint(True)
            fixture.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
            fixture.set_keep_below(True)
            image = project_root() / "assets/wallpapers" / (heritage.wallpaper if heritage else "ten-blue.jpg" if ten else "aero-seven-night.jpg")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(image), rect.width, rect.height, False)
            fixture.add(Gtk.Image.new_from_pixbuf(pixbuf))
            fixture.set_default_size(rect.width, rect.height)
            fixture.move(rect.x, rect.y)
            fixture.show_all()
            fixture.get_window().lower()
            self._capture_fixture = fixture

        def _capture_start(self):
            try:
                self._toggle_menu()
                assert self.menu.get_visible()
                GLib.timeout_add(450, self._capture_menu)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_screen(self, name):
            root = Gdk.get_default_root_window()
            bounds = root.get_geometry()
            pixels = Gdk.pixbuf_get_from_window(root, 0, 0, bounds.width, bounds.height)
            if pixels is None:
                raise RuntimeError("Virtual X11 screen could not be captured")
            destination = project_root() / "screenshots" / name
            pixels.savev(str(destination), "png", [], [])

        def _capture_menu(self):
            try:
                self._assert_popup_on_monitor(self.menu)
                if profile == "winxp":
                    self._assert_luna_run_link_visible()
                self._capture_screen(f"ricebowl-{profile}-start-0.9.1{self._capture_variant}.png")
                if profile == "winxp":
                    self.luna_browse.clicked()
                    GLib.timeout_add(350, self._capture_luna_flyout)
                else:
                    self._hide_menu()
                    self._toggle_actions()
                    assert self.actions.get_visible()
                    GLib.timeout_add(400, self._capture_actions)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_luna_flyout(self):
            try:
                assert self.luna_programs_popup.get_mapped(), "XP All Programs popup not mapped"
                self._assert_luna_popup_above_taskbar(self.luna_programs_popup)
                category = next((item for item in self.luna_programs_popup.get_children()
                                 if isinstance(item, Gtk.MenuItem) and item.get_submenu()), None)
                if category:
                    # A real pointer hover also validates the submenu placement;
                    # programmatic select() lacks an X11 trigger event.
                    import subprocess

                    x, y = category.get_window().get_root_origin()
                    allocation = category.get_allocation()
                    subprocess.run(["xdotool", "mousemove", str(x + allocation.x +
                                    allocation.width // 2), str(y + allocation.y +
                                    allocation.height // 2)], check=True, timeout=3)
                self._luna_capture_submenu = category.get_submenu() if category else None
                GLib.timeout_add(600, self._capture_luna_nested)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_luna_nested(self):
            try:
                submenu = self._luna_capture_submenu
                if submenu is not None:
                    assert submenu.get_mapped(), "XP category submenu did not open on hover"
                    self._assert_luna_popup_above_taskbar(submenu)
                    parent_x, _y = self.luna_programs_popup.get_window().get_root_origin()
                    child_x, _y = submenu.get_window().get_root_origin()
                    assert (child_x >= parent_x + self.luna_programs_popup.get_allocated_width() - 4), (
                        "XP submenu must cascade beside its parent, not cover categories")
                self._capture_screen(f"ricebowl-winxp-programs-0.9.1{self._capture_variant}.png")
                self._hide_menu()
                self._toggle_actions()
                GLib.timeout_add(400, self._capture_actions)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_actions(self):
            try:
                self._assert_popup_on_monitor(self.actions)
                if profile == "winxp":
                    self._assert_control_footer_visible()
                self._capture_screen(f"ricebowl-{profile}-controls-0.9.1{self._capture_variant}.png")
                if profile == "winxp":
                    self.luna_control_show_category("Appearance and Themes")
                    GLib.timeout_add(350, self._capture_luna_detail)
                    return False
                if profile == "chromeos" and not self._capture_variant:
                    # Include *secondary* ChromeOS screens in the gallery: the
                    # shell overview alone misses the native notification log
                    # and independent Settings window. Never inject fake alerts.
                    self.chrome_quick_show_page("Notifications")
                    GLib.timeout_add(1100, self._capture_chrome_notifications)
                    return False
                if profile == "aero":
                    self._hide_actions()
                    self.luna_tray.toggle("alerts")
                    GLib.timeout_add(780, self._capture_aero_alerts)
                    return False
                if profile == "windows10":
                    self._hide_actions()
                    self._open_ten_settings("home")
                    GLib.timeout_add(650, self._capture_ten_settings_home)
                    return False
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_ten_settings_home(self):
            try:
                settings = self.ten_settings
                assert settings.window.get_mapped() and settings.current == "home"
                assert settings.home_search.get_visible() and not settings.sidebar.get_visible()
                home_scroll = settings.stack.get_child_by_name("home")
                adjustment = home_scroll.get_vadjustment()
                assert adjustment.get_upper() <= adjustment.get_page_size() + 3, (
                    "Windows 10 category home clips its bottom row at the capture size")
                self._capture_screen(
                    f"ricebowl-windows10-settings-home-0.9.1{self._capture_variant}-extra.png")
                settings.navigate("sound")
                GLib.timeout_add(400, self._capture_ten_settings_detail)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_ten_settings_detail(self):
            try:
                settings = self.ten_settings
                assert settings.window.get_mapped() and settings.current == "sound"
                assert settings.sidebar.get_visible() and settings._sliders["audio"].get_visible()
                self._capture_screen(
                    f"ricebowl-windows10-settings-sound-0.9.1{self._capture_variant}-extra.png")
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_aero_alerts(self):
            try:
                popup = self.luna_tray.popovers["alerts"]
                assert popup.get_mapped(), "Windows 7 Action Center did not map"
                rect = self._desktop_rect()
                x, y = popup.get_window().get_root_origin()
                width, height = popup.get_size()
                assert (rect.x <= x and rect.y <= y and
                        x + width <= rect.x + rect.width and
                        y + height <= rect.y + rect.height - panel_height), (
                        f"Windows 7 Action Center offscreen: {x},{y} {width}x{height}")
                self._capture_screen(
                    f"ricebowl-aero-action-center-0.9.1{self._capture_variant}-extra.png")
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_chrome_notifications(self):
            try:
                assert self.chrome_quick_stack.get_visible_child_name() == "Notifications"
                self._assert_popup_on_monitor(self.actions)
                self._capture_screen("ricebowl-chromeos-notifications-0.9.1-extra.png")
                self._open_chrome_settings(section="Device")
                GLib.timeout_add(450, self._capture_chrome_settings)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_chrome_settings(self):
            try:
                assert self._chrome_settings is not None
                assert self._chrome_settings.window.get_visible()
                self._capture_screen("ricebowl-chromeos-settings-0.9.1-extra.png")
                self._chrome_settings.window.hide()
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_luna_detail(self):
            try:
                assert self.luna_control_stack.get_visible_child_name() == "detail"
                self._capture_screen(f"ricebowl-winxp-detail-0.9.1{self._capture_variant}.png")
                self.luna_control_switch.clicked()
                GLib.timeout_add(350, self._capture_luna_classic)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_luna_classic(self):
            try:
                assert self.luna_control_stack.get_visible_child_name() == "classic"
                self._capture_screen(f"ricebowl-winxp-classic-0.9.1{self._capture_variant}.png")
                self._hide_actions()
                self.luna_tray.toggle("audio")
                GLib.timeout_add(460, self._capture_luna_audio)
                return False
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_luna_tray(self, name):
            popup = self.luna_tray.popovers[name]
            assert popup.get_mapped(), f"XP {name} tray popup did not map"
            width, height = popup.get_allocated_width(), popup.get_allocated_height()
            assert width > 150 and height > 80, f"XP {name} tray popup collapsed"
            # Mapping and GTK allocation are not enough: a DOCK-child popup
            # can be clipped to the 40px taskbar and look invisible.
            root_x, root_y = popup.get_window().get_root_origin()
            rect = self._desktop_rect()
            assert (rect.x <= root_x and root_x + width <= rect.x + rect.width and
                    rect.y <= root_y and root_y + height <= rect.y + rect.height - panel_height), (
                        f"XP {name} popup offscreen: origin=({root_x},{root_y}) "
                        f"size=({width},{height}) monitor={rect}")
            self._capture_screen(f"ricebowl-winxp-tray-{name}-0.9.1{self._capture_variant}.png")

        def _capture_luna_audio(self):
            try:
                self._capture_luna_tray("audio")
                self.luna_tray.toggle("network")
                GLib.timeout_add(520, self._capture_luna_network)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_luna_network(self):
            try:
                self._capture_luna_tray("network")
                self.luna_tray.toggle("battery")
                GLib.timeout_add(480, self._capture_luna_battery)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_luna_battery(self):
            try:
                self._capture_luna_tray("battery")
                self.luna_tray.toggle("bluetooth")
                GLib.timeout_add(460, self._capture_luna_bluetooth)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_luna_bluetooth(self):
            try:
                self._capture_luna_tray("bluetooth")
                self.luna_tray.toggle("clock")
                GLib.timeout_add(460, self._capture_luna_clock)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_luna_clock(self):
            try:
                self._capture_luna_tray("clock")
                self.luna_tray.toggle("clock")
                self.luna_open_taskbar_properties()
                GLib.timeout_add(420, self._capture_luna_properties)
                return False
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_luna_properties(self):
            try:
                dialog = self._luna_taskbar_dialog
                assert dialog is not None and dialog.get_mapped()
                rect = self._desktop_rect()
                x, y = dialog.get_window().get_root_origin()
                width, height = dialog.get_size()
                assert (rect.x <= x and rect.y <= y and
                        x + width <= rect.x + rect.width and
                        y + height <= rect.y + rect.height - panel_height), (
                    f"XP properties outside usable monitor: {x},{y} {width}x{height}")
                self._capture_screen(
                    f"ricebowl-winxp-properties-0.9.1{self._capture_variant}-extra.png")
                dialog.response(Gtk.ResponseType.CANCEL)
                if self._tray is not None:
                    GLib.timeout_add(440, self._capture_luna_tray_preferences)
                    self._tray._open_preferences()
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
                return False
            GLib.timeout_add(280, self._capture_luna_run_start)
            return False

        def _capture_luna_run_start(self):
            try:
                GLib.timeout_add(400, self._capture_luna_run_snapshot)
                self._luna_open_run()
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_luna_run_snapshot(self):
            try:
                dialog = self._luna_run_dialog
                assert dialog is not None and dialog.get_mapped()
                assert dialog.get_style_context().has_class("luna-run-dialog")
                rect = self._desktop_rect()
                x, y = dialog.get_window().get_root_origin()
                width, height = dialog.get_size()
                assert (rect.x <= x and rect.y <= y and
                        x + width <= rect.x + rect.width and
                        y + height <= rect.y + rect.height - panel_height), (
                    f"XP Run dialog offscreen: {x},{y} {width}x{height}")
                self._capture_screen(f"ricebowl-winxp-run-0.9.1{self._capture_variant}-extra.png")
                dialog.response(Gtk.ResponseType.CANCEL)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                if getattr(self, "_luna_run_dialog", None) is not None:
                    self._luna_run_dialog.response(Gtk.ResponseType.CANCEL)
            return False

        def _capture_luna_tray_preferences(self):
            try:
                dialog = self._tray._preferences_dialog
                assert dialog is not None and dialog.get_mapped()
                rect = self._desktop_rect()
                x, y = dialog.get_window().get_root_origin()
                width, height = dialog.get_size()
                assert (rect.x <= x and rect.y <= y and
                        x + width <= rect.x + rect.width and
                        y + height <= rect.y + rect.height - panel_height), (
                    f"XP notification preferences offscreen: {x},{y} {width}x{height}")
                self._capture_screen(
                    f"ricebowl-winxp-notification-icons-0.9.1{self._capture_variant}-extra.png")
                dialog.response(Gtk.ResponseType.CANCEL)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                if self._tray is not None and self._tray._preferences_dialog is not None:
                    self._tray._preferences_dialog.response(Gtk.ResponseType.CANCEL)
            return False

        def _capture_workspace_start(self):
            """Open an actual file-manager window under the active XFWM theme."""
            try:
                import subprocess

                fixture = os.environ.get("RICEBOWL_CAPTURE_FIXTURE_DIR", "")
                if not fixture or not Path(fixture).is_dir():
                    raise RuntimeError("Missing isolated screenshot fixture directory")
                self._capture_file_manager = subprocess.Popen(
                    ["thunar", fixture], stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE, text=True)
                self._capture_window_attempts = 0
                GLib.timeout_add(550, self._capture_workspace_position)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_workspace_position(self):
            try:
                import subprocess

                self._capture_window_attempts += 1
                result = subprocess.run(
                    ["xdotool", "search", "--onlyvisible", "--name", "RiceBowl-Preview"],
                    capture_output=True, text=True, timeout=3)
                if not result.stdout.strip():
                    # Gtk/Thunar first starts Xfconf and GApplication via D-Bus;
                    # a fixed 1.5s sleep was not reliable on GitHub runners.
                    if self._capture_window_attempts < 12:
                        GLib.timeout_add(500, self._capture_workspace_position)
                        return False
                    process = self._capture_file_manager
                    detail = ""
                    if process.poll() is not None:
                        detail = process.communicate(timeout=1)[1][-900:]
                    raise AssertionError(
                        "Thunar did not map a RiceBowl-Preview window within 6s; "
                        f"exit={process.poll()}, stderr={detail!r}")
                window_id = result.stdout.splitlines()[-1].strip()
                if not window_id.isdecimal():
                    raise AssertionError("Thunar has no mapped X11 window")
                # Center the genuine Thunar window on either the 1600x900
                # gallery canvas or a compact 1024x768 acceptance desktop.
                monitor = self._desktop_rect()
                width = min(1020, max(1, monitor.width - 32))
                height = min(640, max(1, monitor.height - 48 - 40))
                x = monitor.x + (monitor.width - width) // 2
                y = monitor.y + max(20, (monitor.height - 48 - height) // 2)
                for args in (("windowsize", window_id, str(width), str(height)),
                             ("windowmove", window_id, str(x), str(y)),
                             ("windowactivate", "--sync", window_id)):
                    subprocess.run(["xdotool", *args], check=True, timeout=4,
                                   capture_output=True)
                # Give Thunar time to finish its first folder scan; a captured
                # loading throbber is not representative of the settled UI.
                GLib.timeout_add(1100, self._capture_workspace_finish)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_workspace_finish(self):
            try:
                # Exercise actual Wnck-based window integration, not a fake
                # screenshot composed from image assets or shell widgets.
                if self._window_tracker is None:
                    raise AssertionError("Native Wnck window tracking is unavailable")
                screen = self._window_tracker.screen
                screen.force_update()
                if not any(
                        "thunar" in (window.get_name() or "").casefold()
                        or (window.get_class_group() is not None and
                            "thunar" in (window.get_class_group().get_id() or "").casefold())
                        for window in screen.get_windows()):
                    raise AssertionError("Real Thunar window missing from XFWM4 workspace")
                compact = "-1024" if os.environ.get("RICEBOWL_CAPTURE_SIZE") == "1024" else ""
                self._capture_screen(f"ricebowl-{profile}-workspace-0.9.1{compact}.png")
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _assert_popup_on_monitor(self, popup):
            """An on-screen image is insufficient if its controls overlap the bar."""
            rect = self._desktop_rect()
            actual_w, actual_h = popup.get_size()
            actual_x, actual_y = popup.get_window().get_root_origin()
            if not (rect.x <= actual_x and rect.y <= actual_y and
                    actual_x + actual_w <= rect.x + rect.width and
                    actual_y + actual_h <= rect.y + rect.height - panel_height):
                raise AssertionError(
                    f"{profile} popup outside usable monitor: "
                    f"{actual_x},{actual_y} {actual_w}x{actual_h}, "
                    f"monitor={rect.x},{rect.y} {rect.width}x{rect.height}")

        def _assert_luna_popup_above_taskbar(self, popup):
            rect = self._desktop_rect()
            x, y = popup.get_window().get_root_origin()
            width, height = popup.get_allocated_width(), popup.get_allocated_height()
            if (x < rect.x or y < rect.y or x + width > rect.x + rect.width or
                    y + height > rect.y + rect.height - panel_height):
                raise AssertionError(f"XP submenu overlaps workarea: {x},{y} {width}x{height}")

        def _assert_luna_run_link_visible(self):
            """The final XP system action must not disappear beneath the footer."""
            link = self.luna_run_link.translate_coordinates(self.menu, 0, 0)
            footer = self.luna_footer.translate_coordinates(self.menu, 0, 0)
            if link is None or footer is None or link[1] < 0 or (
                    link[1] + self.luna_run_link.get_allocated_height() > footer[1]):
                raise AssertionError("XP Luna Run action is clipped by its footer")

        def _assert_control_footer_visible(self):
            """Keep the mute/status controls visible without an initial scroll."""
            location = self.mute_button.translate_coordinates(self.actions, 0, 0)
            bottom = (location[1] + self.mute_button.get_allocated_height()
                      if location is not None else None)
            window_height = self.actions.get_allocated_height()
            viewport = self.actions.get_child()
            adjustment = viewport.get_vadjustment()
            if bottom is None or location[1] < 0:
                raise AssertionError(f"{profile} device controls have invalid position")
            if bottom > window_height - 8:
                # At a short monitor height, clipping is unavoidable; verify
                # the GTK scroller really exposes the rest of the controls.
                can_scroll = adjustment.get_upper() > adjustment.get_page_size() + 4
                full_height = self._control_natural_height()
                available = self._desktop_rect().height - panel_height - 16
                if full_height <= available or not can_scroll:
                    raise AssertionError(
                        f"{profile} device controls are clipped on open: "
                        f"mute bottom={bottom}, window={window_height}, "
                        f"natural={full_height}, usable={available}, scroll={can_scroll}")

        def _control_natural_height(self):
            content = self.actions.get_child().get_child()
            if isinstance(content, Gtk.Viewport):
                content = content.get_child()
            return content.get_preferred_height()[1] + 20

        def _shutdown(self, *_args):
            if profile == "aero":
                self._win7_stop_preview()
                self._win7_end_peek()
            for name in self._popup_hide_sources:
                self._cancel_popup_hide(name)
            if self._tray is not None:
                self._tray.close()
                self._tray = None
            if self.luna_balloon is not None:
                self.luna_balloon.close()
            if profile in ("winxp", "aero") and self.luna_tray is not None:
                self.luna_tray.close()
            if profile == "windows10" and hasattr(self, "ten_controller"):
                self.ten_controller.close()
            if profile == "chromeos" and hasattr(self, "chrome_controller"):
                self.chrome_controller.close()
                if hasattr(self, "chrome_notifications"):
                    self.chrome_notifications.close()
                if self._chrome_settings is not None:
                    self._chrome_settings.close()
            if profile == "frutiger" and hasattr(self, "frutiger_controller"):
                if hasattr(self, "aqua_control_suspend"):
                    self.aqua_control_suspend()
                if hasattr(self, "_aqua_flyouts"):
                    self._aqua_flyouts.close()
                if hasattr(self, "_aqua_drives"):
                    self._aqua_drives.close()
                if hasattr(self, "_aqua_notifications"):
                    self._aqua_notifications.close()
                self.frutiger_controller.close()
            if profile == "winclassic" and hasattr(self, "classic98_controller"):
                self.classic98_controller.close()
            for component in ("ten_network", "ten_settings", "ten_task_view"):
                instance = getattr(self, component, None)
                if instance is not None:
                    instance.close()
            if self._volume_write_source:
                GLib.source_remove(self._volume_write_source)
                self._volume_write_source = 0
            if self._luna_volume_monitor is not None:
                for handler in self._luna_volume_signals:
                    self._luna_volume_monitor.disconnect(handler)
                self._luna_volume_signals = ()
                self._luna_volume_monitor = None
            if profile == "winclassic" and hasattr(self, "classic98_tray_close"):
                self.classic98_tray_close()
            if profile == "winclassic" and hasattr(self, "classic98_desktop"):
                self.classic98_desktop.close()
            if hasattr(self, "actions"):
                self.actions.destroy()

        def _screen_changed(self, *_args):
            if profile == "aero":
                self._win7_stop_preview()
                self._win7_end_peek()
            rect = self._desktop_rect()
            self.bar.resize(rect.width, panel_height)
            self.bar.move(rect.x, rect.y + rect.height - panel_height)
            if self.bar.get_realized():
                self._reserve_workarea(self.bar)
            self._task_capacity = task_capacity(rect.width, self._effective_task_pin_count(),
                                                340 if tiles else 345 if profile == "aero" else
                                                230 if profile == "winxp" else 185,
                                                compact=profile == "aero")
            if getattr(self, "_window_tracker", None) is not None:
                self._window_tracker.refresh()
            if self.menu.get_visible():
                self._hide_menu()
            if self.actions.get_visible():
                self._hide_actions()
            if profile == "windows10":
                self.ten_network.hide()
                if hasattr(self, "ten_task_view"):
                    self.ten_task_view.hide()
            if profile == "winclassic" and hasattr(self, "classic98_tray_hide"):
                self.classic98_tray_hide()

        def _render_pins(self):
            for child in self.pinned_box.get_children():
                self.pinned_box.remove(child)
            by_id = {app.get_id(): app for app in self.apps if app.get_id()}
            for identifier in self._pinned_ids:
                app = by_id.get(identifier)
                if app is None:
                    continue
                btn = self._class(Gtk.Button(), "aero-pin")
                if profile == "aero":
                    btn.get_style_context().add_class("win7-pin")
                icon = app.get_icon()
                image = (Gtk.Image.new_from_gicon(icon, Gtk.IconSize.LARGE_TOOLBAR) if icon else
                         self._icon("application-x-executable"))
                if profile == "aero":
                    image.set_pixel_size(29)
                if profile == "chromeos":
                    image.set_pixel_size(32)
                if profile == "winclassic":
                    image.set_pixel_size(16)
                btn.set_image(image)
                name = app.get_display_name() or app.get_name() or identifier
                btn.set_tooltip_text(name)
                btn.get_accessible().set_name("Launch " + name)
                btn.connect("clicked", lambda _btn, selected=app: self._launch(selected))
                btn.connect("button-press-event", lambda widget, event, selected=app:
                            self._pin_context(widget, selected, event))
                if profile == "aero":
                    target = Gtk.TargetEntry.new("application/x-ricebowl-win7-pin",
                                                 Gtk.TargetFlags.SAME_APP, 0)
                    btn.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                                        [target], Gdk.DragAction.MOVE)
                    btn.drag_dest_set(Gtk.DestDefaults.ALL, [target], Gdk.DragAction.MOVE)
                    btn.connect("drag-data-get", lambda _button, _context, selection, _info, _time,
                                source=identifier: selection.set(
                                    selection.get_target(), 8, source.encode("utf-8")))
                    btn.connect("drag-data-received", lambda button, context, x, _y, selection,
                                _info, time, target_id=identifier:
                                self._win7_pin_dropped(button, context, x, selection, time, target_id))
                self.pinned_box.pack_start(btn, False, False, 0)
            self.pinned_box.show_all()

        def _win7_pin_dropped(self, button, context, x, selection, time, target):
            """Accept only local validated desktop IDs; persist before redraw."""
            data = selection.get_data()
            try:
                source = data.decode("utf-8").rstrip("\x00") if data is not None else ""
            except UnicodeDecodeError:
                source = ""
            success = self._win7_reorder_pin(source, target,
                                             after=x >= button.get_allocated_width() / 2)
            Gtk.drag_finish(context, success, False, time)

        def _win7_reorder_pin(self, source, target, *, after=False):
            if profile != "aero":
                return False
            from .aero_pins import reorder_pins

            if source not in self._pinned_ids or target not in self._pinned_ids:
                return False
            candidate = reorder_pins(self._pinned_ids, source, target, after=after)
            if candidate == self._pinned_ids:
                return True
            try:
                save_pins(self._pin_config_path, candidate)
            except (PinConfigError, OSError) as exc:
                self._error("Unable to save taskbar pin order: " + str(exc))
                return False
            self._pinned_ids = candidate
            self._render_pins()
            return True

        def _pin_context(self, widget, app, event=None):
            if event is not None and event.button != 3:
                return False
            identifier = app.get_id()
            if not identifier:
                return False
            menu = Gtk.Menu()
            if profile == "winxp":
                self._track_start_popup(menu)
            pinned = identifier in self._pinned_ids
            if profile == "aero" and widget.get_parent() is self.pinned_box:
                menu.get_style_context().add_class("win7-jumplist")
                launch = Gtk.MenuItem(label="Open " + (app.get_display_name() or app.get_name()))
                launch.connect("activate", lambda _item: self._launch(app))
                menu.append(launch)
                recent = self._win7_app_recent_files(app)
                if recent:
                    menu.append(Gtk.SeparatorMenuItem())
                    heading = Gtk.MenuItem(label="Recent")
                    heading.set_sensitive(False)
                    menu.append(heading)
                    for name, uri in recent:
                        item = Gtk.MenuItem(label=name)
                        item.connect("activate", lambda _item, address=uri, selected=app:
                                     self._win7_launch_recent(selected, address))
                        menu.append(item)
                menu.append(Gtk.SeparatorMenuItem())
                if pinned and len(self._pinned_ids) > 1:
                    index = self._pinned_ids.index(identifier)
                    for title, delta in (("Move pin left", -1), ("Move pin right", 1)):
                        item = Gtk.MenuItem(label=title)
                        destination = index + delta
                        item.set_sensitive(0 <= destination < len(self._pinned_ids))
                        if 0 <= destination < len(self._pinned_ids):
                            adjacent = self._pinned_ids[destination]
                            item.connect("activate", lambda _item, target=adjacent, kind=delta:
                                         self._win7_reorder_pin(identifier, target, after=kind > 0))
                        menu.append(item)
                    menu.append(Gtk.SeparatorMenuItem())
            elif profile == "winxp":
                launch = self._luna_menu_item("Open " + (app.get_display_name() or app.get_name()),
                                              app.get_icon() or "application-x-executable")
                launch.connect("activate", lambda _item: self._launch(app))
                menu.append(launch)
                menu.append(Gtk.SeparatorMenuItem())
                favorites = self._luna_favorites()
                favorite = identifier in favorites
                start_item = self._luna_menu_item(
                    "Unpin from Start menu" if favorite else "Pin to Start menu",
                    "ricehub-luna-cp-programs")
                start_item.set_sensitive(favorite or len(favorites) < 4)
                start_item.connect("activate", lambda _item: self._change_luna_favorite(
                    identifier, "unpin" if favorite else "pin"))
                menu.append(start_item)
                if favorite and len(favorites) > 1:
                    for title, action in (("Move favorite up", "up"),
                                          ("Move favorite down", "down")):
                        item = self._luna_menu_item(title, "ricehub-luna-cp-programs")
                        index = favorites.index(identifier)
                        item.set_sensitive(index > 0 if action == "up" else
                                           index < len(favorites) - 1)
                        item.connect("activate", lambda _item, kind=action:
                                     self._change_luna_favorite(identifier, kind))
                        menu.append(item)
                menu.append(Gtk.SeparatorMenuItem())
            label = "Unpin from taskbar" if pinned else "Pin to taskbar"
            item = (self._luna_menu_item(label, "list-remove" if pinned else "list-add")
                    if profile == "winxp" else Gtk.MenuItem(label=label))
            item.set_sensitive(pinned or len(self._pinned_ids) < PIN_LIMIT)
            item.connect("activate", lambda _item: self._change_pin(identifier, not pinned))
            menu.append(item)
            menu.show_all()
            if event is not None:
                menu.popup_at_pointer(event)
            else:
                menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)
            return True

        def _win7_app_recent_files(self, app):
            """Only real local recent files supported by this installed app."""
            get_types = getattr(app, "get_supported_types", None)
            supported = set(get_types() or ()) if callable(get_types) else set()
            if not supported:
                return ()
            try:
                entries = Gtk.RecentManager.get_default().get_items()[:60]
                recent = []
                for entry in entries:
                    uri = entry.get_uri()
                    if (uri.startswith("file:") and entry.get_mime_type() in supported
                            and entry.exists() and (uri not in (url for _, url in recent))):
                        recent.append((entry.get_display_name(), uri))
                        if len(recent) == 5:
                            break
                return tuple(recent)
            except (GLib.Error, OSError, RuntimeError) as exc:
                logging.getLogger(__name__).debug("Recent files unavailable for Jump List: %s", exc)
                return ()

        def _win7_launch_recent(self, app, uri):
            try:
                app.launch_uris([uri], None)
                self._hide_menu()
            except (GLib.Error, OSError) as exc:
                self._error("Cannot open recent file: " + str(exc))

        def _luna_favorites(self):
            if self._luna_start_state.favorites is not None:
                return self._luna_start_state.favorites
            featured, _recent = luna_programs(self.apps, self._pinned_ids, "")
            return tuple(app.get_id() for app in featured if app.get_id())

        def _change_luna_favorite(self, identifier, action):
            from .luna_start_state import change_favorite, save_start_state

            previous = self._luna_start_state.favorites
            if not change_favorite(self._luna_start_state, identifier, action,
                                   defaults=self._luna_favorites()):
                return
            try:
                save_start_state(self._luna_start_state)
            except (OSError, ValueError) as exc:
                self._luna_start_state.favorites = previous
                self._error("Unable to save Start favorites: " + str(exc),
                            title="Could not update Start menu")
                return
            if self.menu and self.menu.get_visible():
                self._populate(self.search.get_text())

        def _change_pin(self, identifier, add):
            candidate = list(self._pinned_ids)
            if add and identifier not in candidate:
                candidate.append(identifier)
            elif not add and identifier in candidate:
                candidate.remove(identifier)
            else:
                return
            try:
                save_pins(self._pin_config_path, candidate)
            except (PinConfigError, OSError) as exc:
                self._error("Unable to save taskbar pins: " + str(exc))
                return
            self._pinned_ids = tuple(candidate)
            self._render_pins()
            if tiles:
                self._render_ten_tiles()
            self._pin_count = len(candidate)
            self._task_capacity = task_capacity(self._desktop_rect().width, self._effective_task_pin_count(),
                                                340 if tiles else 345 if profile == "aero" else
                                                230 if profile == "winxp" else 185,
                                                compact=profile == "aero")
            if self._window_tracker is not None:
                self._window_tracker.refresh()

        def _reserve_workarea(self, widget, *_args):
            """Reserve the bottom strip on X11, but never change XFCE panel settings."""
            option = "RICEHUB_TEN_RESERVE" if ten else f"RICEHUB_{profile.upper()}_RESERVE"
            if os.environ.get(option, "1") == "0":
                return
            try:
                gi.require_version("GdkX11", "3.0")
                from gi.repository import GdkX11
                rect = self._desktop_rect()
                props = bottom_strut(rect.x, rect.y, rect.width, rect.height,
                                     Gdk.Screen.get_default().get_height(), panel_height)
                library = ctypes.util.find_library("X11")
                if not library:
                    return
                lib = ctypes.CDLL(library)
                lib.XOpenDisplay.restype = ctypes.c_void_p
                lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
                lib.XInternAtom.restype = ctypes.c_ulong
                lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
                lib.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                                ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                                ctypes.c_void_p, ctypes.c_int]
                lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
                lib.XFlush.argtypes = [ctypes.c_void_p]
                display = lib.XOpenDisplay(None)
                if not display:
                    return
                try:
                    xid = GdkX11.X11Window.get_xid(widget.get_window())
                    cardinal = lib.XInternAtom(display, b"CARDINAL", 0)
                    for name, values in zip(("_NET_WM_STRUT", "_NET_WM_STRUT_PARTIAL"), props):
                        atom = lib.XInternAtom(display, name.encode("ascii"), 0)
                        data = (ctypes.c_ulong * len(values))(*values)
                        lib.XChangeProperty(display, xid, atom, cardinal, 32, 0, data, len(values))
                    lib.XFlush(display)
                finally:
                    lib.XCloseDisplay(display)
            except (OSError, AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logging.getLogger(__name__).warning("RiceBowl workarea reservation unavailable: %s", exc)

        def _open_tool(self, command):
            """Open a known XFCE utility without a shell or implicit system changes."""
            if command not in LAUNCHABLE_TOOLS:
                logging.getLogger(__name__).warning("Rejected unknown desktop utility: %r", command)
                return
            executable = shutil.which(command)
            if not executable:
                self._error(command + " is not installed.")
                return
            try:
                subprocess.Popen([executable], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
                self._hide_menu()
                if ten or profile == "chromeos":
                    self._hide_actions()
            except OSError as exc:
                self._error(str(exc))

        def _show_desktop(self, *_args):
            if self._window_tracker is not None:
                if profile == "aero":
                    # A click during temporary Peek commits Show Desktop.
                    if self._win7_peek_timer:
                        GLib.source_remove(self._win7_peek_timer)
                        self._win7_peek_timer = 0
                    if self._win7_peek_active:
                        self._win7_peek_active = False
                        self._hide_menu()
                        return
                screen = self._window_tracker.screen
                screen.toggle_showing_desktop(not screen.get_showing_desktop())
                self._hide_menu()

        def _win7_begin_peek(self, *_args):
            if self._window_tracker is None or self._win7_peek_active:
                return False
            if self._win7_peek_timer:
                GLib.source_remove(self._win7_peek_timer)
            self._win7_peek_timer = GLib.timeout_add(450, self._win7_preview_desktop)
            return False

        def _win7_preview_desktop(self):
            self._win7_peek_timer = 0
            if (self._window_tracker is not None and
                    not self._window_tracker.screen.get_showing_desktop()):
                self._window_tracker.screen.toggle_showing_desktop(True)
                self._win7_peek_active = True
            return False

        def _win7_end_peek(self):
            if self._win7_peek_timer:
                GLib.source_remove(self._win7_peek_timer)
                self._win7_peek_timer = 0
            if self._win7_peek_active and self._window_tracker is not None:
                self._window_tracker.screen.toggle_showing_desktop(False)
            self._win7_peek_active = False

        def _win7_leave_peek(self, *_args):
            self._win7_end_peek()
            return False

        def _catalog_changed(self, *_args):
            self.apps = app_catalog(Gio)
            self._render_pins()
            self._populate(self.search.get_text())
            if tiles:
                self._render_ten_tiles()

        def _class(self, widget, name):
            widget.get_style_context().add_class(name)
            return widget

        def _desktop_rect(self):
            screen = Gdk.Screen.get_default()
            monitor = screen.get_primary_monitor()
            return screen.get_monitor_geometry(monitor if monitor >= 0 else 0)

        def _icon(self, name, size=Gtk.IconSize.LARGE_TOOLBAR):
            if profile in ("aero", "winclassic", "winxp"):
                theme_dir = {"aero": "RiceHub-Aero", "winclassic": "RiceHub-Classic-Icons",
                             "winxp": "RiceHub-Luna-Icons"}[profile]
                for category in ("places", "apps", "devices"):
                    candidate = (project_root() / ("assets/icons/" + theme_dir + "/scalable") /
                                 category / (name + ".svg"))
                    if candidate.is_file():
                        pixels = 16 if size == Gtk.IconSize.MENU else 48 if size == Gtk.IconSize.DIALOG else 24
                        try:
                            return Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                str(candidate), pixels, pixels, True))
                        except (GLib.Error, OSError):
                            pass
                if profile == "winxp" and name != "applications-other":
                    theme = Gtk.IconTheme.get_default()
                    if theme is not None and not theme.has_icon(name):
                        return self._icon("applications-other", size)
            return Gtk.Image.new_from_icon_name(name, size)

        def _set_status_icon(self, image, kind):
            """Use Rice-specific vector artwork, with a GTK icon fallback."""
            path = project_root() / "assets/status" / profile / (kind + ".svg")
            fallback = ("audio-volume-muted" if kind == "muted" else
                        "audio-volume-high" if kind == "sound" else
                        "network-wireless" if kind == "wifi" else
                        "network-wired" if kind == "ethernet" else
                        "network-offline" if kind == "offline" else
                        "battery-good-symbolic")
            try:
                image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), 20, 20, True))
            except (GLib.Error, OSError):
                image.set_from_icon_name(fallback, Gtk.IconSize.MENU)

        def _status_action(self, name):
            """Open usable controls for audio/power; network settings for Wi-Fi."""
            if profile == "winclassic":
                self.classic98_tray_show(name)
                return
            if profile == "frutiger":
                if not hasattr(self, "_aqua_flyouts"):
                    from .frutiger_flyouts import AquaFlyouts

                    self._aqua_flyouts = AquaFlyouts(self, Gtk)
                self._aqua_flyouts.show(name)
                return
            if profile == "chromeos" and name == "network":
                self._toggle_chrome_quick_page("Network")
                return
            if name in ("audio", "battery"):
                self._toggle_actions()
                return
            options = {
                "network": ("nm-connection-editor", "xfce4-settings-manager"),
                "audio": ("pavucontrol", "xfce4-settings-manager"),
                "battery": ("xfce4-power-manager-settings", "xfce4-settings-manager"),
            }[name]
            for candidate in options:
                if shutil.which(candidate):
                    self._open_tool(candidate)
                    return
            self._error("No suitable " + name + " settings application was found.")

        def _install_status_widgets(self, row):
            if profile == "winxp":
                from .luna_tray import LunaTray
                from .luna_notifications import LunaBalloon

                self.luna_tray = LunaTray(self, Gtk, GLib)
                self.luna_balloon = LunaBalloon(self, Gtk, Gdk, GLib)
            elif profile == "aero":
                from .win7_tray import Win7Tray
                from .win7_notifications import Win7Balloon

                self.luna_tray = Win7Tray(self, Gtk, GLib)
                self.luna_balloon = Win7Balloon(self, Gtk, Gdk, GLib)
            elif profile == "windows10":
                from .ten_riceware import TenController

                self.ten_controller = TenController(self, Gtk, GLib)
            elif profile == "winclassic":
                from .classic98_riceware import Classic98Controller

                self.classic98_controller = Classic98Controller(GLib)
            elif profile == "chromeos":
                from .chrome_riceware import ChromeController

                self.chrome_controller = ChromeController(GLib)
            elif profile == "frutiger":
                from .frutiger_riceware import FrutigerController

                self.frutiger_controller = FrutigerController(GLib)
            for name in ("battery", "network", "audio"):
                button = self._class(Gtk.Button(), "rice-status")
                button.get_style_context().add_class("rice-status-" + name)
                contents = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
                image = Gtk.Image()
                contents.pack_start(image, False, False, 0)
                label = Gtk.Label()
                contents.pack_start(label, False, False, 0)
                button.add(contents)
                button.get_accessible().set_name(name.capitalize() + " status")
                if profile == "windows10" and name == "network":
                    button.connect("clicked", lambda _button: self._toggle_ten_network())
                elif self.luna_tray is None:
                    button.connect("clicked", lambda _button, selected=name:
                                   self._status_action(selected))
                row.pack_end(button, False, False, 0)
                self._status_widgets[name] = (button, image, label)
                if self.luna_tray is not None:
                    self.luna_tray.install(name, button)
            if self.luna_tray is not None:
                bluetooth = self._class(Gtk.Button(), "rice-status")
                bluetooth.add(self._icon("bluetooth-active" if profile == "aero" else
                                         "ricehub-luna-task-bluetooth", Gtk.IconSize.MENU))
                bluetooth.set_tooltip_text("Bluetooth devices and adapter")
                bluetooth.get_accessible().set_name("Bluetooth device controls")
                row.pack_end(bluetooth, False, False, 0)
                self.luna_tray.install("bluetooth", bluetooth)
                self.luna_tray.install("clock", self._luna_clock_button)
                if profile == "aero":
                    alert = self._class(Gtk.Button(label="⚑"), "win7-alert-button")
                    alert.get_accessible().set_name("Windows 7 Action Center notifications")
                    row.pack_end(alert, False, False, 0)
                    self.luna_tray.install("alerts", alert)
            elif profile == "frutiger":
                bluetooth = self._class(Gtk.Button(), "rice-status")
                bluetooth.add(self._icon("bluetooth-active", Gtk.IconSize.MENU))
                bluetooth.get_accessible().set_name("Open Aqua Bluetooth devices")
                bluetooth.set_tooltip_text("Bluetooth devices · Aqua World")
                bluetooth.connect("clicked", lambda _button: self._status_action("bluetooth"))
                row.pack_end(bluetooth, False, False, 0)
                self.aqua_bluetooth_button = bluetooth
                drives = self._class(Gtk.Button(), "rice-status")
                drives.add(self._icon("drive-removable-media", Gtk.IconSize.MENU))
                drives.get_accessible().set_name("Open Aqua connected locations")
                drives.set_tooltip_text("Mounted USB and network locations · Aqua World")

                def show_drives(_button):
                    if not hasattr(self, "_aqua_drives"):
                        from .frutiger_drives import AquaDrives
                        self._aqua_drives = AquaDrives(self, Gtk, Gio)
                    self._aqua_drives.show()

                drives.connect("clicked", show_drives)
                row.pack_end(drives, False, False, 0)
                self.aqua_drives_button = drives
                notifications = self._class(Gtk.Button(), "rice-status")
                notifications.add(self._icon("preferences-desktop-notification", Gtk.IconSize.MENU))
                notifications.get_accessible().set_name("Open Aqua notifications")
                notifications.set_tooltip_text("Native XFCE notifications · Aqua World")
                notifications.connect("clicked", lambda _button: self._show_aqua_notifications())
                row.pack_end(notifications, False, False, 0)
                self.aqua_notifications_button = notifications
            elif profile == "winclassic":
                bluetooth = self._class(Gtk.Button(), "rice-status")
                bluetooth.add(self._icon("bluetooth-active", Gtk.IconSize.MENU))
                bluetooth.set_tooltip_text("Bluetooth devices and adapter")
                bluetooth.get_accessible().set_name("Bluetooth controls")
                bluetooth.connect("clicked", lambda _button: self.classic98_tray_show("bluetooth"))
                row.pack_end(bluetooth, False, False, 0)
                self.classic98_bluetooth_button = bluetooth
            self._refresh_status_async()
            GLib.timeout_add_seconds(20, self._refresh_status_async)

        def _refresh_status_async(self):
            if self._status_pending:
                return True
            self._status_pending = True
            if profile in ("winxp", "aero") and self.luna_tray is not None:
                self.luna_tray.refresh_status(self._apply_status)
                return True
            if profile == "windows10":
                self.ten_controller.refresh_status(self._apply_status)
                if self.ten_controller.opened:
                    self.ten_controller.refresh_switches()
                return True
            if profile == "winclassic":
                self.classic98_controller.refresh_status(self._apply_status)
                return True
            if profile == "chromeos":
                self.chrome_controller.refresh_status(self._apply_status)
                return True
            if profile == "frutiger":
                self.frutiger_controller.refresh_status(self._apply_status)
                return True
            def worker():
                try:
                    from .hardware_status import read_status
                    status = read_status()
                except Exception as exc:
                    logging.getLogger(__name__).warning("Hardware status probe failed: %s", exc)
                    status = None
                GLib.idle_add(self._apply_status, status)
            threading.Thread(target=worker, name="ricebowl-status", daemon=True).start()
            return True

        def _apply_status(self, status):
            self._status_pending = False
            if status is None:
                if profile == "chromeos":
                    for action, label in getattr(self, "chrome_quick_status_labels", ()):
                        label.set_text("Status temporarily unavailable")
                if self.luna_tray is not None:
                    self.luna_tray.on_status(None)
                if hasattr(self, "frutiger_status_label"):
                    self.frutiger_status_label.set_text(frutiger_status_summary(None))
                if profile in ("windows10", "winclassic", "chromeos") and hasattr(self, "volume_status_label"):
                    self.control_network_label.set_text("Network: unavailable — retrying")
                    self.control_battery_label.set_text("Battery: unavailable — retrying")
                    self.volume_status_label.set_text("Audio backend unavailable — retrying")
                    self.volume_scale.set_sensitive(False)
                    self.mute_button.set_sensitive(False)
                if profile == "frutiger" and hasattr(self, "control_network_label"):
                    self.control_network_label.set_text("Network: unavailable — retrying")
                    self.control_battery_label.set_text("Battery: unavailable — retrying")
                    self.volume_status_label.set_text("Volume: unavailable — retrying")
                    self.volume_scale.set_sensitive(False)
                    self.mute_button.set_sensitive(False)
                    detail = getattr(self, "aqua_control_detail_status", None)
                    if detail is not None:
                        detail.set_text("Device status temporarily unavailable")
                if hasattr(self, "_aqua_flyouts"):
                    self._aqua_flyouts.sync(None)
                for button, _image, _label in self._status_widgets.values():
                    # Luna's tray popovers are also the recovery path when a
                    # transient probe fails; keep them openable for details.
                    button.set_sensitive(self.luna_tray is not None or
                                         profile in ("windows10", "winclassic", "chromeos", "frutiger"))
                    button.set_tooltip_text("Hardware status temporarily unavailable")
                return False
            previous_status = self._last_status
            self._last_status = status
            if profile == "chromeos":
                from .chrome_settings import status_text
                for action, label in getattr(self, "chrome_quick_status_labels", ()):
                    label.set_text(status_text(action, status))
                if self._chrome_settings is not None:
                    self._chrome_settings.refresh()
            if self.luna_balloon is not None:
                from .luna_notifications import event_messages

                for message in event_messages(previous_status, status):
                    if profile == "aero" and self.luna_tray is not None:
                        self.luna_tray.announce(message)
                    else:
                        self.luna_balloon.show(message)
            if self.luna_tray is not None:
                self.luna_tray.on_status(status)
            if hasattr(self, "_aqua_flyouts"):
                self._aqua_flyouts.sync(status)
            if hasattr(self, "frutiger_status_label"):
                self.frutiger_status_label.set_text(frutiger_status_summary(status))
            if hasattr(self, "control_network_label"):
                self.control_network_label.set_text(
                    "Network: " + {"wifi": "Wi-Fi", "ethernet": "Ethernet",
                                   "offline": "No active route"}[status.network])
                detail = getattr(self, "aqua_control_detail_status", None)
                if detail is not None:
                    detail.set_text(
                        self.control_network_label.get_text() if
                        getattr(self, "aqua_control_detail_kind", None) == "connections" else
                        (f"Battery: {status.battery.percent}% — {status.battery.label}"
                         if status.battery else "Battery: not detected"))
                if hasattr(self, "chrome_network_detail"):
                    self.chrome_network_detail.set_text({
                        "wifi": "Wi-Fi · connected", "ethernet": "Ethernet · connected",
                        "offline": "Offline",
                    }[status.network])
                battery = status.battery
                self.control_battery_label.set_text(
                    f"Battery: {battery.percent}% — {battery.label}" if battery else
                    "Battery: not detected")
                if battery:
                    self.control_battery_level.set_value(battery.percent)
                    self.control_battery_level.show()
                else:
                    self.control_battery_level.hide()
                if status.sound.muted is not None and not self._mute_writing:
                    self.mute_button.set_sensitive(True)
                    self.mute_button.set_active(status.sound.muted)
                elif status.sound.muted is None:
                    self.mute_button.set_sensitive(False)
                if status.sound.percent is not None:
                    self.volume_scale.set_sensitive(True)
                    self.volume_status_label.set_text(
                        f"Volume: {status.sound.percent}%"
                        + (" (muted)" if status.sound.muted else ""))
                    if not self._volume_writing and self._volume_queued is None:
                        self._volume_programmatic = True
                        try:
                            self.volume_scale.set_value(
                                min(100, status.sound.percent))
                        finally:
                            self._volume_programmatic = False
                else:
                    self.volume_scale.set_sensitive(False)
                    self.volume_status_label.set_text(
                        "Volume backend unavailable")
            battery_button, battery_icon, battery_label = self._status_widgets["battery"]
            battery = status.battery
            if battery is None:
                if self.luna_tray is None and profile not in ("winclassic", "frutiger"):
                    battery_button.hide()
                else:
                    battery_button.show_all()
                    self._set_status_icon(battery_icon, "battery-0")
                    battery_label.set_text("")
                    battery_button.set_tooltip_text("Power settings · no laptop battery detected")
                    battery_button.get_accessible().set_name("Power settings, no battery")
            else:
                battery_button.show_all()
                level = min(100, (battery.percent + 12) // 25 * 25)
                self._set_status_icon(battery_icon, "battery-charging" if battery.charging
                                      else "battery-" + str(level))
                battery_label.set_text(str(battery.percent) + "%")
                battery_button.set_sensitive(True)
                battery_button.set_tooltip_text(
                    f"Battery {battery.percent}% — {battery.label}. Open power settings")
                battery_button.get_accessible().set_name(
                    f"Battery {battery.percent} percent, {battery.label}")
            network_button, network_icon, network_label = self._status_widgets["network"]
            self._set_status_icon(network_icon, status.network)
            network_label.set_text("" if profile != "chromeos" else
                                   "Wi-Fi" if status.network == "wifi" else
                                   "LAN" if status.network == "ethernet" else "Offline")
            network_button.set_tooltip_text({
                "wifi": "Wi-Fi is the default route; open network settings",
                "ethernet": "Ethernet / other default route; open network settings",
                "offline": "No IPv4 default route; open network settings",
            }[status.network])
            network_button.get_accessible().set_name("Network " + status.network)
            sound_button, sound_icon, sound_label = self._status_widgets["audio"]
            sound = status.sound
            self._set_status_icon(sound_icon, "muted" if sound.muted else "sound")
            sound_label.set_text("" if sound.percent is None or profile != "chromeos"
                                 else str(sound.percent) + "%")
            sound_button.set_tooltip_text(
                "Volume unknown; open sound settings" if sound.percent is None else
                f"Audio {sound.percent}% — {'muted' if sound.muted else 'unmuted'}; open sound settings")
            sound_button.get_accessible().set_name(
                "Audio status unknown" if sound.percent is None else
                f"Audio {sound.percent} percent" + (", muted" if sound.muted else ""))
            if hasattr(self, "status_summary"):
                self.status_summary.set_text(
                    ("Battery " + str(battery.percent) + "% · " if battery else "") +
                    status.network.upper() + " · " +
                    ("Audio unavailable" if sound.percent is None else
                     "Audio " + str(sound.percent) + "%"))
            return False

        def _queue_volume_change(self, slider):
            if self._volume_programmatic:
                return
            self._volume_queued = int(round(slider.get_value()))
            if self._volume_write_source:
                GLib.source_remove(self._volume_write_source)
            self._volume_write_source = GLib.timeout_add(
                260, self._commit_volume_change)

        def _commit_volume_change(self):
            self._volume_write_source = 0
            if self._volume_writing or self._volume_queued is None:
                return False
            value = self._volume_queued
            self._volume_queued = None
            self._volume_writing = True
            self.volume_status_label.set_text(f"Adjusting volume to {value}%…")
            if self.luna_tray is not None:
                self.luna_tray.volume_pending(value)
            if profile in ("winxp", "aero") and self.luna_tray is not None:
                self.luna_tray.change_audio("audio_volume", value, self._volume_change_complete)
            elif profile == "windows10":
                self.ten_controller.change_audio("audio_volume", value,
                                                 self._volume_change_complete)
            elif profile == "winclassic":
                self.classic98_controller.change_audio("audio_volume", value,
                                                        self._volume_change_complete)
            elif profile == "chromeos":
                self.chrome_controller.change_audio("audio_volume", value,
                                                    self._volume_change_complete)
            elif profile == "frutiger":
                self.frutiger_controller.change_audio("audio_volume", value,
                                                      self._volume_change_complete)
            else:
                def worker():
                    from .hardware_status import set_sound_volume
                    try:
                        state = set_sound_volume(value)
                        error = None
                    except (OSError, RuntimeError, ValueError) as exc:
                        state, error = None, str(exc)
                    GLib.idle_add(self._volume_change_complete, state, error)
                threading.Thread(target=worker, daemon=True,
                                 name="ricebowl-set-volume").start()
            return False

        def _volume_change_complete(self, state, error):
            self._volume_writing = False
            if self.luna_tray is not None:
                self.luna_tray.volume_done(state, error)
            if error:
                self.volume_status_label.set_text("Volume unavailable — " + error)
            elif state is not None:
                self.volume_status_label.set_text(
                    f"Volume {state.percent}%"
                    + (" (muted)" if state.muted else ""))
            if self._volume_queued is not None and not self._volume_write_source:
                self._volume_write_source = GLib.timeout_add(
                    180, self._commit_volume_change)
            else:
                self._refresh_status_async()
            return False

        def _toggle_output_mute(self, button):
            if self._mute_writing or self._last_status is None:
                return
            sound = self._last_status.sound
            if sound.muted is None:
                return
            requested = bool(button.get_active())
            # GTK ToggleButton is optimistic; display the real state until
            # the backend confirms the change.
            button.set_active(sound.muted)
            button.set_sensitive(False)
            if self.luna_tray is not None:
                self.luna_tray.audio_mute.set_sensitive(False)
            self._mute_writing = True

            if profile in ("winxp", "aero") and self.luna_tray is not None:
                self.luna_tray.change_audio("audio_mute", requested, self._mute_change_complete)
            elif profile == "windows10":
                self.ten_controller.change_audio("audio_mute", requested,
                                                 self._mute_change_complete)
            elif profile == "winclassic":
                self.classic98_controller.change_audio("audio_mute", requested,
                                                        self._mute_change_complete)
            elif profile == "chromeos":
                self.chrome_controller.change_audio("audio_mute", requested,
                                                    self._mute_change_complete)
            elif profile == "frutiger":
                self.frutiger_controller.change_audio("audio_mute", requested,
                                                      self._mute_change_complete)
            else:
                def worker():
                    from .hardware_status import set_sound_mute
                    try:
                        state = set_sound_mute(requested)
                        error = None
                    except (OSError, ValueError, RuntimeError) as exc:
                        state, error = None, str(exc)
                    GLib.idle_add(self._mute_change_complete, state, error)

                threading.Thread(target=worker, daemon=True,
                                 name="ricebowl-set-mute").start()

        def _mute_change_complete(self, state, error):
            self._mute_writing = False
            if self.luna_tray is not None:
                self.luna_tray.mute_done(state, error)
            if error:
                self.volume_status_label.set_text("Mute action failed: " + error)
            else:
                self.mute_button.set_active(bool(state.muted))
                self.volume_status_label.set_text(
                    "Audio muted" if state.muted else "Audio unmuted")
            self._refresh_status_async()
            return False

        def _create_taskbar(self):
            rect = self._desktop_rect()
            win = Gtk.ApplicationWindow(application=self)
            win.set_title("RiceBowl Windows 10 Taskbar" if ten else
                          f"RiceBowl {heritage.name} Taskbar" if heritage else "RiceBowl Aero Taskbar")
            win.set_decorated(False)
            win.set_resizable(False)
            win.set_skip_taskbar_hint(True)
            win.set_skip_pager_hint(True)
            win.set_type_hint(Gdk.WindowTypeHint.DOCK)
            win.set_keep_above(True)
            win.set_accept_focus(False)
            win.set_default_size(rect.width, panel_height)
            win.move(rect.x, rect.y + rect.height - panel_height)

            row = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                      spacing=3 if profile in ("winclassic", "windows10") else
                                      4 if profile in ("winxp", "aero") else 8), "aero-taskbar")
            if profile == "aero":
                row.get_style_context().add_class("win7-taskbar")
            elif profile == "frutiger":
                row.get_style_context().add_class("frutiger-taskbar")
            if not ten and os.environ.get("RICEHUB_AERO_GLASS") == "1":
                row.get_style_context().add_class("aero-glass")
            start = self._class(Gtk.Button(), "aero-start")
            if profile == "aero":
                start.get_style_context().add_class("win7-start")
            elif profile == "frutiger":
                start.get_style_context().add_class("frutiger-start")
            contents = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            logo = project_root() / ("assets/ten-start.svg" if ten else
                                     "assets/" + heritage.logo if heritage else "assets/aero-penguin.svg")
            try:
                img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(logo), 19 if profile == "winclassic" else 19 if ten else 26 if profile == "winxp" else 36,
                    19 if profile == "winclassic" else 19 if ten else 26 if profile == "winxp" else 36, True))
            except (GLib.Error, OSError):
                img = self._icon("start-here", Gtk.IconSize.LARGE_TOOLBAR)
            contents.pack_start(img, False, False, 0)
            if not ten and profile not in ("chromeos", "aero"):
                contents.pack_start(Gtk.Label(label=heritage.start_label if heritage else "Start"), False, False, 0)
            start.add(contents)
            start.get_accessible().set_name("Toggle " + (heritage.name if heritage else
                "Windows 10" if ten else "Aero") + " application menu")
            start.connect("clicked", lambda _button: self._toggle_menu())
            if profile == "winxp":
                start.connect("button-press-event", self._luna_start_context)
            start.set_tooltip_text("Start")
            row.pack_start(start, False, False, 0 if profile in ("winxp", "aero", "winclassic", "windows10") else 4)
            if profile == "chromeos":
                # Three independent visual zones: launcher, centered shelf,
                # and the device-status pill at the far right.
                row.pack_start(Gtk.Box(), True, True, 0)
                shelf_box = self._class(
                    Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
                    "chrome-app-shelf")
                row.pack_start(shelf_box, False, False, 0)
            else:
                shelf_box = row
            self.start_button = start
            if ten:
                # Windows 10 supports the compact taskbar search-icon mode.
                # The functional text field remains inside Start, not twice on screen.
                search_button = self._class(Gtk.Button(), "ten-search")
                search_button.add(self._icon("edit-find-symbolic", Gtk.IconSize.BUTTON))
                search_button.get_accessible().set_name("Search installed applications")
                search_button.set_tooltip_text("Search installed applications")
                search_button.connect("clicked", lambda _button: self._open_search())
                row.pack_start(search_button, False, False, 0)
                view = self._class(Gtk.Button(), "ten-search")
                view.add(self._icon("view-grid-symbolic", Gtk.IconSize.BUTTON))
                view.get_accessible().set_name("Task View: open windows and desktops")
                view.set_tooltip_text("Task View")
                view.connect("clicked", lambda _button: self._toggle_ten_task_view())
                row.pack_start(view, False, False, 0)
            self.pinned_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            if profile == "frutiger":
                self.pinned_box.get_style_context().add_class("frutiger-pins")
            if profile in ("winclassic", "winxp"):
                quick_launch = self._class(
                    Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2),
                    "classic98-quicklaunch" if profile == "winclassic" else "luna-quicklaunch")
                if profile == "winclassic":
                    self.classic98_quick_launch = quick_launch
                elif profile == "winxp":
                    self._luna_quick_launch = quick_launch
                quick_launch.pack_start(self.pinned_box, False, False, 0)
                desktop_quick = self._class(Gtk.Button(),
                                            "classic98-desktop-quick" if profile == "winclassic"
                                            else "luna-desktop-quick")
                desktop_quick.set_image(self._icon("user-desktop", Gtk.IconSize.MENU))
                desktop_quick.set_tooltip_text("Show Desktop")
                desktop_quick.get_accessible().set_name("Show Desktop")
                desktop_quick.connect("clicked", self._show_desktop)
                quick_launch.pack_start(desktop_quick, False, False, 0)
                shelf_box.pack_start(quick_launch, False, False, 2)
                separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                if profile == "winxp":
                    self._luna_quick_separator = separator
                shelf_box.pack_start(separator, False, False, 2)
            else:
                shelf_box.pack_start(self.pinned_box, False, False, 0)
            self._render_pins()
            self._pin_count = len(self._pinned_ids)
            self.tasks = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            self._task_capacity = task_capacity(rect.width, self._effective_task_pin_count(),
                                                340 if tiles else 345 if profile == "aero" else
                                                230 if profile == "winxp" else 185,
                                                compact=profile == "aero")
            self.overflow_button = self._class(Gtk.Button(), "aero-task-overflow")
            self.overflow_button.get_accessible().set_name("Show other running windows")
            self.overflow_button.connect("clicked", self._show_overflow)
            shelf_box.pack_start(self.tasks, False, False, 4)
            if profile in ("winclassic", "winxp", "aero", "windows10"):
                # Only blank taskbar space owns this menu; right-clicks on
                # tray controls and task buttons retain their own semantics.
                taskbar_spacer = Gtk.EventBox()
                taskbar_spacer.set_visible_window(False)
                taskbar_spacer.connect("button-press-event",
                                        self._classic98_taskbar_context if profile == "winclassic"
                                        else self._luna_taskbar_context if profile == "winxp"
                                        else self._ten_taskbar_context if profile == "windows10"
                                        else self._win7_taskbar_context)
            else:
                taskbar_spacer = Gtk.Box()
            row.pack_start(taskbar_spacer, True, True, 0)
            right_area = row
            if profile in ("chromeos", "winxp", "frutiger"):
                right_area = self._class(
                    Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
                    "chrome-status-pill" if profile == "chromeos" else
                    "luna-tray" if profile == "winxp" else "frutiger-tray")
                row.pack_end(right_area, False, False, 0 if profile == "winxp" else 4)
            desktop = self._class(Gtk.Button(), "aero-desktop")
            if profile == "aero":
                desktop.get_style_context().add_class("win7-desktop")
                desktop.set_tooltip_text("Peek at desktop (hover) / Show desktop (click)")
                desktop.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
                desktop.connect("enter-notify-event", self._win7_begin_peek)
                desktop.connect("leave-notify-event", self._win7_leave_peek)
            else:
                desktop.set_tooltip_text("Show desktop / restore windows")
            desktop.get_accessible().set_name("Show desktop or restore windows")
            desktop.connect("clicked", self._show_desktop)
            if profile not in ("winclassic", "winxp"):
                right_area.pack_end(desktop, False, False, 0)
            self.show_desktop_button = desktop_quick if profile in ("winclassic", "winxp") else desktop
            clock = self._class(Gtk.Label(), "aero-time")
            clock.set_justify(Gtk.Justification.CENTER)
            if profile == "winclassic":
                clock_button = self._class(Gtk.Button(), "classic98-clock-button")
                self.classic98_clock_button = clock_button
                clock_button.add(clock)
                clock_button.set_tooltip_text("Open date and time")
                clock_button.get_accessible().set_name("Open date and time")
                clock_button.connect("clicked", lambda _button:
                                     self.classic98_tray_show("clock"))
                right_area.pack_end(clock_button, False, False, 4)
            elif profile == "chromeos":
                clock_button = self._class(Gtk.Button(), "chrome-clock-button")
                clock_button.add(clock)
                clock_button.set_tooltip_text("Open local calendar")
                clock_button.get_accessible().set_name("Open local calendar")
                clock_button.connect("clicked", lambda _button: self._toggle_chrome_calendar())
                right_area.pack_end(clock_button, False, False, 4)
                bell = self._class(Gtk.Button(), "chrome-clock-button")
                self.chrome_notifications_button = bell
                bell_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
                bell_content.pack_start(self._icon("preferences-system-notifications",
                                                   Gtk.IconSize.MENU), False, False, 0)
                self.chrome_notifications_badge = self._class(
                    Gtk.Label(label=""), "chrome-notifications-badge")
                bell_content.pack_start(self.chrome_notifications_badge, False, False, 0)
                bell.add(bell_content)
                bell.set_tooltip_text("Open notification history")
                bell.get_accessible().set_name("Open notifications")
                bell.connect("clicked", lambda _button: self._toggle_chrome_notifications())
                right_area.pack_end(bell, False, False, 0)
            elif profile in ("winxp", "aero"):
                clock_button = self._class(Gtk.Button(), "luna-clock-button" if profile == "winxp"
                                           else "win7-clock-button")
                clock_button.add(clock)
                clock_button.get_accessible().set_name("Show date and calendar")
                self._luna_clock_button = clock_button
                if profile == "winxp":
                    clock_button.set_tooltip_text("Show the current date and calendar")
                right_area.pack_end(clock_button, False, False, 6)
            elif profile == "frutiger":
                clock_button = self._class(Gtk.Button(), "rice-status")
                clock_button.add(clock)
                clock_button.get_accessible().set_name("Open Aqua calendar")
                clock_button.set_tooltip_text("Show the current date and local calendar")

                def show_aqua_calendar(_button):
                    if hasattr(self, "_aqua_notifications"):
                        self._aqua_notifications.popover.popdown()
                    if hasattr(self, "_aqua_flyouts"):
                        for other in self._aqua_flyouts.popovers.values():
                            other.popdown()
                    if hasattr(self, "_aqua_drives"):
                        self._aqua_drives.popover.popdown()
                    if not hasattr(self, "_aqua_calendar"):
                        from .frutiger_calendar import AquaCalendar
                        self._aqua_calendar = AquaCalendar(clock_button, Gtk)
                    self._aqua_calendar.show()

                clock_button.connect("clicked", show_aqua_calendar)
                right_area.pack_end(clock_button, False, False, 6)
                self.aqua_clock_button = clock_button
            else:
                right_area.pack_end(clock, False, False, 6)
            if tiles:
                action = self._class(
                    Gtk.Button() if profile == "chromeos" else Gtk.Button(label="▤"),
                    "aero-quick")
                if profile == "chromeos":
                    action.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
                action.get_accessible().set_name("Toggle " + (heritage.control_heading if heritage else "Windows 10 Action Center"))
                action.set_tooltip_text("Quick settings and notification information")
                action.connect("clicked", lambda _button: self._toggle_actions())
                right_area.pack_end(action, False, False, 0)
            elif profile != "aero":
                control = self._class(Gtk.Button(), "aero-quick")
                control.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
                control.set_tooltip_text("Control Panel")
                control.get_accessible().set_name("Toggle " + (heritage.control_heading if heritage else "Windows 7 Control Panel"))
                control.connect("clicked", lambda _button: self._toggle_actions())
                right_area.pack_end(control, False, False, 0)
            self._install_status_widgets(right_area)
            tray_option = "RICEHUB_TEN_TRAY" if ten else f"RICEHUB_{profile.upper()}_TRAY"
            if os.environ.get(tray_option, "1") != "0":
                tray_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                right_area.pack_end(tray_box, False, False, 4)
                try:
                    from .aero_tray import StatusNotifierTray
                    self._tray = StatusNotifierTray(
                        tray_box, Gtk, Gio, GLib, GdkPixbuf,
                        visible_limit=3 if profile in ("aero", "winxp") else None,
                        theme="luna" if profile == "winxp" else "win7")
                except (GLib.Error, RuntimeError, OSError) as exc:
                    logging.getLogger(__name__).warning("Optional Aero tray unavailable: %s", exc)
            def update_clock():
                clock.set_text(GLib.DateTime.new_now_local().format(
                    "%H:%M" if profile in ("winxp", "winclassic") else
                    "%H:%M\n%d %b" if not ten else "%H:%M\n%d/%m/%Y"))
                if profile in ("winxp", "winclassic"):
                    clock.set_tooltip_text(GLib.DateTime.new_now_local().format("%A, %d %B %Y"))
                return True
            update_clock()
            GLib.timeout_add_seconds(30, update_clock)
            win.add(row)
            win.connect("realize", self._reserve_workarea)
            win.connect("map-event", self._publish_ready)
            win.show_all()
            if profile == "winclassic":
                self._classic98_apply_taskbar_options()
            elif profile == "winxp":
                self._luna_apply_taskbar_options()
            win.move(rect.x, rect.y + rect.height - panel_height)
            self.bar = win
            if profile == "windows10":
                from .ten_network import TenNetworkFlyout

                self.ten_network = TenNetworkFlyout(self, Gtk, Gdk,
                                                    self.ten_controller.runner)

        def _classic98_apply_taskbar_options(self):
            if profile != "winclassic" or self._classic98_taskbar_options is None:
                return
            for widget, key in (
                (self.classic98_quick_launch, "show_quick_launch"),
                (self.classic98_clock_button, "show_clock"),
            ):
                if widget is not None:
                    widget.set_visible(self._classic98_taskbar_options[key])

        def _effective_task_pin_count(self):
            if (profile == "winxp" and self._luna_taskbar_options is not None and
                    not self._luna_taskbar_options["show_quick_launch"]):
                return 0
            return self._pin_count

        def _luna_apply_taskbar_options(self):
            if profile != "winxp" or self._luna_taskbar_options is None:
                return
            self._luna_quick_launch.set_visible(self._luna_taskbar_options["show_quick_launch"])
            self._luna_quick_separator.set_visible(self._luna_taskbar_options["show_quick_launch"])
            self._luna_clock_button.set_visible(self._luna_taskbar_options["show_clock"])
            self._task_capacity = task_capacity(self._desktop_rect().width,
                                                self._effective_task_pin_count(), 230)
            if getattr(self, "_window_tracker", None) is not None:
                self._window_tracker.refresh()
            if getattr(self, "menu", None) is not None and self.menu.get_visible():
                self._populate(self.search.get_text())

        def _luna_install_volume_notifications(self):
            """Use Gio's actual mount signals; avoid polling or fabricated ejects."""
            try:
                monitor = Gio.VolumeMonitor.get()
                connected = (
                    monitor.connect("mount-added", self._luna_mount_event, True),
                    monitor.connect("mount-removed", self._luna_mount_event, False),
                )
            except (GLib.Error, RuntimeError, OSError) as exc:
                logging.getLogger(__name__).debug("XP removable-mount notifications unavailable: %s", exc)
                return
            self._luna_volume_monitor = monitor
            self._luna_volume_signals = connected

        def _luna_mount_event(self, _monitor, mount, added):
            if self.luna_balloon is None:
                return
            from .luna_notifications import removable_mount_message
            message = removable_mount_message(mount, added=added)
            if message:
                if profile == "aero" and self.luna_tray is not None:
                    self.luna_tray.announce(message)
                else:
                    self.luna_balloon.show(message)

        def luna_open_taskbar_properties(self):
            if profile != "winxp":
                return
            from .luna_taskbar_settings import show
            show(self, Gtk)

        def _luna_open_help(self):
            if profile != "winxp":
                return
            from .luna_help import show_help
            show_help(self, Gtk)

        def _luna_open_run(self):
            if profile != "winxp":
                return
            from .classic98_menu import show_run
            show_run(self, Gtk, Gio, theme="winxp")

        def _luna_start_context(self, _widget, event):
            if profile != "winxp" or event.button != 3:
                return False
            menu = Gtk.Menu()
            self._track_start_popup(menu)
            item = Gtk.MenuItem(label="Properties")
            item.connect("activate", lambda *_args: self.luna_open_taskbar_properties())
            menu.append(item)
            menu.show_all()
            menu.popup_at_pointer(event)
            return True

        def classic98_open_taskbar_properties(self):
            if profile != "winclassic":
                return
            from .classic98_taskbar_settings import show
            show(self, Gtk)

        def _classic98_taskbar_context(self, _widget, event):
            if profile != "winclassic" or event.button != 3:
                return False
            menu = self._classic98_taskbar_menu()
            menu.show_all()
            menu.popup_at_pointer(event)
            return True

        def _task_manager_item(self, label="Task Manager"):
            name = preferred_task_manager()
            item = Gtk.MenuItem(label=label)
            item.set_sensitive(name is not None)
            if name is None:
                item.set_tooltip_text("Install xfce4-taskmanager or gnome-system-monitor")
            else:
                item.connect("activate", lambda _item, selected=name: self._open_tool(selected))
            return item

        def _classic98_taskbar_menu(self):
            menu = Gtk.Menu()
            menu.get_style_context().add_class("classic98-window-menu")
            menu.append(self._task_manager_item())
            menu.append(Gtk.SeparatorMenuItem())
            properties = Gtk.MenuItem(label="Properties")
            properties.connect("activate", lambda *_args:
                               self.classic98_open_taskbar_properties())
            menu.append(properties)
            return menu

        def _luna_taskbar_context(self, _widget, event):
            """XP blank-taskbar menu; actions touch no XFCE state without consent."""
            if profile != "winxp" or event.button != 3:
                return False
            menu = self._luna_taskbar_menu()
            menu.show_all()
            menu.popup_at_pointer(event)
            return True

        def _luna_taskbar_menu(self):
            menu = Gtk.Menu()
            self._track_start_popup(menu)
            menu.append(self._task_manager_item())
            menu.append(Gtk.SeparatorMenuItem())
            for title, action in (
                ("Taskbar and Start Menu Properties…", self.luna_open_taskbar_properties),
                ("Customize notification icons…", lambda: self._tray.open_preferences()
                 if self._tray is not None else None),
                ("Show Desktop", self._show_desktop),
                ("Add XP desktop icons…", lambda: self._luna_manage_desktop("install")),
                ("Remove XP desktop icons…", lambda: self._luna_manage_desktop("remove")),
                ("Desktop Properties…", lambda: self._open_tool("xfdesktop-settings")),
            ):
                if title in ("Show Desktop", "Desktop Properties…"):
                    menu.append(Gtk.SeparatorMenuItem())
                item = Gtk.MenuItem(label=title)
                if title == "Desktop Properties…":
                    item.set_sensitive(shutil.which("xfdesktop-settings") is not None)
                elif title == "Customize notification icons…":
                    item.set_sensitive(self._tray is not None)
                item.connect("activate", lambda _item, callback=action: callback())
                menu.append(item)
            return menu

        def _ten_taskbar_context(self, _widget, event):
            """Right-click blank Windows 10 taskbar space, not pinned apps or tray."""
            if profile != "windows10" or event.button != 3:
                return False
            menu = self._ten_taskbar_menu()
            menu.show_all()
            menu.popup_at_pointer(event)
            return True

        def _ten_taskbar_menu(self):
            menu = Gtk.Menu()
            menu.get_style_context().add_class("aero-menu-root")
            desktop = Gtk.MenuItem(label="Show the desktop")
            desktop.set_sensitive(self._window_tracker is not None)
            desktop.connect("activate", lambda _item: self._show_desktop())
            menu.append(desktop)
            menu.append(Gtk.SeparatorMenuItem())
            menu.append(self._task_manager_item())
            return menu

        def _luna_manage_desktop(self, action):
            """Explicit opt-in with confirmation; untouched user icons remain safe."""
            self._manage_desktop_shortcuts(action, "winxp")

        def _win7_taskbar_context(self, _widget, event):
            """Windows 7 blank Superbar area, without stealing app/SNI clicks."""
            if profile != "aero" or event.button != 3:
                return False
            menu = self._win7_taskbar_menu()
            menu.show_all()
            menu.popup_at_pointer(event)
            return True

        def _win7_visible_layout_windows(self):
            """Only normal visible windows on the focused monitor can be tiled."""
            tracker = self._window_tracker
            if tracker is None or self._win7_snap is None:
                return None, ()
            windows = []
            for window in tracker.screen.get_windows():
                if (is_task_window(window, tracker.wnck) and not window.is_minimized()
                        and not window.is_fullscreen()):
                    area = self._win7_window_workarea(int(window.get_xid()))
                    if area is not None:
                        windows.append((int(window.get_xid()), area))
            if not windows:
                return None, ()
            active = tracker.screen.get_active_window()
            active_xid = int(active.get_xid()) if active is not None else None
            selected_area = next((area for xid, area in windows if xid == active_xid), windows[0][1])
            return selected_area, tuple(xid for xid, area in windows if area == selected_area)

        def _win7_arrange_desktop_windows(self, mode):
            if self._win7_snap is None:
                return
            if mode == "undo":
                previous = tuple(self._win7_snap.original)
                for xid in previous:
                    self._win7_arrange_window(xid, "restore")
                return
            area, xids = self._win7_visible_layout_windows()
            if area is None:
                return
            positions = window_layout(area, len(xids), mode)
            timestamp = Gtk.get_current_event_time()
            for xid, geometry in zip(xids, positions):
                self._win7_snap.place(xid, geometry, timestamp)

        def _win7_taskbar_menu(self):
            """Create real Windows 7 desktop actions with supported backends."""
            menu = Gtk.Menu()
            menu.get_style_context().add_class("win7-jumplist")
            area, xids = self._win7_visible_layout_windows()
            for title, mode in (("Cascade windows", "cascade"),
                                ("Show windows stacked", "stacked"),
                                ("Show windows side by side", "side-by-side"),
                                ("Undo window arrangement", "undo")):
                item = Gtk.MenuItem(label=title)
                if mode == "undo":
                    available = bool(self._win7_snap and self._win7_snap.original)
                else:
                    available = bool(area and window_layout(area, len(xids), mode))
                item.set_sensitive(available)
                item.set_tooltip_text("Only normal, visible windows on the active monitor; up to 12 at once")
                item.connect("activate", lambda _item, selected=mode:
                             self._win7_arrange_desktop_windows(selected))
                menu.append(item)
            menu.append(Gtk.SeparatorMenuItem())
            for title, action in (
                ("Show the desktop", self._show_desktop),
                ("Customize notification icons…", lambda: self._tray.open_preferences()
                 if self._tray is not None else None),
                ("Add Windows 7 desktop icons…", lambda: self._win7_manage_desktop("install")),
                ("Remove RiceBowl desktop icons…", lambda: self._win7_manage_desktop("remove")),
                ("Personalize…", lambda: self._open_tool("xfdesktop-settings")),
            ):
                if title == "Personalize…":
                    menu.append(Gtk.SeparatorMenuItem())
                item = Gtk.MenuItem(label=title)
                if title == "Personalize…":
                    item.set_sensitive(shutil.which("xfdesktop-settings") is not None)
                elif title == "Customize notification icons…":
                    item.set_sensitive(self._tray is not None)
                item.connect("activate", lambda _item, callback=action: callback())
                menu.append(item)
            menu.append(Gtk.SeparatorMenuItem())
            menu.append(self._task_manager_item(label="Start Task Manager"))
            return menu

        def _win7_manage_desktop(self, action):
            self._manage_desktop_shortcuts(action, "aero")

        def _manage_desktop_shortcuts(self, action, style):
            """Install/remove only our unedited links after explicit confirmation."""
            if profile != style:
                return
            from .riceware.plate import manage_shortcuts

            era = "Windows 7" if style == "aero" else "XP"
            managed_profile = "win7" if style == "aero" else "xp"

            title = ("Add " + era + " desktop icons?" if action == "install" else
                     "Remove RiceBowl " + era + " desktop icons?")
            dialog = Gtk.MessageDialog(
                transient_for=self.bar, flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO, text=title)
            dialog.format_secondary_text(
                "Only unmodified RiceBowl " + era + " shortcuts are changed. Existing files and edited shortcuts "
                "are always preserved. XFDesktop manages icons and trash using real Linux backends.")
            answer = dialog.run()
            dialog.destroy()
            if answer != Gtk.ResponseType.YES:
                return
            try:
                changed, kept = manage_shortcuts(managed_profile, action)
            except (OSError, RuntimeError, ValueError) as exc:
                self._error(str(exc), title=era + " desktop icons")
                return
            info = (str(len(changed)) + " shortcuts " +
                    ("installed" if action == "install" else "removed") + ".")
            if kept:
                info += " Preserved: " + ", ".join(kept)
            result = Gtk.MessageDialog(
                transient_for=self.bar, flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.CLOSE, text=era + " desktop icons")
            result.format_secondary_text(info)
            result.run()
            result.destroy()

        def _windows_changed(self, windows, active):
            """Render copied task data without retaining native WnckWindow objects."""
            if profile == "aero":
                self._win7_windows_changed(windows, active)
                return
            if profile == "winxp":
                should_group = (self._luna_taskbar_options["group_similar_windows"] and
                                len(windows) > self._task_capacity)
                if should_group:
                    self._luna_windows_grouped(windows, active)
                    return
                if self._luna_grouped_mode:
                    self._luna_grouped_mode = False
                    self._visible_window_ids = ()
                    self._luna_group_buttons.clear()
                    self._luna_group_members.clear()
                    for child in self.tasks.get_children():
                        self.tasks.remove(child)
            visible, self._overflow_windows = select_windows(tuple(windows), active, self._task_capacity)
            visible_ids = tuple(window.xid for window in visible)
            if visible_ids != self._visible_window_ids:
                for child in self.tasks.get_children():
                    self.tasks.remove(child)
                previous = self.window_buttons
                self.window_buttons = {}
                for window in visible:
                    xid = window.xid
                    if xid in previous:
                        button, icon, label = previous[xid]
                    else:
                        button = self._class(Gtk.Button(), "aero-task")
                        if profile == "aero":
                            button.get_style_context().add_class("win7-task")
                        button.set_size_request(44 if profile == "aero" else
                                                42 if profile in ("chromeos", "windows10") else 135,
                                                37 if profile == "aero" else 35)
                        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                        label = Gtk.Label(xalign=0)
                        label.set_max_width_chars(12)
                        label.set_ellipsize(Pango.EllipsizeMode.END)
                        if profile in ("chromeos", "aero", "windows10"):
                            label.set_no_show_all(True)
                            label.hide()
                        content.pack_start(icon, False, False, 0)
                        content.pack_start(label, True, True, 0)
                        button.add(content)
                        button.connect("clicked", lambda _btn, target=xid: self._activate_task(target))
                        if profile == "winclassic":
                            button.connect("button-press-event", lambda widget, event, target=xid:
                                           self._classic_task_context(widget, event, target))
                        elif profile == "winxp":
                            button.connect("button-press-event", lambda widget, event, target=xid:
                                           self._luna_task_context(widget, event, target))
                    self.window_buttons[xid] = (button, icon, label)
                    self.tasks.pack_start(button, False, False, 0)
                self._visible_window_ids = visible_ids
            for window in visible:
                button, icon, label = self.window_buttons[window.xid]
                title = window.title
                if label.get_text() != title:
                    label.set_text(title)
                    button.set_tooltip_text(title)
                    button.get_accessible().set_name("Switch to " + title)
                pixbuf = window.mini_icon
                if pixbuf is not None:
                    icon.set_from_pixbuf(pixbuf)
                context = button.get_style_context()
                if window == active and not window.minimized:
                    context.add_class("aero-task-active")
                else:
                    context.remove_class("aero-task-active")
            if self._overflow_windows:
                self.overflow_button.set_label(f"+{len(self._overflow_windows)}")
                if self.overflow_button.get_parent() is None:
                    self.tasks.pack_start(self.overflow_button, False, False, 0)
            elif self.overflow_button.get_parent() is self.tasks:
                self.tasks.remove(self.overflow_button)
            self.tasks.show_all()
            if profile == "windows10" and hasattr(self, "ten_task_view"):
                self.ten_task_view.refresh()

        def _luna_windows_grouped(self, windows, active):
            """XP combines siblings only when needed, never by title alone."""
            grouped = group_windows(tuple(windows))
            active_xid = active.xid if active is not None else None
            visible, hidden = select_groups(grouped, active_xid, self._task_capacity)
            self._overflow_windows = tuple(win for group in hidden for win in group.windows)
            self._luna_group_members = {group.key: group for group in grouped}
            identifiers = tuple(group.key for group in visible)
            if (not self._luna_grouped_mode or
                    identifiers != tuple(self._luna_group_buttons)):
                self._luna_grouped_mode = True
                for child in self.tasks.get_children():
                    self.tasks.remove(child)
                self._luna_group_buttons.clear()
                for group in visible:
                    button = self._class(Gtk.Button(), "aero-task")
                    button.get_style_context().add_class("luna-group-task")
                    button.set_size_request(135, 35)
                    line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
                    icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                    caption = Gtk.Label(xalign=0)
                    caption.set_ellipsize(Pango.EllipsizeMode.END)
                    caption.set_max_width_chars(15)
                    line.pack_start(icon, False, False, 0)
                    line.pack_start(caption, True, True, 0)
                    button.add(line)
                    button.connect("clicked", lambda widget, key=group.key:
                                   self._luna_group_click(widget, key))
                    button.connect("button-press-event", lambda widget, event, key=group.key:
                                   self._luna_group_context(widget, event, key))
                    self.tasks.pack_start(button, False, False, 0)
                    self._luna_group_buttons[group.key] = (button, icon, caption)
            for group in visible:
                button, icon, caption = self._luna_group_buttons[group.key]
                current = next((win for win in group.windows if win.xid == active_xid),
                               group.windows[0])
                if current.mini_icon is not None:
                    icon.set_from_pixbuf(current.mini_icon)
                name = current.title if len(group.windows) == 1 else (
                    f"{group.windows[0].title} ({len(group.windows)})")
                caption.set_text(name)
                button.set_tooltip_text("\n".join(win.title for win in group.windows))
                button.get_accessible().set_name("Choose window: " + name)
                state = button.get_style_context()
                if active_xid in group.xids and not current.minimized:
                    state.add_class("aero-task-active")
                else:
                    state.remove_class("aero-task-active")
            if self._overflow_windows:
                self.overflow_button.set_label(f"+{len(self._overflow_windows)}")
                if self.overflow_button.get_parent() is None:
                    self.tasks.pack_start(self.overflow_button, False, False, 0)
            elif self.overflow_button.get_parent() is self.tasks:
                self.tasks.remove(self.overflow_button)
            self.tasks.show_all()

        def _luna_group_click(self, button, key):
            group = self._luna_group_members.get(key)
            if group is None:
                return
            if len(group.windows) == 1:
                self._activate_task(group.windows[0].xid)
            else:
                self._luna_group_popup(button, group)

        def _luna_group_context(self, button, event, key):
            if event.button != 3:
                return False
            group = self._luna_group_members.get(key)
            if group is None:
                return False
            self._luna_group_popup(button, group, show_close=True)
            return True

        def _luna_group_popup(self, button, group, *, show_close=False):
            menu = Gtk.Menu()
            self._track_start_popup(menu)
            for window in group.windows:
                item = Gtk.MenuItem(label=window.title)
                item.connect("activate", lambda _item, xid=window.xid:
                             self._activate_task(xid))
                menu.append(item)
            if show_close:
                menu.append(Gtk.SeparatorMenuItem())
                for window in group.windows:
                    item = Gtk.MenuItem(label="Close " + window.title)
                    item.connect("activate", lambda _item, xid=window.xid:
                                 self._win7_close_window(xid))
                    menu.append(item)
            menu.show_all()
            menu.popup_at_widget(button, Gdk.Gravity.NORTH_WEST,
                                 Gdk.Gravity.SOUTH_WEST, None)

        def _win7_windows_changed(self, windows, active):
            """Show one task button per WM_CLASS, never discard member windows."""
            groups = group_windows(tuple(windows))
            active_xid = active.xid if active is not None else None
            if self._win7_snap is not None:
                self._win7_snap.forget_closed(window.xid for window in windows)
            visible, hidden = select_groups(groups, active_xid, self._task_capacity)
            self._overflow_windows = tuple(member for group in hidden for member in group.windows)
            identifiers = tuple(group.key for group in visible)
            signature = {group.key: group.xids for group in groups}
            if signature != self._win7_group_signature:
                self._win7_stop_preview()
            self._win7_group_signature = signature
            self._win7_group_members = {group.key: group for group in groups}
            if identifiers != self._win7_visible_groups:
                self._win7_stop_preview()
                for child in self.tasks.get_children():
                    self.tasks.remove(child)
                self._win7_group_buttons.clear()
                for group in visible:
                    button = self._class(Gtk.Button(), "aero-task")
                    button.get_style_context().add_class("win7-task")
                    button.set_size_request(48, 42)
                    content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                    icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                    badge = self._class(Gtk.Label(), "win7-group-count")
                    badge.set_no_show_all(True)
                    content.pack_start(icon, False, False, 0)
                    content.pack_start(badge, False, False, 0)
                    button.add(content)
                    button.connect("clicked", lambda widget, key=group.key:
                                   self._win7_group_click(key, widget))
                    button.connect("button-press-event", lambda widget, event, key=group.key:
                                   self._win7_group_context(widget, event, key))
                    button.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
                    button.connect("enter-notify-event", lambda widget, event, key=group.key:
                                   self._win7_preview_hover(widget, key))
                    button.connect("leave-notify-event", self._win7_preview_leave)
                    self.tasks.pack_start(button, False, False, 0)
                    self._win7_group_buttons[group.key] = (button, icon, badge)
                self._win7_visible_groups = identifiers
            for group in visible:
                button, icon, badge = self._win7_group_buttons[group.key]
                foreground = next((w for w in group.windows if w.xid == active_xid), group.windows[0])
                artwork = foreground.large_icon or foreground.mini_icon
                if artwork is not None:
                    # Wnck's mini icon is normally 16px; the original Win7
                    # large-icon Superbar uses a ~32px image, so prefer its
                    # high-resolution counterpart without retaining Wnck objects.
                    if foreground.large_icon is not None and (
                            artwork.get_width() > 30 or artwork.get_height() > 30):
                        artwork = artwork.scale_simple(30, 30, GdkPixbuf.InterpType.BILINEAR)
                    icon.set_from_pixbuf(artwork)
                count = len(group.windows)
                badge.set_text(str(count))
                if count > 1:
                    badge.show()
                else:
                    badge.hide()
                title = (group.title if count == 1 else f"{group.title} ({count} windows)")
                attention = any(w.needs_attention and w.xid != active_xid for w in group.windows)
                if attention:
                    title += " — Needs attention"
                button.set_tooltip_text(title)
                button.get_accessible().set_name("Open window previews for " + title)
                style = button.get_style_context()
                if attention:
                    style.add_class("win7-task-attention")
                else:
                    style.remove_class("win7-task-attention")
                if active_xid in group.xids and not foreground.minimized:
                    style.add_class("aero-task-active")
                else:
                    style.remove_class("aero-task-active")
            if self._overflow_windows:
                self.overflow_button.set_label(f"+{len(self._overflow_windows)}")
                if self.overflow_button.get_parent() is None:
                    self.tasks.pack_start(self.overflow_button, False, False, 0)
            elif self.overflow_button.get_parent() is self.tasks:
                self.tasks.remove(self.overflow_button)
            self.tasks.show_all()
            for group in visible:
                if len(group.windows) == 1:
                    self._win7_group_buttons[group.key][2].hide()

        def _win7_group_click(self, key, button):
            group = self._win7_group_members.get(key)
            if group is None:
                return
            if len(group.windows) == 1:
                self._win7_stop_preview()
                self._activate_task(group.windows[0].xid)
            else:
                self._win7_stop_preview()
                self._win7_show_preview(key, button)

        def _win7_close_window(self, xid):
            """Ask the real application to close; it can still warn about unsaved work."""
            if self._window_tracker is None:
                return
            window = self._window_tracker.wnck.Window.get(xid)
            if window is not None:
                window.close(Gtk.get_current_event_time())
            self._win7_stop_preview()

        def _win7_window_workarea(self, xid):
            """Use the selected window's monitor including its X11 panel struts."""
            if self._window_tracker is None:
                return None
            window = self._window_tracker.wnck.Window.get(xid)
            if window is None:
                return None
            display = Gdk.Display.get_default()
            if display is None:
                return None
            regions = []
            for index in range(display.get_n_monitors()):
                monitor = display.get_monitor(index)
                if monitor is not None:
                    region = monitor.get_workarea()
                    if region.width > 0 and region.height > 0:
                        regions.append((region.x, region.y, region.width, region.height))
            if not regions:
                return None
            return closest_workarea(tuple(window.get_geometry()), tuple(regions))

        def _win7_arrange_window(self, xid, action):
            """Arrange with Wnck/XFWM; do not intercept system-wide keybindings."""
            if self._win7_snap is None:
                return
            area = self._win7_window_workarea(xid)
            if area is None:
                return
            if not self._win7_snap.arrange(xid, action, area, Gtk.get_current_event_time()):
                logging.getLogger(__name__).info("Cannot %s window %s", action, xid)

        def _win7_append_arrange_items(self, menu, xid):
            for title, action in (("Snap to left half", "left"),
                                  ("Snap to right half", "right"),
                                  ("Maximize", "maximize"),
                                  ("Restore previous size", "restore")):
                item = Gtk.MenuItem(label=title)
                item.set_sensitive(self._win7_snap is not None and
                                   (action != "restore" or xid in self._win7_snap.original))
                item.connect("activate", lambda _item, target=xid, mode=action:
                             self._win7_arrange_window(target, mode))
                menu.append(item)

        def _win7_group_context(self, button, event, key):
            if event.button != 3:
                return False
            menu = self._win7_group_menu(key)
            if menu is None:
                return False
            self._win7_stop_preview()
            menu.show_all()
            menu.popup_at_pointer(event)
            return True

        def _win7_group_menu(self, key):
            """Build a fully native Jump List; the caller owns its GTK lifetime."""
            group = self._win7_group_members.get(key)
            if group is None:
                return None
            menu = Gtk.Menu()
            menu.get_style_context().add_class("win7-jumplist")
            app = self._win7_group_app(key)
            if app is not None:
                name = app.get_display_name() or app.get_name()
                launch = Gtk.MenuItem(label="Open new " + name + " window")
                launch.connect("activate", lambda _item, selected=app: self._launch(selected))
                menu.append(launch)
                identifier = app.get_id()
                if identifier:
                    pinned = identifier in self._pinned_ids
                    pin = Gtk.MenuItem(label="Unpin from taskbar" if pinned else "Pin to taskbar")
                    pin.set_sensitive(pinned or len(self._pinned_ids) < PIN_LIMIT)
                    pin.connect("activate", lambda _item: self._change_pin(identifier, not pinned))
                    menu.append(pin)
                menu.append(Gtk.SeparatorMenuItem())
            for window in group.windows[:16]:
                item = Gtk.MenuItem(label="Switch to " + window.title)
                item.connect("activate", lambda _item, xid=window.xid: self._activate_task(xid))
                menu.append(item)
            if self._win7_snap is not None:
                menu.append(Gtk.SeparatorMenuItem())
                if len(group.windows) == 1:
                    self._win7_append_arrange_items(menu, group.windows[0].xid)
                else:
                    arrange = Gtk.MenuItem(label="Arrange windows")
                    submenu = Gtk.Menu()
                    for window in group.windows[:16]:
                        window_item = Gtk.MenuItem(label=window.title)
                        window_menu = Gtk.Menu()
                        self._win7_append_arrange_items(window_menu, window.xid)
                        window_item.set_submenu(window_menu)
                        submenu.append(window_item)
                    arrange.set_submenu(submenu)
                    menu.append(arrange)
            menu.append(Gtk.SeparatorMenuItem())
            for window in group.windows[:16]:
                item = Gtk.MenuItem(label="Close " + window.title)
                item.connect("activate", lambda _item, xid=window.xid: self._win7_close_window(xid))
                menu.append(item)
            return menu

        def _win7_group_app(self, key):
            """Match WM_CLASS to installed .desktop metadata only when unambiguous."""
            if not key.startswith("app:"):
                return None
            group_id = key[4:]
            candidates = []
            for app in self.apps:
                wmclass = getattr(app, "get_startup_wm_class", None)
                identity = wmclass() if callable(wmclass) else None
                desktop_id = app.get_id() or ""
                if ((identity and identity.casefold() == group_id) or
                        desktop_id.casefold() == group_id + ".desktop"):
                    candidates.append(app)
            return candidates[0] if len(candidates) == 1 else None

        def _win7_preview_hover(self, button, key):
            if self._win7_preview_timer:
                GLib.source_remove(self._win7_preview_timer)
            self._win7_preview_timer = GLib.timeout_add(450, self._win7_show_preview, key, button)
            return False

        def _win7_preview_leave(self, *_args):
            if self._win7_preview_timer:
                GLib.source_remove(self._win7_preview_timer)
            self._win7_preview_timer = GLib.timeout_add(650, self._win7_stop_preview)
            return False

        def _win7_stop_preview(self, *_args):
            if self._win7_preview_timer:
                GLib.source_remove(self._win7_preview_timer)
                self._win7_preview_timer = 0
            if self._win7_preview is not None:
                self._win7_preview.popdown()
                self._win7_preview.destroy()
                self._win7_preview = None
            self._win7_preview_group = None
            return False

        def _win7_thumbnail(self, xid):
            """Bounded best-effort capture of an X11 drawable, never persisted."""
            if (self._window_tracker is None or
                    self._window_tracker.wnck.Window.get(xid) is None):
                return None
            try:
                gi.require_version("GdkX11", "3.0")
                from gi.repository import GdkX11
                drawable = GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(), xid)
                if drawable is None or not drawable.is_visible():
                    return None
                width, height = min(drawable.get_width(), 360), min(drawable.get_height(), 210)
                if width < 20 or height < 20:
                    return None
                pixbuf = Gdk.pixbuf_get_from_window(drawable, 0, 0, width, height)
                if pixbuf is not None:
                    return pixbuf.scale_simple(180, 105, GdkPixbuf.InterpType.BILINEAR)
            except (ImportError, GLib.Error, OSError, RuntimeError, ValueError, AttributeError) as exc:
                logging.getLogger(__name__).debug("X11 thumbnail unavailable: %s", exc)
            return None

        def _win7_show_preview(self, key, button):
            self._win7_preview_timer = 0
            group = self._win7_group_members.get(key)
            if group is None or not button.get_mapped():
                return False
            if self._win7_preview_group == key and self._win7_preview is not None:
                return False
            self._win7_stop_preview()
            popover = self._class(Gtk.Popover.new(button), "win7-preview")
            popover.set_modal(False)
            popover.set_position(Gtk.PositionType.TOP)
            popover.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
            popover.connect("enter-notify-event", lambda *_args: self._win7_cancel_preview_timer())
            popover.connect("leave-notify-event", self._win7_preview_leave)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
            scroller.set_size_request(min(620, len(group.windows) * 200), 166)
            cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            for window in group.windows[:20]:
                card = self._class(Gtk.Button(), "win7-preview-card")
                card.set_size_request(193, 153)
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                thumb = self._win7_thumbnail(window.xid)
                if thumb is not None:
                    picture = Gtk.Image.new_from_pixbuf(thumb)
                else:
                    picture = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL),
                                          "win7-preview-fallback")
                    preview_icon = (Gtk.Image.new_from_pixbuf(window.mini_icon) if
                                    window.mini_icon is not None else
                                    self._icon("application-x-executable", Gtk.IconSize.DIALOG))
                    picture.set_center_widget(preview_icon)
                content.pack_start(picture, True, True, 0)
                caption = self._class(Gtk.Label(label=window.title), "win7-preview-name")
                caption.set_max_width_chars(23)
                caption.set_ellipsize(Pango.EllipsizeMode.END)
                content.pack_start(caption, False, False, 0)
                card.add(content)
                card.get_accessible().set_name("Activate " + window.title)
                card.connect("clicked", lambda _btn, xid=window.xid: self._activate_preview(xid))
                cards.pack_start(card, False, False, 0)
            scroller.add(cards)
            popover.add(scroller)
            self._win7_preview = popover
            self._win7_preview_group = key
            popover.show_all()
            popover.popup()
            return False

        def _win7_cancel_preview_timer(self):
            if self._win7_preview_timer:
                GLib.source_remove(self._win7_preview_timer)
                self._win7_preview_timer = 0
            return False

        def _activate_preview(self, xid):
            self._win7_stop_preview()
            self._activate_task(xid)

        def _classic_task_context(self, widget, event, xid):
            from .classic98_taskbar import show

            return show(self, widget, event, xid, Gtk, Gdk)

        def _luna_task_context(self, widget, event, xid):
            """Use verified live Wnck operations, with an XP-specific popup skin."""
            from .classic98_taskbar import show

            return show(self, widget, event, xid, Gtk, Gdk, style_class="luna-popup")

        def _activate_task(self, xid):
            if self._window_tracker:
                # Resolve a live object only for this click; never capture it in
                # a button closure after the application window is closed.
                toggle_window_id(self._window_tracker.wnck, self._window_tracker.screen,
                                 xid, Gtk.get_current_event_time())
            self._hide_menu()

        def _show_overflow(self, button):
            menu = Gtk.Menu()
            for window in self._overflow_windows:
                item = Gtk.MenuItem(label=window.title)
                item.connect("activate", lambda _item, target=window.xid: self._activate_task(target))
                menu.append(item)
            menu.show_all()
            menu.popup_at_widget(button, Gdk.Gravity.NORTH_WEST, Gdk.Gravity.SOUTH_WEST, None)

        def _win7_side_action(self, title, icon, *, path=None, commands=(), callback=None):
            """Render a real Win7-style place, disabling unavailable Linux tools."""
            if path is not None:
                return self._place_button(title, icon, path, css_class="win7-place")
            button = self._class(Gtk.Button(), "win7-place")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.pack_start(self._icon(icon, Gtk.IconSize.MENU), False, False, 0)
            row.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
            button.add(row)
            selected = next((program for program in commands if shutil.which(program)), None)
            button.set_sensitive(callback is not None or selected is not None)
            button.get_accessible().set_name("Open " + title)
            button.set_tooltip_text("Open " + title if callback or selected else
                                    "Requires " + " or ".join(commands))
            if callback is not None:
                button.connect("clicked", lambda _button: callback())
            elif selected:
                button.connect("clicked", lambda _button, program=selected: self._open_tool(program))
            return button

        def _open_win7_explorer(self):
            binary = shutil.which("rice-explorer")
            if not binary:
                self._error("Install RiceExplorer to use the optional Windows 7 file manager.")
                return
            try:
                subprocess.Popen(win7_explorer_command(binary, Path.home()),
                                 start_new_session=True)
            except OSError as exc:
                self._error("Could not start RiceExplorer: " + str(exc))
                return
            self._hide_menu()

        def _win7_expand_programs(self):
            self._win7_all_programs = not self._win7_all_programs
            self._app_page_size = 24
            self._populate(self.search.get_text())

        def _create_win7_menu(self):
            """Aero Start: white recent-program pane, blue glass links and search."""
            import getpass

            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl Windows 7 Start")
            menu.set_decorated(False)
            menu.set_resizable(True)  # shrink the scroller on 1024x768 displays
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            menu.set_default_size(525, 535)

            frame = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "win7-menu-root")
            left = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                               "win7-programs")
            left.set_size_request(295, -1)
            left.set_hexpand(True)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_height(165)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            scroller.add(self.results)
            left.pack_start(scroller, True, True, 0)
            divider = self._class(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                                  "win7-programs-separator")
            left.pack_start(divider, False, False, 2)
            self.win7_all_button = self._class(Gtk.Button(label="▸  All Programs"),
                                               "win7-all-programs")
            self.win7_all_button.get_accessible().set_name("Show all installed programs")
            self.win7_all_button.connect("clicked", lambda *_args: self._win7_expand_programs())
            left.pack_start(self.win7_all_button, False, False, 0)
            search = self._class(Gtk.SearchEntry(), "win7-search")
            search.set_placeholder_text("Search programs")
            search.get_accessible().set_name("Search installed programs")
            left.pack_end(search, False, False, 0)
            frame.pack_start(left, True, True, 0)

            side = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                               "win7-side")
            side.set_size_request(202, -1)
            avatar = self._class(Gtk.Image(), "win7-user-orb")
            try:
                avatar.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(project_root() / "assets/aero-penguin.svg"), 55, 55, True))
            except (GLib.Error, OSError):
                avatar.set_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
            header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            avatar.set_halign(Gtk.Align.CENTER)
            header.pack_start(avatar, False, False, 0)
            name = self._class(Gtk.Label(label=getpass.getuser()), "win7-user-name")
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_max_width_chars(18)
            header.pack_start(name, False, False, 3)
            side.pack_start(header, False, False, 7)

            home = Path.home()
            for label, icon, folder in (
                ("Documents", "folder-documents", home / "Documents"),
                ("Pictures", "folder-pictures", home / "Pictures"),
                ("Music", "folder-music", home / "Music"),
                ("Downloads", "folder-download", home / "Downloads"),
                ("Computer", "computer", Path("/")),
            ):
                side.pack_start(self._win7_side_action(label, icon, path=folder), False, False, 0)
            # The Rust file manager already ships a structural Win7 skin, but
            # its mount/copy recovery gates are still open. Offer a visible
            # opt-in launch without replacing Thunar or default MIME handlers.
            if shutil.which("rice-explorer"):
                side.pack_start(self._win7_side_action(
                    "RiceExplorer (preview)", "system-file-manager",
                    callback=self._open_win7_explorer), False, False, 0)
            side.pack_start(self._class(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                                        "win7-side-separator"), False, False, 2)
            side.pack_start(self._win7_side_action(
                "Control Panel", "preferences-system", callback=self._toggle_actions),
                False, False, 0)
            side.pack_start(self._win7_side_action(
                "Devices and Printers", "printer", commands=("system-config-printer",)),
                False, False, 0)
            side.pack_start(Gtk.Box(), True, True, 0)
            power = self._class(Gtk.Button(label="Shut down…"), "win7-power")
            power.get_accessible().set_name("Open XFCE session and power options")
            power.set_tooltip_text("Opens the XFCE session dialog; does not immediately shut down")
            power.set_sensitive(shutil.which("xfce4-session-logout") is not None)
            power.connect("clicked", lambda _button: self._open_tool("xfce4-session-logout"))
            power.set_halign(Gtk.Align.END)
            side.pack_end(power, False, False, 3)
            frame.pack_start(side, False, False, 0)

            menu.add(frame)
            self._win7_all_programs = False
            self._finish_heritage_menu(menu, search)

        def _create_menu(self):
            if profile == "aero":
                self._create_win7_menu()
                return
            if profile == "winxp":
                self._create_luna_menu()
                return
            if profile == "winclassic":
                self._create_classic_menu()
                return
            if profile == "frutiger":
                self._create_frutiger_menu()
                return
            if tiles:
                self._create_ten_menu()
                return
            classic = profile == "winclassic"
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl " + (heritage.name if heritage else "Aero") + " Start")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _, _, menu_w, menu_h = menu_geometry(rect.x, rect.y, rect.width, rect.height,
                                                 preferred_width=355 if classic else 490,
                                                 preferred_height=465 if classic else 505)
            menu.set_default_size(menu_w, menu_h)
            body = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "aero-menu-root")
            if classic:
                # Unlike Luna's two-column Start menu, Windows 98/2000 used
                # a narrow program list with a vertical branded side rail.
                badge = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "classic-brand")
                badge.set_size_request(38, -1)
                brand = self._class(Gtk.Label(label="RiceBowl   98"), "classic-brand-label")
                brand.set_angle(90)
                badge.pack_end(brand, False, False, 18)
                body.pack_start(badge, False, False, 0)
            main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7 if classic else 10)
            main.set_margin_start(8 if classic else 14)
            main.set_margin_top(8 if classic else 14)
            main.set_margin_bottom(8 if classic else 10)
            main.set_margin_end(8 if classic else 10)
            main.set_size_request(min(310, max(150, menu_w - (60 if classic else 36))), -1)
            main.pack_start(self._class(Gtk.Label(label=heritage.menu_heading if heritage else "Programs", xalign=0), "aero-menu-heading"), False, False, 0)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search programs")
            search.get_accessible().set_name("Search installed programs")
            main.pack_start(search, False, False, 0)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_height(max(85, min(340, menu_h - 160)))
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            scroller.add(self.results)
            main.pack_start(scroller, True, True, 0)
            body.pack_start(main, True, True, 0)
            if not classic:
                side = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12), "aero-menu-side")
                try:
                    logo = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(project_root() / "assets/aero-penguin.svg"), 70, 70, True))
                except (GLib.Error, OSError):
                    logo = self._icon("start-here", Gtk.IconSize.DIALOG)
                side.pack_start(logo, False, False, 0)
                for title, icon, uri in (
                    ("Home", "user-home", Path.home().as_uri()),
                    ("Computer", "computer", "file:///"),
                    ("Documents", "folder-documents", (Path.home() / "Documents").as_uri()),
                ):
                    btn = self._class(Gtk.Button(label=title), "aero-menu-app")
                    btn.set_image(self._icon(icon, Gtk.IconSize.MENU))
                    btn.set_always_show_image(True)
                    btn.connect("clicked", lambda _btn, address=uri: self._open_uri(address))
                    side.pack_start(btn, False, False, 0)
                if menu_w >= 470:
                    body.pack_start(side, False, False, 0)
            footer = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8), "aero-menu-footer")
            footer.set_margin_top(6)
            if shutil.which("xfce4-settings-manager"):
                settings = self._class(Gtk.Button(label="Control Panel"), "aero-menu-app")
                settings.connect("clicked", lambda _btn: self._open_tool("xfce4-settings-manager"))
                footer.pack_start(settings, True, True, 0)
            if shutil.which("xfce4-session-logout"):
                power = self._class(Gtk.Button(label="Shut down…" if classic else "Log off…"), "aero-menu-power")
                power.set_tooltip_text("Open XFCE's session dialog; no immediate logout")
                power.connect("clicked", lambda _btn: self._open_tool("xfce4-session-logout"))
                footer.pack_end(power, False, False, 0)
            main.pack_end(footer, False, False, 0)
            menu.add(body)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            def update_search(*_args):
                self._app_page_size = 24
                self._populate(search.get_text())
            search.connect("search-changed", update_search)
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu = menu
            self.search = search
            self._populate("")

        def _place_button(self, title, icon_name, path, css_class="rice-place",
                          *, offer_create=False):
            """Use real XDG folders, never a placeholder filesystem action."""
            button = self._class(Gtk.Button(), css_class)
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            content.pack_start(self._icon(icon_name, Gtk.IconSize.MENU), False, False, 0)
            content.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
            button.add(content)
            button.get_accessible().set_name("Open " + title)
            exists = path.is_dir()
            button.set_sensitive(exists or offer_create)
            button.set_tooltip_text("Open " + str(path) if exists else
                                    ("Create and open " + str(path) + " (with confirmation)"
                                     if offer_create else "Folder does not exist: " + str(path)))
            button.connect("clicked", lambda _button, target=path:
                           self._open_luna_user_folder(target) if offer_create else
                           self._open_uri(target.as_uri()))
            if path.is_dir() and path != Path("/"):
                from .riceware.dnd_gtk import attach_folder_drop

                attach_folder_drop(button, path, Gtk, Gdk, GLib)
            return button

        def _finish_heritage_menu(self, menu, search):
            """Same keyboard, focus and installed-app lifecycle for each identity."""
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            def changed(*_args):
                self._app_page_size = 24
                self._populate(search.get_text())
            search.connect("search-changed", changed)
            self.menu, self.search = menu, search
            self._populate("")

        def _track_start_popup(self, menu):
            """Keep the Win98/XP Start window open while GTK cascades own focus."""
            if profile not in ("winxp", "winclassic"):
                return menu
            if profile == "winxp":
                menu.get_style_context().add_class("luna-popup")

            def mapped(_menu):
                self._start_open_menus.add(_menu)
                self._cancel_popup_hide("menu")

            def unmapped(_menu):
                self._start_open_menus.discard(_menu)
                if not self._start_open_menus and not self.menu.is_active():
                    self._schedule_popup_hide("menu")

            menu.connect("map", mapped)
            menu.connect("unmap", unmapped)
            return menu

        def _luna_menu_item(self, title, icon=None):
            """Period-appropriate icon and label for every Luna flyout depth."""
            item = Gtk.MenuItem()
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            if icon is not None:
                if isinstance(icon, Gio.Icon):
                    image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU)
                else:
                    image = self._icon(icon, Gtk.IconSize.MENU)
                row.pack_start(image, False, False, 0)
            label = Gtk.Label(label=title, xalign=0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(35)
            row.pack_start(label, True, True, 0)
            item.add(row)
            item.get_accessible().set_name(title)
            item.set_tooltip_text(title)
            return item

        def _programs_cascade(self, reveal_search):
            """One real .desktop category flyout for XP and Classic, no fake items."""
            groups = (
                ("Accessories", ("Utility", "Accessories", "TextEditor")),
                ("Games", ("Game",)),
                ("Graphics", ("Graphics", "Photography")),
                ("Internet", ("Network", "WebBrowser", "Email")),
                ("Multimedia", ("Audio", "Video", "Player")),
                ("Office", ("Office", "Spreadsheet", "WordProcessor")),
                ("System Tools", ("System", "Settings", "FileManager", "Terminal")),
            )
            programs_menu = self._track_start_popup(Gtk.Menu())
            if profile == "winxp":
                program_groups = luna_program_groups(self.apps)
            else:
                program_groups = []
                for title, categories in groups:
                    members = []
                    for app in self.apps:
                        classifier = getattr(app, "get_categories", None)
                        names = (classifier() or "").split(";") if callable(classifier) else ()
                        if any(category in names for category in categories):
                            members.append(app)
                        if len(members) >= 20:
                            break
                    if members:
                        program_groups.append((title, None, members))
            for title, icon, members in program_groups:
                submenu = self._track_start_popup(Gtk.Menu())
                for app in members:
                    name = app.get_display_name() or app.get_name()
                    item = (self._luna_menu_item(name, app.get_icon() or "applications-other")
                            if profile == "winxp" else Gtk.MenuItem(label=name))
                    item.connect("activate", lambda _item, selected=app: self._launch(selected))
                    submenu.append(item)
                parent = (self._luna_menu_item(title, icon) if profile == "winxp" else
                          Gtk.MenuItem(label=title))
                parent.set_submenu(submenu)
                programs_menu.append(parent)
            if programs_menu.get_children():
                programs_menu.append(Gtk.SeparatorMenuItem())
            all_item = (self._luna_menu_item("Search all installed programs…", "system-search")
                        if profile == "winxp" else
                        Gtk.MenuItem(label="Search all installed programs…"))
            all_item.connect("activate", lambda *_args: reveal_search())
            programs_menu.append(all_item)
            programs_menu.show_all()
            return programs_menu

        def _luna_navigation(self, label, icon_name, *, path=None, command=None, callback=None):
            """XP right-column link; never enable unavailable system operations."""
            button = self._class(Gtk.Button(), "luna-place")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            row.pack_start(self._icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
            row.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
            button.add(row)
            button.get_accessible().set_name(label)
            if path is not None:
                button.set_sensitive(path.is_dir())
                button.set_tooltip_text("Open " + str(path) if path.is_dir() else
                                        "Folder not available: " + str(path))
                button.connect("clicked", lambda _button: self._open_uri(path.as_uri()))
                if path.is_dir() and path != Path("/"):
                    from .riceware.dnd_gtk import attach_folder_drop

                    attach_folder_drop(button, path, Gtk, Gdk, GLib)
            elif command is not None:
                candidates = (command,) if isinstance(command, str) else command
                installed = next((name for name in candidates if shutil.which(name)), None)
                button.set_sensitive(installed is not None)
                button.set_tooltip_text("Open " + label if installed else
                                        "Requires " + " or ".join(candidates))
                if installed:
                    button.connect("clicked", lambda _button, executable=installed:
                                   self._open_tool(executable))
            elif callback is not None:
                button.connect("clicked", lambda _button: callback())
            return button

        def _open_luna_user_folder(self, folder):
            """Offer to create a missing XDG folder, never silently make files."""
            if folder.is_dir():
                self._open_uri(folder.as_uri())
                return
            dialog = Gtk.MessageDialog(
                transient_for=self.menu, modal=True, message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Create {folder.name} folder?")
            dialog.format_secondary_text(
                f"The folder {folder} does not exist. Create it and open it?")
            try:
                if dialog.run() != Gtk.ResponseType.YES:
                    return
            finally:
                dialog.destroy()
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                self._error(f"Cannot create {folder}: {exc}")
                return
            self._open_uri(folder.as_uri())

        def _luna_recent_documents(self):
            """Real XDG recent files, only when GTK knows about them."""
            button = self._class(Gtk.MenuButton(), "luna-place")
            button.get_accessible().set_name("Recent documents")
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            content.pack_start(self._icon("document-open-recent", Gtk.IconSize.LARGE_TOOLBAR),
                               False, False, 0)
            content.pack_start(Gtk.Label(label="My Recent Documents", xalign=0),
                               True, True, 0)
            content.pack_end(Gtk.Label(label="▸"), False, False, 0)
            button.add(content)
            button.set_direction(Gtk.ArrowType.RIGHT)
            menu = self._track_start_popup(Gtk.Menu())
            self.luna_recent_popup = menu
            try:
                items = (item for item in Gtk.RecentManager.get_default().get_items()
                         if item.exists() and item.get_uri().startswith("file:"))
                for item in sorted(items, key=lambda entry: entry.get_modified(),
                                   reverse=True)[:10]:
                    entry = self._luna_menu_item(item.get_display_name(), "text-x-generic")
                    entry.connect("activate", lambda _entry, uri=item.get_uri():
                                  self._open_uri(uri))
                    menu.append(entry)
            except (GLib.Error, OSError) as exc:
                logging.getLogger(__name__).debug("Recent documents unavailable: %s", exc)
            if not menu.get_children():
                entry = self._luna_menu_item("No recent documents", "document-open-recent")
                entry.set_sensitive(False)
                menu.append(entry)
            menu.show_all()
            button.set_popup(menu)
            return button

        def _reveal_luna_search(self):
            self.search.set_no_show_all(False)
            self.search.show()
            self.search.grab_focus()

        def _create_luna_menu(self):
            """XP Luna: blue user band, ivory apps list, blue places and power footer."""
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl XP Luna Start")
            menu.set_decorated(False)
            # GTK's natural height may exceed the requested menu height.
            # Keep the scrollable app list shrinkable and the window movable.
            menu.set_resizable(True)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            menu.set_default_size(480, 540)

            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                               "luna-menu")
            header = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10),
                                 "luna-user")
            avatar = self._class(Gtk.Image(), "luna-avatar")
            try:
                avatar.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(project_root() / "assets/ricebowl-xp-user.svg"), 44, 44, True))
            except (GLib.Error, OSError):
                avatar.set_from_icon_name("computer", Gtk.IconSize.DIALOG)
            header.pack_start(avatar, False, False, 0)
            user_label = self._class(
                Gtk.Label(label=os.environ.get("USER", "Desktop"), xalign=0),
                "luna-user-name")
            header.pack_start(user_label, True, True, 0)
            root.pack_start(header, False, False, 0)

            columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            apps = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2),
                               "luna-apps")
            apps.set_size_request(247, -1)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search programs")
            search.get_accessible().set_name("Search installed programs")
            search.set_no_show_all(True)
            apps.pack_start(search, False, False, 2)
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.set_min_content_height(140)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            scroll.add(self.results)
            apps.pack_start(scroll, True, True, 0)
            browse = self._class(Gtk.Button(label="All Programs  ▸"), "luna-all-programs")
            self.luna_programs_popup = self._programs_cascade(self._reveal_luna_search)
            self.luna_programs_popup.attach_to_widget(browse, None)
            browse.connect("clicked", lambda widget: self.luna_programs_popup.popup_at_widget(
                widget, Gdk.Gravity.SOUTH_EAST, Gdk.Gravity.SOUTH_WEST, None))
            self.luna_browse = browse
            browse.get_accessible().set_name("Browse all installed programs")
            apps.pack_end(browse, False, False, 3)
            columns.pack_start(apps, True, True, 0)

            places = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                                 "luna-places")
            places.set_size_request(205, -1)
            home = Path.home()
            for name, icon, kind, fallback in (
                ("My Documents", "folder-documents", GLib.UserDirectory.DIRECTORY_DOCUMENTS, "Documents"),
                ("My Pictures", "folder-pictures", GLib.UserDirectory.DIRECTORY_PICTURES, "Pictures"),
                ("My Music", "folder-music", GLib.UserDirectory.DIRECTORY_MUSIC, "Music"),
            ):
                folder = Path(GLib.get_user_special_dir(kind) or home / fallback)
                button = self._luna_navigation(
                    name, icon, callback=lambda target=folder: self._open_luna_user_folder(target))
                button.set_tooltip_text("Open " + str(folder) if folder.is_dir() else
                                        "Create and open " + str(folder) + " (with confirmation)")
                places.pack_start(button, False, False, 0)
            places.pack_start(self._luna_navigation("My Computer", "computer", path=Path("/")),
                              False, False, 0)
            places.pack_start(self._luna_recent_documents(), False, False, 0)
            places.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
            places.pack_start(self._luna_navigation(
                "Control Panel", "preferences-system", callback=self._toggle_actions),
                False, False, 0)
            for name, icon, cmd in (
                ("Network Connections", "network-workgroup", "nm-connection-editor"),
                ("Printers and Faxes", "printer", "system-config-printer"),
            ):
                places.pack_start(self._luna_navigation(name, icon, command=cmd), False, False, 0)
            places.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
            places.pack_start(self._luna_navigation("Help and Support", "help-browser",
                                                     callback=self._luna_open_help), False, False, 0)
            places.pack_start(self._luna_navigation("Search", "system-search",
                                                     command="catfish" if shutil.which("catfish") else None,
                                                     callback=self._reveal_luna_search), False, False, 0)
            self.luna_run_link = self._luna_navigation(
                "Run…", "system-run", callback=self._luna_open_run)
            places.pack_start(self.luna_run_link, False, False, 0)
            place_scroll = Gtk.ScrolledWindow()
            place_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            place_scroll.set_min_content_height(120)
            place_scroll.set_min_content_width(205)
            place_scroll.add(places)
            columns.pack_start(place_scroll, False, False, 0)
            root.pack_start(columns, True, True, 0)

            footer = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                                 "luna-footer")
            footer.pack_start(Gtk.Box(), True, True, 0)
            for name, icon, css in (("Log Off", "system-log-out", "luna-logoff"),
                                    ("Turn Off Computer", "system-shutdown", "luna-shutdown")):
                button = self._class(Gtk.Button(label=name), "luna-power")
                button.get_style_context().add_class(css)
                button.set_image(self._icon(icon, Gtk.IconSize.MENU))
                button.set_always_show_image(True)
                button.set_tooltip_text("Open XFCE session dialog; no immediate logout")
                button.set_sensitive(shutil.which("xfce4-session-logout") is not None)
                button.connect("clicked", lambda _button:
                               self._open_tool("xfce4-session-logout"))
                footer.pack_start(button, False, False, 0)
            root.pack_end(footer, False, False, 0)
            self.luna_footer = footer
            menu.add(root)
            self._finish_heritage_menu(menu, search)

        def _create_classic_menu(self):
            """Native Windows 98 Start with dynamic Gio/XDG descendants."""
            from .classic98_menu import build

            build(self, Gtk, Gdk, Gio, GLib, Pango)

        def _reveal_classic_search(self):
            self.classic_search.set_no_show_all(False)
            self.classic_results_scroll.set_no_show_all(False)
            self.classic_search.show()
            self.classic_results_scroll.show_all()
            self.classic_search.grab_focus()
            GLib.idle_add(self._reanchor_luna_menu)

        def _create_frutiger_menu(self):
            """The real Aqua World launcher: nature, refractive glass and live apps."""
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl Frutiger Aero — Your World")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            menu.get_style_context().add_class("aqua-window")
            rect = self._desktop_rect()
            _x, _y, width, height = menu_geometry(
                rect.x, rect.y, rect.width, rect.height,
                preferred_width=600, preferred_height=600)
            menu.set_default_size(width, height)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6),
                               "aqua-dashboard")
            root.get_style_context().add_class("aero-menu-root")
            # CSS padding is painted. GTK border-width exposes an ugly opaque
            # rectangular margin around rounded Aqua surfaces.
            root.set_border_width(0)
            heading = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11),
                                  "aqua-hero")
            logo = project_root() / "assets/ricebowl-frutiger-start.svg"
            try:
                mark = Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(str(logo), 49, 49, True))
            except (GLib.Error, OSError):
                mark = self._icon("start-here", Gtk.IconSize.DIALOG)
            heading.pack_start(self._class(mark, "aqua-hero-orb"), False, False, 0)
            titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            titles.pack_start(self._class(
                Gtk.Label(label="Your World", xalign=0), "aero-menu-heading"),
                False, False, 0)
            titles.pack_start(self._class(
                Gtk.Label(label="Explore  •  Connect  •  Create", xalign=0),
                "aero-menu-sub"), False, False, 0)
            self.frutiger_status_label = self._class(Gtk.Label(
                label=frutiger_status_summary(self._last_status), xalign=0),
                "aqua-status-caption")
            self.frutiger_status_label.set_ellipsize(Pango.EllipsizeMode.END)
            self.frutiger_status_label.set_tooltip_text("Live desktop status")
            titles.pack_start(self.frutiger_status_label, False, False, 0)
            heading.pack_start(titles, True, True, 0)
            gear = self._class(Gtk.Button(), "aqua-gear")
            gear.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
            gear.get_accessible().set_name("Open desktop settings")
            gear.set_tooltip_text("Open Aqua Control Center")
            gear.connect("clicked", lambda _button:
                         self._show_aqua_control())
            heading.pack_end(gear, False, False, 0)
            root.pack_start(heading, False, False, 0)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search your applications")
            search.get_accessible().set_name("Search applications")
            root.pack_start(search, False, False, 0)
            shortcuts = self._class(Gtk.Grid(column_spacing=8, row_spacing=6),
                                    "aqua-shortcuts")
            shortcuts.set_column_homogeneous(True)
            def xdg_path(kind, fallback):
                location = GLib.get_user_special_dir(kind)
                return Path(location) if location else Path.home() / fallback

            documents = xdg_path(GLib.UserDirectory.DIRECTORY_DOCUMENTS, "Documents")
            music = xdg_path(GLib.UserDirectory.DIRECTORY_MUSIC, "Music")
            for i, (name, icon_name, target) in enumerate((
                ("Home", "user-home", Path.home()),
                ("Files", "system-file-manager", Path("/")),
                ("Documents", "folder-documents", documents),
                ("Music", "folder-music", music),
            )):
                button = self._class(Gtk.Button(), "aqua-shortcut")
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                col.pack_start(self._icon(icon_name, Gtk.IconSize.DIALOG),
                               False, False, 0)
                col.pack_start(Gtk.Label(label=name), False, False, 0)
                button.add(col)
                button.get_accessible().set_name("Open " + name)
                button.set_tooltip_text("Open " + str(target) if target.is_dir() else
                                        "Create and open " + str(target) + " (with confirmation)")
                button.connect("clicked", lambda _button, folder=target:
                               self._open_luna_user_folder(folder))
                if target.is_dir() and target != Path("/"):
                    from .riceware.dnd_gtk import attach_folder_drop

                    attach_folder_drop(button, target, Gtk, Gdk, GLib)
                shortcuts.attach(button, i, 0, 1, 1)
            root.pack_start(shortcuts, False, False, 0)
            # Three live pages mirror the reference: Apps / Places / Settings.
            tabs = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7),
                               "aqua-tabs")
            self.aqua_stack = Gtk.Stack()
            self.aqua_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            self.aqua_stack.set_transition_duration(140)
            # Nine settings rows have a greater natural height than the app
            # grid. GTK's homogeneous default otherwise expands the fixed
            # 600px launcher and can make navigation effectively inaccessible.
            self.aqua_stack.set_vhomogeneous(False)
            buttons = {}
            for name in ("Apps", "Places", "Settings"):
                button = self._class(Gtk.ToggleButton(label=name), "aqua-tab")
                button.set_hexpand(True)
                button.get_accessible().set_name("Show " + name + " page")
                tabs.pack_start(button, True, True, 0)
                buttons[name] = button
            root.pack_start(tabs, False, False, 0)
            section = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8),
                                  "aqua-section")
            section_title = self._class(Gtk.Label(label="DISCOVER YOUR APPS", xalign=0),
                                        "aqua-section-title")
            section_hint = self._class(Gtk.Label(label="Right-click to pin", xalign=1),
                                       "aqua-section-hint")
            section.pack_start(section_title, True, True, 0)
            section.pack_end(section_hint, False, False, 0)
            section.set_no_show_all(True)
            root.pack_start(section, False, False, 0)
            # Keep exits from the taller Settings page *outside* its scroll
            # container. Long lists and a remembered scroll offset must never
            # hide the only back navigation.
            settings_navigation = self._class(
                Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8),
                "aqua-settings-navigation")
            return_to_apps = self._class(Gtk.Button(label="‹ All apps"), "aqua-settings-back")
            self._frutiger_back_to_apps = return_to_apps
            return_to_apps.set_tooltip_text("Return to applications")
            return_to_apps.get_accessible().set_name("Back to all applications")
            return_to_apps.connect("clicked", lambda _button: switch_to("Apps"))
            settings_navigation.pack_start(return_to_apps, True, True, 0)
            back_to_places = self._class(Gtk.Button(label="Places ›"), "aqua-settings-back")
            self._frutiger_back_to_places = back_to_places
            back_to_places.set_tooltip_text("Browse your places and mounted drives")
            back_to_places.get_accessible().set_name("Open places")
            back_to_places.connect("clicked", lambda _button: switch_to("Places"))
            settings_navigation.pack_end(back_to_places, True, True, 0)
            # The navigation container is excluded from the launcher's later
            # show_all() pass (no_show_all keeps it hidden outside Settings).
            # Realize its two children now so showing the container later
            # exposes clickable buttons, not an empty/childless GTK region.
            settings_navigation.show_all()
            settings_navigation.set_no_show_all(True)
            root.pack_start(settings_navigation, False, False, 0)
            # Gtk.ToggleButton.set_active() can emit "clicked" in GTK3.
            # The guarded switcher prevents cross-tab recursive re-entry.
            switch_to = frutiger_tab_switcher(
                self.aqua_stack, buttons, section, search, settings_navigation)
            self._frutiger_switch_to = switch_to
            self._frutiger_tab_buttons = buttons
            for name, button in buttons.items():
                button.connect("clicked", lambda _button, chosen=name: switch_to(chosen))

            apps_scroll = Gtk.ScrolledWindow()
            apps_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            apps_scroll.set_min_content_height(135)
            self.results = self._class(Gtk.FlowBox(), "aqua-app-grid")
            self.results.set_selection_mode(Gtk.SelectionMode.NONE)
            self.results.set_min_children_per_line(2)
            self.results.set_max_children_per_line(3)
            self.results.set_column_spacing(9)
            self.results.set_row_spacing(9)
            self.results.set_homogeneous(True)
            apps_scroll.add(self.results)
            self.aqua_stack.add_named(apps_scroll, "Apps")

            places_page = Gtk.ScrolledWindow()
            places_page.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            places_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            places_grid = Gtk.Grid(column_spacing=9, row_spacing=8)
            places_grid.set_margin_top(7)
            places_grid.set_margin_bottom(7)
            home = Path.home()
            entries = (
                ("Home", "user-home", home),
                ("Documents", "folder-documents", documents),
                ("Downloads", "folder-download", xdg_path(GLib.UserDirectory.DIRECTORY_DOWNLOAD, "Downloads")),
                ("Music", "folder-music", music),
                ("Pictures", "folder-pictures", xdg_path(GLib.UserDirectory.DIRECTORY_PICTURES, "Pictures")),
                ("Videos", "folder-videos", xdg_path(GLib.UserDirectory.DIRECTORY_VIDEOS, "Videos")),
                ("Desktop", "user-desktop", xdg_path(GLib.UserDirectory.DIRECTORY_DESKTOP, "Desktop")),
                ("File system", "drive-harddisk", Path("/")),
            )
            for index, (title, icon_name, path) in enumerate(entries):
                button = self._place_button(title, icon_name, path, "aqua-place", offer_create=True)
                places_grid.attach(button, index % 2, index // 2, 1, 1)
            places_content.pack_start(places_grid, False, False, 0)
            trash = self._class(Gtk.Button(), "aqua-place")
            trash_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            trash_line.pack_start(self._icon("user-trash", Gtk.IconSize.MENU), False, False, 0)
            trash_line.pack_start(Gtk.Label(label="Trash", xalign=0), True, True, 0)
            trash.add(trash_line)
            trash.get_accessible().set_name("Open Trash")
            trash.set_tooltip_text("Open the real desktop Trash folder")
            trash.connect("clicked", lambda _button: self._open_uri("trash:///"))
            places_content.pack_start(trash, False, False, 0)
            places_content.pack_start(self._class(Gtk.Label(label="CONNECTED LOCATIONS", xalign=0),
                                                  "aqua-section-title"), False, False, 3)
            mounts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            places_content.pack_start(mounts_box, False, False, 0)
            monitor = Gio.VolumeMonitor.get()

            def refresh_mounts(*_args):
                for old in tuple(mounts_box.get_children()):
                    mounts_box.remove(old)
                visible = []
                for mount in monitor.get_mounts():
                    try:
                        if mount.is_shadowed():
                            continue
                        uri = mount.get_default_location().get_uri()
                        if uri in ("file:///", "file:///boot"):
                            continue
                        visible.append((mount.get_name(), uri))
                    except (AttributeError, GLib.Error):
                        continue
                for title, uri in sorted(visible, key=lambda row: row[0].casefold()):
                    button = self._class(Gtk.Button(), "aqua-place")
                    line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
                    line.pack_start(self._icon("drive-removable-media", Gtk.IconSize.MENU),
                                    False, False, 0)
                    line.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
                    button.add(line)
                    button.get_accessible().set_name("Open mounted location " + title)
                    button.set_tooltip_text(uri)
                    button.connect("clicked", lambda _button, destination=uri:
                                   self._open_uri(destination))
                    mounts_box.pack_start(button, False, False, 0)
                if not visible:
                    mounts_box.pack_start(self._class(Gtk.Label(
                        label="No mounted removable or network locations", xalign=0),
                        "aqua-section-hint"), False, False, 0)
                mounts_box.show_all()

            refresh_mounts()
            for signal in ("mount-added", "mount-removed", "mount-changed"):
                monitor.connect(signal, refresh_mounts)
            places_page.add(places_content)
            self.aqua_stack.add_named(places_page, "Places")

            settings_page = Gtk.ScrolledWindow()
            settings_page.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            settings_page.set_min_content_height(135)
            settings_page.set_max_content_height(325)
            settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            for title, icon_name, category in (
                ("Connections", "network-wireless", "connections"),
                ("Sound & media", "audio-volume-high", "sound"),
                ("Personalize", "preferences-desktop-theme", "personalize"),
                ("Display & windows", "video-display", "display"),
                ("Power & battery", "battery", "power"),
                ("Devices & input", "input-keyboard", "devices"),
                ("Applications", "system-software-install", "applications"),
                ("System & recovery", "computer", "system"),
                ("Accessibility", "preferences-desktop-accessibility", "accessibility"),
            ):
                btn = self._class(Gtk.Button(), "aqua-place")
                content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
                content.pack_start(self._icon(icon_name, Gtk.IconSize.MENU), False, False, 0)
                content.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
                btn.add(content)
                btn.set_tooltip_text("Open Aqua Control Center · " + title)
                btn.connect("clicked", lambda _button, page=category:
                            self._show_aqua_control(page))
                settings_box.pack_start(btn, False, False, 0)
            settings_page.add(settings_box)
            self.aqua_stack.add_named(settings_page, "Settings")

            def reset_settings_scroll(_stack, _param):
                if self.aqua_stack.get_visible_child_name() == "Settings":
                    settings_page.get_vadjustment().set_value(0)

            self.aqua_stack.connect("notify::visible-child-name", reset_settings_scroll)

            root.pack_start(self.aqua_stack, True, True, 0)
            footer = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                                 "aqua-footer")
            footer.pack_start(self._class(Gtk.Label(label="RiceBowl  •  your desktop"),
                                          "aqua-caption"), True, True, 0)
            for icon_name, name in (("preferences-system", "Settings"),
                                    ("system-shutdown", "Power")):
                btn = self._class(Gtk.Button(), "aqua-footer-action")
                btn.set_image(self._icon(icon_name, Gtk.IconSize.MENU))
                btn.set_tooltip_text("Open " + name)
                btn.get_accessible().set_name("Open " + name)
                if name == "Settings":
                    btn.connect("clicked", lambda _button: self._show_aqua_control())
                else:
                    command = "xfce4-session-logout"
                    btn.set_sensitive(shutil.which(command) is not None)
                    btn.connect("clicked", lambda _button, app=command: self._open_tool(app))
                footer.pack_start(btn, False, False, 0)
            root.pack_start(footer, False, False, 0)
            switch_to("Apps")
            menu.add(root)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            def search_changed(*_args):
                self._app_page_size = 24
                searching = bool(search.get_text().strip())
                section_title.set_text("SEARCH YOUR WORLD" if searching else "DISCOVER YOUR APPS")
                section_hint.set_text("Apps · Places · Settings" if searching else
                                      "Right-click to pin")
                if search.get_text().strip():
                    switch_to("Apps")
                self._populate(search.get_text())
            search.connect("search-changed", search_changed)
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu, self.search = menu, search
            self._populate("")

        def _open_ten_settings(self, page="home"):
            """Open the independent Windows 10 Settings renderer, not XFCE Manager."""
            if profile != "windows10":
                return
            self._hide_menu()
            self._hide_actions()
            self.ten_network.hide()
            if not hasattr(self, "ten_settings"):
                from .ten_settings import TenSettings

                self.ten_settings = TenSettings(self, Gtk, Gdk, GLib,
                                                self.ten_controller.runner)
            self.ten_settings.show(page)

        def _toggle_ten_network(self):
            if profile != "windows10":
                return
            if self.ten_network.window.get_visible():
                self.ten_network.hide()
                return
            self._hide_menu()
            self._hide_actions()
            if hasattr(self, "ten_task_view"):
                self.ten_task_view.hide()
            self.ten_network.show()

        def _toggle_ten_task_view(self):
            if profile != "windows10":
                return
            if not hasattr(self, "ten_task_view"):
                from .ten_task_view import TenTaskView

                self.ten_task_view = TenTaskView(self, Gtk, Gdk, GLib)
            if self.ten_task_view.window.get_visible():
                self.ten_task_view.hide()
                return
            self._hide_menu()
            self._hide_actions()
            self.ten_network.hide()
            self.ten_task_view.show()

        def _open_ten_explorer(self):
            """Opt-in Rust renderer; never change Thunar/MIME defaults."""
            if profile != "windows10":
                return
            binary = shutil.which("rice-explorer")
            if not binary:
                self._error("RiceExplorer is not installed; Thunar remains available.")
                return
            try:
                subprocess.Popen((binary, "--theme", "win10", str(Path.home())),
                                 start_new_session=True)
            except OSError as exc:
                self._error("Could not start RiceExplorer: " + str(exc))
                return
            self._hide_menu()

        def _create_ten_menu(self):
            """Windows 10 Start: navigation rail, alphabetical apps, grouped live tiles."""
            if profile == "chromeos":
                self._create_chrome_launcher()
                return
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl Windows 10 Start")
            menu.set_decorated(False)
            menu.set_resizable(True)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _, _, menu_w, menu_h = menu_geometry(rect.x, rect.y, rect.width, rect.height,
                                                 preferred_width=690, preferred_height=560,
                                                 panel_height=panel_height)
            menu.set_default_size(menu_w, menu_h)
            def user_directory(kind, fallback):
                location = GLib.get_user_special_dir(kind)
                return Path(location) if location else Path.home() / fallback

            home = Path.home()
            documents = user_directory(GLib.UserDirectory.DIRECTORY_DOCUMENTS, "Documents")
            downloads = user_directory(GLib.UserDirectory.DIRECTORY_DOWNLOAD, "Downloads")
            pictures = user_directory(GLib.UserDirectory.DIRECTORY_PICTURES, "Pictures")
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "aero-menu-root")
            rail = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2), "ten-rail")
            rail.set_size_request(49, -1)

            navigation = self._class(Gtk.MenuButton(label="☰"), "ten-rail-button")
            navigation.get_accessible().set_name("Open Start navigation")
            navigation.set_tooltip_text("Start navigation")
            navigation_menu = Gtk.Menu()
            for label, uri, commands in (
                ("Home", home.as_uri(), ()),
                ("Documents", documents.as_uri(), ()),
                ("Downloads", downloads.as_uri(), ()),
                ("Settings", "", ("xfce4-settings-manager",)),
                ("Sign out / Power", "", ("xfce4-session-logout",)),
            ):
                item = Gtk.MenuItem(label=label)
                if uri:
                    item.set_sensitive(Gio.File.new_for_uri(uri).query_exists(None))
                    item.connect("activate", lambda _item, location=uri: self._open_uri(location))
                else:
                    command = next((cmd for cmd in commands if shutil.which(cmd)), None)
                    if label == "Settings":
                        item.connect("activate", lambda _item: self._open_ten_settings())
                    else:
                        item.set_sensitive(command is not None)
                    if command and label != "Settings":
                        item.connect("activate", lambda _item, cmd=command: self._open_tool(cmd))
                navigation_menu.append(item)
            navigation_menu.show_all()
            navigation.set_popup(navigation_menu)
            rail.pack_start(navigation, False, False, 0)
            rail.pack_start(Gtk.Box(), True, True, 0)
            for text, icon, uri, command in (
                ("Your files", "user-home", home.as_uri(), ""),
                ("Documents", "folder-documents", documents.as_uri(), ""),
                ("Pictures", "folder-pictures", pictures.as_uri(), ""),
                ("Settings", "preferences-system", "", "xfce4-settings-manager"),
                ("Power", "system-shutdown", "", "xfce4-session-logout"),
            ):
                button = self._class(Gtk.Button(), "ten-rail-button")
                button.set_image(self._icon(icon, Gtk.IconSize.LARGE_TOOLBAR))
                button.set_tooltip_text(text)
                button.get_accessible().set_name(text)
                if command:
                    if text == "Settings":
                        button.connect("clicked", lambda _button: self._open_ten_settings())
                    else:
                        button.set_sensitive(shutil.which(command) is not None)
                        button.connect("clicked", lambda _button, cmd=command:
                                       self._open_tool(cmd))
                else:
                    button.set_sensitive(Gio.File.new_for_uri(uri).query_exists(None))
                    button.connect("clicked", lambda _button, location=uri: self._open_uri(location))
                rail.pack_start(button, False, False, 0)
            if shutil.which("rice-explorer"):
                explorer = self._class(Gtk.Button(), "ten-rail-button")
                explorer.set_image(self._icon("system-file-manager", Gtk.IconSize.LARGE_TOOLBAR))
                explorer.set_tooltip_text("RiceExplorer · Windows 10 (preview)")
                explorer.get_accessible().set_name("Open optional RiceExplorer Windows 10")
                explorer.connect("clicked", lambda _button: self._open_ten_explorer())
                rail.pack_start(explorer, False, False, 0)
            root.pack_start(rail, False, False, 0)

            main = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10), "ten-menu-main")
            main.pack_start(self._class(Gtk.Label(label="Start", xalign=0),
                                        "aero-menu-heading"), False, False, 0)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search installed apps")
            search.get_accessible().set_name("Search installed applications")
            main.pack_start(search, False, False, 0)

            columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            main.pack_start(columns, True, True, 0)
            apps_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            apps_column.set_size_request(238, -1)
            apps_column.pack_start(self._class(Gtk.Label(label="All apps", xalign=0),
                                               "ten-section-heading"),
                                   False, False, 0)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.results = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1),
                                       "ten-app-list")
            scroller.add(self.results)
            apps_column.pack_start(scroller, True, True, 0)
            columns.pack_start(apps_column, True, True, 0)

            self.ten_tiles_panel = self._class(
                Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10), "ten-tiles-panel")
            self.ten_tiles_panel.pack_start(
                self._class(Gtk.Label(label="Productivity", xalign=0), "ten-section-heading"),
                False, False, 0)
            self.tile_grid = Gtk.Grid(row_spacing=5, column_spacing=5)
            self.ten_tiles_panel.pack_start(self.tile_grid, False, False, 0)
            self.ten_tiles_panel.pack_start(
                self._class(Gtk.Label(label="Explore", xalign=0), "ten-section-heading"),
                False, False, 3)
            self.explore_grid = Gtk.Grid(row_spacing=5, column_spacing=5)
            self.ten_tiles_panel.pack_start(self.explore_grid, False, False, 0)
            columns.pack_start(self.ten_tiles_panel, False, False, 0)
            root.pack_start(main, True, True, 0)

            menu.add(root)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)

            def search_changed(*_args):
                self._app_page_size = 24
                query = search.get_text()
                self.ten_tiles_panel.set_visible(not bool(query.strip()))
                self._populate(query)
            search.connect("search-changed", search_changed)
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu, self.search = menu, search
            self._render_ten_tiles()
            self._populate("")

        def _open_chrome_settings(self, section=None, action=None):
            """Reuse one settings window, scoped exclusively to ChromeOS."""
            if profile != "chromeos":
                return
            if self._chrome_settings is None:
                from .chrome_settings import ChromeSettings
                self._chrome_settings = ChromeSettings(self, Gtk, Gdk, GLib)
            self._hide_menu()
            self._hide_actions()
            self._chrome_settings.present(section or (action.section if action else None))
            if action is not None:
                self._chrome_settings.show_detail(action)

        def _create_chrome_launcher(self):
            """Material You launcher with genuine Gio applications and real shelf pins."""
            from .chrome_shell import apply_rounded_window_shape
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl ChromeOS App Launcher")
            menu.set_decorated(False)
            menu.set_resizable(True)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _x, _y, menu_w, menu_h = menu_geometry(
                rect.x, rect.y, rect.width, rect.height,
                preferred_width=610, preferred_height=628, panel_height=panel_height)
            menu.set_default_size(menu_w, menu_h)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12),
                               "chrome-launcher")
            header = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                                 "chrome-launcher-header")
            try:
                emblem = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(project_root() / "assets/ricebowl-chrome-start.svg"), 29, 29, True))
            except (GLib.Error, OSError):
                emblem = self._icon("start-here", Gtk.IconSize.LARGE_TOOLBAR)
            header.pack_start(emblem, False, False, 0)
            header.pack_start(self._class(
                Gtk.Label(label="Launcher", xalign=0),
                "chrome-launcher-title"), True, True, 0)
            settings = self._class(Gtk.Button(), "chrome-launcher-settings")
            settings.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
            settings.set_tooltip_text("Open ChromeOS-inspired Settings")
            settings.get_accessible().set_name("Open ChromeOS-inspired Settings")
            settings.connect("clicked", lambda _button: self._open_chrome_settings())
            header.pack_end(settings, False, False, 0)
            root.pack_start(header, False, False, 0)

            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search your installed apps")
            search.get_accessible().set_name("Search all installed applications")
            root.pack_start(search, False, False, 0)

            pinned_label = self._class(
                Gtk.Label(label="Pinned", xalign=0), "chrome-section-heading")
            root.pack_start(pinned_label, False, False, 0)
            self.tile_grid = Gtk.Grid(row_spacing=4, column_spacing=7)
            self.tile_grid.set_halign(Gtk.Align.START)
            root.pack_start(self.tile_grid, False, False, 0)
            root.pack_start(self._class(
                Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                "chrome-divider"), False, False, 1)
            all_apps_label = self._class(
                Gtk.Label(label="All apps", xalign=0), "chrome-section-heading")
            root.pack_start(all_apps_label, False, False, 0)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_height(185)
            self.results = Gtk.Grid(row_spacing=5, column_spacing=7)
            self.results.set_halign(Gtk.Align.START)
            self.results.set_valign(Gtk.Align.START)
            scroller.add(self.results)
            root.pack_start(scroller, True, True, 0)
            root.pack_start(self._class(Gtk.Label(
                label="Right-click an app to pin or unpin it on the shelf",
                xalign=0), "chrome-quick-detail"), False, False, 0)
            menu.add(root)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            def shape_later(*_args):
                GLib.idle_add(apply_rounded_window_shape, menu, 26)
                return False
            menu.connect("configure-event", shape_later)
            def search_changed(*_args):
                self._app_page_size = 24
                needle = search.get_text().strip()
                self.tile_grid.set_visible(not bool(needle))
                pinned_label.set_visible(not bool(needle))
                all_apps_label.set_text("Search results" if needle else "All apps")
                self._populate(needle)
            search.connect("search-changed", search_changed)
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu, self.search = menu, search
            self._render_ten_tiles()
            self._populate("")

        def _chrome_app_button(self, app):
            """Uniform real Gio icons: never let intrinsic SVG sizes break the grid."""
            button = self._class(Gtk.Button(), "chrome-app-card")
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            icon = app.get_icon()
            picture = (Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG) if icon else
                       self._icon("applications-other", Gtk.IconSize.DIALOG))
            picture.set_pixel_size(44)
            picture.set_halign(Gtk.Align.CENTER)
            content.pack_start(picture, False, False, 0)
            title = app.get_display_name() or app.get_name() or "Application"
            name = self._class(Gtk.Label(label=title), "chrome-app-label")
            name.set_max_width_chars(14)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            content.pack_start(name, False, False, 0)
            button.add(content)
            button.set_size_request(125, 91)
            button.set_tooltip_text(title + " · Right-click to pin or unpin")
            button.get_accessible().set_name("Launch " + title)
            button.connect("clicked", lambda _button, selected=app: self._launch(selected))
            button.connect("button-press-event", lambda widget, event, selected=app:
                           self._pin_context(widget, selected, event))
            button.connect("popup-menu", lambda widget, selected=app:
                           self._pin_context(widget, selected))
            return button

        def _populate_chrome_apps(self, query):
            matches = matching_apps(self.apps, query)
            for index, app in enumerate(matches[:self._app_page_size]):
                self.results.attach(self._chrome_app_button(app),
                                    index % 4, index // 4, 1, 1)
            if not matches:
                self.results.attach(self._class(Gtk.Label(
                    label="No installed applications match your search", xalign=0),
                    "chrome-empty"), 0, 0, 4, 1)
            if len(matches) > self._app_page_size:
                more = self._class(Gtk.Button(label="Show more apps"), "chrome-app-card")
                more.get_accessible().set_name("Show more installed applications")
                def expand(_button):
                    self._app_page_size += 24
                    self._populate(self.search.get_text())
                more.connect("clicked", expand)
                more_row = (min(len(matches), self._app_page_size) + 3) // 4
                self.results.attach(more, 0, more_row, 4, 1)
            self.results.show_all()

        def _render_ten_tiles(self):
            if not hasattr(self, "tile_grid"):
                return
            if profile == "windows10":
                from .ten_shell import start_tiles

                for grid in (self.tile_grid, self.explore_grid):
                    for child in grid.get_children():
                        grid.remove(child)
                apps = start_tiles(self.apps, self._pinned_ids)
                for index, app in enumerate(apps):
                    grid = self.tile_grid if index < 4 else self.explore_grid
                    tile_index = index if index < 4 else index - 4
                    button = self._class(Gtk.Button(), "ten-tile")
                    if index in (1, 4):
                        button.get_style_context().add_class("ten-tile-alt")
                    if index == 0:
                        button.get_style_context().add_class("ten-tile-wide")
                    button.set_size_request(136, 95 if index == 0 else 81)
                    name = app.get_display_name() or app.get_name() or "Application"
                    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                    icon = app.get_icon()
                    picture = (Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG) if icon else
                               self._icon("applications-other", Gtk.IconSize.DIALOG))
                    picture.set_halign(Gtk.Align.CENTER)
                    content.pack_start(picture, True, True, 0)
                    caption = self._class(Gtk.Label(label=name, xalign=0), "ten-tile-label")
                    caption.set_max_width_chars(16)
                    caption.set_ellipsize(Pango.EllipsizeMode.END)
                    content.pack_end(caption, False, False, 0)
                    button.add(content)
                    button.get_accessible().set_name("Launch " + name)
                    button.set_tooltip_text(name + " · Right-click to pin or unpin")
                    button.connect("clicked", lambda _button, selected=app: self._launch(selected))
                    button.connect("button-press-event", lambda widget, event, selected=app:
                                   self._pin_context(widget, selected, event))
                    button.connect("popup-menu", lambda widget, selected=app:
                                   self._pin_context(widget, selected))
                    grid.attach(button, tile_index % 2, tile_index // 2, 1, 1)
                if not apps:
                    self.tile_grid.attach(self._class(
                        Gtk.Label(label="No desktop applications installed", xalign=0),
                        "ten-muted"), 0, 0, 2, 1)
                self.tile_grid.show_all()
                self.explore_grid.show_all()
                return
            for child in self.tile_grid.get_children():
                self.tile_grid.remove(child)
            if profile == "chromeos":
                from .chrome_shell import launcher_favorites
                for index, app in enumerate(
                        launcher_favorites(self.apps, self._pinned_ids)):
                    self.tile_grid.attach(self._chrome_app_button(app), index, 0, 1, 1)
                self.tile_grid.show_all()
                return

        def _create_actions(self):
            """Profile-aware controls; never simulate state-changing toggles."""
            if profile == "frutiger":
                from .frutiger_control_center import build

                self.actions = build(self, Gtk, Gdk)
                return
            if profile == "aero":
                from .win7_control_panel import build

                self.actions = build(self, Gtk, Gdk)
                return
            if profile == "winxp":
                from .luna_control_panel import build

                self.actions = build(self, Gtk, Gdk)
                return
            if ten:
                from .ten_action_center import build

                self.actions = build(self, Gtk, Gdk)
                return
            if profile == "chromeos":
                from .chrome_quick_settings import build

                self.actions = build(self, Gtk, Gdk, GLib)
                return
            if profile == "winclassic":
                from .classic98_control_panel import build as build_control_panel
                from .classic98_tray import build as build_tray

                self.actions = build_control_panel(self, Gtk, Gdk)
                build_tray(self, Gtk, Gdk)
                return
            actions = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            heading = heritage.control_heading if heritage else ("Action Center" if ten else "Control Panel")
            actions.set_title("RiceBowl " + heading)
            actions.set_decorated(False)
            # GtkScrolledWindow has no useful implicit minimum height.
            # A non-resizable utility window collapses to its first header,
            # making the controls look like a clipped title strip.
            actions.set_resizable(True)
            rect = self._desktop_rect()
            actions.set_default_size(
                382 if profile == "winclassic" else 388 if profile == "frutiger" else
                412 if profile == "aero" else 330,
                min(action_heights.get(profile, 430), rect.height - panel_height - 16))
            actions.set_skip_taskbar_hint(True)
            actions.set_skip_pager_hint(True)
            actions.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            actions.set_transient_for(self.bar)
            actions.set_keep_above(True)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10),
                               "ten-action-root" if tiles else "aero-control-root")
            if profile == "frutiger":
                root.get_style_context().add_class("aqua-control-root")
            root.set_size_request(300, 265)

            if profile == "winclassic":
                # Controls remain a real resizable GTK popup, with an original
                # Win98-style caption instead of a modern card heading.
                caption = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                               spacing=6), "classic-control-caption")
                caption.pack_start(self._icon("classic-control-panel", Gtk.IconSize.MENU),
                                   False, False, 2)
                caption.pack_start(Gtk.Label(label=heading, xalign=0), True, True, 0)
                close = self._class(Gtk.Button(label="×"), "classic-control-close")
                close.get_accessible().set_name("Close Control Panel")
                close.connect("clicked", lambda _button: self._hide_actions())
                caption.pack_end(close, False, False, 0)
                root.pack_start(caption, False, False, 0)
            else:
                title = self._class(Gtk.Label(label=heading, xalign=0), "aero-menu-heading")
                if profile == "frutiger":
                    hero = self._class(
                        Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                        "aqua-control-hero")
                    hero.pack_start(self._icon("preferences-system", Gtk.IconSize.DIALOG),
                                    False, False, 0)
                    hero.pack_start(title, True, True, 0)
                    root.pack_start(hero, False, False, 0)
                else:
                    root.pack_start(title, False, False, 0)
            descriptions = {
                "winxp": "Pick a category to configure your computer",
                "winclassic": "Configure Linux desktop settings",
                "chromeos": "Device controls and preferences",
                "frutiger": "Your connected desktop",
                "aero": "Adjust your computer's settings",
                "windows10": "Quick actions and system settings",
            }
            subtitle = self._class(Gtk.Label(label=descriptions.get(profile, ""), xalign=0),
                                   "aero-menu-sub")
            subtitle.set_line_wrap(True)
            root.pack_start(subtitle, False, False, 0)

            if profile == "chromeos":
                sections = (
                    ("Connectivity", (("Wi-Fi & network", "network-wireless", "nm-connection-editor"),
                                      ("Bluetooth", "bluetooth", "blueman-manager"))),
                    ("Device", (("Audio", "audio-volume-high", "pavucontrol"),
                                ("Display", "video-display", "xfce4-display-settings"),
                                ("Preferences", "preferences-system", "xfce4-settings-manager"))),
                )
            elif profile == "winxp":
                sections = (
                    ("Pick a category", (("Network and Internet", "network-workgroup", "nm-connection-editor"),
                                         ("Sounds and Audio", "audio-card", "pavucontrol"),
                                         ("Appearance and Themes", "preferences-desktop-theme", "xfce4-appearance-settings"),
                                         ("Printers and Hardware", "printer", "system-config-printer"))),
                    ("Other settings", (("Control Panel", "preferences-system", "xfce4-settings-manager"),)),
                )
            elif profile == "winclassic":
                sections = (
                    ("Choose an item", (("Display", "video-display", "xfce4-display-settings"),
                                        ("Multimedia", "audio-card", "pavucontrol"),
                                        ("Network", "network-workgroup", "nm-connection-editor"),
                                        ("System", "computer", "xfce4-settings-manager"),
                                        ("Mouse", "input-mouse", "xfce4-mouse-settings"),
                                        ("Keyboard", "input-keyboard", "xfce4-keyboard-settings"),
                                        ("Appearance", "preferences-desktop-theme", "xfce4-appearance-settings"),
                                        ("Power", "battery", "xfce4-power-manager-settings"))),
                )
            elif profile == "frutiger":
                sections = (
                    ("Connections", (("Network", "network-wireless", "nm-connection-editor"),
                                      ("Bluetooth", "bluetooth", "blueman-manager"))),
                    ("Personalize", (("Appearance", "preferences-desktop-theme", "xfce4-appearance-settings"),
                                     ("Sound", "audio-volume-high", "pavucontrol"),
                                     ("Display", "video-display", "xfce4-display-settings"))),
                )
            else:
                sections = (
                    ("Quick settings" if tiles else "Control Panel items" if profile == "aero" else "System tools",
                     (("Network", "network-wireless", "nm-connection-editor"),
                      ("Sound", "audio-volume-high", "pavucontrol"),
                      ("Display", "video-display", "xfce4-display-settings"),
                      ("Settings", "preferences-system", "xfce4-settings-manager"))),
                )

            category_buttons = []
            if profile == "aero":
                search = self._class(Gtk.SearchEntry(), "win7-control-search")
                search.set_placeholder_text("Search Control Panel")
                search.get_accessible().set_name("Search Control Panel settings")
                root.pack_start(search, False, False, 0)
            for section_title, entries in sections:
                section = self._class(Gtk.Label(label=section_title, xalign=0), "aero-menu-sub")
                root.pack_start(section, False, False, 0)
                grid = Gtk.Grid(row_spacing=5, column_spacing=5)
                if profile == "winclassic":
                    grid.get_style_context().add_class("classic-control-grid")
                for index, (label, icon_name, command) in enumerate(entries):
                    button = self._class(Gtk.Button(), "ten-quick" if tiles else "aero-control-quick")
                    classic_icon = profile == "winclassic"
                    contents = Gtk.Box(
                        orientation=(Gtk.Orientation.VERTICAL if classic_icon else
                                     Gtk.Orientation.HORIZONTAL), spacing=5 if classic_icon else 7)
                    contents.pack_start(
                        self._icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR if classic_icon else
                                   Gtk.IconSize.MENU), False, False, 0)
                    caption = Gtk.Label(label=label, xalign=0.5 if classic_icon else 0)
                    caption.set_line_wrap(True)
                    caption.set_max_width_chars(
                        12 if classic_icon else 27 if profile == "winxp" else 20)
                    if classic_icon:
                        caption.set_justify(Gtk.Justification.CENTER)
                        button.set_hexpand(True)
                    contents.pack_start(caption, True, True, 0)
                    button.add(contents)
                    button.set_tooltip_text("Open " + label if shutil.which(command) else
                                            label + " is not installed")
                    button.get_accessible().set_name("Open " + label)
                    button.set_sensitive(shutil.which(command) is not None)
                    button.connect("clicked", lambda _button, cmd=command: self._open_tool(cmd))
                    if profile == "aero":
                        category_buttons.append((label, button))
                    # XP category names are full-length navigation entries, not
                    # tiny quick-action tiles: a two-column layout overflows 330px.
                    if profile == "winxp":
                        grid.attach(button, 0, index, 1, 1)
                    elif profile == "winclassic":
                        grid.attach(button, index % 3, index // 3, 1, 1)
                    else:
                        grid.attach(button, index % 2, index // 2, 1, 1)
                root.pack_start(grid, False, False, 0)
            if profile == "aero":
                empty_settings = self._class(Gtk.Label(label="No matching settings", xalign=0),
                                             "aero-menu-sub")
                empty_settings.set_no_show_all(True)
                root.pack_start(empty_settings, False, False, 0)

                def filter_settings(entry):
                    needle = entry.get_text().casefold().strip()
                    for label, button in category_buttons:
                        button.set_visible(needle in label.casefold())
                    empty_settings.set_visible(not any(button.get_visible()
                                                       for _, button in category_buttons))

                search.connect("search-changed", filter_settings)

            # Actual hardware information and a VERIFIED volume slider make
            # this a usable control panel rather than decorative quick tiles.
            hardware = self._class(
                Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7),
                "rice-hardware-panel")
            hardware.pack_start(self._class(
                Gtk.Label(label="Live device status" if profile == "frutiger" else
                          "Device status", xalign=0), "aero-menu-sub"),
                False, False, 0)
            self.control_network_label = self._class(
                Gtk.Label(label="Network: reading…", xalign=0),
                "rice-control-detail")
            self.control_network_label.set_line_wrap(True)
            hardware.pack_start(self.control_network_label, False, False, 0)
            self.control_battery_label = self._class(
                Gtk.Label(label="Battery: reading…", xalign=0),
                "rice-control-detail")
            hardware.pack_start(self.control_battery_label, False, False, 0)
            self.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
            self.control_battery_level.set_value(0)
            self.control_battery_level.set_no_show_all(True)
            hardware.pack_start(self.control_battery_level, False, False, 0)
            self.volume_status_label = self._class(
                Gtk.Label(label="Volume: reading…", xalign=0),
                "rice-control-detail")
            hardware.pack_start(self.volume_status_label, False, False, 0)
            self.volume_scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, 0, 100, 5)
            self.volume_scale.set_draw_value(False)
            self.volume_scale.set_sensitive(False)
            self.volume_scale.get_accessible().set_name("System output volume")
            self.volume_scale.set_tooltip_text(
                "Adjust actual PipeWire/PulseAudio output volume, verified after changing")
            self.volume_scale.connect("value-changed", self._queue_volume_change)
            hardware.pack_start(self.volume_scale, False, False, 0)
            self.mute_button = self._class(
                Gtk.ToggleButton(label="Mute output"), "rice-mute")
            self.mute_button.set_sensitive(False)
            self.mute_button.get_accessible().set_name("Mute or unmute output")
            self.mute_button.connect("clicked", self._toggle_output_mute)
            hardware.pack_start(self.mute_button, False, False, 0)
            root.pack_end(hardware, False, False, 4)

            self.status_summary = self._class(
                Gtk.Label(label="Reading hardware status…", xalign=0),
                "rice-status-summary")
            self.status_summary.set_line_wrap(True)
            root.pack_end(self.status_summary, False, False, 2)
            actions_scroll = Gtk.ScrolledWindow()
            actions_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            actions_scroll.set_min_content_width(300)
            actions_scroll.set_min_content_height(260)
            actions_scroll.add(root)
            actions.add(actions_scroll)
            actions.connect("focus-out-event", lambda *_args: self._schedule_popup_hide("control"))
            actions.connect("key-press-event", lambda _widget, event: self._action_key(event))
            self.actions = actions

        def _action_key(self, event):
            if event.keyval == Gdk.KEY_Escape:
                if (profile == "chromeos" and hasattr(self, "chrome_quick_stack")
                        and self.chrome_quick_stack.get_visible_child_name() != "overview"):
                    self.chrome_quick_show_home()
                    return True
                self._hide_actions()
                return True
            return False

        def _cancel_popup_hide(self, name):
            source = self._popup_hide_sources[name]
            self._popup_hide_sources[name] = 0
            if source:
                GLib.source_remove(source)

        def _schedule_popup_hide(self, name):
            # XFCE briefly transfers focus when executing a shortcut. A delayed
            # dismissal lets the explicit remote toggle take precedence.
            self._cancel_popup_hide(name)
            self._popup_hide_sources[name] = GLib.timeout_add(650, self._hide_if_unfocused, name)
            return False

        def _hide_if_unfocused(self, name):
            self._popup_hide_sources[name] = 0
            window = self.menu if name == "menu" else self.actions
            if name == "control" and profile in ("frutiger", "winxp"):
                # Standalone settings windows persist across app focus changes.
                return False
            if name == "menu" and self._start_open_menus:
                return False
            if window.get_visible() and not window.is_active():
                if name == "menu":
                    self._hide_menu()
                else:
                    self._hide_actions()
            return False

        def _hide_actions(self):
            self._cancel_popup_hide("control")
            if profile == "chromeos" and hasattr(self, "chrome_notifications"):
                self.chrome_notifications.discard()
                if hasattr(self, "chrome_quick_suspend_all"):
                    self.chrome_quick_suspend_all()
            if profile == "windows10" and hasattr(self, "ten_controller"):
                self.ten_controller.discard()
            if profile == "frutiger" and hasattr(self, "aqua_control_suspend"):
                self.aqua_control_suspend()
            self.actions.hide()

        def _show_aqua_notifications(self):
            if profile != "frutiger":
                return
            if not hasattr(self, "_aqua_notifications"):
                from .frutiger_notifications import AquaNotifications

                self._aqua_notifications = AquaNotifications(self, Gtk)
            if hasattr(self, "_aqua_flyouts"):
                for popover in self._aqua_flyouts.popovers.values():
                    popover.popdown()
            if hasattr(self, "_aqua_drives"):
                self._aqua_drives.popover.popdown()
            if hasattr(self, "_aqua_calendar"):
                self._aqua_calendar.popover.popdown()
            self._aqua_notifications.show()

        def _show_aqua_control(self, category=None, task=None):
            """Open a real Aqua detail page without toggling an open panel shut."""
            if profile != "frutiger":
                return
            # The launcher is a keep-above utility window. When Control Center
            # is already open, _toggle_actions() is skipped below; without an
            # unconditional hide the launcher can remain in front and block
            # further application/menu actions until XFWM's focus timer fires.
            self._hide_menu()
            if hasattr(self, "_aqua_notifications"):
                self._aqua_notifications.popover.popdown()
            if hasattr(self, "_aqua_flyouts"):
                for popover in self._aqua_flyouts.popovers.values():
                    popover.popdown()
            if hasattr(self, "_aqua_drives"):
                self._aqua_drives.popover.popdown()
            if hasattr(self, "_aqua_calendar"):
                self._aqua_calendar.popover.popdown()
            if not self.actions.get_visible():
                self._toggle_actions()
            if self.actions.get_visible():
                if category and task:
                    self.aqua_control_show_task(category, task)
                elif category:
                    self.aqua_control_show_category(category)
                else:
                    self.aqua_control_show_home()
                self.actions.present()

        def _toggle_chrome_quick_page(self, page):
            """Route shelf controls into owned pages, toggling the same page shut."""
            if profile != "chromeos":
                return
            self._cancel_popup_hide("control")
            if self.actions.get_visible():
                if self.chrome_quick_stack.get_visible_child_name() == page:
                    self._hide_actions()
                else:
                    self.chrome_quick_show_page(page)
                    self.actions.present()
                return
            self._toggle_actions()
            if self.actions.get_visible():
                self.chrome_quick_show_page(page)

        def _toggle_chrome_calendar(self):
            """The clock opens a real month view without breaking system-menu toggle."""
            self._toggle_chrome_quick_page("Calendar")

        def _toggle_chrome_notifications(self):
            """Open Xfce's real notification log without replacing its daemon."""
            self._toggle_chrome_quick_page("Notifications")

        def _toggle_actions(self):
            self._cancel_popup_hide("control")
            if profile == "winclassic" and hasattr(self, "classic98_tray_hide"):
                self.classic98_tray_hide()
            if profile == "windows10":
                self.ten_network.hide()
                if hasattr(self, "ten_task_view"):
                    self.ten_task_view.hide()
            if self.luna_tray is not None:
                for popup in self.luna_tray.popovers.values():
                    popup.hide()
            if self.actions.get_visible():
                self._hide_actions()
                return
            self._hide_menu()
            rect = self._desktop_rect()
            if profile == "winclassic":
                width = min(690, max(0, rect.width - 20))
                height = min(475, max(0, rect.height - panel_height - 20))
                if width < 300 or height < 235:
                    self._error("The display is too small for Control Panel.")
                    return
                self.actions.show_all()
                if not getattr(self, "_classic98_settings_positioned", False):
                    self.actions.resize(width, height)
                    self.actions.move(rect.x + (rect.width - width) // 2,
                                      rect.y + (rect.height - panel_height - height) // 2)
                    self._classic98_settings_positioned = True
                self.actions.present()
                return
            if profile == "winxp":
                width = min(746, max(0, rect.width - 24))
                height = min(536, max(0, rect.height - panel_height - 24))
                if width < 410 or height < 320:
                    self._error("The display is too small for Control Panel.")
                    return
                self.luna_control_show_home()
                self.actions.show_all()
                if not getattr(self, "_luna_settings_positioned", False):
                    self.actions.resize(width, height)
                    self.actions.move(rect.x + (rect.width - width) // 2,
                                      rect.y + (rect.height - panel_height - height) // 2)
                    self._luna_settings_positioned = True
                self.actions.present()
                return
            if profile == "aero":
                width = min(810, max(0, rect.width - 32))
                height = min(565, max(0, rect.height - panel_height - 32))
                if width < 320 or height < 280:
                    self._error("The display is too small for Control Panel.")
                    return
                self.actions.show_all()
                # show_all also unhides no-show-all children: restore the
                # authoritative category/search view before presenting.
                self.win7_panel_search.set_text("")
                self.win7_panel_reset()
                if not getattr(self, "_win7_settings_positioned", False):
                    self.actions.resize(width, height)
                    self.actions.move(rect.x + (rect.width - width) // 2,
                                      rect.y + (rect.height - panel_height - height) // 2)
                    self._win7_settings_positioned = True
                self.actions.present()
                return
            if profile == "frutiger":
                width = min(492, max(0, rect.width - 24))
                height = min(620, max(0, rect.height - panel_height - 24))
                if width < 290 or height < 275:
                    self._error("The display is too small for Aqua Control Center.")
                    return
                self.aqua_control_show_home()
                self.actions.show_all()
                if not getattr(self, "_aqua_settings_positioned", False):
                    self.actions.resize(width, height)
                    self.actions.move(rect.x + rect.width - width - 10,
                                      rect.y + rect.height - panel_height - height - 8)
                    self._aqua_settings_positioned = True
                self.actions.present()
                self._refresh_status_async()
                return
            width = min(396 if profile == "chromeos" else 362 if ten else 382 if profile == "winclassic" else 388 if profile == "frutiger" else 412 if profile == "aero" else 330,
                        max(0, rect.width - 16))
            self.actions.show_all()
            desired_height = action_heights.get(profile, 430)
            if profile in ("winxp", "winclassic"):
                # gtk.ScrolledWindow reports a 260px minimum, not its full
                # child's natural height; the 1998 icon view can be taller
                # than a hard-coded utility-window size after font scaling.
                desired_height = max(desired_height, self._control_natural_height())
            height = min(desired_height, max(0, rect.height - panel_height - 16))
            if width < 235 or height < 250:
                self._error("The display is too small for " + ("Action Center." if ten else "Control Panel."))
                return
            if profile == "chromeos":
                self.chrome_quick_show_home()
                self.chrome_quick_clock.set_text(
                    GLib.DateTime.new_now_local().format("%a, %d %b · %H:%M"))
            self.actions.resize(width, height)
            margin = 10 if profile == "chromeos" else 0 if ten else 8
            self.actions.move(rect.x + rect.width - width - margin,
                              rect.y + rect.height - panel_height - height - margin)
            self.actions.present()
            if profile == "windows10":
                self.ten_controller.on_open()
            if profile == "chromeos":
                # Utility popups don't reliably emit a second configure event
                # after present() under Xvfb. Apply the X11 mask once mapped.
                from .chrome_shell import apply_rounded_window_shape

                GLib.idle_add(apply_rounded_window_shape, self.actions, 26)
                # Some X11 window managers reset the shape during the first
                # utility resize; reapply after that configure settles.
                GLib.timeout_add(150, apply_rounded_window_shape, self.actions, 26)
            elif profile == "frutiger":
                # GTK's rounded CSS child still sits inside a rectangular
                # utility window under uncomposited XFWM4. Use the proven
                # optional X11 shape mask instead of painting square corners.
                from .chrome_shell import apply_rounded_window_shape

                GLib.idle_add(apply_rounded_window_shape, self.actions, 22)
                GLib.timeout_add(150, apply_rounded_window_shape, self.actions, 22)

        def _open_search(self):
            if not self.menu.get_visible():
                self._toggle_menu()
            if self.menu.get_visible():
                if profile == "winxp":
                    self._reveal_luna_search()
                elif profile == "winclassic":
                    self._reveal_classic_search()
                else:
                    self.search.grab_focus()

        def _populate(self, query):
            for child in self.results.get_children():
                self.results.remove(child)
            if ten:
                self._populate_windows10(query)
                return
            if profile == "chromeos":
                self._populate_chrome_apps(query)
                return
            if profile == "frutiger":
                self._populate_frutiger(query)
                return
            if profile == "winxp":
                self._populate_luna(query)
                return
            if profile == "aero":
                self._populate_win7(query)
                return
            matches = matching_apps(self.apps, query)
            if not matches:
                self.results.pack_start(self._class(Gtk.Label(label="No matching applications", xalign=0),
                                                     "aero-menu-sub"), False, False, 8)
            for app in matches[:self._app_page_size]:
                btn = self._class(Gtk.Button(), "aero-menu-app")
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                icon = app.get_icon()
                row.pack_start(Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU) if icon else
                               self._icon("applications-other", Gtk.IconSize.MENU), False, False, 0)
                row.pack_start(Gtk.Label(label=app.get_display_name(), xalign=0), True, True, 0)
                btn.add(row)
                btn.connect("clicked", lambda _btn, selected=app: self._launch(selected))
                btn.connect("button-press-event", lambda widget, event, selected=app:
                            self._pin_context(widget, selected, event))
                btn.connect("popup-menu", lambda widget, selected=app: self._pin_context(widget, selected))
                self.results.pack_start(btn, False, False, 0)
            if len(matches) > self._app_page_size:
                more = self._class(Gtk.Button(label="All Programs · Show more"), "aero-menu-app")
                more.get_accessible().set_name("Show more installed applications")
                def expand(_button):
                    self._app_page_size += 24
                    self._populate(self.search.get_text())
                more.connect("clicked", expand)
                self.results.pack_start(more, False, False, 0)
            self.results.show_all()

        def _populate_windows10(self, query):
            """Compact Windows 10 alphabetical app rail with real Gio launchers."""
            matches = matching_apps(self.apps, query)
            if not matches:
                self.results.pack_start(self._class(Gtk.Label(
                    label="No matching applications", xalign=0), "ten-muted"),
                    False, False, 12)
            previous_letter = None
            for app in matches[:self._app_page_size]:
                title = app.get_display_name() or app.get_name() or "Application"
                letter = title[0].upper() if title[0].isalpha() else "#"
                if not query.strip() and letter != previous_letter:
                    self.results.pack_start(self._class(
                        Gtk.Label(label=letter, xalign=0), "ten-letter"), False, False, 3)
                    previous_letter = letter
                button = self._class(Gtk.Button(), "aero-menu-app")
                content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                icon = app.get_icon()
                content.pack_start(
                    Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU) if icon else
                    self._icon("applications-other", Gtk.IconSize.MENU),
                    False, False, 0)
                label = self._class(Gtk.Label(label=title, xalign=0), "ten-app-label")
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.set_max_width_chars(23)
                content.pack_start(label, True, True, 0)
                button.add(content)
                button.set_tooltip_text(title + " · Right-click to pin or unpin")
                button.get_accessible().set_name("Launch " + title)
                button.connect("clicked", lambda _button, selected=app: self._launch(selected))
                button.connect("button-press-event", lambda widget, event, selected=app:
                               self._pin_context(widget, selected, event))
                button.connect("popup-menu", lambda widget, selected=app:
                               self._pin_context(widget, selected))
                self.results.pack_start(button, False, False, 0)
            if len(matches) > self._app_page_size:
                more = self._class(Gtk.Button(label="Show more apps"), "aero-menu-app")
                more.get_accessible().set_name("Show more installed applications")
                def expand(_button):
                    self._app_page_size += 24
                    self._populate(self.search.get_text())
                more.connect("clicked", expand)
                self.results.pack_start(more, False, False, 4)
            self.results.show_all()

        def _populate_frutiger(self, query):
            """Icon-first Gio apps plus bounded real places/settings search."""
            matches = frutiger_apps(self.apps, self._pinned_ids, query)
            for app in matches[:self._app_page_size]:
                title = app.get_display_name() or app.get_name() or "Application"
                button = self._class(Gtk.Button(), "aqua-app-tile")
                content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                icon = app.get_icon()
                # Custom Gio SVG/GFileIcon providers can report a very large
                # intrinsic size. Keep the entire icon grid at real 48px.
                picture = (Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG) if icon
                           else self._icon("applications-other", Gtk.IconSize.DIALOG))
                picture.set_pixel_size(48)
                content.pack_start(picture, False, False, 0)
                label = Gtk.Label(label=title)
                label.set_max_width_chars(16)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                content.pack_start(label, False, False, 0)
                button.add(content)
                button.get_accessible().set_name("Launch " + title)
                button.set_tooltip_text(title)
                button.connect("clicked", lambda _button, selected=app: self._launch(selected))
                button.connect("button-press-event", lambda widget, event, selected=app:
                               self._pin_context(widget, selected, event))
                button.connect("popup-menu", lambda widget, selected=app:
                               self._pin_context(widget, selected))
                self.results.add(button)
            extra_results = 0
            if query.strip():
                from .frutiger_control_center import search_aqua

                needle = query.casefold().strip()
                special_dirs = (
                    ("Home", "user-home", Path.home()),
                    ("Desktop", "user-desktop", Path(
                        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)
                        or Path.home() / "Desktop")),
                    ("Documents", "folder-documents", Path(
                        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
                        or Path.home() / "Documents")),
                    ("Downloads", "folder-download", Path(
                        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
                        or Path.home() / "Downloads")),
                    ("Music", "folder-music", Path(
                        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
                        or Path.home() / "Music")),
                    ("Pictures", "folder-pictures", Path(
                        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
                        or Path.home() / "Pictures")),
                    ("Videos", "folder-videos", Path(
                        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
                        or Path.home() / "Videos")),
                )
                for title, icon_name, path in special_dirs:
                    if needle not in title.casefold():
                        continue
                    button = self._class(Gtk.Button(), "aqua-app-tile")
                    inside = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                    inside.pack_start(self._icon(icon_name, Gtk.IconSize.DIALOG),
                                      False, False, 0)
                    inside.pack_start(Gtk.Label(label=title), False, False, 0)
                    button.add(inside)
                    button.get_accessible().set_name("Open location " + title)
                    button.connect("clicked", lambda _button, folder=path:
                                   self._open_luna_user_folder(folder))
                    self.results.add(button)
                    extra_results += 1
                if "trash" in needle or needle in "trash":
                    button = self._class(Gtk.Button(label="Trash"), "aqua-app-tile")
                    button.get_accessible().set_name("Open Trash")
                    button.connect("clicked", lambda _button: self._open_uri("trash:///"))
                    self.results.add(button)
                    extra_results += 1
                for category, task in search_aqua(query):
                    button = self._class(Gtk.Button(), "aqua-app-tile")
                    inside = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                    inside.pack_start(self._icon(task[1], Gtk.IconSize.DIALOG),
                                      False, False, 0)
                    title = Gtk.Label(label=task[0])
                    title.set_line_wrap(True)
                    title.set_max_width_chars(20)
                    inside.pack_start(title, False, False, 0)
                    button.add(inside)
                    button.get_accessible().set_name("Open setting " + task[0])
                    button.set_tooltip_text(category[1] + " · " + task[3])
                    button.connect("clicked", lambda _button, page=category[0], item=task[0]:
                                   self._show_aqua_control(page, item))
                    self.results.add(button)
                    extra_results += 1
            if not matches and not extra_results:
                empty = self._class(Gtk.Label(label="No matching apps, places or settings"),
                                    "aqua-empty")
                self.results.add(empty)
            if len(matches) > self._app_page_size:
                more = self._class(Gtk.Button(label="Show more applications…"),
                                   "aqua-app-tile")
                more.get_accessible().set_name("Show more installed applications")
                def expand(_button):
                    self._app_page_size += 24
                    self._populate(self.search.get_text())
                more.connect("clicked", expand)
                self.results.add(more)
            self.results.show_all()

        def _populate_win7(self, query):
            apps = win7_programs(self.apps, self._pinned_ids, query,
                                 all_programs=self._win7_all_programs,
                                 limit=self._app_page_size if (query.strip() or self._win7_all_programs) else 9)
            for app in apps:
                button = self._class(Gtk.Button(), "win7-program")
                content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
                icon = app.get_icon()
                content.pack_start(Gtk.Image.new_from_gicon(icon, Gtk.IconSize.LARGE_TOOLBAR) if icon else
                                   self._icon("applications-other", Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
                label = self._class(Gtk.Label(label=app.get_display_name() or app.get_name(),
                                              xalign=0), "win7-program-label")
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.set_max_width_chars(27)
                content.pack_start(label, True, True, 0)
                button.add(content)
                button.get_accessible().set_name("Launch " + (app.get_display_name() or app.get_name()))
                button.connect("clicked", lambda _btn, selected=app: self._launch(selected))
                button.connect("button-press-event", lambda widget, event, selected=app:
                               self._pin_context(widget, selected, event))
                button.connect("popup-menu", lambda widget, selected=app:
                               self._pin_context(widget, selected))
                self.results.pack_start(button, False, False, 0)
            if not apps:
                label = self._class(Gtk.Label(label="No matching programs", xalign=0),
                                    "aero-menu-sub")
                label.set_margin_top(12)
                self.results.pack_start(label, False, False, 0)
            if (query.strip() or self._win7_all_programs) and (
                    len(matching_apps(self.apps, query)) > self._app_page_size):
                more = self._class(Gtk.Button(label="Show more programs…"), "win7-all-programs")
                more.connect("clicked", lambda *_args: self._expand_win7_programs(query))
                self.results.pack_start(more, False, False, 0)
            self.win7_all_button.set_label("◂  Back" if self._win7_all_programs else "▸  All Programs")
            self.win7_all_button.get_accessible().set_name(
                "Show recent and pinned programs" if self._win7_all_programs else
                "Show all installed programs")
            self.results.show_all()

        def _expand_win7_programs(self, query):
            self._app_page_size += 24
            self._populate(query)

        def _populate_luna(self, query):
            """XP: 2 prominent favorites, a separator and actual installed apps."""
            featured, regular = luna_programs(
                self.apps, self._pinned_ids, query,
                self._app_page_size if query.strip() else
                self._luna_taskbar_options["recent_program_count"],
                start_favorites=self._luna_start_state.favorites,
                history=self._luna_start_state.launches)

            def add_app(app, *, large=False):
                button = self._class(Gtk.Button(), "luna-program")
                if large:
                    button.get_style_context().add_class("luna-featured")
                content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
                icon = app.get_icon()
                size = Gtk.IconSize.LARGE_TOOLBAR if large else Gtk.IconSize.MENU
                content.pack_start(Gtk.Image.new_from_gicon(icon, size) if icon else
                                   self._icon("applications-other", size), False, False, 0)
                caption = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                if large:
                    classifier = getattr(app, "get_categories", None)
                    category = (classifier() or "").split(";") if callable(classifier) else ()
                    headline = "Internet" if "WebBrowser" in category else (
                        "E-mail" if "Email" in category else "Favorite program")
                    title = self._class(Gtk.Label(label=headline, xalign=0), "luna-program-category")
                    caption.pack_start(title, False, False, 0)
                label = Gtk.Label(label=app.get_display_name() or app.get_name(), xalign=0)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                caption.pack_start(label, False, False, 0)
                content.pack_start(caption, True, True, 0)
                button.add(content)
                button.get_accessible().set_name("Launch " + (app.get_display_name() or app.get_name()))
                button.connect("clicked", lambda _button, selected=app: self._launch(selected))
                button.connect("button-press-event", lambda widget, event, selected=app:
                               self._pin_context(widget, selected, event))
                button.connect("popup-menu", lambda widget, selected=app:
                               self._pin_context(widget, selected))
                self.results.pack_start(button, False, False, 0)

            for app in featured:
                add_app(app, large=True)
            if featured and regular:
                self.results.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                                        False, False, 5)
            for app in regular:
                add_app(app)
            if not featured and not regular:
                self.results.pack_start(self._class(
                    Gtk.Label(label="No installed programs match", xalign=0),
                    "luna-empty"), False, False, 12)
            if query.strip() and len(matching_apps(self.apps, query)) > self._app_page_size:
                more = self._class(Gtk.Button(label="Show more results…"), "luna-program")
                more.connect("clicked", lambda *_args: self._expand_luna_results(query))
                self.results.pack_start(more, False, False, 0)
            self.results.show_all()

        def _expand_luna_results(self, query):
            self._app_page_size += 24
            self._populate(query)

        def _search_key(self, event):
            if event.keyval == Gdk.KEY_Escape:
                self._hide_menu()
                return True
            if profile == "winxp":
                buttons = [child for child in self.results.get_children()
                           if isinstance(child, Gtk.Button) and child.get_visible()
                           and child.get_sensitive()]
                if event.keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
                    step = 1 if event.keyval == Gdk.KEY_Down else -1
                    if self.search.is_focus():
                        if buttons:
                            buttons[0 if step > 0 else -1].grab_focus()
                            return True
                    else:
                        # Only intercept navigation inside XP's left app list.
                        # Right-column links retain their normal GTK keyboard
                        # handling; never jump back to the first app on Down.
                        focus = self.menu.get_focus()
                        if focus in buttons:
                            destination = buttons[(buttons.index(focus) + step) % len(buttons)]
                            destination.grab_focus()
                            return True
                elif not self.search.is_focus():
                    # Typing with a selected app should open the *real* XP
                    # search field, not silently discard the keystroke.
                    modifiers = (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK |
                                 Gdk.ModifierType.SUPER_MASK)
                    char = Gdk.keyval_to_unicode(event.keyval)
                    if not (event.state & modifiers) and char:
                        typed = chr(char)
                        if typed.isprintable() and not typed.isspace():
                            previous = self.search.get_text() if self.search.get_visible() else ""
                            self._reveal_luna_search()
                            self.search.set_text(previous + typed)
                            self.search.set_position(-1)
                            return True
            if self.search.is_focus() and event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                apps = matching_apps(self.apps, self.search.get_text())
                if apps:
                    self._launch(apps[0])
                    return True
            if (event.keyval == Gdk.KEY_Down and self.search.is_focus()
                    and self.results.get_children()):
                first = next((child for child in self.results.get_children()
                              if isinstance(child, (Gtk.Button, Gtk.FlowBoxChild))
                              and child.get_visible() and child.get_sensitive()), None)
                if first is None:
                    return False
                if profile == "frutiger" and isinstance(first, Gtk.FlowBoxChild):
                    first = first.get_child()
                first.grab_focus()
                return True
            return False

        def _hide_menu(self):
            if profile in ("winclassic", "winxp"):
                # Native Gtk.Menu flyouts are separate X11 popup surfaces: hiding
                # the Start Gtk.Window alone does not release their pointer grab.
                for popup in tuple(self._start_open_menus):
                    popup.popdown()
            self._cancel_popup_hide("menu")
            self._menu_focused = False
            if self.menu:
                self.menu.hide()
            return False

        def _menu_focus_in(self, *_args):
            self._menu_focused = True
            return False

        def _menu_focus_out(self, *_args):
            return self._schedule_popup_hide("menu")

        def _toggle_menu(self):
            self._cancel_popup_hide("menu")
            if profile == "winclassic" and hasattr(self, "classic98_tray_hide"):
                self.classic98_tray_hide()
            if profile == "windows10":
                self.ten_network.hide()
                if hasattr(self, "ten_task_view"):
                    self.ten_task_view.hide()
            if self.luna_tray is not None:
                for popup in self.luna_tray.popovers.values():
                    popup.hide()
            if self.menu.get_visible():
                self._hide_menu()
                return
            if profile not in ("frutiger", "winxp"):
                self._hide_actions()
            rect = self._desktop_rect()
            self._menu_focused = False
            self._menu_opened_at = GLib.get_monotonic_time()
            if profile == "aero":
                self._win7_all_programs = False
            self.search.set_text("")
            if profile == "aero":
                self._populate("")
            elif profile == "frutiger":
                # Opening the launcher always returns to the app overview;
                # last session's Settings/Places tab is not a hidden surprise.
                self._frutiger_switch_to("Apps")
            preferred_sizes = {
                "winxp": (480, 540),
                "winclassic": (262, 332),
                "chromeos": (610, 628),
                "frutiger": (600, 600),
                "windows10": (690, 560),
                "aero": (525, 535),
            }
            preferred_width, preferred_height = preferred_sizes.get(profile, (490, 505))
            x, y, w, h = menu_geometry(
                rect.x, rect.y, rect.width, rect.height,
                preferred_width=preferred_width, preferred_height=preferred_height,
                panel_height=panel_height)
            if w < 180 or h < 180:
                self._error("The display is too small for the Start menu.")
                return
            if profile == "chromeos":
                x = rect.x + min(16, max(8, rect.width - w))
            if profile == "winxp":
                self._app_page_size = 24
                self.search.set_text("")
                self._populate("")
                self.search.set_no_show_all(True)
                self.search.hide()
            elif profile == "winclassic":
                self.classic_refresh_submenus()
                self.classic_search.set_no_show_all(True)
                self.classic_search.hide()
                self.classic_results_scroll.set_no_show_all(True)
                self.classic_results_scroll.hide()
            self.menu.show_all()
            self.menu.resize(w, h)
            self.menu.move(x, y)
            self.menu.present()
            if profile == "frutiger":
                from .chrome_shell import apply_rounded_window_shape

                GLib.idle_add(apply_rounded_window_shape, self.menu, 27)
                GLib.timeout_add(150, apply_rounded_window_shape, self.menu, 27)
            if profile == "winxp":
                GLib.idle_add(self._reanchor_luna_menu)
                first_app = next((widget for widget in self.results.get_children()
                                  if isinstance(widget, Gtk.Button)), None)
                if first_app:
                    first_app.grab_focus()
            elif profile == "aero":
                GLib.idle_add(self._reanchor_luna_menu)
                # Win+typing is a core Windows 7 behavior: let keyboard input
                # enter search even when the recent-app list is visible.
                self.search.grab_focus()
            elif profile == "winclassic":
                GLib.idle_add(self._reanchor_luna_menu)
                first = next((child for child in self.menu.get_child().get_children()[-1].get_children()
                              if isinstance(child, Gtk.MenuButton)), None)
                if first is not None:
                    first.grab_focus()
            else:
                self.search.grab_focus()

        def _reanchor_luna_menu(self):
            """Anchor using GTK's allocated height, not its requested height."""
            if not self.menu.get_visible():
                return False
            rect = self._desktop_rect()
            actual_w, actual_h = self.menu.get_size()
            self.menu.move(rect.x + 8, actual_popup_y(rect.y, rect.height, actual_h,
                                                       panel_height=panel_height))
            return False

        def _open_uri(self, uri):
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
                self._hide_menu()
            except GLib.Error as exc:
                self._error(str(exc))

        def _launch(self, app):
            try:
                launch_app_checked(app)
                if profile == "winxp" and self._luna_start_state is not None:
                    from .luna_start_state import record_launch, save_start_state

                    record_launch(self._luna_start_state, app.get_id())
                    try:
                        save_start_state(self._luna_start_state)
                    except (OSError, ValueError) as exc:
                        logging.getLogger(__name__).warning("Could not save XP recent apps: %s", exc)
                self._hide_menu()
            except (GLib.Error, OSError, RuntimeError) as exc:
                self._error(str(exc))

        def _error(self, message, *, title="Could not launch application"):
            dialog = Gtk.MessageDialog(transient_for=self.bar, flags=Gtk.DialogFlags.MODAL,
                                       message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                       text=title)
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()

    app = AeroShell()
    result = app.run(argv or ["ricehub-aero-shell"])
    return 1 if app._smoke_failed else result
