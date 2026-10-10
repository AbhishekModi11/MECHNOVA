"""CAM Operation definitions and geometric toolpath generation."""

import math
from typing import List, Tuple
from shapely.geometry import Polygon, MultiPolygon

from cadcnc.schemas.common import Point3D
from cadcnc.schemas.cam import MoveType, ToolpathMove

def generate_facing_toolpath_moves(
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    z_cut: float,
    tool_diameter_mm: float,
    feed_mm_min: float,
    clearance_z: float = 5.0,
    stepover_frac: float = 0.6
) -> List[ToolpathMove]:
    """Generates zig-zag raster toolpath moves for top surface face milling."""
    moves: List[ToolpathMove] = []
    stepover = tool_diameter_mm * stepover_frac
    y_current = y_min + (tool_diameter_mm * 0.4)
    direction_forward = True

    # Start above stock at clearance Z
    last_p = Point3D(x=x_min - tool_diameter_mm, y=y_current, z=z_cut + clearance_z)

    while y_current <= (y_max + tool_diameter_mm * 0.2):
        if direction_forward:
            p_start = Point3D(x=x_min - tool_diameter_mm, y=y_current, z=z_cut + clearance_z)
            p_plunge = Point3D(x=x_min - tool_diameter_mm, y=y_current, z=z_cut)
            p_cut = Point3D(x=x_max + tool_diameter_mm, y=y_current, z=z_cut)
        else:
            p_start = Point3D(x=x_max + tool_diameter_mm, y=y_current, z=z_cut + clearance_z)
            p_plunge = Point3D(x=x_max + tool_diameter_mm, y=y_current, z=z_cut)
            p_cut = Point3D(x=x_min - tool_diameter_mm, y=y_current, z=z_cut)

        # Rapid to start
        moves.append(ToolpathMove(
            move_type=MoveType.RAPID,
            start=last_p, end=p_start,
            feed_mm_min=10000.0,
            length_mm=round(math.dist(last_p.to_tuple(), p_start.to_tuple()), 2)
        ))
        # Plunge to cut level
        moves.append(ToolpathMove(
            move_type=MoveType.PLUNGE,
            start=p_start, end=p_plunge,
            feed_mm_min=feed_mm_min * 0.4,
            length_mm=round(clearance_z, 2)
        ))
        # Cutting pass
        moves.append(ToolpathMove(
            move_type=MoveType.CUT,
            start=p_plunge, end=p_cut,
            feed_mm_min=feed_mm_min,
            length_mm=round(math.dist(p_plunge.to_tuple(), p_cut.to_tuple()), 2)
        ))
        # Retract to clearance Z
        p_retract = Point3D(x=p_cut.x, y=p_cut.y, z=z_cut + clearance_z)
        moves.append(ToolpathMove(
            move_type=MoveType.RETRACT,
            start=p_cut, end=p_retract,
            feed_mm_min=10000.0,
            length_mm=round(clearance_z, 2)
        ))

        last_p = p_retract
        y_current += stepover
        direction_forward = not direction_forward

    return moves

def generate_drilling_toolpath_moves(
    center: Point3D,
    depth_mm: float,
    z_top: float,
    feed_mm_min: float,
    clearance_z: float = 5.0,
    is_peck: bool = False,
    peck_increment: float = 4.0
) -> List[ToolpathMove]:
    """Generates drill plunge and peck cycle toolpath moves."""
    moves: List[ToolpathMove] = []
    p_safe = Point3D(x=center.x, y=center.y, z=z_top + clearance_z)

    if not is_peck:
        p_bottom = Point3D(x=center.x, y=center.y, z=z_top - depth_mm)
        moves.append(ToolpathMove(
            move_type=MoveType.PLUNGE,
            start=p_safe, end=p_bottom,
            feed_mm_min=feed_mm_min,
            length_mm=round(depth_mm + clearance_z, 2)
        ))
        moves.append(ToolpathMove(
            move_type=MoveType.RETRACT,
            start=p_bottom, end=p_safe,
            feed_mm_min=10000.0,
            length_mm=round(depth_mm + clearance_z, 2)
        ))
    else:
        # Peck drilling simulation
        curr_z = z_top
        target_z = z_top - depth_mm
        while curr_z > target_z:
            next_z = max(target_z, curr_z - peck_increment)
            p_start = Point3D(x=center.x, y=center.y, z=curr_z)
            p_peck = Point3D(x=center.x, y=center.y, z=next_z)
            moves.append(ToolpathMove(
                move_type=MoveType.PLUNGE,
                start=p_start, end=p_peck,
                feed_mm_min=feed_mm_min,
                length_mm=round(curr_z - next_z, 2)
            ))
            # Rapid retract to clear chip
            moves.append(ToolpathMove(
                move_type=MoveType.RETRACT,
                start=p_peck, end=p_safe,
                feed_mm_min=10000.0,
                length_mm=round(z_top + clearance_z - next_z, 2)
            ))
            curr_z = next_z

    return moves

def generate_pocket_clearing_moves(
    corners_2d: List[Tuple[float, float]],
    z_top: float,
    depth_mm: float,
    tool_diameter_mm: float,
    feed_mm_min: float,
    stepdown_mm: float = 3.0,
    stepover_frac: float = 0.5,
    clearance_z: float = 5.0
) -> List[ToolpathMove]:
    """Generates 2D concentric offset clearing passes down through Z levels."""
    moves: List[ToolpathMove] = []
    poly = Polygon(corners_2d)
    if not poly.is_valid or poly.is_empty:
        return []

    tool_r = tool_diameter_mm * 0.5
    stepover = tool_diameter_mm * stepover_frac
    z_target = z_top - depth_mm
    current_z = z_top

    # Step down in depth layers
    while current_z > z_target:
        current_z = max(z_target, current_z - stepdown_mm)
        # Compute inward offsets
        inset = poly.buffer(-tool_r)
        while not inset.is_empty and inset.area > 0.05:
            # Extract ring coordinates
            if isinstance(inset, MultiPolygon):
                rings = [p.exterior.coords for p in inset.geoms]
            else:
                rings = [inset.exterior.coords]

            for ring in rings:
                coords = list(ring)
                if len(coords) < 2:
                    continue
                # Plunge at first vertex
                p_first = Point3D(x=coords[0][0], y=coords[0][1], z=current_z)
                p_safe = Point3D(x=coords[0][0], y=coords[0][1], z=z_top + clearance_z)
                moves.append(ToolpathMove(
                    move_type=MoveType.PLUNGE,
                    start=p_safe, end=p_first,
                    feed_mm_min=feed_mm_min * 0.3,
                    length_mm=round(z_top + clearance_z - current_z, 2)
                ))
                # Cutting contour
                for k in range(len(coords) - 1):
                    p_from = Point3D(x=coords[k][0], y=coords[k][1], z=current_z)
                    p_to = Point3D(x=coords[k + 1][0], y=coords[k + 1][1], z=current_z)
                    moves.append(ToolpathMove(
                        move_type=MoveType.CUT,
                        start=p_from, end=p_to,
                        feed_mm_min=feed_mm_min,
                        length_mm=round(math.dist(p_from.to_tuple(), p_to.to_tuple()), 2)
                    ))
                # Retract to safe Z
                p_last = Point3D(x=coords[-1][0], y=coords[-1][1], z=current_z)
                moves.append(ToolpathMove(
                    move_type=MoveType.RETRACT,
                    start=p_last, end=p_safe,
                    feed_mm_min=10000.0,
                    length_mm=round(z_top + clearance_z - current_z, 2)
                ))

            inset = inset.buffer(-stepover)

    return moves
