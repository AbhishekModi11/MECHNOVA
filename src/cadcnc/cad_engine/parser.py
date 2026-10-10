"""STEP/STP file parser using Open CASCADE Technology (OCP)."""

import time
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from OCP.STEPControl import STEPControl_Reader  # type: ignore
    from OCP.IFSelect import IFSelect_RetDone  # type: ignore
    from OCP.TopExp import TopExp_Explorer  # type: ignore
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX  # type: ignore
    from OCP.TopoDS import TopoDS, TopoDS_Shape, TopoDS_Solid  # type: ignore
except ImportError as err:
    raise ImportError(
        "Failed to import Open CASCADE Technology (OCP). "
        "Please ensure the Python 3.11 virtual environment (.venv) is selected/activated "
        "where 'cadquery-ocp' is installed."
    ) from err

class STEPParseError(Exception):
    """Raised when a STEP file cannot be parsed or contains no valid solids."""
    pass

class CADModel:
    """Encapsulates a loaded STEP model and its top-level OCCT shapes."""
    def __init__(
        self,
        file_path: Path,
        shape: TopoDS_Shape,
        solids: List[TopoDS_Solid],
        unit: str,
        load_time_s: float
    ):
        self.file_path = file_path
        self.shape = shape
        self.solids = solids
        self.unit = unit
        self.load_time_s = load_time_s
        self.primary_solid: TopoDS_Solid = solids[0]

def detect_step_unit(file_path: Path) -> str:
    """Inspects STEP header tokens to determine measurement unit."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            header_sample = f.read(16384)
            if "INCH" in header_sample:
                return "in"
            if "METRE" in header_sample or "MILLI" in header_sample:
                return "mm"
    except Exception:
        pass
    return "mm"

def load_step_model(file_path: Path | str) -> CADModel:
    """Loads a STEP/STP file, validates solids, and returns a CADModel instance.
    
    Raises:
        STEPParseError: If file is missing, empty, corrupt, or contains no 3D solids.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise STEPParseError(f"File not found: {path}")
    
    if path.stat().st_size == 0:
        raise STEPParseError(f"STEP file is empty (0 bytes): {path}")

    start_time = time.perf_counter()
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise STEPParseError(f"Failed to read STEP file (OCCT status code: {status}): {path}")

    num_roots = reader.TransferRoots()
    if num_roots == 0:
        raise STEPParseError(f"No valid geometric roots transferred from STEP file: {path}")

    shape = reader.OneShape()
    if shape.IsNull():
        raise STEPParseError(f"Resulting shape is null from STEP file: {path}")

    # Explore and collect all solids
    solids: List[TopoDS_Solid] = []
    exp_solid = TopExp_Explorer(shape, TopAbs_SOLID)
    while exp_solid.More():
        curr_shape = exp_solid.Current()
        solids.append(TopoDS.Solid_s(curr_shape))
        exp_solid.Next()

    if not solids:
        raise STEPParseError(
            f"Model in '{path.name}' contains no 3D solid geometry (only wires, surfaces, or open shells). "
            f"CNC machining requires a closed 3D solid."
        )

    load_time_s = time.perf_counter() - start_time
    unit = detect_step_unit(path)

    return CADModel(
        file_path=path,
        shape=shape,
        solids=solids,
        unit=unit,
        load_time_s=load_time_s
    )
