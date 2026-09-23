from fastapi import APIRouter, HTTPException
from app.services.paint_service import PaintService
router = APIRouter()
@router.get("/history")
def history(limit: int = 50):
    with PaintService() as s: return {"items": s.history(limit)}
@router.get("/history/{run_id}")
def history_detail(run_id: int):
    # 回放旧记录：直接返回当时钉选的输入与结果，不按房间现状重算
    with PaintService() as s:
        r = s.history_run(run_id)
        if not r: raise HTTPException(404)
        return r
