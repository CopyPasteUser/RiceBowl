//! Bounded, non-executable RicePlate recipes and shared widget geometry.
//! The Waybar adapter and native renderer consume the same bounded panel JSON.

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
const PAGE_BUTTON_WIDTH: u32 = 24;
const MAX_RECIPE_BYTES: usize = 64 * 1024;
pub const MAX_TRACKED_TASKS: usize = 128;
const MAX_LAYOUT_NODES: usize = 24;
const MAX_LAYOUT_LABELS: usize = 8;
const MAX_LAYOUT_DEPTH: usize = 3;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Widget {
    Launcher,
    Tasks,
    Clock,
    Gap(u32),
    Label(u8),
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
    PreviousTasks,
    NextTasks,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TaskViewport {
    pub start: usize,
    pub slots: usize,
    pub cell_width: u32,
    pub content_width: u32,
    pub prev: bool,
    pub next: bool,
}

pub struct PanelStyle {
    pub height: u32,
    pub top: bool,
    /// Launcher, per-task and clock logical widths (schema v1 uses defaults).
    pub widths: [u32; 3],
    pub sections: [Vec<Widget>; 3],
    pub labels: Vec<String>,
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
    #[serde(default, deserialize_with = "deserialize_present")]
    sections: Option<Sections>,
    #[serde(default, deserialize_with = "deserialize_present")]
    layout: Option<LayoutSections>,
    // Distinguish an absent field from an explicitly supplied JSON null.
    #[serde(default, deserialize_with = "deserialize_present")]
    metrics: Option<PanelMetrics>,
}

fn deserialize_present<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where
    D: serde::Deserializer<'de>,
    T: Deserialize<'de>,
{
    T::deserialize(deserializer).map(Some)
}

#[derive(Deserialize, Clone, Copy)]
#[serde(deny_unknown_fields)]
struct PanelMetrics {
    launcher_width: u32,
    task_width: u32,
    clock_width: u32,
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
struct LayoutSections {
    start: Vec<LayoutNode>,
    center: Vec<LayoutNode>,
    end: Vec<LayoutNode>,
}

#[derive(Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
enum LayoutNode {
    Widget { id: String },
    Gap { width: u32 },
    Label { text: String },
    Group { gap: u32, children: Vec<LayoutNode> },
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

fn expand_layout(
    node: &LayoutNode, depth: usize, counts: &mut [usize; 2],
    seen: &mut HashSet<String>, rendered: &mut Vec<Widget>, labels: &mut Vec<String>,
) -> Result<(), Box<dyn Error>> {
    counts[0] += 1;
    if depth > MAX_LAYOUT_DEPTH || counts[0] > MAX_LAYOUT_NODES {
        return Err("Panel layout exceeds bounded depth or node count".into());
    }
    match node {
        LayoutNode::Widget { id } => {
            if !seen.insert(id.clone()) { return Err("Duplicate panel widget".into()); }
            match id.as_str() {
                "launcher" => rendered.push(Widget::Launcher),
                "tasks" => rendered.push(Widget::Tasks),
                "clock" => rendered.push(Widget::Clock),
                // Known but unsupported native controls remain Waybar-only.
                "network" | "audio" | "battery" | "tray" => {},
                _ => return Err("Unsupported panel widget or action".into()),
            }
        }
        LayoutNode::Gap { width } => {
            if !(4..=64).contains(width) { return Err("Panel gap width invalid".into()); }
            rendered.push(Widget::Gap(*width));
        }
        LayoutNode::Label { text } => {
            if text.is_empty() || text.len() > 24 || !text.bytes().all(|b|
                b.is_ascii_alphanumeric() || b" ._:+-".contains(&b)) {
                return Err("Panel label is not bounded safe ASCII".into());
            }
            counts[1] += 1;
            if counts[1] > MAX_LAYOUT_LABELS { return Err("Too many labels".into()); }
            let index = labels.len() as u8;
            labels.push(text.clone());
            rendered.push(Widget::Label(index));
        }
        LayoutNode::Group { gap, children } => {
            if depth >= MAX_LAYOUT_DEPTH || *gap > 32 || !(1..=6).contains(&children.len()) {
                return Err("Invalid panel group".into());
            }
            for (index, child) in children.iter().enumerate() {
                if index > 0 && *gap > 0 { rendered.push(Widget::Gap(*gap)); }
                expand_layout(child, depth + 1, counts, seen, rendered, labels)?;
            }
        }
    }
    Ok(())
}

pub fn parse(raw: &str, expected_id: Option<&str>) -> Result<PanelStyle, Box<dyn Error>> {
    if raw.len() > MAX_RECIPE_BYTES {
        return Err("RicePlate recipe exceeds 64 KiB".into());
    }
    let recipe: Recipe = serde_json::from_str(raw)?;
    let id = recipe.id.as_bytes();
    if ![1, 2, 3].contains(&recipe.schema_version) || id.len() < 2 || id.len() > 32
        || !id[0].is_ascii_lowercase()
        || !id.iter().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || *b == b'-')
        || expected_id.is_some_and(|expected| expected != recipe.id.as_str())
        || recipe.name.is_empty() || recipe.name.chars().count() > 60
        || recipe.name.chars().any(char::is_control)
        || !(28..=64).contains(&recipe.panel.height)
        || !["top", "bottom"].contains(&recipe.panel.position.as_str()) {
        return Err("RicePlate recipe metadata or dimensions are invalid".into());
    }
    let widths = match (recipe.schema_version, recipe.panel.metrics) {
        (1, None) => [LAUNCHER_WIDTH, TASK_WIDTH, CLOCK_WIDTH],
        (2 | 3, Some(metrics))
            if (64..=256).contains(&metrics.launcher_width)
                && (96..=256).contains(&metrics.task_width)
                && (64..=256).contains(&metrics.clock_width) =>
            [metrics.launcher_width, metrics.task_width, metrics.clock_width],
        _ => return Err("RicePlate v2/v3 requires bounded metrics; v1 forbids them".into()),
    };
    let mut seen: HashSet<String> = HashSet::new();
    let mut sections: [Vec<Widget>; 3] = std::array::from_fn(|_| Vec::new());
    let mut labels = Vec::new();
    match (recipe.schema_version, recipe.panel.sections, recipe.panel.layout) {
        (1 | 2, Some(source), None) => {
            let selected = [source.start, source.center, source.end];
            for (index, widgets) in selected.into_iter().enumerate() {
                if widgets.len() > 7 { return Err("RicePlate section has more than seven widgets".into()); }
                for widget in widgets {
                    if !seen.insert(widget.clone()) {
                        return Err("RicePlate recipe duplicates a widget".into());
                    }
                    match widget.as_str() {
                        "launcher" => sections[index].push(Widget::Launcher),
                        "tasks" => sections[index].push(Widget::Tasks),
                        "clock" => sections[index].push(Widget::Clock),
                        "network" | "audio" | "battery" | "tray" => {},
                        _ => return Err("Unsupported RicePlate widget or action".into()),
                    }
                }
            }
        }
        (3, None, Some(layout)) => {
            let source = [layout.start, layout.center, layout.end];
            let mut counts = [0_usize, 0_usize];
            for (index, nodes) in source.iter().enumerate() {
                if nodes.len() > 8 { return Err("Too many layout roots".into()); }
                for node in nodes {
                    expand_layout(node, 1, &mut counts, &mut seen,
                                  &mut sections[index], &mut labels)?;
                }
            }
        }
        _ => return Err("Legacy sections and v3 layouts are mutually exclusive".into()),
    }
    if !seen.contains("launcher") && !seen.contains("tasks") {
        return Err("RicePlate requires a launcher or task widget".into());
    }
    Ok(PanelStyle {
        height: recipe.panel.height,
        top: recipe.panel.position == "top",
        widths,
        sections,
        labels,
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

fn width_for(style: &PanelStyle, widget: Widget, tasks: usize) -> u32 {
    match widget {
        Widget::Launcher => style.widths[0],
        Widget::Clock => style.widths[2],
        Widget::Tasks => tasks as u32 * style.widths[1],
        Widget::Gap(width) => width,
        Widget::Label(index) => style.labels[index as usize].len() as u32 * 8 + 16,
    }
}

pub fn layout(style: &PanelStyle, screen_width: u32, tasks: usize) -> Vec<PlacedWidget> {
    let fixed_width: u32 = style.sections.iter().flatten().filter(|&&w| w != Widget::Tasks)
        .map(|&w| width_for(style, w, 0)).sum();
    let has_clock = style.sections.iter().flatten().any(|&w| w == Widget::Clock);
    let show_clock = !has_clock || screen_width >= fixed_width;
    let effective_fixed = if show_clock { fixed_width }
        else { fixed_width.saturating_sub(style.widths[2]) };
    let visible = tasks.min(MAX_TRACKED_TASKS)
        .min((screen_width.saturating_sub(effective_fixed + 8) / style.widths[1]) as usize);
    let section_width = |widgets: &[Widget]| -> u32 {
        widgets.iter().filter(|&&w| w != Widget::Clock || show_clock)
            .map(|&w| width_for(style, w, visible)).sum()
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
            let width = width_for(style, widget, visible);
            if width > 0 {
                result.push(PlacedWidget { widget, x, width });
                x = x.saturating_add(width);
            }
        }
    }
    result
}

pub fn task_view(style: &PanelStyle, screen_width: u32,
                 tasks: usize, offset: usize) -> Option<TaskViewport> {
    let item = layout(style, screen_width, tasks).into_iter()
        .find(|placed| placed.widget == Widget::Tasks)?;
    let slots = (item.width / style.widths[1]) as usize;
    if slots == 0 { return None; }
    let overflowing = tasks > slots;
    let start = if overflowing { offset.min(tasks - slots) } else { 0 };
    let controls = if overflowing { PAGE_BUTTON_WIDTH * 2 } else { 0 };
    let content_width = item.width.saturating_sub(controls);
    Some(TaskViewport {
        start, slots, cell_width: content_width / slots as u32,
        content_width, prev: overflowing && start > 0,
        next: overflowing && start + slots < tasks,
    })
}

pub fn hit(x: f64, screen_width: u32, tasks: usize,
           offset: usize, style: &PanelStyle) -> Option<Hit> {
    if !x.is_finite() || x < 0.0 || x >= f64::from(screen_width) { return None; }
    for item in layout(style, screen_width, tasks) {
        if x < f64::from(item.x) || x >= f64::from(item.x + item.width) { continue; }
        return match item.widget {
            Widget::Launcher => Some(Hit::Launcher),
            Widget::Tasks => {
                let view = task_view(style, screen_width, tasks, offset)?;
                let local = x - f64::from(item.x);
                if local >= f64::from(view.content_width) {
                    if local < f64::from(view.content_width + PAGE_BUTTON_WIDTH) && view.prev {
                        Some(Hit::PreviousTasks)
                    } else if local >= f64::from(view.content_width + PAGE_BUTTON_WIDTH)
                        && view.next {
                        Some(Hit::NextTasks)
                    } else { None }
                } else {
                    let index = ((local / f64::from(view.cell_width)) as usize)
                        .min(view.slots - 1);
                    Some(Hit::Task(view.start + index))
                }
            }
            Widget::Clock => None,
            Widget::Gap(_) | Widget::Label(_) => None,
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
        assert_eq!(hit(110.0, 800, 2, 0, &a), Some(Hit::Task(0)));
        assert_eq!(hit(110.0, 800, 2, 0, &b), None);
        assert_eq!(hit(250.0, 800, 2, 0, &b), Some(Hit::Task(0)));
        assert_eq!(hit(760.0, 800, 2, 0, &b), None);
        assert_eq!(hit(150.0, 180, 20, 0, &b), None);
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
        assert_eq!(hit(40.0, 800, 2, 0, &style), None);
        assert_eq!(hit(390.0, 800, 2, 0, &style), Some(Hit::Launcher));
        assert_eq!(hit(490.0, 800, 2, 0, &style), Some(Hit::Task(0)));
    }

    #[test]
    fn overflow_pages_reach_all_windows_without_overlapping_hit_areas() {
        let style = load("classic").unwrap();
        let view = task_view(&style, 800, 10, 0).unwrap();
        assert_eq!((view.slots, view.start), (3, 0));
        assert!(!view.prev && view.next);
        let start = LAUNCHER_WIDTH as f64;
        let nav = start + f64::from(view.content_width);
        assert_eq!(hit(start + 10.0, 800, 10, 0, &style), Some(Hit::Task(0)));
        assert_eq!(hit(nav + 5.0, 800, 10, 0, &style), None);
        assert_eq!(hit(nav + 30.0, 800, 10, 0, &style), Some(Hit::NextTasks));
        assert_eq!(hit(start + 10.0, 800, 10, 3, &style), Some(Hit::Task(3)));
        assert_eq!(hit(nav + 5.0, 800, 10, 3, &style), Some(Hit::PreviousTasks));
        let last = task_view(&style, 800, 10, usize::MAX).unwrap();
        assert_eq!(last.start, 7);
        assert!(last.prev && !last.next);
        assert_eq!(hit(start + 10.0, 800, 10, usize::MAX, &style), Some(Hit::Task(7)));
        assert_eq!(hit(nav + 30.0, 800, 10, usize::MAX, &style), None);
    }

    #[test]
    fn small_panels_and_unneeded_paging_do_not_expose_fake_controls() {
        let style = load("chrome").unwrap();
        assert!(task_view(&style, 180, 20, 0).is_none());
        let view = task_view(&style, 800, 2, 99).unwrap();
        assert_eq!((view.start, view.slots), (0, 2));
        assert!(!view.prev && !view.next);
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

    #[test]
    fn v2_metrics_resize_real_widget_geometry_and_hit_testing() {
        let original = include_str!("../../../macrice/de/resources/recipes/classic.json");
        let v2 = original.replace("\"schema_version\": 1", "\"schema_version\": 2")
            .replace("\"height\": 36,",
                     "\"height\": 36, \"metrics\": {\"launcher_width\": 120, \"task_width\": 196, \"clock_width\": 80},");
        let style = parse(&v2, Some("classic")).unwrap();
        assert_eq!(style.widths, [120, 196, 80]);
        let placed = layout(&style, 800, 2);
        assert_eq!(placed.iter().find(|item| item.widget == Widget::Launcher).unwrap().width, 120);
        assert_eq!(placed.iter().find(|item| item.widget == Widget::Tasks).unwrap().width, 392);
        assert_eq!(hit(119.0, 800, 2, 0, &style), Some(Hit::Launcher));
        assert_eq!(hit(121.0, 800, 2, 0, &style), Some(Hit::Task(0)));
        assert_eq!(hit(320.0, 800, 2, 0, &style), Some(Hit::Task(1)));
        assert_eq!(task_view(&style, 800, 10, 0).unwrap().slots, 3);
    }

    #[test]
    fn v2_requires_exact_bounded_metrics_and_v1_stays_strict() {
        let original = include_str!("../../../macrice/de/resources/recipes/classic.json");
        let v2_without_metrics = original.replace("\"schema_version\": 1", "\"schema_version\": 2");
        assert!(parse(&v2_without_metrics, None).is_err());
        let with_metrics = original.replace("\"height\": 36,",
            "\"height\": 36, \"metrics\": {\"launcher_width\": 120, \"task_width\": 196, \"clock_width\": 80},");
        assert!(parse(&with_metrics, None).is_err());
        let with_null = original.replace("\"height\": 36,", "\"height\": 36, \"metrics\": null,");
        assert!(parse(&with_null, None).is_err());
        let invalid = with_metrics.replace("\"schema_version\": 1", "\"schema_version\": 2")
            .replace("\"task_width\": 196", "\"task_width\": 1");
        assert!(parse(&invalid, None).is_err());
    }

    const NESTED: &str = include_str!("../../../tests/fixtures/riceplate-nested-v3.json");

    #[test]
    fn v3_nested_layout_changes_actual_native_geometry_and_hit_areas() {
        let style = parse(NESTED, Some("my-layout")).unwrap();
        assert!(style.top);
        assert_eq!(style.labels, vec!["Y2K"]);
        let placed = layout(&style, 800, 2);
        assert!(placed.iter().any(|node| node.widget == Widget::Label(0) && node.x == 112));
        assert!(placed.iter().any(|node| node.widget == Widget::Gap(20) && node.x == 160));
        let task = placed.iter().find(|node| node.widget == Widget::Tasks).unwrap();
        assert_eq!(task.x, 188);
        assert_eq!(hit(120.0, 800, 2, 0, &style), None);
        assert_eq!(hit(189.0, 800, 2, 0, &style), Some(Hit::Task(0)));
        assert_eq!(hit(705.0, 800, 2, 0, &style), None);
    }

    #[test]
    fn v3_rejects_unknown_properties_executable_nodes_and_deep_groups() {
        let original: serde_json::Value = serde_json::from_str(NESTED).unwrap();
        let mut unsafe_label = original.clone();
        unsafe_label["panel"]["layout"]["start"][0]["children"][1]["text"] =
            serde_json::json!("<script>");
        assert!(parse(&unsafe_label.to_string(), None).is_err());
        let mut executable_gap = original.clone();
        executable_gap["panel"]["layout"]["start"][0]["children"][2]["exec"] =
            serde_json::json!("shell");
        assert!(parse(&executable_gap.to_string(), None).is_err());
        let mut unknown = original.clone();
        unknown["panel"]["layout"]["start"][0]["children"][2]["type"] =
            serde_json::json!("run");
        assert!(parse(&unknown.to_string(), None).is_err());
        let mut both = original.clone();
        both["panel"]["sections"] = serde_json::json!({"start":[],"center":[],"end":[]});
        assert!(parse(&both.to_string(), None).is_err());
        let child = r#"{"type":"widget","id":"launcher"}"#;
        let group = |inside: String| format!(r#"{{"type":"group","gap":0,"children":[{inside}]}}"#);
        let too_deep = group(group(group(child.to_string())));
        let mut deep = original;
        deep["panel"]["layout"]["start"] = serde_json::json!([
            serde_json::from_str::<serde_json::Value>(&too_deep).unwrap()
        ]);
        assert!(parse(&deep.to_string(), None).is_err());
    }
}
