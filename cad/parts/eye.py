"""Eyeball parts (spec 2.2, 7.1 P1-P4). Built in the eye frame (origin at the eye centre, x along the
optical axis, z up), then moved to the eye centre in H at the rest pose."""
import math

import cadquery as cq

from .. import params as P
from ..geom import box, cone, cyl, prism, shell_sphere, tube
from . import purchased


def _revolve_x(pts):
    """Revolve a closed (x, r) profile 360 deg about the x axis."""
    return cq.Workplane("XY").polyline(pts).close().revolve(360, (0, 0, 0), (1, 0, 0)).val()


def _to_eye(shape, side):
    return shape.translate(cq.Vector(0, P.Y_EYE[side], 0))


def sclera_pieces():
    """P1 sclera shell (eye frame). Returns (shell_with_keel, pole_bosses) so the motion check can tell
    the pivot's designed axial gap from the rear-opening clearance."""
    sh = shell_sphere((0, 0, 0), P.EYE_R_IN, P.EYE_R)
    sh = sh.cut(cone((0, 0, 0), (-1, 0, 0), P.OPEN_HALF, 30.0))
    sh = sh.cut(cyl("x", (0, 0, 0), P.LIMBUS_D / 2, 0.0, 20.0))
    # pan keel: bracket under the shell, out through the rear opening to the crank pin (-14, 0, -16)
    k0, k1 = P.KEEL_Z
    keel = box(-P.CRANK, P.KEEL_X[1], -P.KEEL_W / 2, P.KEEL_W / 2, k0, k1)
    keel = keel.fuse(cyl("z", (-P.CRANK, 0, 0), P.KEEL_W / 2, k0, k1))
    keel = keel.cut(cyl("z", (-P.CRANK, 0, 0), 0.8, k0 - 1, k1 + 1))       # M2 stud pilot
    shell = sh.fuse(keel).clean()
    bosses = []
    for s in (1, -1):
        b = cyl("z", (0, 0, 0), P.POLE_BOSS_D / 2, s * P.POLE_BOSS_Z0, s * (P.EYE_R - 0.8))
        bosses.append(b)
    bos = bosses[0].fuse(bosses[1])
    bore = cyl("z", (0, 0, 0), P.POLE_BORE_D / 2, -P.EYE_R - 1, P.EYE_R + 1)
    shell = shell.cut(bore)
    bos = bos.cut(bore).cut(shell)
    return shell, bos


def sclera(side):
    shell, bos = sclera_pieces()
    return _to_eye(shell.fuse(bos).clean(), side)


def cornea(side):
    """P2 clear cornea dome with its base ring in the limbus bore."""
    cx = P.CORNEA_C
    ro, ri = P.CORNEA_R, P.CORNEA_R - P.CORNEA_WALL
    rb = P.LIMBUS_D / 2 - 0.02                                         # base ring OD (slip fit)
    xo = cx + math.sqrt(ro ** 2 - rb ** 2)                             # outer sphere meets the ring OD
    rin_ring = 6.2
    xi = cx + math.sqrt(ri ** 2 - rin_ring ** 2)

    def mid(r, x0, r0):
        a0 = math.atan2(r0, x0 - cx)
        return (cx + r * math.cos(a0 / 2), r * math.sin(a0 / 2))
    prof = (cq.Workplane("XY").moveTo(P.APEX_X, 0).threePointArc(mid(ro, xo, rb), (xo, rb))
            .lineTo(P.CORNEA_BASE_X, rb).lineTo(P.CORNEA_BASE_X, rin_ring).lineTo(xi, rin_ring)
            .threePointArc(mid(ri, xi, rin_ring), (cx + ri, 0)).close())
    dome = prof.revolve(360, (0, 0, 0), (1, 0, 0)).val()
    return _to_eye(dome, side)


def iris_disc(side):
    """P3 translucent iris disc, black pupil sleeve and the light-mixing cone ring that clamps B3."""
    x_b, x_f = P.IRIS_FRONT_X - P.IRIS_T, P.IRIS_FRONT_X
    rp, rs = P.PUPIL_D / 2, P.SLEEVE_OD / 2
    xb3 = P.B3_BX + P.B3_T                                           # 7.8, B3 F face
    pts = [(P.SLEEVE_BACK_X, rp), (P.SLEEVE_BACK_X, rs), (x_b, rs), (x_b, 6.9),
           (P.CAVITY_X_LED, P.CAVITY_R_LED), (xb3, P.CAVITY_R_LED)]
    for x in (xb3, 8.5, 9.2, 9.9, 10.5):
        pts.append((x, math.sqrt((P.EYE_R_IN - 0.1) ** 2 - x ** 2) - 0.05))
    pts += [(x_b, P.IRIS_D / 2), (x_f, P.IRIS_D / 2), (x_f, rp)]
    return _to_eye(_revolve_x(pts), side)


def _sph_r(x, margin=0.1):
    return math.sqrt((P.EYE_R_IN - margin) ** 2 - x ** 2)


def carrier(side):
    """P4 camera carrier (right) or dummy carrier (left), glued inside the sclera."""
    x0, x1 = P.CARRIER_X0, P.B3_BX
    xr = P.B3_BX + P.B3_T
    disc =_revolve_x([(x0, 0.0), (x0, _sph_r(x0)), (4.0, _sph_r(4.0)), (5.5, _sph_r(5.5)), (x1, _sph_r(x1)), (x1, 0.0)])
    wall = _revolve_x([(x1 - 0.01, P.CARRIER_RING_ID / 2), (x1 - 0.01, _sph_r(x1)), (xr, _sph_r(xr)),
                       (xr, P.CARRIER_RING_ID / 2)])
    c = disc.fuse(wall)
    # B3 key: fill the ring interior beyond the flat (right eye: flat down, left: flat up)
    k = -1.0 if side == "R" else 1.0
    key = box(x1 - 0.01, xr, -10, 10, k * P.CARRIER_RING_FLAT, k * 12).intersect(cyl("x", (0, 0, 0), P.CARRIER_RING_ID / 2 + 0.1, x1 - 0.02, xr))
    c = c.fuse(key)
    # B-side component pocket outside the 8.7 mm keepout square
    pocket = cyl("x", (0, 0, 0), P.B3_D / 2 + 0.1, x1 - P.B3_B_H - 0.35, x1 + 0.01).cut(
        box(x1 - 2, x1 + 1, -P.B3_KEEPOUT_SQ / 2, P.B3_KEEPOUT_SQ / 2, -P.B3_KEEPOUT_SQ / 2, P.B3_KEEPOUT_SQ / 2))
    c = c.cut(pocket)
    t = -P.nasal(side)                                               # temporal sign (y)
    hp = P.CARRIER_POCKET / 2
    if side == "R":
        c = c.cut(box(P.CAM_BACK_X, xr + 1, -hp, hp, -hp, hp))       # holder pocket
        fz, fw = P.FPC_SLOT
        c = c.cut(box(x0 - 0.5, P.CAM_BACK_X + 0.4, t * 4.1, t * (6.2 + fw), -fz / 2, fz / 2))   # FPC exit
    else:
        # dummy module (same envelope as the camera) printed in black
        c = c.fuse(purchased.ov2640_eye(side, neck=False))
    # ring wires: B3's four pads sit at r 7.6, 2.1 mm apart, on the temporal side -> arc slot
    W = P.RING_WIRE_SLOT
    a = W["half_deg"]
    pts = [(0.0, 0.0)] + [(t * 12 * math.cos(math.radians(-a + 2 * a * i / 16)), 12 * math.sin(math.radians(-a + 2 * a * i / 16)))
                          for i in range(17)]
    slot = prism(pts, "yz", x0 - 1, xr + 1).intersect(tube("x", (0, 0, 0), W["r"][0], W["r"][1], x0 - 1, xr + 1))
    c = c.cut(slot)
    return _to_eye(c.clean(), side)


def camera(side="R"):
    """OV2640 module envelope (purchased), right eye only."""
    return _to_eye(purchased.ov2640_eye(side), side)


def b3_envelope(side):
    """B3 iris ring envelope from spec 4.4: board, F-side LED band, B-side parts outside the keepout."""
    x0, x1 = P.B3_BX, P.B3_BX + P.B3_T
    k = -1.0 if side == "R" else 1.0
    board = cyl("x", (0, 0, 0), P.B3_D / 2, x0, x1).cut(cyl("x", (0, 0, 0), P.B3_ID / 2, x0 - 1, x1 + 1))
    board = board.cut(box(x0 - 1, x1 + 1, -10, 10, k * P.B3_FLAT, k * 10))
    f = tube("x", (0, 0, 0), P.B3_LED_R[0], P.B3_LED_R[1], x1, x1 + P.B3_F_H)
    b = tube("x", (0, 0, 0), P.B3_ID / 2 + 0.6, P.B3_D / 2 - 0.3, x0 - P.B3_B_H, x0)
    b = b.cut(box(x0 - 2, x0 + 1, -P.B3_KEEPOUT_SQ / 2, P.B3_KEEPOUT_SQ / 2, -P.B3_KEEPOUT_SQ / 2, P.B3_KEEPOUT_SQ / 2))
    b = b.cut(box(x0 - 2, x0 + 1, -10, 10, k * (P.B3_FLAT - 0.3), k * 10))
    return {"board": _to_eye(board, side), "f": _to_eye(f, side), "b": _to_eye(b, side)}


def pole_pins(side):
    lo, hi = P.POLE_PIN_Z
    pins = [cyl("z", (0, 0, 0), P.POLE_PIN_D / 2, s * lo, s * hi) for s in (1, -1)]
    return _to_eye(pins[0].fuse(pins[1]), side)


def keel_stud(side):
    return _to_eye(purchased.ball_stud((-P.CRANK, 0, P.COUPLER_Z), (-P.CRANK, 0, P.KEEL_Z[1] - 0.5)), side)
