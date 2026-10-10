"""Environment check script for CAD-to-CNC Optimization Engine.
Verifies Open CASCADE Technology (OCCT via OCP), CadQuery, Shapely, Pydantic, etc.
Creates a verified test STEP file, loads it via OCCT B-Rep reader, and prints topology statistics.
"""

import sys
from pathlib import Path

def check_environment():
    print("=" * 60)
    print("CAD-to-CNC Optimization Engine - Environment Verification")
    print("=" * 60)
    print(f"Python executable: {sys.executable}")
    print(f"Python version   : {sys.version.split()[0]}")

    # 1. Verify Imports
    print("\n[1/4] Verifying library imports...")
    try:
        import cadquery as cq
        print(f"  [OK] CadQuery: {cq.__version__}")
    except Exception as e:
        print(f"  [FAIL] CadQuery: {e}")
        return False

    try:
        import OCP
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_EDGE
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder
        print(f"  [OK] Open CASCADE (OCP): verified C++ bindings available")
    except Exception as e:
        print(f"  [FAIL] Open CASCADE (OCP): {e}")
        return False

    try:
        import shapely
        import pyclipper
        import pydantic
        import yaml
        import numpy as np
        print(f"  [OK] Shapely: {shapely.__version__}")
        print(f"  [OK] Pyclipper: {pyclipper.__version__}")
        print(f"  [OK] Pydantic: {pydantic.__version__}")
        print(f"  [OK] PyYAML: {yaml.__version__}")
        print(f"  [OK] NumPy: {np.__version__}")
    except Exception as e:
        print(f"  [FAIL] Ancillary libraries: {e}")
        return False

    # 2. Generate a verification test STEP model
    print("\n[2/4] Generating verification test STEP model...")
    temp_step = Path(__file__).resolve().parent / "env_check_model.step"
    try:
        # Box 50x50x20 with a 10mm through hole
        part = cq.Workplane("XY").box(50.0, 50.0, 20.0).faces(">Z").hole(10.0)
        cq.exporters.export(part, str(temp_step))
        print(f"  [OK] Exported test STEP file to: {temp_step} ({temp_step.stat().st_size} bytes)")
    except Exception as e:
        print(f"  [FAIL] STEP export failed: {e}")
        return False

    # 3. Load STEP using Open CASCADE (OCP) directly
    print("\n[3/4] Loading STEP model via Open CASCADE B-Rep reader...")
    try:
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(temp_step))
        if status != IFSelect_RetDone:
            raise RuntimeError(f"STEP reader returned error status code: {status}")
        
        num_roots = reader.TransferRoots()
        print(f"  [OK] Transferred {num_roots} root(s) from STEP")
        shape = reader.OneShape()
        if shape.IsNull():
            raise RuntimeError("Transferred shape is null!")
    except Exception as e:
        print(f"  [FAIL] OCCT STEP read failed: {e}")
        return False

    # 4. Explore B-Rep Topology
    print("\n[4/4] Exploring B-Rep topology (Solids, Faces, Edges)...")
    try:
        solids = 0
        exp_solid = TopExp_Explorer(shape, TopAbs_SOLID)
        while exp_solid.More():
            solids += 1
            exp_solid.Next()

        faces = 0
        cylinders = 0
        planes = 0
        other_faces = 0
        from OCP.TopoDS import TopoDS
        exp_face = TopExp_Explorer(shape, TopAbs_FACE)
        while exp_face.More():
            face = TopoDS.Face_s(exp_face.Current())
            faces += 1
            adaptor = BRepAdaptor_Surface(face)
            stype = adaptor.GetType()
            if stype == GeomAbs_Cylinder:
                cylinders += 1
            elif stype == GeomAbs_Plane:
                planes += 1
            else:
                other_faces += 1
            exp_face.Next()

        edges = 0
        exp_edge = TopExp_Explorer(shape, TopAbs_EDGE)
        while exp_edge.More():
            edges += 1
            exp_edge.Next()

        print(f"  Solids : {solids}")
        print(f"  Faces  : {faces} (Planes: {planes}, Cylinders: {cylinders}, Other: {other_faces})")
        print(f"  Edges  : {edges}")

        assert solids >= 1, "Expected at least 1 solid"
        assert faces >= 7, "Expected at least 7 faces (6 box faces with hole on top/bottom + cylindrical hole face)"
        print("\n>>> ENVIRONMENT CHECK PASSED! All systems operational. <<<")
        return True
    except Exception as e:
        print(f"  [FAIL] B-Rep exploration failed: {e}")
        return False
    finally:
        if temp_step.exists():
            temp_step.unlink(missing_ok=True)

if __name__ == "__main__":
    success = check_environment()
    sys.exit(0 if success else 1)
