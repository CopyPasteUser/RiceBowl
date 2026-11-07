//! Native RicePlate experiment: an input-capable, idle event-driven layer surface.
//! No session takeover: launch only inside an already running Wayland session.

use std::{error::Error, process::Command, time::Duration};

use chrono::{Datelike, Local, Timelike};
use font8x8::{UnicodeFonts, BASIC_FONTS};
mod calendar;
mod desktop_layout;
mod icon_positions;
mod native_menu;
mod recipe;
mod task_groups;
mod task_navigation;
use native_menu::{Hit as MenuHit, MenuState};
use calendar::{CalendarState, Hit as CalendarHit};
use recipe::{Hit, PanelStyle, Widget};
use task_navigation::Target as KeyboardTarget;
use smithay_client_toolkit::{
    compositor::{CompositorHandler, CompositorState, FrameCallbackData},
    delegate_registry,
    output::{OutputHandler, OutputState},
    reexports::{calloop::EventLoop, calloop_wayland_source::WaylandSource},
    registry::{ProvidesRegistryState, RegistryState},
    registry_handlers,
    seat::{
        keyboard::{KeyEvent, KeyboardHandler, Keysym, Modifiers, RawModifiers},
        pointer::{PointerEvent, PointerEventKind, PointerHandler},
        Capability, SeatHandler, SeatState,
    },
    shell::{
        wlr_layer::{
            Anchor, KeyboardInteractivity, Layer, LayerShell, LayerShellHandler, LayerSurface,
            LayerSurfaceConfigure,
        },
        WaylandSurface,
    },
    shm::{slot::SlotPool, Shm, ShmHandler},
};
use task_groups::{TaskGroup, WindowInfo};
use wayland_client::{
    globals::registry_queue_init,
    protocol::{wl_keyboard, wl_output, wl_pointer, wl_seat, wl_shm, wl_surface},
    Connection, Dispatch, QueueHandle,
};
use wayland_protocols_wlr::foreign_toplevel::v1::client::{
    zwlr_foreign_toplevel_handle_v1::{self, ZwlrForeignToplevelHandleV1},
    zwlr_foreign_toplevel_manager_v1::{self, ZwlrForeignToplevelManagerV1},
};

const MAX_WIDTH: u32 = 16384;
const MAX_HEIGHT: u32 = 256;
const MAX_OUTPUT_PANELS: usize = 8;
const BTN_LEFT: u32 = 0x110;

fn clock_now() -> String {
    Local::now().format("%H:%M").to_string()
}

fn next_clock_timeout() -> Duration {
    let now = Local::now();
    let milliseconds =
        u64::from(60 - now.second()) * 1000 - u64::from(now.nanosecond() / 1_000_000);
    Duration::from_millis(milliseconds.max(50))
}

fn main() -> Result<(), Box<dyn Error>> {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    // Explicit test entrypoint for CI and packagers; no Wayland connection.
    if matches!(arguments.as_slice(), [arg] if arg == "--version") {
        println!("riceplate-native 0.1.0 (experimental)");
        return Ok(());
    }
    if matches!(arguments.as_slice(), [arg] if arg == "--help") {
        println!("Usage: riceplate-native [--recipe classic|chrome|/absolute/private.json [--preview-menu|--preview-calendar]]");
        return Ok(());
    }
    let (recipe_name, preview_menu, preview_calendar) = match arguments.as_slice() {
        [] => ("classic", false, false),
        [flag, recipe] if flag == "--recipe" => (recipe.as_str(), false, false),
        [flag, recipe, preview] if flag == "--recipe" && preview == "--preview-menu" =>
            (recipe.as_str(), true, false),
        [flag, recipe, preview] if flag == "--recipe" && preview == "--preview-calendar" =>
            (recipe.as_str(), false, true),
        _ => {
            return Err(
                "Usage: riceplate-native [--recipe classic|chrome|/absolute/private.json [--preview-menu|--preview-calendar]]".into(),
            )
        }
    };
    let mut recipe = recipe::load(recipe_name)?;
    if let Err(error) = icon_positions::restore(&mut recipe) {
        eprintln!("RicePlate: ignored invalid saved desktop icon positions: {error}");
    }
    if preview_menu && recipe.menu.is_none() {
        return Err("Native menu preview requires schema v4/v5".into());
    }
    let clock_present = recipe.sections.iter().flatten().any(|widget| *widget == Widget::Clock)
        || recipe.compact.as_ref().is_some_and(|(_, sections)|
            sections.iter().flatten().any(|widget| *widget == Widget::Clock));
    if preview_calendar && !clock_present {
        return Err("Calendar preview requires a native clock widget".into());
    }
    let conn = Connection::connect_to_env()?;
    let (globals, event_queue) = registry_queue_init(&conn)?;
    let qh = event_queue.handle();
    let mut event_loop: EventLoop<RicePlate> = EventLoop::try_new()?;
    WaylandSource::new(conn.clone(), event_queue).insert(event_loop.handle())?;
    let compositor = CompositorState::bind(&globals, &qh)?;
    let layer_shell = LayerShell::bind(&globals, &qh)?;
    let shm = Shm::bind(&globals, &qh)?;
    let toplevel_manager: Option<ZwlrForeignToplevelManagerV1> = globals.bind(&qh, 1..=3, ()).ok();
    if toplevel_manager.is_none() {
        eprintln!("RicePlate: compositor lacks wlr-foreign-toplevel-management; taskbar disabled");
    }
    let layer = layer_shell.create_layer_surface(
        &qh,
        compositor.create_surface(&qh),
        Layer::Top,
        Some("riceplate-preview"),
        None,
    );
    let edge = if recipe.top {
        Anchor::TOP
    } else {
        Anchor::BOTTOM
    };
    layer.set_anchor(edge | Anchor::LEFT | Anchor::RIGHT);
    layer.set_size(0, recipe.height);
    layer.set_exclusive_zone(recipe.height as i32);
    layer.set_keyboard_interactivity(KeyboardInteractivity::OnDemand);
    layer.commit();

    // One small Bottom-layer surface per icon: transparent desktop space is
    // never covered by a full-screen input-catching window.
    let mut icon_layers = Vec::new();
    for icon in &recipe.desktop_icons {
        let surface = layer_shell.create_layer_surface(
            &qh,
            compositor.create_surface(&qh),
            Layer::Bottom,
            Some("riceplate-desktop-icon"),
            None,
        );
        surface.set_anchor(Anchor::TOP | Anchor::LEFT);
        surface.set_size(recipe::ICON_WIDTH, recipe::ICON_HEIGHT);
        surface.set_margin(icon.y as i32, 0, 0, icon.x as i32);
        surface.set_exclusive_zone(-1);
        surface.set_keyboard_interactivity(KeyboardInteractivity::OnDemand);
        surface.commit();
        icon_layers.push(IconLayer {
            surface,
            pool: None,
            configured: false,
            output: None,
            placed: Some((icon.x, icon.y)),
        });
    }

    // The native start menu shares the validated schema-v4/v5 recipe and the
    // same process as the panel. When closed it is parked beyond the output,
    // not destroyed (a null buffer would invalidate its layer-shell role).
    let menu_layer = recipe.menu.as_ref().map(|_| {
        let surface = layer_shell.create_layer_surface(
            &qh,
            compositor.create_surface(&qh),
            Layer::Top,
            Some("riceplate-native-menu"),
            None,
        );
        surface.set_anchor(
            (if recipe.top {
                Anchor::TOP
            } else {
                Anchor::BOTTOM
            }) | Anchor::LEFT,
        );
        surface.set_size(native_menu::WIDTH, native_menu::HEIGHT);
        surface.set_margin(
            if recipe.top { recipe.height as i32 } else { 0 },
            0,
            if recipe.top { 0 } else { recipe.height as i32 },
            MAX_WIDTH as i32,
        );
        surface.set_exclusive_zone(-1);
        surface.set_keyboard_interactivity(KeyboardInteractivity::None);
        surface.commit();
        MenuLayer { surface, pool: None, configured: false, output: None }
    });
    let preview_secondary_menu = preview_menu
        && std::env::var("RICEBOWL_DE_NESTED").as_deref() == Ok("1")
        && std::env::var("RICEBOWL_DE_MENU_OUTPUT").as_deref() == Ok("secondary");

    // One owner-private calendar popup, idle and parked until the clock is used.
    let calendar_layer = clock_present.then(|| {
        let surface = layer_shell.create_layer_surface(
            &qh, compositor.create_surface(&qh), Layer::Top,
            Some("riceplate-native-calendar"), None,
        );
        surface.set_anchor((if recipe.top { Anchor::TOP } else { Anchor::BOTTOM }) | Anchor::RIGHT);
        surface.set_size(calendar::WIDTH, calendar::HEIGHT);
        surface.set_margin(
            if recipe.top { recipe.height as i32 } else { 0 },
            MAX_WIDTH as i32, // Park beyond the visible output while closed.
            if recipe.top { 0 } else { recipe.height as i32 },
            0,
        );
        surface.set_exclusive_zone(-1);
        surface.set_keyboard_interactivity(KeyboardInteractivity::None);
        surface.commit();
        CalendarLayer { surface, pool: None, configured: false, output: None }
    });
    let preview_secondary_calendar = preview_calendar
        && std::env::var("RICEBOWL_DE_NESTED").as_deref() == Ok("1")
        && std::env::var("RICEBOWL_DE_CALENDAR_OUTPUT").as_deref() == Ok("secondary");

    let mut app = RicePlate {
        compositor,
        layer_shell,
        registry: RegistryState::new(&globals),
        outputs: OutputState::new(&globals, &qh),
        seats: SeatState::new(&globals, &qh),
        shm,
        layer,
        mirrors: Vec::new(),
        icon_layers,
        menu_layer,
        menu_mirrors: Vec::new(),
        active_menu: None,
        preview_secondary_menu,
        calendar_layer,
        calendar_mirrors: Vec::new(),
        active_calendar: None,
        preview_secondary_calendar,
        menu_state: MenuState::default(),
        calendar_state: CalendarState::new(Local::now().date_naive()),
        calendar_focused: false,
        recipe,
        clock: clock_now(),
        pointer: None,
        keyboard: None,
        focused_icon: None,
        focused_panel: None,
        focused_target: None,
        icon_drag: None,
        icon_position_dirty: false,
        menu_focused: false,
        primary_seat: None,
        primary_output: None,
        primary_output_seen: false,
        toplevel_manager,
        tasks: Vec::new(),
        task_offset: 0,
        pool: None,
        width: 0,
        height: 0,
        configured: false,
        closed: false,
        frame_pending: false,
        needs_redraw: false,
    };
    if preview_menu && !preview_secondary_menu { app.set_menu_visible(true, &qh); }
    if preview_calendar && !preview_secondary_calendar {
        app.set_calendar_visible(true, &qh);
    }
    while !app.closed {
        // Calloop sleeps on Wayland's fd and wakes at the next minute,
        // so the clock updates without any resident 1 Hz poll/frame loop.
        event_loop.dispatch(Some(next_clock_timeout()), &mut app)?;
        let current = clock_now();
        if app.clock != current {
            app.clock = current;
            app.request_redraw(&qh);
        }
        let today = Local::now().date_naive();
        if app.calendar_state.today != today {
            app.calendar_state.today = today;
            if app.calendar_state.visible { app.redraw_calendar(&qh); }
        }
    }
    app.save_icon_positions();
    Ok(())
}

struct Task {
    handle: ZwlrForeignToplevelHandleV1,
    title: String,
    app_id: String,
    active: bool,
    ready: bool,
}

struct IconLayer {
    surface: LayerSurface,
    pool: Option<SlotPool>,
    configured: bool,
    output: Option<wl_output::WlOutput>,
    placed: Option<(u32, u32)>,
}

struct IconDrag {
    index: usize,
    anchor: (f64, f64),
    started: (u32, u32),
    moved: bool,
}

struct MenuLayer {
    surface: LayerSurface,
    pool: Option<SlotPool>,
    configured: bool,
    output: Option<wl_output::WlOutput>,
}

struct CalendarLayer {
    surface: LayerSurface,
    pool: Option<SlotPool>,
    configured: bool,
    output: Option<wl_output::WlOutput>,
}

struct PanelMirror {
    output: wl_output::WlOutput,
    surface: LayerSurface,
    pool: Option<SlotPool>,
    width: u32,
    height: u32,
    configured: bool,
    frame_pending: bool,
    needs_redraw: bool,
    task_offset: usize,
}

struct RicePlate {
    compositor: CompositorState,
    layer_shell: LayerShell,
    registry: RegistryState,
    outputs: OutputState,
    seats: SeatState,
    shm: Shm,
    layer: LayerSurface,
    mirrors: Vec<PanelMirror>,
    icon_layers: Vec<IconLayer>,
    menu_layer: Option<MenuLayer>,
    menu_mirrors: Vec<MenuLayer>,
    active_menu: Option<wl_surface::WlSurface>,
    preview_secondary_menu: bool,
    calendar_layer: Option<CalendarLayer>,
    calendar_mirrors: Vec<CalendarLayer>,
    active_calendar: Option<wl_surface::WlSurface>,
    preview_secondary_calendar: bool,
    menu_state: MenuState,
    calendar_state: CalendarState,
    calendar_focused: bool,
    recipe: PanelStyle,
    clock: String,
    pointer: Option<wl_pointer::WlPointer>,
    keyboard: Option<wl_keyboard::WlKeyboard>,
    focused_icon: Option<usize>,
    focused_panel: Option<wl_surface::WlSurface>,
    focused_target: Option<KeyboardTarget>,
    icon_drag: Option<IconDrag>,
    icon_position_dirty: bool,
    menu_focused: bool,
    primary_seat: Option<wl_seat::WlSeat>,
    primary_output: Option<wl_output::WlOutput>,
    primary_output_seen: bool,
    toplevel_manager: Option<ZwlrForeignToplevelManagerV1>,
    tasks: Vec<Task>,
    task_offset: usize,
    pool: Option<SlotPool>,
    width: u32,
    height: u32,
    configured: bool,
    closed: bool,
    frame_pending: bool,
    needs_redraw: bool,
}

impl RicePlate {
    fn panel_geometry(&self, surface: &wl_surface::WlSurface)
        -> Option<(Option<usize>, u32, usize)>
    {
        if surface == self.layer.wl_surface() {
            return Some((None, self.width, self.task_offset));
        }
        self.mirrors.iter().enumerate()
            .find(|(_, mirror)| mirror.surface.wl_surface() == surface)
            .map(|(index, mirror)| (Some(index), mirror.width, mirror.task_offset))
    }

    fn activate_launcher(&mut self, mirror: Option<usize>, qh: &QueueHandle<Self>) {
        if self.menu_layer.is_some() {
            self.toggle_menu_for_panel(mirror, qh);
        } else {
            self.activate_action("applications", qh);
        }
    }

    fn activate_group(&mut self, index: usize) {
        let groups = self.grouped_tasks();
        if let Some(group) = groups.get(index) {
            let active_index = group.members.iter().copied()
                .find(|&member| self.tasks[member].active);
            let (target, minimize) = task_groups::click_target(group, active_index);
            if minimize {
                self.tasks[target].handle.set_minimized();
            } else if let Some(seat) = self.primary_seat.as_ref() {
                self.tasks[target].handle.activate(seat);
            }
        }
    }

    fn handle_panel_key(&mut self, key: Keysym, qh: &QueueHandle<Self>) -> bool {
        let Some(surface) = self.focused_panel.as_ref() else { return false; };
        let Some((mirror, width, offset)) = self.panel_geometry(surface) else { return false; };
        let groups = self.grouped_tasks();
        let count = groups.len();
        match key {
            Keysym::Right | Keysym::Tab | Keysym::Down
            | Keysym::Left | Keysym::ISO_Left_Tab | Keysym::Up => {
                let delta = if matches!(key, Keysym::Left | Keysym::ISO_Left_Tab | Keysym::Up) {
                    -1
                } else { 1 };
                self.focused_target = task_navigation::advance(
                    &self.recipe, width, count, self.focused_target, delta,
                );
                let next = task_navigation::reveal(
                    &self.recipe, width, count, offset, self.focused_target,
                );
                if let Some(index) = mirror {
                    self.mirrors[index].task_offset = next;
                } else {
                    self.task_offset = next;
                }
                self.request_redraw(qh);
            }
            Keysym::Return | Keysym::KP_Enter | Keysym::space => {
                match self.focused_target {
                    Some(KeyboardTarget::Launcher) => self.activate_launcher(mirror, qh),
                    Some(KeyboardTarget::Task(index)) => self.activate_group(index),
                    None => {}
                }
            }
            Keysym::Escape => {
                self.focused_target = None;
                self.request_redraw(qh);
            }
            _ => return false,
        }
        true
    }

    fn save_icon_positions(&mut self) {
        if !self.icon_position_dirty {
            return;
        }
        if let Err(error) = icon_positions::save(&self.recipe) {
            eprintln!("RicePlate: cannot persist desktop icon positions: {error}");
            return;
        }
        self.icon_position_dirty = false;
    }

    fn sync_mirrors(&mut self, qh: &QueueHandle<Self>) {
        // An output can disappear between wl_surface.leave and its eventual
        // enter on another output. Never leave the remaining display blank
        // while the compositor is deciding where the unbound primary goes.
        // Before the very first enter, defer to the compositor's initial
        // placement to avoid redundant startup panels.
        if !self.primary_output_seen { return; }
        let outputs: Vec<_> = self.outputs.outputs()
            .filter(|output| self.primary_output.as_ref() != Some(output))
            .filter(|output| self.logical_output_size(output).is_some())
            .take(MAX_OUTPUT_PANELS).collect();
        let old_count = self.mirrors.len();
        self.mirrors.retain(|mirror| outputs.contains(&mirror.output));
        if old_count != self.mirrors.len() {
            eprintln!("RicePlate: secondary panels removed: {} -> {}", old_count, self.mirrors.len());
        }
        for output in outputs.iter().cloned() {
            if self.mirrors.iter().any(|mirror| mirror.output == output) { continue; }
            eprintln!("RicePlate: creating secondary panel on {output:?}");
            let surface = self.layer_shell.create_layer_surface(
                qh, self.compositor.create_surface(qh), Layer::Top,
                Some("riceplate-output-panel"), Some(&output),
            );
            let edge = if self.recipe.top { Anchor::TOP } else { Anchor::BOTTOM };
            surface.set_anchor(edge | Anchor::LEFT | Anchor::RIGHT);
            surface.set_size(0, self.recipe.height);
            surface.set_exclusive_zone(self.recipe.height as i32);
            surface.set_keyboard_interactivity(KeyboardInteractivity::OnDemand);
            surface.commit();
            self.mirrors.push(PanelMirror {
                output, surface, pool: None, width: 0, height: 0,
                configured: false, frame_pending: false, needs_redraw: false,
                task_offset: 0,
            });
        }
        self.menu_mirrors.retain(|menu|
            menu.output.as_ref().is_some_and(|output| outputs.contains(output)));
        if self.menu_layer.is_some() {
            for output in &outputs {
                if self.menu_mirrors.iter().any(|menu|
                    menu.output.as_ref() == Some(output)) { continue; }
                let surface = self.layer_shell.create_layer_surface(
                    qh, self.compositor.create_surface(qh), Layer::Top,
                    Some("riceplate-output-menu"), Some(output),
                );
                surface.set_anchor((if self.recipe.top { Anchor::TOP } else { Anchor::BOTTOM })
                    | Anchor::LEFT);
                surface.set_size(native_menu::WIDTH, native_menu::HEIGHT);
                surface.set_margin(
                    if self.recipe.top { self.recipe.height as i32 } else { 0 },
                    0,
                    if self.recipe.top { 0 } else { self.recipe.height as i32 },
                    MAX_WIDTH as i32,
                );
                surface.set_exclusive_zone(-1);
                surface.set_keyboard_interactivity(KeyboardInteractivity::None);
                surface.commit();
                self.menu_mirrors.push(MenuLayer {
                    surface, pool: None, configured: false, output: Some(output.clone()),
                });
            }
        }
        if self.active_menu.as_ref().is_some_and(|surface|
            self.menu_layer.as_ref().is_none_or(|root| root.surface.wl_surface() != surface)
            && !self.menu_mirrors.iter().any(|menu|
                menu.surface.wl_surface() == surface)) {
            self.active_menu = None;
            self.menu_state.close();
            self.menu_focused = false;
        }
        if self.preview_secondary_menu {
            if let Some(surface) = self.menu_mirrors.first()
                .map(|menu| menu.surface.wl_surface().clone()) {
                self.show_menu_at(surface, qh);
                self.preview_secondary_menu = false;
            }
        }
        self.calendar_mirrors.retain(|calendar|
            calendar.output.as_ref().is_some_and(|output| outputs.contains(output)));
        if self.calendar_layer.is_some() {
            for output in &outputs {
                if self.calendar_mirrors.iter().any(|calendar|
                    calendar.output.as_ref() == Some(output)) { continue; }
                let surface = self.layer_shell.create_layer_surface(
                    qh, self.compositor.create_surface(qh), Layer::Top,
                    Some("riceplate-output-calendar"), Some(output),
                );
                surface.set_anchor((if self.recipe.top { Anchor::TOP } else { Anchor::BOTTOM })
                    | Anchor::RIGHT);
                surface.set_size(calendar::WIDTH, calendar::HEIGHT);
                surface.set_margin(
                    if self.recipe.top { self.recipe.height as i32 } else { 0 },
                    MAX_WIDTH as i32,
                    if self.recipe.top { 0 } else { self.recipe.height as i32 },
                    0,
                );
                surface.set_exclusive_zone(-1);
                surface.set_keyboard_interactivity(KeyboardInteractivity::None);
                surface.commit();
                self.calendar_mirrors.push(CalendarLayer {
                    surface, pool: None, configured: false, output: Some(output.clone()),
                });
            }
        }
        if self.active_calendar.as_ref().is_some_and(|surface|
            self.calendar_layer.as_ref().is_none_or(|root|
                root.surface.wl_surface() != surface)
            && !self.calendar_mirrors.iter().any(|calendar|
                calendar.surface.wl_surface() == surface)) {
            self.active_calendar = None;
            self.calendar_state.visible = false;
            self.calendar_focused = false;
        }
        if self.preview_secondary_calendar {
            if let Some(surface) = self.calendar_mirrors.first()
                .map(|calendar| calendar.surface.wl_surface().clone()) {
                self.show_calendar_at(surface, qh);
                self.preview_secondary_calendar = false;
            }
        }
        if self.focused_panel.as_ref().is_some_and(|surface|
            self.panel_geometry(surface).is_none()) {
            self.focused_panel = None;
            self.focused_target = None;
        }
    }

    fn redraw_mirror(&mut self, index: usize, qh: &QueueHandle<Self>) {
        let groups = self.grouped_tasks();
        let selected = if self.focused_panel.as_ref()
            == self.mirrors.get(index).map(|mirror| mirror.surface.wl_surface()) {
            self.focused_target
        } else { None };
        let Some(mirror) = self.mirrors.get_mut(index) else { return };
        if !mirror.configured || mirror.width == 0 || mirror.height == 0 { return; }
        let surface = mirror.surface.wl_surface();
        let Some(pool) = mirror.pool.as_mut() else { return };
        let (buffer, canvas) = match pool.create_buffer(
            mirror.width as i32, mirror.height as i32,
            (mirror.width * 4) as i32, wl_shm::Format::Argb8888,
        ) {
            Ok(value) => value,
            Err(error) => {
                eprintln!("RicePlate: deferring busy output panel buffer: {error}");
                surface.frame(qh, FrameCallbackData(surface.clone()));
                mirror.frame_pending = true;
                mirror.surface.commit();
                return;
            }
        };
        paint_panel(canvas, mirror.width, mirror.height, &self.recipe, &groups,
                    &self.clock, mirror.task_offset, selected);
        surface.damage_buffer(0, 0, mirror.width as i32, mirror.height as i32);
        if let Err(error) = buffer.attach_to(surface) {
            eprintln!("RicePlate: cannot attach output panel: {error}");
            return;
        }
        surface.frame(qh, FrameCallbackData(surface.clone()));
        mirror.frame_pending = true;
        mirror.needs_redraw = false;
        mirror.surface.commit();
    }

    fn set_menu_visible(&mut self, visible: bool, qh: &QueueHandle<Self>) {
        if visible {
            if let Some(surface) = self.menu_layer.as_ref()
                .map(|menu| menu.surface.wl_surface().clone()) {
                self.show_menu_at(surface, qh);
            }
            return;
        }
        self.menu_state.close();
        self.menu_focused = false;
        self.active_menu = None;
        for layer in self.menu_layer.iter().chain(self.menu_mirrors.iter()) {
            layer.surface.set_keyboard_interactivity(KeyboardInteractivity::None);
            layer.surface.set_margin(
                if self.recipe.top { self.recipe.height as i32 } else { 0 },
                0,
                if self.recipe.top { 0 } else { self.recipe.height as i32 },
                MAX_WIDTH as i32,
            );
            layer.surface.commit();
        }
    }

    fn show_menu_at(&mut self, surface: wl_surface::WlSurface, qh: &QueueHandle<Self>) {
        if !self.menu_layer.iter().chain(self.menu_mirrors.iter()).any(|menu|
            menu.surface.wl_surface() == &surface) { return; }
        if self.calendar_state.visible { self.set_calendar_visible(false, qh); }
        self.menu_state.open();
        self.menu_focused = false;
        self.active_menu = Some(surface.clone());
        for layer in self.menu_layer.iter().chain(self.menu_mirrors.iter()) {
            let active = layer.surface.wl_surface() == &surface;
            layer.surface.set_keyboard_interactivity(if active {
                KeyboardInteractivity::OnDemand
            } else {
                KeyboardInteractivity::None
            });
            layer.surface.set_margin(
                if self.recipe.top { self.recipe.height as i32 } else { 0 },
                0,
                if self.recipe.top { 0 } else { self.recipe.height as i32 },
                if active { 0 } else { MAX_WIDTH as i32 },
            );
            layer.surface.commit();
        }
        self.redraw_menu(qh);
    }

    fn toggle_menu_for_panel(&mut self, mirror: Option<usize>, qh: &QueueHandle<Self>) {
        let target = match mirror {
            Some(index) => self.mirrors.get(index).and_then(|panel|
                self.menu_mirrors.iter().find(|menu|
                    menu.output.as_ref() == Some(&panel.output)))
                .map(|menu| menu.surface.wl_surface().clone()),
            None => self.menu_layer.as_ref()
                .map(|menu| menu.surface.wl_surface().clone()),
        };
        let Some(target) = target else { return; };
        if self.menu_state.visible && self.active_menu.as_ref() == Some(&target) {
            self.set_menu_visible(false, qh);
        } else {
            self.show_menu_at(target, qh);
        }
    }

    fn activate_action(&mut self, action: &str, qh: &QueueHandle<Self>) {
        if self.menu_state.visible {
            self.set_menu_visible(false, qh);
        }
        if action == "logout" && !logout_available() {
            eprintln!("RicePlate: log out unavailable outside a labwc-managed session");
            return;
        }
        let (program, args): (&str, &[&str]) = match action {
            "applications" => ("fuzzel", &[]),
            "terminal" => ("foot", &[]),
            "lock" => ("swaylock", &["-f"]),
            "logout" => ("labwc", &["--exit"]),
            _ => return, // Validated recipe contract disallows other IDs.
        };
        if let Err(error) = Command::new(program).args(args).spawn() {
            eprintln!("RicePlate: cannot run {action}: {error}");
        }
    }

    fn redraw_menu(&mut self, _qh: &QueueHandle<Self>) {
        let Some(active) = self.active_menu.as_ref() else { return; };
        let layer = self.menu_layer.as_mut().filter(|menu|
            menu.surface.wl_surface() == active)
            .or_else(|| self.menu_mirrors.iter_mut().find(|menu|
                menu.surface.wl_surface() == active));
        let (Some(layer), Some(menu)) = (layer, self.recipe.menu.as_ref()) else { return };
        if !layer.configured || !self.menu_state.visible { return; }
        let surface = layer.surface.wl_surface();
        let Some(pool) = layer.pool.as_mut() else {
            return;
        };
        let (buffer, canvas) = match pool.create_buffer(
            native_menu::WIDTH as i32,
            native_menu::HEIGHT as i32,
            (native_menu::WIDTH * 4) as i32,
            wl_shm::Format::Argb8888,
        ) {
            Ok(result) => result,
            Err(error) => {
                eprintln!("RicePlate: native menu buffer unavailable: {error}");
                return;
            }
        };
        paint_menu(canvas, menu, &self.recipe, &self.menu_state);
        surface.damage_buffer(0, 0, native_menu::WIDTH as i32, native_menu::HEIGHT as i32);
        if let Err(error) = buffer.attach_to(surface) {
            eprintln!("RicePlate: native menu attach failed: {error}");
            self.closed = true;
            return;
        }
        layer.surface.commit();
    }

    fn set_calendar_visible(&mut self, visible: bool, qh: &QueueHandle<Self>) {
        if visible {
            if let Some(surface) = self.calendar_layer.as_ref()
                .map(|calendar| calendar.surface.wl_surface().clone()) {
                self.show_calendar_at(surface, qh);
            }
            return;
        }
        self.calendar_state.visible = false;
        self.calendar_focused = false;
        self.active_calendar = None;
        for layer in self.calendar_layer.iter().chain(self.calendar_mirrors.iter()) {
            layer.surface.set_keyboard_interactivity(KeyboardInteractivity::None);
            layer.surface.set_margin(
                if self.recipe.top { self.recipe.height as i32 } else { 0 },
                MAX_WIDTH as i32,
                if self.recipe.top { 0 } else { self.recipe.height as i32 }, 0,
            );
            layer.surface.commit();
        }
    }

    fn show_calendar_at(&mut self, surface: wl_surface::WlSurface, qh: &QueueHandle<Self>) {
        if !self.calendar_layer.iter().chain(self.calendar_mirrors.iter()).any(|calendar|
            calendar.surface.wl_surface() == &surface) { return; }
        if self.menu_state.visible { self.set_menu_visible(false, qh); }
        self.calendar_state.open(Local::now().date_naive());
        self.calendar_focused = false;
        self.active_calendar = Some(surface.clone());
        for layer in self.calendar_layer.iter().chain(self.calendar_mirrors.iter()) {
            let active = layer.surface.wl_surface() == &surface;
            layer.surface.set_keyboard_interactivity(if active {
                KeyboardInteractivity::OnDemand
            } else {
                KeyboardInteractivity::None
            });
            layer.surface.set_margin(
                if self.recipe.top { self.recipe.height as i32 } else { 0 },
                if active { 8 } else { MAX_WIDTH as i32 },
                if self.recipe.top { 0 } else { self.recipe.height as i32 }, 0,
            );
            layer.surface.commit();
        }
        self.redraw_calendar(qh);
    }

    fn toggle_calendar_for_panel(&mut self, mirror: Option<usize>, qh: &QueueHandle<Self>) {
        let target = match mirror {
            Some(index) => self.mirrors.get(index).and_then(|panel|
                self.calendar_mirrors.iter().find(|calendar|
                    calendar.output.as_ref() == Some(&panel.output)))
                .map(|calendar| calendar.surface.wl_surface().clone()),
            None => self.calendar_layer.as_ref()
                .map(|calendar| calendar.surface.wl_surface().clone()),
        };
        let Some(target) = target else { return; };
        if self.calendar_state.visible && self.active_calendar.as_ref() == Some(&target) {
            self.set_calendar_visible(false, qh);
        } else {
            self.show_calendar_at(target, qh);
        }
    }

    fn redraw_calendar(&mut self, _qh: &QueueHandle<Self>) {
        let Some(active) = self.active_calendar.as_ref() else { return; };
        let layer = self.calendar_layer.as_mut().filter(|calendar|
            calendar.surface.wl_surface() == active)
            .or_else(|| self.calendar_mirrors.iter_mut().find(|calendar|
                calendar.surface.wl_surface() == active));
        let Some(layer) = layer else { return; };
        if !layer.configured || !self.calendar_state.visible { return; }
        let surface = layer.surface.wl_surface();
        // Keep the popup's shared-memory allocation lazy during idle sessions.
        if layer.pool.is_none() {
            let bytes = (calendar::WIDTH * calendar::HEIGHT * 4 * 3) as usize;
            match SlotPool::new(bytes, &self.shm) {
                Ok(pool) => layer.pool = Some(pool),
                Err(error) => {
                    eprintln!("RicePlate: calendar allocation failed: {error}");
                    self.set_calendar_visible(false, _qh);
                    return;
                }
            }
        }
        let Some(pool) = layer.pool.as_mut() else { return; };
        let (buffer, canvas) = match pool.create_buffer(
            calendar::WIDTH as i32, calendar::HEIGHT as i32,
            (calendar::WIDTH * 4) as i32, wl_shm::Format::Argb8888,
        ) {
            Ok(result) => result,
            Err(error) => {
                eprintln!("RicePlate: calendar buffer unavailable: {error}");
                return;
            }
        };
        paint_calendar(canvas, &self.recipe, &self.calendar_state);
        surface.damage_buffer(0, 0, calendar::WIDTH as i32, calendar::HEIGHT as i32);
        if let Err(error) = buffer.attach_to(surface) {
            eprintln!("RicePlate: calendar attach failed: {error}");
            self.closed = true;
            return;
        }
        layer.surface.commit();
    }

    fn redraw_icon(&mut self, index: usize) {
        let Some(layer) = self.icon_layers.get_mut(index) else {
            return;
        };
        if !layer.configured || layer.placed.is_none() {
            return;
        }
        let width = recipe::ICON_WIDTH;
        let height = recipe::ICON_HEIGHT;
        let surface = layer.surface.wl_surface();
        let pool = layer.pool.as_mut().expect("configured icon has pool");
        let (buffer, canvas) = match pool.create_buffer(
            width as i32,
            height as i32,
            (width * 4) as i32,
            wl_shm::Format::Argb8888,
        ) {
            Ok(result) => result,
            Err(error) => {
                eprintln!("RicePlate: desktop icon buffer unavailable: {error}");
                return;
            }
        };
        let icon = &self.recipe.desktop_icons[index];
        paint_icon(canvas, icon, self.recipe.active, self.recipe.foreground,
                   self.focused_icon == Some(index));
        surface.damage_buffer(0, 0, width as i32, height as i32);
        if let Err(error) = buffer.attach_to(surface) {
            eprintln!("RicePlate: desktop icon attach failed: {error}");
            self.closed = true;
            return;
        }
        layer.surface.commit();
    }

    fn logical_output_size(&self, output: &wl_output::WlOutput) -> Option<(u32, u32)> {
        let info = self.outputs.info(output)?;
        // xdg-output logical dimensions include fractional scale and rotation.
        // Old compositors may expose only physical mode and integer scale.
        let (width, height) = info.logical_size.or_else(|| {
            info.modes.iter().find(|mode| mode.current).map(|mode| {
                let scale = info.scale_factor.max(1);
                (mode.dimensions.0 / scale, mode.dimensions.1 / scale)
            })
        })?;
        if width <= 0 || height <= 0 {
            return None;
        }
        Some((width as u32, height as u32))
    }

    fn reflow_icons(&mut self) {
        // The current preview creates one set of layer surfaces, owned by the
        // compositing output to which they were assigned. Full multi-output
        // desktop replication is a separate, gated milestone.
        let Some(output) = self
            .primary_output
            .clone()
            .or_else(|| self.icon_layers.iter().find_map(|icon| icon.output.clone()))
        else {
            return;
        };
        let Some((width, height)) = self.logical_output_size(&output) else {
            return;
        };
        let placements = desktop_layout::place(
            &self.recipe.desktop_icons,
            width,
            height,
            self.recipe.top,
            self.recipe.height,
        );
        for (index, placement) in placements.into_iter().enumerate() {
            let restored = {
                let layer = &mut self.icon_layers[index];
                if layer.placed == placement {
                    continue;
                }
                let restored = layer.placed.is_none() && placement.is_some();
                layer.placed = placement;
                if let Some((x, y)) = placement {
                    layer.surface.set_margin(y as i32, 0, 0, x as i32);
                } else {
                    // Keep the layer-shell role mapped: a null-buffer commit
                    // would permanently destroy it under the protocol. Park
                    // the icon beyond the output until room is available.
                    layer.surface.set_margin(
                        height as i32 + recipe::ICON_HEIGHT as i32,
                        0,
                        0,
                        width as i32 + recipe::ICON_WIDTH as i32,
                    );
                }
                layer.surface.commit();
                restored && layer.configured
            };
            if restored {
                self.redraw_icon(index);
            }
        }
    }

    fn grouped_tasks(&self) -> Vec<TaskGroup> {
        task_groups::group_windows(
            self.tasks
                .iter()
                .enumerate()
                .map(|(index, task)| WindowInfo {
                    index,
                    app_id: &task.app_id,
                    title: &task.title,
                    active: task.active,
                    ready: task.ready,
                }),
        )
    }

    fn request_redraw(&mut self, qh: &QueueHandle<Self>) {
        self.needs_redraw = true;
        if !self.frame_pending {
            self.redraw(qh);
        }
        for index in 0..self.mirrors.len() {
            self.mirrors[index].needs_redraw = true;
            if !self.mirrors[index].frame_pending { self.redraw_mirror(index, qh); }
        }
    }

    fn reveal_task(&mut self, index: usize) {
        let groups = self.grouped_tasks();
        let Some(group_index) = groups
            .iter()
            .position(|group| group.members.contains(&index))
        else {
            return;
        };
        let Some(view) =
            recipe::task_view(&self.recipe, self.width, groups.len(), self.task_offset)
        else {
            return;
        };
        if group_index < view.start {
            self.task_offset = group_index;
        } else if group_index >= view.start + view.slots {
            self.task_offset = group_index + 1 - view.slots;
        }
        for mirror in &mut self.mirrors {
            if let Some(view) = recipe::task_view(
                &self.recipe, mirror.width, groups.len(), mirror.task_offset,
            ) {
                if group_index < view.start { mirror.task_offset = group_index; }
                else if group_index >= view.start + view.slots {
                    mirror.task_offset = group_index + 1 - view.slots;
                }
            }
        }
    }

    fn redraw(&mut self, qh: &QueueHandle<Self>) {
        if !self.configured || self.width == 0 || self.height == 0 {
            return;
        }
        let width = self.width;
        let height = self.height;
        let groups = self.grouped_tasks();
        let selected = if self.focused_panel.as_ref() == Some(self.layer.wl_surface()) {
            self.focused_target
        } else { None };
        let surface = self.layer.wl_surface();
        let stride = (width * 4) as i32;
        let pool = self
            .pool
            .as_mut()
            .expect("configured surface has a memory pool");
        let (buffer, canvas) = match pool.create_buffer(
            width as i32,
            height as i32,
            stride,
            wl_shm::Format::Argb8888,
        ) {
            Ok(result) => result,
            Err(error) => {
                // Compositor may still own the last buffer; retry on its next
                // frame instead of killing the shell during a burst of events.
                eprintln!("RicePlate: deferring busy Wayland buffer: {error}");
                surface.frame(qh, FrameCallbackData(surface.clone()));
                self.frame_pending = true;
                self.layer.commit();
                return;
            }
        };
        paint_panel(canvas, width, height, &self.recipe, &groups,
                    &self.clock, self.task_offset, selected);
        surface.damage_buffer(0, 0, width as i32, height as i32);
        if let Err(error) = buffer.attach_to(surface) {
            eprintln!("RicePlate: failed to attach Wayland buffer: {error}");
            self.closed = true;
            return;
        }
        surface.frame(qh, FrameCallbackData(surface.clone()));
        self.frame_pending = true;
        self.needs_redraw = false;
        self.layer.commit();
    }
}

fn paint_panel(canvas: &mut [u8], width: u32, height: u32,
               style: &PanelStyle, groups: &[TaskGroup], clock: &str, offset: usize,
               selected: Option<KeyboardTarget>) {
    for pixel in canvas.chunks_exact_mut(4) {
        pixel.copy_from_slice(&style.background.to_le_bytes());
    }
    for placed in recipe::layout(style, width, groups.len()) {
        match placed.widget {
            Widget::Launcher => {
                fill_rect(canvas, width, height, placed.x, 0, placed.width, height,
                          style.active);
                draw_text(canvas, width, height,
                          placed.x + placed.width.saturating_sub(32) / 2,
                          height / 2 - 4, "Apps", style.foreground);
                if selected == Some(KeyboardTarget::Launcher) {
                    paint_focus_border(canvas, width, height, placed.x, placed.width,
                                       style.foreground);
                }
            }
            Widget::Tasks => {
                let Some(view) = recipe::task_view(style, width, groups.len(), offset) else {
                    continue;
                };
                for (index, group) in groups.iter().skip(view.start).take(view.slots).enumerate() {
                    let consumed = (index as u32) * view.cell_width;
                    let x = placed.x + consumed;
                    let cell_width = if index + 1 == view.slots {
                        view.content_width - consumed
                    } else {
                        view.cell_width
                    };
                    if group.active {
                        fill_rounded_rect(canvas, width, height, x, 0,
                                          cell_width.saturating_sub(2), height,
                                          style.task_radius, style.active);
                    }
                    let label = task_groups::visible_label(group, cell_width);
                    draw_text(canvas, width, height, x + 10, height / 2 - 4,
                              &label, style.foreground);
                    if selected == Some(KeyboardTarget::Task(view.start + index)) {
                        paint_focus_border(canvas, width, height, x, cell_width,
                                           style.foreground);
                    }
                }
                if view.prev {
                    draw_text(canvas, width, height, placed.x + view.content_width + 8,
                              height / 2 - 4, "<", style.foreground);
                }
                if view.next {
                    draw_text(canvas, width, height, placed.x + view.content_width + 32,
                              height / 2 - 4, ">", style.foreground);
                }
            }
            Widget::Clock => {
                draw_text(canvas, width, height,
                          placed.x + placed.width.saturating_sub(40) / 2,
                          height / 2 - 4, clock, style.foreground);
            }
            Widget::Gap(_) => {}
            Widget::Label(index) => {
                if let Some(label) = style.labels.get(index as usize) {
                    draw_text(canvas, width, height, placed.x + style.label_padding,
                              height / 2 - 4, label, style.foreground);
                }
            }
        }
    }
}

fn paint_focus_border(canvas: &mut [u8], width: u32, height: u32,
                      x: u32, cell_width: u32, color: u32) {
    if cell_width < 6 || height < 6 { return; }
    let inset = x.saturating_add(2);
    let inside = cell_width.saturating_sub(4);
    fill_rect(canvas, width, height, inset, 2, inside, 2, color);
    fill_rect(canvas, width, height, inset, height - 4, inside, 2, color);
    fill_rect(canvas, width, height, inset, 2, 2, height - 4, color);
    fill_rect(canvas, width, height, x.saturating_add(cell_width - 4), 2, 2, height - 4, color);
}

fn logout_available() -> bool {
    // An isolated Creator render can inherit an outer labwc PID. Never let a
    // preview's menu terminate the real logged-in desktop.
    if std::env::var("RICEBOWL_DE_NESTED").as_deref() == Ok("1") {
        return false;
    }
    std::env::var("LABWC_PID")
        .ok()
        .and_then(|value| value.parse::<u32>().ok())
        .is_some_and(|pid| pid > 1)
}

fn paint_menu(canvas: &mut [u8], menu: &recipe::NativeMenu, style: &PanelStyle, state: &MenuState) {
    let width = native_menu::WIDTH;
    let height = native_menu::HEIGHT;
    for pixel in canvas.chunks_exact_mut(4) {
        pixel.copy_from_slice(&style.background.to_le_bytes());
    }
    fill_rect(canvas, width, height, 0, 0, width, 38, style.active);
    draw_text(
        canvas,
        width,
        height,
        16,
        15,
        &menu.title.chars().take(32).collect::<String>(),
        style.foreground,
    );
    let groups = menu.groups.len().max(1) as u32;
    for (index, group) in menu.groups.iter().enumerate() {
        let x = index as u32 * width / groups;
        let next = (index as u32 + 1) * width / groups;
        if state.group == index {
            fill_rect(
                canvas,
                width,
                height,
                x,
                native_menu::TAB_TOP,
                next - x,
                native_menu::TAB_HEIGHT,
                style.active,
            );
        }
        let available = (next - x).saturating_sub(16) / 8;
        let label: String = group.title.chars().take(available as usize).collect();
        draw_text(
            canvas,
            width,
            height,
            x + 8,
            native_menu::TAB_TOP + 16,
            &label,
            style.foreground,
        );
    }
    if let Some(group) = menu.groups.get(state.group) {
        for (index, action) in group.actions.iter().enumerate() {
            let top = native_menu::ACTION_TOP + index as u32 * native_menu::ACTION_HEIGHT;
            if index == state.selected {
                fill_rounded_rect(
                    canvas,
                    width,
                    height,
                    8,
                    top + 2,
                    width - 16,
                    native_menu::ACTION_HEIGHT - 4,
                    style.task_radius,
                    style.active,
                );
            }
            let label = match action.as_str() {
                "applications" => "Applications",
                "terminal" => "Terminal",
                "lock" => "Lock screen",
                "logout" if logout_available() => "Log out of RiceBowl",
                "logout" => "Log out (unavailable)",
                _ => "Unsupported",
            };
            draw_text(canvas, width, height, 20, top + 16, label, style.foreground);
        }
    }
    draw_text(
        canvas,
        width,
        height,
        12,
        height - 16,
        "Arrows  Enter  Esc close",
        style.foreground,
    );
}

fn paint_calendar(canvas: &mut [u8], style: &PanelStyle, state: &CalendarState) {
    let width = calendar::WIDTH;
    let height = calendar::HEIGHT;
    for pixel in canvas.chunks_exact_mut(4) {
        pixel.copy_from_slice(&style.background.to_le_bytes());
    }
    fill_rect(canvas, width, height, 0, 0, width, 56, style.active);
    draw_text(canvas, width, height, 12, 22,
              &state.month.format("%B %Y").to_string(), style.foreground);
    draw_text(canvas, width, height, 262, 22, "<", style.foreground);
    draw_text(canvas, width, height, 306, 22, ">", style.foreground);
    for (index, weekday) in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].iter().enumerate() {
        draw_text(canvas, width, height,
                  calendar::GRID_X + index as u32 * calendar::CELL_WIDTH + 12,
                  82, weekday, style.foreground);
    }
    let muted = {
        let foreground = style.foreground;
        let background = style.background;
        let channel = |shift| {
            (((foreground >> shift) & 0xff_u32) + 2_u32 * ((background >> shift) & 0xff_u32)) / 3_u32
        };
        0xff00_0000_u32 | (channel(16) << 16) | (channel(8) << 8) | channel(0)
    };
    for (index, (day, this_month)) in state.cells().into_iter().enumerate() {
        let x = calendar::GRID_X + (index % 7) as u32 * calendar::CELL_WIDTH;
        let y = calendar::GRID_Y + (index / 7) as u32 * calendar::CELL_HEIGHT;
        if day == state.today {
            fill_rounded_rect(canvas, width, height, x + 4, y + 2,
                              calendar::CELL_WIDTH - 8, calendar::CELL_HEIGHT - 4,
                              7, style.active);
        }
        if day == state.selected {
            fill_rect(canvas, width, height, x + 4, y + 1,
                      calendar::CELL_WIDTH - 8, 2, style.foreground);
            fill_rect(canvas, width, height, x + 4, y + calendar::CELL_HEIGHT - 3,
                      calendar::CELL_WIDTH - 8, 2, style.foreground);
        }
        let label = day.day().to_string();
        draw_text(canvas, width, height,
                  x + (calendar::CELL_WIDTH - label.len() as u32 * 8) / 2,
                  y + 13, &label, if this_month { style.foreground } else { muted });
    }
    fill_rounded_rect(canvas, width, height, 12, 322, 92, 28, 4, style.active);
    draw_text(canvas, width, height, 31, 332, "Today", style.foreground);
    draw_text(canvas, width, height, 183, 332, "Esc to close", style.foreground);
}

fn paint_icon(canvas: &mut [u8], icon: &recipe::DesktopIcon, active: u32,
              foreground: u32, focused: bool) {
    let width = recipe::ICON_WIDTH;
    let height = recipe::ICON_HEIGHT;
    canvas.fill(0); // Leave the surrounding desktop visible.
    if focused {
        // Narrow focus frame: keep the rest of the desktop hit area transparent.
        fill_rect(canvas, width, height, 0, 0, width, 2, foreground);
        fill_rect(canvas, width, height, 0, height - 2, width, 2, foreground);
        fill_rect(canvas, width, height, 0, 0, 2, height, foreground);
        fill_rect(canvas, width, height, width - 2, 0, 2, height, foreground);
    }
    let glyph = match icon.action.as_str() {
        "applications" => "Apps",
        "terminal" => ">_",
        "lock" => "Lock",
        _ => return,
    };
    fill_rounded_rect(canvas, width, height, 24, 4, 56, 48, 10, active);
    // Contrast backplate prevents white labels from vanishing on bright rices.
    fill_rounded_rect(canvas, width, height, 2, 58, 100, 26, 6, 0xb020_2c36);
    draw_text(
        canvas,
        width,
        height,
        52 - (glyph.len() as u32 * 4),
        24,
        glyph,
        foreground,
    );
    draw_text(
        canvas,
        width,
        height,
        (width - icon.label.len() as u32 * 8) / 2,
        66,
        &icon.label,
        foreground,
    );
}

fn fill_rect(
    canvas: &mut [u8],
    width: u32,
    height: u32,
    x: u32,
    y: u32,
    w: u32,
    h: u32,
    color: u32,
) {
    for row in y..y.saturating_add(h).min(height) {
        for column in x..x.saturating_add(w).min(width) {
            let index = ((row * width + column) * 4) as usize;
            canvas[index..index + 4].copy_from_slice(&color.to_le_bytes());
        }
    }
}

fn fill_rounded_rect(
    canvas: &mut [u8],
    width: u32,
    height: u32,
    x: u32,
    y: u32,
    w: u32,
    h: u32,
    radius: u32,
    color: u32,
) {
    let r = radius.min(w / 2).min(h / 2);
    if r == 0 {
        fill_rect(canvas, width, height, x, y, w, h, color);
        return;
    }
    let corner = (r as i64 - 1).pow(2);
    for py in 0..h.min(height.saturating_sub(y)) {
        for px in 0..w.min(width.saturating_sub(x)) {
            let dx = if px < r {
                r - 1 - px
            } else {
                px.saturating_sub(w - r)
            };
            let dy = if py < r {
                r - 1 - py
            } else {
                py.saturating_sub(h - r)
            };
            if (dx as i64).pow(2) + (dy as i64).pow(2) <= corner {
                let index = (((y + py) * width + x + px) * 4) as usize;
                canvas[index..index + 4].copy_from_slice(&color.to_le_bytes());
            }
        }
    }
}

fn draw_text(canvas: &mut [u8], width: u32, height: u32, x: u32, y: u32, text: &str, color: u32) {
    for (offset, character) in text.chars().enumerate() {
        let Some(bitmap) = BASIC_FONTS.get(character) else {
            continue;
        };
        let origin = x.saturating_add((offset as u32).saturating_mul(8));
        for (row, bits) in bitmap.iter().enumerate() {
            for column in 0..8_u32 {
                if *bits & (1_u8 << column) != 0 {
                    fill_rect(
                        canvas,
                        width,
                        height,
                        origin + column,
                        y + row as u32,
                        1,
                        1,
                        color,
                    );
                }
            }
        }
    }
}

impl CompositorHandler for RicePlate {
    fn scale_factor_changed(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &wl_surface::WlSurface,
        _: i32,
    ) {
    }
    fn transform_changed(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &wl_surface::WlSurface,
        _: wl_output::Transform,
    ) {
    }
    fn frame(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        surface: &wl_surface::WlSurface,
        _: u32,
    ) {
        if surface != self.layer.wl_surface() {
            if let Some(index) = self.mirrors.iter().position(|mirror|
                    mirror.surface.wl_surface() == surface) {
                self.mirrors[index].frame_pending = false;
                if self.mirrors[index].needs_redraw { self.redraw_mirror(index, qh); }
            }
            return;
        }
        self.frame_pending = false;
        if self.needs_redraw {
            self.redraw(qh);
        }
    }
    fn surface_enter(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        surface: &wl_surface::WlSurface,
        output: &wl_output::WlOutput,
    ) {
        if surface == self.layer.wl_surface() {
            eprintln!("RicePlate: primary panel entered {output:?}");
            self.primary_output = Some(output.clone());
            self.primary_output_seen = true;
            self.reflow_icons();
            self.sync_mirrors(qh);
            return;
        }
        if let Some(layer) = self
            .icon_layers
            .iter_mut()
            .find(|icon| icon.surface.wl_surface() == surface)
        {
            layer.output = Some(output.clone());
            self.reflow_icons();
        }
    }
    fn surface_leave(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        surface: &wl_surface::WlSurface,
        output: &wl_output::WlOutput,
    ) {
        if surface == self.layer.wl_surface() {
            eprintln!("RicePlate: primary panel left {output:?}");
            if self.primary_output.as_ref() == Some(output) {
                self.primary_output = None;
            }
            self.sync_mirrors(qh);
            return;
        }
        if let Some(layer) = self
            .icon_layers
            .iter_mut()
            .find(|icon| icon.surface.wl_surface() == surface)
        {
            if layer.output.as_ref() == Some(output) {
                layer.output = None;
            }
        }
    }
}

impl LayerShellHandler for RicePlate {
    fn closed(&mut self, _: &Connection, qh: &QueueHandle<Self>, layer: &LayerSurface) {
        if self.focused_panel.as_ref() == Some(layer.wl_surface()) {
            self.focused_panel = None;
            self.focused_target = None;
        }
        if layer.wl_surface() == self.layer.wl_surface() {
            self.closed = true;
        } else if let Some(index) = self.mirrors.iter().position(|mirror|
                mirror.surface.wl_surface() == layer.wl_surface()) {
            self.mirrors.remove(index);
        } else if self
            .menu_layer
            .as_ref()
            .is_some_and(|menu| menu.surface.wl_surface() == layer.wl_surface())
        {
            self.menu_layer = None;
            if self.active_menu.as_ref() == Some(layer.wl_surface()) {
                self.set_menu_visible(false, qh);
            }
        } else if let Some(index) = self.menu_mirrors.iter().position(|menu|
            menu.surface.wl_surface() == layer.wl_surface()) {
            self.menu_mirrors.remove(index);
            if self.active_menu.as_ref() == Some(layer.wl_surface()) {
                self.set_menu_visible(false, qh);
            }
        } else if self.calendar_layer.as_ref()
            .is_some_and(|calendar| calendar.surface.wl_surface() == layer.wl_surface()) {
            self.calendar_layer = None;
            if self.active_calendar.as_ref() == Some(layer.wl_surface()) {
                self.set_calendar_visible(false, qh);
            }
        } else if let Some(index) = self.calendar_mirrors.iter().position(|calendar|
            calendar.surface.wl_surface() == layer.wl_surface()) {
            self.calendar_mirrors.remove(index);
            if self.active_calendar.as_ref() == Some(layer.wl_surface()) {
                self.set_calendar_visible(false, qh);
            }
        } else if let Some(icon) = self
            .icon_layers
            .iter_mut()
            .find(|icon| icon.surface.wl_surface() == layer.wl_surface())
        {
            icon.configured = false;
        }
    }
    fn configure(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        layer: &LayerSurface,
        config: LayerSurfaceConfigure,
        _: u32,
    ) {
        if let Some(index) = self.mirrors.iter().position(|mirror|
                mirror.surface.wl_surface() == layer.wl_surface()) {
            let width = config.new_size.0;
            let height = config.new_size.1;
            if width == 0 || width > MAX_WIDTH || height == 0 || height > MAX_HEIGHT {
                eprintln!("RicePlate: invalid extra-output panel geometry");
                self.mirrors.remove(index);
                return;
            }
            let mirror = &mut self.mirrors[index];
            if (width, height) != (mirror.width, mirror.height) {
                let byte_count = width as usize * height as usize * 4 * 3;
                match SlotPool::new(byte_count, &self.shm) {
                    Ok(pool) => mirror.pool = Some(pool),
                    Err(error) => {
                        eprintln!("RicePlate: cannot allocate extra-output panel: {error}");
                        self.mirrors.remove(index);
                        return;
                    }
                }
            }
            mirror.width = width;
            mirror.height = height;
            mirror.configured = true;
            self.redraw_mirror(index, qh);
            return;
        }
        if self.calendar_layer.as_ref().is_some_and(|calendar|
            calendar.surface.wl_surface() == layer.wl_surface())
            || self.calendar_mirrors.iter().any(|calendar|
                calendar.surface.wl_surface() == layer.wl_surface()) {
            if config.new_size != (calendar::WIDTH, calendar::HEIGHT) {
                eprintln!("RicePlate: compositor proposed unsupported calendar dimensions");
                if self.calendar_layer.as_ref().is_some_and(|calendar|
                    calendar.surface.wl_surface() == layer.wl_surface()) {
                    self.calendar_layer = None;
                } else {
                    self.calendar_mirrors.retain(|calendar|
                        calendar.surface.wl_surface() != layer.wl_surface());
                }
                if self.active_calendar.as_ref() == Some(layer.wl_surface()) {
                    self.set_calendar_visible(false, qh);
                }
                return;
            }
            if let Some(calendar_layer) = self.calendar_layer.as_mut()
                .filter(|calendar| calendar.surface.wl_surface() == layer.wl_surface()) {
                calendar_layer.configured = true;
            } else if let Some(calendar_layer) = self.calendar_mirrors.iter_mut().find(|calendar|
                calendar.surface.wl_surface() == layer.wl_surface()) {
                calendar_layer.configured = true;
            }
            self.redraw_calendar(qh);
            return;
        }
        if self.menu_layer.as_ref().is_some_and(|menu|
            menu.surface.wl_surface() == layer.wl_surface())
            || self.menu_mirrors.iter().any(|menu|
                menu.surface.wl_surface() == layer.wl_surface()) {
            if config.new_size != (native_menu::WIDTH, native_menu::HEIGHT) {
                eprintln!("RicePlate: compositor proposed unsupported native menu geometry");
                if self.menu_layer.as_ref().is_some_and(|menu|
                    menu.surface.wl_surface() == layer.wl_surface()) {
                    self.menu_layer = None;
                } else {
                    self.menu_mirrors.retain(|menu|
                        menu.surface.wl_surface() != layer.wl_surface());
                }
                if self.active_menu.as_ref() == Some(layer.wl_surface()) {
                    self.set_menu_visible(false, qh);
                }
                return;
            }
            let menu_layer = self.menu_layer.as_mut().filter(|menu|
                menu.surface.wl_surface() == layer.wl_surface())
                .or_else(|| self.menu_mirrors.iter_mut().find(|menu|
                    menu.surface.wl_surface() == layer.wl_surface()))
                .expect("matched a live native menu layer");
            if menu_layer.pool.is_none() {
                let byte_count = (native_menu::WIDTH * native_menu::HEIGHT * 4 * 3) as usize;
                match SlotPool::new(byte_count, &self.shm) {
                    Ok(pool) => menu_layer.pool = Some(pool),
                    Err(error) => {
                        eprintln!("RicePlate: cannot allocate native menu: {error}");
                        self.set_menu_visible(false, qh);
                        return;
                    }
                }
            }
            menu_layer.configured = true;
            self.redraw_menu(qh);
            return;
        }
        if let Some(index) = self
            .icon_layers
            .iter()
            .position(|icon| icon.surface.wl_surface() == layer.wl_surface())
        {
            if config.new_size != (recipe::ICON_WIDTH, recipe::ICON_HEIGHT) {
                eprintln!("RicePlate: compositor proposed unexpected desktop icon size");
                return;
            }
            let icon = &mut self.icon_layers[index];
            if icon.pool.is_none() {
                let bytes = recipe::ICON_WIDTH as usize * recipe::ICON_HEIGHT as usize * 4 * 2;
                match SlotPool::new(bytes, &self.shm) {
                    Ok(pool) => icon.pool = Some(pool),
                    Err(error) => {
                        eprintln!("RicePlate: cannot allocate icon memory: {error}");
                        self.closed = true;
                        return;
                    }
                }
            }
            icon.configured = true;
            self.redraw_icon(index);
            return;
        }
        if layer.wl_surface() != self.layer.wl_surface() {
            return;
        }
        let width = config.new_size.0;
        let height = config.new_size.1;
        if width == 0 || width > MAX_WIDTH || height == 0 || height > MAX_HEIGHT {
            eprintln!("RicePlate: compositor proposed unsupported surface dimensions");
            self.closed = true;
            return;
        }
        if (width, height) != (self.width, self.height) {
            // Three slots permit updates while the compositor is still
            // reading earlier buffers. Allocation stays bounded to 48 MiB.
            let byte_count = width as usize * height as usize * 4 * 3;
            match SlotPool::new(byte_count, &self.shm) {
                Ok(pool) => self.pool = Some(pool),
                Err(error) => {
                    eprintln!("RicePlate: cannot allocate shared memory: {error}");
                    self.closed = true;
                    return;
                }
            }
        }
        self.width = width;
        self.height = height;
        self.configured = true;
        if let Some(index) = self.tasks.iter().position(|task| task.active && task.ready) {
            self.reveal_task(index);
        }
        self.request_redraw(qh);
    }
}

impl OutputHandler for RicePlate {
    fn output_state(&mut self) -> &mut OutputState {
        &mut self.outputs
    }
    fn new_output(&mut self, _: &Connection, qh: &QueueHandle<Self>, _: wl_output::WlOutput) {
        self.reflow_icons();
        self.sync_mirrors(qh);
    }
    fn update_output(&mut self, _: &Connection, qh: &QueueHandle<Self>, _: wl_output::WlOutput) {
        self.reflow_icons();
        self.sync_mirrors(qh);
    }
    fn output_destroyed(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        output: wl_output::WlOutput,
    ) {
        if self.primary_output.as_ref() == Some(&output) {
            self.primary_output = None;
        }
        for icon in &mut self.icon_layers {
            if icon.output.as_ref() == Some(&output) {
                icon.output = None;
            }
        }
        self.reflow_icons();
        self.sync_mirrors(qh);
    }
}

impl SeatHandler for RicePlate {
    fn seat_state(&mut self) -> &mut SeatState {
        &mut self.seats
    }
    fn new_seat(&mut self, _: &Connection, _: &QueueHandle<Self>, seat: wl_seat::WlSeat) {
        if self.primary_seat.is_none() {
            self.primary_seat = Some(seat);
        }
    }
    fn new_capability(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        seat: wl_seat::WlSeat,
        capability: Capability,
    ) {
        if capability == Capability::Keyboard && self.keyboard.is_none() {
            match self.seats.get_keyboard(qh, &seat, None) {
                Ok(keyboard) => self.keyboard = Some(keyboard),
                Err(error) => eprintln!("RicePlate: keyboard unavailable: {error}"),
            }
        }
        if capability == Capability::Pointer && self.pointer.is_none() {
            match self.seats.get_pointer(qh, &seat) {
                Ok(pointer) => self.pointer = Some(pointer),
                Err(error) => eprintln!("RicePlate: pointer unavailable: {error}"),
            }
        }
    }
    fn remove_capability(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        _: wl_seat::WlSeat,
        capability: Capability,
    ) {
        if capability == Capability::Pointer {
            if let Some(pointer) = self.pointer.take() {
                pointer.release();
            }
            self.icon_drag = None;
            self.save_icon_positions();
        } else if capability == Capability::Keyboard {
            if let Some(keyboard) = self.keyboard.take() {
                keyboard.release();
            }
            self.menu_focused = false;
            self.calendar_focused = false;
            if let Some(index) = self.focused_icon.take() {
                self.redraw_icon(index);
                self.save_icon_positions();
            }
            self.focused_panel = None;
            self.focused_target = None;
            self.request_redraw(qh);
        }
    }
    fn remove_seat(&mut self, _: &Connection, _: &QueueHandle<Self>, seat: wl_seat::WlSeat) {
        if self.primary_seat.as_ref() == Some(&seat) {
            self.primary_seat = None;
        }
    }
}

impl KeyboardHandler for RicePlate {
    fn enter(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        _: &wl_keyboard::WlKeyboard,
        surface: &wl_surface::WlSurface,
        _: u32,
        _: &[u32],
        _: &[Keysym],
    ) {
        self.menu_focused = self.menu_state.visible
            && self.active_menu.as_ref() == Some(surface);
        self.calendar_focused = self.calendar_state.visible
            && self.active_calendar.as_ref() == Some(surface);
        if let Some((mirror, width, offset)) = self.panel_geometry(surface) {
            let groups = self.grouped_tasks();
            let active = groups.iter().position(|group| group.active);
            self.focused_panel = Some(surface.clone());
            self.focused_target = task_navigation::initial(
                &self.recipe, width, groups.len(), active,
            );
            let next = task_navigation::reveal(
                &self.recipe, width, groups.len(), offset, self.focused_target,
            );
            if let Some(index) = mirror {
                self.mirrors[index].task_offset = next;
            } else {
                self.task_offset = next;
            }
            self.request_redraw(qh);
        } else if self.focused_panel.take().is_some() {
            self.focused_target = None;
            self.request_redraw(qh);
        }
        let next = self.icon_layers.iter()
            .position(|icon| icon.surface.wl_surface() == surface && icon.placed.is_some());
        if self.focused_icon != next {
            let previous = self.focused_icon;
            self.focused_icon = next;
            if let Some(index) = previous { self.redraw_icon(index); }
            if let Some(index) = next { self.redraw_icon(index); }
            self.save_icon_positions();
        }
    }

    fn leave(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        _: &wl_keyboard::WlKeyboard,
        surface: &wl_surface::WlSurface,
        _: u32,
    ) {
        if self.active_menu.as_ref() == Some(surface) && self.menu_focused {
            self.set_menu_visible(false, qh);
        }
        if self.active_calendar.as_ref() == Some(surface) && self.calendar_focused {
            self.set_calendar_visible(false, qh);
        }
        if let Some(index) = self.focused_icon {
            if self.icon_layers[index].surface.wl_surface() == surface {
                self.focused_icon = None;
                self.redraw_icon(index);
                self.save_icon_positions();
            }
        }
        if self.focused_panel.as_ref() == Some(surface) {
            self.focused_panel = None;
            self.focused_target = None;
            self.request_redraw(qh);
        }
    }

    fn press_key(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        _: &wl_keyboard::WlKeyboard,
        _: u32,
        event: KeyEvent,
    ) {
        if self.calendar_state.visible && self.calendar_focused {
            match event.keysym {
                Keysym::Left => self.calendar_state.move_selection(-1),
                Keysym::Right => self.calendar_state.move_selection(1),
                Keysym::Up => self.calendar_state.move_selection(-7),
                Keysym::Down => self.calendar_state.move_selection(7),
                Keysym::Prior => self.calendar_state.shift(-1),
                Keysym::Next => self.calendar_state.shift(1),
                Keysym::Home => self.calendar_state.go_today(Local::now().date_naive()),
                Keysym::Escape => {
                    self.set_calendar_visible(false, qh);
                    return;
                }
                _ => return,
            }
            self.redraw_calendar(qh);
            return;
        }
        if self.handle_panel_key(event.keysym, qh) {
            return;
        }
        if let Some(index) = self.focused_icon {
            match event.keysym {
                Keysym::Return | Keysym::KP_Enter | Keysym::space => {
                    let action = self.recipe.desktop_icons[index].action.clone();
                    self.activate_action(&action, qh);
                }
                Keysym::Left | Keysym::Right | Keysym::Up | Keysym::Down => {
                    let icon = &mut self.recipe.desktop_icons[index];
                    match event.keysym {
                        Keysym::Left => icon.x = icon.x.saturating_sub(16),
                        Keysym::Right => icon.x = icon.x.saturating_add(16).min(desktop_layout::MAX_SAVED_POSITION),
                        Keysym::Up => icon.y = icon.y.saturating_sub(16),
                        Keysym::Down => icon.y = icon.y.saturating_add(16).min(desktop_layout::MAX_SAVED_POSITION),
                        _ => unreachable!(),
                    }
                    self.reflow_icons();
                    self.icon_position_dirty = true;
                }
                Keysym::Escape => {
                    self.save_icon_positions();
                }
                _ => {}
            }
            return;
        }
        if !self.menu_state.visible || !self.menu_focused {
            return;
        }
        let Some(menu) = self.recipe.menu.as_ref() else {
            return;
        };
        let action = match event.keysym {
            Keysym::Escape => {
                self.set_menu_visible(false, qh);
                return;
            }
            Keysym::Up => {
                self.menu_state.select_by(menu, -1);
                None
            }
            Keysym::Down | Keysym::Tab => {
                self.menu_state.select_by(menu, 1);
                None
            }
            Keysym::Left => {
                self.menu_state.group_by(menu, -1);
                None
            }
            Keysym::Right => {
                self.menu_state.group_by(menu, 1);
                None
            }
            Keysym::Return | Keysym::KP_Enter | Keysym::space => {
                self.menu_state.current_action(menu).map(str::to_owned)
            }
            _ => return,
        };
        if let Some(action) = action {
            self.activate_action(&action, qh);
        } else {
            self.redraw_menu(qh);
        }
    }

    fn repeat_key(
        &mut self,
        conn: &Connection,
        qh: &QueueHandle<Self>,
        keyboard: &wl_keyboard::WlKeyboard,
        serial: u32,
        event: KeyEvent,
    ) {
        // Never repeat Enter/Space: holding a key must not launch multiple apps.
        if matches!(event.keysym, Keysym::Left | Keysym::Right | Keysym::Up
            | Keysym::Down | Keysym::Tab | Keysym::ISO_Left_Tab) {
            self.press_key(conn, qh, keyboard, serial, event);
        }
    }

    fn release_key(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &wl_keyboard::WlKeyboard,
        _: u32,
        event: KeyEvent,
    ) {
        if matches!(event.keysym, Keysym::Left | Keysym::Right | Keysym::Up | Keysym::Down) {
            self.save_icon_positions();
        }
    }

    fn update_modifiers(
        &mut self,
        _: &Connection,
        _: &QueueHandle<Self>,
        _: &wl_keyboard::WlKeyboard,
        _: u32,
        _: Modifiers,
        _: RawModifiers,
        _: u32,
    ) {
    }
}

impl PointerHandler for RicePlate {
    fn pointer_frame(
        &mut self,
        _: &Connection,
        qh: &QueueHandle<Self>,
        _: &wl_pointer::WlPointer,
        events: &[PointerEvent],
    ) {
        for event in events {
            if self.active_calendar.as_ref() == Some(&event.surface) {
                if let PointerEventKind::Press { button: BTN_LEFT, .. } = event.kind {
                    match self.calendar_state.hit(event.position.0, event.position.1) {
                        Some(CalendarHit::Previous) => self.calendar_state.shift(-1),
                        Some(CalendarHit::Next) => self.calendar_state.shift(1),
                        Some(CalendarHit::Today) => {
                            self.calendar_state.go_today(Local::now().date_naive());
                        }
                        Some(CalendarHit::Day(day)) => self.calendar_state.select(day),
                        None => continue,
                    }
                    self.redraw_calendar(qh);
                }
                continue;
            }
            if self.active_menu.as_ref() == Some(&event.surface) {
                if let PointerEventKind::Press {
                    button: BTN_LEFT, ..
                } = event.kind
                {
                    if let Some(menu) = self.recipe.menu.as_ref() {
                        match self
                            .menu_state
                            .hit(menu, event.position.0, event.position.1)
                        {
                            Some(MenuHit::Group(index)) => {
                                self.menu_state.group = index;
                                self.menu_state.selected = 0;
                                self.redraw_menu(qh);
                            }
                            Some(MenuHit::Action(index)) => {
                                if let Some(action) = menu.groups[self.menu_state.group]
                                    .actions
                                    .get(index)
                                    .cloned()
                                {
                                    self.activate_action(&action, qh);
                                }
                            }
                            Some(MenuHit::Close) => self.set_menu_visible(false, qh),
                            None => {}
                        }
                    }
                }
                continue;
            }
            if let Some(index) = self
                .icon_layers
                .iter()
                .position(|icon| &event.surface == icon.surface.wl_surface())
            {
                if self.icon_layers[index].placed.is_none() {
                    continue;
                }
                match event.kind {
                    PointerEventKind::Press { button: BTN_LEFT, .. } => {
                        if let Some(position) = self.icon_layers[index].placed {
                            self.icon_drag = Some(IconDrag {
                                index, anchor: event.position, started: position, moved: false,
                            });
                        }
                    }
                    PointerEventKind::Motion { .. } => {
                        if let Some(drag) = self.icon_drag.as_mut().filter(|d| d.index == index) {
                            let current = self.icon_layers[index].placed.unwrap();
                            let desired = desktop_layout::dragged_to(
                                current, drag.anchor, event.position,
                            );
                            if desired.0.abs_diff(drag.started.0)
                                + desired.1.abs_diff(drag.started.1) >= 6
                            {
                                drag.moved = true;
                            }
                            if drag.moved && desired != current {
                                let icon = &mut self.recipe.desktop_icons[index];
                                (icon.x, icon.y) = desired;
                                self.reflow_icons();
                                self.icon_position_dirty = true;
                            }
                        }
                    }
                    PointerEventKind::Release { button: BTN_LEFT, .. } => {
                        if let Some(drag) = self.icon_drag.take() {
                            if drag.index == index && !drag.moved {
                                let action = self.recipe.desktop_icons[index].action.clone();
                                self.activate_action(&action, qh);
                            } else if drag.index == index {
                                self.save_icon_positions();
                            }
                        }
                    }
                    _ => {}
                }
                continue;
            }
            let mirror_index = self.mirrors.iter().position(|mirror|
                &event.surface == mirror.surface.wl_surface());
            let (panel_width, panel_height, panel_offset) = if let Some(index) = mirror_index {
                let mirror = &self.mirrors[index];
                (mirror.width, mirror.height, mirror.task_offset)
            } else if &event.surface == self.layer.wl_surface() {
                (self.width, self.height, self.task_offset)
            } else { continue; };
            if let PointerEventKind::Press { button, .. } = event.kind {
                if button == BTN_LEFT
                    && event.position.1 >= 0.0
                    && event.position.1 < f64::from(panel_height)
                {
                    let groups = self.grouped_tasks();
                    match recipe::hit(
                        event.position.0,
                        panel_width,
                        groups.len(),
                        panel_offset,
                        &self.recipe,
                    ) {
                        Some(Hit::Launcher) => {
                            if self.focused_panel.as_ref() == Some(&event.surface) {
                                self.focused_target = Some(KeyboardTarget::Launcher);
                                self.request_redraw(qh);
                            }
                            self.activate_launcher(mirror_index, qh);
                        }
                        Some(Hit::Clock) => {
                            self.toggle_calendar_for_panel(mirror_index, qh);
                        }
                        Some(Hit::Task(index)) => {
                            if self.focused_panel.as_ref() == Some(&event.surface) {
                                self.focused_target = Some(KeyboardTarget::Task(index));
                                self.request_redraw(qh);
                            }
                            self.activate_group(index);
                        }
                        Some(Hit::PreviousTasks) => {
                            if let Some(view) = recipe::task_view(
                                &self.recipe,
                                panel_width,
                                groups.len(),
                                panel_offset,
                            ) {
                                let next = view.start.saturating_sub(view.slots);
                                if let Some(index) = mirror_index {
                                    self.mirrors[index].task_offset = next;
                                } else { self.task_offset = next; }
                                self.request_redraw(qh);
                            }
                        }
                        Some(Hit::NextTasks) => {
                            if let Some(view) = recipe::task_view(
                                &self.recipe,
                                panel_width,
                                groups.len(),
                                panel_offset,
                            ) {
                                let next = (view.start + view.slots)
                                    .min(groups.len().saturating_sub(view.slots));
                                if let Some(index) = mirror_index {
                                    self.mirrors[index].task_offset = next;
                                } else { self.task_offset = next; }
                                self.request_redraw(qh);
                            }
                        }
                        None => {}
                    }
                }
            }
        }
    }
}

impl Dispatch<ZwlrForeignToplevelManagerV1, ()> for RicePlate {
    fn event(
        state: &mut Self,
        _: &ZwlrForeignToplevelManagerV1,
        event: zwlr_foreign_toplevel_manager_v1::Event,
        _: &(),
        _: &Connection,
        qh: &QueueHandle<Self>,
    ) {
        match event {
            zwlr_foreign_toplevel_manager_v1::Event::Toplevel { toplevel } => {
                if state.tasks.len() >= recipe::MAX_TRACKED_TASKS {
                    toplevel.destroy();
                } else {
                    state.tasks.push(Task {
                        handle: toplevel,
                        title: String::new(),
                        app_id: String::new(),
                        active: false,
                        ready: false,
                    });
                }
            }
            zwlr_foreign_toplevel_manager_v1::Event::Finished => {
                state.toplevel_manager = None;
                state.tasks.clear();
                state.task_offset = 0;
                state.request_redraw(qh);
            }
            _ => {}
        }
    }
}

impl Dispatch<ZwlrForeignToplevelHandleV1, ()> for RicePlate {
    fn event(
        state: &mut Self,
        proxy: &ZwlrForeignToplevelHandleV1,
        event: zwlr_foreign_toplevel_handle_v1::Event,
        _: &(),
        _: &Connection,
        qh: &QueueHandle<Self>,
    ) {
        if let zwlr_foreign_toplevel_handle_v1::Event::Closed = event {
            if let Some(index) = state.tasks.iter().position(|task| task.handle == *proxy) {
                state.tasks.remove(index).handle.destroy();
                state.task_offset = state
                    .task_offset
                    .min(state.grouped_tasks().len().saturating_sub(1));
                if let Some(active) = state
                    .tasks
                    .iter()
                    .position(|task| task.active && task.ready)
                {
                    state.reveal_task(active);
                }
                state.request_redraw(qh);
            }
            return;
        }
        if let Some(index) = state.tasks.iter().position(|task| task.handle == *proxy) {
            let task = &mut state.tasks[index];
            let mut refresh = false;
            match event {
                zwlr_foreign_toplevel_handle_v1::Event::Title { title } => {
                    task.title = title.chars().take(256).collect()
                }
                zwlr_foreign_toplevel_handle_v1::Event::AppId { app_id } => {
                    task.app_id = app_id.chars().take(256).collect()
                }
                zwlr_foreign_toplevel_handle_v1::Event::State { state: states } => {
                    task.active = states
                        .chunks_exact(4)
                        .any(|raw| u32::from_ne_bytes(raw.try_into().unwrap_or_default()) == 2)
                }
                zwlr_foreign_toplevel_handle_v1::Event::Done => {
                    task.ready = true;
                    refresh = true;
                }
                _ => {}
            }
            if refresh {
                if state.tasks[index].active {
                    state.reveal_task(index);
                }
                state.request_redraw(qh);
            }
        }
    }
}

impl ShmHandler for RicePlate {
    fn shm_state(&mut self) -> &mut Shm {
        &mut self.shm
    }
}

delegate_registry!(RicePlate);
impl ProvidesRegistryState for RicePlate {
    fn registry(&mut self) -> &mut RegistryState {
        &mut self.registry
    }
    registry_handlers![OutputState, SeatState];
}
smithay_client_toolkit::delegate_dispatch2!(RicePlate);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shared_panel_painter_renders_on_independent_output_buffers() {
        let style = recipe::parse(
            include_str!("../../../tests/fixtures/riceplate-desktop-v5.json"),
            Some("mockup-desktop"),
        ).unwrap();
        let width = 800;
        let height = style.height;
        let mut first = vec![0_u8; (width * height * 4) as usize];
        let mut second = vec![0_u8; (width * height * 4) as usize];
        paint_panel(&mut first, width, height, &style, &[], "12:00", 0, None);
        paint_panel(&mut second, width, height, &style, &[], "12:00", 0, None);
        assert_eq!(first, second);
        assert_eq!(&first[(width * (height / 2) + 400) as usize * 4..][..4],
                   &style.background.to_le_bytes());
        assert!(first.chunks_exact(4).any(|pixel|
            pixel == style.active.to_le_bytes()));
    }

    #[test]
    fn keyboard_focus_frame_only_marks_the_selected_panel_widget() {
        let style = recipe::load("classic").unwrap();
        let width = 960;
        let height = style.height;
        let len = (width * height * 4) as usize;
        let mut normal = vec![0; len];
        let mut selected = vec![0; len];
        paint_panel(&mut normal, width, height, &style, &[], "12:00", 0, None);
        paint_panel(&mut selected, width, height, &style, &[], "12:00", 0,
                    Some(KeyboardTarget::Launcher));
        assert_ne!(normal, selected);
        let launcher = recipe::layout(&style, width, 0).into_iter()
            .find(|item| item.widget == Widget::Launcher).unwrap();
        let pixel = ((2 * width + launcher.x + 10) * 4) as usize;
        assert_eq!(&selected[pixel..pixel + 4], &style.foreground.to_le_bytes());
    }

    #[test]
    fn calendar_painter_renders_actual_month_and_day_states() {
        let style = recipe::load("classic").unwrap();
        let today = chrono::NaiveDate::from_ymd_opt(2024, 2, 29).unwrap();
        let mut state = CalendarState::new(today);
        state.open(today);
        let mut february = vec![0; (calendar::WIDTH * calendar::HEIGHT * 4) as usize];
        let mut march = vec![0; february.len()];
        paint_calendar(&mut february, &style, &state);
        assert_eq!(&february[..4], &style.active.to_le_bytes());
        assert!(february.chunks_exact(4).any(|pixel|
            pixel == style.foreground.to_le_bytes()));
        state.shift(1);
        paint_calendar(&mut march, &style, &state);
        assert_ne!(february, march, "real month names/days must change the pixels");
    }

    #[test]
    fn desktop_icon_paint_preserves_transparent_background() {
        let icon = recipe::DesktopIcon {
            label: "Terminal".into(),
            action: "terminal".into(),
            x: 32,
            y: 112,
        };
        let mut pixels = vec![255; (recipe::ICON_WIDTH * recipe::ICON_HEIGHT * 4) as usize];
        paint_icon(&mut pixels, &icon, 0xff4179aa, 0xfff3f7fa, false);
        assert_eq!(&pixels[0..4], &[0, 0, 0, 0]);
        assert!(pixels
            .chunks_exact(4)
            .any(|pixel| pixel == 0xff4179aa_u32.to_le_bytes()));
        assert!(pixels
            .chunks_exact(4)
            .any(|pixel| pixel == 0xfff3f7fa_u32.to_le_bytes()));
        paint_icon(&mut pixels, &icon, 0xff4179aa, 0xfff3f7fa, true);
        assert_eq!(&pixels[0..4], &0xfff3f7fa_u32.to_le_bytes());
        assert_eq!(
            &pixels[((recipe::ICON_HEIGHT - 1) * recipe::ICON_WIDTH * 4) as usize..][..4],
            &0xfff3f7fa_u32.to_le_bytes(),
        );
    }

    #[test]
    fn draw_clips_to_surface_bounds() {
        let mut pixels = vec![0_u8; 4 * 3 * 4];
        fill_rect(&mut pixels, 4, 3, 2, 1, 20, 20, 0xff4179aa);
        assert_eq!(&pixels[0..4], &[0, 0, 0, 0]);
        assert_eq!(
            &pixels[(2 * 4 + 3) * 4..(2 * 4 + 4) * 4],
            &0xff4179aa_u32.to_le_bytes()
        );
    }

    #[test]
    fn label_pixels_come_from_font_glyphs() {
        let mut pixels = vec![0_u8; 20 * 12 * 4];
        draw_text(&mut pixels, 20, 12, 0, 0, "A", 0xfff3f7fa);
        assert!(pixels
            .chunks_exact(4)
            .any(|color| color == 0xfff3f7fa_u32.to_le_bytes()));
    }

    #[test]
    fn labels_are_bounded_and_have_fallbacks() {
        assert_eq!(
            task_groups::task_label("", "org.example.Terminal"),
            "org.example.Termin"
        );
        assert_eq!(task_groups::task_label("", ""), "Window");
        assert_eq!(task_groups::task_label("Readme", "org.example"), "Readme");
    }

    #[test]
    fn clock_format_is_fixed_width_and_minute_sized() {
        let time = chrono::NaiveTime::from_hms_opt(2, 3, 59).unwrap();
        assert_eq!(time.format("%H:%M").to_string(), "02:03");
        assert!(next_clock_timeout() <= Duration::from_secs(60));
        assert!(!clock_now().is_empty());
    }

    #[test]
    fn native_menu_draws_real_recipe_groups_without_opaque_overlay_elsewhere() {
        let style = recipe::parse(
            include_str!("../../../tests/fixtures/riceplate-desktop-v5.json"),
            Some("mockup-desktop"),
        ).unwrap();
        let menu = style.menu.as_ref().unwrap();
        let mut state = MenuState::default();
        state.open();
        let mut canvas = vec![0; (native_menu::WIDTH * native_menu::HEIGHT * 4) as usize];
        paint_menu(&mut canvas, menu, &style, &state);
        assert_eq!(&canvas[0..4], &style.active.to_le_bytes());
        assert_eq!(&canvas[(100 * native_menu::WIDTH * 4) as usize..][..4],
                   &style.background.to_le_bytes());
        assert_eq!(state.current_action(menu), Some("applications"));
        state.group_by(menu, 1);
        assert_eq!(state.current_action(menu), Some("lock"));
    }
}
