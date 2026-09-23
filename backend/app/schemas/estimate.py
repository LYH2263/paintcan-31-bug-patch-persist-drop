from typing import Literal
from pydantic import BaseModel, StrictInt

class TouchUpBlock(BaseModel):
    # 宽高必须为正整数；StrictInt 拒绝 1.5、"2" 等非整数入参
    w: StrictInt
    h: StrictInt

class EstimateRequest(BaseModel):
    room_id: int
    coats: int | None = None
    coverage: float | None = None
    touch_ups: list[TouchUpBlock] = []
    touch_up_mode: Literal["merge", "separate"] = "merge"
    touch_up_coverage: float | None = None
    persist: bool = True
