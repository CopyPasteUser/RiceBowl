"""Versioned, opt-in shared Linux APIs for independent RiceBowl renderers.

Importing this package never probes hardware or starts a background service.
The API version is independent of RiceBowl's application/release version.
"""

API_VERSION = "1.0"


def manifest() -> dict[str, object]:
    """Stable feature discovery without accessing hardware or user files."""
    from . import packs, profiles, spice

    return {
        "api_version": API_VERSION,
        "profiles": dict(profiles.PROFILE_FAMILIES),
        "rice_packs": {"schema_version": packs.SCHEMA_VERSION,
                       "inspect": "riceware packs list|show|check|template",
                       "apply": "riceware packs apply ID --yes"},
        "components": {
            "riceSpice": {"read": (*spice.READERS, "scan_wifi"),
                          "write": tuple(spice.WRITERS)},
            "ricePop": {"read": ("status", "history", "unread", "quiet_mode"),
                        "write": ("send", "mark_read", "dismiss", "clear_history",
                                  "set_quiet_mode")},
            "ricePlate": {"read": ("snapshot", "appearance"),
                          "write": ("save_appearance", "manage_shortcuts"),
                          "preview": ("riceware plate preview --style winxp",)},
            "riceWine": {"read": ("wine_version", "list_prefixes", "list_apps"),
                         "write": ("create_prefix", "resume_prefix", "launch",
                                   "register", "unregister", "launch_app")},
        },
    }
