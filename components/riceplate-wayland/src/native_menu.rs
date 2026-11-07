//! Bounded, input-independent navigation for a real native RicePlate menu.
//! Every row maps to a validated recipe action; labels never become commands.

use crate::recipe::NativeMenu;

pub const WIDTH: u32 = 320;
pub const HEIGHT: u32 = 304;
pub const TAB_TOP: u32 = 46;
pub const TAB_HEIGHT: u32 = 40;
pub const ACTION_TOP: u32 = 108;
pub const ACTION_HEIGHT: u32 = 42;

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
}

impl MenuState {
    pub fn open(&mut self) {
        self.visible = true;
        self.group = 0;
        self.selected = 0;
        self.notice = None;
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
    }

    pub fn select_by(&mut self, menu: &NativeMenu, delta: isize) {
        let Some(group) = menu.groups.get(self.group) else {
            return;
        };
        let count = group.actions.len();
        if count == 0 {
            return;
        }
        self.selected = (self.selected as isize + delta).rem_euclid(count as isize) as usize;
    }

    pub fn current_action<'a>(&self, menu: &'a NativeMenu) -> Option<&'a str> {
        menu.groups
            .get(self.group)?
            .actions
            .get(self.selected)
            .map(String::as_str)
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
        if (f64::from(ACTION_TOP)..f64::from(ACTION_TOP + 4 * ACTION_HEIGHT)).contains(&y) {
            let index = (y as u32 - ACTION_TOP) / ACTION_HEIGHT;
            return menu
                .groups
                .get(self.group)?
                .actions
                .get(index as usize)
                .map(|_| Hit::Action(index as usize));
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
}
