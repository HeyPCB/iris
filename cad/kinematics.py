"""Iris kinematics: lever geometry, pose model and rigid transforms for every moving group.

A pose is a dict with keys
  tilt, pan_R, pan_L          (deg)
  up_R, lo_R, up_L, lo_L      lid margin elevations (deg, absolute)
  brow_R, brow_L              (deg, + = inner end up)
Missing keys take rest values (REST).
"""
import math

import numpy as np

from . import params as P

REST = {"tilt": 0.0, "pan_R": 0.0, "pan_L": 0.0, "up_R": P.UP_REST, "lo_R": P.LO_REST,
        "up_L": P.UP_REST, "lo_L": P.LO_REST, "brow_R": 0.0, "brow_L": 0.0}

LID_SERVO = {("U", "R"): "lidU_R", ("U", "L"): "lidU_L", ("L", "R"): "lidL_R", ("L", "L"): "lidL_L"}


def full(pose):
    out = dict(REST)
    out.update(pose or {})
    return out


# ------------------------------------------------------------------------------------- lids
def servo_axis_xz(name):
    p = P.SERVOS[name][0]
    return p[0], p[2]


def coupler_dir(kind, side):
    """Direction (deg, XZ elevation) of the lid-axis -> servo-axis vector; the parallelogram coupler
    stays parallel to it."""
    x, z = servo_axis_xz(LID_SERVO[(kind, side)])
    return math.degrees(math.atan2(z, x))


def coupler_len(kind, side):
    x, z = servo_axis_xz(LID_SERVO[(kind, side)])
    return math.hypot(x, z)


def lever_offset(kind, side):
    """Lever angle minus margin angle. The lever is perpendicular to the coupler at mid-travel, on the
    '+90 deg' branch: the upper-lid lever points back (behind the lid axis), the lower-lid lever points
    forward, so the two levers of one eye never meet (separation >= 68 deg over the whole lid
    envelope)."""
    rng = P.UP_RANGE if kind == "U" else P.LO_RANGE
    mid = 0.5 * (rng[0] + rng[1])
    phi_mid = coupler_dir(kind, side) + 90.0
    return (phi_mid - mid + 180.0) % 360.0 - 180.0 if kind == "L" else (phi_mid - mid) % 360.0


def lever_angle(kind, side, margin):
    return margin + lever_offset(kind, side)


def transmission(kind, side, margin):
    """Transmission angle between lever and coupler (deg, 90 = best)."""
    a = abs((lever_angle(kind, side, margin) - coupler_dir(kind, side)) % 180.0)
    return a if a <= 90 else 180 - a


def rest_margin(kind):
    return P.UP_REST if kind == "U" else P.LO_REST


def lid_ball(kind, side, margin):
    """Lid-end ball centre (H)."""
    phi = math.radians(lever_angle(kind, side, margin))
    return (P.LEVER * math.cos(phi), P.Y_EYE[side] + P.nasal(side) * P.LID_BALL_DY, P.LEVER * math.sin(phi))


def horn_ball(kind, side, margin):
    """Horn-end ball centre (H)."""
    name = LID_SERVO[(kind, side)]
    x, z = servo_axis_xz(name)
    phi = math.radians(lever_angle(kind, side, margin))
    ys = math.copysign(P.HORN_BALL_Y, P.SERVOS[name][0][1])
    return (x + P.LEVER * math.cos(phi), ys, z + P.LEVER * math.sin(phi))


# ------------------------------------------------------------------------------------- pan
def eye_pin(side, pan):
    """Eye crank pin in the cradle frame."""
    t = math.radians(pan)
    return (-P.CRANK * math.cos(t), P.Y_EYE[side] - P.CRANK * math.sin(t), P.COUPLER_Z)


def servo_pin(side, pan):
    t = math.radians(pan)
    ys = math.copysign(P.PAN_SERVO_Y, P.Y_EYE[side])
    return (-P.CRANK * math.cos(t), ys - P.CRANK * math.sin(t), P.COUPLER_Z)


def pan_transmission(pan):
    """Angle between crank (along -X at rest) and coupler (along Y): 90 - |pan|."""
    return 90.0 - abs(pan)


# ------------------------------------------------------------------------------------- lid envelope
def up_envelope(tilt):
    lo = max(P.UP_RANGE[0], P.UP_REST + tilt + P.UP_FOLLOW["closed"])
    hi = min(P.UP_RANGE[1], P.UP_REST + tilt + P.UP_FOLLOW["open_max"])
    return lo, hi


def lo_envelope(tilt):
    base = P.LO_REST + P.LO_FOLLOW["gain"] * tilt
    return max(P.LO_RANGE[0], base + P.LO_FOLLOW["low"]), min(P.LO_RANGE[1], base + P.LO_FOLLOW["high"])


def follow(tilt, du=0.0, dl=0.0):
    """Lid margins following gaze (firmware model, spec 2.5 / 8), clamped to the mechanical ranges."""
    u = min(max(P.UP_REST + tilt + du, P.UP_RANGE[0]), P.UP_RANGE[1])
    l = min(max(P.LO_REST + P.LO_FOLLOW["gain"] * tilt + dl, P.LO_RANGE[0]), P.LO_RANGE[1])
    return u, l


# ------------------------------------------------------------------------------------- transforms
def _rot_axis(axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def rot_about(point, axis, deg):
    M = np.eye(4)
    R = _rot_axis(axis, deg)
    p = np.asarray(point, float)
    M[:3, :3] = R
    M[:3, 3] = p - R @ p
    return M


def translate(v):
    M = np.eye(4)
    M[:3, 3] = v
    return M


def elev(deg, point=(0, 0, 0)):
    """Elevation increase about an axis parallel to Y = right-handed rotation about +Y by -deg."""
    return rot_about(point, (0, 1, 0), -deg)


def group_transform(group, pose):
    """4x4 transform (rest -> pose) for a motion group."""
    q = full(pose)
    T_tilt = elev(q["tilt"])
    if group == "fixed" or group.startswith("flex"):
        return np.eye(4)
    if group == "cradle":
        return T_tilt
    kind, _, side = group.partition("_")
    if kind in ("eye", "crank", "pcoup"):
        pan = q["pan_" + side]
        if kind == "eye":
            return T_tilt @ rot_about((0, P.Y_EYE[side], 0), (0, 0, 1), pan)
        if kind == "crank":
            ys = math.copysign(P.PAN_SERVO_Y, P.Y_EYE[side])
            return T_tilt @ rot_about((0, ys, 0), (0, 0, 1), pan)
        p0, p1 = np.array(eye_pin(side, 0.0)), np.array(eye_pin(side, pan))
        return T_tilt @ translate(p1 - p0)
    if kind in ("lidU", "lidL", "hornU", "hornL", "rodU", "rodL"):
        k = kind[-1]
        m = q[("up_" if k == "U" else "lo_") + side]
        d = m - rest_margin(k)
        if kind.startswith("lid"):
            return elev(d)
        if kind.startswith("horn"):
            x, z = servo_axis_xz(LID_SERVO[(k, side)])
            return elev(d, (x, 0, z))
        b0, b1 = np.array(horn_ball(k, side, rest_margin(k))), np.array(horn_ball(k, side, m))
        return translate(b1 - b0)
    if kind == "brow":
        b = q["brow_" + side]
        y0 = P.SERVOS["brow_" + side][0]
        # inner end is toward the nose: +Y for the right brow, -Y for the left
        sgn = 1.0 if side == "R" else -1.0
        return rot_about(y0, (1, 0, 0), sgn * b)
    raise KeyError(group)


def apply(M, pts):
    pts = np.asarray(pts, float)
    return pts @ M[:3, :3].T + M[:3, 3]


def table():
    """Kinematics summary for the docs (cad/out/kinematics.json)."""
    out = {"lids": {}, "pan": {}}
    for side in P.SIDES:
        for kind, rng in (("U", P.UP_RANGE), ("L", P.LO_RANGE)):
            tr = [transmission(kind, side, m) for m in np.linspace(rng[0], rng[1], 96)]
            out["lids"][LID_SERVO[(kind, side)]] = {
                "servo_axis_xz": servo_axis_xz(LID_SERVO[(kind, side)]),
                "coupler_len_xz": round(coupler_len(kind, side), 2),
                "coupler_dir_deg": round(coupler_dir(kind, side), 2),
                "lever_offset_deg": round(lever_offset(kind, side), 2),
                "lever_range_deg": [round(lever_angle(kind, side, rng[0]), 1), round(lever_angle(kind, side, rng[1]), 1)],
                "min_transmission_deg": round(min(tr), 1),
                "ball_y_offset": round(horn_ball(kind, side, 0)[1] - lid_ball(kind, side, 0)[1], 2),
            }
    out["pan"] = {"crank": P.CRANK, "coupler": P.COUPLER_L,
                  "transmission_deg_at_35": pan_transmission(35.0),
                  "crank_tip_sweep_x": [round(-P.CRANK, 2), round(-P.CRANK * math.cos(math.radians(35)), 2)],
                  "crank_tip_sweep_y": round(P.CRANK * math.sin(math.radians(35)), 2)}
    vg = {}
    for d in (150, 250, 400, 700, 1000, 2000):
        vg[d] = round(math.degrees(math.atan(P.IPD / 2 / d)), 2)
    out["vergence_per_eye_deg"] = vg
    return out
