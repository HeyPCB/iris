# Building Iris

> **Status: not yet built.** This guide follows the CAD; no head has been assembled from it yet. Expect
> to adjust fits after the first prints. The checks that must happen on the bench are listed in
> [verification.md](verification.md).

<p align="center"><img src="../media/exploded.png" alt="Iris exploded view" width="860"></p>

## 1. Printed parts

All files are in [`cad/out/parts/`](../cad/out/parts/) as STEP and STL, exported **in assembly
position** (head frame H), so they line up when imported together. Rotate each part onto its print
face in the slicer. Quantities, volumes and masses come from [`cad/out/parts.json`](../cad/out/parts.json)
(PETG 1.27, PLA 1.24, resin 1.15 g/cm3; solid volume, so real prints with infill weigh less).

| # | File | Qty | Material | Volume (cm3) | Mass each (g) | Print notes |
|---|---|---|---|---|---|---|
| P1 | `sclera` | 2 | SLA white resin, or PLA at 0.1 mm + paint | 2.86 | 3.3 | open back down; supports inside only; sand and lacquer the outside |
| P2 | `cornea` | 2 | SLA clear | 0.19 | 0.2 | dome up, supports on the base ring only; polish and lacquer, or dip-coat |
| P3 | `iris_disc` | 2 | SLA translucent | 0.41 | 0.5 | disc face down; paint the iris pattern on the front (or apply a printed film); paint the sleeve black and the cavity cone white |
| P4 | `carrier_R` | 1 | PLA/PETG black | 1.72 | 2.1 | B3 seat up; 0.1 mm layers |
| P4 | `carrier_L` | 1 | PLA/PETG black | 2.06 | 2.5 | dummy-module side up |
| P5 | `spine` | 1 | PETG | 18.79 | 23.9 | rear plate flat on the bed; supports under the rails |
| P6 | `fork` | 2 | PETG or nylon | 1.04 | 1.3 | on its side (Y face down) so the layers run along the arms; 100 % infill |
| P7 | `temple_arm_R` / `_L` | 1 + 1 | PETG | 4.06 / 4.11 | 5.2 | plate flat; supports under the ear ledges; ream the MR63ZZ seat (R) |
| P8 | `tilt_tongue` | 1 | PETG | 0.87 | 1.1 | tongue flat; 100 % infill |
| P9 | `nose_block` | 1 | PETG | 1.57 | 2.0 | floor down |
| P10 | `column` | 1 | PETG | 12.49 | 15.9 | flat |
| P11 | `lidU_R`, `lidU_L`, `lidL_R`, `lidL_L` | 1 each | SLA, or PLA at 0.1 mm | 1.16 / 0.68 | 1.3 / 0.8 | convex side up, tree supports inside; round the margins; skin paint, optional lash slot |
| P12 | `pan_crank` | 2 | PETG | 0.42 | 0.5 | hub up; 100 % infill |
| P13a | `brow_hub` | 2 | PETG | 0.85 | 1.1 | standing on the spline end |
| P13b | `brow_R` / `brow_L` | 1 + 1 | PLA, flocked or painted | 0.72 | 0.9 | back face down |
| P14 | `face_shell` | 1 | PLA or PETG, painted | 99.9 | 123.9 | standing on its open bottom edge; tree supports for the eye sockets and the top fillet; 3 walls, 15 % infill |
| P15a | `side_plate_R` / `_L` | 1 + 1 | PETG | 31.3 | 39.7 | flat |
| P15b | `top_bridge` | 1 | PETG | 37.2 | 47.3 | bridge plate down; brow brackets hang up |
| P16a | `base_plate` | 1 | PETG | 76.8 | 97.5 | flat |
| P16b | `back_cover` | 1 | PETG | 165.0 | 209.6 | standing on its open front (seam) edge |
| P17 | `lid_horn` | 4 | PETG | 0.19 | 0.2 | arm flat; 100 % infill |

General PETG settings: 0.2 mm layers, 4 perimeters, 30 % gyroid infill unless noted, 0.4 mm nozzle.
Small mechanism parts (P6, P8, P12, P17) at 100 % infill. Check the Dia 2 and Dia 3 bores with a drill
bit after printing: the pole-pin bores in P1 (2.05) and the lid caps (3.2) are running fits, the
other pin bores are press fits (1.95, 2.95).

## 2. Purchased parts (BOM)

| Item | Qty | Used for | Notes |
|---|---|---|---|
| Feetech SCS0009 bus servo (or Waveshare SC09) | 9 (+1 spare) | pan x2, tilt, lids x4, brows x2 | 6 V, 20T spline, 5264-3 lead 150 mm |
| OV2640 camera module, 24-pin 0.5 mm FPC, 68-70 deg lens | 1 (+1 spare) | right eye | **FPC >= 100 mm overall (120 mm class)**; the 75 mm part is too short |
| MR63ZZ bearing 3 x 6 x 2.5 | 1 | right temple arm | |
| Steel dowel Dia 3 x 16 | 2 | temporal lid pins | |
| Steel dowel Dia 3 x 12 | 2 | right temple pin, left loose bushing pin | |
| Steel dowel Dia 3 x 8 | 2 | nasal lid pins (cut the left one to 7 mm) | |
| Steel dowel Dia 3 x 6 | 1 | P8 drive pin | |
| Steel dowel Dia 2 x 8 | 4 | pole pins | |
| M2 ball link (4.8 mm ball) | 12 | 4 lid pushrods, 2 pan couplers | |
| M2 ball stud (4.8 mm ball) | 12 | 2 keels, 2 pan cranks, 4 lid levers, 4 lid horns | |
| M2 threaded rod | 200 mm | cut to the six pushrods | pan 26.0, lid L 22.0, lid R 34.9 mm between ball centres |
| M2 x 6 screw + M2 heat-set insert | 12 + 8 | B1 (4, inserts in P5), B2 (4, inserts in P16a), B4 (4, self-tapping into the face-shell bosses) | |
| M2 x 8 screw | 18 | servo ears | self-tapping into the column / brackets, or with inserts in the temple-arm ledges (4) |
| M2 x 8 self-tapping screw | about 30 | forks to the spine, temple arms to the rails, column, nose block, skull plates, top bridge, back cover, P8 clamp | |
| Neodymium magnet 6 x 3 mm N52 | 8 | 4 pairs: face shell to the skull side plates and to the base plate | glue with epoxy, check polarity |
| Speaker 28 mm, 8 Ohm, 1 W | 1 | chin holder on the base plate | bridge-tied: neither wire is ground |
| JST SH cables, double-ended same-direction | SH-10, SH-7, SH-8 at 150 mm; 2 x SH-4 pigtails | H1, H2, BROW, RING_R/L | see [system.md](system.md) |
| 5264-3 servo extension lead | 4 x 100 mm | brows, upper lids | |
| 32 AWG silicone wire, Kapton tape, TPU grommets | - | ring wires, FPC strain relief, servo ear damping | |
| USB-C PD charger >= 27 W (9 V 3 A), or a PD power bank | 1 | power | |
| Boards B1, B2, B3 x2, B4 | 1 / 1 / 2 / 1 | electronics | from the four board repositories |

## 3. Before assembly

1. **Inserts.** Melt M2 heat-set inserts into the four B1 bosses (P5), the four B2 bosses (P16a) and
   the four pan-servo ear ledges (P7, two per arm).
2. **Servo IDs.** Every SCS0009 ships as ID 1. Connect one servo at a time and set its ID (table in
   [mechanism.md](mechanism.md)). Label each servo. Set the return delay (register 7) to 0.
3. **Servo neutral.** Drive each servo to 511 (150 deg) before fitting its horn, crank, hub or tongue.
   The 20T spline gives 18 deg steps; mount at the nearest tooth and record the remaining offset as the
   servo's calibration.
4. **Pushrods.** Cut the M2 rod and thread the ball links so the ball centres are 26.0 mm (pan
   couplers), 22.0 mm (left lids) and 34.9 mm (right lids) apart.

## 4. Eyes

1. Glue the camera carrier (P4 R) into the right sclera, B3 seat facing the front, FPC slot toward
   the temple (robot right). Glue the dummy carrier into the left sclera the same way, slot toward
   the left temple.
2. Right eye: seat the OV2640 in the holder pocket (lens forward), lead its FPC out through the
   temporal slot and bend it 90 deg (r >= 2 mm) so it runs straight back as a vertical strip.
3. Solder four 32 AWG wires to each B3's back pads (P1 5V_LED, P2 DIN, P3 GND, P4 GND), pass them out
   through the carrier's wire hole, and drop B3 into its keyed seat (right eye flat down, left eye
   flat up), LEDs forward.
4. Paint the inside of the iris cone white and the pupil sleeve black. Insert the iris disc from the
   front: the cone ring clamps B3's outer edge.
5. Glue the cornea into the limbus bore; it seats on the iris disc.
6. Screw an M2 ball stud into each keel, pointing down.

## 5. Tilt cradle

1. Bolt the two forks to the front of the rails (two M2 screws per foot).
2. Bolt the temple arms to the ends of the bottom rail. Leave the MR63ZZ out of the right arm for now
   (step 7.5).
3. Screw the pan servos (IDs 1 R, 2 L) to the temple-arm ledges, spline up.
4. Fit the pan cranks (P12) on the pan splines pointing straight back at neutral; screw an M2 ball
   stud into each crank tip, pointing down.
5. Slide each eye between its fork arms and push the two Dia 2 x 8 pole pins in from outside, through
   the sclera's pole bores and the bosses into the fork arms (press fit in the fork).
6. Snap the 26 mm pan couplers onto the keel and crank studs.
7. Screw B1 onto its four bosses, F side toward the eyes. Feed the camera FPC through the window in the
   right side wall and into J1 (bottom contact: fingers toward B1). Plug the ring cables into J2 (right
   eye) and J3 (left eye). Tape the FPC to the right fork spine with a loop that allows +-35 deg pan.

## 6. Frame and lid servos

1. Screw the centre column (P10) to the base plate. Fit the four lid servos through the column windows:
   the left servos (IDs 5, 7) clamp their ears on the +Y face, the right servos (IDs 4, 6) on the -Y face.
2. Fit the tilt servo (ID 3) through its window, spline toward +Y, ears on the two pads.
3. Press the right nasal lid pin (Dia 3 x 8) into the nose block (P9) and screw P9 over the tilt
   servo's base.
4. Fit P8 on the tilt spline, tongue pointing straight back at neutral, and tighten its clamp screw.
   Press the left nasal lid pin (Dia 3, 7 mm) into P8's face and the Dia 3 x 6 drive pin through the
   tongue end.
5. Fit the four lid horns (P17) with their arms at the lever angles of the rest pose (elevation in the
   XZ plane): upper L 213 deg, upper R 205 deg (both pointing back and down), lower L -13 deg, lower R
   -5 deg (both pointing forward). Screw an M2 ball stud into each horn tip, pointing away from the
   servo.

## 7. Install the cradle and the lids

1. Screw the right skull side plate to the base plate (temple pin not yet fitted).
2. Lower the cradle in about 6 mm behind its final position, then push it forward: P8's drive pin
   enters the open back of the radial slot in the cradle's drive block. Hold the cradle there.
3. Right lids: slide the nasal caps of the lower lid, then the upper lid, onto the right nasal pin
   (from the nose block), swing the lids over the eye, and push a Dia 3 x 16 temporal pin in from
   outside, through the open bearing seat of the right temple arm, into the temporal caps (press fit
   in the stub boss).
4. Left lids: the same, on the left nasal pin carried by P8 and through the left temple arm.
5. Press the MR63ZZ into the right temple arm's outer seat, then press the right temple pin
   (Dia 3 x 12) through the skull plate's boss into the bearing. The cradle now turns on the bearing
   and the P8 drive pin.
6. Snap the four lid pushrods onto the lever studs and the horn studs.
7. Screw on the left side plate with its loose bushing pin (Dia 3 x 12, Dia 3.2 bore in the left
   arm), then the top bridge.

## 8. Brows, face and electronics

1. Screw the brow servos (IDs 9 L, 8 R) to the brackets under the top bridge, spline forward. Fit the
   brow hubs (P13a) on the splines with the D-flat up at neutral.
2. Screw B2 onto the base-plate bosses (USB-C mouths at the back). Route H1 and H2 (150 mm) from B2's
   front edge up to B1's bottom edge with a service loop that allows +25 / -30 deg tilt. Plug the nine
   servo leads into J10-J19 per the port map in [system.md](system.md) (pad 1 = DATA; check the
   D / V / G silkscreen). Connect the speaker to J7 and seat it in the chin ring.
3. Screw B4 to the four bosses inside the face shell from its back side (sensors toward the shell's
   ToF slot, ALS hole and mic holes). Plug the BROW cable (150 mm) into B4 J1.
4. Glue the magnets into the face shell pads and the matching pockets in the side plates and the base
   plate posts.
5. Offer the face shell up: the brow hubs pass through the Dia 10 holes; push the brows onto the D-keyed
   hub ends. Plug the BROW cable into B1 J4 before the shell closes.
6. Screw the back cover to the base plate from below (four M2).

## 9. First power-up

1. USB-C DATA only (PC): logic runs, servos stay off. Check that the camera streams and both rings
   light (30 % cap).
2. Add USB-C PWR (>= 27 W PD charger): check that VIN reads 9 V on the INA226, then enable the servos.
3. Move each joint slowly through its range in a setup mode and record the calibration offsets.
   Keep the lids inside the envelope in [mechanism.md](mechanism.md).
