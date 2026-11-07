//! Local, offline calendar state and bounded click geometry for native RicePlate.
//! Presentation and Wayland input are owned by the existing shell process.

use chrono::{Datelike, Duration, NaiveDate};

pub const WIDTH: u32 = 336;
pub const HEIGHT: u32 = 352;
pub const GRID_X: u32 = 12;
pub const GRID_Y: u32 = 104;
pub const CELL_WIDTH: u32 = 44;
pub const CELL_HEIGHT: u32 = 34;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Hit {
    Previous,
    Next,
    Today,
    Day(NaiveDate),
}

pub struct CalendarState {
    pub today: NaiveDate,
    pub month: NaiveDate,
    pub selected: NaiveDate,
    pub visible: bool,
}

impl CalendarState {
    pub fn new(today: NaiveDate) -> Self {
        Self {
            today,
            month: NaiveDate::from_ymd_opt(today.year(), today.month(), 1).unwrap(),
            selected: today,
            visible: false,
        }
    }

    pub fn open(&mut self, today: NaiveDate) {
        self.today = today;
        self.month = NaiveDate::from_ymd_opt(today.year(), today.month(), 1).unwrap();
        self.selected = today;
        self.visible = true;
    }

    pub fn shift(&mut self, delta: i32) {
        let index = self.month.year() * 12 + self.month.month0() as i32;
        let next = index.saturating_add(delta);
        let year = next.div_euclid(12);
        let month = next.rem_euclid(12) as u32 + 1;
        if let Some(day) = NaiveDate::from_ymd_opt(year, month, 1) {
            self.month = day;
            self.selected = (1..=self.selected.day())
                .rev()
                .find_map(|number| NaiveDate::from_ymd_opt(year, month, number))
                .unwrap();
        }
    }

    pub fn go_today(&mut self, date: NaiveDate) {
        self.open(date);
    }

    pub fn select(&mut self, day: NaiveDate) {
        self.selected = day;
        self.month = NaiveDate::from_ymd_opt(day.year(), day.month(), 1).unwrap();
    }

    pub fn move_selection(&mut self, delta_days: i64) {
        if let Some(day) = self.selected.checked_add_signed(Duration::days(delta_days)) {
            self.select(day);
        }
    }

    pub fn cells(&self) -> Vec<(NaiveDate, bool)> {
        let offset = i64::from(self.month.weekday().num_days_from_monday());
        let first = self
            .month
            .checked_sub_signed(Duration::days(offset))
            .unwrap_or(self.month);
        (0..42)
            .filter_map(|index| {
                first.checked_add_signed(Duration::days(index)).map(|date| {
                    (
                        date,
                        date.month() == self.month.month() && date.year() == self.month.year(),
                    )
                })
            })
            .collect()
    }

    pub fn hit(&self, x: f64, y: f64) -> Option<Hit> {
        if !self.visible
            || !x.is_finite()
            || !y.is_finite()
            || x < 0.0
            || y < 0.0
            || x >= f64::from(WIDTH)
            || y >= f64::from(HEIGHT)
        {
            return None;
        }
        if (10.0..46.0).contains(&y) {
            if (244.0..286.0).contains(&x) {
                return Some(Hit::Previous);
            }
            if (288.0..330.0).contains(&x) {
                return Some(Hit::Next);
            }
        }
        if (322.0..350.0).contains(&y) && (12.0..104.0).contains(&x) {
            return Some(Hit::Today);
        }
        let local_x = x - f64::from(GRID_X);
        let local_y = y - f64::from(GRID_Y);
        if local_x < 0.0
            || local_x >= f64::from(CELL_WIDTH * 7)
            || local_y < 0.0
            || local_y >= f64::from(CELL_HEIGHT * 6)
        {
            return None;
        }
        let column = (local_x / f64::from(CELL_WIDTH)) as usize;
        let row = (local_y / f64::from(CELL_HEIGHT)) as usize;
        self.cells()
            .get(row * 7 + column)
            .map(|(date, _)| Hit::Day(*date))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn day(year: i32, month: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(year, month, day).unwrap()
    }

    #[test]
    fn leap_year_and_monday_grid_are_real_dates() {
        let mut calendar = CalendarState::new(day(2026, 11, 7));
        calendar.open(day(2026, 11, 7));
        calendar.month = day(2024, 2, 1);
        let cells = calendar.cells();
        assert_eq!(cells.len(), 42);
        assert_eq!(cells[0].0, day(2024, 1, 29));
        assert!(cells.contains(&(day(2024, 2, 29), true)));
        assert_eq!(cells[6].0.weekday().num_days_from_monday(), 6);
    }

    #[test]
    fn month_navigation_and_today_reset_cross_year() {
        let mut calendar = CalendarState::new(day(2026, 12, 19));
        calendar.open(day(2026, 12, 19));
        calendar.shift(1);
        assert_eq!(calendar.month, day(2027, 1, 1));
        calendar.shift(-2);
        assert_eq!(calendar.month, day(2026, 11, 1));
        calendar.go_today(day(2027, 3, 3));
        assert_eq!(calendar.selected, day(2027, 3, 3));
        assert_eq!(calendar.month, day(2027, 3, 1));
        calendar.move_selection(-7);
        assert_eq!(calendar.selected, day(2027, 2, 24));
        assert_eq!(calendar.month, day(2027, 2, 1));
        calendar.go_today(day(2024, 1, 31));
        calendar.shift(1);
        assert_eq!(calendar.selected, day(2024, 2, 29));
    }

    #[test]
    fn pointer_hit_testing_is_bounded_and_selects_real_dates() {
        let mut calendar = CalendarState::new(day(2026, 11, 7));
        assert_eq!(calendar.hit(250.0, 15.0), None);
        calendar.open(day(2026, 11, 7));
        assert_eq!(calendar.hit(250.0, 15.0), Some(Hit::Previous));
        assert_eq!(calendar.hit(300.0, 15.0), Some(Hit::Next));
        assert_eq!(calendar.hit(20.0, 335.0), Some(Hit::Today));
        assert_eq!(calendar.hit(20.0, 110.0), Some(Hit::Day(day(2026, 10, 26))));
        assert_eq!(calendar.hit(-1.0, 120.0), None);
        assert_eq!(calendar.hit(f64::NAN, 120.0), None);
    }
}
