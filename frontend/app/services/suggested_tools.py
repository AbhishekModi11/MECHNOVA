"""
Proxy / direct access to MECHNOVA Suggested Tools & Machining Engine.
"""
from cad_service.suggested_tools import (
    suggest_tools_for_project,
    generate_gcode_preview,
    MATERIAL_CATALOG,
    STANDARD_FACE_MILLS,
    STANDARD_END_MILL_DIAMETERS
)

__all__ = [
    "suggest_tools_for_project",
    "generate_gcode_preview",
    "MATERIAL_CATALOG",
    "STANDARD_FACE_MILLS",
    "STANDARD_END_MILL_DIAMETERS"
]
