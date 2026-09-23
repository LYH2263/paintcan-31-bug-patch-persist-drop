"""局部补刷模块：估漆可附加一组补刷块。

- merge：补刷面积合计后并入墙面净面积，按墙面涂布率换漆；
- separate：补刷面积按补刷专用涂布率单独换升数，再与墙面升数合计。

补刷块宽高必须为正整数（单位 m），任一不合规即拒绝，且不写估算记录。
"""

MERGE = "merge"
SEPARATE = "separate"


def normalize(blocks):
    """校验并归一化补刷块；宽高非正整数抛 ValueError。"""
    out = []
    for b in blocks or []:
        w, h = b.get("w"), b.get("h")
        # bool 是 int 子类，需显式排除
        if isinstance(w, bool) or isinstance(h, bool) \
                or not isinstance(w, int) or not isinstance(h, int) or w <= 0 or h <= 0:
            raise ValueError("touch-up block width and height must be positive integers")
        out.append({"w": w, "h": h})
    return out


def total_area(blocks):
    return round(sum(b["w"] * b["h"] for b in blocks), 2)
