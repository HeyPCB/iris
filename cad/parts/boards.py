"""Board envelopes from spec section 4 (outline, holes, maximum component heights), and the loader that
places a real board STEP (KiCad export) in the head frame for the fit check.

Brief frame (heypcb-kicad, spec 4): mm from the board's top-left corner, x right, y DOWN, seen from
the F side. KiCad STEP exports keep x, flip y (STEP y = -KiCad y) and put the B face at z = 0 and the
F face at z = thickness.
"""

import cadquery as cq

from .. import params as P
from ..geom import V, box, cyl, frame_location, prism, rounded_rect_pts

# brief frame -> H for each board: functions of (x, y) and the F-side normal in H
MAPS = {
    "B1": {"to_h": lambda x, y, n: (P.B1["f_x"] + n, x - 40.0, 20.0 - y), "w": P.B1["w"], "h": P.B1["h"],
           "f_normal": (1, 0, 0), "group": "cradle", "fillet": P.B1["fillet"],
           "holes": [(4.0, 4.0), (76.0, 4.0), (4.0, 36.0), (76.0, 36.0)], "f_h": P.B1["f_h"], "b_h": P.B1["b_h"]},
    "B2": {"to_h": lambda x, y, n: (-30.0 - y, 32.0 - x, P.B2["f_z"] + n), "w": P.B2["w"], "h": P.B2["h"],
           "f_normal": (0, 0, 1), "group": "fixed", "fillet": P.B2["fillet"],
           "holes": [(4.0, 4.0), (60.0, 4.0), (4.0, 76.0), (60.0, 76.0)], "f_h": P.B2["f_h"], "b_h": P.B2["b_h"]},
    "B4": {"to_h": lambda x, y, n: (P.B4["f_x"] + n, x - 58.0, 56.0 - y), "w": P.B4["w"], "h": P.B4["h"],
           "f_normal": (1, 0, 0), "group": "fixed", "fillet": P.B4["fillet"],
           "holes": [(12.0, 6.0), (34.0, 6.0), (82.0, 6.0), (104.0, 6.0)], "f_h": P.B4["f_h"], "b_h": P.B4["b_h"]},
}
THICK = 1.6


def board_location(board):
    """cq.Location from the board frame to H. Board frame = KiCad STEP convention, right-handed:
    origin at the brief origin (outline top-left corner) on the F face, x right, y UP (brief y = -y),
    z out of the F face (B face at z = -1.6)."""
    m = MAPS[board]["to_h"]
    o = V(*m(0, 0, 0))
    ex = V(*m(1, 0, 0)) - o
    ey = o - V(*m(0, 1, 0))
    ez = V(*m(0, 0, 1)) - o
    return frame_location((ex, ey, ez), (o.x, o.y, o.z))


def holes_h(board):
    m = MAPS[board]["to_h"]
    return [m(x, y, 0.0) for x, y in MAPS[board]["holes"]]


def normal_h(board):
    return MAPS[board]["f_normal"]


def envelope(board):
    """Board slab (with Dia 2.2 holes) + F-side and B-side height envelopes over the whole outline, minus
    a Dia 6 keepout around each mounting hole. Built in the board frame, placed in H."""
    M = MAPS[board]
    w, h = M["w"], M["h"]
    pts = rounded_rect_pts(w, h, M["fillet"], cx=w / 2, cy=-h / 2)
    slab = prism(pts, "xy", -THICK, 0.0)
    f = prism(pts, "xy", 0.0, M["f_h"])
    b = prism(pts, "xy", -THICK - M["b_h"], -THICK)
    for x, y in M["holes"]:
        slab = slab.cut(cyl("z", (x, -y, 0), P.M2_HOLE / 2, -10, 10))
        f = f.cut(cyl("z", (x, -y, 0), P.MOUNT_KEEPOUT_D / 2, -10, 20))
        b = b.cut(cyl("z", (x, -y, 0), P.MOUNT_KEEPOUT_D / 2, -20, 10))
    loc = board_location(board)
    return {"board": slab.moved(loc), "f": f.moved(loc), "b": b.moved(loc)}


def antenna_zone():
    """B1 WROOM antenna keepout (brief x 31-49, y 0-7, B side), grown by 5 mm (spec 7.1 P5)."""
    z = box(31.0 - 5, 49.0 + 5, 5.0, -(7.0 + 5), -THICK - 3.6 - 5, 5.0)
    return z.moved(board_location("B1"))


def load_real(board, step_path):
    """Place a KiCad STEP of `board` in H. The board body is the solid whose bounding box best matches
    the outline (w x h x 1.6 mm); its top-left corner (min x, max y) becomes the board-frame origin and
    its top face the F face. Returns (shape in H, info)."""
    shp = cq.importers.importStep(step_path).val()
    M = MAPS[board]
    sols = shp.Solids()
    best = None
    for s in sols:
        bb = s.BoundingBox()
        err = abs(bb.xlen - M["w"]) + abs(bb.ylen - M["h"]) + abs(bb.zlen - THICK)
        if best is None or err < best[0]:
            best = (err, s, bb)
    err, body, bb = best
    placed = shp.translate(V(-bb.xmin, -bb.ymax, -bb.zmax)).moved(board_location(board))
    body_h = body.translate(V(-bb.xmin, -bb.ymax, -bb.zmax)).moved(board_location(board))
    info = {"body_bbox_step": [round(v, 3) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)],
            "outline_error_mm": round(err, 3), "n_solids": len(sols)}
    return placed, body_h, info
