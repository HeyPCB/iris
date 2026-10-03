"""Board fit check: mounting holes vs bosses, mounting-face contact, and clearance of each board
(envelope or real KiCad STEP) to every other part over the motion that moves it relative to them.

  python -m cad.fit                                   # spec section 4 envelopes
  python -m cad.fit --B1 cortex.step --B2 brainstem.step --B3 ring.step --B4 brow.step

A real board replaces its envelope. B1 rides on the cradle (checked over the tilt sweep), B2 and B4
are fixed (checked against the moving cradle, eyes, lids and brows), B3 rides in each eye.
Output: cad/out/fit.json
"""
import argparse
import json
import math
import os

import numpy as np

from . import assembly as A
from . import check as C
from . import params as P
from .parts import boards

BOSSES = {   # mount boss axes in H: (point on the mounting face, axis direction into the boss)
    "B1": [((P.B1_BOSS_X[1], y, z), (-1, 0, 0)) for y, z in P.B1["holes_yz"]],
    "B2": [((x, y, P.B2_BOSS_Z[1]), (0, 0, -1)) for x, y in P.B2["holes_xy"]],
    "B4": [((P.B4["f_x"], y, z), (1, 0, 0)) for y, z in P.B4["holes_yz"]],
}
MOUNT_PARTS = {"B1": "spine", "B2": "base_plate", "B4": "face_shell"}
GROUP = {"B1": "cradle", "B2": "fixed", "B4": "fixed"}


def _holes_in(shape_h, r_lo=1.0, r_hi=1.2):
    """Centres (H) of cylindrical faces with radius in [r_lo, r_hi] (mounting holes) on a shape."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    out = []
    for f in shape_h.Faces():
        s = BRepAdaptor_Surface(f.wrapped)
        if s.GetType() != GeomAbs_Cylinder:
            continue
        cyl = s.Cylinder()
        r = cyl.Radius()
        if r_lo <= r <= r_hi:
            c = f.Center()
            out.append((round(c.x, 3), round(c.y, 3), round(c.z, 3), round(2 * r, 3)))
    uniq = []
    for h in out:
        if not any(math.dist(h[:3], u[:3]) < 0.5 for u in uniq):
            uniq.append(h)
    return uniq


def _hole_report(board, body_h):
    exp = boards.holes_h(board)
    n = boards.normal_h(board)
    found = _holes_in(body_h)
    rows = []
    for e, (bp, bd) in zip(exp, BOSSES[board]):
        best = None
        for h in found:
            dvec = np.subtract(h[:3], e)
            dvec = dvec - np.dot(dvec, n) * np.asarray(n)      # in-plane offset only
            d = float(np.linalg.norm(dvec))
            if best is None or d < best[0]:
                best = (d, h)
        boss_off = np.subtract(bp, e)
        boss_off = boss_off - np.dot(boss_off, n) * np.asarray(n)
        rows.append({"expected_H": [round(v, 2) for v in e],
                     "found_H": None if best is None else list(best[1][:3]),
                     "found_dia": None if best is None else best[1][3],
                     "hole_offset_mm": None if best is None else round(best[0], 3),
                     "boss_axis_offset_mm": round(float(np.linalg.norm(boss_off)), 3)})
    return rows, len(found)


def _face_gap(board, body_h):
    """Distance between the board body and each boss tip face (0 = seated)."""
    bb = body_h.BoundingBox()
    n = np.asarray(boards.normal_h(board), float)
    gaps = []
    for bp, bd in BOSSES[board]:
        # mounting face coordinate along the normal: B face for B1/B2 (bosses behind), F face for B4
        lo = np.array([bb.xmin, bb.ymin, bb.zmin])
        hi = np.array([bb.xmax, bb.ymax, bb.zmax])
        k = int(np.argmax(np.abs(n)))
        face = lo[k] if np.dot(bd, n) < 0 else hi[k]
        gaps.append(round(float(abs(face - bp[k])), 3))
    return gaps


def run(real=None, quick=False):
    real = real or {}
    parts = A.build()
    info = {}
    # replace envelopes by real boards where given
    for b, path in real.items():
        if b == "B3":
            continue
        shp, body, meta = boards.load_real(b, path)
        name = f"{b}_env"
        p = parts[name]
        p.shape, p.subs, p.label = shp, {}, f"{b} real board ({os.path.basename(path)})"
        p.kind = "board_real"
        info[b] = {"source": path, **meta, "body": body}
    meshes = {}
    for n, p in parts.items():
        if n in [f"{b}_env" for b in real if b != "B3"]:
            m = A.mesh_of(p.shape, 0.1, 0.3)
            meshes[n] = m
    meshes.update({k: v for k, v in A.meshes(parts, tol=C.TOL, ang=0.15).items() if k.split("/")[0] not in meshes})
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
    C.SEARCH = 6.0                      # report distances up to 6 mm (beyond: listed as null)
    board_items = [n for n in items if n.split("/")[0] in ("B1_env", "B2_env", "B4_env", "B3_env_R", "B3_env_L")]
    groups = sorted({it["group"] for it in items.values()})
    by_group = {g: [n for n, it in items.items() if it["group"] == g] for g in groups}
    C._CTX = (items, by_group)
    jobs = []
    for bi in board_items:
        gb = items[bi]["group"]
        for g in groups:
            sides = {x.rpartition("_")[2] for x in (g, gb) if x not in ("fixed", "cradle")}
            if len(sides) > 1:
                continue
            others = [n for n in by_group[g] if n not in board_items or n == bi]
            if g == gb:
                continue
            jobs.append((bi, g, C.poses(set(C.dofs(g)) | set(C.dofs(gb)), G), others))
    results = {}
    for bi, g, pl, others in jobs:
        sub_ctx = {bi: items[bi], **{o: items[o] for o in others}}
        C._CTX = (sub_ctx, {items[bi]["group"]: [bi], g: others})
        res, _ = C._sweep((items[bi]["group"], g, pl))
        results.update(res)
    # static neighbours in the board's own group
    for bi in board_items:
        g = items[bi]["group"]
        for o in by_group[g]:
            if o == bi or o.split("/")[0] == bi.split("/")[0]:
                continue
            xa, xb = items[bi]["man"], items[o]["man"]
            d = xa.min_gap(xb, C.SEARCH)
            vol = (xa ^ xb).volume() if d <= 1e-6 else 0.0
            results[(bi, o)] = {"min": d, "pose": {}, "vol": vol, "vol_pose": {} if vol else None, "groups": (g, g)}
    out = {"generated_by": "cad/fit.py", "mode": "real boards" if real else "spec section 4 envelopes", "boards": {}}
    for b in ("B1", "B2", "B4", "B3"):
        rows = []
        for (na, nb), r in results.items():
            if not (na.startswith(b) or nb.startswith(b)):
                continue
            mine, other = (na, nb) if na.startswith(b) else (nb, na)
            typ, req, why = C.classify(na, nb, r["groups"][0] == r["groups"][1])
            rows.append({"board_item": mine, "other": other, "type": typ, "required_mm": req, "reason": why,
                         "min_mm": round(r["min"], 3) if r["min"] < C.SEARCH else None,
                         "pose": {k: round(v, 2) for k, v in r["pose"].items()}, "overlap_mm3": round(r["vol"], 4),
                         "pass": typ in ("contact", "joint") or (r["vol"] <= 0 and r["min"] >= req - 1e-3)})
        rows.sort(key=lambda r: r["min_mm"] if r["min_mm"] is not None else 99)
        entry = {"source": info.get(b, {}).get("source", "envelope (spec section 4)"),
                 "clearances": rows[:20], "collisions": [r for r in rows if r["type"] in ("moving", "static") and r["overlap_mm3"] > 0],
                 "below_threshold": [r for r in rows if r["type"] in ("moving", "static") and not r["pass"] and r["overlap_mm3"] <= 0]}
        if b in BOSSES:
            body = info[b]["body"] if b in info else boards.envelope(b)["board"]
            hr, nfound = _hole_report(b, body)
            entry["holes"] = hr
            entry["holes_found_on_board"] = nfound
            entry["mount_face_gap_mm"] = _face_gap(b, body)
            if b in info:
                entry["step_info"] = {k: v for k, v in info[b].items() if k not in ("body", "source")}
        out["boards"][b] = entry
    # antenna keepout: no printed plastic within 5 mm of the WROOM antenna (spec 7.1 P5)
    zone = C.to_manifold(A.mesh_of(boards.antenna_zone(), 0.1, 0.3))
    hits = []
    for n, it in items.items():
        if it["group"] == "cradle" and parts[it["part"]].kind == "printed":
            v = (zone ^ it["man"]).volume()
            if v > 1e-3:
                hits.append({"part": n, "overlap_mm3": round(v, 3)})
    out["boards"]["B1"]["antenna_keepout_5mm"] = {"intrusions": hits, "pass": not hits}
    path = os.path.join(A.OUT, "fit.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    for b, e in out["boards"].items():
        worst = next((r for r in e["clearances"] if r["type"] in ("moving", "static") and r["min_mm"] is not None), None)
        print(f"{b}: collisions {len(e['collisions'])}, below threshold {len(e['below_threshold'])}, "
              f"closest {worst['other'] if worst else '-'} {worst['min_mm'] if worst else '-'} mm"
              + (f", holes off {[h['hole_offset_mm'] for h in e['holes']]}, face gaps {e['mount_face_gap_mm']}" if 'holes' in e else ""))
    print("antenna keepout:", out["boards"]["B1"]["antenna_keepout_5mm"])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for b in ("B1", "B2", "B3", "B4"):
        ap.add_argument("--" + b, default=None)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    real = {b: getattr(a, b) for b in ("B1", "B2", "B3", "B4") if getattr(a, b)}
    run(real, quick=a.quick)
