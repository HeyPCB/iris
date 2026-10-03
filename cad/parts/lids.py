"""Nested visor lids (spec 2.5, 7.1 P11), built at their rest margins.

Each lid is a spherical lune centred on the eye centre that rotates about the Y axis through its own
poles, so the lid margins are great circles that meet at the canthi: the almond fissure comes from
the geometry. The poles carry the hub caps (bushings on Dia 3 pins). The upper lid (r 17.0-18.2) nests
inside the lower lid (r 18.4-19.6) everywhere, including at the caps, so the two lids of one eye
cannot touch whatever their angles.

The 9 mm drive lever is a tab of the lid's own spherical shell at the nasal pole, with an M2 ball
stud pointing toward the nose. The upper-lid lever points back; the lower-lid lever points forward
(see kinematics.lever_offset)."""
import math

from .. import kinematics as K
from .. import params as P
from ..geom import box, cyl, rot_elev, shell_sphere, sphere, wedge_y
from . import purchased


def _radii(kind):
    return P.R_UP if kind == "U" else P.R_LO


def lid(kind, side):
    yc = P.Y_EYE[side]
    c = (0.0, yc, 0.0)
    n = P.nasal(side)
    r_in, r_out = _radii(kind)
    m0 = K.rest_margin(kind)
    a0, a1 = (m0, m0 + P.SPAN_U) if kind == "U" else (m0 - P.SPAN_L, m0)
    lune = shell_sphere(c, r_in, r_out).intersect(wedge_y(c, a0, a1, r=40.0, y_half=30.0))
    cap_r = P.CAP_UP_R if kind == "U" else P.CAP_LO_R
    caps = shell_sphere(c, cap_r[0], cap_r[1]).intersect(cyl("y", c, P.CAP_RHO, yc - 30, yc + 30))
    # lever tab (nasal pole) in the lid's own shell band, at the lever angle
    phi = K.lever_angle(kind, side, m0)
    tab_r = (r_in, r_out) if kind == "U" else P.LO_TAB_R
    strip = box(0.0, P.LEVER_RHO, yc, yc + n * 30.0, -P.LEVER_W / 2, P.LEVER_W / 2)
    strip = strip.fuse(cyl("y", (P.LEVER_RHO, 0, 0), P.LEVER_W / 2, yc, yc + n * 30.0))
    strip = rot_elev(strip, phi, (0, 0, 0))
    tab = shell_sphere(c, tab_r[0], tab_r[1]).intersect(strip).intersect(cyl("y", c, P.LEVER_RHO + 2.6, yc - 30, yc + 30))
    tab = tab.intersect(box(-40, 40, yc + n * P.TAB_DY_MIN, yc + n * 30.0, -40, 40))
    # stud boss: from inside the tab out to just below the ball-link housing
    bx, bz = P.LEVER * math.cos(math.radians(phi)), P.LEVER * math.sin(math.radians(phi))
    boss_end = P.LID_BALL_DY - P.BALL["housing_t"] / 2 - 0.2
    boss = cyl("y", (bx, 0, bz), 2.25, yc + n * 12.0, yc + n * boss_end)
    boss = boss.cut(sphere(c, r_in if kind == "U" else r_in + 0.4))
    shell = lune.fuse(caps, tab).clean().cut(cyl("y", c, P.LID_BORE_D / 2, yc - 30, yc + 30))
    pilot = cyl("y", (bx, 0, bz), 0.8, yc + n * 12.0, yc + n * 25.0)            # M2 stud pilot
    return {"shell": shell.cut(pilot), "boss": boss.cut(pilot)}


def lid_stud(kind, side):
    m0 = K.rest_margin(kind)
    ball = K.lid_ball(kind, side, m0)
    n = P.nasal(side)
    base = (ball[0], ball[1] - n * 3.0, ball[2])
    return purchased.ball_stud(ball, base)


def lid_pushrod(kind, side):
    m0 = K.rest_margin(kind)
    return purchased.pushrod(K.lid_ball(kind, side, m0), K.horn_ball(kind, side, m0), "y")
