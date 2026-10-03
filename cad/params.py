"""Iris mechanism parameters. Every dimension the CAD uses lives here.

Head frame H (all mm, degrees):
  origin midway between the two eye rotation centres,
  +X forward (out of the face), +Y robot-left, +Z up.
  Right eye centre (0, -39, 0), left eye centre (0, +39, 0). The interocular axis is the Y axis.

Sources: `spec.md` is the Iris system specification v0.1 (section numbers in the comments).
Rows marked BINDING come from spec section 2.8 or section 4 and are contracts with the board designers.
Rows marked CHANGED differ from a non-binding spec value; docs/mechanism.md says why.

Angle conventions (used everywhere, see cad/kinematics.py):
  tilt  + = look up. Rotates the cradle about the Y axis so that +X moves toward +Z.
  pan   + = eye turns toward +Y (rotation about +Z through the eye centre).
  lid   margin elevation, atan2(z, x) of the lid margin about the Y axis through the eye centre.
  brow  + = inner (nasal) end up.
"""

# ----------------------------------------------------------------------------------------------
# Eyes (spec 1.2, 2.2)
IPD = 78.0                                  # BINDING eye centre spacing
Y_EYE = {"R": -IPD / 2, "L": +IPD / 2}      # BINDING eye centres (0, +-39, 0)
SIDES = ("R", "L")


def nasal(side):
    """+1 if the nasal direction of this eye is +Y (right eye), -1 for the left eye."""
    return 1.0 if side == "R" else -1.0


EYE_R = 15.0                 # BINDING sclera outer radius (eyeball diameter 30.0)
EYE_R_IN = 13.4              # sclera inner radius (1.6 mm wall)
OPEN_HALF = 65.0             # CHANGED (spec 60): rear opening cone half-angle about -x; shell spans 0..115 deg
CORNEA_R = 9.75              # cornea outer radius
CORNEA_WALL = 0.8
APEX_X = 16.40               # corneal apex, eye frame
CORNEA_C = APEX_X - CORNEA_R # cornea sphere centre on the optical axis (6.65)
LIMBUS_D = 14.64             # limbus bore in the sclera
IRIS_FRONT_X = 11.9          # iris front plane
IRIS_T = 0.8                 # iris disc thickness (x 11.1 .. 11.9)
IRIS_D = 14.50               # disc diameter (slip fit in the 14.64 limbus bore)
PUPIL_D = 5.6                # pupil hole
SLEEVE_OD = 6.6              # black pupil sleeve, ID = PUPIL_D
SLEEVE_BACK_X = 9.10         # sleeve runs back over the lens step (step top at 9.90)
CAVITY_R_LED = 8.0           # iris-disc cone ring: inner radius over the LED band (LED corners at r 7.67)
CAVITY_X_LED = 8.9           # ... up to this x, then the cone tapers to the disc edge
CORNEA_BASE_X = IRIS_FRONT_X # cornea base ring seats on the iris disc

# Pole pivots (spec 2.2, 2.4, 2.8)
POLE_BOSS_D = 5.0            # BINDING boss diameter
POLE_BOSS_Z0 = 9.8           # BINDING boss inner face |z| (to the shell)
POLE_PIN_D = 2.0             # BINDING pin diameter
POLE_BORE_D = 2.05           # running bore in the boss and shell
POLE_PIN_Z = (6.8, 14.8)     # Dia 2 x 8 dowel, |z| span (pressed in the fork arm, runs in the boss)

# Pan keel and crank pin on the eye (spec 2.2, 2.4)
CRANK = 14.0                 # BINDING crank length (eye and servo side)
COUPLER_Z = -16.0            # BINDING crank / coupler plane (ball centres)
KEEL_W = 4.0                 # keel width (y)
KEEL_Z = (-13.4, -10.1)      # keel band behind the shell (0.6 below the fork arm, 0.6 above the ball link)
KEEL_X = (-15.8, 2.0)

# Camera module envelope: Union Image ZY-XSF3M2640B, drawing [SEEED] p.7 (simplified, labelled envelope)
CAM_HOLDER = 8.5             # holder 8.5 x 8.5
CAM_BACK_X = 4.36            # module back face, eye frame (spec 2.2)
CAM_STACK = {"fpc": 0.35, "holder": 2.65, "lens": 4.65, "step": 5.54}   # heights from the back face
CAM_LENS_D = 7.2
CAM_STEP_D = 5.4
CAM_FPC_W = 6.0
CAM_FPC_T = 0.15

# B3 iris ring (spec 4.4, BINDING outline)
B3_D = 18.0
B3_ID = 7.6
B3_FLAT = 8.4
B3_T = 0.8
B3_BX = 7.0                  # B face, eye frame
B3_F_H = 0.9                 # F-side height (WS2812C-2020 0.84)
B3_B_H = 0.6                 # B-side height outside the 8.7 mm keepout square
B3_LED_R = (5.2, 7.7)        # LED band envelope (12 x 2.0 mm LEDs centred on r 6.6)
B3_KEEPOUT_SQ = 8.7

# Eye carrier (P4)
CARRIER_X0 = 2.8             # back face of the carrier disc
CARRIER_POCKET = 8.6         # camera holder pocket
CARRIER_RING_ID = 18.2       # B3 seat
CARRIER_RING_FLAT = 8.5      # key flat distance from the centre (B3 flat at 8.4)
FPC_SLOT = (7.0, 1.2)        # FPC exit slot (z height, y width), temporal
RING_WIRE_HOLE_D = 2.0

# ----------------------------------------------------------------------------------------------
# Pan forks (spec 2.4, 7.1 P6)
FORK_ARM_W = 4.0             # BINDING (y)
FORK_ARM_Z = (7.0, 9.5)      # BINDING |z| band
FORK_ARM_X = (-40.0, 1.0)    # arm runs from the spine to just past the pin axis
FORK_SPINE_X = (-42.0, -40.0)
FORK_SPINE_Z = 12.0          # spine |z| (feet overlap the rails)
FORK_PIN_BORE = 1.95         # press fit for the Dia 2 pin

# Pan servo and coupler (spec 2.4, 2.8)
PAN_SERVO_Y = 65.0           # BINDING |Y| of the pan servo output axis
COUPLER_L = PAN_SERVO_Y - IPD / 2   # 26.0, BINDING
PAN_CRANK_ARM_Z = (-13.4, -11.0)    # crank arm above the coupler plane (0.6 over the link); stud points down
PAN_CRANK_HUB_D = 7.0
PAN_CRANK_HUB_Z0 = -19.6     # 0.6 mm above the gear cover top (-20.2)

# ----------------------------------------------------------------------------------------------
# SCS0009 envelope, Feetech product specification 2020-11-23 [FT9] p.6 (labelled envelope, simplified)
SV = {
    "L": 23.3,           # case length
    "W": 12.1,           # case width
    "H_CASE": 21.45,     # case top (main) above the bottom
    "H_COVER": 25.25,    # gear cover top above the bottom
    "COVER_L": 15.1,     # gear cover length from the shaft end of the case (est. from the drawing)
    "SPLINE_D": 3.95,    # 20T spline OD
    "SPLINE_H": 3.2,     # spline above the cover (28.45 - 25.25)
    "SHAFT_OFF": 5.7,    # shaft from the case centre toward the near end
    "EAR_L": 32.5,       # overall ear length (16.25 each side of the case centre)
    "EAR_HOLE": 28.5,    # ear hole spacing (14.25 each side)
    "EAR_Z": (16.8, 18.4),  # ear band above the bottom
    "EAR_W": 11.0,       # ear tab width (est.)
    "HOLE_D": 2.0,
    "OUT_ABOVE_SPLINE": 1.0,  # the spec's "output point" is 1.0 mm above the spline tip
}
SV_OUT_TO_COVER = SV["SPLINE_H"] + SV["OUT_ABOVE_SPLINE"]   # 4.2 mm from output point to cover top

# Servo outputs: (output point, shaft direction, long-side direction). BINDING spec 2.3, 2.5, 2.6, 2.8
SERVOS = {
    "tilt":   ((0.0, 15.95, 0.0), "+y", "-x"),
    "pan_R":  ((0.0, -PAN_SERVO_Y, COUPLER_Z), "+z", "-x"),
    "pan_L":  ((0.0, +PAN_SERVO_Y, COUPLER_Z), "+z", "-x"),
    "lidU_L": ((-8.0, 15.0, 20.5), "+y", "+x"),
    "lidU_R": ((-8.0, -15.0, 34.0), "-y", "+x"),
    "lidL_L": ((-8.0, 15.0, -20.5), "+y", "+x"),
    "lidL_R": ((-8.0, -15.0, -34.0), "-y", "+x"),
    "brow_R": ((0.0, -54.0, 38.0), "+x", "+z"),
    "brow_L": ((0.0, 54.0, 38.0), "+x", "+z"),
}
SERVO_IDS = {"pan_R": 1, "pan_L": 2, "tilt": 3, "lidU_R": 4, "lidU_L": 5, "lidL_R": 6, "lidL_L": 7,
             "brow_R": 8, "brow_L": 9}           # BINDING spec 5 port map

# ----------------------------------------------------------------------------------------------
# Tilt cradle (spec 2.3, 7.1 P5/P7/P8)
TILT_RANGE = (-30.0, 25.0)   # BINDING
RAIL_X = (-46.0, -42.0)      # BINDING rails
RAIL_TOP = {"z": (7.0, 12.0), "y": 46.0}
RAIL_BOT = {"z": (-12.0, -7.0), "y": 73.0}
REAR_PLATE_X = (-60.6, -57.6)   # behind B1's B-side parts (B face -53.6, parts <= 3.6)
REAR_PLATE_Y = 45.0
REAR_PLATE_Z = 22.0
B1_BOSS_D = 5.0
B1_BOSS_X = (-57.6, -53.6)   # BINDING boss faces at X -53.6
ANTENNA_NOTCH = {"y": 14.0, "z0": 8.0}   # no plastic within 5 mm of the WROOM antenna (spec 7.1 P5)
SIDE_WALL_Y = (41.0, 45.0)
DRIVE_BLOCK = {"x": (-46.0, -36.5), "y": (15.0, 18.0), "z": 7.0}
DRIVE_SLOT = {"x": (-47.0, -36.8), "w": 3.3}   # open at the back: the cradle slides forward onto the P8 pin

TEMPLE_ARM_Y = (71.6, 74.0)  # spec |Y| 71-74; inner face 0.55 mm clear of the pan servo case
PIVOT_BOSS = {"d": 10.0, "y": (70.0, 74.0)}
MR63 = {"od": 6.0, "id": 3.0, "w": 2.5}      # MR63ZZ bearing 3 x 6 x 2.5
TEMPLE_PIN_Y = (71.5, 84.0)  # right temple pin: frame plate (84) to bearing (BINDING support region 74-80)
LID_STUB_BOSS = {"d": 7.0, "y": (60.8, 70.0)}
CRANK_NOTCH = {"x": (-18.8, -1.0), "z": (-19.8, -9.4)}

TONGUE = {"hub_d": 9.0, "y": (12.25, 14.5), "hub_y1": 15.95, "x_end": -40.0, "w0": 9.0, "w1": 7.0,
          "pin_d": 3.0, "pin_y1": 17.5}

# ----------------------------------------------------------------------------------------------
# Lids (spec 2.5, 2.8)
R_UP = (17.0, 18.2)          # BINDING upper lid shell
R_LO = (18.4, 19.6)          # BINDING lower lid shell
UP_REST, LO_REST = 19.0, -20.0
UP_RANGE = (-40.0, 55.0)     # BINDING mechanical ranges
LO_RANGE = (-50.0, -6.0)
SPAN_U = 72.0                # shell extent behind the upper margin (covers the top of the opening when closed)
SPAN_L = 30.0                # shell extent below the lower margin
CAP_RHO = 3.5                # hub caps at the canthi (both poles)
CAP_UP_R = (16.0, R_UP[1])   # upper cap thickened inward (sclera at 15.0)
CAP_LO_R = (R_LO[0], 20.8)   # lower cap thickened outward
LID_PIN_D = 3.0
LID_BORE_D = 3.2
LEVER = 9.0                  # BINDING lever length on the nasal hubs
LEVER_W = 5.0                # lever tab width
LEVER_RHO = 11.6             # tab reaches past the stud
TAB_DY_MIN = 12.0            # lever tabs start 12 mm toward the nose (the panned eye keel stays inside 11 mm)
LO_TAB_R = (R_LO[0], R_LO[1])   # lower lever tab (same band as the shell; shank of its own link passes 0.7 mm above)
LID_BALL_DY = 21.3           # lid-end ball centre, distance from the eye centre toward the nose
MARGIN_ROUND = 0.5

# Lid firmware envelope (spec 2.5, 8): margins follow tilt, plus blink / expression offsets
UP_FOLLOW = {"closed": -37.0, "open_max": 36.0}   # du offsets from (UP_REST + tilt); blink closes to -18 at tilt 0
LO_FOLLOW = {"gain": 0.5, "low": -30.0, "high": 14.0}

# Lid servo horns (P17)
HORN_HUB_D = 7.0
HORN_PLATE = (15.0, 16.3)    # |Y| band of the printed horn arm (clears the opposite lid servo cases)
HORN_BALL_Y = 18.5           # |Y| of the horn-end ball centre
HORN_HUB_Y0 = 11.3           # 0.5 mm above the gear cover (|Y| 10.8)

# Ball links and studs (M2, purchased; envelope)
BALL = {"d": 4.8, "stud_d": 2.0, "housing_d": 6.6, "housing_t": 4.0, "shank_d": 3.6, "shank_l": 5.0,
        "rod_d": 2.0}

# ----------------------------------------------------------------------------------------------
# Brows (spec 2.6)
BROW_RANGE = (-20.0, 20.0)
BROW_LEN = 45.0
BROW_PIVOT_FRAC = 1.0 / 3.0  # pivot at the outer third
BROW_H = 6.0
BROW_T = 4.0
BROW_HUB_D = 6.0
BROW_HOLE_D = 10.0

# ----------------------------------------------------------------------------------------------
# Head frame, skull, base, shells
HEAD = {"x": (-113.5, 29.0), "y": 88.0, "z": (-67.0, 78.0), "wall": 2.5,
        "r_front": 14.0, "r_rear": 24.0, "r_top": 20.0}
FACE_SEAM_X = -12.0          # face shell / back cover split
SIDE_PLATE_Y = (80.0, 84.0)
TOP_BRIDGE_Z = (64.0, 67.0)
BASE_Z = (-70.0, -67.0)
COLUMN_Y = 2.35              # centre column plate half-thickness (lid servo ears clamp on both faces)
COLUMN_X = (-24.0, 15.5)
EYE_SOCKET = {"cx": 33.5, "a": (12.0, 32.0, 24.0)}   # ellipsoid carved into the face plane
EYE_OPENING = {"w": 37.0, "up": 13.0, "lo": 11.0}    # almond opening per eye (spec ~40 x 24; canthi at +-18.5)
NOSE = {"c": (28.5, 0.0, -15.0), "a": (10.0, 7.5, 16.0)}
SPEAKER = {"d": 28.0, "t": 5.0, "c": (18.0, 0.0, -50.0)}   # c = back of the cone rim
MAGNET = {"d": 6.0, "t": 3.0}

# Boards (spec 4, BINDING)
B1 = {"w": 80.0, "h": 40.0, "t": 1.6, "fillet": 2.0, "f_x": -52.0, "f_h": 4.5, "b_h": 3.6,
      "holes_yz": [(-36, 16), (36, 16), (-36, -16), (36, -16)]}
B2 = {"w": 64.0, "h": 80.0, "t": 1.6, "fillet": 3.0, "f_z": -60.0, "f_h": 12.0, "b_h": 2.0,
      "x": (-110.0, -30.0), "holes_xy": [(-34, 28), (-34, -28), (-106, 28), (-106, -28)]}
B4 = {"w": 116.0, "h": 12.0, "t": 1.6, "fillet": 2.0, "f_x": 22.0, "f_h": 1.6, "b_h": 4.5,
      "zc": 50.0, "holes_yz": [(-46, 50), (-24, 50), (24, 50), (46, 50)]}
B2_BOSS_Z = (-67.0, -61.6)   # BINDING boss tops at Z -61.6
M2_HOLE = 2.2
M2_INSERT_HOLE = 3.2
MOUNT_KEEPOUT_D = 6.0        # no components within this diameter around board mounting holes (envelope)

# Clearance targets (task brief)
CLEAR_MOVING = 0.5
CLEAR_STATIC = 0.3
