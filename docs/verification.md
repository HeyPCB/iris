# Verification

What was checked in CAD, how, and with what result; and what can only be checked on the bench.
Iris has **not been built**: everything in the first half of this page is a property of the CAD
model, not of a working head.

Re-run the checks from the repository root:

```sh
python -m cad.build    # parts, watertight STLs, parts.json
python -m cad.check    # motion check  -> cad/out/check.json
python -m cad.fit      # board fit     -> cad/out/fit.json
```

## 1. Printed parts

`cad/build.py` exports 27 printed part files (36 printed parts with the duplicates) as STEP and
STL and records each in [`cad/out/parts.json`](../cad/out/parts.json).

- Every B-rep is a single valid solid.
- **Every STL is watertight** (checked with trimesh after export; OpenCASCADE leaves zero-area slivers
  at sphere poles, which the export removes before the check).
- Total printed volume is about 505 cm3 (636 g as solid PETG/PLA/resin; real prints with infill weigh
  less). The face shell (100 cm3) and back cover (165 cm3) are half of it.

## 2. Motion check

[`cad/check.py`](../cad/check.py) -> [`cad/out/check.json`](../cad/out/check.json)

**Method.**

- Every part, and the sub-solids that matter (sclera shell vs pole bosses, lid shell vs lever boss,
  servo body vs spline, board slab vs component envelopes), is tessellated at 0.04 mm chordal
  tolerance and turned into a manifold mesh.
- The model has 80 parts in 22 motion groups (fixed frame, tilt cradle, two eyes, two pan cranks, two
  pan couplers, four lids, four lid horns, four lid pushrods, two brows). For each
  pair of groups, only the joints that move one relative to the other are swept: for example eye vs
  upper lid sweeps tilt x pan x upper-lid angle, and the frame vs a lid horn sweeps the horn's servo
  angle alone.
- Grid: tilt -30 ... +25 in 9 steps; pan -35 ... +35 in 9 steps per eye; upper lid -40 ... +55 in 20
  steps; lower lid -50 ... -6 in 12 steps; brows -20 ... +20 in 5 steps. When a pair depends on tilt
  and a lid, the lid is swept inside the firmware "lids follow gaze" envelope for that tilt (upper =
  19 + tilt + [-37, +36], lower = -20 + 0.5 tilt + [-30, +14], clamped to the mechanical ranges);
  otherwise the full mechanical range is swept.
- Each pose measures the exact triangle-to-triangle gap (manifold3d `min_gap`) and, where parts touch,
  the overlap volume. The worst pose of every pair closer than 1.5 mm is re-measured exactly on the
  B-rep solids (OpenCASCADE `BRepExtrema_DistShapeShape`).
- Requirements: **>= 0.5 mm** between parts that move relative to each other, **>= 0.3 mm** between
  parts of one rigid group. Designed contacts (screwed, pressed, glued seats) and designed running fits
  (pins in bores, ball links on studs, the pivot face gap, the nested lids) are listed separately with
  their own expected minimum.

**Result (latest run): 740 part pairs, 80 540 pose evaluations, 0 collisions, 0 pairs below the
threshold, 0 joint or contact problems.**

Smallest clearances between moving parts (exact B-rep distance at the worst pose):

| Pair | Clearance | Worst pose |
|---|---|---|
| brow hub vs its servo's gear cover (both brows) | 0.50 mm | constant (coaxial running gap) |
| lid horn hubs vs their servo's gear cover (4) | 0.50 mm | constant |
| tilt tongue P8 vs the tilt servo case | 0.50 mm | tilt -30 |
| tilt tongue P8 vs the upper-left horn | 0.50 mm | tilt -30, upper lid L +15 |
| nose block vs the upper-right lid stud | 0.50 mm | upper lid R -40 |
| lower lid vs its own pushrod (L and R) | 0.52 mm | lower lid -22 (L) / -50 (R) |
| lid horns vs the stacked servo on the other side | 0.55 mm | lower L -50, upper R +35 |
| nose block vs the right lower lid | 0.56 mm | lower lid R -50 |
| brows vs the face shell | 0.60 mm | brow -20 |
| cornea vs the upper lid (both eyes) | 0.60 mm | tilt +6.25, pan +-35, upper lid -5 (spec: 0.6 by design) |
| fork vs sclera shell (keel under the lower arm; opening rim) | 0.60 mm | tilt +18.75, pan 0 |
| pan crank vs its coupler; sclera vs coupler; pan crank vs servo | 0.60 mm | various |

Smallest static clearances (one rigid group): nose block vs tilt servo case 0.30 mm; sclera pole
bosses vs carrier 0.30 mm; skull side plates vs face shell 0.40 mm; cradle rear plate vs B1's back-side
envelope 0.40 mm.

Designed running fits, as built: nested lid shells and caps 0.20 mm (spec 2.5 accepts 0.2); ball-link
faces on their own studs 0.20 mm; pan pivot axial gap (pole boss to fork arm) 0.30 mm.

**Named poses.** The spec's sweep extremes (look down 30 deg and blink at +-35 deg pan; look up 25 deg
with wide-open lids at +35 deg pan; lids closed and tucked; lids fully open; and the same with
vergence instead of version) were each checked as a whole assembly: no collisions, smallest moving
clearance 0.50 mm in every pose.

**Negative controls.** Three poses outside the design range must collide, and do: pan 55 deg (fork arm
hits the sclera rim, 13 mm3), tilt +45 deg (14 colliding pairs, cradle into frame and B2), upper lid
+85 deg (the upper pushrod sweeps over P8 and the left nasal pin). This shows the sweep detects contact.

**Outside the lid envelope.** Sweeping the lids through their full mechanical ranges at every tilt
(ignoring the firmware envelope) finds one problem: with the upper lid fully open (+55) while looking
down 30 deg, the upper lid's shell reaches the fork's top arm (13.6 mm3 overlap). Firmware must keep
the upper margin at or below tilt + 55; the envelope above does.

**Problems the check found and the design changes they caused** (all now fixed):

- The upper-left lid horn, if mounted on the spline like the concept's horn disc, cuts 1.2 mm into the
  upper-right servo case: the horn arms now sit at |Y| 15.0-16.3.
- At the spec's 60 deg rear opening, the fork arms graze the sclera rim at +-35 deg pan: the opening is
  now 65 deg.
- The keel of a fully panned eye meets the upper lid's lever tab: the tabs now start 12 mm from the
  eye centre toward the nose.
- Same-direction lid levers collide at every blink: the upper lever now points back, the lower one
  forward.
- Ball-link housings and studs against the nose block, the P8 hub and their own lids: ball planes,
  the nose-block floor and the P8 hub were adjusted to give 0.5 mm.
- Pan cranks against the temple-arm plates at +-35 deg pan: the crank window in the temple arm was
  widened.

**Limits of the check.**

- Rigid bodies only. The camera FPC, the ring wires, the harnesses and the servo leads are not modelled
  as flexible parts. What was kept free for them: the |Z| < 3 band behind the right eye down to B1, the
  FPC window in the cradle's right side wall, the column's harness opening.
- Purchased parts are envelopes from datasheet main dimensions (SCS0009, OV2640 module, M2 ball links
  with an estimated 6.6 x 4.0 mm housing). Real horns, ball links and connectors differ: check the parts
  you buy against the envelopes.
- Nominal geometry: no print tolerances, no deflection under load, no wear. Running clearances of
  0.2-0.5 mm are tight for FDM; print the small mechanism parts at fine layers and check them.
- The pose grid is discrete (worst case between grid points can be a few hundredths of a millimetre
  smaller; the B-rep refinement measures exactly at the worst grid pose only).

## 3. Board fit

[`cad/fit.py`](../cad/fit.py) -> [`cad/out/fit.json`](../cad/out/fit.json). Until the boards are
released this uses envelopes built from spec section 4: the outline with its fillet and Dia 2.2 holes,
plus slabs at the maximum component height on each side over the whole outline (minus a Dia 6
keep-out around each mounting hole). Each board is swept with everything that moves relative to it.

| Board | Holes vs mount bosses | Mounting face to boss tips | Interference | Closest part |
|---|---|---|---|---|
| B1 Cortex (on the cradle) | 4 / 4 on axis (0.00 mm) | 0.00 mm (B face on bosses at X -53.6) | none | cradle rear plate 0.40 mm behind the 3.6 mm back-side envelope; side walls 1.0 mm from the front-side envelope; fixed parts more than 6 mm away over the whole tilt sweep |
| B2 Brainstem (base) | 4 / 4 on axis (0.00 mm) | 0.00 mm (B face on bosses at Z -61.6) | none | base-plate bosses 0.50 mm from the back-side envelope's keep-outs; back cover 1.0 mm behind the USB-C edge; cradle 2.45 mm above B2's 12 mm front-side envelope at full look-up |
| B3 Iris ring x2 (in each eye) | no holes (keyed flat in the carrier) | seated on the camera holder / dummy and clamped by the iris cone | none | sclera 1.46 mm |
| B4 Brow (forehead) | 4 / 4 on axis (0.00 mm) | 0.00 mm (F face on the shell bosses at X +22.0) | none | face shell 0.50 mm from the front-side envelope's keep-outs, inner face 4.5 mm in front of the F face (spec: >= 2.0); brow hubs 3.0 mm below |

B1's WROOM antenna zone grown by 5 mm (spec 7.1 P5) contains no cradle plastic.

**Real boards.** When the KiCad STEP exports exist, run
`python -m cad.fit --B1 cortex.step --B2 brainstem.step --B3 ring.step --B4 brow.step`. The loader finds
the board body by its outline size, places it by its top-left corner and F face, finds the Dia 2.2
mounting holes on it and reports their offset from the boss axes, and sweeps every component model
against the mechanism.

## 4. To test on the bench

From spec section 9, plus the mechanical items this CAD cannot settle.

| Test | Pass criterion |
|---|---|
| Servo timing (SCS0009, 6 V, eye-mass dummy on a 14 mm crank) | 20 deg move <= 60 ms, settle +-0.5 deg; this measures the 16 ms ramp estimate |
| Tilt with the full cradle | 20 deg in <= 80 ms; holding current < 150 mA; no sag (else add the counterweight pocket) |
| Blink | rest -> closed <= 100 ms; no lid-lid or lid-cornea contact over the full pan/tilt grid |
| Noise | each servo <= 60 dB(A) at 30 cm while idle-holding; record the whole head during a saccade |
| Camera FPC | 100 000 pan cycles +-35 deg with the routing of spec 3.2, no image dropouts |
| Camera through the cornea dome | face-detector recall within 10 % of the bare lens (same scene) |
| USB-C | 20 W, 27 W and 45 W PD chargers negotiate 9 V; a PC port gives logic-only mode |
| Bus signal | DATA rise time < 100 ns at port J18 with all servos connected |
| Printed fits | pole pins run freely in the Dia 2.05 bores with < 0.1 mm play; lid caps turn freely on the Dia 3 pins; pressed pins stay put |
| Fork stiffness | eye deflection under a 0.5 N side load at the cornea < 0.2 mm (4 x 2.5 mm PETG arms, 41 mm long) |
| P8 clamp | no slip on the tilt spline at stall torque (2.3 kg.cm); otherwise add the stock horn under it |
| Lid pushrod lengths | lid margins match the servo angles within 1 deg after calibration (ball-link thread adjustment) |
| Face shell | brows clear the shell (0.6 mm in CAD) after painting; ToF crosstalk through the open slot (spec Q6) |
| Thermal | servo case temperature after 10 min of idle saccades below 60 C inside the closed head |
