"""Tilt cradle: spine and rear plate (P5), forks (P6), temple arms (P7). Rest pose, H frame.
The cradle tilts about the Y axis: right side on a fixed Dia 3 pin in an MR63ZZ bearing, left side
driven by the tilt servo through the P8 tongue (cad/parts/linkage.py)."""
import math

from .. import params as P
from ..geom import box, cyl, fuse_all, prism


def spine():
    """P5: two rails behind the eyes, side walls, rear plate with the four B1 bosses, the radial drive
    slot block for P8, and the FPC window on the right."""
    x0, x1 = P.RAIL_X
    rt = box(x0, x1, -P.RAIL_TOP["y"], P.RAIL_TOP["y"], *P.RAIL_TOP["z"])
    rb = box(x0, x1, -P.RAIL_BOT["y"], P.RAIL_BOT["y"], *P.RAIL_BOT["z"])
    px0, px1 = P.REAR_PLATE_X
    plate = box(px0, px1, -P.REAR_PLATE_Y, P.REAR_PLATE_Y, -P.REAR_PLATE_Z, P.REAR_PLATE_Z)
    plate = plate.cut(box(px0 - 1, px1 + 1, -P.ANTENNA_NOTCH["y"], P.ANTENNA_NOTCH["y"], P.ANTENNA_NOTCH["z0"], 40))
    walls = []
    for s in (1, -1):
        wy = sorted((s * P.SIDE_WALL_Y[0], s * P.SIDE_WALL_Y[1]))
        walls.append(box(px0, x1, wy[0], wy[1], P.RAIL_BOT["z"][0], P.RAIL_TOP["z"][1]))
        walls.append(box(px0, -55.0, wy[0], wy[1], -P.REAR_PLATE_Z, P.REAR_PLATE_Z))
    bosses = [cyl("x", (0, y, z), P.B1_BOSS_D / 2, *P.B1_BOSS_X) for y, z in P.B1["holes_yz"]]
    D = P.DRIVE_BLOCK
    drive = box(D["x"][0], D["x"][1], D["y"][0], D["y"][1], -D["z"], D["z"])
    s = fuse_all([rt, rb, plate, drive] + walls + bosses)
    for y, z in P.B1["holes_yz"]:
        s = s.cut(cyl("x", (0, y, z), P.M2_INSERT_HOLE / 2, P.B1_BOSS_X[1] - 4.0, P.B1_BOSS_X[1] + 1))
    S = P.DRIVE_SLOT
    s = s.cut(box(S["x"][0], S["x"][1], D["y"][0] - 1, D["y"][1] + 1, -S["w"] / 2, S["w"] / 2))
    # FPC window through the right side wall (camera FPC turns +Y along B1's front face into J1)
    s = s.cut(box(-53.2, -48.2, -P.SIDE_WALL_Y[1] - 1, -P.SIDE_WALL_Y[0] + 1, -4.2, 4.2))
    # ring-wire window through the left side wall (B1 J3 RING_L opens toward +Y at Y +39.2)
    s = s.cut(box(-53.2, -47.2, P.SIDE_WALL_Y[0] - 1, P.SIDE_WALL_Y[1] + 1, -4.5, 4.5))
    # fork mounting holes (M2, along X through the rails)
    for y in P.Y_EYE.values():
        for z in (9.5, -9.5):
            s = s.cut(cyl("x", (0, y, z), 1.1, x0 - 1, x1 + 1))
    # temple-arm joints at the bottom-rail ends
    for sy in (1, -1):
        s = s.cut(cyl("y", (-44.0, 0, -9.5), 0.8, sy * 66.0, sy * 74.0))
    return s.clean()


def fork(side):
    """P6: inside-out fork. Spine behind the eye, two arms entering through the rear opening, Dia 2 pole
    pins pressed into the arm tips."""
    y = P.Y_EYE[side]
    w = P.FORK_ARM_W / 2
    sx0, sx1 = P.FORK_SPINE_X
    sp = box(sx0, sx1, y - w, y + w, -P.FORK_SPINE_Z, P.FORK_SPINE_Z)
    arms = [box(P.FORK_ARM_X[0] - 0.5, P.FORK_ARM_X[1], y - w, y + w, s * P.FORK_ARM_Z[0], s * P.FORK_ARM_Z[1])
            for s in (1, -1)]
    # root gussets between spine and arms
    gus = []
    for s in (1, -1):
        g = prism([(sx1, s * P.FORK_ARM_Z[0]), (sx1 + 4.0, s * P.FORK_ARM_Z[0]), (sx1, s * (P.FORK_ARM_Z[0] - 4.0))],
                  "xz", y - w, y + w)
        gus.append(g)
    f = fuse_all([sp] + arms + gus)
    f = f.cut(cyl("z", (0, y, 0), P.FORK_PIN_BORE / 2, -12, 12))
    for z in (9.5, -9.5):
        f = f.cut(cyl("x", (0, y, z), 1.1, sx0 - 1, sx1 + 1))
    return f.clean()


def temple_arm(side):
    """P7: temple arm. Pivot boss on the Y axis (right: MR63ZZ seat on the fixed temple pin; left: loose
    bushing), pan servo ear ledges, lid stub-pin boss, window for the pan crank sweep."""
    s = math.copysign(1.0, P.Y_EYE[side])
    ya, yb = P.TEMPLE_ARM_Y
    pts = [(6.0, 5.5), (6.0, -6.0), (13.0, -14.0), (13.0, -32.0), (-25.0, -32.0), (-25.0, -20.5),
           (-47.0, -13.0), (-47.0, -6.0), (-6.0, 5.5)]
    plate = prism(pts, "xz", s * ya, s * yb)
    N = P.CRANK_NOTCH
    plate = plate.cut(box(N["x"][0], N["x"][1], s * (ya - 1), s * (yb + 1), N["z"][0], N["z"][1]))
    piv = cyl("y", (0, 0, 0), P.PIVOT_BOSS["d"] / 2, s * P.PIVOT_BOSS["y"][0], s * P.PIVOT_BOSS["y"][1])
    stub = cyl("y", (0, 0, 0), P.LID_STUB_BOSS["d"] / 2, s * P.LID_STUB_BOSS["y"][0], s * P.LID_STUB_BOSS["y"][1] + s * 0.01)
    ez0, ez1 = -31.5, -28.85
    ledges = [box(-25.0, -17.7, s * 59.4, s * ya, ez0, ez1), box(6.3, 13.0, s * 59.4, s * ya, ez0, ez1)]
    a = fuse_all([plate, piv, stub] + ledges)
    for x in (-19.95, 8.55):
        a = a.cut(cyl("z", (x, s * P.PAN_SERVO_Y, 0), P.M2_INSERT_HOLE / 2, ez0 - 1, ez1 + 1))
    a = a.cut(cyl("y", (0, 0, 0), P.LID_PIN_D / 2 - 0.05, s * 50, s * 71.0))       # temporal lid pin (press)
    if side == "R":
        a = a.cut(cyl("y", (0, 0, 0), P.MR63["od"] / 2, s * (yb - P.MR63["w"]), s * (yb + 1)))
        a = a.cut(cyl("y", (0, 0, 0), 1.7, s * 70.9, s * (yb + 1)))
    else:
        a = a.cut(cyl("y", (0, 0, 0), (P.LID_PIN_D + 0.2) / 2, s * 70.9, s * (yb + 1)))   # loose bushing
    a = a.cut(cyl("y", (-44.0, 0, -9.5), 1.1, s * (ya - 1), s * (yb + 1)))          # rail joint
    return a.clean()
