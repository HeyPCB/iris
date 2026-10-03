"""Board fit check: mounting holes vs bosses, mounting-face contact, and clearance of each board
(spec envelope or real KiCad STEP) to every other part over the motion that moves it relative to them.

  python -m cad.fit                       # real boards if found (--boards DIR, IRIS_BOARDS, or board
                                          # repositories cloned next to this one), else spec envelopes
  python -m cad.fit --envelopes           # force the spec section 4 envelopes
  python -m cad.fit --boards DIR          # DIR holds iris_cortex/fab/iris_cortex.step ... or iris-cortex/fab/...

B1 rides on the tilt cradle (swept over tilt against the frame, eyes and lids), B2 and B4 are fixed
(swept against the moving cradle, eyes, lids and brows), B3 rides in each eye. Real boards are
normalised to their ordered thickness (B1, B2, B4 1.6 mm; B3 0.8 mm); for B3 the 1.51 mm thickness of
the fab STEP is checked as a second case. Parts whose 3D model is missing from a STEP are added as
envelopes (cad/parts/boards.py). Output: cad/out/fit.json
"""
import argparse
import math
import os

import json
import numpy as np

from . import assembly as A
from . import check as C
from . import params as P
from .parts import boards

BOSSES = {   # mount boss axes in H: (point on the boss tip face, axis direction into the boss)
    "B1": [((P.B1_BOSS_X[1], y, z), (-1, 0, 0)) for y, z in P.B1["holes_yz"]],
    "B2": [((x, y, P.B2_BOSS_Z[1]), (0, 0, -1)) for x, y in P.B2["holes_xy"]],
    "B4": [((P.B4["f_x"], y, z), (1, 0, 0)) for y, z in P.B4["holes_yz"]],
}
BOARD_PARTS = ("B1", "B2", "B4", "B3_R", "B3_L")


def _holes_in(shape_h, r_lo=1.0, r_hi=1.2):
    """Centres (H) of cylindrical faces with radius in [r_lo, r_hi] (mounting holes) on a shape."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    out = []
    for f in shape_h.Faces():
        s = BRepAdaptor_Surface(f.wrapped)
        if s.GetType() != GeomAbs_Cylinder:
            continue
        r = s.Cylinder().Radius()
        if r_lo <= r <= r_hi:
            c = f.Center()
            out.append((c.x, c.y, c.z, 2 * r))
    uniq = []
    for h in out:
        if not any(math.dist(h[:3], u[:3]) < 0.5 for u in uniq):
            uniq.append(h)
    return uniq


def _hole_report(board, body_raw_h):
    exp = boards.holes_h(board)
    n = np.asarray(boards.normal_h(board), float)
    found = _holes_in(body_raw_h)
    rows = []
    for e, (bp, bd) in zip(exp, BOSSES[board]):
        best = None
        for h in found:
            dv = np.subtract(h[:3], e)
            dv = dv - np.dot(dv, n) * n                       # in-plane offset only
            d = float(np.linalg.norm(dv))
            if best is None or d < best[0]:
                best = (d, h)
        bo = np.subtract(bp, e)
        bo = bo - np.dot(bo, n) * n
        rows.append({"expected_H": [round(v, 2) for v in e],
                     "found_H": None if best is None else [round(v, 3) for v in best[1][:3]],
                     "found_dia": None if best is None else round(best[1][3], 3),
                     "hole_to_boss_axis_mm": None if best is None else round(best[0] + float(np.linalg.norm(bo)), 3)})
    return rows, len(found)


def _face_gaps(board, body_h):
    """Gap between the board's mounting face and each boss tip (0 = seated)."""
    bb = body_h.BoundingBox()
    n = np.asarray(boards.normal_h(board), float)
    k = int(np.argmax(np.abs(n)))
    lo = [bb.xmin, bb.ymin, bb.zmin][k]
    hi = [bb.xmax, bb.ymax, bb.zmax][k]
    out = []
    for bp, bd in BOSSES[board]:
        face = lo if np.dot(bd, n) < 0 else hi                 # bosses behind the board touch its B face
        out.append(round(float(abs(face - bp[k])), 3))
    return out


def _raw_body_h(board, path):
    """The STEP board body (not thickness-normalised, so its holes stay cylinders), placed in H."""
    import cadquery as cq
    shp = cq.importers.importStep(path).val()
    body = max(shp.Solids(), key=lambda s: s.Volume())
    bb = body.BoundingBox()
    return body.translate(cq.Vector(-bb.xmin, -bb.ymax, -bb.zmax)).moved(boards.board_location(board))


def _b3_as_exported(path, items):
    """B3 at the 1.51 mm thickness of the fab STEP, right eye, against the eye parts (static)."""
    parts, info = boards.load_real("B3", path, thickness=1.51)
    placed = boards.place_real("B3", parts, "R")
    out = []
    for k, shp in placed.items():
        man = C.to_manifold(A.mesh_of(shp, 0.03, 0.2))
        for n, it in items.items():
            if it["group"] != "eye_R" or n.startswith("B3_"):
                continue
            d = man.min_gap(it["man"], 3.0)
            v = (man ^ it["man"]).volume() if d <= 1e-6 else 0.0
            if d < 1.0:
                out.append({"b3_item": k, "other": n, "min_mm": round(d, 3), "overlap_mm3": round(v, 3)})
    out.sort(key=lambda r: (-r["overlap_mm3"], r["min_mm"]))
    return out


def run(real=None, quick=False):
    A.use_real_boards(real or {})
    parts = A.build()
    meshes = A.meshes(parts, tol=C.TOL, ang=0.15)
    items = {}
    for mn, mesh in meshes.items():
        pn = mn.split("/")[0]
        p = parts[pn]
        man = C.to_manifold(mesh)
        if man.status() != C.m3.Error.NoError:
            import trimesh
            man = C.to_manifold(trimesh.convex.convex_hull(mesh))
        items[mn] = {"part": pn, "group": p.group, "man": man,
                     "shape": p.subs[mn.split("/")[1]] if "/" in mn else p.shape}
    G = C.grid(quick)
    old_search = C.SEARCH
    C.SEARCH = 6.0                      # report distances up to 6 mm (beyond: null)
    board_items = [n for n in items if n.split("/")[0] in BOARD_PARTS]
    groups = sorted({it["group"] for it in items.values()})
    by_group = {g: [n for n, it in items.items() if it["group"] == g] for g in groups}
    results = {}
    for bi in board_items:
        gb = items[bi]["group"]
        for g in groups:
            if g == gb:
                continue
            sides = {x.rpartition("_")[2] for x in (g, gb) if x not in ("fixed", "cradle")}
            if len(sides) > 1:
                continue
            others = list(by_group[g])
            if not others:
                continue
            C._CTX = ({bi: items[bi], **{o: items[o] for o in others}}, {gb: [bi], g: others})
            res, _ = C._sweep((gb, g, C.poses(set(C.dofs(g)) | set(C.dofs(gb)), G)))
            results.update(res)
    for bi in board_items:                                     # static neighbours in the board's group
        g = items[bi]["group"]
        for o in by_group[g]:
            if o.split("/")[0] == bi.split("/")[0]:
                continue
            xa, xb = items[bi]["man"], items[o]["man"]
            d = xa.min_gap(xb, C.SEARCH)
            vol = (xa ^ xb).volume() if d <= 1e-6 else 0.0
            results[(bi, o)] = {"min": d, "pose": {}, "vol": vol, "vol_pose": {} if vol else None, "groups": (g, g)}
    # nearest moving neighbour of each board over its sweep, even when farther than the 6 mm search
    nearest = {}
    C.SEARCH = 40.0
    for b in ("B1", "B2", "B4", "B3_R"):
        best = None
        for (na, nb), r in results.items():
            if not (na.startswith(b) or nb.startswith(b)) or r["groups"][0] == r["groups"][1]:
                continue
            typ, _, _ = C.classify(na, nb, False)
            if typ != "moving":
                continue
            mine, other = (na, nb) if na.startswith(b) else (nb, na)
            if r["min"] < 6.0:
                cand = (r["min"], mine, other, r["pose"])
            else:
                ga, gb = items[mine]["group"], items[other]["group"]
                C._CTX = ({mine: items[mine], other: items[other]}, {ga: [mine], gb: [other]})
                rr, _ = C._sweep((ga, gb, C.poses(set(C.dofs(ga)) | set(C.dofs(gb)), C.grid(True))))
                v = list(rr.values())[0]
                cand = (v["min"], mine, other, v["pose"])
            if best is None or cand[0] < best[0]:
                best = cand
        if best is None or best[0] >= 6.0:                    # nothing within 6 mm: sweep all of the other side
            for mine in [n for n in items if n.startswith(b)]:
                ga = items[mine]["group"]
                for other in by_group.get("cradle" if ga != "cradle" else "fixed", []):
                    gb = items[other]["group"]
                    C._CTX = ({mine: items[mine], other: items[other]}, {ga: [mine], gb: [other]})
                    rr, _ = C._sweep((ga, gb, C.poses(set(C.dofs(ga)) | set(C.dofs(gb)), C.grid(True))))
                    for v in rr.values():
                        if best is None or v["min"] < best[0]:
                            best = (v["min"], mine, other, v["pose"])
        if best:
            nearest[b[:2]] = {"min_mm": round(best[0], 2), "board_item": best[1], "other": best[2],
                              "pose": {k: round(v, 2) for k, v in best[3].items()}}
    out = {"generated_by": "cad/fit.py", "mode": "real boards (KiCad STEP)" if real else "spec section 4 envelopes",
           "thresholds": {"moving_mm": P.CLEAR_MOVING, "static_mm": P.CLEAR_STATIC}, "boards": {}}
    for b in ("B1", "B2", "B4", "B3"):
        rows = []
        for (na, nb), r in results.items():
            if not (na.startswith(b) or nb.startswith(b)):
                continue
            mine, other = (na, nb) if na.startswith(b) else (nb, na)
            typ, req, why = C.classify(na, nb, r["groups"][0] == r["groups"][1])
            ok = typ == "contact" or (typ == "joint" and req == 0) or (r["vol"] <= 0 and r["min"] >= req - 1e-3)
            rows.append({"board_item": mine, "other": other, "type": typ, "required_mm": req, "reason": why,
                         "min_mm": round(r["min"], 3) if r["min"] < C.SEARCH else None,
                         "pose": {k: round(v, 2) for k, v in r["pose"].items()}, "overlap_mm3": round(r["vol"], 4),
                         "pass": bool(ok)})
        rows.sort(key=lambda r: (r["type"] not in ("moving", "static"), r["min_mm"] if r["min_mm"] is not None else 99))
        entry = {"source": "envelope (spec section 4)",
                 "clearances": [r for r in rows if r["type"] in ("moving", "static")][:25],
                 "designed_contacts": [r for r in rows if r["type"] in ("contact", "joint")],
                 "collisions": [r for r in rows if r["type"] in ("moving", "static") and r["overlap_mm3"] > 0],
                 "below_threshold": [r for r in rows if r["type"] in ("moving", "static") and not r["pass"]
                                     and r["overlap_mm3"] <= 0]}
        if b in (real or {}):
            entry["source"] = boards.source_label(real[b])
            _, info = boards.load_real(b, real[b])
            entry["step_info"] = info
            entry["missing_models_added_as_envelopes"] = {
                "B1": "J1 AFC07 FPC connector", "B2": "J10-J19 Molex 5267 headers, J1/J2 USB-C, THT tails",
                "B3": "12 x WS2812C-2020 LEDs"}.get(b, "none")
        if b in BOSSES:
            body = parts[b].subs["board"]
            raw = _raw_body_h(b, real[b]) if b in (real or {}) else body
            hr, nfound = _hole_report(b, raw)
            entry["holes"] = hr
            entry["holes_found_on_board"] = nfound
            entry["mount_face_gap_mm"] = _face_gaps(b, body)
        if b == "B3" and "B3" in (real or {}):
            entry["as_exported_1p51mm"] = {
                "note": "fab STEP body is 1.51 mm; the board is ordered 0.8 mm and the seat is designed for 0.8 mm. "
                        "These are the contacts the 1.51 mm board would make with the eye parts (right eye).",
                "contacts": _b3_as_exported(real["B3"], items)}
        entry["nearest_moving_part"] = nearest.get(b)
        out["boards"][b] = entry
    zone = C.to_manifold(A.mesh_of(boards.antenna_zone(), 0.1, 0.3))
    hits = []
    for n, it in items.items():
        if it["group"] == "cradle" and parts[it["part"]].kind == "printed":
            v = (zone ^ it["man"]).volume()
            if v > 1e-3:
                hits.append({"part": n, "overlap_mm3": round(v, 3)})
    out["boards"]["B1"]["antenna_keepout_5mm"] = {"intrusions": hits, "pass": not hits}
    C.SEARCH = old_search
    path = os.path.join(A.OUT, "fit.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    for b, e in out["boards"].items():
        cl = [r for r in e["clearances"] if r["min_mm"] is not None]
        worst = cl[0] if cl else None
        print(f"{b}: collisions {len(e['collisions'])}, below threshold {len(e['below_threshold'])}, closest "
              + (f"{worst['other']} {worst['min_mm']} mm ({worst['type']})" if worst else "> 6 mm")
              + (f", hole-to-boss {[h['hole_to_boss_axis_mm'] for h in e['holes']]}, face gaps {e['mount_face_gap_mm']}"
                 if "holes" in e else ""))
    print("antenna keepout:", out["boards"]["B1"]["antenna_keepout_5mm"])
    if "as_exported_1p51mm" in out["boards"]["B3"]:
        print("B3 at 1.51 mm:", out["boards"]["B3"]["as_exported_1p51mm"]["contacts"][:4])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", default=None, help="folder with the board STEP files")
    ap.add_argument("--envelopes", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    real = {} if a.envelopes else A.resolve_boards(a.boards)
    run(real, quick=a.quick)
