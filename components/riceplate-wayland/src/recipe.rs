//! Bounded, non-executable RicePlate recipes and shared widget geometry.
//! The Waybar adapter and native renderer consume the same schema-v1 JSON.

use std::{
    collections::HashSet,
    error::Error,
    fs::OpenOptions,
    io::Read,
    os::unix::fs::{MetadataExt, OpenOptionsExt},
    path::Path,
};

use serde::Deserialize;

pub const LAUNCHER_WIDTH: u32 = 104;
pub const TASK_WIDTH: u32 = 164;
pub const CLOCK_WIDTH: u32 = 96;
const MAX_RECIPE_BYTES: usize = 64 * 1024;
pub const MAX_TRACKED_TASKS: usize = 128;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Widget {
    Launcher,
    Tasks,
    Clock,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PlacedWidget {
    pub widget: Widget,
    pub x: u32,
    pub width: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hit {
    Launcher,
    Task(usize),
}

pub struct PanelStyle {
    pub height: u32,
    pub top: bool,
    pub sections: [Vec<Widget>; 3],
    pub background: u32,
    pub foreground: u32,
    pub active: u32,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Recipe {
    schema_version: u32,
    id: String,
    name: String,
    panel: Panel,
    colors: Colors,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Panel {
    position: String,
    height: u32,
    sections: Sections,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Sections {
    start: Vec<String>,
    center: Vec<String>,
    end: Vec<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Colors {
    background: String,
    foreground: String,
    active: String,
}

fn color(raw: &str) -> Result<u32, Box<dyn Error>> {
    if raw.len() != 7 || !raw.starts_with('#') || !raw[1..].bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("RicePlate color must be six hexadecimal RGB digits".into());
    }
    Ok(0xff00_0000 | u32::from_str_radix(&raw[1..], 16)?)
}

pub fn parse(raw: &str, expected_id: Option<&str>) -> Result<PanelStyle, Box<dyn Error>> {
    if raw.len() > MAX_RECIPE_BYTES {
        return Err("RicePlate recipe exceeds 64 KiB".into());
    }
    let recipe: Recipe = serde_json::from_str(raw)?;
    let id = recipe.id.as_bytes();
    if recipe.schema_version != 1 || id.len() < 2 || id.len() > 32
        || !id[0].is_ascii_lowercase()
        || !id.iter().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || *b == b'-')
        || expected_id.is_some_and(|expected| expected != recipe.id.as_str())
        || recipe.name.is_empty() || recipe.name.chars().count() > 60
        || recipe.name.chars().any(char::is_control)
        || !(28..=64).contains(&recipe.panel.height)
        || !["top", "bottom"].contains(&recipe.panel.position.as_str()) {
        return Err("RicePlate recipe metadata or dimensions are invalid".into());
    }
    let mut seen = HashSet::new();
    let mut sections: [Vec<Widget>; 3] = std::array::from_fn(|_| Vec::new());
    let source = [&recipe.panel.sections.start, &recipe.panel.sections.center,
                  &recipe.panel.sections.end];
    for (index, widgets) in source.iter().enumerate() {
        if widgets.len() > 7 { return Err("RicePlate section has more than seven widgets".into()); }
        for widget in widgets.iter() {
            if !seen.insert(widget.as_str()) {
                return Err("RicePlate recipe duplicates a widget".into());
            }
            match widget.as_str() {
                "launcher" => sections[index].push(Widget::Launcher),
                "tasks" => sections[index].push(Widget::Tasks),
                "clock" => sections[index].push(Widget::Clock),
                // Valid v1 widgets that still use the fully functional Waybar backend:
                "network" | "audio" | "battery" | "tray" => {}
                _ => return Err("Unsupported RicePlate widget or action".into()),
            }
        }
    }
    if !seen.contains("launcher") && !seen.contains("tasks") {
        return Err("RicePlate requires a launcher or task widget".into());
    }
    Ok(PanelStyle {
        height: recipe.panel.height,
        top: recipe.panel.position == "top",
        sections,
        background: color(&recipe.colors.background)?,
        foreground: color(&recipe.colors.foreground)?,
        active: color(&recipe.colors.active)?,
    })
}

pub fn load(name_or_path: &str) -> Result<PanelStyle, Box<dyn Error>> {
    let (raw, expected): (String, Option<&str>) = match name_or_path {
        "classic" => (include_str!("../../../macrice/de/resources/recipes/classic.json").into(),
                      Some("classic")),
        "chrome" => (include_str!("../../../macrice/de/resources/recipes/chrome.json").into(),
                     Some("chrome")),
        path => {
            let path = Path::new(path);
            if !path.is_absolute() {
                return Err("Choose classic, chrome or an absolute private JSON path".into());
            }
            let file = OpenOptions::new().read(true)
                .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC).open(path)?;
            let metadata = file.metadata()?;
            // Verify the opened inode, never just path metadata; no symlinks,
            // world/group-readable recipes, foreign owners, devices or pipes.
            if !metadata.is_file() || metadata.uid() != unsafe { libc::geteuid() }
                || metadata.mode() & 0o077 != 0 || metadata.len() > MAX_RECIPE_BYTES as u64 {
                return Err("Custom RicePlate recipe must be an owner-private regular file".into());
            }
            let mut data = Vec::new();
            file.take(MAX_RECIPE_BYTES as u64 + 1).read_to_end(&mut data)?;
            if data.len() > MAX_RECIPE_BYTES { return Err("Recipe exceeds 64 KiB".into()); }
            (String::from_utf8(data)?, None)
        }
    };
    parse(&raw, expected)
}

fn width_for(widget: Widget, tasks: usize) -> u32 {
    match widget {
        Widget::Launcher => LAUNCHER_WIDTH,
        Widget::Clock => CLOCK_WIDTH,
        Widget::Tasks => tasks as u32 * TASK_WIDTH,
    }
}

pub fn layout(style: &PanelStyle, screen_width: u32, tasks: usize) -> Vec<PlacedWidget> {
    let fixed_width: u32 = style.sections.iter().flatten().filter(|&&w| w != Widget::Tasks)
        .map(|&w| width_for(w, 0)).sum();
    let show_clock = screen_width >= fixed_width;
    let effective_fixed = if show_clock { fixed_width }
        else { fixed_width.saturating_sub(CLOCK_WIDTH) };
    let visible = tasks.min(MAX_TRACKED_TASKS)
        .min((screen_width.saturating_sub(effective_fixed + 8) / TASK_WIDTH) as usize);
    let section_width = |widgets: &[Widget]| -> u32 {
        widgets.iter().filter(|&&w| w != Widget::Clock || show_clock)
            .map(|&w| width_for(w, visible)).sum()
    };
    let widths: [u32; 3] = std::array::from_fn(|i| section_width(&style.sections[i]));
    let end_x = screen_width.saturating_sub(widths[2]);
    let middle_x = (screen_width.saturating_sub(widths[1]) / 2)
        .max(widths[0]).min(end_x.saturating_sub(widths[1]));
    let mut result = Vec::new();
    for (index, begin) in [0, middle_x, end_x].into_iter().enumerate() {
        let mut x = begin;
        for &widget in &style.sections[index] {
            if widget == Widget::Clock && !show_clock { continue; }
            let width = width_for(widget, visible);
            if width > 0 {
                result.push(PlacedWidget { widget, x, width });
                x = x.saturating_add(width);
            }
        }
    }
    result
}

pub fn hit(x: f64, screen_width: u32, tasks: usize, style: &PanelStyle) -> Option<Hit> {
    if !x.is_finite() || x < 0.0 || x >= f64::from(screen_width) { return None; }
    for item in layout(style, screen_width, tasks) {
        if x < f64::from(item.x) || x >= f64::from(item.x + item.width) { continue; }
        return match item.widget {
            Widget::Launcher => Some(Hit::Launcher),
            Widget::Tasks => Some(Hit::Task(
                ((x - f64::from(item.x)) / f64::from(TASK_WIDTH)) as usize)),
            Widget::Clock => None,
        };
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundled_recipes_are_distinct_and_validated() {
        let a = load("classic").unwrap();
        let b = load("chrome").unwrap();
        assert_eq!((a.height, b.height), (36, 44));
        assert_ne!(a.background, b.background);
        assert_eq!(hit(110.0, 800, 2, &a), Some(Hit::Task(0)));
        assert_eq!(hit(110.0, 800, 2, &b), None);
        assert_eq!(hit(250.0, 800, 2, &b), Some(Hit::Task(0)));
        assert_eq!(hit(760.0, 800, 2, &b), None);
        assert_eq!(hit(150.0, 180, 20, &b), None);
        assert!(layout(&b, 180, 20).iter().all(|item| item.widget != Widget::Clock));
    }

    #[test]
    fn custom_composition_repositions_all_supported_widgets() {
        let sample = include_str!("../../../macrice/de/resources/recipes/classic.json");
        let reordered = sample.replace(
            "\"start\": [\"launcher\", \"tasks\"],",
            "\"start\": [\"clock\"],"
        ).replace(
            "\"end\": [\"network\", \"audio\", \"battery\", \"clock\", \"tray\"]",
            "\"end\": [\"network\", \"audio\", \"battery\", \"launcher\", \"tasks\", \"tray\"]"
        );
        let style = parse(&reordered, Some("classic")).unwrap();
        assert_eq!(hit(40.0, 800, 2, &style), None);
        assert_eq!(hit(390.0, 800, 2, &style), Some(Hit::Launcher));
        assert_eq!(hit(490.0, 800, 2, &style), Some(Hit::Task(0)));
    }

    #[test]
    fn denies_unknown_actions_and_oversized_recipes() {
        let sample = include_str!("../../../macrice/de/resources/recipes/classic.json");
        assert!(parse(&sample.replace("\"launcher\"", "\"exec-shell\""), None).is_err());
        assert!(parse(&sample.replace("\"schema_version\": 1",
               "\"schema_version\": 1, \"exec\": \"payload\""), None).is_err());
        assert!(parse(&"x".repeat(65_537), None).is_err());
        assert!(load("relative.json").is_err());
    }
}
