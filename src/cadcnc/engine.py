"""Engine: Core orchestrator for CAD analysis, feature recognition, CAM, and optimization."""

import json
import logging
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Any, Tuple, List
from pydantic import BaseModel, Field

from cadcnc.cad_engine.parser import load_step_model, CADModel, STEPParseError
from cadcnc.cad_engine.geometry import (
    compute_bounding_box, compute_volume_and_area, classify_surface
)
from cadcnc.cad_engine.topology import build_topology_graph, TopologyGraph
from cadcnc.cad_engine.tessellate import export_model_preview, export_feature_map
from cadcnc.schemas.config import ThresholdsConfig
from cadcnc.schemas.cad import ModelSummary, SurfaceCounts
from cadcnc.schemas.features import FeaturesCollection, FeatureMap
from cadcnc.schemas.optimization import (
    ToolRecommendationsReport, MachiningPlan, ComparisonReport
)
from cadcnc.schemas.cam import ToolpathsCollection, ValidationReport
from cadcnc.schemas.analysis import ManufacturabilityReport
from cadcnc.schemas.run_log import RunLog, StageTiming

logger = logging.getLogger("cadcnc")

class EngineRunRequest(BaseModel):
    model_path: Path
    out_dir: Path = Path("out")
    material_id: str = "aluminum_6061"
    machine_path: Optional[Path] = None
    tools_path: Optional[Path] = None
    stock_path: Optional[Path] = None
    config_path: Optional[Path] = None

class EngineRunResult(BaseModel):
    schema_version: str = "1.0.0"
    success: bool
    summary: ModelSummary
    features: FeaturesCollection
    manufacturability: ManufacturabilityReport
    tool_recommendations: ToolRecommendationsReport
    machining_plan: MachiningPlan
    comparison: ComparisonReport
    toolpaths: ToolpathsCollection
    validation: ValidationReport
    run_log: RunLog
    output_files: List[str] = Field(default_factory=list)

class Engine:
    """Headless CAD-to-CNC Optimization Engine."""

    def __init__(self):
        pass

    def analyze(
        self,
        model_path: Path | str,
        out_dir: Path | str,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> ModelSummary:
        """Loads STEP model, computes geometry metrics, tessellates preview, and writes model_summary.json.
        
        Args:
            model_path: Path to .step or .stp CAD file.
            out_dir: Directory where model_summary.json, model_preview.glb, and feature_map.json are written.
            progress_cb: Optional callback(stage_name, fraction_complete).
        
        Returns:
            ModelSummary Pydantic model.
        """
        model_path = Path(model_path).resolve()
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        if progress_cb:
            progress_cb("Loading STEP CAD file", 0.1)

        # 1. Parse STEP
        cad_model = load_step_model(model_path)
        primary_solid = cad_model.primary_solid

        if progress_cb:
            progress_cb("Analyzing B-Rep topology", 0.4)

        t0_analysis = time.perf_counter()

        # 2. Geometry measurements
        bbox = compute_bounding_box(primary_solid)
        volume, area = compute_volume_and_area(primary_solid)

        # 3. Build topology graph
        top_graph = build_topology_graph(primary_solid)

        # 4. Count surface types
        surface_counts = SurfaceCounts()
        for face_node in top_graph.faces.values():
            stype = face_node.surface_type
            if hasattr(surface_counts, stype):
                setattr(surface_counts, stype, getattr(surface_counts, stype) + 1)
            else:
                surface_counts.other += 1

        analysis_time_s = time.perf_counter() - t0_analysis

        if progress_cb:
            progress_cb("Tessellating 3D preview model", 0.7)

        # 5. Tessellate preview
        preview_glb_path = out_dir / "model_preview.glb"
        export_model_preview(primary_solid, preview_glb_path)

        # 6. Initial empty feature map
        feature_map_path = out_dir / "feature_map.json"
        initial_map = {fid: [] for fid in top_graph.faces.keys()}
        export_feature_map(initial_map, feature_map_path)

        # 7. Count B-Rep entities
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX
        
        solids_cnt = len(cad_model.solids)
        shells_cnt = 0
        exp_shell = TopExp_Explorer(primary_solid, TopAbs_SHELL)
        while exp_shell.More():
            shells_cnt += 1
            exp_shell.Next()

        edges_cnt = len(top_graph.edges)
        faces_cnt = len(top_graph.faces)

        vertices_cnt = 0
        exp_vert = TopExp_Explorer(primary_solid, TopAbs_VERTEX)
        while exp_vert.More():
            vertices_cnt += 1
            exp_vert.Next()

        summary = ModelSummary(
            schema_version="1.0.0",
            filename=model_path.name,
            size_bytes=model_path.stat().st_size,
            unit=cad_model.unit,
            solids_count=solids_cnt,
            shells_count=shells_cnt,
            faces_count=faces_cnt,
            edges_count=edges_cnt,
            vertices_count=vertices_cnt,
            bounding_box=bbox,
            volume_mm3=volume,
            surface_area_mm2=area,
            face_counts_by_surface_type=surface_counts,
            load_time_s=cad_model.load_time_s,
            analysis_time_s=analysis_time_s
        )

        # 8. Save model_summary.json
        summary_path = out_dir / "model_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))

        if progress_cb:
            progress_cb("CAD analysis complete", 1.0)

        return summary

    def features(
        self,
        model_path: Path | str,
        out_dir: Path | str,
        config: Optional[ThresholdsConfig] = None,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> FeaturesCollection:
        """Detects manufacturing features and exports features.json and feature_map.json."""
        if config is None:
            config = ThresholdsConfig()

        model_path = Path(model_path).resolve()
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        if progress_cb:
            progress_cb("Loading CAD solid", 0.1)

        cad_model = load_step_model(model_path)
        solid = cad_model.primary_solid

        if progress_cb:
            progress_cb("Building topology graph", 0.3)

        top_graph = build_topology_graph(solid)

        if progress_cb:
            progress_cb("Executing feature detectors", 0.6)

        from cadcnc.feature_detection.registry import global_registry
        detector_results = global_registry.run_all(top_graph, solid, config)

        holes = detector_results.get("hole_detector", [])
        pockets = detector_results.get("pocket_detector", [])
        slots = detector_results.get("slot_detector", [])
        corners = detector_results.get("corner_detector", [])
        walls = detector_results.get("wall_detector", [])

        # Planar faces extraction
        from cadcnc.schemas.features import PlanarFaceFeature
        planar_faces: List[PlanarFaceFeature] = []
        max_z = -float("inf")
        top_fid = None

        for fid, fnode in top_graph.faces.items():
            if fnode.surface_type == "plane":
                is_top = (fnode.normal_or_axis.z > 0.95 and fnode.location.z > max_z)
                if is_top:
                    max_z = fnode.location.z
                    top_fid = fid
                planar_faces.append(PlanarFaceFeature(
                    face_id=fid,
                    normal=fnode.normal_or_axis,
                    area_mm2=fnode.area_mm2,
                    is_top_candidate=False,
                    center=fnode.location
                ))

        for pf in planar_faces:
            if pf.face_id == top_fid:
                pf.is_top_candidate = True

        collection = FeaturesCollection(
            schema_version="1.0.0",
            holes=holes,
            pockets=pockets,
            slots=slots,
            internal_corners=corners,
            thin_walls=walls,
            planar_faces=planar_faces
        )

        # Write features.json
        features_json_path = out_dir / "features.json"
        with open(features_json_path, "w", encoding="utf-8") as f:
            f.write(collection.model_dump_json(indent=2))

        # Update feature_map.json
        face_map: Dict[str, List[str]] = {fid: [] for fid in top_graph.faces.keys()}
        for h in holes:
            for fid in h.face_ids:
                if fid in face_map:
                    face_map[fid].append(h.id)
        for p in pockets:
            if p.floor_face_id in face_map:
                face_map[p.floor_face_id].append(p.id)
            for w in p.wall_face_ids:
                if w in face_map:
                    face_map[w].append(p.id)
        for s in slots:
            if s.floor_face_id and s.floor_face_id in face_map:
                face_map[s.floor_face_id].append(s.id)
            for w in s.wall_face_ids:
                if w in face_map:
                    face_map[w].append(s.id)

        export_feature_map(face_map, out_dir / "feature_map.json")

        if progress_cb:
            progress_cb("Feature detection complete", 1.0)

        return collection

    def tools(
        self,
        model_path: Path | str,
        out_dir: Path | str,
        tools_path: Optional[Path | str] = None,
        material_id: str = "aluminum_6061",
        config: Optional[ThresholdsConfig] = None,
        features_coll: Optional[FeaturesCollection] = None,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> ToolRecommendationsReport:
        """Selects and ranks candidate cutting tools for each feature."""
        if features_coll is None:
            features_coll = self.features(model_path, out_dir, config=config, progress_cb=progress_cb)

        if tools_path is None:
            tools_path = Path(__file__).resolve().parent.parent.parent / "data" / "tools_example.json"
        from cadcnc.optimization.tool_selector import load_tool_database, select_tools_for_features
        tools_db = load_tool_database(tools_path)

        report = select_tools_for_features(features_coll, tools_db, material_id)
        out_path = Path(out_dir) / "tool_recommendations.json"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        return report

    def check(
        self,
        model_path: Path | str,
        out_dir: Path | str,
        machine_path: Optional[Path | str] = None,
        tools_path: Optional[Path | str] = None,
        material_id: str = "aluminum_6061",
        config: Optional[ThresholdsConfig] = None,
        summary: Optional[ModelSummary] = None,
        features_coll: Optional[FeaturesCollection] = None,
        recs: Optional[ToolRecommendationsReport] = None,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> ManufacturabilityReport:
        """Evaluates manufacturability findings, accessibility setups, and DFM score."""
        if summary is None:
            summary = self.analyze(model_path, out_dir, progress_cb=progress_cb)
        if features_coll is None:
            features_coll = self.features(model_path, out_dir, config=config)
        if recs is None:
            recs = self.tools(model_path, out_dir, tools_path=tools_path, material_id=material_id, config=config, features_coll=features_coll)

        if machine_path is None:
            machine_path = Path(__file__).resolve().parent.parent.parent / "config" / "machine_3axis_example.yaml"
        import yaml
        from cadcnc.schemas.config import MachineConfig
        with open(machine_path, "r", encoding="utf-8") as f:
            m_data = yaml.safe_load(f)
        machine_config = MachineConfig.model_validate(m_data)

        if config is None:
            config = ThresholdsConfig()

        from cadcnc.analysis.manufacturability import evaluate_manufacturability
        report = evaluate_manufacturability(summary, features_coll, recs, config, machine_config)
        out_path = Path(out_dir) / "manufacturability.json"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        return report

    def plan(
        self,
        model_path: Path | str,
        out_dir: Path | str,
        material_id: str = "aluminum_6061",
        machine_path: Optional[Path | str] = None,
        tools_path: Optional[Path | str] = None,
        stock_path: Optional[Path | str] = None,
        config: Optional[ThresholdsConfig] = None,
        summary: Optional[ModelSummary] = None,
        features_coll: Optional[FeaturesCollection] = None,
        recs: Optional[ToolRecommendationsReport] = None,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[MachiningPlan, ComparisonReport]:
        """Generates operation sequences (baseline & optimized) and computes comparison.json."""
        if summary is None:
            summary = self.analyze(model_path, out_dir, progress_cb=progress_cb)
        if features_coll is None:
            features_coll = self.features(model_path, out_dir, config=config)
        if recs is None:
            recs = self.tools(model_path, out_dir, tools_path=tools_path, material_id=material_id, config=config, features_coll=features_coll)

        if machine_path is None:
            machine_path = Path(__file__).resolve().parent.parent.parent / "config" / "machine_3axis_example.yaml"
        import yaml
        from cadcnc.schemas.config import MachineConfig, StockConfig, MaterialsDatabase
        with open(machine_path, "r", encoding="utf-8") as f:
            m_data = yaml.safe_load(f)
        machine_config = MachineConfig.model_validate(m_data)

        if stock_path is None:
            stock_path = Path(__file__).resolve().parent.parent.parent / "config" / "stock_example.yaml"
        with open(stock_path, "r", encoding="utf-8") as f:
            s_data = yaml.safe_load(f)
        stock_config = StockConfig.model_validate(s_data)

        mat_path = Path(__file__).resolve().parent.parent.parent / "data" / "materials.json"
        with open(mat_path, "r", encoding="utf-8") as f:
            mat_raw = json.load(f)
        materials_db = MaterialsDatabase.model_validate(mat_raw)

        from cadcnc.optimization.machining_plan import build_machining_plan
        from cadcnc.optimization.waste_estimator import estimate_stock_and_waste
        from cadcnc.optimization.comparison import generate_comparison_report

        plan_res = build_machining_plan(features_coll, recs, machine_config, materials_db, material_id)
        stock_res = estimate_stock_and_waste(summary.bounding_box, summary.volume_mm3, stock_config)
        comp_res = generate_comparison_report(plan_res, stock_res)

        # Write operation_plan.json and comparison.json
        out_plan = Path(out_dir) / "operation_plan.json"
        with open(out_plan, "w", encoding="utf-8") as f:
            f.write(plan_res.model_dump_json(indent=2))

        out_comp = Path(out_dir) / "comparison.json"
        with open(out_comp, "w", encoding="utf-8") as f:
            f.write(comp_res.model_dump_json(indent=2))

        return plan_res, comp_res

    def toolpaths(
        self,
        model_path: Path | str,
        out_dir: Path | str,
        material_id: str = "aluminum_6061",
        machine_path: Optional[Path | str] = None,
        tools_path: Optional[Path | str] = None,
        stock_path: Optional[Path | str] = None,
        config: Optional[ThresholdsConfig] = None,
        summary: Optional[ModelSummary] = None,
        features_coll: Optional[FeaturesCollection] = None,
        recs: Optional[ToolRecommendationsReport] = None,
        dfm_report: Optional[ManufacturabilityReport] = None,
        plan_res: Optional[MachiningPlan] = None,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[ToolpathsCollection, ValidationReport]:
        """Generates continuous toolpaths, validates machine envelope and safety, and conditionally exports G-code."""
        if summary is None:
            summary = self.analyze(model_path, out_dir, progress_cb=progress_cb)
        if features_coll is None:
            features_coll = self.features(model_path, out_dir, config=config)
        if recs is None:
            recs = self.tools(model_path, out_dir, tools_path=tools_path, material_id=material_id, config=config, features_coll=features_coll)
        if dfm_report is None:
            dfm_report = self.check(model_path, out_dir, machine_path=machine_path, tools_path=tools_path, material_id=material_id, config=config, summary=summary, features_coll=features_coll, recs=recs)
        if plan_res is None:
            plan_res, _ = self.plan(model_path, out_dir, material_id=material_id, machine_path=machine_path, tools_path=tools_path, stock_path=stock_path, config=config, summary=summary, features_coll=features_coll, recs=recs)

        if machine_path is None:
            machine_path = Path(__file__).resolve().parent.parent.parent / "config" / "machine_3axis_example.yaml"
        import yaml
        from cadcnc.schemas.config import MachineConfig
        with open(machine_path, "r", encoding="utf-8") as f:
            m_data = yaml.safe_load(f)
        machine_config = MachineConfig.model_validate(m_data)

        if tools_path is None:
            tools_path = Path(__file__).resolve().parent.parent.parent / "data" / "tools_example.json"
        from cadcnc.optimization.tool_selector import load_tool_database
        tools_db = load_tool_database(tools_path)

        if config is None:
            config = ThresholdsConfig()

        from cadcnc.cam.toolpath import generate_full_toolpaths
        from cadcnc.cam.validation import validate_toolpaths_and_plan
        from cadcnc.cam.postprocessor import PostProcessor

        if progress_cb:
            progress_cb("Generating geometric toolpaths", 0.5)

        tp_coll = generate_full_toolpaths(plan_res, features_coll, summary.bounding_box, tools_db, config)

        if progress_cb:
            progress_cb("Executing closed-loop validation gate", 0.8)

        val_report = validate_toolpaths_and_plan(tp_coll, machine_config, tools_db, dfm_report)

        # G-code Gating: write .nc file ONLY if all mandatory checks passed
        program_path = Path(out_dir) / "program_setup1.nc"
        if val_report.all_mandatory_checks_passed:
            postprocessor = PostProcessor(machine_config, tools_db)
            gcode_str = postprocessor.generate_gcode(tp_coll, 1001, "SETUP-1")
            with open(program_path, "w", encoding="utf-8") as f:
                f.write(gcode_str)
            val_report.exported_gcode_files = ["program_setup1.nc"]
            val_report.gcode_export_permitted = True
        else:
            val_report.exported_gcode_files = []
            val_report.gcode_export_permitted = False
            if program_path.exists():
                program_path.unlink()

        # Save toolpaths.json and validation_report.json
        out_tp = Path(out_dir) / "toolpaths.json"
        with open(out_tp, "w", encoding="utf-8") as f:
            f.write(tp_coll.model_dump_json(indent=2))

        out_val = Path(out_dir) / "validation_report.json"
        with open(out_val, "w", encoding="utf-8") as f:
            f.write(val_report.model_dump_json(indent=2))

        if progress_cb:
            progress_cb("Toolpaths and validation complete", 1.0)

        return tp_coll, val_report

    def report(
        self,
        model_path: Path | str,
        out_dir: Path | str,
        material_id: str = "aluminum_6061",
        machine_path: Optional[Path | str] = None,
        tools_path: Optional[Path | str] = None,
        stock_path: Optional[Path | str] = None,
        config: Optional[ThresholdsConfig] = None,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[Path, Path]:
        """Runs pipeline and generates report.md and report.html."""
        req = EngineRunRequest(
            model_path=Path(model_path),
            out_dir=Path(out_dir),
            material_id=material_id,
            machine_path=Path(machine_path) if machine_path else None,
            tools_path=Path(tools_path) if tools_path else None,
            stock_path=Path(stock_path) if stock_path else None
        )
        res = self.run(req, progress_cb=progress_cb)
        return Path(out_dir) / "report.md", Path(out_dir) / "report.html"

    def run(
        self,
        request: EngineRunRequest,
        progress_cb: Optional[Callable[[str, float], None]] = None
    ) -> EngineRunResult:
        """Executes the full end-to-end CAD-to-CNC optimization pipeline.
        
        Writes all deliverables in request.out_dir:
          model_summary.json
          features.json
          manufacturability.json
          tool_recommendations.json
          operation_plan.json
          toolpaths.json
          validation_report.json
          comparison.json
          program_setup1.nc (ONLY if validation passed)
          model_preview.glb + feature_map.json
          report.md and report.html
          run_log.json
        """
        import importlib.metadata
        import sys
        import yaml

        t0_total = time.perf_counter()
        out_dir = Path(request.out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        stage_timings: List[StageTiming] = []
        warnings_list: List[str] = []

        # Load configs
        config = None
        if request.config_path:
            with open(request.config_path, "r", encoding="utf-8") as f:
                c_data = yaml.safe_load(f)
            config = ThresholdsConfig.model_validate(c_data)
        else:
            config = ThresholdsConfig()

        # 1. Analyze CAD
        t0 = time.perf_counter()
        if progress_cb:
            progress_cb("Stage 1/7: B-Rep CAD parsing and geometry analysis", 0.1)
        summary = self.analyze(request.model_path, out_dir)
        stage_timings.append(StageTiming(stage_name="cad_analysis", duration_s=round(time.perf_counter() - t0, 4)))

        # 2. Features
        t0 = time.perf_counter()
        if progress_cb:
            progress_cb("Stage 2/7: Manufacturing feature recognition", 0.25)
        features_coll = self.features(request.model_path, out_dir, config=config)
        stage_timings.append(StageTiming(stage_name="feature_detection", duration_s=round(time.perf_counter() - t0, 4)))

        # 3. Tools
        t0 = time.perf_counter()
        if progress_cb:
            progress_cb("Stage 3/7: Tool selection and scoring", 0.4)
        recs = self.tools(
            request.model_path, out_dir,
            tools_path=request.tools_path,
            material_id=request.material_id,
            config=config,
            features_coll=features_coll
        )
        stage_timings.append(StageTiming(stage_name="tool_selection", duration_s=round(time.perf_counter() - t0, 4)))

        # 4. Manufacturability Check
        t0 = time.perf_counter()
        if progress_cb:
            progress_cb("Stage 4/7: DFM manufacturability and accessibility check", 0.55)
        dfm_report = self.check(
            request.model_path, out_dir,
            machine_path=request.machine_path,
            tools_path=request.tools_path,
            material_id=request.material_id,
            config=config,
            summary=summary,
            features_coll=features_coll,
            recs=recs
        )
        stage_timings.append(StageTiming(stage_name="manufacturability_check", duration_s=round(time.perf_counter() - t0, 4)))

        # 5. Planning
        t0 = time.perf_counter()
        if progress_cb:
            progress_cb("Stage 5/7: Machining operation sequencing and optimization", 0.7)
        plan_res, comp_res = self.plan(
            request.model_path, out_dir,
            material_id=request.material_id,
            machine_path=request.machine_path,
            tools_path=request.tools_path,
            stock_path=request.stock_path,
            config=config,
            summary=summary,
            features_coll=features_coll,
            recs=recs
        )
        stage_timings.append(StageTiming(stage_name="machining_planning", duration_s=round(time.perf_counter() - t0, 4)))

        # 6. Toolpaths & Validation Gate
        t0 = time.perf_counter()
        if progress_cb:
            progress_cb("Stage 6/7: CAM toolpaths and validation gate", 0.85)
        tp_coll, val_report = self.toolpaths(
            request.model_path, out_dir,
            material_id=request.material_id,
            machine_path=request.machine_path,
            tools_path=request.tools_path,
            stock_path=request.stock_path,
            config=config,
            summary=summary,
            features_coll=features_coll,
            recs=recs,
            dfm_report=dfm_report,
            plan_res=plan_res
        )
        stage_timings.append(StageTiming(stage_name="cam_toolpaths_validation", duration_s=round(time.perf_counter() - t0, 4)))

        # Determine machine name
        machine_name = "Standard 3-Axis VMC"
        if request.machine_path:
            try:
                with open(request.machine_path, "r", encoding="utf-8") as f:
                    m_data = yaml.safe_load(f)
                machine_name = m_data.get("machine", {}).get("name", machine_name)
            except Exception:
                pass

        # Feature counts
        feature_counts = {
            "holes": len(features_coll.holes),
            "pockets": len(features_coll.pockets),
            "slots": len(features_coll.slots),
            "internal_corners": len(features_coll.internal_corners),
            "thin_walls": len(features_coll.thin_walls),
            "planar_faces": len(features_coll.planar_faces)
        }

        # Library provenance
        lib_versions = {
            "python": sys.version.split()[0],
        }
        for pkg in ["cadquery-ocp", "cadquery", "shapely", "pyclipper", "pydantic", "trimesh", "numpy"]:
            try:
                lib_versions[pkg] = importlib.metadata.version(pkg)
            except Exception:
                lib_versions[pkg] = "unknown"

        # 7. Reporting
        t0 = time.perf_counter()
        if progress_cb:
            progress_cb("Stage 7/7: Report generation (Markdown & HTML)", 0.95)

        total_duration = time.perf_counter() - t0_total

        run_log = RunLog(
            schema_version="1.0.0",
            model_path=str(request.model_path),
            material_id=request.material_id,
            machine_id=machine_name,
            total_duration_s=round(total_duration, 4),
            stage_timings=stage_timings,
            feature_counts=feature_counts,
            library_versions=lib_versions,
            warnings=warnings_list,
            success=True
        )

        from cadcnc.reporting.report_builder import write_reports
        md_file, html_file = write_reports(
            out_dir=out_dir,
            summary=summary,
            features=features_coll,
            dfm=dfm_report,
            recs=recs,
            plan=plan_res,
            comp=comp_res,
            val=val_report,
            run_log=run_log,
            material_id=request.material_id,
            machine_name=machine_name
        )
        stage_timings.append(StageTiming(stage_name="reporting", duration_s=round(time.perf_counter() - t0, 4)))

        # Update run_log with final timing and save
        run_log.total_duration_s = round(time.perf_counter() - t0_total, 4)
        run_log_path = out_dir / "run_log.json"
        with open(run_log_path, "w", encoding="utf-8") as f:
            f.write(run_log.model_dump_json(indent=2))

        actual_files = [f.name for f in out_dir.iterdir() if f.is_file()]

        if progress_cb:
            progress_cb("Pipeline execution complete", 1.0)

        return EngineRunResult(
            schema_version="1.0.0",
            success=True,
            summary=summary,
            features=features_coll,
            manufacturability=dfm_report,
            tool_recommendations=recs,
            machining_plan=plan_res,
            comparison=comp_res,
            toolpaths=tp_coll,
            validation=val_report,
            run_log=run_log,
            output_files=actual_files
        )


