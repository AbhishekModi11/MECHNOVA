"""Feature detector registry defining the common plugin interface."""

from typing import Callable, Dict, List, Any
from OCP.TopoDS import TopoDS_Solid

from cadcnc.cad_engine.topology import TopologyGraph
from cadcnc.schemas.config import ThresholdsConfig

class FeatureDetectorPlugin:
    def __init__(self, name: str, detect_func: Callable[[TopologyGraph, TopoDS_Solid, ThresholdsConfig], List[Any]]):
        self.name = name
        self.detect_func = detect_func

    def detect(self, graph: TopologyGraph, solid: TopoDS_Solid, config: ThresholdsConfig) -> List[Any]:
        return self.detect_func(graph, solid, config)

class FeatureRegistry:
    def __init__(self):
        self._detectors: Dict[str, FeatureDetectorPlugin] = {}

    def register(self, name: str, detect_func: Callable[[TopologyGraph, TopoDS_Solid, ThresholdsConfig], List[Any]]):
        self._detectors[name] = FeatureDetectorPlugin(name, detect_func)

    def get(self, name: str) -> FeatureDetectorPlugin:
        return self._detectors[name]

    def run_all(self, graph: TopologyGraph, solid: TopoDS_Solid, config: ThresholdsConfig) -> Dict[str, List[Any]]:
        results = {}
        for name, detector in self._detectors.items():
            results[name] = detector.detect(graph, solid, config)
        return results

global_registry = FeatureRegistry()

# Register core detectors
from cadcnc.feature_detection.hole_detector import detect_holes
from cadcnc.feature_detection.pocket_detector import detect_pockets
from cadcnc.feature_detection.slot_detector import detect_slots
from cadcnc.feature_detection.corner_detector import detect_internal_corners
from cadcnc.feature_detection.wall_detector import detect_thin_walls

global_registry.register("hole_detector", detect_holes)
global_registry.register("pocket_detector", detect_pockets)
global_registry.register("slot_detector", detect_slots)
global_registry.register("corner_detector", detect_internal_corners)
global_registry.register("wall_detector", detect_thin_walls)
