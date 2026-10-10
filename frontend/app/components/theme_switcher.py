from nicegui import ui
from app.theme import THEMES, get_current_theme, set_theme


def render_theme_switcher():
    """Renders a sleek theme accent selector."""
    current = get_current_theme()

    with ui.row().classes("theme-switcher items-center gap-1.5 p-1 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)]"):
        for key, info in THEMES.items():
            is_active = (key == current)
            active_cls = "theme-dot-active" if is_active else ""
            
            def make_handler(k=key):
                def handler():
                    set_theme(k)
                    ui.run_javascript(f"if (window.switchMechnovaTheme) window.switchMechnovaTheme('{k}');")
                return handler

            btn = ui.button(on_click=make_handler(key)).props("round flat size=sm").classes(
                f"w-6 h-6 p-0 transition-all theme-dot-btn {active_cls}"
            ).props(f'data-theme-key="{key}"').tooltip(f"Switch to {info['name']} theme")
            with btn:
                ui.element("div").classes("w-4 h-4 rounded-full").style(f"background-color: {info['swatch']}; pointer-events: none;")
