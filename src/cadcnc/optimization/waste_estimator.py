"""Stock dimensions, material removal, and stock utilization estimation."""

from dataclasses import dataclass
from cadcnc.schemas.common import BoundingBox3D
from cadcnc.schemas.config import StockConfig

@dataclass
class StockEstimationResult:
    stock_dx_mm: float
    stock_dy_mm: float
    stock_dz_mm: float
    stock_volume_mm3: float
    part_volume_mm3: float
    removed_volume_mm3: float
    stock_utilization_percent: float
    waste_reduction_percent: float

def estimate_stock_and_waste(
    part_bbox: BoundingBox3D,
    part_volume_mm3: float,
    stock_config: StockConfig
) -> StockEstimationResult:
    """Computes raw stock block volume, total chip removal, and utilization ratio."""
    allowance_x = stock_config.stock.allowance_x_mm
    allowance_y = stock_config.stock.allowance_y_mm
    allowance_z_top = stock_config.stock.allowance_z_top_mm
    allowance_z_bot = stock_config.stock.allowance_z_bottom_mm

    stock_dx = part_bbox.dx + (2.0 * allowance_x)
    stock_dy = part_bbox.dy + (2.0 * allowance_y)
    stock_dz = part_bbox.dz + allowance_z_top + allowance_z_bot

    stock_vol = stock_dx * stock_dy * stock_dz
    removed_vol = max(0.0, stock_vol - part_volume_mm3)

    utilization_pct = 0.0
    if stock_vol > 0.0:
        utilization_pct = (part_volume_mm3 / stock_vol) * 100.0

    # In MVP Phase 1 without nesting/stock geometry resizing, report 0.0% for waste reduction
    waste_reduction_pct = 0.0

    return StockEstimationResult(
        stock_dx_mm=round(stock_dx, 2),
        stock_dy_mm=round(stock_dy, 2),
        stock_dz_mm=round(stock_dz, 2),
        stock_volume_mm3=round(stock_vol, 2),
        part_volume_mm3=round(part_volume_mm3, 2),
        removed_volume_mm3=round(removed_vol, 2),
        stock_utilization_percent=round(utilization_pct, 1),
        waste_reduction_percent=round(waste_reduction_pct, 1)
    )
