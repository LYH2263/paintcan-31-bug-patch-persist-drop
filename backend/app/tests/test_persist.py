"""persist 钉选一致性回归：试算回包、历史列表摘要、按号详情必须是同一套含补刷的升数。"""
import os
import tempfile

# 必须在 import app.db 之前指向临时目录，避免污染/依赖真实库
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="paintcan-test-")

import pytest

from app import seed
from app.services.paint_service import PaintService

seed.init_db()

TOUCH_KEYS = (
    "gross_m2", "openings_m2", "net_m2", "liters", "coats", "coverage",
    "touch_up_m2", "touch_ups", "touch_up_mode",
    "wall_liters", "touch_up_liters", "total_liters",
)


@pytest.fixture()
def svc():
    with PaintService() as s:
        yield s


def pinned(resp):
    """从试算回包里取钉选字段（去掉 run_id/room_id）。"""
    return {k: resp[k] for k in TOUCH_KEYS if k in resp}


def total_of(result_json_raw):
    """复刻前端 BatchHistory.vue 的 totalOf 读数。"""
    import json
    r = json.loads(result_json_raw) if isinstance(result_json_raw, str) else result_json_raw
    if r.get("total_liters") is not None:
        return r["total_liters"]
    if r.get("wall_liters") is not None and r.get("touch_up_liters") is not None:
        return round(float(r["wall_liters"]) + float(r["touch_up_liters"]), 2)
    return r["liters"]


def test_persist_merge_matches_preview_and_history(svc):
    blocks = [{"w": 2, "h": 3}]
    preview = svc.estimate(1, False, touch_ups=blocks, touch_up_mode="merge")
    saved = svc.estimate(1, True, touch_ups=blocks, touch_up_mode="merge")
    assert pinned(saved) == pinned(preview)
    assert saved["total_liters"] == 13.1  # 净 46.41 + 补刷 6 = 52.41 m²，2 遍 / 8

    run = svc.history_run(saved["run_id"])
    assert run["result_json"] == pinned(preview)
    assert run["input_json"]["touch_ups"] == blocks
    assert run["input_json"]["touch_up_mode"] == "merge"

    rows = svc.history(500)
    row = next(r for r in rows if r["id"] == saved["run_id"])
    assert total_of(row["result_json"]) == preview["total_liters"]


def test_persist_separate_matches_preview_and_history(svc):
    blocks = [{"w": 2, "h": 3}]
    preview = svc.estimate(1, False, touch_ups=blocks,
                           touch_up_mode="separate", touch_up_coverage=6)
    saved = svc.estimate(1, True, touch_ups=blocks,
                         touch_up_mode="separate", touch_up_coverage=6)
    assert pinned(saved) == pinned(preview)
    # 墙面 11.6 + 补刷 6*2/6=2.0 → 13.6；不得并入墙面净面积按 8 重算
    assert preview["wall_liters"] == 11.6
    assert preview["touch_up_liters"] == 2.0
    assert preview["total_liters"] == 13.6

    run = svc.history_run(saved["run_id"])
    assert run["result_json"]["wall_liters"] == 11.6
    assert run["result_json"]["touch_up_liters"] == 2.0
    assert run["result_json"]["total_liters"] == 13.6
    assert run["input_json"]["touch_up_coverage"] == 6

    rows = svc.history(500)
    row = next(r for r in rows if r["id"] == saved["run_id"])
    assert total_of(row["result_json"]) == 13.6


def test_negative_touchup_rejected_and_not_written(svc):
    before = len(svc.history(500))
    with pytest.raises(ValueError):
        svc.estimate(1, True, touch_ups=[{"w": -2, "h": 3}], touch_up_mode="merge")
    after = len(svc.history(500))
    assert after == before


def test_removing_blocks_does_not_rewrite_old_run(svc):
    blocks = [{"w": 2, "h": 3}]
    first = svc.estimate(1, True, touch_ups=blocks, touch_up_mode="separate",
                         touch_up_coverage=6)
    old = svc.history_run(first["run_id"])
    assert old["result_json"]["total_liters"] == 13.6

    # 同房间删掉补刷块再估，生成新记录
    second = svc.estimate(1, True, touch_ups=[])
    assert second["run_id"] != first["run_id"]
    assert second["run_id"] is not None

    # 旧条钉选内容原样保留
    old_again = svc.history_run(first["run_id"])
    assert old_again["result_json"] == old["result_json"]
    assert old_again["input_json"] == old["input_json"]
    assert old_again["result_json"]["total_liters"] == 13.6
    assert old_again["result_json"]["touch_ups"] == blocks


def test_no_touchups_shape_unchanged(svc):
    r = svc.estimate(1, True, touch_ups=[])
    body = {k: v for k, v in r.items() if k not in ("run_id", "room_id")}
    assert set(body) == {"gross_m2", "openings_m2", "net_m2",
                         "liters", "coats", "coverage"}
    assert body["liters"] == 11.6


def test_http_negative_touchup_returns_400_and_writes_nothing():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        before = len(client.get("/api/history?limit=500").json()["items"])
        resp = client.post("/api/estimate", json={
            "room_id": 1, "persist": True,
            "touch_ups": [{"w": -2, "h": 3}], "touch_up_mode": "merge",
        })
        assert resp.status_code == 400
        after = len(client.get("/api/history?limit=500").json()["items"])
        assert after == before


def test_http_preview_persist_history_same_liters():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        body = {"room_id": 1, "touch_ups": [{"w": 2, "h": 3}],
                "touch_up_mode": "separate", "touch_up_coverage": 6}
        preview = client.post("/api/estimate", json={**body, "persist": False}).json()
        saved = client.post("/api/estimate", json={**body, "persist": True}).json()
        assert saved["total_liters"] == preview["total_liters"] == 13.6

        detail = client.get(f"/api/history/{saved['run_id']}").json()
        assert detail["result_json"]["total_liters"] == 13.6

        rows = client.get("/api/history?limit=500").json()["items"]
        row = next(r for r in rows if r["id"] == saved["run_id"])
        assert total_of(row["result_json"]) == 13.6
