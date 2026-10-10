"""Command line interface for cadcnc."""

import argparse
import sys
from pathlib import Path

from cadcnc.engine import Engine, EngineRunRequest
from cadcnc.cad_engine.parser import STEPParseError

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="cadcnc",
        description="Automated CAD-to-CNC Optimization Engine - B-Rep feature recognition and CAM planning."
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # cadcnc run
    run_parser = subparsers.add_parser("run", help="Run full end-to-end CAD-to-CNC optimization pipeline")
    run_parser.add_argument("--model", required=True, help="Path to input STEP/STP 3D CAD model")
    run_parser.add_argument("--material", default="aluminum_6061", help="Material ID from materials database")
    run_parser.add_argument("--machine", default=None, help="Path to machine config YAML/JSON")
    run_parser.add_argument("--tools", default=None, help="Path to tools database JSON")
    run_parser.add_argument("--stock", default=None, help="Path to stock config YAML/JSON")
    run_parser.add_argument("--config", default=None, help="Path to thresholds config YAML")
    run_parser.add_argument("--out", default="out", help="Output directory")

    # cadcnc analyze
    analyze_parser = subparsers.add_parser("analyze", help="Stage 1: Load CAD, compute geometry and B-Rep summary")
    analyze_parser.add_argument("--model", required=True, help="Path to input STEP/STP CAD model")
    analyze_parser.add_argument("--out", default="out", help="Output directory")

    # cadcnc features
    features_parser = subparsers.add_parser("features", help="Stage 2: Recognize manufacturing features (holes, etc.)")
    features_parser.add_argument("--model", required=True, help="Path to input STEP/STP CAD model")
    features_parser.add_argument("--config", default=None, help="Path to thresholds config YAML")
    features_parser.add_argument("--out", default="out", help="Output directory")

    # cadcnc tools
    tools_parser = subparsers.add_parser("tools", help="Stage 3: Select and rank candidate cutting tools")
    tools_parser.add_argument("--model", required=True, help="Path to input STEP/STP CAD model")
    tools_parser.add_argument("--material", default="aluminum_6061", help="Material ID")
    tools_parser.add_argument("--tools", default=None, help="Path to tools database JSON")
    tools_parser.add_argument("--out", default="out", help="Output directory")

    # cadcnc check
    check_parser = subparsers.add_parser("check", help="Stage 4: Run DFM manufacturability and accessibility analysis")
    check_parser.add_argument("--model", required=True, help="Path to input STEP/STP CAD model")
    check_parser.add_argument("--material", default="aluminum_6061", help="Material ID")
    check_parser.add_argument("--machine", default=None, help="Path to machine config YAML")
    check_parser.add_argument("--tools", default=None, help="Path to tools database JSON")
    check_parser.add_argument("--out", default="out", help="Output directory")

    # cadcnc plan
    plan_parser = subparsers.add_parser("plan", help="Stage 5: Plan and optimize operations sequence and estimate savings")
    plan_parser.add_argument("--model", required=True, help="Path to input STEP/STP CAD model")
    plan_parser.add_argument("--material", default="aluminum_6061", help="Material ID")
    plan_parser.add_argument("--machine", default=None, help="Path to machine config YAML")
    plan_parser.add_argument("--tools", default=None, help="Path to tools database JSON")
    plan_parser.add_argument("--stock", default=None, help="Path to stock config YAML")
    plan_parser.add_argument("--out", default="out", help="Output directory")

    # cadcnc toolpaths
    toolpaths_parser = subparsers.add_parser("toolpaths", help="Stage 6: Generate toolpaths, validate and export G-code")
    toolpaths_parser.add_argument("--model", required=True, help="Path to input STEP/STP CAD model")
    toolpaths_parser.add_argument("--material", default="aluminum_6061", help="Material ID")
    toolpaths_parser.add_argument("--machine", default=None, help="Path to machine config YAML")
    toolpaths_parser.add_argument("--tools", default=None, help="Path to tools database JSON")
    toolpaths_parser.add_argument("--stock", default=None, help="Path to stock config YAML")
    toolpaths_parser.add_argument("--config", default=None, help="Path to thresholds config YAML")
    toolpaths_parser.add_argument("--out", default="out", help="Output directory")

    # cadcnc report
    report_parser = subparsers.add_parser("report", help="Stage 7: Generate markdown and HTML optimization report")
    report_parser.add_argument("--model", required=True, help="Path to input STEP/STP CAD model")
    report_parser.add_argument("--material", default="aluminum_6061", help="Material ID")
    report_parser.add_argument("--machine", default=None, help="Path to machine config YAML")
    report_parser.add_argument("--tools", default=None, help="Path to tools database JSON")
    report_parser.add_argument("--stock", default=None, help="Path to stock config YAML")
    report_parser.add_argument("--config", default=None, help="Path to thresholds config YAML")
    report_parser.add_argument("--out", default="out", help="Output directory")

    parsed = parser.parse_args(args)

    if not parsed.subcommand:
        parser.print_help()
        sys.exit(1)

    engine = Engine()

    if parsed.subcommand == "analyze":
        try:
            print(f"Analyzing CAD model: {parsed.model} -> {parsed.out}")
            summary = engine.analyze(parsed.model, parsed.out)
            print(f"[SUCCESS] Model analyzed successfully:")
            print(f"  Solid volume : {summary.volume_mm3:.2f} mm3")
            print(f"  Faces count  : {summary.faces_count} (Planes: {summary.face_counts_by_surface_type.plane}, Cylinders: {summary.face_counts_by_surface_type.cylinder})")
            print(f"  Edges count  : {summary.edges_count}")
            print(f"  Output files : {parsed.out}/model_summary.json, {parsed.out}/model_preview.glb")
            sys.exit(0)
        except STEPParseError as e:
            print(f"[ERROR] CAD Parse Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[FATAL ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "features":
        try:
            print(f"Recognizing features in: {parsed.model} -> {parsed.out}")
            coll = engine.features(parsed.model, parsed.out)
            print(f"[SUCCESS] Features recognized:")
            print(f"  Holes detected   : {len(coll.holes)}")
            for h in coll.holes:
                print(f"    - {h.id}: {h.type.upper()} D={h.diameter_mm:.1f}mm depth={h.depth_mm:.1f}mm ({h.status.value})")
            print(f"  Pockets detected : {len(coll.pockets)}")
            print(f"  Slots detected   : {len(coll.slots)}")
            print(f"  Output files     : {parsed.out}/features.json, {parsed.out}/feature_map.json")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "tools":
        try:
            print(f"Selecting cutting tools for: {parsed.model} -> {parsed.out}")
            recs = engine.tools(parsed.model, parsed.out, tools_path=parsed.tools, material_id=parsed.material)
            print(f"[SUCCESS] Tools recommended for {len(recs.recommendations)} features:")
            for r in recs.recommendations:
                status_str = f"Selected: {r.selected_tool_id}" if r.selected_tool_id else "NO MATCHING TOOL"
                print(f"  - {r.feature_id} ({r.feature_type}): {status_str} ({len(r.ranked_candidates)} candidates)")
            print(f"  Output files     : {parsed.out}/tool_recommendations.json")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "check":
        try:
            print(f"Evaluating manufacturability for: {parsed.model} -> {parsed.out}")
            report = engine.check(
                parsed.model, parsed.out,
                machine_path=parsed.machine, tools_path=parsed.tools, material_id=parsed.material
            )
            print(f"[SUCCESS] Manufacturability score: {report.overall_score}/100.0")
            print(f"  Green findings   : {report.green_count}")
            print(f"  Yellow warnings  : {report.yellow_count}")
            print(f"  Red blockers     : {report.red_count}")
            for f in report.findings:
                print(f"    [{f.severity.value.upper()}] {f.category}: {f.explanation}")
            print(f"  Output files     : {parsed.out}/manufacturability.json")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "plan":
        try:
            print(f"Planning and optimizing operations for: {parsed.model} -> {parsed.out}")
            plan, comp = engine.plan(
                parsed.model, parsed.out,
                material_id=parsed.material,
                machine_path=parsed.machine,
                tools_path=parsed.tools,
                stock_path=parsed.stock
            )
            print(f"[SUCCESS] Machining plan generated:")
            print(f"  Total operations : {plan.optimized_plan.total_operations}")
            print(f"  Baseline time    : {comp.baseline.total_estimated_cycle_time_s:.1f}s (Tool changes: {comp.baseline.tool_changes_count})")
            print(f"  Optimized time   : {comp.optimized.total_estimated_cycle_time_s:.1f}s (Tool changes: {comp.optimized.tool_changes_count})")
            print(f"  Time savings     : {comp.time_savings.percentage_difference:.1f}% ({comp.time_savings.absolute_difference:.1f}s)")
            print(f"  Rapid travel cut : {comp.rapid_distance_savings.percentage_difference:.1f}% ({comp.rapid_distance_savings.absolute_difference:.1f}mm)")
            print(f"  Stock utilization: {comp.stock_utilization_percent:.1f}%")
            print(f"  Output files     : {parsed.out}/operation_plan.json, {parsed.out}/comparison.json")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "toolpaths":
        try:
            print(f"Generating toolpaths and validating for: {parsed.model} -> {parsed.out}")
            tp, val = engine.toolpaths(
                parsed.model, parsed.out,
                material_id=parsed.material,
                machine_path=parsed.machine,
                tools_path=parsed.tools,
                stock_path=parsed.stock,
                config=None
            )
            print(f"[SUCCESS] Toolpath operations compiled: {tp.total_operations} ops, {tp.total_moves} moves.")
            print(f"Validation checks result:")
            for chk in val.checks:
                status_icon = "[PASS]" if chk.passed else "[FAIL]"
                print(f"  {status_icon} {chk.name}: {chk.details}")
            if val.gcode_export_permitted:
                print(f"[SUCCESS] Validation PASSED. G-code exported: {', '.join(val.exported_gcode_files)}")
            else:
                print(f"[GATING BLOCKED] Validation FAILED. G-code export prohibited:")
                for r in val.failure_reasons:
                    print(f"  - {r}")
            print(f"  Output files     : {parsed.out}/toolpaths.json, {parsed.out}/validation_report.json")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "report":
        try:
            print(f"Generating comprehensive optimization report for: {parsed.model} -> {parsed.out}")
            md_path, html_path = engine.report(
                parsed.model, parsed.out,
                material_id=parsed.material,
                machine_path=parsed.machine,
                tools_path=parsed.tools,
                stock_path=parsed.stock
            )
            print(f"[SUCCESS] Reports generated successfully:")
            print(f"  Markdown report : {md_path}")
            print(f"  HTML report     : {html_path}")
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "run":
        try:
            print(f"=================================================================")
            print(f"  CAD-to-CNC Optimization Engine: Automated Processing Pipeline")
            print(f"=================================================================")
            print(f"Input CAD Model   : {parsed.model}")
            print(f"Target Material   : {parsed.material}")
            print(f"Output Directory  : {parsed.out}")
            print("")

            req = EngineRunRequest(
                model_path=Path(parsed.model),
                out_dir=Path(parsed.out),
                material_id=parsed.material,
                machine_path=Path(parsed.machine) if parsed.machine else None,
                tools_path=Path(parsed.tools) if parsed.tools else None,
                stock_path=Path(parsed.stock) if parsed.stock else None,
                config_path=Path(parsed.config) if parsed.config else None
            )

            def print_progress(stage_name: str, frac: float):
                bar = "#" * int(frac * 20) + "-" * (20 - int(frac * 20))
                print(f"[{bar}] {int(frac * 100):3d}% | {stage_name}")

            res = engine.run(req, progress_cb=print_progress)

            print("")
            print(f"=================================================================")
            print(f"  PIPELINE EXECUTION COMPLETE (in {res.run_log.total_duration_s:.3f} s)")
            print(f"=================================================================")
            print(f"1. Model Summary:")
            print(f"   Solid: {res.summary.solids_count} | Faces: {res.summary.faces_count} | Edges: {res.summary.edges_count}")
            print(f"   Volume: {res.summary.volume_mm3:.2f} mm3 | Dimensions: {res.summary.bounding_box.dx:.1f} x {res.summary.bounding_box.dy:.1f} x {res.summary.bounding_box.dz:.1f} mm")
            print("")
            print(f"2. Features Recognized:")
            print(f"   Holes: {len(res.features.holes)} | Pockets: {len(res.features.pockets)} | Slots: {len(res.features.slots)} | Corners: {len(res.features.internal_corners)} | Walls: {len(res.features.thin_walls)}")
            print("")
            print(f"3. DFM Manufacturability Score:")
            print(f"   Score: {res.manufacturability.overall_score:.1f}/100.0 ({res.manufacturability.green_count} Green, {res.manufacturability.yellow_count} Yellow, {res.manufacturability.red_count} Red)")
            print("")
            print(f"4. Optimization Results:")
            print(f"   Cycle Time Reduction : {res.comparison.time_savings.percentage_difference:.1f}% ({res.comparison.baseline.total_estimated_cycle_time_s:.1f}s -> {res.comparison.optimized.total_estimated_cycle_time_s:.1f}s)")
            print(f"   Rapid Travel Cut     : {res.comparison.rapid_distance_savings.percentage_difference:.1f}% ({res.comparison.baseline.rapid_travel_distance_mm:.1f}mm -> {res.comparison.optimized.rapid_travel_distance_mm:.1f}mm)")
            print(f"   Tool Changes Saved   : {res.comparison.tool_change_savings.absolute_difference} changes ({res.comparison.baseline.tool_changes_count} -> {res.comparison.optimized.tool_changes_count})")
            print(f"   Stock Utilization    : {res.comparison.stock_utilization_percent:.1f}%")
            print("")
            print(f"5. Closed-Loop Validation Gate & G-Code Export:")
            if res.validation.gcode_export_permitted:
                print(f"   Validation Status    : PASSED [OK]")
                print(f"   Exported G-code      : {', '.join(res.validation.exported_gcode_files)}")
            else:
                print(f"   Validation Status    : BLOCKED [FAIL]")
                for r in res.validation.failure_reasons:
                    print(f"     - {r}")
            print("")
            print(f"6. Deliverables Produced in '{parsed.out}':")
            for fn in sorted(res.output_files):
                print(f"   - {fn}")
            print("=================================================================")
            sys.exit(0)
        except STEPParseError as e:
            print(f"[ERROR] CAD Parse Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[FATAL ERROR]: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
