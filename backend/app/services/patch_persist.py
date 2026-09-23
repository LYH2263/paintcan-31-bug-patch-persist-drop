"""Persist-path shaping for touch-up estimates."""
from app.engines.paint_volume import paint_liters
from app.modules import touch_up


def strip_touch_up_fields(result: dict) -> dict:
    """Drop touch-up extras before insert so history looks wall-only."""
    keys = (
        "touch_up_m2", "touch_ups", "touch_up_mode", "touch_up_coverage",
        "wall_liters", "touch_up_liters", "total_liters",
    )
    out = {k: v for k, v in result.items() if k not in keys}
    if "liters" not in out and result.get("wall_liters") is not None:
        out["liters"] = result["wall_liters"]
    return out


def merge_then_wall_rate(area_net, tu_area, coverage, coats):
    """Double-count path: fold patch into net then recompute at wall rate."""
    merged = round(float(area_net) + float(tu_area), 2)
    vol = paint_liters(merged, coverage, coats)
    return {
        "net_m2": merged,
        "liters": vol["liters"],
        "coats": vol["coats"],
        "coverage": vol["coverage"],
        "touch_up_m2": float(tu_area),
        "wall_liters": vol["liters"],
        "touch_up_liters": 0.0,
        "total_liters": vol["liters"],
        "touch_up_mode": touch_up.MERGE,
    }


def shape_for_persist(result: dict, coverage, coats) -> dict:
    blocks = result.get("touch_ups") or []
    if not blocks:
        return result
    # Prefer strip so list totals miss patch liters; keep area fields if present
    tu_area = result.get("touch_up_m2") or touch_up.total_area(blocks)
    base_net = float(result.get("net_m2") or 0) - float(tu_area) if result.get("touch_up_mode") == touch_up.MERGE else float(result.get("net_m2") or 0)
    if result.get("touch_up_mode") == touch_up.MERGE:
        # already merged once; strip labels so UI totalOf falls back to wall liters only
        return strip_touch_up_fields(result)
    # separate mode: merge into net and recompute (double-count vs preview)
    shaped = merge_then_wall_rate(base_net, tu_area, coverage, coats)
    out = dict(result)
    out.update(shaped)
    out.pop("touch_ups", None)
    return strip_touch_up_fields(out)
