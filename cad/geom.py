"""Small geometry helpers on top of CadQuery solids (cq.Solid / cq.Compound / cq.Shape).

Everything is built directly in the head frame H (see params.py) unless a docstring says otherwise.
"""
import math

import cadquery as cq

V = cq.Vector
AX = {"x": V(1, 0, 0), "y": V(0, 1, 0), "z": V(0, 0, 1)}


def axis_vec(spec):
    """'+x', '-y', ... -> unit vector."""
    s = -1.0 if spec[0] == "-" else 1.0
    return AX[spec[-1]] * s


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from bounds."""
    lo = V(min(x0, x1), min(y0, y1), min(z0, z1))
    return cq.Solid.makeBox(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0), lo)


def cyl(axis, c, r, a0, a1):
    """Cylinder of radius r along an axis ('x', 'y' or 'z') through point c, from coordinate a0 to a1
    along that axis."""
    i = "xyz".index(axis)
    p = list(c)
    lo, hi = min(a0, a1), max(a0, a1)
    p[i] = lo
    return cq.Solid.makeCylinder(r, hi - lo, V(*p), AX[axis])


def cyl_pts(p0, p1, r):
    """Cylinder between two 3D points."""
    a, b = V(*p0), V(*p1)
    d = b - a
    return cq.Solid.makeCylinder(r, d.Length, a, d.normalized())


def tube(axis, c, r_in, r_out, a0, a1):
    lo, hi = min(a0, a1), max(a0, a1)
    return cyl(axis, c, r_out, lo, hi).cut(cyl(axis, c, r_in, lo - 1, hi + 1))


def sphere(c, r):
    return cq.Solid.makeSphere(r, V(*c), angleDegrees1=-90, angleDegrees2=90)


def shell_sphere(c, r_in, r_out):
    return sphere(c, r_out).cut(sphere(c, r_in))


def ellipsoid(c, a):
    """Ellipsoid with semi-axes a = (ax, ay, az) centred at c."""
    s = cq.Solid.makeSphere(1.0, V(0, 0, 0), angleDegrees1=-90, angleDegrees2=90)
    m = cq.Matrix([[a[0], 0, 0, c[0]], [0, a[1], 0, c[1]], [0, 0, a[2], c[2]]])
    return s.transformGeometry(m)


def cone(apex, direction, half_angle_deg, length):
    """Solid cone with its apex at `apex`, opening along `direction`."""
    d = V(*direction).normalized()
    return cq.Solid.makeCone(0.0, length * math.tan(math.radians(half_angle_deg)), length, V(*apex), d)


def _plane_pts(pts, plane, offset):
    out = []
    for u, v in pts:
        if plane == "xz":
            out.append(V(u, offset, v))
        elif plane == "yz":
            out.append(V(offset, u, v))
        else:
            out.append(V(u, v, offset))
    return out


def prism(pts, plane, a0, a1):
    """Extrude a closed polygon. plane 'xz': pts are (x, z), extruded along Y from a0 to a1.
    'yz': (y, z) along X. 'xy': (x, y) along Z."""
    lo, hi = min(a0, a1), max(a0, a1)
    w = cq.Wire.makePolygon(_plane_pts(pts, plane, lo), close=True)
    f = cq.Face.makeFromWires(w)
    n = {"xz": V(0, 1, 0), "yz": V(1, 0, 0), "xy": V(0, 0, 1)}[plane]
    return cq.Solid.extrudeLinear(f, n * (hi - lo))


def arc_pts(cx, cz, r, a0, a1, n=24):
    """Points on a circular arc in a 2D plane (degrees)."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def wedge_y(c, a0, a1, r=60.0, y_half=40.0, n=48):
    """Angular sector about an axis parallel to Y through c, between elevation angles a0..a1 (deg),
    elevation = atan2(z, x). Returns a prism spanning y_c +- y_half."""
    if a1 - a0 >= 359.9:
        return cyl("y", c, r, c[1] - y_half, c[1] + y_half)
    pts = [(c[0], c[2])] + arc_pts(c[0], c[2], r, a0, a1, n)
    return prism(pts, "xz", c[1] - y_half, c[1] + y_half)


def frame_location(cols, origin):
    """cq.Location for the rigid map local -> H whose columns are the local axes `cols` (3 unit
    vectors) and whose origin is `origin`."""
    from OCP.gp import gp_Trsf
    a, b, c = cols
    t = gp_Trsf()
    t.SetValues(a.x, b.x, c.x, origin[0], a.y, b.y, c.y, origin[1], a.z, b.z, c.z, origin[2])
    return cq.Location(t)


def rot(shape, axis_pt, axis_dir, deg):
    """Right-handed rotation about an axis."""
    p = V(*axis_pt)
    return shape.rotate(p, p + V(*axis_dir), deg)


def rot_elev(shape, deg, c=(0, 0, 0)):
    """Increase elevation (atan2(z, x)) by deg about an axis parallel to Y through c."""
    return rot(shape, c, (0, 1, 0), -deg)


def mirror_y(shape):
    """Mirror across the XZ plane (Y -> -Y)."""
    return shape.mirror("XZ", (0, 0, 0))


def fuse_all(shapes):
    shapes = [s for s in shapes if s is not None]
    out = shapes[0]
    if len(shapes) > 1:
        out = out.fuse(*shapes[1:])
    return out.clean()


def rounded_rect_pts(w, h, r, cx=0.0, cy=0.0, n=8):
    """Closed rounded rectangle polygon (u, v) centred at (cx, cy)."""
    pts = []
    corners = [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
               (w / 2 - r, -h / 2 + r, 270)]
    for x, y, a in corners:
        for i in range(n + 1):
            t = math.radians(a + 90.0 * i / n)
            pts.append((cx + x + r * math.cos(t), cy + y + r * math.sin(t)))
    return pts


def largest_solid(shape):
    """Return the largest solid of a compound (booleans can leave slivers)."""
    sols = shape.Solids()
    if len(sols) <= 1:
        return sols[0] if sols else shape
    return max(sols, key=lambda s: s.Volume())


def solid_of(shape):
    """Single solid if the shape is one, else a compound of its solids."""
    sols = shape.Solids()
    if len(sols) == 1:
        return sols[0]
    return cq.Compound.makeCompound(sols)
