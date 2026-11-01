---
version: 1.0.0rc11
reference: "User's macOS Control Center 1.3.1 and screenshot of DoYourData-style macOS menu"
colors:
  primary: "#0a84ff"
  dark-surface: "#0e1118"
  dark-sidebar: "#151b25"
  dark-card: "#1a222d"
  dark-text: "#f6f8ff"
  dark-muted: "#abb5c6"
  dark-accent: "#0a84ff"
  light-surface: "#f5f7fb"
  light-card: "#ffffff"
  light-text: "#1a2435"
  light-accent: "#007aff"
  graphite-surface: "#1b1d21"
  graphite-accent: "#a5bedc"
  ocean-surface: "#101c2d"
  ocean-accent: "#69b8ff"
  violet-surface: "#211a2a"
  violet-accent: "#d6aaff"
typography:
  primary:
    fontFamily: '"SF Pro Text", "Inter", sans-serif'
    fontSize: "12px"
  display:
    fontFamily: '"SF Pro Display", "Inter", sans-serif'
    fontSize: "17px"
spacing:
  header: "12px"
  content: "11px"
  rail: "5px"
rounded:
  launcher: "20px"
  setting-card: "13px"
  app-tile: "13px"
  segmented-button: "999px"
---

# MacMenu design contract

## Visual relationship to the Control Center

The actual v1.3.1 Control Center is the source of the default midnight `#0e1118`
surface, saturated `#0a84ff` accent, subtle elevated modules, quiet borders,
compact 12–13 px typography, and 20 px outside radius. MacMenu uses the same
visual grammar, **not** a cloned Control Center layout: an app launcher still
needs immediately accessible search and app icons.

Four further user-selectable palettes extend the same visual system: Light,
Graphite, Ocean and Violet. Auto follows the active XFCE/GTK dark preference.
The color values in this document mirror `macmenu/ui.py:PALETTES`. An opaque
surface is intentional: GTK3 cannot guarantee real macOS background blur on
XFCE/X11, and translucent text would weaken legibility.

## Interaction architecture

- **One header:** a 26 px original Linux penguin mark, search box and a single More
  button. The brand symbol is non-interactive and has an accessible name; it
  adds no new setting or action. Tooltips and accessible
  names describe every icon. No competing display-mode controls.
- **Task-first header:** one search field and More menu. The
  content title says All Applications or the selected category. Count only
  appears during a search.
- **Monochrome identity:** an original white penguin silhouette with negative-space
  eyes, beak and belly echoes macOS menu-bar icon restraint without reproducing
  Apple's silhouette. The same outline uses dark ink `#1a2435` on Light for
  readable contrast. A dark neutral tile `#151b25` gives the white mark enough
  contrast as an app/panel icon; no colored Tux mascot or extra decoration.
  `assets/macmenu-penguin.svg` is also a reusable future MacBar resource.
- **Single macOS layout:** 53 px icon rail with a four-column app grid in one
  recessed module. Named tooltips and active indicators explain each category.
  The rail contains only category navigation, with no fixed footer, session
  separators or power controls. This reduces visual clutter and gives more
  scrolling room on shorter displays.
- **Responsibility split:** the separate Control Center owns Lock, Switch User,
  Log Out and Power. MacMenu owns application discovery, search and launch.
  Its secondary menu contains only Preferences, Files, Terminal and XFCE Settings.
- **Context actions:** favorite, sorting and `.desktop` actions appear on
  right-click / keyboard context activation, rather than on every app row.
- **Preferences:** segmented Appearance / Privacy & Data pages, each with
  grouped settings in a single quiet card. Six immediate-apply theme preview
  buttons replace a hidden color dropdown. Every setting has a reason to exist.
- **Keyboard:** a repeatable one-command open/close toggle, search focus,
  categories, launch and Escape work without the mouse.

## Density, latency, and accessibility

The launcher is 572×486 by default. The extra 36 px compared with rc4 restores
four complete grid columns alongside the new icon rail. Tile height keeps a
partial fifth row out of sight while the list remains scrollable. Real application
icons come from the active Linux icon theme; MacMenu does not bundle counterfeit
macOS system icons. Text is only truncated when necessary, with full app names
available by tooltip. The blue selection state and focus ring remain distinguishable
from hover states. Native controls keep keyboard and assistive APIs where possible.

Default window: 572×486; minimum: 420×350. Icon
rail: 53 px. Large app catalogs create
only 30 initial widgets; up to 48 matching apps are rendered without paging.
Runtime `macmenu/ui.py:PALETTES` owns theme values and GTK CSS; this document
mirrors accepted colors and explains how they are used. The bundled brand mark
is rasterized by GdkPixbuf once per selected light/dark mode and cached for
theme switching; no SVG decoding or I/O happens on warm shortcut toggles.

Small catalogs of up to 48 matching apps render completely, removing a pointless
sticky "Show more" control in typical use. Larger catalogs initially create
at most 30 app widgets. Existing GTK tiles are recycled for search and reopen;
icon objects are changed only when the app identity or icon size changes.
Background retention is on by default for instant repeated shortcuts; a
clearly labeled setting allows users to trade reopening speed for lower RSS.

## Anti-patterns explicitly rejected

- Fake macOS blur or transparency; custom-rendered lookalike widgets.
- Parallel Whisker/List layout, display toggles or hidden View preferences.
- Per-app favorite stars, repeated secondary actions, multiple system widgets,
  session buttons or a duplicated Control Center power menu.
- Extra page title, oversized brand header, verbose onboarding.
- Animation, prefetching or daemon state without measured user benefit.

See [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for the individual setting review.
