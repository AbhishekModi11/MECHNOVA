import asyncio
from nicegui import ui
from app.api_client import api
from app.session import login_user, is_authenticated
from app.components.theme_switcher import render_theme_switcher


def register_login_page():
    @ui.page("/login")
    def login_page():
        if is_authenticated():
            ui.navigate.to("/worker")
            return

        ui.add_head_html("""
            <link rel="stylesheet" href="/static/css/tokens.css">
            <link rel="stylesheet" href="/static/css/themes.css">
            <link rel="stylesheet" href="/static/css/animations.css">
            <script>
                (function() {
                    function loadScript(src, cb) {
                        if (document.querySelector('script[data-src="' + src + '"]')) {
                            if (cb) cb();
                            return;
                        }
                        var s = document.createElement('script');
                        s.setAttribute('data-src', src);
                        s.src = src;
                        s.onload = cb;
                        document.head.appendChild(s);
                    }
                    if (typeof THREE === 'undefined') {
                        loadScript('/static/js/vendor/three.min.js', function() {
                            loadScript('/static/js/background_scene.js');
                        });
                    } else {
                        loadScript('/static/js/background_scene.js');
                    }
                })();
            </script>
        """)

        with ui.column().classes("min-h-screen w-full items-center justify-center p-4 relative z-10"):
            # Brand Header
            with ui.row().classes("items-center justify-between w-full max-w-md mb-4 px-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("precision_manufacturing", size="36px").classes("text-[var(--accent-600)]")
                    with ui.column().classes("gap-0"):
                        ui.label("MECHNOVA").classes("font-black text-2xl tracking-wider text-[var(--accent-900)] leading-none")
                        ui.label("Autonomous CAD-to-CNC Engine").classes("text-xs text-[var(--text-muted)] tracking-widest uppercase")
                render_theme_switcher()

            # Main Login Card with Glassmorphism
            with ui.card().classes("w-full max-w-md p-6 glass-panel border border-[var(--border)] shadow-xl rounded-2xl"):
                with ui.tabs().classes("w-full") as tabs:
                    tab_worker = ui.tab("Worker Login", icon="badge")
                    tab_admin = ui.tab("Admin Login", icon="admin_panel_settings")

                with ui.tab_panels(tabs, value=tab_worker).classes("w-full bg-transparent p-0 mt-4"):
                    # 1. WORKER PANEL
                    with ui.tab_panel(tab_worker).classes("p-0 flex flex-col gap-3"):
                        ui.label("Shop Floor Operator Sign In").classes("text-xs text-[var(--text-muted)] font-medium")
                        
                        email_input_w = ui.input("Company Email", value="elena@mechnova.com").props("outlined dense").classes("w-full")
                        pwd_input_w = ui.input("Password", value="worker123", password=True, password_toggle_button=True).props("outlined dense").classes("w-full")
                        error_label_w = ui.label("").classes("text-xs text-red-600 font-semibold hidden")

                        # Worker Mode Transition Modal Dialog
                        worker_modal = ui.dialog().props("persistent backdrop-filter='blur(8px)'")
                        with worker_modal:
                            with ui.card().classes("p-6 glass-panel worker-mode-hud rounded-2xl w-96 relative overflow-hidden text-center flex flex-col items-center gap-3"):
                                ui.element("div").classes("scanline-effect")
                                with ui.element("div").classes("w-16 h-16 rounded-full bg-[var(--accent-50)] border-2 border-[var(--accent-600)] flex items-center justify-center relative shadow-lg"):
                                    ui.icon("settings", size="36px").classes("text-[var(--accent-600)] spindle-spin")
                                    ui.icon("engineering", size="20px").classes("text-[var(--accent-900)] absolute")
                                
                                ui.label("SWITCHING TO WORKER MODE").classes("text-xs font-mono font-bold tracking-widest text-[var(--accent-600)] uppercase")
                                modal_worker_name = ui.label("Authenticating Operator...").classes("text-lg font-black text-[var(--accent-900)]")
                                
                                with ui.column().classes("w-full gap-1 text-[11px] font-mono text-[var(--text-muted)] text-left bg-[var(--surface-alt)] p-2.5 rounded-lg border border-[var(--border)]"):
                                    step1_lbl = ui.label("⏳ Verifying Company Email...")
                                    step2_lbl = ui.label("⏳ Authorizing Spindle & Tool Crib...")
                                    step3_lbl = ui.label("⏳ Calibrating 3D CAD Engine...")

                                modal_progress = ui.linear_progress(value=0.1, color="primary", size="6px").classes("w-full rounded-full")
                                
                                with ui.badge(color="positive").classes("text-xs font-mono font-bold px-3 py-1 shadow-sm"):
                                    ui.label("⚡ WORKER MODE ACTIVATED")

                        async def handle_worker_login():
                            error_label_w.classes(remove="block", add="hidden")
                            try:
                                btn_w.props("loading")
                                res = await api.login(str(email_input_w.value or ""), str(pwd_input_w.value or ""), role_tab="worker")
                                login_user(res["access_token"], res["user"])
                                
                                # Launch Worker Mode Transition Animation
                                worker_name = res['user'].get('name', 'Operator')
                                modal_worker_name.set_text(f"Welcome, {worker_name}!")
                                worker_modal.open()
                                
                                step1_lbl.set_text(f"✓ Email Verified: {email_input_w.value}")
                                step1_lbl.classes(add="text-green-700 font-semibold")
                                modal_progress.set_value(0.35)
                                await asyncio.sleep(0.4)
                                
                                step2_lbl.set_text("✓ Tool Crib & CNC Telemetry: CONNECTED")
                                step2_lbl.classes(add="text-green-700 font-semibold")
                                modal_progress.set_value(0.70)
                                await asyncio.sleep(0.4)
                                
                                step3_lbl.set_text("✓ Autonomous CAD Console: READY")
                                step3_lbl.classes(add="text-green-700 font-semibold")
                                modal_progress.set_value(1.0)
                                await asyncio.sleep(0.5)
                                
                                worker_modal.close()
                                ui.navigate.to("/worker")
                            except Exception as e:
                                error_label_w.set_text(str(e))
                                error_label_w.classes(remove="hidden", add="block")
                            finally:
                                btn_w.props(remove="loading")

                        btn_w = ui.button("Sign In as Worker", on_click=handle_worker_login).classes("w-full btn-accent mt-2 py-2.5")

                    # 2. ADMIN PANEL
                    with ui.tab_panel(tab_admin).classes("p-0 flex flex-col gap-3"):
                        ui.label("Shop Administrator Sign In").classes("text-xs text-[var(--text-muted)] font-medium")
                        
                        email_input_a = ui.input("Admin Email", value="admin@mechnova.com").props("outlined dense").classes("w-full")
                        pwd_input_a = ui.input("Password", value="admin123", password=True, password_toggle_button=True).props("outlined dense").classes("w-full")
                        error_label_a = ui.label("").classes("text-xs text-red-600 font-semibold hidden")

                        async def handle_admin_login():
                            error_label_a.classes(remove="block", add="hidden")
                            try:
                                btn_a.props("loading")
                                res = await api.login(str(email_input_a.value or ""), str(pwd_input_a.value or ""), role_tab="admin")
                                login_user(res["access_token"], res["user"])
                                ui.notify(f"Welcome, Administrator {res['user']['name']}!", type="positive")
                                ui.navigate.to("/admin")
                            except Exception as e:
                                error_label_a.set_text(str(e))
                                error_label_a.classes(remove="hidden", add="block")
                            finally:
                                btn_a.props(remove="loading")

                        btn_a = ui.button("Sign In as Admin", on_click=handle_admin_login).classes("w-full btn-accent mt-2 py-2.5")

                # Demo Credentials Legend
                ui.separator().classes("my-3")
                with ui.expansion("Demo Accounts (Click to inspect)", icon="info").classes("w-full text-xs text-[var(--text-muted)]"):
                    ui.markdown("""
                    **Admin**: `admin@mechnova.com` / `admin123`  
                    **Worker**: `elena@mechnova.com` / `worker123`  
                    *Role tab verification is strictly enforced.*
                    """)
