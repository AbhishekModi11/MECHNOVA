from nicegui import ui
from app.api_client import api


async def render_notification_bell():
    """Renders interactive notification bell with badge and popover list."""
    try:
        data = await api.get_notifications()
        unread = data.get("unread_count", 0)
        notifs = data.get("notifications", [])
    except Exception:
        unread = 0
        notifs = []

    badge_props = f'color="red" floating' if unread > 0 else 'style="display:none"'

    with ui.button(icon="notifications").props("flat round color=primary"):
        if unread > 0:
            ui.badge(str(unread), color="red").props("floating")

        with ui.menu().classes("w-80 p-2 glass-panel"):
            with ui.row().classes("items-center justify-between w-full px-2 py-1 border-b border-[var(--border)]"):
                ui.label("Notifications").classes("font-bold text-sm text-[var(--text)]")
                ui.label(f"{unread} new").classes("text-xs text-[var(--text-muted)]")

            if not notifs:
                ui.label("No recent notifications").classes("text-xs text-[var(--text-muted)] p-3 text-center")
            else:
                with ui.column().classes("gap-1 max-h-60 overflow-y-auto w-full pt-1"):
                    for n in notifs[:8]:
                        bg_cls = "bg-[var(--accent-50)]" if not n["read"] else ""
                        with ui.card().classes(f"p-2 w-full text-xs border border-[var(--border)] {bg_cls}"):
                            ui.label(n["message"]).classes("font-medium text-[var(--text)] leading-snug")
                            ui.label(n["created_at"][:16].replace("T", " ")).classes("text-[10px] text-[var(--text-muted)] mt-1")
