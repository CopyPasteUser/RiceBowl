# RiceBowl (Wayland Preview) — first login-session track

**Experimental / opt-in.** This is an independently selectable labwc session
with a temporary native Waybar panel, not the finished RicePlate/RiceSpice/
RicePop desktop. The current XFCE/X11 rice suite and its backups stay intact.
Mint 22/Ubuntu 24.04's labwc **0.7.1** is supported by using its
`--startup` command and requesting compositor exit when the shell finishes.

## Prerequisites

- Linux display manager that enumerates `/usr/share/wayland-sessions`
  (check your specific login manager on the actual computer).
- User-local RiceBowl already installed with `bash install.sh`.
- `labwc`, `waybar`, `foot`, `fuzzel`, `swaylock`, a proper logind
  `XDG_RUNTIME_DIR` and D-Bus user session.
- `xdg-desktop-portal`, GTK and wlroots portal backends for file pickers
  and screencast; `xwayland` for legacy X11 clients.
- Optional: `swaybg` wallpaper, `swayidle` idle lock, `mako`
  notifications and an installed user polkit agent.

The package only installs the session chooser, a small forwarding wrapper,
RiceBowl-specific portal preferences and a namespaced systemd user target.
It **does not install RiceBowl itself**, overwrite `~/.config/labwc`, edit
global XFCE configuration or set the default session.

The preview `.deb` builder normalizes filesystem/archive timestamps and
supports the standard `SOURCE_DATE_EPOCH` override. Run
`sh scripts/test_wayland_package_reproducibility.sh` to verify that two builds
at different wall-clock times are byte-for-byte identical. This verifies the
small **session-entry package**, not a complete RiceBowl 1.0 application bundle.

## Build and opt in (Debian/Ubuntu/Mint)

From the current RiceBowl checkout:

```bash
bash install.sh --dry-run
bash install.sh
ricebowl de check --json
sh scripts/build_wayland_session_deb.sh
```

Review the package before installing:

```bash
dpkg-deb --contents dist/ricebowl-wayland-session_0.1.0~preview1_all.deb
sudo apt install ./dist/ricebowl-wayland-session_0.1.0~preview1_all.deb
```

Log out. In the login manager's session selector, choose
**RiceBowl (Wayland Preview)**. Your existing XFCE session remains an
independent choice. If the entry is not shown, use the current XFCE session
and inspect the display manager's session-directory support before changing
system settings.

**Nothing in the ordinary `bash install.sh` enables this session.** Do not
install the preview package on a production-only machine without keeping a
working alternative login/session available.

### Nested developer test

From another desktop, `ricebowl de start --nested` explicitly launches a
separate compositor with activation-environment updates disabled, so it
doesn't hijack the current desktop's D-Bus/systemd Wayland variables.
The compositor still requires hardware/driver support for a nested backend.

### RicePlate layout recipes (first data-only contract)

The experimental Waybar adapter can render two structurally different,
declarative RicePlate panel layouts without starting a second panel or
modifying your live desktop configuration:

```bash
ricebowl de recipes
ricebowl de start --nested --recipe classic
ricebowl de start --nested --recipe chrome
```

For offline authoring agents and mockup-to-rice experiments, the **read-only,
versioned panel component catalog** describes what the current native and
Waybar backends actually implement:

```bash
ricebowl de catalog --json
```

The versioned `catalog_version` (currently **3**) identifies the response format, while
`recipe.schema_versions` (currently **1, 2, 3, 4**) identifies supported recipe versions. Each
component has a known ID, real backend support level, fixed behavior and
keyboard-availability flag. Unsupported functionality is reported explicitly
instead of presenting an imaginary action or widget. This catalog never reads
private desktop state, invokes a model or changes a rice; it is the first
machine-readable Creator *discovery* contract, not the full Creator API.

The next read-only Creator building block validates one recipe and optionally
compares it with a bundled, imported or owner-private base recipe:

```bash
ricebowl de review --recipe classic --json
ricebowl de review --recipe /absolute/path/to/my-rice.json --compare chrome --json
```

`review_version: 1` describes a versioned JSON response (panel-only for v1–v3,
initial shell components for v4 and opt-in desktop icons for v5) with `ok`,
`applied: false`, a normalized `recipe`, a `summary`, and an optional
`comparison`. The summary includes an SHA-256 of the **normalized recipe
semantics** (not of the source file's bytes), native-unavailable widgets and
whether full widget support still requires Waybar. The comparison reports a
stable list of JSON Pointer paths and old/new values, including absent v1
metrics versus v2 metric defaults. Source file locations are not echoed.
Whitespace/key ordering changes do not affect the semantic fingerprint.

Exit status is `0` for a valid review, `2` for an invalid/inaccessible recipe
when `--json` is requested (a fixed, path-free `invalid_recipe` JSON response),
and `1` for rejected command flags or ordinary human-readable recipe errors.
The review never launches labwc, probes live hardware, writes a draft or
changes an active/next-login rice. It is **not** a rendered preview, image
comparison, complete RicePack validator or guarantee of functional parity.

#### Offline Creator component edits (experimental)

Agents can now read `ricebowl de catalog --json` and use the
`authoring.draft_edit` contract to build a **new panel draft** from actual
supported components. The contract publishes editable JSON Pointer paths,
limits, an explicit `set` operation and an example against `classic`.

For example, save this data as `/absolute/path/panel-edits.json` (an
owner-controlled regular `.json` file, not group/world writable):

```json
{
  "edit_version": 1,
  "operations": [
    {"op": "set", "path": "/panel/height", "value": 44},
    {"op": "set", "path": "/panel/sections/start", "value": ["launcher"]},
    {"op": "set", "path": "/panel/sections/center", "value": ["tasks"]}
  ]
}
```

Then validate and create a **new** private runtime-compatible JSON recipe:

```bash
ricebowl de recipe-init --base classic --id my-panel --name "My Panel" \
  --output /absolute/path/my-panel-base.json
ricebowl de draft-edit --recipe /absolute/path/my-panel-base.json \
  --edit /absolute/path/panel-edits.json \
  --output /absolute/path/my-panel-draft.json --json
ricebowl de review --recipe /absolute/path/my-panel-draft.json \
  --compare /absolute/path/my-panel-base.json --json
ricebowl de start --nested --recipe /absolute/path/my-panel-draft.json
```

The editor supports only validated panel property changes: name, panel edge,
height, schema-v1/v2 `start`/`center`/`end` widget lists, schema-v3 typed
`panel.layout` regions, hex colors and schema-v2/v3/v4 widget widths. Schema
v4 additionally offers explicit menu, wallpaper, design-token and responsive
editing paths.
IDs/schema versions are immutable; use `recipe-init` to create
a fresh identity or v2/v3/v4 template. A draft made directly from `classic` remains
identified as `classic` and can be previewed by absolute path, but cannot be
imported over the reserved built-in ID. At most 16 `set` operations and 16 KiB of
edit data are accepted; duplicate paths, unknown components, scripts, external
assets, unsupported actions and no-op edits are rejected. The destination
must not exist; the new file is created with mode `0600` without overwriting
the source. `--json` uses exit `0` for success, `2` for validation/creation
failure with a structured error code and (only for allowlisted properties)
a JSON Pointer diagnostic, and `1` for invalid flags. Errors never echo
private source/output paths, arbitrary edit values or executable content.

Neither the active session nor its next-login selection changes; actual visual
inspection is still a separate nested labwc step. These are reusable **panel
components only**. Menu, desktop, notification, settings and full RicePack
composition still need their respective native components and schemas.

#### Nested panel layouts (schema v3)

For AI-assisted building from an OS screenshot or generated mockup, schema v3
adds genuine **horizontal nested composition** to the panel recipe instead of
only rearranging a flat widget list. It is opt-in; existing v1/v2 recipes are
still accepted unchanged. Start with a private template:

```bash
ricebowl de recipe-init --schema-version 3 --base classic \
  --id y2k-panel --name "Y2K panel" --output "$HOME/y2k-panel.json"
ricebowl de catalog --json
```

Replace `panel.layout` in the new JSON with the example below (preserve the
generated `id`, `name`, `colors` and `panel.metrics`):

```json
"layout": {
  "start": [{"type": "group", "gap": 8, "children": [
    {"type": "widget", "id": "launcher"},
    {"type": "label", "text": "Y2K"},
    {"type": "gap", "width": 20},
    {"type": "widget", "id": "tasks"}
  ]}],
  "center": [],
  "end": [{"type": "widget", "id": "clock"}]
}
```

Run `ricebowl de review --recipe "$HOME/y2k-panel.json" --json` to validate
and inspect its normalized structure, then `ricebowl de start --nested
--recipe "$HOME/y2k-panel.json"` for Waybar or add `--panel native` for the
experimental native Rust panel. For agent edits, the `draft-edit` operation
`set /panel/layout/start` (or `center`/`end`) accepts a replacement list of
typed nodes; edits are validated, saved to a **new private file** and never
automatically applied.

Every node has an exact type and fields, with no CSS, commands, action strings
or remote assets. `widget` uses a unique existing ID from the catalog. `group`
has 1–6 children, gap 0–32 logical pixels and can nest at most three levels
total. A `gap` has width 4–64; a noninteractive `label` allows 1–24 safe ASCII
characters (`A–Z`, `a–z`, digits, spaces, `._:+-`). Limits are 24 typed nodes,
8 labels and 8 root nodes per panel region. Widget IDs cannot be duplicated,
and either a launcher or task list is required. The native panel currently
renders only launcher, tasks, clock, labels and spacing; network, audio,
battery and tray remain **Waybar-only**. Waybar uses GTK/CSS minimum widths,
so the visual pixel result can differ from Rust's fixed geometry. Grouping is
horizontal and panel-only, without flex/grid, responsiveness, generic content
containers, custom actions or AI running inside the desktop.

The shared real-backend example is
[`tests/fixtures/riceplate-nested-v3.json`](tests/fixtures/riceplate-nested-v3.json).
The native Rust tests assert geometry and click behavior for it, and the native
CI exercises its start inside headless labwc. A physical GPU/display and
multi-resolution visual QA still require separate acceptance.

#### Schema-v4 shell composition preview

For the first **multi-region** mockup-to-desktop authoring slice, use the v4
template rather than writing scripts or altering labwc/Waybar files yourself:

```bash
ricebowl de recipe-init --schema-version 4 --base classic \
  --id my-shell --name "My Shell" --output "$HOME/my-shell.json"
ricebowl de review --recipe "$HOME/my-shell.json" --json
ricebowl de start --nested --recipe "$HOME/my-shell.json"
```

Schema v4 retains v3 `panel.layout`, widths and colors, and adds four strictly
required, typed objects:

| Section | Runtime behavior | Bounds / limits |
| --- | --- | --- |
| `menu` | Generates a genuine **labwc root context menu** in an isolated private per-session config; action IDs map to fixed `fuzzel`, `foot`, `swaylock -f` or labwc Exit | 1–4 groups, 1–4 unique actions each, short ASCII labels; no commands in recipes |
| `desktop.wallpaper` | Selects an existing **original bundled** wallpaper for `swaybg` | Only catalog-listed wallpaper IDs; no arbitrary asset paths |
| `tokens` | `label_padding` changes native text geometry / Waybar CSS; `task_radius` changes native active task backgrounds / Waybar CSS | Integer 0–16 and 0–12 logical px respectively |
| `responsive` | `compact_layout` replaces the full panel layout at or below `compact_max_width` **live in native Rust** | Breakpoint 480–1440, same strict nested node limits; Waybar only supports explicit width-dependent offline generation |

All fields can be edited through the existing safe `de draft-edit` workflow,
with `/menu/title`, `/menu/groups`, `/desktop/wallpaper`, `/tokens/...` and
`/responsive/...` JSON Pointer paths. `de catalog --json` advertises exact
supported actions, wallpapers and backend limitations. The canonical example
[`tests/fixtures/riceplate-shell-v4.json`](tests/fixtures/riceplate-shell-v4.json)
is consumed by Python and the native Rust renderer's geometry tests and is
started in headless labwc CI. The existing login and XFCE defaults are never
replaced; temporary compositor menu files are removed on normal shutdown.

**Honest boundary:** This is a functional context menu and background, not
yet a visually configurable Windows-style Start menu. Original mockups cannot
be automatically converted into working control backends. Waybar does not
currently recompile its compact variant when the display is resized; the
native panel selects it during layout.

#### Schema-v5 native desktop icons preview

Schema v5 adds an optional *preview feature*, required when using that schema:
`desktop.icons`. Each entry contains only `label`, `action`, `x` and `y`.
There are 1–8 icons, labels contain 1–12 safe ASCII characters, coordinates
are bounded (`x`: 0–4096, `y`: 72–4096), and their 104×88 logical-pixel hit
areas must not overlap. Actions are fixed IDs: `applications`, `terminal`,
`lock` (mapped respectively to `fuzzel`, `foot`, `swaylock -f`). No arbitrary
commands or filesystem links are accepted.

```bash
ricebowl de recipe-init --schema-version 5 --base classic \
  --id my-desktop --name "My Desktop" --output "$HOME/my-desktop.json"
ricebowl de review --recipe "$HOME/my-desktop.json" --json
ricebowl de start --nested --panel native --recipe "$HOME/my-desktop.json"
```

The [shared fixture](tests/fixtures/riceplate-desktop-v5.json) shows the exact
JSON shape. `/desktop/icons` is available for `de draft-edit` and visible in
semantic `de review` comparisons. RicePlate draws each icon as a small
transparent Wayland Bottom-layer surface in its **existing process**; it does
not cover the desktop with a giant input window. The ordinary Waybar fallback
still renders the panel, menu and wallpaper but **does not show icons**. This
first slice has mouse clicks only: drag/reposition, keyboard focus, desktop
widgets, independent multi-output ownership and real-GPU acceptance remain
open. Native RicePlate now **reflows shortcuts within its selected logical
output** on mode/scale changes, preserving valid positions and parking icons
outside the output when no safe, non-overlapping hit area exists. This placement is not persisted;
fractional-scale visual quality and multi-monitor hotplug still need device
acceptance. Do not treat it as a finished desktop.

For **real** Wayland screenshots, install `grim` and explicitly invoke the
Creator capture command **inside the Wayland compositor you want to inspect**:

```bash
ricebowl de capture --output "$HOME/riceplate-actual.png" --json
ricebowl de visual-compare \
  --reference "$HOME/reference.png" --actual "$HOME/riceplate-actual.png" --json
```

`de capture` is a versioned, on-demand Creator endpoint (discoverable via
`de catalog --json`) which captures the **current** Wayland desktop, not a
newly launched or automatically isolated preview. Its screenshot can include
private windows; never share captures without reviewing them. It writes a
new owner-private PNG, refuses to overwrite files or symlinks and reports
actual dimensions and SHA-256. The legacy manual helper
`scripts/capture_wayland_panel.sh` also remains available. Comparison requires Pillow and
outputs JSON dimensions, mean RGB pixel error and the fraction of changed
pixels, not a made-up fidelity percentage. The native CI also captures a
**genuine headless labwc screenshot** in its downloadable preview artifact.
For reproducible screenshots **without an active Wayland login** (and without
touching any current desktop), install `labwc`, `wlr-randr`, `grim`, `swaybg`
and the experimental `riceplate-native` binary, then run as a normal user:

```bash
ricebowl de render --recipe classic \
  --output "$HOME/riceplate-isolated.png" \
  --width 1024 --height 768 --scale 1.0 --json
```

This starts a temporary headless compositor (Pixman), renders the requested
validated rice with native RicePlate and a bundled wallpaper, captures it,
and stops the session automatically. A new private PNG is published only on
success. `--scale` accepts 1, 1.25, 1.5 or 2. This is a rendering aid, **not**
proof of interactive correctness, visual similarity or real-GPU compatibility.
For schema-v5 rices the **optional region inspection** also locates the real
panel, remaining desktop and individual icon hit areas. It identifies clipped
icons or icons colliding with the panel; this describes geometry, not whether
the compositor successfully drew or activated each control. To obtain private
no-overwrite visual diagnostics:

```bash
ricebowl de visual-compare \
  --reference "$HOME/reference.png" \
  --actual "$HOME/riceplate-actual.png" \
  --recipe "$HOME/my-desktop.json" \
  --overlay "$HOME/compare-overlay.png" \
  --heatmap "$HOME/compare-heatmap.png" --json
```

The on-demand Creator CLI emits a versioned machine-readable result with
overall and per-region RGB errors plus a recipe fingerprint. The legacy
`scripts/compare_wayland_captures.py` standalone command remains available
and uses **the same comparison engine**. The overlay blends the original captures; the red
heatmap amplifies changed pixels. Both outputs are new, private `0600` files,
and the source images and recipe are never modified. Reference and actual
must have the same dimensions, be PNG and fit the 16-megapixel safety bound.

Native CI now captures the *same running shell* at 1024×768, 1366×768 and
1920×1080 plus a 1.25-scale case. The downloadable build artifact includes
the actual compositor PNGs and a `capture-manifest.json` with hashes, recipe,
scale and inspected geometry. A self-comparison in CI checks only geometry;
it is **not** a similarity score or a replacement for a manually approved
reference. Real-hardware mixed-DPI/multi-output behavior, font tolerance,
visual baseline sign-off and functional keyboard testing remain open.

#### Existing recipe creation, import/export and selection

Custom recipes use the strict JSON schema illustrated in
`macrice/de/resources/recipes/`. Supply an **absolute path** to an owner-only,
regular JSON file (`chmod 600 YOUR_FILE.json`). Recipes are limited to 64 KiB,
known panel widgets and six-digit colors. They cannot run commands, import CSS,
load assets or define new system actions. Temporary Waybar configurations are
created under the private `XDG_RUNTIME_DIR` and removed at session exit.

To create a rice without editing an installed/bundled recipe, choose your own
absolute JSON location (in an existing directory):

```bash
ricebowl de recipe-init --base chrome --id my-rice --name "My Rice" \
  --output "$HOME/my-rice.json"
ricebowl de recipes --recipe "$HOME/my-rice.json" --json
ricebowl de start --nested --recipe "$HOME/my-rice.json"
```

To exchange this **panel-only** recipe offline, import its JSON into the
user-private collection (without changing your active desktop), then use its
ID in either panel preview mode:

```bash
ricebowl de recipe-import --recipe "$HOME/my-rice.json"
ricebowl de recipes --json
ricebowl de start --nested --panel native --recipe my-rice
ricebowl de recipe-export --recipe my-rice --output "$HOME/my-rice-share.json"
```

Choose which validated panel recipe the **next opt-in Wayland login** uses,
without restarting or changing the current desktop:

```bash
ricebowl de recipe-select --recipe my-rice
ricebowl de recipe-current --json
ricebowl de recipe-restore   # One-level undo for the next login
```

To share the *appearance* of a validated RicePlate panel recipe with the
independently installed Taskotto process monitor, export its separate,
versioned and non-executable TOML contract:

```bash
ricebowl de taskotto-export --recipe classic --output "$HOME/taskotto-rice.toml"
RICEBOWL_TASKOTTO_RICEPACK="$HOME/taskotto-rice.toml" taskotto
```

This does not apply a desktop rice or require Taskotto to be installed for
export. Taskotto checks the file itself and allows a reversible in-app
preview. The v1 handoff carries only RicePlate's validated foreground,
background and active colors plus a supported base family when a known
wallpaper identifier exists; no arbitrary launcher, scripts, icons or
window-decorator settings are handed over. Existing destination files are
never overwritten, and exports are owner-only `0600`. Use a new filename for
each revision. This is a **manual opt-in bridge**, not automatic session-wide
application styling or a complete cross-app RicePack transaction.

The selection is an atomic `0600` preference inside the owner-private recipe
directory. Repeating the same selection preserves the last undo target; the
selection lock serializes parallel updates. The default is `classic`. A
corrupted selection or subsequently deleted recipe is reported and ignored
at login so the built-in classic panel can start. An **explicitly** requested
invalid recipe still fails before launching labwc. This selects only the
Wayland panel layout; full live desktop rice switching is not implemented.

Imports accept owner-controlled `0600` or `0644` regular `.json` files,
reject symlinks, unsafe directories, invalid schemas, reserved IDs and
duplicate names, and store the result privately in
`$XDG_CONFIG_HOME/ricebowl/recipes/` (or `~/.config/ricebowl/recipes/`).
Exported files are `0600` and existing files are never overwritten. Share
the exported JSON using your normal file-transfer tool; it contains no
executables or assets. This is **not** yet a complete, visual RicePack format.

The initializer creates a fully validated `0600` file through an atomic,
no-overwrite operation. Edit its `panel.sections`, `position`, `height` and
`colors` to map a reference/mockup to known widgets; validate again before
preview. No shell code from the recipe is executed. This is **manual assisted
authoring**, not automatic screenshot conversion or a full layout editor.

For mockup layouts that need different panel button widths, explicitly create
a **panel-only schema v2** recipe (v1 remains the default and is unchanged):

```bash
ricebowl de recipe-init --schema-version 2 --base classic \
  --id custom-widths --name "Custom widths" --output "$HOME/custom-widths.json"
```

Edit `panel.metrics` in that JSON file, for example:

```json
"metrics": {"launcher_width": 120, "task_width": 196, "clock_width": 80}
```

The required integer dimensions are in logical pixels: launcher **64–256**,
per-task **96–256**, clock **64–256**. Unknown fields, missing dimensions,
booleans and out-of-range values are rejected. Native RicePlate uses these
widths for actual drawing and click areas; the Waybar preview translates them
to CSS minimum widths, so long text/font metrics can yield a wider fallback
widget. This is **not** a general RicePack v2 or automated mockup importer.

This demonstrates structural composition through a shared recipe contract;
it does **not** mean RicePlate's Rust layer-shell renderer, arbitrary mockup
conversion or all seven native profiles are implemented yet.

### Native RicePlate layer-shell experiment (developers only)

The GitHub Actions **Native RicePlate prototype** workflow now attaches a
14-day downloadable `riceplate-native-preview-<commit>` build artifact for
each Rust/workflow change. Its folder contains the Ubuntu 24.04 x86_64
experimental binary, the exact Cargo dependency resolution used by CI,
`BUILDINFO.txt` and `SHA256SUMS`. Verify after downloading:

```bash
cd riceplate-native-preview
sha256sum -c SHA256SUMS
chmod +x riceplate-native  # GitHub ZIP download may discard executable bits
./riceplate-native --version
```

This is a short-lived **QA artifact**, not a signed release, portable Linux
installer, or complete RiceBowl session. Use the existing `--nested` preview
instructions and do not replace your login desktop with the binary.

The repository additionally includes `components/riceplate-wayland`, an
event-driven Rust/Smithay Client Toolkit layer-shell prototype. It paints a
simple labelled surface with a fixed `Apps` button that launches the installed
Fuzzel command without passing any recipe data to a shell. When labwc offers
`wlr-foreign-toplevel-management`, the prototype also displays live window
titles and supports click-to-activate via the Wayland seat; clicking an active
single-window task requests minimization. Windows with the same nonempty
Wayland app ID share a labelled task group with a visible count; clicking the
active group cycles through its windows. Windows with unknown IDs remain
separate. The window list is deliberately bounded; when there are more groups
than can fit, the native taskbar exposes previous/next page controls to reach
remaining groups, automatically reveals the active group, and keeps input hit
areas aligned with the visible labels. Only visible entries accept clicks; if the
protocol is missing the panel keeps its launcher and reports the limitation.
It is **not** a replacement taskbar: it still lacks a calendar
popover, tray, keyboard task navigation, notification handling or multi-output ownership. Do not start it automatically
alongside Waybar.

The native prototype understands two *bundled* schema-v1 RicePlate recipes:
`classic` (left-aligned bottom taskbar) and `chrome` (centered task list and
taller shelf). Both are parsed from the same recipe JSON files as the
temporary Waybar adapter, with strict schema/widget/color checks. It also
accepts owner-private absolute JSON recipe files (regular files, permissions
`0600`, no final symlinks, maximum 64 KiB). The three implemented widgets
(launcher, tasks and local-time clock) may be arranged in the start, center or
end section in any order, including custom top panels; their hit areas follow
the rendered geometry and shrink on narrow displays. The clock is updated
on minute boundaries through the Wayland event loop without a 1 Hz timer.
Custom schema-v2/v3 panel recipes additionally support strict per-widget widths;
schema-v3 adds validated nested groups, static text and spacers with real native
geometry/hit areas; schema-v1 recipes retain their original native dimensions.
Other indicators and the tray still need functional Rust backends. The native
renderer deliberately omits unavailable widgets without displaying pretend
buttons. Custom recipes cannot contain commands or arbitrary executable code.

In a *disposable/nested* labwc session, developers with Rust 1.86+ can try:

```bash
cargo run --manifest-path components/riceplate-wayland/Cargo.toml -- --recipe chrome
```

To exercise RicePlate as the **only** panel within RiceBowl's isolated labwc
session, first install the experimental binary into your user-local PATH:

```bash
cargo install --path components/riceplate-wayland
command -v riceplate-native
ricebowl de start --nested --panel native --recipe chrome
```

The experimental Rust crate does not yet ship a committed `Cargo.lock`; a
reproducible locked native-binary package remains a 1.0 release gate.

This is an explicit developer opt-in, **not** the login-manager default. The
temporary Waybar dependency remains installed and available for recovery: if
RicePlate crashes or cannot start after session preflight, the session logs
the problem and restores Waybar automatically. A deliberate clean panel exit
or an external session shutdown does not restart Waybar. If the native binary
is absent before startup, the CLI refuses the request without touching the
current desktop. The native panel deliberately omits system widgets not yet
implemented; use ordinary `ricebowl de start --nested` for a fuller preview.

To preview a private recipe without changing any desktop settings:

```bash
recipe_copy=$(mktemp --suffix=.json)
cp macrice/de/resources/recipes/classic.json "$recipe_copy"
chmod 600 "$recipe_copy"
cargo run --manifest-path components/riceplate-wayland/Cargo.toml -- --recipe "$recipe_copy"
rm -- "$recipe_copy"
```

The dedicated CI workflow compiles it and checks that both bundled recipes and
a private custom recipe remain alive on a real headless labwc compositor.
The Python session tests additionally verify native launch, crash fallback,
D-Bus restart argument preservation and intentional shutdown behavior.
Nothing changes the XFCE path, Waybar default or the optional session package.

## First-session controls

| Key | Action |
| --- | --- |
| Super + Return | Open Foot terminal |
| Super + Space | Open Fuzzel launcher |
| Super + L | Lock with Swaylock |
| Alt + F4 | Close the focused window (labwc default) |
| Desktop right-click | labwc root menu, including Exit |

Until RicePlate is native, Waybar provides the taskbar, clock, tray and
available system indicators. Only one panel is started. A terminated panel
requests a clean labwc exit instead of leaving the user on an empty desktop.
The temporary shell does not use XFCE's panel or XFDesktop.

## Session boundaries and recovery

An on-demand, read-only process snapshot can now include recognized labwc,
Waybar, native RicePlate and associated upstream services alongside XFCE:

```bash
ricebowl performance desktop --samples 3 --json
```

The report distinguishes XFCE and Wayland PSS totals, marks unreadable
measurements unknown and warns if both Waybar and native RicePlate are seen.
It includes **all matching user-owned processes**, potentially across nested
sessions, so it is not by itself evidence of one session's idle RAM or CPU.
Use isolated login/hardware acceptance for the 1.0 benchmark.

- Labwc reads **only** the bundled `macrice/de/resources/labwc` configuration
  through `--config-dir`. The user's own labwc setup is left untouched.
- The session launcher rejects root execution, missing core dependencies,
  unsafe runtime-directory permissions and an accidental non-nested launch
  inside a desktop.
- labwc 0.7.1 needs an explicit D-Bus activation-environment import; the
  session's autostart performs it for primary sessions. Nested instances
  never import shared activation variables.
- The preview starts/stops its own `ricebowl-session.target`; it does not
  stop `graphical-session.target` used by other sessions.
- The temporary shell supervises its Waybar and optional helper processes.
  Its exit requests termination only of the labwc instance it belongs to.
- The login package can be uninstalled with
  `sudo apt remove ricebowl-wayland-session`. Your user-local RiceBowl
  installation, XFCE session and personal files remain.

If the Wayland session fails to start, the display manager should return to
its greeter. Select XFCE. If the greeter itself is unavailable, use a text
console (`Ctrl+Alt+F3`) to remove the optional session package, **not** the
XFCE desktop packages. Review the user's journal and display-manager logs.

## Physical acceptance checklist (not yet signed off)

- [ ] Login manager lists both RiceBowl Wayland and XFCE.
- [ ] Login, logout, repeated login and crash recovery work.
- [ ] Waybar taskbar, launchers, focus/Alt-Tab, multi-monitor and hotplug.
- [ ] Clipboard between native Wayland and XWayland apps.
- [ ] Flatpak/portal file picker, screenshot, OBS/PipeWire screencast.
- [ ] Polkit authentication (with and without an installed agent).
- [ ] Swaylock, idle lock, suspend/resume, lid and power-button behavior.
- [ ] Input layout/IME, touchpad/tablet, HiDPI scaling and accessibility.
- [ ] Systemd and D-Bus activation variables remain correct across logout
      and returning to XFCE.
- [ ] Real baseline PSS/RSS, idle CPU and login duration recorded on Mint.

These are genuine device acceptance gates; CI cannot replace them. If they
fail, the XFCE session stays the supported default.

[Main DE roadmap](RICEBOWL_DE_ROADMAP.md) · [Current XFCE boundaries](XFCE_RESOURCE_BOUNDARIES.md)
