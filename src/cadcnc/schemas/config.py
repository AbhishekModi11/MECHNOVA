"""Configuration schemas for machines, materials, tools, thresholds, and stock."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Thresholds(BaseModel):
    min_wall_thickness_mm: float = 1.5
    slot_aspect_ratio_min: float = 2.5
    min_feature_size_mm: float = 1.0
    peck_drill_ratio_threshold: float = 3.0
    safe_clearance_z_mm: float = 5.0
    rapid_traverse_z_mm: float = 10.0
    retract_z_mm: float = 2.0
    default_stepdown_fraction: float = 0.5
    default_stepover_fraction: float = 0.6
    finish_stock_allowance_mm: float = 0.3
    stock_allowance_xy_mm: float = 4.0
    stock_allowance_z_top_mm: float = 2.0
    stock_allowance_z_bottom_mm: float = 5.0
    uncertain_confidence_threshold: float = 0.70

class ThresholdsConfig(BaseModel):
    schema_version: str = "1.0.0"
    thresholds: Thresholds = Field(default_factory=Thresholds)

class TravelLimits(BaseModel):
    x_min: float = -300.0
    x_max: float = 300.0
    y_min: float = -200.0
    y_max: float = 200.0
    z_min: float = -150.0
    z_max: float = 150.0

class Machine(BaseModel):
    id: str = "VMC-3AXIS-STD"
    name: str = "Standard 3-Axis Vertical Machining Center"
    axes: int = 3
    indexed_3plus2: bool = True
    travel_limits_mm: TravelLimits = Field(default_factory=TravelLimits)
    max_spindle_rpm: float = 12000.0
    max_feed_mm_min: float = 5000.0
    rapid_rate_mm_min: float = 10000.0
    tool_changer_capacity: int = 20
    tool_change_time_s: float = 8.0
    setup_change_time_s: float = 300.0
    controller_flavor: str = "fanuc"
    allowed_setup_orientations: List[List[float]] = Field(default_factory=lambda: [
        [0.0, 0.0, 1.0],
        [0.0, 0.0, -1.0],
        [1.0, 0.0, 0.0],
        [-1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, -1.0, 0.0]
    ])
    workholding_assumption: str = "Standard precision machine vise clamping bottom 5mm of stock."

class MachineConfig(BaseModel):
    schema_version: str = "1.0.0"
    machine: Machine = Field(default_factory=Machine)

class Stock(BaseModel):
    mode: str = "bounding_box_allowance"
    allowance_x_mm: float = 4.0
    allowance_y_mm: float = 4.0
    allowance_z_top_mm: float = 2.0
    allowance_z_bottom_mm: float = 5.0
    material_id: str = "aluminum_6061"

class StockConfig(BaseModel):
    schema_version: str = "1.0.0"
    stock: Stock = Field(default_factory=Stock)

class CuttingData(BaseModel):
    cutting_speed_m_min: float
    chip_load_drill_mm_flute: float
    chip_load_mill_mm_tooth: float
    plunge_factor: float = 0.4

class MaterialItem(BaseModel):
    id: str
    name: str
    category: str
    hardness_hb: float
    density_g_cm3: float
    machinability_rating: float
    cutting_data: Dict[str, CuttingData]
    source: str
    data_quality: str

class MaterialsDatabase(BaseModel):
    schema_version: str = "1.0.0"
    disclaimer: str
    materials: Dict[str, MaterialItem]

class ToolItem(BaseModel):
    id: str
    name: str
    type: str  # drill, flat_end_mill, ball_end_mill, face_mill
    diameter_mm: float
    reach_mm: float
    flute_length_mm: float
    tool_material: str  # carbide, hss
    flutes: int
    point_angle_deg: Optional[float] = None
    compatible_materials: List[str]
    operations: List[str]
    max_rpm: float

class ToolsDatabase(BaseModel):
    schema_version: str = "1.0.0"
    data_notice: str
    tools: List[ToolItem]
