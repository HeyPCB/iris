"""Head skin and brows: face shell (P14), back cover (P16b), brows and brow hubs (P13).

v1 face is a stylised hard shell: a rounded box with a flat face plane at X = +29, carved eye
sockets with almond openings, a nose and a speaker grille. The face plane is set by three things:
B4 needs the shell's inner face 2 mm or more in front of its F face (X +22); the pan servos swing
forward to X +24.6 at full look-up; the brows sit on the face plane."""
import math

import cadquery as cq

from .. import params as P
from ..geom import box, cyl, ellipsoid, fuse_all, prism


def _rbox(x0, x1, y, z0, z1, rf, rr, rt):
    """Box with filleted vertical front/rear edges and a filleted top."""
    return (cq.Workplane("XY").box(x1 - x0, 2 * y, z1 - z0).translate(((x0 + x1) / 2, 0, (z0 + z1) / 2))
            .edges("|Z and >X").fillet(rf).edges("|Z and <X").fillet(rr)
            .faces(">Z").edges().fillet(rt).val())


def head_outer():
    H = P.HEAD
    return _rbox(H["x"][0], H["x"][1], H["y"], H["z"][0], H["z"][1], H["r_front"], H["r_rear"], H["r_top"] - 6.0)


def head_inner():
    H = P.HEAD
    t = H["wall"]
    return _rbox(H["x"][0] + t, H["x"][1] - t, H["y"] - t, H["z"][0] - 5.0, H["z"][1] - t,
                 H["r_front"] - t, H["r_rear"] - t, H["r_top"] - 6.0 - t)


def head_skin():
    """Full rounded-box head skin, open at the bottom, 2.5 mm wall."""
    return head_outer().cut(head_inner())


def _almond(side):
    yc = P.Y_EYE[side]
    O = P.EYE_OPENING
    w = O["w"] / 2
    # circular arcs through the canthi (yc +- w, 0) and the apex (yc, +up) / (yc, -lo)
    def arc(h, sgn):
        R = (w * w + h * h) / (2 * h)
        return R, sgn * (h - R)
    Ru, czu = arc(O["up"], 1)
    Rl, czl = arc(O["lo"], -1)
    au = math.degrees(math.asin(w / Ru))
    al = math.degrees(math.asin(w / Rl))
    up = [(yc + Ru * math.sin(math.radians(t)), czu + Ru * math.cos(math.radians(t)))
          for t in [au - 2 * au * i / 32 for i in range(33)]]
    lo = [(yc + Rl * math.sin(math.radians(t)), czl - Rl * math.cos(math.radians(t)))
          for t in [-al + 2 * al * i / 32 for i in range(1, 32)]]
    return up + lo


def face_shell():
    """P14 face shell: front of the head skin (X >= seam), sockets, openings, holes, B4 bosses."""
    S = P.EYE_SOCKET
    t = P.HEAD["wall"]
    xf = P.HEAD["x"][1]
    outer = head_outer().intersect(box(P.FACE_SEAM_X, 60, -100, 100, -100, 100))
    inner = head_inner()
    for side in P.SIDES:
        c = (S["cx"], P.Y_EYE[side], 0.0)
        outer = outer.cut(ellipsoid(c, S["a"]))
        inner = inner.cut(ellipsoid(c, tuple(a + t for a in S["a"])))
    face = outer.cut(inner)
    for side in P.SIDES:
        face = face.cut(prism(_almond(side), "yz", 10.0, 40.0))
    # nose
    nose = ellipsoid(P.NOSE["c"], P.NOSE["a"]).intersect(box(xf - 2.0, 60, -50, 50, -80, 80))
    face = face.fuse(nose)
    feats = []
    # magnet pads on the side walls (one per side, mating the skull side plates at X 2, Z 30)
    yi = P.HEAD["y"] - t
    for s in (1, -1):
        feats.append(cyl("y", (2.0, 0, 30.0), 5.0, s * (yi - 1.1), s * (yi + 0.01)))
        feats.append(box(xf - t - 2.3, xf - t + 0.01, s * 35.5, s * 44.5, -64.0, -55.0))   # base magnet pads
    for y, z in P.B4["holes_yz"]:
        feats.append(cyl("x", (0, y, z), 2.5, P.B4["f_x"], xf - t + 0.01))
    # touch pads: fill the air gap in front of B4's touch electrodes with plastic (0.3 mm off the board)
    y0, y1 = P.B4_TOUCH_Y
    for x0, x1 in P.B4_TOUCH:
        feats.append(box(P.B4["f_x"] + 0.3, xf - t + 0.01, x0 - 58.0, x1 - 58.0, 56.0 - y1, 56.0 - y0))
    face = fuse_all([face] + feats)
    # holes
    cuts = []
    for side in P.SIDES:
        y, z = P.SERVOS["brow_" + side][0][1:]
        cuts.append(cyl("x", (0, y, z), P.BROW_HOLE_D / 2, 15, 40))
    Wn = P.B4_WINDOWS                    # as-built B4 window positions (brief frame -> H: Y = x - 58, Z = 56 - y)
    tx, ty, tw, th = Wn["tof"]
    cuts.append(box(15, 40, tx - 58.0 - tw / 2, tx - 58.0 + tw / 2, 56.0 - ty - th / 2, 56.0 - ty + th / 2))   # ToF slot
    ax, ay, ad = Wn["als"]
    cuts.append(cyl("x", (0, ax - 58.0, 56.0 - ay), ad / 2, 15, 40))                                     # ALS
    for mx, my in Wn["mics"]:
        cuts.append(cyl("x", (0, mx - 58.0, 56.0 - my), Wn["mic_d"] / 2, 15, 40))                       # mic ports
    for y, z in P.B4["holes_yz"]:
        cuts.append(cyl("x", (0, y, z), 0.8, P.B4["f_x"] - 1, xf - t - 0.6))        # M2 self-tap
    sz = P.SPEAKER["c"][2]
    for k in range(-2, 3):
        cuts.append(box(15, 40, -11.0, 11.0, sz + 2.6 * k - 0.8, sz + 2.6 * k + 0.8))   # grille
    for s in (1, -1):
        cuts.append(cyl("y", (2.0, 0, 30.0), P.MAGNET["d"] / 2 + 0.1, s * (yi - 1.1 - 0.01), s * (yi - 1.1 + P.MAGNET["t"] + 0.2)))
        cuts.append(cyl("x", (0, s * 40.0, -59.5), P.MAGNET["d"] / 2 + 0.1, xf - t - 2.3 - 0.01, xf - t - 2.3 + P.MAGNET["t"] + 0.2))
    for cshape in cuts:
        face = face.cut(cshape)
    return face.clean()


BACK_BOSSES = ((-104.0, 50.0), (-104.0, -50.0), (-95.0, 76.0), (-95.0, -76.0))   # M2 from under the base plate


def back_cover():
    """P16b back cover: rear of the head skin, USB-C openings for B2's two receptacles (spec 4.2)."""
    b = head_outer().intersect(box(-200, P.FACE_SEAM_X, -100, 100, -100, 100)).cut(head_inner())
    xr = P.HEAD["x"][0]
    for y0, y1 in ((9.8, 20.2), (-20.2, -9.8)):
        b = b.cut(box(xr - 1, xr + P.HEAD["wall"] + 1, y0, y1, -61.0, -55.7))
    for k in range(5):
        b = b.cut(box(xr - 1, xr + P.HEAD["wall"] + 1, -30.0, 30.0, 20.0 + 6.0 * k, 22.0 + 6.0 * k))   # vents
    yi = P.HEAD["y"] - P.HEAD["wall"]
    bosses = []
    for x, y in BACK_BOSSES:
        bosses.append(cyl("z", (x, y, 0), 3.0, P.HEAD["z"][0], P.HEAD["z"][0] + 6.0))
        if abs(y) > 65:
            bosses.append(box(x - 3, x + 3, y, math.copysign(yi + 0.01, y), P.HEAD["z"][0], P.HEAD["z"][0] + 6.0))
        else:
            bosses.append(box(xr + P.HEAD["wall"] - 0.01, x, y - 3, y + 3, P.HEAD["z"][0], P.HEAD["z"][0] + 6.0))
    b = fuse_all([b] + bosses)
    for x, y in BACK_BOSSES:
        b = b.cut(cyl("z", (x, y, 0), 0.8, P.HEAD["z"][0] - 1, P.HEAD["z"][0] + 5.0))
    return b.clean()


# ------------------------------------------------------------------------------------- brows
def _brow_profile(side):
    """Brow outline in YZ: 45 mm, pivot (hub) at the outer third, inner end thicker, slight arch."""
    y0, z0 = P.SERVOS["brow_" + side][0][1:]
    n = 1.0 if side == "R" else -1.0          # toward the nose
    L = P.BROW_LEN
    a_in, a_out = L * (1 - P.BROW_PIVOT_FRAC), L * P.BROW_PIVOT_FRAC
    top, bot = [], []
    N = 24
    for i in range(N + 1):
        u = -a_out + (a_in + a_out) * i / N            # along the brow, + toward the nose
        f = (u + a_out) / (a_in + a_out)              # 0 outer .. 1 inner
        arch = 2.2 * (1 - ((f - 0.45) / 0.55) ** 2) - 2.2 * (1 - ((a_out / L - 0.45) / 0.55) ** 2)
        h = 2.0 + 3.6 * f                             # half... full height 2..5.6
        top.append((y0 + n * u, z0 + arch + h / 2))
        bot.append((y0 + n * u, z0 + arch - h / 2))
    return top + bot[::-1]


def brow(side):
    """P13b brow (flocked or painted), D-bore for the hub."""
    x0 = P.HEAD["x"][1] + 0.6
    y0, z0 = P.SERVOS["brow_" + side][0][1:]
    b = prism(_brow_profile(side), "yz", x0, x0 + P.BROW_T)
    b = b.fuse(cyl("x", (0, y0, z0), 4.2, x0, x0 + P.BROW_T))
    try:
        b = cq.Workplane().add(b).edges("|X").fillet(0.4).val()
    except Exception:
        pass
    hole = cyl("x", (0, y0, z0), P.BROW_HUB_D / 2 + 0.05, x0 - 1, x0 + 3.0).cut(
        box(x0 - 2, x0 + 4, y0 - 5, y0 + 5, z0 + 2.2, z0 + 5))
    return b.cut(hole).clean()


def brow_hub(side):
    """P13a hub: on the brow servo spline, through the Dia 10 hole in the face shell, D-key into the
    brow."""
    (x, y, z), _, _ = P.SERVOS["brow_" + side]
    x_sp = x - P.SV["OUT_ABOVE_SPLINE"] - P.SV["SPLINE_H"]   # spline root (cover top)
    x0 = x_sp + 0.5
    x1 = P.HEAD["x"][1] + 0.6 + 3.0 - 0.2
    h = cyl("x", (0, y, z), P.BROW_HUB_D / 2, x0, x1)
    h = h.cut(box(x1 - 3.2, x1 + 1, y - 5, y + 5, z + 2.2 - 0.05, z + 5))     # D-flat key
    h = h.cut(cyl("x", (0, y, z), P.SV["SPLINE_D"] / 2 - 0.05, x0 - 1, x - P.SV["OUT_ABOVE_SPLINE"]))
    h = h.cut(cyl("x", (0, y, z), 1.1, x0 - 1, x1 + 1))
    return h.clean()
