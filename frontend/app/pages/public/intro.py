from nicegui import ui, app
import asyncio

MECHNOVA_MEANINGS = [
    {"letter": "M", "title": "Model Analysis", "desc": "Automated volumetric & topological geometry extraction"},
    {"letter": "E", "title": "Engineering Geometry", "desc": "Prismatic feature decomposition & orientation planes"},
    {"letter": "C", "title": "CAD Feature Detection", "desc": "Instant recognition of holes, pockets, slots, and walls"},
    {"letter": "H", "title": "High-Precision Machining", "desc": "Micron-level feeds, speeds, and spindle RPM calculations"},
    {"letter": "N", "title": "Numerical Optimization", "desc": "Minimal air-time rapid moves and scallop height control"},
    {"letter": "O", "title": "Optimized Toolpaths", "desc": "Adaptive helical clearing & high-speed trochoidal passes"},
    {"letter": "V", "title": "Virtual CNC Simulation", "desc": "Collision-free G-code verification & machine kinematics"},
    {"letter": "A", "title": "Automated Manufacturing", "desc": "Zero-latency dispatch from digital CAD to CNC floor"},
]


def register_intro_page():
    @ui.page("/")
    def intro_page():
        ui.add_head_html("""
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Orbitron:wght@600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
            <style>
                .font-orbitron { font-family: 'Orbitron', sans-serif; }
                .font-space { font-family: 'Space Grotesk', sans-serif; }
                .text-glow-title { text-shadow: 0 0 25px rgba(56, 189, 248, 0.6), 0 0 50px rgba(14, 165, 233, 0.4); }
                .text-glow-cyan { text-shadow: 0 0 15px rgba(56, 189, 248, 0.85); }
                
                @keyframes riseUp {
                    0% { opacity: 0; transform: translateY(30px) scale(0.96); }
                    100% { opacity: 1; transform: translateY(0) scale(1); }
                }
                .animate-rise {
                    animation: riseUp 0.65s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                }
                @keyframes pulseGlow {
                    0%, 100% { box-shadow: 0 0 0 rgba(56,189,248,0); }
                    50% { box-shadow: 0 0 22px rgba(56,189,248,0.7); transform: scale(1.03); }
                }
                .pulse-highlight {
                    animation: pulseGlow 0.4s ease-in-out;
                }
                @media (prefers-reduced-motion: reduce) {
                    .bg-video-el { display: none !important; }
                }
            </style>
        """)

        # Full-Screen Looping Video Background
        ui.html("""
            <div class="fixed inset-0 w-full h-full overflow-hidden pointer-events-none -z-10 bg-[#050b1f]">
                <img src="/static/bg/intro_poster.png" class="absolute inset-0 w-full h-full object-cover opacity-80" alt="" aria-hidden="true">
                <video autoplay muted loop playsinline preload="auto" poster="/static/bg/intro_poster.png" class="bg-video-el absolute inset-0 w-full h-full object-cover" aria-hidden="true">
                    <source src="/static/bg/intro.webm" type="video/webm">
                    <source src="/static/bg/intro.mp4" type="video/mp4">
                </video>
                <div class="absolute inset-0 bg-gradient-to-b from-[#050b1f]/85 via-[#07132e]/75 to-[#050b1f]/90" aria-hidden="true"></div>
                <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,rgba(5,11,31,0.65)_100%)]" aria-hidden="true"></div>
            </div>
        """)

        with ui.column().classes("min-h-screen w-full justify-between p-6 sm:p-10 text-slate-100 relative z-10 max-w-7xl mx-auto"):
            # Header with badge and skip button
            with ui.row().classes("w-full justify-between items-center z-20"):
                with ui.row().classes("items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-950/40 border border-sky-800/50 backdrop-blur-md text-xs font-mono text-sky-400 uppercase tracking-widest"):
                    ui.icon("memory", size="16px").classes("text-sky-400 animate-pulse")
                    ui.label("AUTONOMOUS ENGINE · V2.4")

                ui.button("Skip intro →", on_click=lambda: ui.navigate.to("/overview")).props("flat dense").classes("text-xs sm:text-sm font-semibold text-slate-400 hover:text-white px-3.5 py-1.5 rounded-lg hover:bg-slate-800/40 border border-transparent hover:border-slate-700/60 transition-all")

            # Main Hero & 8-Meaning List Split
            with ui.row().classes("w-full my-auto py-8 sm:py-12 items-center justify-between gap-8 lg:gap-12 flex-wrap lg:flex-nowrap"):
                # Left Column: Brand Hero & Call-to-Action
                with ui.column().classes("w-full lg:w-5/12 gap-5 items-start"):
                    with ui.row().classes("items-center gap-2 px-3 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono"):
                        ui.icon("explore", size="14px")
                        ui.label("DIGITAL MACHINING SUITE")

                    with ui.column().classes("gap-1"):
                        ui.html("""
                            <h1 class="font-orbitron font-black text-4xl sm:text-6xl xl:text-7xl tracking-wider text-white text-glow-title leading-tight">
                                MECH<span class="text-sky-400">NOVA</span>
                            </h1>
                        """)
                        ui.label("CAD-to-CNC Autonomous Suite").classes("font-space text-lg sm:text-xl text-slate-300 font-medium tracking-wide")

                    ui.label(
                        "Bridge the gap between digital CAD design and physical 5-axis precision milling. "
                        "Autonomous feature recognition, cutting tool assignment, and ISO G-code generation in seconds."
                    ).classes("text-xs sm:text-sm text-slate-400 leading-relaxed max-w-md")

                    with ui.row().classes("pt-2 items-center gap-4"):
                        continue_btn = ui.button("Continue →", on_click=lambda: ui.navigate.to("/overview")).classes("btn-primary text-sm font-bold py-3 px-7 rounded-xl shadow-lg shadow-sky-500/25 tracking-wide hover:scale-105 transition-all")
                        auto_label = ui.label("").classes("text-xs text-slate-400 font-mono")

                # Right Column: The 8 Meaning Lines
                with ui.column().classes("w-full lg:w-7/12 gap-2.5 sm:gap-3"):
                    with ui.row().classes("w-full justify-between items-center text-xs font-mono font-semibold tracking-wider text-slate-400 uppercase mb-1"):
                        ui.label("Autonomous Pipeline Architecture")
                        counter_label = ui.label("0/8 Active").classes("text-sky-400 font-bold")

                    # Container for animated items
                    items_container = ui.column().classes("w-full gap-2")

            # Footer
            with ui.row().classes("w-full justify-between items-center text-xs text-slate-500 font-mono pt-4 border-t border-slate-800/50"):
                ui.label("MECHNOVA Autonomous Suite")
                ui.label("ISO 6983 G-CODE READY · 3-AXIS / 5-AXIS")

        # Background async task to reveal each meaning one-by-one
        async def run_reveal_sequence():
            await asyncio.sleep(0.3)
            cards = []
            for idx, item in enumerate(MECHNOVA_MEANINGS):
                counter_label.set_text(f"{idx + 1}/8 Active")
                with items_container:
                    card = ui.element("div").classes(
                        "w-full flex items-center justify-between px-4 py-2.5 rounded-xl border border-slate-800/80 "
                        "bg-slate-900/60 hover:bg-slate-900/80 backdrop-blur-md animate-rise transition-all"
                    )
                    with card:
                        with ui.row().classes("items-center gap-3.5"):
                            with ui.element("div").classes(
                                "w-8 h-8 rounded-lg flex items-center justify-center font-orbitron font-black text-lg "
                                "bg-sky-500/15 border border-sky-500/30 text-sky-400 text-glow-cyan"
                            ):
                                ui.label(item["letter"])
                            with ui.column().classes("gap-0"):
                                ui.label(item["title"]).classes("font-space text-sm sm:text-base font-semibold text-white tracking-wide leading-tight")
                                ui.label(item["desc"]).classes("text-[11px] sm:text-xs text-slate-400 hidden sm:inline-block leading-normal")
                        ui.label(f"0{idx + 1}").classes("text-[10px] font-mono text-slate-500 font-semibold px-2 py-0.5 rounded bg-slate-950/40")
                    cards.append(card)

                await asyncio.sleep(0.85)

            # Highlight pulse sequence M -> A once
            await asyncio.sleep(0.3)
            for card in cards:
                card.classes(add="pulse-highlight")
                await asyncio.sleep(0.16)
                card.classes(remove="pulse-highlight")

            # Show auto-navigating countdown
            auto_label.set_text("Auto-navigating to overview in 4s...")
            for i in range(4, 0, -1):
                auto_label.set_text(f"Auto-navigating to overview in {i}s...")
                await asyncio.sleep(1.0)
            ui.navigate.to("/overview")

        asyncio.create_task(run_reveal_sequence())
