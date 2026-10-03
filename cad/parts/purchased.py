"""Envelopes of purchased parts. These are simplified envelopes drawn from datasheet main dimensions,
not vendor CAD:

  SCS0009 servo   Feetech SCS0009 product specification 2020-11-23, p.6 outline drawing [FT9]
  OV2640 module   Union Image ZY-XSF3M2640B module drawing, Seeed OV2640 datasheet p.7 [SEEED]
  MR63ZZ          3 x 6 x 2.5 mm deep-groove bearing (standard size)
  M2 ball link    generic RC ball link with a 4.8 mm ball (est. housing 6.6 x 4.0 mm)
  dowel pins, magnets, speaker: nominal sizes from the spec's purchased-parts list (spec 7.2)
"""
import cadquery as cq

from .. import params as P
from ..geom import V, axis_vec, box, cyl, cyl_pts, frame_location, sphere, tube


def servo_frame(out_pt, shaft, long):
    """Location from servo-local (u along the long side, v across, h along the shaft; origin at the
    output point) to H."""
    s = axis_vec(shaft)
    l = axis_vec(long)
    w = s.cross(l)
    return frame_location((l, w, s), out_pt)


def scs0009_local():
    """SCS0009 envelope in servo-local coordinates. Origin = the spec's output point (1.0 mm above the
    spline tip, on the shaft axis). +h toward the horn; +u along the long side."""
    S = P.SV
    h_cover = -P.SV_OUT_TO_COVER                 # -4.2
    h_bottom = h_cover - S["H_COVER"]            # -29.45
    h_case = h_bottom + S["H_CASE"]              # -8.0
    u0 = -(S["L"] / 2 - S["SHAFT_OFF"])          # near end: -5.95
    u1 = u0 + S["L"]                             # far end: +17.35
    uc = (u0 + u1) / 2                           # case centre: +5.7
    w2 = S["W"] / 2
    case = box(u0, u1, -w2, w2, h_bottom, h_case)
    cover = box(u0, u0 + S["COVER_L"], -w2, w2, h_case - 0.01, h_cover)
    ear = box(uc - S["EAR_L"] / 2, uc + S["EAR_L"] / 2, -S["EAR_W"] / 2, S["EAR_W"] / 2,
              h_bottom + S["EAR_Z"][0], h_bottom + S["EAR_Z"][1])
    body = case.fuse(cover, ear).clean()
    for du in (-S["EAR_HOLE"] / 2, S["EAR_HOLE"] / 2):
        body = body.cut(cyl("z", (uc + du, 0, 0), S["HOLE_D"] / 2, h_bottom, h_cover))
    spline = cyl("z", (0, 0, 0), S["SPLINE_D"] / 2, h_cover - 0.01, h_cover + S["SPLINE_H"])
    return {"body": body, "spline": spline,
            "ear_holes_u": [uc - S["EAR_HOLE"] / 2, uc + S["EAR_HOLE"] / 2],
            "ear_h": (h_bottom + S["EAR_Z"][0], h_bottom + S["EAR_Z"][1]),
            "case_u": (u0, u1), "cover_h": h_cover, "case_h": h_case, "bottom_h": h_bottom}


def scs0009(name):
    """SCS0009 envelope placed at its spec position. Returns dict body/spline (H frame) + metadata."""
    out_pt, shaft, long = P.SERVOS[name]
    m = servo_frame(out_pt, shaft, long)
    loc = scs0009_local()
    res = {k: loc[k].moved(m) for k in ("body", "spline")}
    res["matrix"] = m
    res["local"] = loc
    return res


def servo_point(name, u, v, h):
    """Map a servo-local point to H."""
    out_pt, shaft, long = P.SERVOS[name]
    s, l = axis_vec(shaft), axis_vec(long)
    w = s.cross(l)
    p = V(*out_pt) + l * u + w * v + s * h
    return (p.x, p.y, p.z)


def ov2640_eye(side, neck=True):
    """OV2640 module envelope in the EYE frame of `side` (x optical axis, origin at the eye centre).
    The FPC neck leaves the holder temporally (spec 3.2). neck=False gives the dummy-module shape."""
    st = P.CAM_STACK
    x0 = P.CAM_BACK_X
    h = P.CAM_HOLDER / 2
    holder = box(x0, x0 + st["holder"], -h, h, -h, h)
    lens = cyl("x", (0, 0, 0), P.CAM_LENS_D / 2, x0 + st["holder"] - 0.01, x0 + st["lens"])
    step = cyl("x", (0, 0, 0), P.CAM_STEP_D / 2, x0 + st["lens"] - 0.01, x0 + st["step"])
    parts = [lens, step]
    if neck:
        t = -P.nasal(side)                  # temporal sign in y
        parts.append(box(x0, x0 + P.CAM_FPC_T, t * (h - 0.01), t * (h + 2.2), -P.CAM_FPC_W / 2, P.CAM_FPC_W / 2))
    return holder.fuse(*parts).clean()


def ball_link(ball_c, stud_axis, other_c):
    """M2 ball-link envelope: housing around the ball (axis = stud axis) plus the shank toward the
    other end of the rod."""
    B = P.BALL
    a = axis_vec(stud_axis)
    c = V(*ball_c)
    hous = cq.Solid.makeCylinder(B["housing_d"] / 2, B["housing_t"], c - a * (B["housing_t"] / 2), a)
    d = (V(*other_c) - c)
    d = V(d.x, d.y, d.z) - a * d.dot(a)       # shank lies in the housing mid-plane
    d = d.normalized()
    s0 = c + d * (B["housing_d"] / 2 - 0.6)
    shank = cq.Solid.makeCylinder(B["shank_d"] / 2, B["shank_l"], s0, d)
    return hous.fuse(shank).clean()


def pushrod(c0, c1, stud_axis):
    """Two ball links plus the M2 rod between them (centres c0, c1)."""
    B = P.BALL
    l0 = ball_link(c0, stud_axis, c1)
    l1 = ball_link(c1, stud_axis, c0)
    a, b = V(*c0), V(*c1)
    d = (b - a).normalized()
    r0 = a + d * (B["housing_d"] / 2 + B["shank_l"] - 1.5)
    r1 = b - d * (B["housing_d"] / 2 + B["shank_l"] - 1.5)
    rod = cyl_pts((r0.x, r0.y, r0.z), (r1.x, r1.y, r1.z), B["rod_d"] / 2)
    return l0.fuse(l1, rod).clean()


def ball_stud(ball_c, base_c):
    """M2 ball stud: ball plus shaft down to the base point."""
    B = P.BALL
    return sphere(ball_c, B["d"] / 2).fuse(cyl_pts(base_c, ball_c, B["stud_d"] / 2)).clean()


def mr63(side_sign):
    """MR63ZZ in the right temple arm, outer face flush at |Y| 74."""
    y1 = side_sign * P.TEMPLE_ARM_Y[1]
    y0 = y1 - side_sign * P.MR63["w"]
    return tube("y", (0, 0, 0), P.MR63["id"] / 2, P.MR63["od"] / 2, y0, y1)


def pin_y(r, y0, y1):
    return cyl("y", (0, 0, 0), r, y0, y1)


def speaker():
    c = P.SPEAKER["c"]
    r = P.SPEAKER["d"] / 2
    can = cyl("x", c, r, c[0], c[0] + 2.0)
    mag = cyl("x", c, 9.0, c[0] - P.SPEAKER["t"] + 2.0, c[0] + 0.01)
    return can.fuse(mag).clean()


def magnet(c, axis):
    i = "xyz".index(axis)
    return cyl(axis, c, P.MAGNET["d"] / 2, c[i] - P.MAGNET["t"] / 2, c[i] + P.MAGNET["t"] / 2)
