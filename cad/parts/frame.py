"""Fixed head frame: nose-bridge block (P9), centre column (P10), skull side plates and top bridge
(P15), base plate (P16). Rest pose, H frame."""
import math

from .. import params as P
from ..geom import box, cyl, fuse_all, prism, rounded_rect_pts


def nose_block():
    """P9: cap under the tilt servo (servo held by its ears on the centre column) carrying the right
    eye's nasal lid pin on the Y axis."""
    floor = box(-18.0, 6.6, -14.8, -13.8, -6.8, 6.8)
    walls = [box(-18.0, 6.6, -14.8, -P.COLUMN_Y, s * 6.6, s * 8.6) for s in (1, -1)]
    boss = cyl("y", (0, 0, 0), 3.5, -17.7, -14.7)
    b = fuse_all([floor, boss] + walls)
    b = b.cut(cyl("y", (0, 0, 0), P.LID_PIN_D / 2 - 0.05, -18, -13.5))
    for x in (-14.0, 2.5):
        for s in (1, -1):
            b = b.cut(cyl("y", (x, 0, s * 7.6), 0.8, -10, 0))            # screws into the column plate
    return b.clean()


def column():
    """P10: vertical centre plate (Y +-2.35). The four lid servos clamp their ears on its faces (left
    servos on +Y, right servos on -Y) and pass through windows; the tilt servo ears sit on 0.95 mm pads.
    Ties the nose block to the top bridge and the base plate."""
    y = P.COLUMN_Y
    pts = [(P.COLUMN_X[0], P.BASE_Z[1]), (14.4, P.BASE_Z[1]), (14.4, -27.0), (P.COLUMN_X[1], -27.0),
           (P.COLUMN_X[1], 40.0), (6.0, P.TOP_BRIDGE_Z[0]), (P.COLUMN_X[0], P.TOP_BRIDGE_Z[0])]
    c = prism(pts, "xz", -y, y)
    m = 0.35
    c = c.cut(box(-13.95 - m, 9.35 + m, -5, 5, 14.45 - m, 40.05 + m))      # upper lid servo pair
    c = c.cut(box(-13.95 - m, 9.35 + m, -5, 5, -40.05 - m, -14.45 + m))    # lower lid servo pair
    c = c.cut(box(-17.35 - m, 5.95 + m, -5, 5, -6.05 - m, 6.05 + m))       # tilt servo
    pads = [box(-22.0, -17.7, y - 0.01, 3.3, -5.5, 5.5), box(6.3, 10.6, y - 0.01, 3.3, -5.5, 5.5)]
    c = fuse_all([c] + pads)
    for z in (20.5, 34.0, -20.5, -34.0):
        for x in (-16.55, 11.95):
            c = c.cut(cyl("y", (x, 0, z), 0.8, -5, 5))
    for x in (-19.95, 8.55):
        c = c.cut(cyl("y", (x, 0, 0), 0.8, -5, 5))
    c = c.cut(box(-19.0, 7.5, -5, 5, 44.0, 58.0))                           # lightening + harness pass
    c = c.cut(box(-19.0, 7.0, -5, 5, -62.0, -46.0))
    return c.clean()


def side_plate(side):
    """P15a: skull side plate. Right plate holds the Dia 3 temple pin (spec Y -74..-80); left plate
    holds the loose bushing pin. Magnet pockets toward the face shell."""
    s = math.copysign(1.0, P.Y_EYE[side])
    ya, yb = P.SIDE_PLATE_Y
    pts = rounded_rect_pts(98.0, P.TOP_BRIDGE_Z[0] - P.BASE_Z[1], 12.0, cx=-39.0,
                           cy=0.5 * (P.TOP_BRIDGE_Z[0] + P.BASE_Z[1]))
    plate = prism(pts, "xz", s * ya, s * yb)
    win = rounded_rect_pts(54.0, 92.0, 10.0, cx=-47.0, cy=0.0)
    plate = plate.cut(prism(win, "xz", s * (ya - 1), s * (yb + 1)))
    boss = cyl("y", (0, 0, 0), 4.0, s * 76.5, s * ya)
    p = fuse_all([plate, boss])
    p = p.cut(cyl("y", (0, 0, 0), P.LID_PIN_D / 2 - 0.05, s * 70, s * 90))
    p = p.cut(cyl("y", (2.0, 0, 30.0), P.MAGNET["d"] / 2 + 0.1, s * (yb - P.MAGNET["t"] - 0.2), s * 90))
    for x in (-80.0, -10.0, 0.0):
        p = p.cut(cyl("z", (x, s * 82.0, 0), 0.8, P.TOP_BRIDGE_Z[0] - 6, P.TOP_BRIDGE_Z[0] + 1))
        p = p.cut(cyl("z", (x, s * 82.0, 0), 0.8, P.BASE_Z[1] - 1, P.BASE_Z[1] + 6))
    return p.clean()


def top_bridge():
    """P15b: top bridge between the side plates, with the two brow-servo brackets."""
    z0, z1 = P.TOP_BRIDGE_Z
    pts = rounded_rect_pts(70.0, 2 * P.SIDE_PLATE_Y[1], 8.0, cx=-27.0, cy=0.0)
    top = prism([(u, v) for u, v in pts], "xy", z0, z1)
    parts = [top]
    for side in P.SIDES:
        s = math.copysign(1.0, P.Y_EYE[side])
        br = box(-15.65, -12.65, s * 45.5, s * 62.5, 24.5, z0 + 0.01)
        br = br.cut(box(-17, -11, s * 47.6, s * 60.4, 31.7, 55.7))
        parts.append(br)
    b = fuse_all(parts)
    for side in P.SIDES:
        s = math.copysign(1.0, P.Y_EYE[side])
        for z in (29.45, 57.95):
            b = b.cut(cyl("x", (0, s * 54.0, z), 0.8, -18, -10))
        for x in (-80.0, -10.0, 0.0):
            b = b.cut(cyl("z", (x, s * 82.0, 0), 1.1, z0 - 1, z1 + 1))
    for x in (-20.0, 10.0):
        b = b.cut(cyl("z", (x, 0, 0), 1.1, z0 - 1, z1 + 1))
    return b.clean()


def base_plate():
    """P16a: base plate. B2 bosses (tops at Z -61.6, M2 inserts), speaker holder, face-shell magnet
    posts, neck mount holes (M3, pattern TBD)."""
    z0, z1 = P.BASE_Z
    hx0, hx1 = P.HEAD["x"]
    pts = rounded_rect_pts(hx1 - hx0, 2 * P.HEAD["y"], P.HEAD["r_front"], cx=0.5 * (hx0 + hx1), cy=0.0)
    plate = prism(pts, "xy", z0, z1)
    parts = [plate]
    for x, y in P.B2["holes_xy"]:
        parts.append(cyl("z", (x, y, 0), 2.5, z1 - 0.01, P.B2_BOSS_Z[1]))
    sc = P.SPEAKER["c"]
    r = P.SPEAKER["d"] / 2
    x0 = sc[0]
    ring = cyl("x", sc, r + 2.2, x0 - 0.5, x0 + 2.5).cut(cyl("x", sc, r + 0.2, x0 - 1, x0 + 3))
    lip = cyl("x", sc, r + 2.2, x0 + 2.5, x0 + 3.5).cut(cyl("x", sc, r - 1.5, x0 + 2, x0 + 4))
    leg = box(x0 - 0.5, x0 + 3.5, -6.0, 6.0, z1 - 0.01, sc[2] - r - 0.5)
    parts += [ring, lip, leg]
    for s in (1, -1):
        parts.append(box(17.0, 24.0, s * 36.0, s * 44.0, z1 - 0.01, -56.0))     # magnet posts
    b = fuse_all(parts)
    for x, y in P.B2["holes_xy"]:
        b = b.cut(cyl("z", (x, y, 0), P.M2_INSERT_HOLE / 2, P.B2_BOSS_Z[1] - 4.0, 0))
    from .face import BACK_BOSSES
    for x, y in BACK_BOSSES:
        b = b.cut(cyl("z", (x, y, 0), 1.1, z0 - 1, z1 + 1))
    for s in (1, -1):
        b = b.cut(cyl("x", (0, s * 40.0, -59.5), P.MAGNET["d"] / 2 + 0.1, 24.0 - P.MAGNET["t"] - 0.2, 26))
        for x in (-50.0, -90.0):
            b = b.cut(cyl("z", (x, s * 42.0, 0), 1.7, z0 - 1, z1 + 1))          # neck M3 (TBD)
        for x in (-80.0, -10.0, 0.0):
            b = b.cut(cyl("z", (x, s * 82.0, 0), 1.1, z0 - 1, z1 + 1))
    return b.clean()
