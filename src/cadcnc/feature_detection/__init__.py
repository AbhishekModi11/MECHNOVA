"""Feature detection package exposing all core manufacturing feature detectors."""

from cadcnc.feature_detection.face_classifier import classify_all_faces, ClassifiedFaces
from cadcnc.feature_detection.hole_detector import detect_holes
from cadcnc.feature_detection.pocket_detector import detect_pockets
from cadcnc.feature_detection.slot_detector import detect_slots
from cadcnc.feature_detection.corner_detector import detect_internal_corners
from cadcnc.feature_detection.wall_detector import detect_thin_walls
from cadcnc.feature_detection.registry import global_registry, FeatureRegistry

__all__ = [
    "classify_all_faces", "ClassifiedFaces",
    "detect_holes", "detect_pockets", "detect_slots",
    "detect_internal_corners", "detect_thin_walls",
    "global_registry", "FeatureRegistry"
]
