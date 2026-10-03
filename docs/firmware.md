# Iris firmware: behaviour notes

> **Status: not written yet.** Nothing on this page exists as code. These are the behaviour notes from
> the Iris system specification v0.1 (section 8) that the hardware is designed to support, plus the
> mechanism numbers the firmware will need from [mechanism.md](mechanism.md). Values marked (est.)
> are estimates to be tuned on the bench.

The firmware runs on B1 (ESP32-S3-WROOM-1-N16R8). Board-level pin and bus details are in
[system.md](system.md) and in the [iris-cortex](https://github.com/HeyPCB/iris-cortex) repository.

## Servo bus

- UART1 at 1 Mbps, 8N1, half-duplex through B2's auto-direction buffer. TX is never echoed.
- Feetech SCS protocol: `FF FF ID LEN INSTR PARAMS ~SUM`. SCS servos are **big-endian**.
- Every 10 ms (100 Hz): one **SYNC WRITE (0x83)** to IDs 1-9 with goal position (register 42), goal
  time (44) and goal speed (46). That is about 70 bytes, about 0.7 ms at 1 Mbps.
- Then a round-robin READ of present position (56), load (60) and temperature (63) for 2-3 servos per
  cycle.
- SCS has **no acceleration register**, so shape moves in firmware (the HL-3604 / STS upgrade servos
  have ACC at 41).
- Set return delay (register 7) to 0. Every servo ships as ID 1: provision IDs one servo at a time in
  a setup mode.

| ID | Joint | Port |
|---|---|---|
| 1 | pan R | B2 J15 |
| 2 | pan L | B2 J10 |
| 3 | tilt | B2 J14 |
| 4 | upper lid R | B2 J16 |
| 5 | upper lid L | B2 J11 |
| 6 | lower lid R | B2 J17 |
| 7 | lower lid L | B2 J12 |
| 8 | brow R | B2 J18 |
| 9 | brow L | B2 J13 |

## Joint model and limits

- All nine joints are 1:1 with their servo: joint angle = servo angle + a per-servo calibration offset
  (pan and lid linkages are parallelograms, tilt and brows are direct).
- Resolution 0.293 deg per count (300 deg over 1024).
- Soft limits (degrees, joint frame of [mechanism.md](mechanism.md)): tilt -30 ... +25; pan -35 ... +35
  per eye; upper lid margin -40 ... +55; lower lid margin -50 ... -6; brows -20 ... +20.
- **Lid envelope** (checked collision-free in CAD): upper = 19 + tilt + [-37, +36], lower = -20 +
  0.5 tilt + [-30, +14], each clamped to its range. Outside this envelope (e.g. upper lid fully open
  while looking down 30 deg) the upper lid hits the fork's top arm: clamp the upper margin to
  tilt + 55 or less.
- Never park a servo against a mechanical stop.

## Gaze model

- Helmholtz: one elevation (tilt) and two azimuths (pans).
- Version = mean pan. Vergence = pan_R - pan_L = 2 atan(39 / d), with d from the ToF (VL53L1X on B4)
  or from the face size.

| Target distance | Pan per eye (nasal) | Total vergence |
|---|---|---|
| 150 mm | 14.57 deg | 29.15 deg |
| 250 mm | 8.87 deg | 17.73 deg |
| 400 mm | 5.57 deg | 11.14 deg |
| 700 mm | 3.19 deg | 6.38 deg |
| 1000 mm | 2.23 deg | 4.47 deg |
| 2000 mm | 1.12 deg | 2.23 deg |

## Saccades

- Trigger: targets from face tracking, sound direction, or an idle scan (Poisson, fixations
  200-330 ms; 86 % of saccades are 15 deg or less).
- Duration from D = 21 + 2.2 A ms (A in degrees); peak about 500 deg/s.
- Command: SCS0009 goal speed at maximum and goal time = D. The 0.293 deg resolution limits
  microsaccades to about 0.3 deg steps.
- Expected SCS0009 move time (est., A / 600 deg/s + 16 ms): 5 deg 24 ms, 10 deg 33 ms, 20 deg 49 ms,
  40 deg 83 ms, against human 32 / 43 / 65 / 109 ms.
- Above about 20 deg from centre, request a head turn if a neck exists.

## Pursuit

Stream positions at 100 Hz with goal speed equal to the target speed, up to 100 deg/s; latency target
125 ms or less.

## Lids and blinks

- Spontaneous blinks: Poisson at 17/min (26/min while "talking"); close in about 90 ms, open in about
  240 ms.
- Add a blink with about 30 % of saccades over 20 deg (est.; gaze-evoked).
- Upper lid tracks tilt 1:1; lower lid at about 0.5 gain; start lid moves about 5 ms after the eye
  move.
- Blink targets (from the CAD): upper margin to rest + tilt - 37 (level gaze: +19 -> -18, a 37 deg
  stroke, about 78 ms at 600 deg/s + 16 ms), lower margin up 8 deg. The upper lid tucks under the
  lower one; the shells cannot touch.
- Expressions: wide (+10 deg upper), squint (lower +15 deg), sleepy (upper -15 deg).

## Face tracking

- esp32-camera with the ESP32-S3-EYE pin map, XCLK 20 MHz, grey QVGA for detection, JPEG for streaming.
- ESP-DL MSR+MNP at about 20 Hz.
- Target in head = eye angle (bus feedback) + pixel offset x deg/px (68.7 deg diagonal FOV).
- Ignore frames that overlap a saccade or a blink.
- Smooth the face position with an alpha-beta filter; saccade when the error is > 3 deg, pursue
  otherwise (est. thresholds).
- Check the image orientation at first light: if the OV2640 rows run along the FPC exit edge, fix it
  with vflip/hmirror; otherwise rotate in firmware or turn the module 90 deg (open question in the
  spec).

## Sound

- I2S0 full duplex at 48 kHz, 32-bit slots: RX from both mics (L / R slots), TX to the amp.
- Two-mic GCC-PHAT gives azimuth. Maximum TDOA 0.108 m / 343 m/s = 0.31 ms, about 15 samples.
- Gate it during servo motion: each servo is about 65 dB at 30 cm.

## Other sensors

- VL53L1X: write the 2V8 / AVDD pad mode (register 0x2E bit 0 = 1), 20-50 Hz, ROI centred.
- APDS-9306: sets ring brightness and blink rate.
- Touch (GPIO14) gives a "pat" reaction.
- LED rings: RMT on GPIO47/48, 800 kHz, 12 LEDs each; brightness cap 30 % on USB-only power. A ring
  swap flag covers the two interchangeable ring cables.

## Power manager

- Read INA226 at 10 Hz.
- Enable SERVO_EN only if VIN >= 8.5 V.
- Stagger servo starts by 2 ms or more.
- Cut torque on overload: servo load register (60) high for > 0.5 s, or VIN current > 3.3 A
  (1 s average).
- USB-only mode: no servos, rings dimmed, amp muted.
