"""Board envelopes from spec section 4 (outline, holes, maximum component heights), and the loader that
places a real board STEP (KiCad export) in the head frame for the fit check.

Brief frame (heypcb-kicad, spec 4): mm from the board's top-left corner, x right, y DOWN, seen from
the F side. KiCad STEP exports keep x, flip y (STEP y = -KiCad y) and put the B face at z = 0 and the
F face at z = thickness.
"""
import hashlib
import os

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


# ------------------------------------------------------------------------------------- real boards
# As-built boards from the four board repositories (KiCad 10.0.6 STEP exports). The STEP body is the
# stackup without copper (1.51 mm); each board is normalised to the thickness that is ordered.
REAL = {
    "B1": {"repo": "iris-cortex", "file": "iris_cortex.step", "t": 1.6},
    "B2": {"repo": "iris-brainstem", "file": "iris_brainstem.step", "t": 1.6},
    "B3": {"repo": "iris-ring", "file": "iris_ring.step", "t": 0.8},
    "B4": {"repo": "iris-brow", "file": "iris_brow.step", "t": 1.6},
}

# B3 LEDs are not in the ring STEP (no 3D model for the footprint): envelopes from the ring's
# placement file (brief-frame centres; WS2812C-2020 is 2.0 x 2.0 x 0.84, modelled 2.1 x 2.1 x 0.9 so the
# corners reach r 8.09 as the ring designer states).
B3_LEDS = [(2.625, 7.292), (4.333, 4.333), (7.292, 2.625), (10.708, 2.625), (13.667, 4.333), (15.375, 7.292),
           (15.375, 10.708), (13.667, 13.667), (10.708, 15.375), (7.292, 15.375), (4.333, 13.667), (2.625, 10.708)]
B3_LED = (2.1, 0.9)
# Other parts whose 3D model is missing from the exports, as F-side boxes in the brief frame
# (x0, x1, y0, y1, height above the F face); sizes from the parts' drawings (est. where noted).
MISSING = {
    "B1": [(0.3, 5.8, 11.0, 29.0, 2.1)],                                  # J1 AFC07-S24FCA-00, 24P 0.5 mm FPC
    "B2": ([(2.25, 9.75, y - 2.6, y + 2.6, 6.4) for y in (16.5, 26.0, 35.5, 45.0, 54.5)]      # J10-J14 5267 vertical
           + [(54.25, 61.75, y - 2.6, y + 2.6, 6.4) for y in (15.2, 24.7, 34.2, 43.7, 53.2)]   # J15-J19 (est. 6.4 tall)
           + [(xc - 4.5, xc + 4.5, 72.8, 80.2, 3.3) for xc in (17.0, 47.0)]),                 # J1, J2 USB-C TYPE-C-31-M-12
}
# B2 through-hole tails are not in the STEP either: pin centres from the board file (brief frame), tail
# length below the B face (Molex 5267 vertical 3.2 mm, USB-C shell legs 1.5 mm).
B2_THT = ([(x, y, 1.0, 1.0, 3.2) for y in (16.5, 26.0, 35.5, 45.0, 54.5) for x in (3.5, 6.0, 8.5)]
          + [(x, y, 1.0, 1.0, 3.2) for y in (15.2, 24.7, 34.2, 43.7, 53.2) for x in (55.5, 58.0, 60.5)]
          + [(x, y, 1.2, 2.0, 1.5) for xc in (17.0, 47.0) for (x, y) in
             ((xc - 2.89, 73.7), (xc + 2.89, 73.7), (xc - 4.32, 73.17), (xc - 4.32, 77.35), (xc + 4.32, 73.17), (xc + 4.32, 77.35))])


def find_real(dirs):
    """Locate the four board STEP files under any of `dirs` (a heypcb-kicad build folder with
    iris_cortex/fab/..., or a folder holding the cloned board repositories iris-cortex/fab/...)."""
    out = {}
    for b, r in REAL.items():
        stem = r["file"][:-5]
        for d in dirs:
            if not d:
                continue
            for cand in (os.path.join(d, stem, "fab", r["file"]), os.path.join(d, r["repo"], "fab", r["file"]),
                         os.path.join(d, r["file"])):
                if os.path.exists(cand):
                    out[b] = cand
                    break
            if b in out:
                break
    return out


def source_label(path):
    """Repository-relative description of a board STEP (no machine paths in outputs)."""
    parts = os.path.normpath(path).split(os.sep)
    tail = "/".join(parts[-3:]) if len(parts) >= 3 else parts[-1]
    with open(path, "rb") as f:
        sha = hashlib.sha1(f.read()).hexdigest()[:12]
    return {"file": tail, "sha1": sha}


def load_real(board, step_path, thickness=None):
    """Real board in its board frame (F face at z = 0, x right, y up, origin at the outline's
    top-left corner), split into board body / F-side parts / B-side parts and normalised to
    `thickness` (default: the ordered thickness). Missing models are added as envelopes."""
    shp = cq.importers.importStep(step_path).val()
    sols = shp.Solids()
    body = max(sols, key=lambda s: s.Volume())
    bb = body.BoundingBox()
    t0 = bb.zlen
    t = REAL[board]["t"] if thickness is None else thickness
    off = V(-bb.xmin, -bb.ymax, -bb.zmax)
    fs, bs = [], []
    for s in sols:
        if s is body:
            continue
        sb = s.BoundingBox()
        if sb.zmin >= bb.zmax - 0.05:
            fs.append(s.translate(off))
        elif sb.zmax <= bb.zmin + 0.05:
            bs.append(s.translate(off + V(0, 0, -(t - t0))))
        else:
            fs.append(s.translate(off))                       # straddling (THT bodies): keep on F
    b0 = body.translate(off)                                  # z in [-t0, 0]
    if t >= t0:                                               # thicken: union with a copy pushed down
        body_n = b0.fuse(b0.translate(V(0, 0, -(t - t0)))).clean()
    else:                                                     # thin: keep the top t of the body
        bb0 = b0.BoundingBox()
        body_n = b0.intersect(box(bb0.xmin - 1, bb0.xmax + 1, bb0.ymin - 1, bb0.ymax + 1, -t, 1.0))
    if board == "B3":
        for x, y in B3_LEDS:
            h = B3_LED[0] / 2
            fs.append(box(x - h, x + h, -y - h, -y + h, 0.0, B3_LED[1]))
    for x0, x1, y0, y1, h in MISSING.get(board, []):
        fs.append(box(x0, x1, -y1, -y0, 0.0, h))
    if board == "B2":
        for x, y, w, l, d in B2_THT:
            bs.append(box(x - w / 2, x + w / 2, -y - l / 2, -y + l / 2, -t - d, -t + 0.01))
    comp = lambda L: cq.Compound.makeCompound(L) if L else None
    info = {"step_body_mm": [round(bb.xlen, 2), round(bb.ylen, 2), round(t0, 3)], "modelled_thickness_mm": t,
            "n_solids": len(sols), "f_parts": len(fs), "b_parts": len(bs),
            "f_height_mm": round(max((s.BoundingBox().zmax for s in fs), default=0.0), 2),
            "b_height_mm": round(max((-t - s.BoundingBox().zmin for s in bs), default=0.0), 2)}
    return {"board": body_n, "f": comp(fs), "b": comp(bs)}, info


def place_real(board, parts, side=None):
    """Move a board-frame board (dict from load_real) to H. B3 needs `side` (R or L)."""
    if board != "B3":
        loc = board_location(board)
        return {k: v.moved(loc) for k, v in parts.items() if v is not None}
    t = parts["board"].BoundingBox().zlen
    # brief frame: right eye +x -> +Y_eye, +y (down) -> -Z_eye, F normal -> +X_eye; left eye turned 180 deg
    s = 1.0 if side == "R" else -1.0
    loc = frame_location((V(0, s, 0), V(0, 0, s), V(1, 0, 0)), (P.B3_BX + t, P.Y_EYE[side], 0.0))
    centre = V(-P.B3_D / 2, P.B3_D / 2, 0.0)
    return {k: v.translate(centre).moved(loc) for k, v in parts.items() if v is not None}
