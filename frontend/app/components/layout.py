from datetime import datetime
from typing import Optional
from nicegui import ui
from app.session import get_current_user, logout_user
from app.components.theme_switcher import render_theme_switcher
from app.components.notification_bell import render_notification_bell


def get_greeting() -> str:
    """Returns greeting according to local time of day."""
    hr = datetime.now().hour
    if hr < 12:
        return "Good morning"
    elif hr < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def app_shell(title: str = "Mechnova Platform"):
    """Context manager wrapping pages in the standard application shell."""
    user = get_current_user() or {"name": "Elena Rostova", "role": "worker", "company_id": "WRK-001"}
    role = user.get("role", "worker")

    # Global CSS and dynamic theme manager injection
    ui.add_head_html("""
        <link rel="stylesheet" href="/static/css/tokens.css">
        <link rel="stylesheet" href="/static/css/themes.css">
        <link rel="stylesheet" href="/static/css/animations.css">
        <script>
            (function() {
                function loadScript(src, readyCheck, callback) {
                    if (readyCheck && readyCheck()) {
                        if (callback) callback();
                        return;
                    }
                    var existing = document.querySelector('script[data-src="' + src + '"]');
                    if (existing) {
                        var poll = setInterval(function() {
                            if (readyCheck && readyCheck()) {
                                clearInterval(poll);
                                if (callback) callback();
                            }
                        }, 25);
                        return;
                    }
                    var s = document.createElement('script');
                    s.setAttribute('data-src', src);
                    s.src = src;
                    s.onload = function() {
                        if (callback) callback();
                    };
                    document.head.appendChild(s);
                }

                loadScript('/static/js/vendor/three.min.js', function() {
                    return typeof window.THREE !== 'undefined';
                }, function() {
                    loadScript('/static/js/vendor/OrbitControls.js', function() {
                        return window.THREE && typeof window.THREE.OrbitControls !== 'undefined';
                    }, function() {
                        loadScript('/static/js/vendor/STLLoader.js', function() {
                            return window.THREE && typeof window.THREE.STLLoader !== 'undefined';
                        }, function() {
                            loadScript('/static/js/background_scene.js', function() {
                                return typeof window.__mechnova_bg_init !== 'undefined';
                            });
                        });
                    });
                });
            })();
        </script>
        <script>
            (function() {
                var saved = localStorage.getItem('mechnova_theme') || localStorage.getItem('mechnova-theme') || 'plum';
                var aliasMap = {'forest': 'green', 'ocean': 'navy', 'plum': 'purple', 'ember': 'brown', 'green': 'green', 'navy': 'navy', 'purple': 'purple', 'brown': 'brown'};
                var alias = aliasMap[saved] || 'purple';
                var canonical = (saved === 'green' ? 'forest' : saved === 'navy' ? 'ocean' : saved === 'purple' ? 'plum' : saved === 'brown' ? 'ember' : saved);
                document.documentElement.setAttribute('data-accent', canonical);
                document.documentElement.setAttribute('data-theme', alias);
                document.documentElement.dataset.theme = alias;

                window.switchMechnovaTheme = function(themeKey) {
                    var am = {'forest': 'green', 'ocean': 'navy', 'plum': 'purple', 'ember': 'brown'};
                    var al = am[themeKey] || 'purple';
                    document.documentElement.setAttribute('data-accent', themeKey);
                    document.documentElement.setAttribute('data-theme', al);
                    document.documentElement.dataset.theme = al;
                    try {
                        localStorage.setItem('mechnova_theme', themeKey);
                        localStorage.setItem('mechnova-theme', al);
                    } catch(e) {}
                    document.querySelectorAll('.theme-dot-btn').forEach(function(el) {
                        if (el.getAttribute('data-theme-key') === themeKey) {
                            el.classList.add('theme-dot-active');
                        } else {
                            el.classList.remove('theme-dot-active');
                        }
                    });
                };

                window.highlightActiveSidebar = function() {
                    var path = window.location.pathname;
                    document.querySelectorAll('.sidebar-nav-item').forEach(function(item) {
                        var href = item.getAttribute('data-href');
                        if (!href) return;
                        var isMatch = false;
                        if (href === '/worker') {
                            isMatch = (path === '/worker' || path === '/worker/');
                        } else if (href === '/worker/new-project') {
                            isMatch = path.includes('/new-project') || path.includes('/upload');
                        } else if (href === '/worker/design-details') {
                            isMatch = path.includes('/design-details');
                        } else if (href === '/worker/history') {
                            isMatch = path.includes('/history');
                        } else if (href === '/worker/equipment') {
                            isMatch = path.includes('/equipment');
                        } else {
                            isMatch = path.startsWith(href);
                        }
                        if (isMatch) {
                            item.classList.add('sidebar-active');
                        } else {
                            item.classList.remove('sidebar-active');
                        }
                    });
                };

                document.addEventListener('DOMContentLoaded', window.highlightActiveSidebar);
                setTimeout(window.highlightActiveSidebar, 200);
            })();
        </script>
    """)

    # Top Header
    with ui.header().classes("px-6 py-3 glass-panel border-b border-[var(--border)] items-center justify-between z-20"):
        with ui.row().classes("items-center gap-4"):
            with ui.row().classes("items-center gap-2 cursor-pointer").on("click", lambda: ui.navigate.to(f"/{role}")):
                ui.icon("precision_manufacturing", size="28px").classes("text-[var(--accent)]")
                with ui.column().classes("gap-0"):
                    ui.label("MECHNOVA").classes("font-black text-lg tracking-wider text-[var(--accent-900)] leading-none")
                    ui.label("CAD-to-CNC Autonomous Suite").classes("text-[10px] text-[var(--text-muted)] tracking-widest uppercase")

            ui.separator().props("vertical").classes("h-6 mx-2")
            ui.label(f"{get_greeting()}, {user.get('name', 'Operator')}").classes("text-sm font-semibold text-[var(--text)] hidden sm:block")
            
            if role == "worker":
                with ui.badge(color="positive").props("outline").classes("text-xs font-mono font-bold px-2 py-0.5 hidden md:flex items-center gap-1"):
                    ui.element("span").classes("w-2 h-2 rounded-full bg-green-500 animate-pulse")
                    ui.label("WORKER MODE")
            
            with ui.badge().classes("text-xs uppercase font-mono px-2 py-0.5 rounded-md border border-[var(--border)] bg-[var(--surface-alt)] text-[var(--text)]"):
                ui.label(str(user.get("company_id") or "WRK-001"))

        with ui.row().classes("items-center gap-3"):
            render_theme_switcher()
            ui.timer(0.1, render_notification_bell, once=True)
            ui.button(icon="logout", on_click=logout_user).props("flat round color=grey size=sm").tooltip("Sign Out")

    # Left Sidebar Navigation
    with ui.left_drawer(value=True).classes("p-4 border-r border-[var(--border)] glass-panel z-10 w-64 flex flex-col justify-between"):
        with ui.column().classes("w-full gap-2"):
            if role == "admin":
                ui.label("ADMINISTRATION").classes("text-[11px] font-bold tracking-wider text-[var(--text-muted)] uppercase mb-1 px-2")
                with ui.item(on_click=lambda: ui.navigate.to("/admin")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/admin"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("dashboard", size="20px")
                    with ui.item_section():
                        ui.item_label("Admin Overview")

                with ui.item(on_click=lambda: ui.navigate.to("/admin/machines")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/admin/machines"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("precision_manufacturing", size="20px")
                    with ui.item_section():
                        ui.item_label("Machine Details")

                with ui.item(on_click=lambda: ui.navigate.to("/admin/workers")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/admin/workers"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("badge", size="20px")
                    with ui.item_section():
                        ui.item_label("Worker Details")

                with ui.item(on_click=lambda: ui.navigate.to("/admin/requests")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/admin/requests"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("schedule", size="20px")
                    with ui.item_section():
                        ui.item_label("Machine Requests")

            else:  # Worker
                # SEPARATED SECTION 1: WORKER DASHBOARD & OPERATIONS
                ui.label("OPERATIONS & TELEMETRY").classes("text-[10px] font-bold tracking-wider text-[var(--text-muted)] uppercase mb-1 px-2")
                with ui.item(on_click=lambda: ui.navigate.to("/worker")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/worker"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("dashboard", size="22px")
                    with ui.item_section():
                        ui.item_label("Worker Dashboard").classes("font-bold text-sm")

                with ui.item(on_click=lambda: ui.navigate.to("/worker/history")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/worker/history"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("history", size="22px")
                    with ui.item_section():
                        ui.item_label("Project History").classes("text-sm font-semibold")

                ui.separator().classes("my-2")

                # SEPARATED SECTION 2: CAD / CNC PROJECT WIZARD & DESIGN
                ui.label("CAD / CNC WORKFLOW").classes("text-[10px] font-bold tracking-wider text-[var(--text-muted)] uppercase mb-1 px-2")
                
                from app.services.project_service import get_active_project_id, set_active_project_id
                active_id = get_active_project_id()

                def handle_new_project_click():
                    ui.run_javascript("try { sessionStorage.removeItem('mechnova_active_project_id'); } catch(e){}")
                    set_active_project_id(None)
                    ui.navigate.to("/worker/new-project")

                with ui.item(on_click=handle_new_project_click).classes("sidebar-nav-item rounded-xl cursor-pointer p-2 shadow-sm").props('data-href="/worker/new-project"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("add_circle", size="22px")
                    with ui.item_section():
                        ui.item_label("New Project").classes("font-bold text-sm")
                        ui.label("Step-by-step CAD setup").classes("text-[10px] text-[var(--text-muted)]")

                if active_id:
                    with ui.item(on_click=lambda: ui.navigate.to(f"/worker/projects/{active_id}/design-details")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/worker/design-details"'):
                        with ui.item_section().props("avatar"):
                            ui.icon("view_in_ar", size="22px")
                        with ui.item_section():
                            ui.item_label("Design Details").classes("text-sm font-semibold")
                            ui.label("Geometry & Features").classes("text-[10px] text-[var(--text-muted)]")
                else:
                    with ui.item(on_click=lambda: ui.notify("Please start or load a project first", type="info")).classes("sidebar-nav-item rounded-xl opacity-60 cursor-pointer p-2").props('data-href="/worker/design-details"'):
                        with ui.item_section().props("avatar"):
                            ui.icon("view_in_ar", size="22px")
                        with ui.item_section():
                            ui.item_label("Design Details").classes("text-sm")
                            ui.label("Upload model first").classes("text-[10px] text-[var(--text-muted)]")

                with ui.item(on_click=lambda: ui.navigate.to("/worker/equipment")).classes("sidebar-nav-item rounded-xl cursor-pointer p-2").props('data-href="/worker/equipment"'):
                    with ui.item_section().props("avatar"):
                        ui.icon("build", size="22px")
                    with ui.item_section():
                        ui.item_label("Equipment / Tool Crib").classes("text-sm font-semibold")

        with ui.element("div").classes("pt-4 border-t border-[var(--border)] text-[11px] text-[var(--text-muted)] px-2"):
            ui.label("MECHNOVA Autonomous Suite").classes("font-semibold text-[var(--accent-900)]")
            ui.label("Shop Floor Operator Console")
