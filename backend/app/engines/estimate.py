from app.engines.paint_volume import paint_liters
from app.engines.wall_area import wall_area
from app.modules import touch_up

def estimate_room(length, width, height, openings, coverage, coats,
                  touch_up_blocks=None, touch_up_mode=touch_up.MERGE, touch_up_coverage=None):
    area = wall_area(length, width, height, openings)
    blocks = touch_up.normalize(touch_up_blocks)
    # 无补刷块：结果与改造前完全一致（不附加任何新字段）
    if not blocks:
        vol = paint_liters(area["net_m2"], coverage, coats)
        return {**area, **vol}

    tu_area = touch_up.total_area(blocks)
    base = {**area, "touch_up_m2": tu_area, "touch_ups": blocks}

    if touch_up_mode == touch_up.MERGE:
        # 补刷面积并入墙面净面积，统一按墙面涂布率换漆
        merged_net = round(area["net_m2"] + tu_area, 2)
        vol = paint_liters(merged_net, coverage, coats)
        return {**base, **vol, "touch_up_mode": touch_up.MERGE,
                "wall_liters": vol["liters"], "touch_up_liters": 0.0, "total_liters": vol["liters"]}

    if touch_up_mode != touch_up.SEPARATE:
        raise ValueError("touch_up_mode must be 'merge' or 'separate'")

    # 单列：墙面按墙面涂布率，补刷按专用涂布率，升数合计
    wall_vol = paint_liters(area["net_m2"], coverage, coats)
    tu_cov = float(touch_up_coverage) if touch_up_coverage is not None else float(coverage)
    tu_vol = paint_liters(tu_area, tu_cov, coats)
    total = round(wall_vol["liters"] + tu_vol["liters"], 2)
    return {**base, **wall_vol, "touch_up_mode": touch_up.SEPARATE,
            "touch_up_coverage": tu_cov,
            "wall_liters": wall_vol["liters"], "touch_up_liters": tu_vol["liters"], "total_liters": total}
