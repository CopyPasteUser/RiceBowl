//! Native RicePlate experiment: an input-capable, idle event-driven layer surface.
//! No session takeover: launch only inside an already running Wayland session.

use std::{error::Error, process::Command, time::Duration};

use chrono::{Local, Timelike};
use font8x8::{UnicodeFonts, BASIC_FONTS};
mod recipe;
mod desktop_layout;
mod task_groups;
use recipe::{Hit, PanelStyle, Widget};
use task_groups::{TaskGroup, WindowInfo};
use smithay_client_toolkit::{
    compositor::{CompositorHandler, CompositorState, FrameCallbackData},
    delegate_registry,
    output::{OutputHandler, OutputState},
    reexports::{
        calloop::EventLoop,
        calloop_wayland_source::WaylandSource,
    },
    registry::{ProvidesRegistryState, RegistryState},
    registry_handlers,
    seat::{
        pointer::{PointerEvent, PointerEventKind, PointerHandler},
        Capability, SeatHandler, SeatState,
    },
    shell::{
        wlr_layer::{Anchor, KeyboardInteractivity, Layer, LayerShell, LayerShellHandler,
                    LayerSurface, LayerSurfaceConfigure},
        WaylandSurface,
    },
    shm::{slot::SlotPool, Shm, ShmHandler},
};
use wayland_client::{
    globals::registry_queue_init,
    protocol::{wl_output, wl_pointer, wl_seat, wl_shm, wl_surface},
    Connection, Dispatch, QueueHandle,
};
use wayland_protocols_wlr::foreign_toplevel::v1::client::{
    zwlr_foreign_toplevel_handle_v1::{self, ZwlrForeignToplevelHandleV1},
    zwlr_foreign_toplevel_manager_v1::{self, ZwlrForeignToplevelManagerV1},
};

const MAX_WIDTH: u32 = 16384;
const MAX_HEIGHT: u32 = 256;
const BTN_LEFT: u32 = 0x110;

fn clock_now() -> String {
    Local::now().format("%H:%M").to_string()
}

fn next_clock_timeout() -> Duration {
    let now = Local::now();
    let milliseconds = u64::from(60 - now.second()) * 1000
        - u64::from(now.nanosecond() / 1_000_000);
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
        println!("Usage: riceplate-native [--recipe classic|chrome|/absolute/private.json]");
        return Ok(());
    }
    let recipe_name = match arguments.as_slice() {
        [] => "classic",
        [flag, recipe] if flag == "--recipe" => recipe.as_str(),
        _ => return Err("Usage: riceplate-native [--recipe classic|chrome|/absolute/private.json]".into()),
    };
    let recipe = recipe::load(recipe_name)?;
    let conn = Connection::connect_to_env()?;
    let (globals, event_queue) = registry_queue_init(&conn)?;
    let qh = event_queue.handle();
    let mut event_loop: EventLoop<RicePlate> = EventLoop::try_new()?;
    WaylandSource::new(conn.clone(), event_queue).insert(event_loop.handle())?;
    let compositor = CompositorState::bind(&globals, &qh)?;
    let layer_shell = LayerShell::bind(&globals, &qh)?;
    let shm = Shm::bind(&globals, &qh)?;
    let toplevel_manager: Option<ZwlrForeignToplevelManagerV1> =
        globals.bind(&qh, 1..=3, ()).ok();
    if toplevel_manager.is_none() {
        eprintln!("RicePlate: compositor lacks wlr-foreign-toplevel-management; taskbar disabled");
    }
    let layer = layer_shell.create_layer_surface(
        &qh, compositor.create_surface(&qh), Layer::Top, Some("riceplate-preview"), None,
    );
    let edge = if recipe.top { Anchor::TOP } else { Anchor::BOTTOM };
    layer.set_anchor(edge | Anchor::LEFT | Anchor::RIGHT);
    layer.set_size(0, recipe.height);
    layer.set_exclusive_zone(recipe.height as i32);
    layer.set_keyboard_interactivity(KeyboardInteractivity::None);
    layer.commit();

    // One small Bottom-layer surface per icon: transparent desktop space is
    // never covered by a full-screen input-catching window.
    let mut icon_layers = Vec::new();
    for icon in &recipe.desktop_icons {
        let surface = layer_shell.create_layer_surface(
            &qh, compositor.create_surface(&qh), Layer::Bottom,
            Some("riceplate-desktop-icon"), None,
        );
        surface.set_anchor(Anchor::TOP | Anchor::LEFT);
        surface.set_size(recipe::ICON_WIDTH, recipe::ICON_HEIGHT);
        surface.set_margin(icon.y as i32, 0, 0, icon.x as i32);
        surface.set_exclusive_zone(-1);
        surface.set_keyboard_interactivity(KeyboardInteractivity::None);
        surface.commit();
        icon_layers.push(IconLayer {
            surface, pool: None, configured: false, output: None,
            placed: Some((icon.x, icon.y)),
        });
    }

    let mut app = RicePlate {
        registry: RegistryState::new(&globals),
        outputs: OutputState::new(&globals, &qh),
        seats: SeatState::new(&globals, &qh),
        shm,
        layer,
        icon_layers,
        recipe,
        clock: clock_now(),
        pointer: None,
        primary_seat: None,
        primary_output: None,
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
    while !app.closed {
        // Calloop sleeps on Wayland's fd and wakes at the next minute,
        // so the clock updates without any resident 1 Hz poll/frame loop.
        event_loop.dispatch(Some(next_clock_timeout()), &mut app)?;
        let current = clock_now();
        if app.clock != current {
            app.clock = current;
            app.request_redraw(&qh);
        }
    }
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

struct RicePlate {
    registry: RegistryState,
    outputs: OutputState,
    seats: SeatState,
    shm: Shm,
    layer: LayerSurface,
    icon_layers: Vec<IconLayer>,
    recipe: PanelStyle,
    clock: String,
    pointer: Option<wl_pointer::WlPointer>,
    primary_seat: Option<wl_seat::WlSeat>,
    primary_output: Option<wl_output::WlOutput>,
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
    fn redraw_icon(&mut self, index: usize) {
        let Some(layer) = self.icon_layers.get_mut(index) else { return };
        if !layer.configured || layer.placed.is_none() { return; }
        let width = recipe::ICON_WIDTH;
        let height = recipe::ICON_HEIGHT;
        let surface = layer.surface.wl_surface();
        let pool = layer.pool.as_mut().expect("configured icon has pool");
        let (buffer, canvas) = match pool.create_buffer(
            width as i32, height as i32, (width * 4) as i32, wl_shm::Format::Argb8888,
        ) {
            Ok(result) => result,
            Err(error) => {
                eprintln!("RicePlate: desktop icon buffer unavailable: {error}");
                return;
            }
        };
        let icon = &self.recipe.desktop_icons[index];
        paint_icon(canvas, icon, self.recipe.active, self.recipe.foreground);
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
        if width <= 0 || height <= 0 { return None; }
        Some((width as u32, height as u32))
    }

    fn reflow_icons(&mut self) {
        // The current preview creates one set of layer surfaces, owned by the
        // compositing output to which they were assigned. Full multi-output
        // desktop replication is a separate, gated milestone.
        let Some(output) = self.primary_output.clone().or_else(||
                self.icon_layers.iter().find_map(|icon| icon.output.clone())) else {
            return;
        };
        let Some((width, height)) = self.logical_output_size(&output) else { return; };
        let placements = desktop_layout::place(&self.recipe.desktop_icons, width, height,
                                                self.recipe.top, self.recipe.height);
        for (index, placement) in placements.into_iter().enumerate() {
            let restored = {
                let layer = &mut self.icon_layers[index];
                if layer.placed == placement { continue; }
                let restored = layer.placed.is_none() && placement.is_some();
                layer.placed = placement;
                if let Some((x, y)) = placement {
                    layer.surface.set_margin(y as i32, 0, 0, x as i32);
                } else {
                    // Keep the layer-shell role mapped: a null-buffer commit
                    // would permanently destroy it under the protocol. Park
                    // the icon beyond the output until room is available.
                    layer.surface.set_margin(height as i32 + recipe::ICON_HEIGHT as i32,
                                             0, 0, width as i32 + recipe::ICON_WIDTH as i32);
                }
                layer.surface.commit();
                restored && layer.configured
            };
            if restored { self.redraw_icon(index); }
        }
    }

    fn grouped_tasks(&self) -> Vec<TaskGroup> {
        task_groups::group_windows(self.tasks.iter().enumerate().map(|(index, task)| {
            WindowInfo {
                index, app_id: &task.app_id, title: &task.title,
                active: task.active, ready: task.ready,
            }
        }))
    }

    fn request_redraw(&mut self, qh: &QueueHandle<Self>) {
        self.needs_redraw = true;
        if !self.frame_pending { self.redraw(qh); }
    }

    fn reveal_task(&mut self, index: usize) {
        let groups = self.grouped_tasks();
        let Some(group_index) = groups.iter().position(|group| group.members.contains(&index))
            else { return };
        let Some(view) = recipe::task_view(
            &self.recipe, self.width, groups.len(), self.task_offset,
        ) else { return };
        if group_index < view.start {
            self.task_offset = group_index;
        } else if group_index >= view.start + view.slots {
            self.task_offset = group_index + 1 - view.slots;
        }
    }

    fn redraw(&mut self, qh: &QueueHandle<Self>) {
        if !self.configured || self.width == 0 || self.height == 0 {
            return;
        }
        let width = self.width;
        let height = self.height;
        let groups = self.grouped_tasks();
        let surface = self.layer.wl_surface();
        let stride = (width * 4) as i32;
        let pool = self.pool.as_mut().expect("configured surface has a memory pool");
        let (buffer, canvas) = match pool.create_buffer(
            width as i32, height as i32, stride, wl_shm::Format::Argb8888,
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
        for pixel in canvas.chunks_exact_mut(4) {
            pixel.copy_from_slice(&self.recipe.background.to_le_bytes());
        }
        for placed in recipe::layout(&self.recipe, width, groups.len()) {
            match placed.widget {
                Widget::Launcher => {
                    fill_rect(canvas, width, height, placed.x, 0, placed.width, height,
                              self.recipe.active);
                    draw_text(canvas, width, height,
                              placed.x + placed.width.saturating_sub(32) / 2, height / 2 - 4,
                              "Apps", self.recipe.foreground);
                }
                Widget::Tasks => {
                    let Some(view) = recipe::task_view(
                        &self.recipe, width, groups.len(), self.task_offset,
                    ) else { continue };
                    for (index, group) in groups.iter().skip(view.start)
                        .take(view.slots).enumerate() {
                        let consumed = (index as u32) * view.cell_width;
                        let x = placed.x + consumed;
                        let cell_width = if index + 1 == view.slots {
                            view.content_width - consumed
                        } else { view.cell_width };
                        if group.active {
                            fill_rounded_rect(canvas, width, height, x, 0,
                                              cell_width.saturating_sub(2), height,
                                              self.recipe.task_radius, self.recipe.active);
                        }
                        let label = task_groups::visible_label(group, cell_width);
                        draw_text(canvas, width, height, x + 10, height / 2 - 4,
                                  &label, self.recipe.foreground);
                    }
                    if view.prev {
                        draw_text(canvas, width, height,
                                  placed.x + view.content_width + 8,
                                  height / 2 - 4, "<", self.recipe.foreground);
                    }
                    if view.next {
                        draw_text(canvas, width, height,
                                  placed.x + view.content_width + 32,
                                  height / 2 - 4, ">", self.recipe.foreground);
                    }
                }
                Widget::Clock => {
                    draw_text(canvas, width, height,
                              placed.x + placed.width.saturating_sub(40) / 2,
                              height / 2 - 4, &self.clock, self.recipe.foreground);
                }
                Widget::Gap(_) => {}
                Widget::Label(index) => {
                    if let Some(label) = self.recipe.labels.get(index as usize) {
                        draw_text(canvas, width, height,
                                  placed.x + self.recipe.label_padding,
                                  height / 2 - 4, label, self.recipe.foreground);
                    }
                }
            }
        }
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

fn paint_icon(canvas: &mut [u8], icon: &recipe::DesktopIcon, active: u32, foreground: u32) {
    let width = recipe::ICON_WIDTH;
    let height = recipe::ICON_HEIGHT;
    canvas.fill(0); // Leave the surrounding desktop visible.
    let glyph = match icon.action.as_str() {
        "applications" => "Apps", "terminal" => ">_", "lock" => "Lock", _ => return,
    };
    fill_rounded_rect(canvas, width, height, 24, 4, 56, 48, 10, active);
    // Contrast backplate prevents white labels from vanishing on bright rices.
    fill_rounded_rect(canvas, width, height, 2, 58, 100, 26, 6, 0xb020_2c36);
    draw_text(canvas, width, height, 52 - (glyph.len() as u32 * 4), 24,
              glyph, foreground);
    draw_text(canvas, width, height, (width - icon.label.len() as u32 * 8) / 2,
              66, &icon.label, foreground);
}

fn fill_rect(canvas: &mut [u8], width: u32, height: u32,
             x: u32, y: u32, w: u32, h: u32, color: u32) {
    for row in y..y.saturating_add(h).min(height) {
        for column in x..x.saturating_add(w).min(width) {
            let index = ((row * width + column) * 4) as usize;
            canvas[index..index + 4].copy_from_slice(&color.to_le_bytes());
        }
    }
}

fn fill_rounded_rect(canvas: &mut [u8], width: u32, height: u32,
                     x: u32, y: u32, w: u32, h: u32, radius: u32, color: u32) {
    let r = radius.min(w / 2).min(h / 2);
    if r == 0 { fill_rect(canvas, width, height, x, y, w, h, color); return; }
    let corner = (r as i64 - 1).pow(2);
    for py in 0..h.min(height.saturating_sub(y)) {
        for px in 0..w.min(width.saturating_sub(x)) {
            let dx = if px < r { r - 1 - px } else { px.saturating_sub(w - r) };
            let dy = if py < r { r - 1 - py } else { py.saturating_sub(h - r) };
            if (dx as i64).pow(2) + (dy as i64).pow(2) <= corner {
                let index = (((y + py) * width + x + px) * 4) as usize;
                canvas[index..index + 4].copy_from_slice(&color.to_le_bytes());
            }
        }
    }
}

fn draw_text(canvas: &mut [u8], width: u32, height: u32,
             x: u32, y: u32, text: &str, color: u32) {
    for (offset, character) in text.chars().enumerate() {
        let Some(bitmap) = BASIC_FONTS.get(character) else { continue };
        let origin = x.saturating_add((offset as u32).saturating_mul(8));
        for (row, bits) in bitmap.iter().enumerate() {
            for column in 0..8_u32 {
                if *bits & (1_u8 << column) != 0 {
                    fill_rect(canvas, width, height, origin + column,
                              y + row as u32, 1, 1, color);
                }
            }
        }
    }
}

impl CompositorHandler for RicePlate {
    fn scale_factor_changed(&mut self, _: &Connection, _: &QueueHandle<Self>,
                            _: &wl_surface::WlSurface, _: i32) {}
    fn transform_changed(&mut self, _: &Connection, _: &QueueHandle<Self>,
                         _: &wl_surface::WlSurface, _: wl_output::Transform) {}
    fn frame(&mut self, _: &Connection, qh: &QueueHandle<Self>,
             surface: &wl_surface::WlSurface, _: u32) {
        if surface != self.layer.wl_surface() { return; }
        self.frame_pending = false;
        if self.needs_redraw { self.redraw(qh); }
    }
    fn surface_enter(&mut self, _: &Connection, _: &QueueHandle<Self>,
                     surface: &wl_surface::WlSurface, output: &wl_output::WlOutput) {
        if surface == self.layer.wl_surface() {
            self.primary_output = Some(output.clone());
            self.reflow_icons();
            return;
        }
        if let Some(layer) = self.icon_layers.iter_mut().find(|icon|
                icon.surface.wl_surface() == surface) {
            layer.output = Some(output.clone());
            self.reflow_icons();
        }
    }
    fn surface_leave(&mut self, _: &Connection, _: &QueueHandle<Self>,
                     surface: &wl_surface::WlSurface, output: &wl_output::WlOutput) {
        if surface == self.layer.wl_surface() {
            if self.primary_output.as_ref() == Some(output) { self.primary_output = None; }
            return;
        }
        if let Some(layer) = self.icon_layers.iter_mut().find(|icon|
                icon.surface.wl_surface() == surface) {
            if layer.output.as_ref() == Some(output) { layer.output = None; }
        }
    }
}

impl LayerShellHandler for RicePlate {
    fn closed(&mut self, _: &Connection, _: &QueueHandle<Self>, layer: &LayerSurface) {
        if layer.wl_surface() == self.layer.wl_surface() {
            self.closed = true;
        } else if let Some(icon) = self.icon_layers.iter_mut().find(|icon|
            icon.surface.wl_surface() == layer.wl_surface()) {
            icon.configured = false;
        }
    }
    fn configure(&mut self, _: &Connection, qh: &QueueHandle<Self>, layer: &LayerSurface,
                 config: LayerSurfaceConfigure, _: u32) {
        if let Some(index) = self.icon_layers.iter().position(|icon|
            icon.surface.wl_surface() == layer.wl_surface()) {
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
        if layer.wl_surface() != self.layer.wl_surface() { return; }
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
    fn output_state(&mut self) -> &mut OutputState { &mut self.outputs }
    fn new_output(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {
        self.reflow_icons();
    }
    fn update_output(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {
        self.reflow_icons();
    }
    fn output_destroyed(&mut self, _: &Connection, _: &QueueHandle<Self>, output: wl_output::WlOutput) {
        if self.primary_output.as_ref() == Some(&output) { self.primary_output = None; }
        for icon in &mut self.icon_layers {
            if icon.output.as_ref() == Some(&output) { icon.output = None; }
        }
        self.reflow_icons();
    }
}

impl SeatHandler for RicePlate {
    fn seat_state(&mut self) -> &mut SeatState { &mut self.seats }
    fn new_seat(&mut self, _: &Connection, _: &QueueHandle<Self>, seat: wl_seat::WlSeat) {
        if self.primary_seat.is_none() { self.primary_seat = Some(seat); }
    }
    fn new_capability(&mut self, _: &Connection, qh: &QueueHandle<Self>,
                      seat: wl_seat::WlSeat, capability: Capability) {
        if capability == Capability::Pointer && self.pointer.is_none() {
            match self.seats.get_pointer(qh, &seat) {
                Ok(pointer) => self.pointer = Some(pointer),
                Err(error) => eprintln!("RicePlate: pointer unavailable: {error}"),
            }
        }
    }
    fn remove_capability(&mut self, _: &Connection, _: &QueueHandle<Self>,
                         _: wl_seat::WlSeat, capability: Capability) {
        if capability == Capability::Pointer {
            if let Some(pointer) = self.pointer.take() { pointer.release(); }
        }
    }
    fn remove_seat(&mut self, _: &Connection, _: &QueueHandle<Self>, seat: wl_seat::WlSeat) {
        if self.primary_seat.as_ref() == Some(&seat) {
            self.primary_seat = None;
        }
    }
}

impl PointerHandler for RicePlate {
    fn pointer_frame(&mut self, _: &Connection, qh: &QueueHandle<Self>,
                     _: &wl_pointer::WlPointer, events: &[PointerEvent]) {
        for event in events {
            if let Some(index) = self.icon_layers.iter().position(|icon|
                &event.surface == icon.surface.wl_surface()) {
                if self.icon_layers[index].placed.is_none() { continue; }
                if let PointerEventKind::Press { button: BTN_LEFT, .. } = event.kind {
                    let icon = &self.recipe.desktop_icons[index];
                    let (program, args): (&str, &[&str]) = match icon.action.as_str() {
                        "applications" => ("fuzzel", &[]),
                        "terminal" => ("foot", &[]),
                        "lock" => ("swaylock", &["-f"]),
                        _ => continue,
                    };
                    if let Err(error) = Command::new(program).args(args).spawn() {
                        eprintln!("RicePlate: cannot run desktop action {program}: {error}");
                    }
                }
                continue;
            }
            if &event.surface != self.layer.wl_surface() { continue }
            if let PointerEventKind::Press { button, .. } = event.kind {
                if button == BTN_LEFT && event.position.1 >= 0.0
                    && event.position.1 < f64::from(self.height) {
                    let groups = self.grouped_tasks();
                    match recipe::hit(event.position.0, self.width,
                                      groups.len(), self.task_offset, &self.recipe) {
                        Some(Hit::Launcher) => {
                            if let Err(error) = Command::new("fuzzel").spawn() {
                                eprintln!("RicePlate: cannot open application launcher: {error}");
                            }
                        }
                        Some(Hit::Task(index)) => {
                            if let Some(group) = groups.get(index) {
                                let active_index = group.members.iter().copied()
                                    .find(|&member| self.tasks[member].active);
                                let (target, minimize) =
                                    task_groups::click_target(group, active_index);
                                if minimize {
                                    self.tasks[target].handle.set_minimized();
                                } else if let Some(seat) = self.primary_seat.as_ref() {
                                    self.tasks[target].handle.activate(seat);
                                }
                            }
                        }
                        Some(Hit::PreviousTasks) => {
                            if let Some(view) = recipe::task_view(
                                &self.recipe, self.width, groups.len(), self.task_offset,
                            ) {
                                self.task_offset = view.start.saturating_sub(view.slots);
                                self.request_redraw(qh);
                            }
                        }
                        Some(Hit::NextTasks) => {
                            if let Some(view) = recipe::task_view(
                                &self.recipe, self.width, groups.len(), self.task_offset,
                            ) {
                                self.task_offset = (view.start + view.slots)
                                    .min(groups.len().saturating_sub(view.slots));
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
        state: &mut Self, _: &ZwlrForeignToplevelManagerV1,
        event: zwlr_foreign_toplevel_manager_v1::Event, _: &(),
        _: &Connection, qh: &QueueHandle<Self>,
    ) {
        match event {
            zwlr_foreign_toplevel_manager_v1::Event::Toplevel { toplevel } => {
                if state.tasks.len() >= recipe::MAX_TRACKED_TASKS {
                    toplevel.destroy();
                } else {
                    state.tasks.push(Task {
                        handle: toplevel, title: String::new(), app_id: String::new(),
                        active: false, ready: false,
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
        state: &mut Self, proxy: &ZwlrForeignToplevelHandleV1,
        event: zwlr_foreign_toplevel_handle_v1::Event, _: &(),
        _: &Connection, qh: &QueueHandle<Self>,
    ) {
        if let zwlr_foreign_toplevel_handle_v1::Event::Closed = event {
            if let Some(index) = state.tasks.iter().position(|task| task.handle == *proxy) {
                state.tasks.remove(index).handle.destroy();
                state.task_offset = state.task_offset
                    .min(state.grouped_tasks().len().saturating_sub(1));
                if let Some(active) = state.tasks.iter().position(|task| task.active && task.ready) {
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
                zwlr_foreign_toplevel_handle_v1::Event::Title { title } =>
                    task.title = title.chars().take(256).collect(),
                zwlr_foreign_toplevel_handle_v1::Event::AppId { app_id } =>
                    task.app_id = app_id.chars().take(256).collect(),
                zwlr_foreign_toplevel_handle_v1::Event::State { state: states } =>
                    task.active = states.chunks_exact(4).any(|raw|
                        u32::from_ne_bytes(raw.try_into().unwrap_or_default()) == 2),
                zwlr_foreign_toplevel_handle_v1::Event::Done => {
                    task.ready = true;
                    refresh = true;
                }
                _ => {}
            }
            if refresh {
                if state.tasks[index].active { state.reveal_task(index); }
                state.request_redraw(qh);
            }
        }
    }
}

impl ShmHandler for RicePlate {
    fn shm_state(&mut self) -> &mut Shm { &mut self.shm }
}

delegate_registry!(RicePlate);
impl ProvidesRegistryState for RicePlate {
    fn registry(&mut self) -> &mut RegistryState { &mut self.registry }
    registry_handlers![OutputState, SeatState];
}
smithay_client_toolkit::delegate_dispatch2!(RicePlate);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn desktop_icon_paint_preserves_transparent_background() {
        let icon = recipe::DesktopIcon {
            label: "Terminal".into(), action: "terminal".into(), x: 32, y: 112,
        };
        let mut pixels = vec![255; (recipe::ICON_WIDTH * recipe::ICON_HEIGHT * 4) as usize];
        paint_icon(&mut pixels, &icon, 0xff4179aa, 0xfff3f7fa);
        assert_eq!(&pixels[0..4], &[0, 0, 0, 0]);
        assert!(pixels.chunks_exact(4).any(|pixel| pixel == 0xff4179aa_u32.to_le_bytes()));
        assert!(pixels.chunks_exact(4).any(|pixel| pixel == 0xfff3f7fa_u32.to_le_bytes()));
    }

    #[test]
    fn draw_clips_to_surface_bounds() {
        let mut pixels = vec![0_u8; 4 * 3 * 4];
        fill_rect(&mut pixels, 4, 3, 2, 1, 20, 20, 0xff4179aa);
        assert_eq!(&pixels[0..4], &[0, 0, 0, 0]);
        assert_eq!(&pixels[(2 * 4 + 3) * 4..(2 * 4 + 4) * 4],
                   &0xff4179aa_u32.to_le_bytes());
    }

    #[test]
    fn label_pixels_come_from_font_glyphs() {
        let mut pixels = vec![0_u8; 20 * 12 * 4];
        draw_text(&mut pixels, 20, 12, 0, 0, "A", 0xfff3f7fa);
        assert!(pixels.chunks_exact(4).any(|color| color == 0xfff3f7fa_u32.to_le_bytes()));
    }

    #[test]
    fn labels_are_bounded_and_have_fallbacks() {
        assert_eq!(task_groups::task_label("", "org.example.Terminal"), "org.example.Termin");
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

}
