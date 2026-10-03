"""Export every printed part (STEP + STL), the purchased-part envelopes and the rest-pose assembly.

  python -m cad.build

Outputs (cad/out/):
  parts/<name>.step, parts/<name>.stl   printed parts, in head-frame (assembly) coordinates
  envelopes/*.step                       SCS0009 and OV2640 envelopes in their own frames
  iris_assembly.step                     rest-pose assembly, all parts and board envelopes, coloured
  parts.json                             parts list: quantity, material, volume, mass, watertight, files
"""
import json
import os

import cadquery as cq
import trimesh

from . import assembly as A
from . import params as P
from .parts import purchased

DENSITY = {"PETG": 1.27, "PLA": 1.24, "SLA": 1.15, "nylon": 1.14}
STL_TOL = {"default": (0.03, 0.15), "large": (0.08, 0.25)}
LARGE = {"face_shell", "back_cover", "base_plate", "top_bridge", "side_plate_R", "side_plate_L", "column", "spine"}


def _density(material):
    for k, v in DENSITY.items():
        if material.startswith(k):
            return v
    return 1.24


def clean_mesh(m):
    """Merge vertices and drop zero-area triangles (OCC leaves slivers at sphere poles); fill any
    pinhole left behind."""
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces(height=1e-7))
    m.remove_unreferenced_vertices()
    m.merge_vertices()
    if not m.is_watertight:
        trimesh.repair.fill_holes(m)
    trimesh.repair.fix_normals(m)
    return m


def _stl(shape, path, large):
    tol, ang = STL_TOL["large" if large else "default"]
    cq.exporters.export(shape, path, tolerance=tol, angularTolerance=ang)
    m = clean_mesh(trimesh.load(path, force="mesh", process=True))
    m.export(path)                       # binary STL
    return m


def export_parts(parts):
    out = os.path.join(A.OUT, "parts")
    os.makedirs(out, exist_ok=True)
    rows = {}
    for n, p in parts.items():
        if p.kind != "printed":
            continue
        stem = p.export_as or n
        if stem in rows:
            rows[stem]["qty"] += 1
            rows[stem]["instances"].append(n)
            continue
        shape = p.shape
        step = os.path.join(out, stem + ".step")
        stl = os.path.join(out, stem + ".stl")
        cq.exporters.export(shape, step)
        m = _stl(shape, stl, n in LARGE)
        vol = shape.Volume() / 1000.0
        bb = shape.BoundingBox()
        rows[stem] = {
            "file_stem": stem, "pnum": p.pnum, "label": p.label, "qty": 1, "instances": [n],
            "material": p.material, "volume_cm3": round(vol, 2),
            "mass_g_each": round(vol * _density(p.material), 1),
            "bbox_mm": [round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1)],
            "brep_valid": bool(shape.isValid()), "solids": len(shape.Solids()),
            "stl_watertight": bool(m.is_watertight), "stl_volume_cm3": round(float(m.volume) / 1000.0, 2),
            "stl_triangles": int(len(m.faces)),
            "files": {"step": f"cad/out/parts/{stem}.step", "stl": f"cad/out/parts/{stem}.stl"},
            "size_kb": {"step": round(os.path.getsize(step) / 1024), "stl": round(os.path.getsize(stl) / 1024)},
        }
        print(f"  {stem:22s} {p.pnum:5s} {vol:8.2f} cm3  watertight={m.is_watertight}  {rows[stem]['size_kb']}", flush=True)
    return sorted(rows.values(), key=lambda r: (int(''.join(c for c in r['pnum'] if c.isdigit()) or 0), r['pnum'], r['file_stem']))


def export_envelopes():
    out = os.path.join(A.OUT, "envelopes")
    os.makedirs(out, exist_ok=True)
    loc = purchased.scs0009_local()
    sv = loc["body"].fuse(loc["spline"]).clean()
    cq.exporters.export(sv, os.path.join(out, "scs0009_envelope.step"))
    cam = purchased.ov2640_eye("R").translate(cq.Vector(-P.CAM_BACK_X, 0, 0))
    cq.exporters.export(cam, os.path.join(out, "ov2640_module_envelope.step"))
    with open(os.path.join(out, "README.md"), "w") as f:
        f.write(
            "# Purchased-part envelopes\n\n"
            "Simplified envelopes drawn from datasheet main dimensions for clearance work. They are not\n"
            "vendor CAD and do not show internal detail.\n\n"
            "| File | Part | Source | Frame |\n|---|---|---|---|\n"
            "| `scs0009_envelope.step` | Feetech SCS0009 bus servo | Feetech SCS0009 product specification "
            "2020-11-23, p.6 outline (case 23.3 x 12.1 x 25.25, spline 3.2, ears 32.5, holes 28.5) | origin 1.0 mm "
            "above the spline tip on the shaft axis, +Z along the shaft, +X along the long side |\n"
            "| `ov2640_module_envelope.step` | OV2640 module, Union Image ZY-XSF3M2640B type | Seeed OV2640 module "
            "datasheet p.7 drawing (holder 8.5 x 8.5, lens 7.2 / 5.4, stack 5.54) | origin at the module back face "
            "on the optical axis, +X out of the lens; FPC neck stub toward -Y |\n")


def _boxed(shape):
    """Component compound -> one bounding box per touching group of solids (one per component, roughly);
    keeps the assembly STEP small."""
    from .geom import box
    bbs = []
    for s in shape.Solids():
        b = s.BoundingBox()
        bbs.append([b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax])
    merged = True
    while merged:
        merged = False
        out = []
        for b in bbs:
            for o in out:
                if all(b[2 * i] <= o[2 * i + 1] + 0.05 and o[2 * i] <= b[2 * i + 1] + 0.05 for i in range(3)):
                    o[:] = [min(o[0], b[0]), max(o[1], b[1]), min(o[2], b[2]), max(o[3], b[3]), min(o[4], b[4]), max(o[5], b[5])]
                    merged = True
                    break
            else:
                out.append(list(b))
        bbs = out
    return cq.Compound.makeCompound([box(*b) for b in bbs if min(b[1] - b[0], b[3] - b[2], b[5] - b[4]) > 0.05])


def export_assembly(parts):
    """Rest-pose assembly. Real boards go in light: their spec outline slab (B4: the 116 x 12 envelope
    of its brow-shaped outline) plus one box per component. The full board models are in the board
    repositories; the fit check uses them directly."""
    from .parts import boards, eye
    asm = cq.Assembly(name="iris")
    for n, p in parts.items():
        shape = p.shape
        if p.kind == "board" and n[:2] in A.REAL_BOARDS:
            slab = eye.b3_envelope(n[-1])["board"] if n.startswith("B3") else boards.envelope(n[:2])["board"]
            shape = cq.Compound.makeCompound([slab] + [_boxed(p.subs[k]) for k in ("f", "b") if k in p.subs])
        asm.add(shape, name=n, color=cq.Color(*p.color, 1.0 if p.alpha > 0.5 else 0.6))
    path = os.path.join(A.OUT, "iris_assembly.step")
    asm.save(path)
    return path


def main():
    parts = A.build(verbose=True)
    rows = export_parts(parts)
    export_envelopes()
    ap = export_assembly(parts)
    purchased_rows = {}
    for n, p in parts.items():
        if p.kind in ("purchased", "board"):
            purchased_rows.setdefault(p.label, 0)
            purchased_rows[p.label] += 1
    total_mass = sum(r["mass_g_each"] * r["qty"] for r in rows)
    out = {"generated_by": "cad/build.py", "frame": "head frame H (params.py); parts exported in assembly position",
           "printed_parts": rows, "printed_total_mass_g": round(total_mass, 0),
           "all_stl_watertight": all(r["stl_watertight"] for r in rows),
           "purchased_in_model": purchased_rows, "assembly_step": "cad/out/iris_assembly.step",
           "assembly_step_kb": round(os.path.getsize(ap) / 1024)}
    with open(os.path.join(A.OUT, "parts.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"{len(rows)} printed part files, total printed mass {total_mass:.0f} g, all watertight: {out['all_stl_watertight']}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", default=None, help="folder with the board STEP files (default: auto)")
    ap.add_argument("--envelopes", action="store_true", help="use the spec section 4 board envelopes")
    a = ap.parse_args()
    A.use_real_boards({} if a.envelopes else A.resolve_boards(a.boards))
    main()
