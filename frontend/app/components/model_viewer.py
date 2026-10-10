from nicegui import ui
import uuid
import json
from typing import Optional, Dict, Any


def render_model_viewer(
    mesh_url: str = "/meshes/default.stl",
    container_height: str = "440px",
    element_id: Optional[str] = None,
    features_data: Optional[Dict[str, Any]] = None,
    initial_mode: str = "critical"
):
    """
    Precision 3D CAD/CNC Viewer powered by Three.js & STLLoader.
    Supports 360-degree orbit, Casual / Edges / Critical modes,
    and automatic CNC hole/pocket feature visualization with ID badges.
    """
    cid = element_id or f"viewer3d_{uuid.uuid4().hex[:8]}"

    with ui.column().classes("w-full gap-2"):
        # Top Toolbar
        with ui.row().classes("items-center justify-between w-full px-3 py-1.5 glass-panel rounded-xl text-xs flex-wrap gap-2 border border-[var(--border)]"):
            # Modes
            with ui.row().classes("items-center gap-1 bg-[var(--surface-alt)] p-1 rounded-lg border border-[var(--border)]"):
                ui.label("Mode:").classes("text-[11px] font-bold text-[var(--text-muted)] px-1")
                ui.button("Casual", on_click=lambda: ui.run_javascript(f"if(window['{cid}']) window['{cid}'].setMode('casual');")).props("flat dense size=sm").classes("text-xs font-semibold text-[var(--text)] hover:text-[var(--accent)]")
                ui.button("Edges", on_click=lambda: ui.run_javascript(f"if(window['{cid}']) window['{cid}'].setMode('edges');")).props("flat dense size=sm").classes("text-xs font-semibold text-[var(--text)] hover:text-[var(--accent)]")
                ui.button("Critical", on_click=lambda: ui.run_javascript(f"if(window['{cid}']) window['{cid}'].setMode('critical');")).props("flat dense size=sm").classes("text-xs font-semibold text-[var(--text)] hover:text-[var(--accent)]")

            # Camera Views
            with ui.row().classes("gap-1 items-center"):
                ui.button("Iso", on_click=lambda: ui.run_javascript(f"if(window['{cid}']) window['{cid}'].setView('iso');")).props("flat dense size=sm").classes("text-xs text-[var(--text-muted)]")
                ui.button("Top", on_click=lambda: ui.run_javascript(f"if(window['{cid}']) window['{cid}'].setView('top');")).props("flat dense size=sm").classes("text-xs text-[var(--text-muted)]")
                ui.button("Front", on_click=lambda: ui.run_javascript(f"if(window['{cid}']) window['{cid}'].setView('front');")).props("flat dense size=sm").classes("text-xs text-[var(--text-muted)]")
                ui.button("Fit", icon="fit_screen", on_click=lambda: ui.run_javascript(f"if(window['{cid}']) window['{cid}'].fit();")).props("flat dense size=sm").classes("text-xs text-[var(--text-muted)]")

        # 3D canvas container
        with ui.element("div").classes("w-full rounded-2xl overflow-hidden border border-[var(--border)] relative bg-[#1b2233] shadow-inner").style(f"height: {container_height};").props(f'id="{cid}"'):
            # Loading skeleton overlay
            with ui.element("div").props(f'id="{cid}_skeleton"').classes("absolute inset-0 flex flex-col items-center justify-center bg-[#1b2233]/90 backdrop-blur-sm z-30 transition-opacity duration-300 gap-3"):
                ui.spinner(size="36px", color="primary")
                ui.label("Rendering 3D CAD Geometry...").classes("text-xs font-mono font-bold text-slate-300 tracking-wide")

            # Critical legend overlay
            with ui.card().props(f'id="{cid}_critical_legend"').classes("absolute bottom-3 left-3 p-2 bg-[#111827]/90 border border-slate-700 rounded-lg text-[10px] text-white flex-col gap-1 shadow-lg z-10 pointer-events-none"):
                with ui.row().classes("items-center gap-1.5"):
                    ui.element("span").classes("w-2.5 h-2.5 rounded-full bg-[#ff3b3b]")
                    ui.label("Through Holes (Red)")
                with ui.row().classes("items-center gap-1.5"):
                    ui.element("span").classes("w-2.5 h-2.5 rounded-full bg-[#ff9f1c]")
                    ui.label("Blind Holes (Orange)")
                with ui.row().classes("items-center gap-1.5"):
                    ui.element("span").classes("w-2.5 h-2.5 rounded-full bg-[#22c55e]")
                    ui.label("Pockets (Green)")
                with ui.row().classes("items-center gap-1.5"):
                    ui.element("span").classes("w-2.5 h-2.5 rounded-full bg-[#3b82f6]")
                    ui.label("Slots (Blue)")
                with ui.row().classes("items-center gap-1.5"):
                    ui.element("span").classes("w-2.5 h-2.5 rounded-full bg-[#a855f7]")
                    ui.label("Windows (Purple)")

            # Active Mode Badge
            with ui.badge(color="primary").props(f'id="{cid}_badge"').classes("absolute top-3 right-3 text-[10px] font-mono font-bold shadow-md z-10 opacity-90"):
                ui.label(f"{initial_mode.capitalize()} Mode")

    feat_json = json.dumps(features_data or {})

    js_code = f"""
    (function() {{
        function initViewer() {{
            const container = document.getElementById('{cid}');
            if (!container) {{
                requestAnimationFrame(initViewer);
                return;
            }}
            if (typeof THREE === 'undefined' || typeof THREE.OrbitControls === 'undefined' || typeof THREE.STLLoader === 'undefined') {{
                setTimeout(initViewer, 30);
                return;
            }}

            // Safety timeout to dismiss skeleton if STL network load is slow
            setTimeout(function() {{
                const sk = document.getElementById('{cid}_skeleton');
                if (sk) {{ sk.style.opacity = '0'; setTimeout(function() {{ if (sk.parentNode) sk.remove(); }}, 300); }}
            }}, 20000);

            class ModelViewer {{
                constructor(container) {{
                    this.el = container;
                    this.scene = new THREE.Scene();
                    this.scene.background = new THREE.Color(0x182030); // Deep slate studio background
                    this.camera = new THREE.PerspectiveCamera(45, (container.clientWidth || 300) / (container.clientHeight || 440), 0.1, 10000);
                    
                    this.renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true, alpha: false }});
                    this.renderer.setPixelRatio(window.devicePixelRatio || 1);
                    this.renderer.domElement.style.display = 'block';
                    this.renderer.domElement.style.position = 'absolute';
                    this.renderer.domElement.style.top = '0';
                    this.renderer.domElement.style.left = '0';
                    this.renderer.domElement.style.width = '100%';
                    this.renderer.domElement.style.height = '100%';
                    container.appendChild(this.renderer.domElement);

                    this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
                    this.controls.enableDamping = true;
                    this.controls.dampingFactor = 0.05;
                    this.controls.minPolarAngle = 0;
                    this.controls.maxPolarAngle = Math.PI; // Full 360 degree rotation

                    // High-Visibility Engineering Lighting Setup
                    // 1. Ambient Light - guarantees all faces, pockets, and holes are never black
                    this.ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
                    this.scene.add(this.ambientLight);

                    // 2. Camera Headlight - always illuminates facing surfaces regardless of orbit angle
                    this.headlight = new THREE.DirectionalLight(0xffffff, 0.85);
                    this.headlight.position.set(0, 0, 1);
                    this.camera.add(this.headlight);
                    this.scene.add(this.camera);

                    // 3. Top-front directional key light
                    const keyLight = new THREE.DirectionalLight(0xffffff, 0.65);
                    keyLight.position.set(300, 400, 500);
                    this.scene.add(keyLight);

                    // 4. Back-fill directional light
                    const fillLight = new THREE.DirectionalLight(0x94a3b8, 0.45);
                    fillLight.position.set(-300, -200, -300);
                    this.scene.add(fillLight);

                    // Z-up Ground Grid
                    this.grid = new THREE.GridHelper(400, 40, 0x3b4a6b, 0x242e44);
                    this.grid.rotation.x = Math.PI / 2;
                    this.scene.add(this.grid);

                    // Main root group that holds both mesh and markers
                    this.rootGroup = new THREE.Group();
                    this.scene.add(this.rootGroup);

                    this.meshGroup = new THREE.Group();
                    this.rootGroup.add(this.meshGroup);

                    this.markersGroup = new THREE.Group();
                    this.rootGroup.add(this.markersGroup);

                    this.mode = '{initial_mode}';
                    this.resize();
                    new ResizeObserver(() => this.resize()).observe(container);

                    const loop = () => {{
                        requestAnimationFrame(loop);
                        if (this.controls) this.controls.update();
                        if (this.headlight && this.camera) {{
                            this.headlight.position.copy(this.camera.position);
                        }}
                        this.renderer.render(this.scene, this.camera);
                    }};
                    loop();
                }}

                resize() {{
                    const w = this.el.clientWidth || 300;
                    const h = this.el.clientHeight || 440;
                    this.renderer.setSize(w, h);
                    this.camera.aspect = w / h;
                    this.camera.updateProjectionMatrix();
                }}

                createBadgeSprite(text, bgColor) {{
                    const canvas = document.createElement('canvas');
                    canvas.width = 128;
                    canvas.height = 64;
                    const ctx = canvas.getContext('2d');

                    ctx.fillStyle = bgColor || '#ff3b3b';
                    ctx.beginPath();
                    ctx.roundRect(8, 8, 112, 48, 12);
                    ctx.fill();
                    ctx.strokeStyle = '#ffffff';
                    ctx.lineWidth = 3;
                    ctx.stroke();

                    ctx.fillStyle = '#ffffff';
                    ctx.font = 'bold 28px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(text, 64, 32);

                    const texture = new THREE.CanvasTexture(canvas);
                    const mat = new THREE.SpriteMaterial({{ map: texture, depthTest: false }});
                    const sprite = new THREE.Sprite(mat);
                    sprite.scale.set(12, 6, 1);
                    return sprite;
                }}

                async load(url, features) {{
                    const t0 = performance.now();
                    const skeleton = document.getElementById('{cid}_skeleton');
                    try {{
                        window.__mechnova_geo_cache = window.__mechnova_geo_cache || {{}};
                        let geo;
                        if (window.__mechnova_geo_cache[url]) {{
                            geo = window.__mechnova_geo_cache[url].clone();
                            console.log('[3D Viewer] Loaded from cache in ' + (performance.now() - t0).toFixed(1) + 'ms: ' + url);
                        }} else {{
                            const loader = new THREE.STLLoader();
                            geo = await loader.loadAsync(url);
                            geo.computeVertexNormals();
                            window.__mechnova_geo_cache[url] = geo;
                            console.log('[3D Viewer] Fetched & parsed in ' + (performance.now() - t0).toFixed(1) + 'ms: ' + url);
                        }}

                        this.meshGroup.clear();
                        this.markersGroup.clear();

                        // Phong Material with DoubleSide & Facet Shading for clear, crisp CAD appearance
                        this.mesh = new THREE.Mesh(
                            geo,
                            new THREE.MeshPhongMaterial({{
                                color: 0x93c5fd, // Clear anodized aluminum blue
                                specular: 0x475569,
                                shininess: 35,
                                flatShading: true,
                                side: THREE.DoubleSide
                            }})
                        );

                        this.edges = new THREE.LineSegments(
                            new THREE.EdgesGeometry(geo, 25),
                            new THREE.LineBasicMaterial({{ color: 0x00f0ff, linewidth: 2 }})
                        );
                        this.edges.visible = (this.mode !== 'casual');

                        this.meshGroup.add(this.mesh, this.edges);

                        // Compute bounding box of geometry to center root group at (0, 0, 0)
                        geo.computeBoundingBox();
                        const bbox = geo.boundingBox;
                        const center = new THREE.Vector3();
                        bbox.getCenter(center);
                        this.rootGroup.position.set(-center.x, -center.y, -center.z);
                        this.rootGroup.updateMatrixWorld(true);

                        this.geo = geo;
                        this.features = features || {{}};
                        this.setMode(this.mode || 'critical');
                        this.fit();

                        // Hide skeleton
                        if (skeleton) {{
                            skeleton.style.opacity = '0';
                            setTimeout(() => {{ if (skeleton.parentNode) skeleton.remove(); }}, 300);
                        }}
                    }} catch(err) {{
                        console.error('Model load error:', err);
                        if (skeleton) skeleton.remove();
                    }}
                }}

                setMode(m) {{
                    this.mode = m;
                    const badge = document.getElementById('{cid}_badge');
                    const legend = document.getElementById('{cid}_critical_legend');

                    if (badge) badge.innerText = (m.charAt(0).toUpperCase() + m.slice(1)) + ' Mode';
                    if (legend) {{
                        if (m === 'critical') legend.classList.remove('hidden');
                        else legend.classList.add('hidden');
                    }}

                    if (this.edges) this.edges.visible = (m !== 'casual');
                    this.markersGroup.clear();

                    if (this.mesh) {{
                        const hasFeatures = this.features && this.features.features && this.features.features.length > 0;
                        if (m === 'casual') {{
                            this.mesh.material.color.set(0x60a5fa); // Crisp CAD Blue
                            this.mesh.material.transparent = false;
                            this.mesh.material.opacity = 1.0;
                        }} else if (m === 'edges') {{
                            this.mesh.material.color.set(0x94a3b8); // Solid precision metal grey
                            this.mesh.material.transparent = false;
                            this.mesh.material.opacity = 1.0;
                        }} else {{
                            // critical mode
                            this.mesh.material.color.set(hasFeatures ? 0x94a3b8 : 0x93c5fd);
                            this.mesh.material.transparent = hasFeatures;
                            this.mesh.material.opacity = hasFeatures ? 0.70 : 1.0;
                        }}
                        this.mesh.material.needsUpdate = true;
                    }}

                    if (m === 'critical' && this.features) {{
                        this.showFeatures();
                    }}
                }}

            showFeatures() {{
                if (!this.features) return;
                const feats = this.features.features || [];
                const colorMap = {{
                    'hole': 0xff3b3b,        // Red
                    'blind_hole': 0xff9f1c,  // Orange
                    'pocket': 0x22c55e,      // Green
                    'slot': 0x3b82f6,        // Blue
                    'window': 0xa855f7       // Purple
                }};
                const badgeBgMap = {{
                    'hole': '#ff3b3b',
                    'blind_hole': '#ff9f1c',
                    'pocket': '#22c55e',
                    'slot': '#3b82f6',
                    'window': '#a855f7'
                }};

                for (const f of feats) {{
                    if (f.enabled === false) continue;
                    const kind = f.kind || 'hole';
                    const col = colorMap[kind] || 0xff3b3b;
                    const axis = f.axis || [0, 0, 1];
                    const ax = axis.findIndex(v => v !== 0);
                    const sign = ax >= 0 ? axis[ax] : 1;
                    const others = [0, 1, 2].filter(a => a !== ax);
                    
                    const depth = f.depth || 10;
                    const center = [...(f.center || [0, 0, 0])];
                    // material lies below the entry surface: center[ax] -= sign * depth / 2
                    if (ax >= 0) {{
                        center[ax] = center[ax] - sign * depth / 2.0;
                    }}

                    let markerMesh = null;
                    if (kind === 'hole' || kind === 'blind_hole') {{
                        const dia = f.diameter || (f.size ? f.size[0] : 10);
                        const radius = dia / 2.0;
                        const geo = new THREE.CylinderGeometry(radius, radius, depth, 32);
                        markerMesh = new THREE.Mesh(
                            geo,
                            new THREE.MeshBasicMaterial({{
                                color: col,
                                wireframe: true,
                                transparent: true,
                                opacity: 0.95
                            }})
                        );
                        // Rotate cylinder from Y-axis to tool approach axis
                        const normAxis = new THREE.Vector3(...axis).normalize();
                        markerMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normAxis);
                    }} else {{
                        // Box for pocket, slot, window
                        const dims = [10, 10, 10];
                        if (f.size && f.size.length >= 2 && others.length >= 2) {{
                            dims[others[0]] = f.size[0];
                            dims[others[1]] = f.size[1];
                            dims[ax] = depth;
                        }}
                        const geo = new THREE.BoxGeometry(dims[0], dims[1], dims[2]);
                        markerMesh = new THREE.Mesh(
                            geo,
                            new THREE.MeshBasicMaterial({{
                                color: col,
                                transparent: true,
                                opacity: 0.70,
                                wireframe: (kind === 'slot')
                            }})
                        );
                    }}

                    if (markerMesh) {{
                        markerMesh.position.set(center[0], center[1], center[2]);
                        this.markersGroup.add(markerMesh);

                        // Add ID sprite badge
                        const sprite = this.createBadgeSprite(f.id || 'F', badgeBgMap[kind]);
                        sprite.position.set(center[0], center[1], center[2] + (ax === 2 ? sign * depth / 2 + 5 : 5));
                        this.markersGroup.add(sprite);
                    }}
                }}
            }}

            setView(v) {{
                const r = this.fitRadius || 150;
                const t = this.controls.target;
                const dirs = {{
                    iso: [1, -1, 0.9],
                    top: [0, 0.001, 1],
                    front: [0, -1, 0]
                }};
                const dir = dirs[v] || dirs.iso;
                const d = new THREE.Vector3(...dir).normalize().multiplyScalar(r * 2.2);
                this.camera.up.set(0, 0, 1);
                this.camera.position.copy(t).add(d);
                this.controls.update();
            }}

            fit() {{
                this.rootGroup.updateMatrixWorld(true);
                const b = new THREE.Box3().setFromObject(this.rootGroup);
                const s = b.getSize(new THREE.Vector3());
                const c = b.getCenter(new THREE.Vector3());
                this.fitRadius = Math.max(s.x, s.y, s.z, 20);
                this.controls.target.copy(c);
                this.setView('iso');
            }}
        }}

        const viewer = new ModelViewer(container);
        window['{cid}'] = viewer;

        if ('{mesh_url}') {{
            viewer.load('{mesh_url}', {feat_json});
        }}
    }}
        initViewer();
    }})();
    """
    ui.add_body_html(f"<script>{js_code}</script>")
