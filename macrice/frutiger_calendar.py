"""Native, local-only Aqua date flyout; no daemon, network or calendar sync."""

from datetime import datetime

from .frutiger_tray_window import create_tray_window


class AquaCalendar:
    def __init__(self, anchor, Gtk):
        self.Gtk = Gtk
        self.popover = create_tray_window(anchor, Gtk, title="Aqua World · Calendar")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.get_style_context().add_class("aqua-flyout-root")
        heading = Gtk.Label(label="Your calendar", xalign=0)
        heading.get_style_context().add_class("aqua-flyout-title")
        root.pack_start(heading, False, False, 0)

        self.caption = Gtk.Label(xalign=0)
        self.caption.get_style_context().add_class("aqua-flyout-status")
        root.pack_start(self.caption, False, False, 0)
        self.calendar = Gtk.Calendar()
        self.calendar.set_display_options(
            Gtk.CalendarDisplayOptions.SHOW_HEADING |
            Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES)
        self.calendar.get_accessible().set_name("Select a date in the local calendar")
        root.pack_start(self.calendar, False, False, 0)

        today = Gtk.Button(label="↻  Return to today")
        today.get_style_context().add_class("aqua-flyout-more")
        today.get_accessible().set_name("Select today's date")
        today.connect("clicked", lambda _button: self.reset_today())
        root.pack_start(today, False, False, 0)
        self.popover.add(root)

    def reset_today(self):
        now = datetime.now().astimezone()
        self.calendar.select_month(now.month - 1, now.year)
        self.calendar.select_day(now.day)
        self.caption.set_text(now.strftime("%A, %d %B %Y · %Z"))

    def show(self):
        self.reset_today()
        self.popover.show_all()
        self.popover.popup()
