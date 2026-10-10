from nicegui import ui, app

def register_overview_page():
    @ui.page("/overview")
    def overview_page():
        ui.add_head_html("""
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Orbitron:wght@600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
            <style>
                html { scroll-behavior: smooth; }
                .font-orbitron { font-family: 'Orbitron', sans-serif; }
                .font-space { font-family: 'Space Grotesk', sans-serif; }
                .text-glow-title { text-shadow: 0 0 25px rgba(56, 189, 248, 0.5), 0 0 50px rgba(14, 165, 233, 0.3); }
                .glass-panel {
                    background: rgba(10, 18, 42, 0.72);
                    backdrop-filter: blur(14px);
                    -webkit-backdrop-filter: blur(14px);
                    border: 1px solid rgba(56, 189, 248, 0.15);
                }
                .glass-card {
                    background: rgba(13, 24, 56, 0.65);
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    border: 1px solid rgba(56, 189, 248, 0.12);
                    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                }
                .glass-card:hover {
                    border-color: rgba(56, 189, 248, 0.4);
                    transform: translateY(-3px);
                    box-shadow: 0 12px 30px -10px rgba(14, 165, 233, 0.25);
                }
                @media (prefers-reduced-motion: reduce) {
                    .bg-video-el { display: none !important; }
                }
            </style>
        """)

        # Looping Background Video
        ui.html("""
            <div class="fixed inset-0 w-full h-full overflow-hidden pointer-events-none -z-10 bg-[#040817]">
                <img src="/static/bg/overview_poster.png" class="absolute inset-0 w-full h-full object-cover opacity-70" alt="" aria-hidden="true">
                <video autoplay muted loop playsinline preload="auto" poster="/static/bg/overview_poster.png" class="bg-video-el absolute inset-0 w-full h-full object-cover" aria-hidden="true">
                    <source src="/static/bg/overview.webm" type="video/webm">
                    <source src="/static/bg/overview.mp4" type="video/mp4">
                </video>
                <div class="absolute inset-0 bg-gradient-to-b from-[#040817]/90 via-[#07132e]/80 to-[#040817]/95" aria-hidden="true"></div>
            </div>
        """)

        # Sticky Navigation Bar
        with ui.element("nav").classes("sticky top-0 z-50 w-full glass-panel border-b border-sky-500/20 px-6 py-3.5"):
            with ui.row().classes("max-w-7xl mx-auto items-center justify-between w-full"):
                with ui.row().classes("items-center gap-3 cursor-pointer").on("click", lambda: ui.navigate.to("/")):
                    with ui.element("div").classes("w-9 h-9 rounded-xl bg-sky-500/15 border border-sky-500/40 flex items-center justify-center font-orbitron font-black text-sky-400 text-lg shadow-lg shadow-sky-500/20"):
                        ui.label("M")
                    with ui.column().classes("gap-0"):
                        ui.label("MECHNOVA").classes("font-orbitron font-black text-white text-lg tracking-wider leading-none")
                        ui.label("CAD-to-CNC Autonomous Suite").classes("text-[10px] font-mono text-sky-400 uppercase tracking-widest leading-tight")

                with ui.row().classes("hidden md:flex items-center gap-7 text-xs font-mono font-medium tracking-wider text-slate-300"):
                    ui.link("SYSTEM", "#what-is").classes("hover:text-sky-400 transition-colors no-underline")
                    ui.link("COMPARISON", "#why-mechnova").classes("hover:text-sky-400 transition-colors no-underline")
                    ui.link("BENEFITS", "#benefits").classes("hover:text-sky-400 transition-colors no-underline")
                    ui.link("PERSONAS", "#personas").classes("hover:text-sky-400 transition-colors no-underline")
                    ui.link("PIPELINE", "#how-it-works").classes("hover:text-sky-400 transition-colors no-underline")

                with ui.row().classes("items-center gap-3"):
                    ui.button("LAUNCH APP", on_click=lambda: ui.navigate.to("/login")).classes(
                        "btn-primary text-xs sm:text-sm font-bold py-2.5 px-6 rounded-xl shadow-lg shadow-sky-500/30 hover:scale-105 transition-all"
                    )

        # Page Body Container
        with ui.column().classes("w-full max-w-7xl mx-auto px-6 py-12 gap-20 text-slate-100 z-10 relative"):

            # ---------------- HERO BANNER ----------------
            with ui.column().classes("w-full items-center text-center py-10 gap-6"):
                with ui.row().classes("items-center gap-2 px-4 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 text-xs font-mono"):
                    ui.icon("precision_manufacturing", size="16px")
                    ui.label("NEXT-GEN INDUSTRIAL CNC INTELLIGENCE")

                ui.html("""
                    <h1 class="font-orbitron font-black text-3xl sm:text-5xl lg:text-6xl text-white tracking-wide text-glow-title leading-tight max-w-4xl">
                        Autonomous CAD-to-CNC<br/>
                        <span class="text-sky-400">Zero-Latency Manufacturing</span>
                    </h1>
                """)

                ui.label(
                    "Transform 3D engineering models into fully analyzed, tooling-assigned, "
                    "and shop-ready CNC machine jobs with comprehensive DFM guidance."
                ).classes("font-space text-base sm:text-lg text-slate-300 max-w-2xl leading-relaxed")

                with ui.row().classes("gap-4 pt-2 items-center flex-wrap justify-center"):
                    ui.button("LAUNCH APP", on_click=lambda: ui.navigate.to("/login")).classes(
                        "btn-primary text-sm sm:text-base font-bold py-3 px-8 rounded-xl shadow-xl shadow-sky-500/30 hover:scale-105 transition-all"
                    )
                    ui.button("Replay Intro", on_click=lambda: ui.navigate.to("/")).props("outline icon=replay").classes(
                        "text-xs sm:text-sm font-semibold text-slate-300 py-3 px-6 rounded-xl border border-slate-700 hover:border-sky-400/60 hover:bg-slate-800/40 transition-all"
                    )

            # ---------------- SECTION 1: WHAT IS MECHNOVA? ----------------
            with ui.column().classes("w-full gap-6 pt-6").props('id="what-is"'):
                with ui.row().classes("items-center gap-2 text-sky-400 text-xs font-mono uppercase tracking-widest"):
                    ui.icon("layers", size="18px")
                    ui.label("01 · PLATFORM ARCHITECTURE")
                ui.label("What is Mechnova?").classes("font-orbitron font-extrabold text-2xl sm:text-3xl text-white")

                with ui.element("div").classes("glass-card p-6 sm:p-8 rounded-2xl w-full border-sky-500/20"):
                    ui.label(
                        "Mechnova bridges the historical disconnect between 3D mechanical CAD design and physical CNC shop floor execution. "
                        "Instead of relying on laborious manual CAM toolpathing and delayed manufacturability reviews, Mechnova autonomously ingests "
                        "STEP and STL solids, parses volumetric and geometric topologies, and surfaces actionable manufacturing intelligence in seconds."
                    ).classes("text-sm sm:text-base text-slate-300 leading-relaxed mb-4")

                    ui.label(
                        "From detecting complex blind pockets and small corner radii to automatically matching your crib's standard cutting tools "
                        "and calculating feeds, speeds, and spindle RPM, Mechnova delivers complete, collision-free shop floor dispatch readiness."
                    ).classes("text-sm sm:text-base text-slate-400 leading-relaxed")

                # Live Algorithmic Benchmark Card
                with ui.element("div").classes("glass-card p-6 rounded-2xl w-full border-sky-500/25 bg-slate-950/60"):
                    with ui.row().classes("w-full justify-between items-center pb-4 border-b border-slate-800"):
                        with ui.row().classes("items-center gap-3"):
                            with ui.element("div").classes("w-3 h-3 rounded-full bg-emerald-400 animate-ping"):
                                pass
                            ui.label("BENCHMARK SOLID MODEL: AEROSPACE MOUNT BRACKET").classes("font-mono text-xs font-bold text-sky-400 tracking-wider")
                        with ui.row().classes("items-center gap-2"):
                            ui.label("SOURCE: bracket.stl (STEP/STL)").classes("text-[10px] font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800")
                            ui.label("100.0 × 60.0 × 20.0 mm").classes("text-[10px] font-mono text-emerald-400 bg-emerald-950/50 px-2.5 py-1 rounded-md border border-emerald-800/40")

                    with ui.grid(columns=4).classes("w-full gap-4 pt-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"):
                        # Column 1: Geometry
                        with ui.column().classes("gap-1.5 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80"):
                            ui.label("DETECTED TOPOLOGY").classes("text-[10px] font-mono text-slate-400 uppercase font-semibold")
                            ui.label("4× M6 C-Bore Holes").classes("text-xs font-bold text-white")
                            ui.label("1× Central Blind Pocket").classes("text-xs font-bold text-white")
                            ui.label("2× Clearance Step Faces").classes("text-xs font-bold text-white")
                            ui.label("Material: Aluminum 6061-T6").classes("text-[11px] text-sky-400 mt-1")

                        # Column 2: DFM Rules
                        with ui.column().classes("gap-1.5 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80"):
                            ui.label("DFM COMPLIANCE").classes("text-[10px] font-mono text-slate-400 uppercase font-semibold")
                            with ui.row().classes("items-center gap-1.5"):
                                ui.icon("check_circle", size="14px").classes("text-emerald-400")
                                ui.label("Wall Thickness: 3.2mm (≥1.2mm)").classes("text-xs text-slate-200")
                            with ui.row().classes("items-center gap-1.5"):
                                ui.icon("check_circle", size="14px").classes("text-emerald-400")
                                ui.label("Pocket Depth: 8mm (L/D = 0.67)").classes("text-xs text-slate-200")
                            with ui.row().classes("items-center gap-1.5"):
                                ui.icon("check_circle", size="14px").classes("text-emerald-400")
                                ui.label("Corner Radius: 3mm (R ≥ 1.5)").classes("text-xs text-slate-200")

                        # Column 3: Auto-Tooling
                        with ui.column().classes("gap-1.5 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80"):
                            ui.label("STANDARD TOOL ALLOCATION").classes("text-[10px] font-mono text-slate-400 uppercase font-semibold")
                            ui.label("T01: 12mm 3F Roughing End Mill").classes("text-xs text-slate-200")
                            ui.label("T02: 6mm 2F Finishing End Mill").classes("text-xs text-slate-200")
                            ui.label("T03: 6.5mm Carbide Jobber Drill").classes("text-xs text-slate-200")
                            ui.label("T04: 90° 4F Chamfer Mill").classes("text-xs text-slate-200")

                        # Column 4: Machine & Cycle Time
                        with ui.column().classes("gap-1.5 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80"):
                            ui.label("DISPATCH TELEMETRY").classes("text-[10px] font-mono text-slate-400 uppercase font-semibold")
                            ui.label("Machine: HAAS VF-2SS (3-Axis)").classes("text-xs font-bold text-sky-400")
                            ui.label("Spindle: 6,800 RPM | 1,450 mm/m").classes("text-xs text-slate-200")
                            ui.label("Est. Cycle Time: 8m 42s").classes("text-xs font-bold text-emerald-400")
                            ui.button("Test This Part In App →", on_click=lambda: ui.navigate.to("/login")).classes(
                                "btn-primary text-[11px] font-bold py-1.5 px-3 mt-1 rounded-lg w-full"
                            )

            # ---------------- SECTION 2: WHY MECHNOVA? (COMPARISON) ----------------
            with ui.column().classes("w-full gap-6 pt-6").props('id="why-mechnova"'):
                with ui.row().classes("items-center gap-2 text-sky-400 text-xs font-mono uppercase tracking-widest"):
                    ui.icon("compare_arrows", size="18px")
                    ui.label("02 · SYSTEM ADVANTAGE")
                ui.label("Why Mechnova?").classes("font-orbitron font-extrabold text-2xl sm:text-3xl text-white")

                with ui.row().classes("w-full gap-6 items-stretch flex-wrap lg:flex-nowrap"):
                    # Conventional Workflow
                    with ui.column().classes("w-full lg:w-1/2 glass-card p-6 rounded-2xl border-rose-500/20 bg-rose-950/10"):
                        with ui.row().classes("items-center gap-2 text-rose-400 font-mono text-xs font-bold uppercase pb-2 border-b border-rose-500/20 w-full"):
                            ui.icon("cancel", size="18px")
                            ui.label("CONVENTIONAL WORKFLOW")
                        with ui.column().classes("gap-3 pt-3 text-xs sm:text-sm text-slate-400"):
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("close", size="16px").classes("text-rose-400 mt-0.5")
                                ui.label("Hours to days waiting on manual CAM toolpath programming.")
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("close", size="16px").classes("text-rose-400 mt-0.5")
                                ui.label("Late surprises on the CNC floor: deep pockets requiring non-existent long-reach tools.")
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("close", size="16px").classes("text-rose-400 mt-0.5")
                                ui.label("Scattered paper setup slips and unverified tool assignments causing scrap.")
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("close", size="16px").classes("text-rose-400 mt-0.5")
                                ui.label("No upfront stock sizing feedback leading to oversized billet stock waste.")

                    # Mechnova Autonomous Workflow
                    with ui.column().classes("w-full lg:w-1/2 glass-card p-6 rounded-2xl border-emerald-500/30 bg-emerald-950/15"):
                        with ui.row().classes("items-center gap-2 text-emerald-400 font-mono text-xs font-bold uppercase pb-2 border-b border-emerald-500/20 w-full"):
                            ui.icon("check_circle", size="18px")
                            ui.label("MECHNOVA AUTONOMOUS SUITE")
                        with ui.column().classes("gap-3 pt-3 text-xs sm:text-sm text-slate-200"):
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("done_all", size="16px").classes("text-emerald-400 mt-0.5")
                                ui.label("Instant feature detection and 3D geometric breakdown in under 15 seconds.")
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("done_all", size="16px").classes("text-emerald-400 mt-0.5")
                                ui.label("Proactive DFM feedback highlighting thin walls, deep cavities, and tight corner radii.")
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("done_all", size="16px").classes("text-emerald-400 mt-0.5")
                                ui.label("Automatic tool assignment matching exact operation requirements to inventory tools.")
                            with ui.row().classes("items-start gap-2"):
                                ui.icon("done_all", size="16px").classes("text-emerald-400 mt-0.5")
                                ui.label("Digital machine booking, live operator tracking, and comprehensive printable job slips.")

            # ---------------- SECTION 3: IMPACT & BENEFITS ----------------
            with ui.column().classes("w-full gap-6 pt-6").props('id="benefits"'):
                with ui.row().classes("items-center gap-2 text-sky-400 text-xs font-mono uppercase tracking-widest"):
                    ui.icon("auto_graph", size="18px")
                    ui.label("03 · PROVEN VALUE")
                ui.label("Impact & Operational Benefits").classes("font-orbitron font-extrabold text-2xl sm:text-3xl text-white")

                BENEFITS = [
                    {"icon": "verified", "title": "Fewer Failed Jobs", "desc": "Pre-machining DFM warnings identify unreachable radii, wall flex risks, and tool collision threats before raw metal is clamped into vices."},
                    {"icon": "speed", "title": "Shorter Cycle Times", "desc": "Physics-calibrated feeds, speeds, and high-efficiency clearing strategies eliminate unnecessary air-cutting and maximize material removal rates."},
                    {"icon": "recycling", "title": "Reduced Material Waste", "desc": "Automated billet and stock envelope optimization calculates minimal stock margins, slashing billet expenditure by up to 28%."},
                    {"icon": "build_circle", "title": "Tool-Life Tracking", "desc": "Intelligent tool selection balances cutting loads across end mills and ball noses, prolonging insert longevity and cutting downtime."},
                    {"icon": "precision_manufacturing", "title": "Digital Machine Dispatch", "desc": "Queue and assign jobs directly to 3-axis and 5-axis CNC machining centers with real-time operational availability checks."},
                    {"icon": "history_edu", "title": "Full Project History", "desc": "Centralized revision history, interactive 3D WebGL model archives, and instant re-generation of stamped job slips."},
                ]

                with ui.grid(columns=3).classes("w-full gap-5 grid-cols-1 md:grid-cols-2 lg:grid-cols-3"):
                    for b in BENEFITS:
                        with ui.element("div").classes("glass-card p-5 rounded-2xl flex flex-col gap-3"):
                            with ui.element("div").classes("w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400"):
                                ui.icon(b["icon"], size="20px")
                            ui.label(b["title"]).classes("font-space font-bold text-base text-white tracking-wide")
                            ui.label(b["desc"]).classes("text-xs text-slate-400 leading-relaxed")

            # ---------------- SECTION 4: WHO BENEFITS? ----------------
            with ui.column().classes("w-full gap-6 pt-6").props('id="personas"'):
                with ui.row().classes("items-center gap-2 text-sky-400 text-xs font-mono uppercase tracking-widest"):
                    ui.icon("groups", size="18px")
                    ui.label("04 · TARGET ROLES")
                ui.label("Who Benefits from Mechnova?").classes("font-orbitron font-extrabold text-2xl sm:text-3xl text-white")

                PERSONAS = [
                    {"role": "CNC Operators & Machinists", "icon": "engineering", "desc": "Clear setup slips, confirmed stock dimensions, zero tool ambiguity, and verified spindle speeds right at the machine console."},
                    {"role": "Shopfloor & Production Admins", "icon": "admin_panel_settings", "desc": "Live machine workload dashboards, worker shift tracking, automated queue scheduling, and maintenance logs."},
                    {"role": "Mechanical & Design Engineers", "icon": "architecture", "desc": "Instant manufacturability feedback during the CAD iteration phase before designs are released to procurement."},
                    {"role": "High-Mix Job Shops", "icon": "store", "desc": "Fast-track quoting and rapid setup turnaround for low-volume aerospace, automotive, and medical prototypes."},
                ]

                with ui.grid(columns=4).classes("w-full gap-5 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"):
                    for p in PERSONAS:
                        with ui.element("div").classes("glass-card p-5 rounded-2xl flex flex-col gap-3"):
                            with ui.element("div").classes("w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-400"):
                                ui.icon(p["icon"], size="20px")
                            ui.label(p["role"]).classes("font-space font-bold text-sm text-white tracking-wide")
                            ui.label(p["desc"]).classes("text-xs text-slate-400 leading-relaxed")

            # ---------------- SECTION 5: HOW IT WORKS (PIPELINE) ----------------
            with ui.column().classes("w-full gap-6 pt-6").props('id="how-it-works"'):
                with ui.row().classes("items-center gap-2 text-sky-400 text-xs font-mono uppercase tracking-widest"):
                    ui.icon("alt_route", size="18px")
                    ui.label("05 · EXECUTION PIPELINE")
                ui.label("How It Works: 5-Step Flow").classes("font-orbitron font-extrabold text-2xl sm:text-3xl text-white")

                STEPS = [
                    {"num": "01", "name": "CAD Upload", "detail": "Drop STEP or STL solid model with bounding stock parameters."},
                    {"num": "02", "name": "3D Inspection", "detail": "Full WebGL 3D solid viewer with orbit, zoom, and wireframe analysis."},
                    {"num": "03", "name": "Feature & DFM", "detail": "Instant detection of pockets, holes, slots, and wall thickness violations."},
                    {"num": "04", "name": "Tooling Match", "detail": "Auto-selection of flat end mills, ball mills, and drills from catalog."},
                    {"num": "05", "name": "Machine Request", "detail": "Queue dispatch to 3-axis/5-axis CNC centers with verified job slips."},
                ]

                with ui.grid(columns=5).classes("w-full gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5"):
                    for s in STEPS:
                        with ui.element("div").classes("glass-card p-4 rounded-xl flex flex-col gap-2 relative"):
                            with ui.row().classes("justify-between items-center w-full"):
                                ui.label(s["num"]).classes("font-orbitron font-black text-sky-400 text-xl")
                                ui.icon("arrow_forward", size="16px").classes("text-slate-600 hidden lg:block")
                            ui.label(s["name"]).classes("font-space font-bold text-sm text-white")
                            ui.label(s["detail"]).classes("text-[11px] text-slate-400 leading-normal")

            # ---------------- SECTION 6: FOOTER CTA CARD ----------------
            with ui.element("div").classes("w-full glass-card p-8 sm:p-12 rounded-3xl border-sky-500/30 text-center flex flex-col items-center gap-6 my-8 bg-gradient-to-b from-[#0a1535]/80 to-[#040817]/90"):
                with ui.element("div").classes("w-14 h-14 rounded-2xl bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400 text-2xl shadow-xl shadow-sky-500/20"):
                    ui.icon("rocket_launch", size="30px")
                
                ui.label("Ready to Accelerate Your CNC Machining?").classes("font-orbitron font-black text-2xl sm:text-4xl text-white")
                ui.label("Step directly into the MECHNOVA Autonomous Suite. Authenticate and process your first part in seconds.").classes("text-sm sm:text-base text-slate-300 max-w-xl")

                ui.button("LAUNCH APP", on_click=lambda: ui.navigate.to("/login")).classes(
                    "btn-primary text-base font-extrabold py-4 px-10 rounded-2xl shadow-2xl shadow-sky-500/40 tracking-wider hover:scale-105 transition-all"
                )

            # Footer credits
            with ui.row().classes("w-full justify-between items-center text-xs text-slate-500 font-mono py-6 border-t border-slate-800/60"):
                ui.label("MECHNOVA Autonomous CAD-to-CNC Suite")
                ui.label("ALL SYSTEMS OPERATIONAL · LOCAL HOST :8080")
