from typing import List, Dict
from nicegui import app, ui

THEMES: Dict[str, Dict[str, str]] = {
    "forest": {
        "name": "Forest (Green)",
        "alias": "green",
        "swatch": "#0D4128",
        "accent": "#1D7147",
        "light": "#EDF8F2"
    },
    "ocean": {
        "name": "Ocean (Navy)",
        "alias": "navy",
        "swatch": "#11356D",
        "accent": "#204C9E",
        "light": "#EDF8F6"
    },
    "plum": {
        "name": "Plum (Purple)",
        "alias": "purple",
        "swatch": "#4F2E85",
        "accent": "#4F2E85",
        "light": "#F6EDF8"
    },
    "ember": {
        "name": "Ember (Brown)",
        "alias": "brown",
        "swatch": "#843413",
        "accent": "#843413",
        "light": "#F8EFED"
    }
}


def get_current_theme() -> str:
    """Returns stored theme key, default forest."""
    return app.storage.user.get("theme", "forest")


def set_theme(theme_key: str) -> None:
    """Sets active theme and updates document data-accent and data-theme attributes."""
    # Support both forest/ocean/plum/ember and green/navy/purple/brown
    resolved_key = theme_key
    for k, v in THEMES.items():
        if theme_key in (k, v.get("alias")):
            resolved_key = k
            break

    if resolved_key in THEMES:
        alias = THEMES[resolved_key]["alias"]
        app.storage.user["theme"] = resolved_key
        ui.run_javascript(f"""
            document.documentElement.setAttribute('data-accent', '{resolved_key}');
            document.documentElement.setAttribute('data-theme', '{alias}');
            document.documentElement.dataset.theme = '{alias}';
            try {{
                localStorage.setItem('mechnova_theme', '{resolved_key}');
                localStorage.setItem('mechnova-theme', '{alias}');
            }} catch(e) {{}}
        """)
