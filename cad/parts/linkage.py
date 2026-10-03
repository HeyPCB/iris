"""Servo-side links: lid servo horns (P17), pan cranks (P12), the tilt drive tongue (P8), and the
purchased couplers, studs and pins that join them. All at the rest pose."""
import math

from .. import kinematics as K
from .. import params as P
from ..geom import box, cyl, rot_elev
from . import purchased


# ------------------------------------------------------------------------------------- lid horns
def lid_horn(kind, side):
    """P17 printed 9 mm horn on a lid servo spline. Hub over the spline, arm plate in the |Y| band
    HORN_PLATE (clear of the opposite servo cases), M2 ball stud pointing away from the servo."""
    name = K.LID_SERVO[(kind, side)]
    (xs, ys, zs), shaft, _ = P.SERVOS[name]
    sg = 1.0 if shaft == "+y" else -1.0
    h0, h1 = P.HORN_PLATE
    hub = cyl("y", (xs, 0, zs), P.HORN_HUB_D / 2, sg * P.HORN_HUB_Y0, sg * h1)
    arm = box(0.0, P.LEVER, sg * h0, sg * h1, -2.5, 2.5).fuse(cyl("y", (P.LEVER, 0, 0), 2.5, sg * h0, sg * h1))
    arm = rot_elev(arm, K.lever_angle(kind, side, K.rest_margin(kind))).translate((xs, 0, zs))
    horn = hub.fuse(arm).clean()
    spline_top = abs(ys) - P.SV["OUT_ABOVE_SPLINE"]
    horn = horn.cut(cyl("y", (xs, 0, zs), P.SV["SPLINE_D"] / 2 - 0.05, sg * (P.HORN_HUB_Y0 - 1), sg * spline_top))
    horn = horn.cut(cyl("y", (xs, 0, zs), 1.1, 0, sg * 30))                      # M2 horn screw
    horn = horn.cut(cyl("y", (xs, 0, zs), 2.1, sg * (h1 - 1.2), sg * 30))         # screw head
    b = K.horn_ball(kind, side, K.rest_margin(kind))
    horn = horn.cut(cyl("y", (b[0], 0, b[2]), 0.8, 0, sg * 30))                   # stud pilot
    return horn


def horn_stud(kind, side):
    b = K.horn_ball(kind, side, K.rest_margin(kind))
    sg = math.copysign(1.0, b[1])
    return purchased.ball_stud(b, (b[0], sg * (P.HORN_PLATE[0] + 0.3), b[2]))


# ------------------------------------------------------------------------------------- pan
def pan_crank(side):
    """P12 14 mm crank on the pan servo spline; arm above the coupler plane, stud pointing down."""
    ys = math.copysign(P.PAN_SERVO_Y, P.Y_EYE[side])
    z0, z1 = P.PAN_CRANK_ARM_Z
    hub = cyl("z", (0, ys, 0), P.PAN_CRANK_HUB_D / 2, P.PAN_CRANK_HUB_Z0, z1)
    arm = box(-P.CRANK, 0, ys - 2.5, ys + 2.5, z0, z1).fuse(cyl("z", (-P.CRANK, ys, 0), 2.5, z0, z1))
    c = hub.fuse(arm).clean()
    spline_top = P.COUPLER_Z - P.SV["OUT_ABOVE_SPLINE"]
    c = c.cut(cyl("z", (0, ys, 0), P.SV["SPLINE_D"] / 2 - 0.05, P.PAN_CRANK_HUB_Z0 - 1, spline_top))
    c = c.cut(cyl("z", (0, ys, 0), 1.1, -40, 0)).cut(cyl("z", (0, ys, 0), 2.1, z1 - 1.0, 0))
    c = c.cut(cyl("z", (-P.CRANK, ys, 0), 0.8, -40, 0))
    return c


def crank_stud(side):
    p = K.servo_pin(side, 0.0)
    return purchased.ball_stud(p, (p[0], p[1], P.PAN_CRANK_ARM_Z[0] + 1.2))


def pan_coupler(side):
    return purchased.pushrod(K.eye_pin(side, 0.0), K.servo_pin(side, 0.0), "z")


# ------------------------------------------------------------------------------------- tilt
def tilt_tongue():
    """P8 tilt drive tongue: clamps the tilt servo spline (split hub + M2 cross screw), carries the
    left nasal lid pin on the axis and a drive pin that rides in a radial slot in the cradle
    (radially compliant, so the servo bearing and the right temple bearing never fight)."""
    T = P.TONGUE
    y0, y1 = T["y"]
    hub = cyl("y", (0, 0, 0), T["hub_d"] / 2, y0, 15.0).fuse(cyl("y", (0, 0, 0), 3.5, 14.9, 17.6))
    pts = [(0.0, T["w0"] / 2), (T["x_end"], T["w1"] / 2), (T["x_end"], -T["w1"] / 2), (0.0, -T["w0"] / 2)]
    from ..geom import prism
    arm = prism(pts, "xz", y0, y1).fuse(cyl("y", (T["x_end"], 0, 0), T["w1"] / 2, y0, y1))
    t = hub.fuse(arm).clean()
    spline_top = P.SERVOS["tilt"][0][1] - P.SV["OUT_ABOVE_SPLINE"]
    t = t.cut(cyl("y", (0, 0, 0), P.SV["SPLINE_D"] / 2 - 0.05, y0 - 1, spline_top))
    t = t.cut(cyl("y", (0, 0, 0), P.LID_PIN_D / 2 - 0.05, spline_top + 0.05, 30))       # lid pin bore
    t = t.cut(box(-6.0, -0.3, y0 - 1, spline_top - 0.3, -0.4, 0.4))                    # clamp slit
    t = t.cut(cyl("z", (-3.2, (y0 + spline_top) / 2, 0), 1.1, -10, 10))               # M2 clamp screw
    t = t.cut(cyl("y", (T["x_end"], 0, 0), T["pin_d"] / 2 - 0.05, y0 - 1, y1 + 1))      # drive pin
    return t


def tongue_drive_pin():
    T = P.TONGUE
    return cyl("y", (T["x_end"], 0, 0), T["pin_d"] / 2, T["y"][0], T["pin_y1"])


# ------------------------------------------------------------------------------------- lid pins
def nasal_pin(side):
    """Dia 3 pin for the nasal lid hubs: right eye from the nose block, left eye from P8."""
    if side == "R":
        return purchased.pin_y(P.LID_PIN_D / 2, -22.0, -14.0)
    return purchased.pin_y(P.LID_PIN_D / 2, 15.0, 22.0)


def temporal_pin(side):
    s = math.copysign(1.0, P.Y_EYE[side])
    return purchased.pin_y(P.LID_PIN_D / 2, s * 56.0, s * 71.0)


# ------------------------------------------------------------------------------------- harness
def _tube(points, r):
    from ..geom import cyl_pts, sphere
    segs = [cyl_pts(a, b, r) for a, b in zip(points[:-1], points[1:])]
    joints = [sphere(p, r) for p in points[1:-1]]
    out = segs[0]
    if len(segs) > 1 or joints:
        out = out.fuse(*(segs[1:] + joints)).clean()
    return out


def brow_cable_cradle():
    """BROW harness (SH-8, 8 x 28 AWG, bundle Dia 3.5) from B1 J4's mouth (brief (17, 7.7), cable up)
    straight up behind the top rail and over B1's top edge. Rides the cradle; keep-out for the check."""
    return _tube(P.BROW_CABLE["cradle"], P.BROW_CABLE["r"])


def brow_cable_frame():
    """BROW harness, frame side: from B4 J1 (back of B4, cable up) over B4's top edge, beside the centre
    column, back under the top bridge to the clip at X -30, then to the start of the service loop."""
    return _tube(P.BROW_CABLE["frame"], P.BROW_CABLE["r"])
