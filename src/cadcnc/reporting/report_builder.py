"""Report builder: generates deterministic Markdown (report.md) and self-contained HTML (report.html)."""

from pathlib import Path
from typing import Optional, Any
from cadcnc.schemas.cad import ModelSummary
from cadcnc.schemas.features import FeaturesCollection
from cadcnc.schemas.analysis import ManufacturabilityReport
from cadcnc.schemas.optimization import ToolRecommendationsReport, MachiningPlan, ComparisonReport
from cadcnc.schemas.cam import ValidationReport
from cadcnc.schemas.run_log import RunLog

DISCLAIMER_TEXT = (
    "DISCLAIMER: This software is an automated manufacturing planning and optimization assistant, "
    "NOT a certified industrial CAM system. All cycle times, toolpaths, and feeds/speeds are simulation-based "
    "estimates. All G-code outputs are prototypes and must NEVER be run on a production machine without "
    "full kinematic simulation, tool clearance checks, and operator dry-run verification."
)

def to_str(val: Any) -> str:
    """Helper safely extracting string from either Enum or primitive string."""
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)

def build_markdown_report(
    summary: ModelSummary,
    features: FeaturesCollection,
    dfm: ManufacturabilityReport,
    recs: ToolRecommendationsReport,
    plan: MachiningPlan,
    comp: ComparisonReport,
    val: ValidationReport,
    run_log: RunLog,
    material_id: str,
    machine_name: str
) -> str:
    """Generates comprehensive, deterministic Markdown report."""
    md: list[str] = []

    md.append(f"# CAD-to-CNC Optimization Report: {summary.filename}")
    md.append("")
    md.append(f"> **Notice:** {DISCLAIMER_TEXT}")
    md.append("")

    # 1. Executive Summary
    md.append("## 1. Executive Summary & Optimization Highlights")
    md.append("")
    md.append(f"| Metric | Baseline Plan | Optimized Plan | Improvement / Savings |")
    md.append(f"| :--- | :--- | :--- | :--- |")
    md.append(f"| **Estimated Cycle Time** | {comp.baseline.total_estimated_cycle_time_s:.1f} s | {comp.optimized.total_estimated_cycle_time_s:.1f} s | **{comp.time_savings.percentage_difference:.1f}% reduction** ({comp.time_savings.absolute_difference:.1f} s saved) |")
    md.append(f"| **Rapid Travel Distance** | {comp.baseline.rapid_travel_distance_mm:.1f} mm | {comp.optimized.rapid_travel_distance_mm:.1f} mm | **{comp.rapid_distance_savings.percentage_difference:.1f}% reduction** ({comp.rapid_distance_savings.absolute_difference:.1f} mm saved) |")
    md.append(f"| **Automatic Tool Changes** | {comp.baseline.tool_changes_count} changes | {comp.optimized.tool_changes_count} changes | **{comp.tool_change_savings.absolute_difference} fewer changes** |")
    md.append(f"| **DFM Manufacturability Score** | — | **{dfm.overall_score:.1f} / 100.0** | Formula: `100 - 25*N_red - 5*N_yellow` |")
    md.append(f"| **Raw Stock Utilization** | — | **{comp.stock_utilization_percent:.1f}%** | Part Vol: {comp.part_volume_mm3:.1f} mm³ / Stock: {comp.stock_volume_mm3:.1f} mm³ |")
    md.append(f"| **G-Code Validation Status** | — | **{'PASSED (Exported)' if val.gcode_export_permitted else 'FAILED (Blocked)'}** | Travel & spindle bounds verified |")
    md.append("")

    # 2. CAD B-Rep Geometry Analysis
    md.append("## 2. CAD Model B-Rep Summary")
    md.append(f"- **Filename:** `{summary.filename}` ({summary.size_bytes} bytes)")
    md.append(f"- **Units:** `{summary.unit}`")
    md.append(f"- **Solids:** {summary.solids_count} | **Shells:** {summary.shells_count} | **Faces:** {summary.faces_count} | **Edges:** {summary.edges_count} | **Vertices:** {summary.vertices_count}")
    md.append(f"- **Bounding Box:** X [{summary.bounding_box.x_min:.2f}, {summary.bounding_box.x_max:.2f}] mm (Δ={summary.bounding_box.dx:.2f} mm), Y [{summary.bounding_box.y_min:.2f}, {summary.bounding_box.y_max:.2f}] mm (Δ={summary.bounding_box.dy:.2f} mm), Z [{summary.bounding_box.z_min:.2f}, {summary.bounding_box.z_max:.2f}] mm (Δ={summary.bounding_box.dz:.2f} mm)")
    md.append(f"- **Volume:** {summary.volume_mm3:.2f} mm³ | **Surface Area:** {summary.surface_area_mm2:.2f} mm²")
    md.append(f"- **Surface Types:** Planes: {summary.face_counts_by_surface_type.plane}, Cylinders: {summary.face_counts_by_surface_type.cylinder}, Cones: {summary.face_counts_by_surface_type.cone}, Spheres: {summary.face_counts_by_surface_type.sphere}, B-Splines: {summary.face_counts_by_surface_type.b_spline}")
    md.append(f"- **Timings:** Load: {summary.load_time_s:.4f} s | Analysis: {summary.analysis_time_s:.4f} s")
    md.append("")

    # 3. Manufacturing Feature Recognition
    md.append("## 3. Recognized Manufacturing Features")
    md.append(f"Detected **{len(features.holes)} holes**, **{len(features.pockets)} pockets**, **{len(features.slots)} slots**, **{len(features.internal_corners)} corners**, and **{len(features.thin_walls)} thin walls**.")
    md.append("")

    if features.holes:
        md.append("### Holes")
        md.append("| Feature ID | Subtype | Diameter (mm) | Depth (mm) | Axis [X,Y,Z] | Opening Position | Status | Confidence |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for h in features.holes:
            pos_str = f"({h.position.x:.1f}, {h.position.y:.1f}, {h.position.z:.1f})"
            axis_str = f"[{h.axis.x:.2f}, {h.axis.y:.2f}, {h.axis.z:.2f}]"
            md.append(f"| `{h.id}` | {to_str(h.type)} | {h.diameter_mm:.2f} | {h.depth_mm:.2f} | {axis_str} | {pos_str} | `{to_str(h.status)}` | {h.confidence:.2f} |")
        md.append("")

    if features.pockets:
        md.append("### Pockets")
        md.append("| Feature ID | Subtype | Length (mm) | Width (mm) | Depth (mm) | Islands | Status | Confidence |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for p in features.pockets:
            md.append(f"| `{p.id}` | {to_str(p.type)} | {p.length_mm:.2f} | {p.width_mm:.2f} | {p.depth_mm:.2f} | {p.islands_count} | `{to_str(p.status)}` | {p.confidence:.2f} |")
        md.append("")

    if features.slots:
        md.append("### Slots")
        md.append("| Feature ID | Subtype | Length (mm) | Width (mm) | Depth (mm) | Aspect Ratio | Status | Confidence |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for s in features.slots:
            md.append(f"| `{s.id}` | {to_str(s.type)} | {s.length_mm:.2f} | {s.width_mm:.2f} | {s.depth_mm:.2f} | {s.aspect_ratio:.2f} | `{to_str(s.status)}` | {s.confidence:.2f} |")
        md.append("")

    if features.internal_corners:
        md.append("### Internal Corners")
        md.append("| Corner ID | Wall Faces | Radius (mm) | Filleted? | Status |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in features.internal_corners:
            r_str = f"{c.radius_mm:.2f}" if c.radius_mm else "0.00 (Sharp)"
            is_fillet_str = "Yes" if c.type == "filleted" else "**No (Sharp)**"
            walls_str = ", ".join(c.wall_face_ids) if c.wall_face_ids else "-"
            md.append(f"| `{c.id}` | `{walls_str}` | {r_str} | {is_fillet_str} | `{to_str(c.status)}` |")
        md.append("")

    if features.thin_walls:
        md.append("### Thin Walls")
        md.append("| Wall ID | Faces | Thickness (mm) | Min Allowed (mm) | Status |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for w in features.thin_walls:
            f_pair = f"{w.face_id_1} <-> {w.face_id_2}"
            md.append(f"| `{w.id}` | `{f_pair}` | **{w.thickness_mm:.2f}** | {w.min_allowed_thickness_mm:.2f} | `{to_str(w.status)}` |")
        md.append("")

    # 4. Manufacturability (DFM)
    md.append("## 4. Manufacturability (DFM) Analysis")
    md.append(f"- **Overall Score:** **{dfm.overall_score:.1f} / 100.0**")
    md.append(f"- **Findings Breakdown:** {dfm.green_count} Green (Informational), {dfm.yellow_count} Yellow (Warnings), {dfm.red_count} Red (Blockers)")
    md.append(f"- **Scoring Formula:** `{dfm.score_formula}`")
    md.append("")
    md.append("| Severity | Category | Kind | Feature | Explanation | Resolution Recommendation |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for f in dfm.findings:
        feat_str = f"`{f.feature_id}`" if f.feature_id else "Global"
        md.append(f"| **{to_str(f.severity).upper()}** | {f.category} | `{to_str(f.kind)}` | {feat_str} | {f.explanation} | {f.how_to_resolve} |")
    md.append("")

    # 5. Tool Selection & Recommendations
    md.append("## 5. Tool Selection & Scoring")
    md.append(f"Configured Material: `{material_id}` | Machine: `{machine_name}`")
    md.append("")
    md.append("| Feature | Selected Tool | Score | Selection Checklist & Justification | Rejections Summary |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    for r in recs.recommendations:
        t_str = f"**`{r.selected_tool_id}`**" if r.selected_tool_id else "*None Available*"
        top_cand = r.ranked_candidates[0] if r.ranked_candidates else None
        score_str = f"{top_cand.score:.1f}" if top_cand else "0.0"
        reasons_str = "<br>".join(f"• {chk}" for chk in top_cand.check_reasons) if top_cand and top_cand.check_reasons else "No passes"
        rejs_str = f"{len(r.rejected_candidates)} tools rejected" if r.rejected_candidates else "None"
        md.append(f"| `{r.feature_id}` ({r.feature_type}) | {t_str} | {score_str} | {reasons_str} | {rejs_str} |")
    md.append("")

    # 6. Machining Sequence & CAM Operations
    md.append("## 6. Optimized Machining Sequence")
    md.append(f"Total Operations: {plan.optimized_plan.total_operations} | Setups: {plan.optimized_plan.total_setup_changes}")
    md.append("")
    md.append("| Step | Op ID | Type | Tool | RPM | Feed (mm/min) | Depth (mm) | Est. Cut Time | Est. Rapid Time |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    step = 1
    for setup in plan.optimized_plan.setups:
        for op in setup.operations:
            md.append(f"| {step} | `{op.id}` | {op.operation_type} | `{op.tool_id}` | {op.spindle_rpm:.0f} | {op.feed_mm_min:.0f} | {op.cutting_depth_mm:.1f} | {op.estimated_cut_time_s:.2f} s | {op.estimated_rapid_time_s:.2f} s |")
            step += 1
    md.append("")

    # 7. CAM Validation Gate
    md.append("## 7. Closed-Loop Validation Gate & G-Code Export")
    md.append(f"- **G-Code Export Permitted:** **{'YES' if val.gcode_export_permitted else 'NO (BLOCKED)'}**")
    if val.exported_gcode_files:
        md.append(f"- **Exported Program Files:** {', '.join(f'`{fn}`' for fn in val.exported_gcode_files)}")
    md.append("")
    md.append("| Gate Check | Status | Details |")
    md.append("| :--- | :--- | :--- |")
    for chk in val.checks:
        stat_badge = "**PASS**" if chk.passed else "**FAIL**"
        md.append(f"| {chk.name} | {stat_badge} | {chk.details} |")
    md.append("")

    # 8. Run Timings & Provenance
    md.append("## 8. Execution Log & Provenance")
    md.append(f"- **Total Monotonic Runtime:** {run_log.total_duration_s:.4f} seconds")
    md.append("- **Stage Timings:**")
    for st in run_log.stage_timings:
        md.append(f"  - `{st.stage_name}`: {st.duration_s:.4f} s")
    md.append("- **Core Libraries:**")
    for lib, ver in run_log.library_versions.items():
        md.append(f"  - `{lib}`: {ver}")
    md.append("")

    return "\n".join(md)

def build_html_report(
    summary: ModelSummary,
    features: FeaturesCollection,
    dfm: ManufacturabilityReport,
    recs: ToolRecommendationsReport,
    plan: MachiningPlan,
    comp: ComparisonReport,
    val: ValidationReport,
    run_log: RunLog,
    material_id: str,
    machine_name: str
) -> str:
    """Generates self-contained, beautifully styled HTML report."""
    score_color = "#10b981" if dfm.overall_score >= 80 else ("#f59e0b" if dfm.overall_score >= 50 else "#ef4444")
    val_status_badge = '<span class="badge pass">PASSED</span>' if val.gcode_export_permitted else '<span class="badge fail">BLOCKED</span>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CAD-CNC Optimization Report - {summary.filename}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0ea5e9;
      --accent: #6366f1;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      border-bottom: 2px solid var(--border);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }}
    h1 {{
      font-size: 2.2rem;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .disclaimer-banner {{
      background: rgba(245, 158, 11, 0.1);
      border-left: 4px solid var(--warning);
      padding: 1rem;
      border-radius: 4px;
      margin-top: 1rem;
      font-size: 0.88rem;
      color: #fde68a;
    }}
    .grid-cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2.5rem;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    .card-title {{
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
    }}
    .card-value {{
      font-size: 1.8rem;
      font-weight: 700;
      color: var(--primary);
    }}
    .card-sub {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }}
    section {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 2rem;
      margin-bottom: 2rem;
    }}
    h2 {{
      font-size: 1.4rem;
      color: var(--primary);
      margin-bottom: 1.25rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.5rem;
    }}
    h3 {{
      font-size: 1.1rem;
      color: var(--text);
      margin: 1.25rem 0 0.75rem 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      margin-bottom: 1.5rem;
      font-size: 0.9rem;
    }}
    th, td {{
      padding: 0.75rem 1rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      background: rgba(15, 23, 42, 0.6);
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
    }}
    tr:hover {{
      background: rgba(255, 255, 255, 0.02);
    }}
    .badge {{
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .badge.pass, .badge.green {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }}
    .badge.fail, .badge.red {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }}
    .badge.yellow {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706; }}
    code {{
      background: rgba(15, 23, 42, 0.8);
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85em;
      color: #38bdf8;
    }}
    @media print {{
      body {{ background: #fff; color: #000; padding: 0; }}
      .card, section {{ border: 1px solid #ccc; background: #fff; color: #000; box-shadow: none; }}
      th {{ background: #eee; color: #000; }}
      code {{ background: #f4f4f4; color: #000; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>CAD-to-CNC Optimization Engine</h1>
      <p style="color: var(--text-muted);">Model: <code>{summary.filename}</code> | Material: <code>{material_id}</code> | Machine: <code>{machine_name}</code></p>
      <div class="disclaimer-banner">
        <strong>SAFETY NOTICE:</strong> {DISCLAIMER_TEXT}
      </div>
    </header>

    <!-- Top KPI Cards -->
    <div class="grid-cards">
      <div class="card">
        <div class="card-title">Cycle Time Savings</div>
        <div class="card-value">{comp.time_savings.percentage_difference:.1f}%</div>
        <div class="card-sub">{comp.baseline.total_estimated_cycle_time_s:.1f}s &rarr; {comp.optimized.total_estimated_cycle_time_s:.1f}s ({comp.time_savings.absolute_difference:.1f}s saved)</div>
      </div>
      <div class="card">
        <div class="card-title">Rapid Travel Reduction</div>
        <div class="card-value">{comp.rapid_distance_savings.percentage_difference:.1f}%</div>
        <div class="card-sub">{comp.baseline.rapid_travel_distance_mm:.1f}mm &rarr; {comp.optimized.rapid_travel_distance_mm:.1f}mm</div>
      </div>
      <div class="card">
        <div class="card-title">DFM Manufacturability</div>
        <div class="card-value" style="color: {score_color};">{dfm.overall_score:.1f}/100</div>
        <div class="card-sub">{dfm.green_count} Green, {dfm.yellow_count} Warnings, {dfm.red_count} Blockers</div>
      </div>
      <div class="card">
        <div class="card-title">G-Code Validation</div>
        <div class="card-value" style="font-size: 1.4rem; padding-top: 0.4rem;">{val_status_badge}</div>
        <div class="card-sub">{'G-code exported' if val.gcode_export_permitted else 'Export gated & prohibited'}</div>
      </div>
    </div>

    <!-- Section 1: Optimization Comparison -->
    <section>
      <h2>1. Optimization Plan Comparison</h2>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Baseline Plan</th>
            <th>Optimized Plan</th>
            <th>Difference / Savings</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Estimated Cycle Time</strong></td>
            <td>{comp.baseline.total_estimated_cycle_time_s:.1f} s</td>
            <td>{comp.optimized.total_estimated_cycle_time_s:.1f} s</td>
            <td><strong>{comp.time_savings.percentage_difference:.1f}% reduction</strong> ({comp.time_savings.absolute_difference:.1f} s)</td>
          </tr>
          <tr>
            <td><strong>Rapid Travel Distance</strong></td>
            <td>{comp.baseline.rapid_travel_distance_mm:.1f} mm</td>
            <td>{comp.optimized.rapid_travel_distance_mm:.1f} mm</td>
            <td><strong>{comp.rapid_distance_savings.percentage_difference:.1f}% reduction</strong> ({comp.rapid_distance_savings.absolute_difference:.1f} mm)</td>
          </tr>
          <tr>
            <td><strong>Tool Changes (ATC)</strong></td>
            <td>{comp.baseline.tool_changes_count} changes</td>
            <td>{comp.optimized.tool_changes_count} changes</td>
            <td><strong>{comp.tool_change_savings.absolute_difference} fewer changes</strong></td>
          </tr>
          <tr>
            <td><strong>Stock Utilization</strong></td>
            <td colspan="2">{comp.part_volume_mm3:.1f} mm³ part / {comp.stock_volume_mm3:.1f} mm³ raw stock</td>
            <td><strong>{comp.stock_utilization_percent:.1f}%</strong></td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Section 2: Model Summary -->
    <section>
      <h2>2. Model B-Rep Geometry Metrics</h2>
      <p>Loaded solid containing <strong>{summary.faces_count} faces</strong>, <strong>{summary.edges_count} edges</strong>, and <strong>{summary.vertices_count} vertices</strong>.</p>
      <table>
        <thead>
          <tr><th>Property</th><th>Value</th></tr>
        </thead>
        <tbody>
          <tr><td>Bounding Box Envelope</td><td>X: {summary.bounding_box.dx:.2f} mm | Y: {summary.bounding_box.dy:.2f} mm | Z: {summary.bounding_box.dz:.2f} mm</td></tr>
          <tr><td>Part Finished Volume</td><td>{summary.volume_mm3:.2f} mm³</td></tr>
          <tr><td>Total Surface Area</td><td>{summary.surface_area_mm2:.2f} mm²</td></tr>
          <tr><td>Surface Classification</td><td>{summary.face_counts_by_surface_type.plane} Planes, {summary.face_counts_by_surface_type.cylinder} Cylinders, {summary.face_counts_by_surface_type.cone} Cones</td></tr>
          <tr><td>Analysis Duration</td><td>Parse: {summary.load_time_s:.3f}s | B-Rep Topology: {summary.analysis_time_s:.3f}s</td></tr>
        </tbody>
      </table>
    </section>

    <!-- Section 3: Feature Recognition -->
    <section>
      <h2>3. Recognized Manufacturing Features</h2>
      <h3>Detected Holes ({len(features.holes)})</h3>
      <table>
        <thead>
          <tr>
            <th>Feature ID</th><th>Subtype</th><th>Diameter</th><th>Depth</th><th>Axis</th><th>Status</th><th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f"<tr><td><code>{h.id}</code></td><td>{to_str(h.type)}</td><td>{h.diameter_mm:.1f} mm</td><td>{h.depth_mm:.1f} mm</td><td>[{h.axis.x:.1f}, {h.axis.y:.1f}, {h.axis.z:.1f}]</td><td><span class='badge pass'>{to_str(h.status)}</span></td><td>{h.confidence:.2f}</td></tr>" for h in features.holes)}
        </tbody>
      </table>

      <h3>Detected Pockets ({len(features.pockets)}) & Slots ({len(features.slots)})</h3>
      <table>
        <thead>
          <tr><th>Feature ID</th><th>Kind</th><th>Dimensions (L &times; W &times; D)</th><th>Status</th><th>Confidence</th></tr>
        </thead>
        <tbody>
          {"".join(f"<tr><td><code>{p.id}</code></td><td>Pocket ({to_str(p.type)})</td><td>{p.length_mm:.1f} &times; {p.width_mm:.1f} &times; {p.depth_mm:.1f} mm</td><td><span class='badge pass'>{to_str(p.status)}</span></td><td>{p.confidence:.2f}</td></tr>" for p in features.pockets)}
          {"".join(f"<tr><td><code>{s.id}</code></td><td>Slot ({to_str(s.type)})</td><td>{s.length_mm:.1f} &times; {s.width_mm:.1f} &times; {s.depth_mm:.1f} mm</td><td><span class='badge pass'>{to_str(s.status)}</span></td><td>{s.confidence:.2f}</td></tr>" for s in features.slots)}
        </tbody>
      </table>
    </section>

    <!-- Section 4: Manufacturability (DFM) -->
    <section>
      <h2>4. Manufacturability Findings & DFM Score ({dfm.overall_score:.1f}/100)</h2>
      <table>
        <thead>
          <tr><th>Severity</th><th>Category</th><th>Feature</th><th>Explanation</th><th>Remediation</th></tr>
        </thead>
        <tbody>
          {"".join(f"<tr><td><span class='badge {to_str(f.severity)}'>{to_str(f.severity)}</span></td><td>{f.category}</td><td><code>{f.feature_id or 'Model'}</code></td><td>{f.explanation}</td><td>{f.how_to_resolve}</td></tr>" for f in dfm.findings)}
        </tbody>
      </table>
    </section>

    <!-- Section 5: Validation Gate -->
    <section>
      <h2>5. Closed-Loop Validation Gate</h2>
      <table>
        <thead>
          <tr><th>Check</th><th>Status</th><th>Details</th></tr>
        </thead>
        <tbody>
          {"".join(f"<tr><td><strong>{c.name}</strong></td><td><span class='badge {'pass' if c.passed else 'fail'}'>{'PASS' if c.passed else 'FAIL'}</span></td><td>{c.details}</td></tr>" for c in val.checks)}
        </tbody>
      </table>
    </section>

    <footer>
      <p style="text-align: center; color: var(--text-muted); font-size: 0.8rem; margin-top: 2rem;">
        Generated by CAD-CNC Optimization Engine &bull; Monotonic Runtime: {run_log.total_duration_s:.3f}s &bull; Schema Version 1.0.0
      </p>
    </footer>
  </div>
</body>
</html>
"""
    return html

def write_reports(
    out_dir: Path | str,
    summary: ModelSummary,
    features: FeaturesCollection,
    dfm: ManufacturabilityReport,
    recs: ToolRecommendationsReport,
    plan: MachiningPlan,
    comp: ComparisonReport,
    val: ValidationReport,
    run_log: RunLog,
    material_id: str,
    machine_name: str
) -> tuple[Path, Path]:
    """Writes report.md and report.html to out_dir."""
    out_path = Path(out_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    md_content = build_markdown_report(
        summary, features, dfm, recs, plan, comp, val, run_log, material_id, machine_name
    )
    html_content = build_html_report(
        summary, features, dfm, recs, plan, comp, val, run_log, material_id, machine_name
    )

    md_file = out_path / "report.md"
    html_file = out_path / "report.html"

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    return md_file, html_file
