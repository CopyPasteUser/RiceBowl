"""Period-styled Windows 98 Help Topics with real contents, index and search.

The user is running Linux: no Windows compatibility or configuration settings
are fabricated. Topic text is original and bundled locally with RiceBowl.
"""
from __future__ import annotations


TOPICS = {
    "Getting Started":
        "RiceBowl is a native Linux desktop that recreates the Windows 98 SE "
        "shell. Use the Start button to open real installed applications and "
        "system settings. Right-click the taskbar for Properties.",
    "Start Menu":
        "Programs groups installed Linux applications. Favorites stores shortcuts "
        "to user-selected files, folders and websites. Documents reads recent "
        "GTK file history. Find searches files; Run opens paths, addresses and "
        "programs. Shut Down invokes the session's supported logout options.",
    "Programs and Quick Launch":
        "Right-click a program inside Start > Programs to pin or unpin it from "
        "Quick Launch. Use Quick Launch for frequently opened programs and the "
        "Show Desktop shortcut. Running-window taskbar buttons have real "
        "window-manager actions.",
    "Finding Files":
        "Open Start > Find > Files or Folders. Search a selected folder by name. "
        "Advanced options support file or folder type, extension, modified date, "
        "size, hidden files and a limited UTF-8 content search. Find reads at "
        "most 50,000 entries and returns at most 500 results. Content search "
        "only reads ordinary files up to 1 MiB each and 32 MiB total. "
        "Stop cancels the worker; no files are changed.",
    "Running Programs":
        "Start > Run accepts installed program names with arguments, local "
        "paths and supported web addresses. Browse selects an existing file. "
        "Run does not execute commands through a shell, and its recent history "
        "remains in memory for this session only. Clear history erases it.",
    "Favorites":
        "Start > Favorites lists your RiceBowl favorites and imported GTK "
        "bookmarks. Organize Favorites can add, rename, reorder and remove "
        "RiceBowl-owned entries without editing your GTK bookmarks.",
    "Recent Documents":
        "Start > Documents lists recently accessed files from GTK. Clear Recent "
        "Documents removes history entries after confirmation; it does not "
        "delete the files themselves. Missing paths are disabled.",
    "Taskbar":
        "Right-click empty taskbar space and select Properties, or choose "
        "Start > Settings > Taskbar & Start Menu. You can toggle the clock "
        "and Quick Launch. Other settings remain unavailable until they can "
        "be implemented safely without modifying other desktop styles.",
    "Control Panel":
        "Open Start > Settings > Control Panel for original-era icon navigation. "
        "Applets open real Linux settings utilities, and unavailable tools are "
        "marked accordingly. Your actual OS remains Linux, not Windows 98.",
    "Audio, Network and Battery":
        "Click the appropriate taskbar status icon to inspect real devices. "
        "Volume and mute use the available Linux audio backend. Network status "
        "comes from live network services. Battery status is shown only when "
        "provided by the machine; no readings are invented.",
    "Files and Folders":
        "Files are stored in native Linux directories. The current explorer "
        "fallback is Thunar. RiceExplorer is a separate customizable file "
        "manager in development. Do not assume Windows drive letters or "
        "that Windows executables run natively.",
    "Privacy and Recovery":
        "Run command history is kept only during the active shell session. "
        "RiceBowl favorites and taskbar preferences use user-owned XDG files. "
        "Use 'macrice rice restore' to restore your previous desktop settings "
        "after switching a rice. Keep Thunar installed until RiceExplorer "
        "is validated on your hardware.",
    "Keyboard and Accessibility":
        "The Start menu and most application windows support ordinary GTK "
        "keyboard navigation. Escape closes dialogs, arrows navigate lists, "
        "and Enter opens selected items. Some historical shortcuts and full "
        "screen-reader parity remain in development.",
}

INDEX = {
    "Applications": "Start Menu",
    "Audio": "Audio, Network and Battery",
    "Backup and Recovery": "Privacy and Recovery",
    "Battery": "Audio, Network and Battery",
    "Control Panel": "Control Panel",
    "Date Filter": "Finding Files",
    "Documents": "Recent Documents",
    "Explorer": "Files and Folders",
    "Favorites": "Favorites",
    "Find": "Finding Files",
    "History": "Running Programs",
    "Hotkeys": "Keyboard and Accessibility",
    "Network": "Audio, Network and Battery",
    "Quick Launch": "Programs and Quick Launch",
    "Run": "Running Programs",
    "Settings": "Control Panel",
    "Start": "Start Menu",
    "Taskbar": "Taskbar",
    "Windows Compatibility": "Files and Folders",
}


def search_topics(query: str) -> tuple[str, ...]:
    """Case-insensitive local text search with a stable results order."""
    needle = query.strip().casefold()
    if not needle:
        return ()
    matches = set()
    for name, body in TOPICS.items():
        if needle in name.casefold() or needle in body.casefold():
            matches.add(name)
    for word, topic in INDEX.items():
        if needle in word.casefold():
            matches.add(topic)
    return tuple(name for name in TOPICS if name in matches)


def show_help(shell, Gtk):
    """Construct a genuine navigable Help viewer; no external browser needed."""
    shell._hide_menu()
    dialog = Gtk.Dialog(title="RiceBowl Help", transient_for=shell.bar)
    dialog.set_default_size(720, 455)
    dialog.set_resizable(True)
    dialog.add_button("Close", Gtk.ResponseType.CLOSE)
    body = dialog.get_content_area()
    body.set_spacing(7)
    body.set_border_width(8)

    toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    back = Gtk.Button(label="◀ Back")
    forward = Gtk.Button(label="Forward ▶")
    home = Gtk.Button(label="Home")
    for button in (back, forward, home):
        toolbar.pack_start(button, False, False, 0)
    body.pack_start(toolbar, False, False, 0)

    divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    body.pack_start(divider, False, False, 0)

    split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
    split.set_position(230)
    body.pack_start(split, True, True, 0)
    tabs = Gtk.Notebook()
    tabs.set_size_request(220, -1)
    split.pack1(tabs, resize=False, shrink=False)

    def make_list_tab(title):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        listing = Gtk.ListBox()
        listing.set_activate_on_single_click(True)
        scroll.add(listing)
        tabs.append_page(scroll, Gtk.Label(label=title))
        return listing

    contents = make_list_tab("Contents")
    alphabet = make_list_tab("Index")
    search_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    search_panel.set_border_width(4)
    search = Gtk.SearchEntry()
    search.set_placeholder_text("Search Help…")
    search.get_accessible().set_name("Search help topics")
    search_panel.pack_start(search, False, False, 0)
    search_scroll = Gtk.ScrolledWindow()
    search_results = Gtk.ListBox()
    search_results.set_activate_on_single_click(True)
    search_scroll.add(search_results)
    search_panel.pack_start(search_scroll, True, True, 0)
    tabs.append_page(search_panel, Gtk.Label(label="Search"))

    article = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    article.set_border_width(10)
    heading = Gtk.Label(xalign=0)
    heading.get_style_context().add_class("classic98-help-title")
    article.pack_start(heading, False, False, 0)
    scroll_text = Gtk.ScrolledWindow()
    reading = Gtk.TextView()
    reading.set_editable(False)
    reading.set_cursor_visible(False)
    reading.set_wrap_mode(Gtk.WrapMode.WORD)
    reading.set_left_margin(7)
    reading.set_right_margin(7)
    scroll_text.add(reading)
    article.pack_start(scroll_text, True, True, 0)
    location = Gtk.Label(xalign=0)
    article.pack_end(location, False, False, 0)
    split.pack2(article, resize=True, shrink=False)

    history = ["Getting Started"]
    cursor = 0

    def display(topic):
        heading.set_text(topic)
        reading.get_buffer().set_text(TOPICS[topic])
        location.set_text(f"RiceBowl Help · {topic}")
        back.set_sensitive(cursor > 0)
        forward.set_sensitive(cursor < len(history) - 1)

    def visit(topic):
        nonlocal history, cursor
        if topic not in TOPICS or topic == history[cursor]:
            return
        history = history[:cursor + 1] + [topic]
        cursor += 1
        display(topic)

    def move(step):
        nonlocal cursor
        next_cursor = cursor + step
        if 0 <= next_cursor < len(history):
            cursor = next_cursor
            display(history[cursor])

    back.connect("clicked", lambda _button: move(-1))
    forward.connect("clicked", lambda _button: move(1))
    home.connect("clicked", lambda _button: visit("Getting Started"))

    def add_row(listing, label, topic):
        row = Gtk.ListBoxRow()
        row._help_topic = topic
        text = Gtk.Label(label=label, xalign=0)
        text.set_line_wrap(True)
        text.set_margin_start(5)
        text.set_margin_end(5)
        text.set_margin_top(4)
        text.set_margin_bottom(4)
        row.add(text)
        listing.add(row)

    def row_selected(_listing, row):
        if row is not None:
            visit(row._help_topic)

    for listing in (contents, alphabet, search_results):
        listing.connect("row-activated", row_selected)
    for name in TOPICS:
        add_row(contents, name, name)
    for name, target in sorted(INDEX.items(), key=lambda pair: pair[0].casefold()):
        add_row(alphabet, name, target)

    def refresh_search(_entry):
        for child in search_results.get_children():
            search_results.remove(child)
        matches = search_topics(search.get_text())
        for name in matches:
            add_row(search_results, name, name)
        search_results.show_all()

    search.connect("search-changed", refresh_search)
    dialog.show_all()
    display(history[cursor])
    try:
        dialog.run()
    finally:
        dialog.destroy()
