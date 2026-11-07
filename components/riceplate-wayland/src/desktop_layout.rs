//! Deterministic icon placement in the logical dimensions of one Wayland output.
//! No file access, timers or per-frame work: recompute only on output changes.

use crate::recipe::{DesktopIcon, ICON_HEIGHT, ICON_WIDTH};

const GAP: u32 = 8;
pub const MAX_SAVED_POSITION: u32 = 16_384;

/// Cycle a keyboard selection through visible icon surfaces only. A hidden
/// icon must never receive Enter or keyboard-movement actions.
pub fn navigate(visible: &[bool], current: usize, delta: isize) -> Option<usize> {
    if visible.is_empty() || !visible.iter().any(|&item| item) { return None; }
    let mut next = current % visible.len();
    for _ in 0..visible.len() {
        next = (next as isize + delta).rem_euclid(visible.len() as isize) as usize;
        if visible[next] { return Some(next); }
    }
    None
}

/// Wayland pointer coordinates are surface-relative, including during a grab.
/// Use the current surface placement to prevent jumps as its margin moves.
pub fn dragged_to(current: (u32, u32), anchor: (f64, f64), pointer: (f64, f64)) -> (u32, u32) {
    let moved = |origin: u32, delta: f64| {
        (f64::from(origin) + delta).round().clamp(0.0, f64::from(MAX_SAVED_POSITION)) as u32
    };
    (moved(current.0, pointer.0 - anchor.0),
     moved(current.1, pointer.1 - anchor.1))
}

fn overlaps(x: u32, y: u32, other_x: u32, other_y: u32) -> bool {
    x.abs_diff(other_x) < ICON_WIDTH && y.abs_diff(other_y) < ICON_HEIGHT
}

/// Preserve each requested position if possible. Displaced icons use the
/// nearest free bounded grid cell; None means there is no safe hit area.
pub fn place(
    icons: &[DesktopIcon], width: u32, height: u32, panel_top: bool, panel_height: u32,
) -> Vec<Option<(u32, u32)>> {
    let upper = if panel_top { panel_height.saturating_add(GAP) } else { GAP };
    let lower = if panel_top { GAP } else { panel_height.saturating_add(GAP) };
    let Some(max_y) = height.checked_sub(lower.saturating_add(ICON_HEIGHT)) else {
        return vec![None; icons.len()];
    };
    let Some(max_x) = width.checked_sub(ICON_WIDTH) else {
        return vec![None; icons.len()];
    };
    if max_y < upper { return vec![None; icons.len()]; }

    let mut placed: Vec<(u32, u32)> = Vec::new();
    let mut result = Vec::with_capacity(icons.len());
    for icon in icons {
        let desired = (icon.x.min(max_x), icon.y.clamp(upper, max_y));
        let free = |(x, y): (u32, u32)| {
            placed.iter().all(|&(other_x, other_y)| !overlaps(x, y, other_x, other_y))
        };
        let selected = if free(desired) {
            Some(desired)
        } else {
            // At most 9*9 candidates, independent of output pixel count.
            // Eight recipe icons fit on normal 640x480 and larger displays.
            let mut candidates = Vec::new();
            for row in 0..=icons.len() {
                let y = upper.saturating_add((row as u32) * (ICON_HEIGHT + GAP));
                if y > max_y { break; }
                for col in 0..=icons.len() {
                    let x = (col as u32) * (ICON_WIDTH + GAP);
                    if x <= max_x && free((x, y)) {
                        candidates.push((x, y));
                    }
                }
            }
            candidates.into_iter().min_by_key(|&(x, y)| {
                (x.abs_diff(desired.0) + y.abs_diff(desired.1), y, x)
            })
        };
        if let Some(position) = selected { placed.push(position); }
        result.push(selected);
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    fn icon(x: u32, y: u32) -> DesktopIcon {
        DesktopIcon { label: "Apps".into(), action: "applications".into(), x, y }
    }

    #[test]
    fn keyboard_navigation_skips_hidden_icons_and_wraps() {
        let visible = [true, false, true, false];
        assert_eq!(navigate(&visible, 0, 1), Some(2));
        assert_eq!(navigate(&visible, 2, 1), Some(0));
        assert_eq!(navigate(&visible, 0, -1), Some(2));
        assert_eq!(navigate(&[false, false], 0, 1), None);
        assert_eq!(navigate(&[], 0, 1), None);
    }

    #[test]
    fn preserves_positions_on_large_output_without_hidden_overlaps() {
        let originals = [icon(32, 96), icon(32, 208), icon(152, 96)];
        assert_eq!(place(&originals, 1920, 1080, true, 40),
                   vec![Some((32, 96)), Some((32, 208)), Some((152, 96))]);
    }

    #[test]
    fn clamps_at_small_and_fractionally_scaled_logical_output_boundaries() {
        let originals = [icon(990, 700), icon(4000, 4000), icon(32, 96)];
        for (width, height) in [(1024, 768), (1093, 614)] {
            let positions = place(&originals, width, height, true, 40);
            assert!(positions.iter().all(Option::is_some));
            for (index, position) in positions.iter().enumerate() {
                let (x, y) = position.unwrap();
                assert!(x + ICON_WIDTH <= width, "icon {index} exceeds width");
                assert!(y >= 48 && y + ICON_HEIGHT <= height - GAP);
            }
            for left in 0..positions.len() {
                for right in (left + 1)..positions.len() {
                    let (x, y) = positions[left].unwrap();
                    let (other_x, other_y) = positions[right].unwrap();
                    assert!(!overlaps(x, y, other_x, other_y));
                }
            }
        }
    }

    #[test]
    fn reserves_bottom_panel_and_hides_icons_if_no_safe_hit_area() {
        let original = [icon(32, 700), icon(32, 700)];
        let placed = place(&original, 640, 480, false, 48);
        assert!(placed.iter().all(Option::is_some));
        assert!(placed.iter().all(|p| p.unwrap().1 + ICON_HEIGHT <= 424));
        assert_eq!(place(&original, 90, 300, true, 40), vec![None, None]);
        assert_eq!(place(&original, 640, 120, false, 48), vec![None, None]);
    }

    #[test]
    fn bounded_search_never_maps_multiple_icons_onto_one_pixel_region() {
        let eight: Vec<_> = (0..8).map(|i| icon(i * 104, 96)).collect();
        let placed = place(&eight, 104, 480, true, 40);
        assert!(placed.iter().any(Option::is_none));
        let visible: Vec<_> = placed.into_iter().flatten().collect();
        for (index, &(x, y)) in visible.iter().enumerate() {
            assert!(visible.iter().skip(index + 1).all(|&(ox, oy)|
                    !overlaps(x, y, ox, oy)));
        }
    }

    #[test]
    fn pointer_motion_translates_positions_without_underflow_or_jumps() {
        assert_eq!(dragged_to((32, 96), (20.0, 10.0), (60.0, 30.0)), (72, 116));
        assert_eq!(dragged_to((72, 116), (20.0, 10.0), (20.0, 10.0)), (72, 116));
        assert_eq!(dragged_to((32, 96), (20.0, 10.0), (-200.0, -200.0)), (0, 0));
        assert_eq!(dragged_to((16_380, 16_380), (0.0, 0.0), (100.0, 100.0)),
                   (MAX_SAVED_POSITION, MAX_SAVED_POSITION));
    }
}
