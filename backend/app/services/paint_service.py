from app.db import connect
from app.engines.estimate import estimate_room
from app.repositories import openings, rooms, runs, settings

class PaintService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_rooms(self): return rooms.list_all(self._c)
    def room_detail(self, rid):
        r = rooms.get(self._c, rid)
        if not r: return None
        return {"room": r, "openings": openings.for_room(self._c, rid)}
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def history_run(self, run_id): return runs.get(self._c, run_id)
    def estimate(self, room_id, persist, coats=None, coverage=None,
                 touch_ups=None, touch_up_mode="merge", touch_up_coverage=None):
        detail = self.room_detail(room_id)
        if not detail: return None
        r = detail["room"]
        cov, ct = settings.coverage_coats(self._c)
        cov = float(coverage or cov)
        ct = int(coats or ct)
        ops = [{"w": o["w"], "h": o["h"]} for o in detail["openings"]]
        blocks = [{"w": b["w"], "h": b["h"]} for b in (touch_ups or [])]
        # 宽高非正整数在 schema 层即 422 拒绝；normalize 再守一道，均在 insert 之前
        result = estimate_room(r["length"], r["width"], r["height"], ops, cov, ct,
                               blocks, touch_up_mode, touch_up_coverage)
        payload = {"room_id": room_id, "coats": ct, "coverage": cov}
        if blocks:
            payload["touch_ups"] = blocks
            payload["touch_up_mode"] = result["touch_up_mode"]
            if result["touch_up_mode"] == "separate":
                payload["touch_up_coverage"] = result["touch_up_coverage"]
        # 持久化钉选：写入的就是本次试算回包的同一份结果，列表摘要与按号详情都取自它，
        # 后续房间/补刷块改动不会重算或改写旧条
        if persist:
            rid = runs.insert(self._c, "estimate", payload, result, room_id)
        else:
            rid = None
        return {"run_id": rid, "room_id": room_id, **result}
    def dashboard(self):
        rs = rooms.list_all(self._c)
        return {"room_count": len(rs), "clean": len([x for x in rs if "种子" not in x["name"] and "多种" not in x["name"]]), "dirty": len([x for x in rs if "多种" in x["name"]])}
