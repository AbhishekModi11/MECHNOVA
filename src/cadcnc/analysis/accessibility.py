"""Feature accessibility analysis and setup grouping."""

from typing import Dict, List, Tuple
from cadcnc.schemas.common import Vector3D
from cadcnc.schemas.config import MachineConfig
from cadcnc.schemas.features import FeaturesCollection

def get_setup_for_vector(
    approach_vector: Vector3D,
    allowed_orientations: List[List[float]],
    tol: float = 0.15
) -> Tuple[bool, str, List[float]]:
    """Checks if an approach vector matches an allowed setup orientation."""
    vx, vy, vz = approach_vector.x, approach_vector.y, approach_vector.z
    # Normalize approach vector
    mag = (vx**2 + vy**2 + vz**2)**0.5
    if mag > 1e-6:
        vx, vy, vz = vx / mag, vy / mag, vz / mag

    for idx, ori in enumerate(allowed_orientations):
        ox, oy, oz = ori[0], ori[1], ori[2]
        dot = vx * ox + vy * oy + vz * oz
        if dot > (1.0 - tol):
            return True, f"setup_{idx + 1}", ori

    return False, "inaccessible", [0.0, 0.0, 0.0]

def analyze_feature_accessibility(
    features: FeaturesCollection,
    machine_config: MachineConfig
) -> Dict[str, Tuple[bool, str, List[float]]]:
    """Evaluates accessibility and assigns setup orientation for each feature."""
    allowed = machine_config.machine.allowed_setup_orientations
    results: Dict[str, Tuple[bool, str, List[float]]] = {}

    # Holes: tool approaches along opposite of hole axis (pointing into opening)
    for hole in features.holes:
        approach = Vector3D(x=-hole.axis.x, y=-hole.axis.y, z=-hole.axis.z)
        accessible, setup_id, ori = get_setup_for_vector(approach, allowed)
        results[hole.id] = (accessible, setup_id, ori)

    # Pockets: tool approaches along floor normal
    for pocket in features.pockets:
        approach = pocket.floor_normal
        accessible, setup_id, ori = get_setup_for_vector(approach, allowed)
        results[pocket.id] = (accessible, setup_id, ori)

    # Slots: tool approaches along +Z for closed slots
    for slot in features.slots:
        approach = Vector3D(x=0.0, y=0.0, z=1.0)
        accessible, setup_id, ori = get_setup_for_vector(approach, allowed)
        results[slot.id] = (accessible, setup_id, ori)

    return results
