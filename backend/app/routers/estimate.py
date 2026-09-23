from fastapi import APIRouter, HTTPException
from app.schemas.estimate import EstimateRequest
from app.services.paint_service import PaintService
router = APIRouter()
@router.post("/estimate")
def post_estimate(body: EstimateRequest):
    with PaintService() as s:
        try:
            r = s.estimate(body.room_id, body.persist, body.coats, body.coverage,
                           [b.model_dump() for b in body.touch_ups],
                           body.touch_up_mode, body.touch_up_coverage)
        except ValueError as e:
            # 宽高非正整数等：拒绝，且在持久化之前抛出，不写记录
            raise HTTPException(400, str(e))
        if not r: raise HTTPException(404)
        return r
