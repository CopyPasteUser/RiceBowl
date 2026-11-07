//! On-demand native notification view, backed by RiceBowl's existing Mako bridge.
//! The bridge remains the sole authority for validating active IDs and dismissals.

use std::{io::Read, process::{Command, Stdio}, thread, time::{Duration, Instant}};

use serde::Deserialize;

const MAX_RESPONSE: u64 = 512 * 1024;
pub const VISIBLE_ROWS: usize = 3;
pub const ROW_TOP: u32 = 90;
pub const ROW_HEIGHT: u32 = 54;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hit { Row(usize), Tab(bool), Back, Refresh, Dismiss }

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Notice {
    pub id: u32,
    pub summary: String,
    pub body: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Snapshot {
    pub active: Vec<Notice>,
    pub history: Vec<Notice>,
}

#[derive(Debug, Default)]
pub struct State {
    pub open: bool,
    pub loading: bool,
    pub error: Option<&'static str>,
    pub notices: Vec<Notice>,
    pub history: Vec<Notice>,
    pub show_history: bool,
    pub selected: usize,
    pub revision: u64,
}

impl State {
    pub fn close(&mut self) {
        self.open = false;
        self.loading = false;
        self.notices.clear(); // Private notification text must not be retained.
        self.history.clear();
        self.show_history = false;
        self.error = None;
        self.selected = 0;
    }

    pub fn begin(&mut self) -> u64 {
        self.open = true;
        self.loading = true;
        self.error = None;
        self.revision = self.revision.wrapping_add(1);
        self.revision
    }

    pub fn update(&mut self, revision: u64, result: Result<Snapshot, &'static str>) -> bool {
        if !self.open || revision != self.revision { return false; }
        self.loading = false;
        match result {
            Ok(snapshot) => {
                self.notices = snapshot.active;
                self.history = snapshot.history;
                self.selected = self.selected.min(self.visible_notices().len().saturating_sub(1));
                self.error = None;
            }
            Err(message) => self.error = Some(message),
        }
        true
    }

    pub fn select(&mut self, delta: isize) {
        if self.visible_notices().is_empty() { return; }
        self.selected = (self.selected as isize + delta)
            .clamp(0, self.visible_notices().len() as isize - 1) as usize;
    }

    pub fn select_tab(&mut self, history: bool) {
        self.show_history = history;
        self.selected = 0;
    }

    pub fn visible_notices(&self) -> &[Notice] {
        if self.show_history { &self.history } else { &self.notices }
    }

    pub fn first_row(&self) -> usize {
        (self.selected / VISIBLE_ROWS) * VISIBLE_ROWS
    }

    pub fn selected_id(&self) -> Option<u32> {
        (!self.show_history && !self.loading && self.error.is_none())
            .then(|| self.notices.get(self.selected))
            .flatten().map(|n| n.id)
    }

    pub fn hit(&self, x: f64, y: f64) -> Option<Hit> {
        if !self.open || !x.is_finite() || !y.is_finite()
            || !(0.0..320.0).contains(&x) || !(0.0..304.0).contains(&y) {
            return None;
        }
        if (40.0..86.0).contains(&y) {
            return Some(Hit::Tab(x >= 160.0));
        }
        if (260.0..304.0).contains(&y) {
            return Some(if x < 90.0 { Hit::Back }
                         else if x < 177.0 { Hit::Refresh }
                         else { Hit::Dismiss });
        }
        if (f64::from(ROW_TOP)..f64::from(ROW_TOP + VISIBLE_ROWS as u32 * ROW_HEIGHT))
            .contains(&y) && !self.loading && self.error.is_none() {
            let index = self.first_row() + ((y as u32 - ROW_TOP) / ROW_HEIGHT) as usize;
            return (index < self.visible_notices().len()).then_some(Hit::Row(index));
        }
        None
    }
}

#[derive(Debug)]
pub enum Request {
    Refresh(u64),
    Dismiss(u64, u32),
}

impl Request {
    pub fn revision(&self) -> u64 {
        match self { Self::Refresh(revision) | Self::Dismiss(revision, _) => *revision }
    }
}

#[derive(Deserialize)]
struct Record {
    id: u32,
    summary: String,
    body: String,
}

pub fn parse(raw: &[u8]) -> Result<Snapshot, &'static str> {
    if raw.len() > MAX_RESPONSE as usize { return Err("Notification data too large"); }
    // The existing bridge may return extra metadata/history; consume only
    // active, sanitized records and never persist or replay notification actions.
    let value: serde_json::Value = serde_json::from_slice(raw)
        .map_err(|_| "Invalid notification data")?;
    if value.get("ok") != Some(&serde_json::Value::Bool(true))
        || value.get("truncated") == Some(&serde_json::Value::Bool(true)) {
        return Err("Notification list unavailable");
    }
    Ok(Snapshot {
        active: parse_records(&value, "active")?,
        history: parse_records(&value, "history")?,
    })
}

fn parse_records(value: &serde_json::Value, field: &str) -> Result<Vec<Notice>, &'static str> {
    let array = value.get(field).and_then(|v| v.as_array())
        .ok_or("Invalid notification data")?;
    if array.len() > 64 { return Err("Notification list too long"); }
    let mut notices = Vec::new();
    for entry in array {
        let record: Record = serde_json::from_value(entry.clone())
            .map_err(|_| "Invalid notification data")?;
        if record.id == 0 || record.summary.chars().count() > 160
            || record.body.chars().count() > 2048
            || notices.iter().any(|item: &Notice| item.id == record.id) {
            return Err("Invalid notification data");
        }
        notices.push(Notice { id: record.id, summary: record.summary, body: record.body });
    }
    Ok(notices)
}

fn call_cli(arguments: &[&str]) -> Result<Vec<u8>, &'static str> {
    let mut child = Command::new("ricebowl").args(arguments)
        .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null())
        .spawn().map_err(|_| "RicePop CLI unavailable")?;
    let stdout = child.stdout.take().ok_or("RicePop CLI unavailable")?;
    // Drain concurrently: waiting before reading can deadlock on a large pipe.
    let reader = thread::spawn(move || {
        let mut data = Vec::new();
        stdout.take(MAX_RESPONSE + 1).read_to_end(&mut data).map(|_| data)
    });
    let started = Instant::now();
    let success = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status.success(),
            Ok(None) if started.elapsed() < Duration::from_secs(9) => {
                thread::sleep(Duration::from_millis(20));
            }
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                break false;
            }
        }
    };
    let output = reader.join().map_err(|_| "RicePop CLI failed")?
        .map_err(|_| "RicePop CLI failed")?;
    if !success || output.len() > MAX_RESPONSE as usize {
        return Err("Notification host unavailable");
    }
    Ok(output)
}

pub fn run(request: &Request) -> Result<Snapshot, &'static str> {
    if let Request::Dismiss(_, notification_id) = request {
        let id = notification_id.to_string();
        let output = call_cli(&["de", "notification-dismiss", "--notification-id", &id, "--json"])?;
        let reply: serde_json::Value = serde_json::from_slice(&output)
            .map_err(|_| "Dismissal response invalid")?;
        if reply.get("ok") != Some(&serde_json::Value::Bool(true))
            || reply.get("notification_id").and_then(|value| value.as_u64()) != Some(u64::from(*notification_id)) {
            return Err("Notification could not be dismissed");
        }
    }
    parse(&call_cli(&["de", "notifications", "--json"])?)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn active_only_malformed_or_ambiguous_data_fails_closed() {
        let fixture = br#"{"ok":true,"active":[{"id":42,"summary":"Hello","body":"News","app_name":"App"}],"history":[{"id":99,"summary":"","body":""}]}"#;
        assert_eq!(parse(fixture).unwrap(), Snapshot {
            active: vec![Notice { id: 42, summary: "Hello".into(), body: "News".into() }],
            history: vec![Notice { id: 99, summary: "".into(), body: "".into() }],
        });
        for bad in [br#"{"ok":false,"active":[],"history":[]}"#.as_slice(),
                    br#"{"ok":true,"truncated":true,"active":[],"history":[]}"#,
                    br#"{"ok":true,"active":[{"id":0,"summary":"x","body":""}],"history":[]}"#,
                    br#"{"ok":true,"active":[{"id":1,"summary":"x","body":""},{"id":1,"summary":"y","body":""}],"history":[]}"#,
                    br#"{"ok":true,"active":[{"id":1,"summary":2,"body":""}],"history":[]}"#,
                    br#"{"ok":true,"active":[]}"#] {
            assert!(parse(bad).is_err());
        }
    }

    #[test]
    fn selection_and_stale_response_are_bounded() {
        let mut state = State::default();
        let old = state.begin();
        let current = state.begin();
        assert!(!state.update(old, Ok(Snapshot { active: vec![], history: vec![] })));
        let items = (1..=8).map(|id| Notice { id, summary: "x".into(), body: "".into() }).collect();
        assert!(state.update(current, Ok(Snapshot { active: items, history: vec![Notice {
            id: 77, summary: "Old".into(), body: "Past".into(),
        }] })));
        state.select(7);
        assert_eq!(state.first_row(), 6);
        assert_eq!(state.selected_id(), Some(8));
        state.select(1);
        assert_eq!(state.selected_id(), Some(8));
        state.select_tab(true);
        assert_eq!(state.visible_notices().len(), 1);
        assert_eq!(state.selected_id(), None);
        assert_eq!(state.hit(250.0, 55.0), Some(Hit::Tab(true)));
        state.open = false;
        assert!(!state.update(current, Ok(Snapshot { active: vec![], history: vec![] })));
        state.close();
        assert!(state.notices.is_empty());
        assert!(state.history.is_empty());
    }

    #[test]
    fn notification_buttons_are_explicit_and_hit_regions_bounded() {
        let mut state = State::default();
        let revision = state.begin();
        state.update(revision, Ok(Snapshot { active: vec![Notice {
            id: 4, summary: "x".into(), body: "".into(),
        }], history: vec![] }));
        assert_eq!(state.hit(10.0, 91.0), Some(Hit::Row(0)));
        assert_eq!(state.hit(10.0, 145.0), None);
        assert_eq!(state.hit(10.0, 275.0), Some(Hit::Back));
        assert_eq!(state.hit(115.0, 275.0), Some(Hit::Refresh));
        assert_eq!(state.hit(280.0, 275.0), Some(Hit::Dismiss));
        assert_eq!(state.hit(-2.0, 275.0), None);
        assert_eq!(state.hit(f64::NAN, 275.0), None);
    }
}
