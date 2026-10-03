# Iris CAD

Parametric CadQuery source for the Iris mechanism. Everything (parts, exports, motion check, board fit,
renders) is generated from these files; nothing in `out/` or `../media/` is edited by hand.

## Requirements

Python 3.12 with CadQuery 2.8, trimesh, manifold3d, VTK (comes with CadQuery) and Pillow:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run every command from the repository root.

| Command | What it does | Output |
|---|---|---|
| `python -m cad.build` | builds every part, exports printed parts (STEP + STL), purchased-part envelopes and the rest-pose assembly | `cad/out/parts/`, `cad/out/envelopes/`, `cad/out/iris_assembly.step`, `cad/out/parts.json` |
| `python -m cad.check` | motion check over the full pose grid (about 2-3 min) | `cad/out/check.json` |
| `python -m cad.check --quick` | coarse grid for development (about 30 s) | `cad/out/check_quick.json` (not committed) |
| `python -m cad.fit` | board fit with the spec section 4 envelopes | `cad/out/fit.json` |
| `python -m cad.fit --B1 a.step --B2 b.step --B3 c.step --B4 d.step` | board fit with real KiCad STEP exports | `cad/out/fit.json` |
| `python -m cad.render` | renders and the gaze GIF (headless VTK) | `media/` |

Built solids and meshes are cached in `cad/out/.cache/` (ignored by git), keyed on a hash of the
geometry sources, so the check and the renders do not rebuild unchanged parts.

## Layout

| File | Contents |
|---|---|
| `params.py` | every dimension, with its spec section; BINDING rows come from spec 2.8 / 4 |
| `geom.py` | small solid helpers (boxes from bounds, cylinders on axes, lunes, prisms, frames) |
| `kinematics.py` | pose model, lever geometry, lid envelope and the rigid transform of every motion group |
| `parts/eye.py` | P1 sclera, P2 cornea, P3 iris disc, P4 carriers, B3 and camera envelopes |
| `parts/cradle.py` | P5 spine and rear plate, P6 forks, P7 temple arms |
| `parts/linkage.py` | P8 tilt tongue, P12 pan cranks, P17 lid horns, couplers, studs and pins |
| `parts/lids.py` | P11 nested visor lids with their lever tabs |
| `parts/frame.py` | P9 nose block, P10 centre column, P15 skull plates and top bridge, P16a base plate |
| `parts/face.py` | P14 face shell, P16b back cover, P13 brows and brow hubs |
| `parts/purchased.py` | envelopes: SCS0009, OV2640 module, MR63ZZ, ball links, pins, speaker |
| `parts/boards.py` | board envelopes from spec 4 and the loader for real board STEP files |
| `assembly.py` | the part registry (groups, colours, BOM data), build cache and meshing |
| `check.py`, `fit.py`, `render.py`, `build.py`, `viz.py` | the scripts above |

## Frame

All parts are modelled and exported in the head frame H at the rest pose: origin midway between the
eye centres, +X forward, +Y robot-left, +Z up, millimetres. A part file therefore lands in its
assembly position when imported; rotate it onto its print face in the slicer.
