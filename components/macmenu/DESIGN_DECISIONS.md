# Design review: every MacMenu control

Review date: 2026-11-01. References: the user's Control Center v1.3.1 and
the supplied DoYourData-style macOS menu screenshot. MacMenu remains an
independent XFCE/GTK3 application.

## Main launcher

| Element | Decision | Why |
| --- | --- | --- |
| Search | Keep, focus at open | Finding an app is the primary task; native clear button is sufficient. |
| List/Grid | Remove completely | One consistent macOS layout eliminates a mode switch, two code paths and redundant view preferences. |
| Window title/branding | Small monochrome penguin, no wordmark | The RC10 brand mark sits beside the search without taking a new row or displacing navigation. It is not a fake Apple logo. |
| Category navigation | One compact symbolic rail | Matches the reference hierarchy while preserving category access with tooltips. |
| App count | Show only while searching | Useful for search feedback; redundant noise while casually browsing the category. |
| Favorites | Keep as category and context action | A permanent star on every app made scanning harder. |
| Recent | Keep as category with opt-out | Useful shortcut, but not worth a dashboard card or an unrequested tracker. |
| Per-app actions | Right-click and Shift+F10 | Preserves features without row buttons. |
| System actions | Keep Files, Terminal, Settings under More | These launch related applications; session and power actions are already owned by the separate Control Center. |
| Preferences | Move into More menu; keep Ctrl+, | Frequently visible gear was wasted chrome. Keyboard command stays discoverable in docs. |
| Session footer | Remove in RC11 | Two extra buttons and their separator duplicated the Control Center and occupied valuable rail height. |
| Login, lock and logout | Remove from MacMenu in RC11 | One clear owner (Control Center) avoids accidental session actions and keeps the launcher task-focused. |
| Show more | Only for catalogs above 48 matches | No reason to add a sticky control for 32 installed apps. Limit huge catalogs to 30 initial widgets. |
| One recessed app panel | Keep | A single contained grid matches the Control Center's soft elevated modules without nested app cards. |
| Motion/blur | Reject for rc6 | Opaque native GTK rendering is predictable on XFCE/X11 and avoids compositor cost. |
| Repeated keyboard shortcut | One `--toggle` command | A persistent GApplication receives each invocation: open, close, reopen; verified across separate processes. |
| Search rendering | Recycle visible GTK tiles | Avoid per-keystroke widget creation and icon reload; allocate only when the user reveals more apps. |
| Branded launcher icon | Original SVG penguin, white or dark monochrome | Recognizable in XFCE's application menu and panel; light palette needs a dark variant for contrast. Reuse the same artwork in a future MacBar integration without coupling apps now. |

### RC6 reference interpretation

| Reference detail | Adopted | Reason |
| --- | --- | --- |
| Slim icon rail with category navigation only | Yes | Strong hierarchy and more room on short displays; icon tooltips retain accessibility. |
| Main app list | Use the established macOS grid | The user chose the macOS style and requested removal of the older Whisker/List mode. |
| Pink/blue translucent wallpaper blur | No | True blur is compositor-dependent on XFCE; six existing palettes stay consistent with Control Center. |
| Three traffic-light circles | No | This launcher has no meaningful maximize/minimize lifecycle; fake buttons would violate the interaction contract. |
| Arrow action on every app row | No | Existing activation and context menus are clearer without repeated controls. |

## Preferences

| Setting or action | Decision | Rationale and default |
| --- | --- | --- |
| View | **Remove completely** | One macOS layout, no persisted layout preference; old keys are safely ignored on upgrade. |
| Color scheme | Replace dropdown with six theme preview buttons: Auto / Midnight / Light / Graphite / Ocean / Violet | Immediate, visible color choice; no submenu, no add-on customization engine. Default: Midnight. Auto respects XFCE/GTK preference. |
| Icon size | Keep: Small / Regular / Large | Helps different screen and vision needs. Default: Regular. |
| Menu position | Keep, clarify "Near pointer" | XFCE panels differ; honest label avoids falsely promising exact panel-button anchoring. Default: Top left. |
| List descriptions | **Remove** | Only existed for the deleted Whisker/List layout. |
| Instant reopening | Keep on by default, allow disabling | Users prioritize near-instant repeated shortcut presses; explicit toggle allows RAM saving. |
| Recent apps | Keep on with clear opt-out | Helps repeat-launching; user can opt out and remove saved history. |
| Clear history | Keep in Privacy & Data | Separate action is more understandable than a global reset. |
| Export / Import | Keep in Privacy & Data | Backup includes potentially sensitive recent app IDs; confirm replacement. |
| Reset preferences | Keep with explicit confirmation | Destructive but necessary for recovery; visually de-emphasized. |
| Language | **No switch** | Interface is English-only; a switch with just one option would be pointless. Installed app names still follow the host locale. |
| Autostart / indexing / recommendations | **Do not add** | A launcher does not need a daemon, online service or speculative tracking. |

## Principles and limitations

1. Preserve Whisker, panel config, XFCE theme, and the separate Control Center.
2. Show the speed/RAM tradeoff transparently; warm state defaults on to serve repeated shortcut invocations.
3. Prefer system app icons and native controls to custom decorative copies.
4. A setting needs a distinct task, a meaningful choice, and a safe default.
5. Verify on actual Linux Mint hardware before calling this stable 1.0.

## RC4 installation decisions

| Change | Behavior | Reason |
| --- | --- | --- |
| Stop prior MacMenu | Ask the prior launcher to quit, then SIGTERM only verified same-user `python3 -m macmenu` processes if needed | Fixes the old-process-stays-running bug without a broad `pkill -f`. |
| Remove old application | Back up the *managed* prior directory, atomically replace it and remove the retired active copy | Prevents leftover Python modules while preserving a recoverable pre-upgrade snapshot. |
| Preserve user preferences | Never modify `~/.config/macmenu/` in the installer | Existing favorites, history and themes stay intact; legacy layout keys are ignored at runtime. |
| System `.deb` present | Explicit permission prompt before removing only `xfce-macmenu` | Never use `sudo` silently or uninstall unrelated packages. |
| Unmanaged paths | Abort with a precise explanation | An unfamiliar launcher or directory might belong to the user; do not overwrite it. |
| Whisker / Control Center | Never touch | They are independent applications and the user's fallback. |
