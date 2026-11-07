//! Bounded, input-independent navigation for a real native RicePlate menu.
//! Every row maps to a validated recipe action; labels never become commands.

use crate::recipe::NativeMenu;

pub const WIDTH: u32 = 320;
pub const HEIGHT: u32 = 304;
pub const TAB_TOP: u32 = 46;
pub const TAB_HEIGHT: u32 = 40;
pub const ACTION_TOP: u32 = 108;
pub const ACTION_HEIGHT: u32 = 42;
pub const VISIBLE_ACTIONS: usize = 4;
pub const MAX_PINS: usize = 8;

pub fn action_label(action: &str) -> &'static str {
    match action {
        "applications" => "Applications",
        "terminal" => "Terminal",
        "settings" => "RiceSpice settings",
        "lock" => "Lock screen",
        "logout" => "Log out of RiceBowl",
        "wifi-toggle" => "Toggle Wi-Fi radio",
        "audio-mute" => "Toggle speaker mute",
        "audio-up" => "Volume +5%",
        "audio-down" => "Volume -5%",
        "notifications" => "Notifications",
        _ => "Unsupported",
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum View {
    #[default]
    Groups,
    Search,
    Saved,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hit {
    Group(usize),
    Action(usize),
    Close,
}

#[derive(Debug, Default)]
pub struct MenuState {
    pub visible: bool,
    pub group: usize,
    pub selected: usize,
    pub notice: Option<&'static str>,
    pub view: View,
    pub search: String,
    pub pins: Vec<String>,
}

impl MenuState {
    pub fn open(&mut self) {
        self.visible = true;
        self.group = 0;
        self.selected = 0;
        self.notice = None;
        self.view = View::Groups;
        self.search.clear();
    }

    pub fn close(&mut self) {
        self.visible = false;
    }

    pub fn group_by(&mut self, menu: &NativeMenu, delta: isize) {
        let count = menu.groups.len();
        if count == 0 {
            return;
        }
        self.group = (self.group as isize + delta).rem_euclid(count as isize) as usize;
        self.selected = 0;
        self.view = View::Groups;
        self.search.clear();
    }

    pub fn open_group(&mut self, index: usize) {
        self.group = index;
        self.selected = 0;
        self.view = View::Groups;
        self.search.clear();
    }

    pub fn actions<'a>(&self, menu: &'a NativeMenu) -> Vec<&'a str> {
        let all = || menu.groups.iter().flat_map(|group|
            group.actions.iter().map(String::as_str));
        match self.view {
            View::Groups => menu.groups.get(self.group).into_iter()
                .flat_map(|group| group.actions.iter().map(String::as_str)).collect(),
            View::Search => {
                let query = self.search.to_ascii_lowercase();
                all().filter(|action| action_label(action)
                    .to_ascii_lowercase().contains(&query)).collect()
            }
            View::Saved => all().filter(|action|
                self.pins.iter().any(|pin| pin.as_str() == *action)).collect(),
        }
    }

    pub fn first_action_row(&self) -> usize {
        (self.selected / VISIBLE_ACTIONS) * VISIBLE_ACTIONS
    }

    pub fn start_search(&mut self) {
        self.view = View::Search;
        self.search.clear();
        self.selected = 0;
    }

    pub fn search_input(&mut self, text: &str) -> bool {
        if text.chars().count() != 1 || self.search.len() >= 24
            || !text.chars().all(|c| c.is_ascii_alphanumeric() || c == ' ' || c == '-') {
            return false;
        }
        if self.view != View::Search { self.start_search(); }
        self.search.push_str(text);
        self.selected = 0;
        true
    }

    pub fn backspace(&mut self) -> bool {
        if self.view != View::Search { return false; }
        self.search.pop();
        self.selected = 0;
        true
    }

    pub fn show_saved(&mut self) {
        self.view = if self.view == View::Saved { View::Groups } else { View::Saved };
        self.search.clear();
        self.selected = 0;
    }

    pub fn back(&mut self) -> bool {
        if self.view == View::Groups { return false; }
        self.view = View::Groups;
        self.search.clear();
        self.selected = 0;
        true
    }

    pub fn toggle_pin(&mut self, menu: &NativeMenu) -> bool {
        let Some(action) = self.current_action(menu).map(str::to_owned) else { return false; };
        if let Some(index) = self.pins.iter().position(|item| *item == action) {
            self.pins.remove(index);
        } else if self.pins.len() < MAX_PINS {
            self.pins.push(action);
        } else {
            return false;
        }
        self.selected = self.selected.min(self.actions(menu).len().saturating_sub(1));
        true
    }

    pub fn select_by(&mut self, menu: &NativeMenu, delta: isize) {
        let count = self.actions(menu).len();
        if count == 0 {
            return;
        }
        self.selected = (self.selected as isize + delta).rem_euclid(count as isize) as usize;
    }

    pub fn current_action<'a>(&self, menu: &'a NativeMenu) -> Option<&'a str> {
        self.actions(menu).get(self.selected).copied()
    }

    pub fn hit(&self, menu: &NativeMenu, x: f64, y: f64) -> Option<Hit> {
        if !self.visible
            || !x.is_finite()
            || !y.is_finite()
            || x < 0.0
            || x >= f64::from(WIDTH)
            || y < 0.0
            || y >= f64::from(HEIGHT)
        {
            return None;
        }
        if (f64::from(TAB_TOP)..f64::from(TAB_TOP + TAB_HEIGHT)).contains(&y) {
            let index = (x as usize * menu.groups.len()) / WIDTH as usize;
            return (index < menu.groups.len()).then_some(Hit::Group(index));
        }
        if (f64::from(ACTION_TOP)..f64::from(ACTION_TOP + VISIBLE_ACTIONS as u32 * ACTION_HEIGHT)).contains(&y) {
            let index = self.first_action_row() +
                ((y as u32 - ACTION_TOP) / ACTION_HEIGHT) as usize;
            return self.actions(menu).get(index).map(|_| Hit::Action(index));
        }
        (y >= f64::from(HEIGHT - 28)).then_some(Hit::Close)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::recipe::NativeMenuGroup;

    fn menu() -> NativeMenu {
        NativeMenu {
            title: "Desktop".into(),
            groups: vec![
                NativeMenuGroup {
                    title: "Programs".into(),
                    actions: vec!["applications".into(), "terminal".into()],
                },
                NativeMenuGroup {
                    title: "Session".into(),
                    actions: vec!["lock".into(), "logout".into()],
                },
            ],
        }
    }

    #[test]
    fn keyboard_cycles_real_actions_and_groups() {
        let data = menu();
        let mut state = MenuState::default();
        state.open();
        assert_eq!(state.current_action(&data), Some("applications"));
        state.select_by(&data, -1);
        assert_eq!(state.current_action(&data), Some("terminal"));
        state.group_by(&data, 1);
        assert_eq!(state.current_action(&data), Some("lock"));
        state.group_by(&data, 1);
        assert_eq!(state.current_action(&data), Some("applications"));
        state.close();
        assert_eq!(state.hit(&data, 15.0, 120.0), None);
    }

    #[test]
    fn pointer_hit_testing_never_invents_actions() {
        let data = menu();
        let mut state = MenuState::default();
        state.open();
        assert_eq!(state.hit(&data, 300.0, 50.0), Some(Hit::Group(1)));
        assert_eq!(state.hit(&data, 20.0, 108.0), Some(Hit::Action(0)));
        assert_eq!(state.hit(&data, 20.0, 200.0), None);
        assert_eq!(state.hit(&data, 20.0, 290.0), Some(Hit::Close));
        assert_eq!(state.hit(&data, f64::NAN, 120.0), None);
        assert_eq!(state.hit(&data, -1.0, 120.0), None);
    }

    #[test]
    fn search_is_bounded_and_finds_labels_across_groups() {
        let data = NativeMenu {
            title: "Demo".into(),
            groups: vec![NativeMenuGroup { title: "Tools".into(), actions: vec![
                "terminal".into(), "audio-up".into(), "audio-down".into(),
                "wifi-toggle".into(), "notifications".into(),
            ] }],
        };
        let mut state = MenuState::default();
        state.open();
        assert!(state.search_input("v"));
        assert!(state.search_input("o"));
        assert!(state.search_input("l"));
        assert_eq!(state.actions(&data), vec!["audio-up", "audio-down"]);
        assert_eq!(state.current_action(&data), Some("audio-up"));
        assert!(!state.search_input("☃"));
        assert!(!state.search_input("invalid"));
        assert_eq!(state.search, "vol");
        assert!(state.backspace());
        assert_eq!(state.search, "vo");
        assert!(state.back());
        assert_eq!(state.view, View::Groups);
        state.open();
        assert_eq!(state.view, View::Groups);
        assert!(state.search.is_empty());
    }

    #[test]
    fn pins_and_paged_search_keep_pointer_and_selection_consistent() {
        let data = NativeMenu {
            title: "Demo".into(),
            groups: vec![NativeMenuGroup { title: "Tools".into(), actions: vec![
                "applications".into(), "terminal".into(), "lock".into(),
                "logout".into(), "wifi-toggle".into(), "audio-up".into(),
            ] }],
        };
        let mut state = MenuState::default();
        state.open();
        state.start_search();
        state.select_by(&data, 5);
        assert_eq!(state.current_action(&data), Some("audio-up"));
        assert_eq!(state.first_action_row(), 4);
        assert_eq!(state.hit(&data, 20.0, 111.0), Some(Hit::Action(4)));
        assert_eq!(state.hit(&data, 20.0, 155.0), Some(Hit::Action(5)));
        assert_eq!(state.hit(&data, 20.0, 206.0), None);
        assert!(state.toggle_pin(&data));
        assert_eq!(state.pins, vec!["audio-up"]);
        state.show_saved();
        assert_eq!(state.actions(&data), vec!["audio-up"]);
        assert!(state.toggle_pin(&data));
        assert!(state.actions(&data).is_empty());
        assert_eq!(state.current_action(&data), None);
        state.close();
        state.open();
        assert!(state.pins.is_empty());
    }
}
