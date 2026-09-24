import json

import pytest

from app import db, seed
from app.services.paint_service import PaintService


@pytest.fixture
def svc(tmp_path, monkeypatch):
    # 每个用例独立的临时库，init_db 写入种子房间/洞口/设置
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    seed.init_db()
    with PaintService() as s:
        yield s


def _preview_fields(resp):
    """试算回包里除路由信封（run_id/room_id）外的钉选结果字段。"""
    return {k: v for k, v in resp.items() if k not in ("run_id", "room_id")}


def _list_summary_liters(svc):
    """复刻前端 BatchHistory.totalOf：取最新一条列表摘要的合计升数。"""
    row = svc.history(1)[0]
    r = json.loads(row["result_json"])
    if r.get("total_liters") is not None:
        return r["total_liters"]
    if r.get("wall_liters") is not None and r.get("touch_up_liters") is not None:
        return round(float(r["wall_liters"]) + float(r["touch_up_liters"]), 2)
    return r["liters"]


@pytest.mark.parametrize("mode,extra", [
    ("merge", {}),
    ("separate", {"touch_up_coverage": 6}),
])
def test_persisted_run_pinned_to_preview(svc, mode, extra):
    kwargs = {"touch_ups": [{"w": 2, "h": 3}], "touch_up_mode": mode, **extra}

    preview = svc.estimate(1, persist=False, **kwargs)
    saved = svc.estimate(1, persist=True, **kwargs)
    assert saved["run_id"] is not None

    # 按号打开：result_json 与试算回包逐字段一致（含补刷拆分，不被剥离/重算）
    detail = svc.history_run(saved["run_id"])
    assert detail["result_json"] == _preview_fields(preview)

    # 列表摘要的合计升数与试算回包一致
    assert _list_summary_liters(svc) == preview["total_liters"]
    assert detail["result_json"]["total_liters"] == preview["total_liters"]


def test_persisted_merge_keeps_patch_out_of_wall_net(svc):
    # merge 模式下写入的净面积是墙面净面积，补刷面积单列保留，升数含补刷加计
    saved = svc.estimate(1, persist=True, touch_ups=[{"w": 2, "h": 3}],
                         touch_up_mode="merge")
    r = svc.history_run(saved["run_id"])["result_json"]
    assert r["net_m2"] == 46.41          # 墙面净面积，未把 6m² 补刷并进去
    assert r["touch_up_m2"] == 6
    assert r["touch_ups"] == [{"w": 2, "h": 3}]
    assert r["liters"] == r["wall_liters"] == r["total_liters"] == 13.1
    assert r["touch_up_liters"] == 0.0


def test_persisted_separate_keeps_split_liters(svc):
    saved = svc.estimate(1, persist=True, touch_ups=[{"w": 2, "h": 3}],
                         touch_up_mode="separate", touch_up_coverage=6)
    r = svc.history_run(saved["run_id"])["result_json"]
    assert r["net_m2"] == 46.41
    assert r["wall_liters"] == 11.6
    assert r["touch_up_liters"] == 2.0
    assert r["liters"] == 11.6
    assert r["total_liters"] == 13.6


def test_negative_touchup_rejected_and_not_written(svc):
    before = len(svc.history(1000))
    with pytest.raises(ValueError):
        svc.estimate(1, persist=True, touch_ups=[{"w": -1, "h": 2}])
    # 拒绝发生在 insert 之前，不新增任何记录
    assert len(svc.history(1000)) == before


def test_zero_touchup_rejected_and_not_written(svc):
    before = len(svc.history(1000))
    with pytest.raises(ValueError):
        svc.estimate(1, persist=True, touch_ups=[{"w": 2, "h": 0}])
    assert len(svc.history(1000)) == before


def test_removing_blocks_does_not_rewrite_old_run(svc):
    first = svc.estimate(1, persist=True, touch_ups=[{"w": 2, "h": 3}],
                         touch_up_mode="merge")
    pinned = dict(svc.history_run(first["run_id"])["result_json"])

    # 之后删掉补刷块再估一笔，旧条钉选内容不得被改写
    second = svc.estimate(1, persist=True, touch_ups=[])
    assert second["run_id"] != first["run_id"]
    assert svc.history_run(first["run_id"])["result_json"] == pinned
    assert svc.history_run(first["run_id"])["result_json"]["total_liters"] == 13.1


def test_persist_without_touchups_matches_base(svc):
    # 无补刷：写入结果与改造前同参一致，不附带任何补刷字段
    saved = svc.estimate(1, persist=True)
    r = svc.history_run(saved["run_id"])["result_json"]
    assert set(r) == {"gross_m2", "openings_m2", "net_m2", "liters", "coats", "coverage"}
    assert r["liters"] == 11.6
    assert _list_summary_liters(svc) == 11.6


def test_input_json_pins_touchup_params(svc):
    saved = svc.estimate(1, persist=True, touch_ups=[{"w": 2, "h": 3}],
                         touch_up_mode="separate", touch_up_coverage=6)
    inp = svc.history_run(saved["run_id"])["input_json"]
    assert inp["touch_ups"] == [{"w": 2, "h": 3}]
    assert inp["touch_up_mode"] == "separate"
    assert inp["touch_up_coverage"] == 6.0
