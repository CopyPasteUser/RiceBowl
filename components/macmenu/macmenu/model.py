"""Search and category logic without a GUI dependency."""

from dataclasses import dataclass
import unicodedata


CATEGORIES = {
    "Development": "Development",
    "Network": "Internet",
    "Office": "Office",
    "AudioVideo": "Media",
    "Audio": "Media",
    "Video": "Media",
    "Graphics": "Graphics",
    "Game": "Games",
    "Education": "Education",
    "System": "System",
    "Settings": "System",
    "Utility": "Utilities",
}

ORDER = [
    "Favorites", "Recent", "All Apps", "Development", "Internet", "Office",
    "Media", "Graphics", "Games", "Education", "System", "Utilities", "Other",
]


@dataclass(frozen=True)
class AppEntry:
    app_id: str
    name: str
    description: str
    category: str
    keywords: str = ""
    icon: object = None
    launcher: object = None


def category_for(raw: str | None) -> str:
    tokens = (raw or "").split(";")
    return next((CATEGORIES[token] for token in tokens if token in CATEGORIES), "Other")


def search_key(value: str) -> str:
    """Accent-insensitive search without changing the displayed application name."""
    folded = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))


def select_apps(
    apps: list[AppEntry], query: str, category: str, favorites: list[str], recent: list[str]
) -> list[AppEntry]:
    needle = search_key(query.strip())
    terms = needle.split()
    def matches_terms(app: AppEntry) -> bool:
        if not terms:
            return True
        haystack = search_key(f"{app.name} {app.description} {app.keywords} {app.category}")
        return all(term in haystack for term in terms)

    matches = [app for app in apps if matches_terms(app)]
    if terms:
        def rank(app: AppEntry) -> tuple[int, int, str]:
            name = search_key(app.name)
            name_terms = all(term in name for term in terms)
            priority = 0 if name == needle else 1 if name.startswith(needle) else 2 if name_terms else 3
            return (priority, 0 if app.app_id in favorites else 1, name)
        return sorted(matches, key=rank)
    if category == "Favorites":
        by_id = {app.app_id: app for app in matches}
        return [by_id[app_id] for app_id in favorites if app_id in by_id]
    if category == "Recent":
        by_id = {app.app_id: app for app in matches}
        return [by_id[app_id] for app_id in recent if app_id in by_id]
    if category != "All Apps":
        matches = [app for app in matches if app.category == category]
    return sorted(matches, key=lambda app: app.name.casefold())


def move_favorite(favorites: list[str], app_id: str, offset: int) -> list[str]:
    if app_id not in favorites:
        return list(favorites)
    result = list(favorites)
    old = result.index(app_id)
    new = max(0, min(len(result) - 1, old + offset))
    result.insert(new, result.pop(old))
    return result


def visible_page(apps: list[AppEntry], limit: int) -> tuple[list[AppEntry], int]:
    """Bound the number of GTK rows instantiated in an initial menu render."""
    shown = apps[:max(0, limit)]
    return shown, len(apps) - len(shown)
