from nicegui import ui

STATUS_STYLES = {
    # Machines
    "working": {"bg": "var(--status-warning-bg)", "border": "var(--status-warning-border)", "text": "var(--status-warning-text)", "label": "Working"},
    "idle": {"bg": "var(--status-success-bg)", "border": "var(--status-success-border)", "text": "var(--status-success-text)", "label": "Idle (Ready)"},
    "maintenance": {"bg": "var(--status-info-bg)", "border": "var(--status-info-border)", "text": "var(--status-info-text)", "label": "Maintenance"},
    "offline": {"bg": "var(--status-danger-bg)", "border": "var(--status-danger-border)", "text": "var(--status-danger-text)", "label": "Offline"},
    
    # Projects
    "draft": {"bg": "var(--surface-alt)", "border": "var(--border)", "text": "var(--text-muted)", "label": "Draft"},
    "analysed": {"bg": "var(--status-review-bg)", "border": "var(--status-review-border)", "text": "var(--status-review-text)", "label": "Analysed [DFM Ready]"},
    "requested": {"bg": "var(--status-warning-bg)", "border": "var(--status-warning-border)", "text": "var(--status-warning-text)", "label": "Pending Approval"},
    "approved": {"bg": "var(--status-success-bg)", "border": "var(--status-success-border)", "text": "var(--status-success-text)", "label": "Approved [Deployable]"},
    "rejected": {"bg": "var(--status-danger-bg)", "border": "var(--status-danger-border)", "text": "var(--status-danger-text)", "label": "Rejected"},
    "deployed": {"bg": "var(--status-warning-bg)", "border": "var(--status-warning-border)", "text": "var(--status-warning-text)", "label": "Cutting (Simulated)"},
    "completed": {"bg": "var(--status-success-bg)", "border": "var(--status-success-border)", "text": "var(--status-success-text)", "label": "100% Completed"},
    
    # Tools
    "fresh": {"bg": "var(--status-success-bg)", "border": "var(--status-success-border)", "text": "var(--status-success-text)", "label": "Fresh (100%)"},
    "in_use": {"bg": "var(--status-info-bg)", "border": "var(--status-info-border)", "text": "var(--status-info-text)", "label": "In Spindle"},
    "worn": {"bg": "var(--status-danger-bg)", "border": "var(--status-danger-border)", "text": "var(--status-danger-text)", "label": "Worn (>85%)"},
    "replaced": {"bg": "var(--status-review-bg)", "border": "var(--status-review-border)", "text": "var(--status-review-text)", "label": "Auto-Replaced"},
}


def render_status_chip(status_key: str, pulse: bool = False):
    """Renders a tinted pastel badge with 1px border matching design tokens."""
    cfg = STATUS_STYLES.get(status_key.lower(), {
        "bg": "var(--surface-alt)", "border": "var(--border)", "text": "var(--text)", "label": status_key.title()
    })
    
    pulse_cls = "pulse-working" if (pulse or status_key.lower() in ("working", "deployed")) else ""
    
    with ui.row().classes(f"items-center px-2.5 py-1 rounded-full text-xs font-semibold {pulse_cls}").style(
        f"background-color: {cfg['bg']}; border: 1px solid {cfg['border']}; color: {cfg['text']};"
    ):
        ui.label(cfg["label"])
