//! Native RicePlate experiment: an input-capable, idle event-driven layer surface.
//! No session takeover: launch only inside an already running Wayland session.

use std::{error::Error, process::Command};

use font8x8::{UnicodeFonts, BASIC_FONTS};
use smithay_client_toolkit::{
    compositor::{CompositorHandler, CompositorState},
    delegate_registry,
    output::{OutputHandler, OutputState},
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
    Connection, QueueHandle,
};

const BAR_HEIGHT: u32 = 40;
const MAX_WIDTH: u32 = 16384;
const MAX_HEIGHT: u32 = 256;
const LAUNCHER_WIDTH: u32 = 104;
const BTN_LEFT: u32 = 0x110;
const DARK: u32 = 0xff203c59;
const ACCENT: u32 = 0xff4179aa;
const TEXT: u32 = 0xfff3f7fa;

fn main() -> Result<(), Box<dyn Error>> {
    // Explicit test entrypoint for CI and packagers; no Wayland connection.
    if std::env::args().skip(1).any(|arg| arg == "--version") {
        println!("riceplate-native 0.1.0 (experimental)");
        return Ok(());
    }
    let conn = Connection::connect_to_env()?;
    let (globals, mut event_queue) = registry_queue_init(&conn)?;
    let qh = event_queue.handle();
    let compositor = CompositorState::bind(&globals, &qh)?;
    let layer_shell = LayerShell::bind(&globals, &qh)?;
    let shm = Shm::bind(&globals, &qh)?;
    let layer = layer_shell.create_layer_surface(
        &qh, compositor.create_surface(&qh), Layer::Top, Some("riceplate-preview"), None,
    );
    layer.set_anchor(Anchor::BOTTOM | Anchor::LEFT | Anchor::RIGHT);
    layer.set_size(0, BAR_HEIGHT);
    layer.set_exclusive_zone(BAR_HEIGHT as i32);
    layer.set_keyboard_interactivity(KeyboardInteractivity::None);
    layer.commit();

    let mut app = RicePlate {
        registry: RegistryState::new(&globals),
        outputs: OutputState::new(&globals, &qh),
        seats: SeatState::new(&globals, &qh),
        shm,
        layer,
        pointer: None,
        pool: None,
        width: 0,
        height: 0,
        configured: false,
        closed: false,
    };
    while !app.closed {
        event_queue.blocking_dispatch(&mut app)?;
    }
    Ok(())
}

struct RicePlate {
    registry: RegistryState,
    outputs: OutputState,
    seats: SeatState,
    shm: Shm,
    layer: LayerSurface,
    pointer: Option<wl_pointer::WlPointer>,
    pool: Option<SlotPool>,
    width: u32,
    height: u32,
    configured: bool,
    closed: bool,
}

impl RicePlate {
    fn redraw(&mut self) {
        if !self.configured || self.width == 0 || self.height == 0 {
            return;
        }
        let width = self.width;
        let height = self.height;
        let surface = self.layer.wl_surface();
        let stride = (width * 4) as i32;
        let pool = self.pool.as_mut().expect("configured surface has a memory pool");
        let (buffer, canvas) = match pool.create_buffer(
            width as i32, height as i32, stride, wl_shm::Format::Argb8888,
        ) {
            Ok(result) => result,
            Err(error) => {
                eprintln!("RicePlate: cannot allocate Wayland buffer: {error}");
                self.closed = true;
                return;
            }
        };
        for pixel in canvas.chunks_exact_mut(4) {
            pixel.copy_from_slice(&DARK.to_le_bytes());
        }
        fill_rect(canvas, width, height, 0, 0, LAUNCHER_WIDTH, height, ACCENT);
        draw_text(canvas, width, height, 27, 16, "Apps", TEXT);
        draw_text(canvas, width, height, LAUNCHER_WIDTH + 16, 16,
                  "RicePlate preview", TEXT);
        surface.damage_buffer(0, 0, width as i32, height as i32);
        if let Err(error) = buffer.attach_to(surface) {
            eprintln!("RicePlate: failed to attach Wayland buffer: {error}");
            self.closed = true;
            return;
        }
        self.layer.commit();
    }
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
    fn frame(&mut self, _: &Connection, _: &QueueHandle<Self>,
             _: &wl_surface::WlSurface, _: u32) {}
    fn surface_enter(&mut self, _: &Connection, _: &QueueHandle<Self>,
                     _: &wl_surface::WlSurface, _: &wl_output::WlOutput) {}
    fn surface_leave(&mut self, _: &Connection, _: &QueueHandle<Self>,
                     _: &wl_surface::WlSurface, _: &wl_output::WlOutput) {}
}

impl LayerShellHandler for RicePlate {
    fn closed(&mut self, _: &Connection, _: &QueueHandle<Self>, _: &LayerSurface) {
        self.closed = true;
    }
    fn configure(&mut self, _: &Connection, _: &QueueHandle<Self>, _: &LayerSurface,
                 config: LayerSurfaceConfigure, _: u32) {
        let width = config.new_size.0;
        let height = config.new_size.1;
        if width == 0 || width > MAX_WIDTH || height == 0 || height > MAX_HEIGHT {
            eprintln!("RicePlate: compositor proposed unsupported surface dimensions");
            self.closed = true;
            return;
        }
        if (width, height) != (self.width, self.height) {
            let byte_count = width as usize * height as usize * 4;
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
        self.redraw();
    }
}

impl OutputHandler for RicePlate {
    fn output_state(&mut self) -> &mut OutputState { &mut self.outputs }
    fn new_output(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {}
    fn update_output(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {}
    fn output_destroyed(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_output::WlOutput) {}
}

impl SeatHandler for RicePlate {
    fn seat_state(&mut self) -> &mut SeatState { &mut self.seats }
    fn new_seat(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_seat::WlSeat) {}
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
    fn remove_seat(&mut self, _: &Connection, _: &QueueHandle<Self>, _: wl_seat::WlSeat) {}
}

impl PointerHandler for RicePlate {
    fn pointer_frame(&mut self, _: &Connection, _: &QueueHandle<Self>,
                     _: &wl_pointer::WlPointer, events: &[PointerEvent]) {
        for event in events {
            if &event.surface != self.layer.wl_surface() { continue }
            if let PointerEventKind::Press { button, .. } = event.kind {
                if button == BTN_LEFT && event.position.0 >= 0.0
                    && event.position.0 < f64::from(LAUNCHER_WIDTH)
                    && event.position.1 >= 0.0
                    && event.position.1 < f64::from(self.height)
                {
                    if let Err(error) = Command::new("fuzzel").spawn() {
                        eprintln!("RicePlate: cannot open application launcher: {error}");
                    }
                }
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
    fn draw_clips_to_surface_bounds() {
        let mut pixels = vec![0_u8; 4 * 3 * 4];
        fill_rect(&mut pixels, 4, 3, 2, 1, 20, 20, ACCENT);
        assert_eq!(&pixels[0..4], &[0, 0, 0, 0]);
        assert_eq!(&pixels[(2 * 4 + 3) * 4..(2 * 4 + 4) * 4],
                   &ACCENT.to_le_bytes());
    }

    #[test]
    fn label_pixels_come_from_font_glyphs() {
        let mut pixels = vec![0_u8; 20 * 12 * 4];
        draw_text(&mut pixels, 20, 12, 0, 0, "A", TEXT);
        assert!(pixels.chunks_exact(4).any(|color| color == TEXT.to_le_bytes()));
    }
}
