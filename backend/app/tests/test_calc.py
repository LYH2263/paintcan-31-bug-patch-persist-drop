import pytest
from app.engines.estimate import estimate_room
from app.engines.paint_volume import paint_liters
from app.engines.wall_area import wall_area

def test_living_room_net():
    a = wall_area(5, 4, 2.8, [{"w": 0.9, "h": 2.1}, {"w": 1.5, "h": 1.4}])
    assert a["gross_m2"] == 50.4
    assert a["net_m2"] == 46.41

def test_liters_two_coats():
    v = paint_liters(46.41, 8, 2)
    assert v["liters"] == 11.6

def test_estimate_combined():
    e = estimate_room(5, 4, 2.8, [{"w": 0.9, "h": 2.1}, {"w": 1.5, "h": 1.4}], 8, 2)
    assert e["liters"] == 11.6

def test_bad_coverage():
    with pytest.raises(ValueError):
        paint_liters(10, 0, 2)

def test_no_touchups_identical_to_base():
    # 无补刷块时结果与改造前同房同参一致（键集合也不变）
    base = estimate_room(5, 4, 2.8, [{"w": 0.9, "h": 2.1}], 8, 2)
    m = estimate_room(5, 4, 2.8, [{"w": 0.9, "h": 2.1}], 8, 2,
                      touch_up_blocks=[], touch_up_mode="separate", touch_up_coverage=5)
    assert m == base
    assert set(m) == {"gross_m2", "openings_m2", "net_m2", "liters", "coats", "coverage"}

def test_touchup_merge():
    # 净 46.41 + 补刷 2*3=6 → 52.41 m²，2 遍 / 8 → 13.1 L
    e = estimate_room(5, 4, 2.8, [{"w": 0.9, "h": 2.1}, {"w": 1.5, "h": 1.4}], 8, 2,
                      touch_up_blocks=[{"w": 2, "h": 3}], touch_up_mode="merge")
    assert e["touch_up_m2"] == 6
    assert e["wall_liters"] == e["total_liters"] == e["liters"] == 13.1
    assert e["touch_up_liters"] == 0.0
    assert e["touch_ups"] == [{"w": 2, "h": 3}]

def test_touchup_separate():
    # 墙面 46.41*2/8 = 11.60；补刷 6*2/6 = 2.0；合计 13.6
    e = estimate_room(5, 4, 2.8, [{"w": 0.9, "h": 2.1}, {"w": 1.5, "h": 1.4}], 8, 2,
                      touch_up_blocks=[{"w": 2, "h": 3}], touch_up_mode="separate",
                      touch_up_coverage=6)
    assert e["touch_up_m2"] == 6
    assert e["wall_liters"] == 11.6
    assert e["touch_up_liters"] == 2.0
    assert e["total_liters"] == 13.6
    assert e["liters"] == 11.6  # 墙面升数仍为 liters 字段

def test_touchup_separate_multiple_blocks():
    e = estimate_room(4, 3, 2.8, [], 8, 2,
                      touch_up_blocks=[{"w": 1, "h": 1}, {"w": 2, "h": 2}],
                      touch_up_mode="separate", touch_up_coverage=5)
    assert e["touch_up_m2"] == 5
    # 墙面净 = 2*(4+3)*2.8 = 39.2 → 9.8；补刷 5*2/5 = 2.0
    assert e["wall_liters"] == 9.8
    assert e["touch_up_liters"] == 2.0
    assert e["total_liters"] == 11.8

def test_touchup_non_positive_or_non_int_rejected():
    from app.modules.touch_up import normalize
    for bad in [{"w": 0, "h": 2}, {"w": 2, "h": 0}, {"w": -1, "h": 2},
                {"w": 1.5, "h": 2}, {"w": "2", "h": 2}, {"w": True, "h": 2}]:
        with pytest.raises(ValueError):
            normalize([bad])
    with pytest.raises(ValueError):
        estimate_room(5, 4, 2.8, [], 8, 2, touch_up_blocks=[{"w": 1.5, "h": 2}])

def test_bad_touchup_mode():
    with pytest.raises(ValueError):
        estimate_room(5, 4, 2.8, [], 8, 2,
                      touch_up_blocks=[{"w": 1, "h": 1}], touch_up_mode="sideways")
