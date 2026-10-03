"""Iris motion check: sweeps every pair of moving groups over the poses that change their relative
position, reports minimum clearances and any collisions to cad/out/check.json.

  python -m cad.check            # full sweep
  python -m cad.check --quick    # coarse grid (development)

Method
  * Every part (or sub-solid) is tessellated (chordal tolerance 0.04 mm) and turned into a manifold
    mesh (manifold3d). For each pair of motion groups, only the degrees of freedom that move one
    relative to the other are swept (e.g. eye vs upper lid: tilt x pan x upper-lid angle).
  * Lid angles are swept inside the firmware lid envelope (lids follow gaze: upper = rest + tilt +
    [-37 (blink) .. +36], lower = rest + 0.5 tilt + [-30 .. +14], clamped to the mechanical ranges);
    pairs that do not depend on tilt see the full mechanical range.
  * Per pose: manifold min_gap (exact triangle distance, 3 mm search) and, when touching, the
    intersection volume. The worst pose of every pair closer than 1.5 mm is re-measured exactly on
    the B-rep solids (OpenCASCADE BRepExtrema).
  * Pair types: 'moving' (different groups, >= 0.5 mm required), 'static' (same group, >= 0.3 mm),
    'contact' (designed contact: fasteners, glued seats; must not interpenetrate > 0.05 mm3) and
    'joint' (designed running fits: pins in bores, ball links on studs, pivot faces, nested lids;
    reported with their own expected minimum).
"""
import argparse
import fnmatch
import itertools
import json
import os
import time

import manifold3d as m3
import numpy as np

from . import assembly as A
from . import kinematics as K
from . import params as P

TOL = 0.04
SEARCH = 3.0

# ------------------------------------------------------------------------------------- DOFs and grid
def dofs(group):
    if group == "fixed":
        return ()
    if group == "cradle":
        return ("tilt",)
    kind, _, s = group.partition("_")
    if kind in ("eye", "crank", "pcoup"):
        return ("tilt", "pan_" + s)
    if kind in ("lidU", "hornU", "rodU"):
        return ("up_" + s,)
    if kind in ("lidL", "hornL", "rodL"):
        return ("lo_" + s,)
    if kind == "brow":
        return ("brow_" + s,)
    raise KeyError(group)


def grid(quick=False):
    if quick:
        return {"tilt": [-30.0, 0.0, 25.0], "pan": [-35.0, 0.0, 35.0], "up": list(np.linspace(-40, 55, 6)),
                "lo": list(np.linspace(-50, -6, 4)), "brow": [-20.0, 0.0, 20.0]}
    return {"tilt": [-30.0, -22.5, -15.0, -7.5, 0.0, 6.25, 12.5, 18.75, 25.0],
            "pan": [-35.0, -26.25, -17.5, -8.75, 0.0, 8.75, 17.5, 26.25, 35.0],
            "up": [float(v) for v in np.linspace(-40, 55, 20)],
            "lo": [float(v) for v in np.linspace(-50, -6, 12)],
            "brow": [-20.0, -10.0, 0.0, 10.0, 20.0]}


def _in(v, rng, eps=1e-6):
    return rng[0] - eps <= v <= rng[1] + eps


def _vals_in(vals, rng):
    out = [v for v in vals if _in(v, rng)]
    for e in rng:
        if not any(abs(e - v) < 1e-6 for v in out):
            out.append(e)
    return sorted(out)


def poses(dset, G, unrestricted=False):
    """Pose list (dicts) over the DOFs in dset, with the lid envelope constraints (unless
    unrestricted: every lid angle in its mechanical range at every tilt)."""
    dset = sorted(dset)
    has_t = "tilt" in dset and not unrestricted
    tilts = G["tilt"] if "tilt" in dset else [None]
    out = []
    for t in tilts:
        axes = []
        for d in dset:
            if d == "tilt":
                continue
            if d.startswith("pan"):
                axes.append((d, G["pan"]))
            elif d.startswith("brow"):
                axes.append((d, G["brow"]))
            elif d.startswith("up"):
                axes.append((d, _vals_in(G["up"], K.up_envelope(t)) if has_t else G["up"]))
            elif d.startswith("lo"):
                axes.append((d, _vals_in(G["lo"], K.lo_envelope(t)) if has_t else G["lo"]))
        for combo in itertools.product(*[a[1] for a in axes]) if axes else [()]:
            q = {} if t is None else {"tilt": t}
            if unrestricted:
                q.update({a[0]: v for a, v in zip(axes, combo)})
                out.append(q)
                continue
            q.update({a[0]: v for a, v in zip(axes, combo)})
            # lids of one eye swept together without tilt: keep only combinations some tilt allows
            for s in P.SIDES:
                if not has_t and ("up_" + s) in q and ("lo_" + s) in q:
                    if not any(_in(q["up_" + s], K.up_envelope(tt)) and _in(q["lo_" + s], K.lo_envelope(tt))
                               for tt in np.linspace(-30, 25, 56)):
                        break
            else:
                out.append(q)
    return out


# ------------------------------------------------------------------------------------- pair rules
# Designed contacts inside one rigid group (fasteners, glued or pressed seats).
CONTACTS = [
    ("column", "servo_*/body", "lid/tilt servo ears clamp on the column faces"),
    ("column", "nose_block", "screwed"), ("column", "top_bridge", "screwed"), ("column", "base_plate", "screwed"),
    ("nose_block", "nasal_pin_R", "pin pressed in"),
    ("side_plate_*", "top_bridge", "screwed"), ("side_plate_*", "base_plate", "screwed"),
    ("side_plate_R", "temple_pin_R", "pin pressed in"), ("side_plate_L", "temple_pin_L", "pin pressed in"),
    ("top_bridge", "servo_brow_*/body", "brow servo ears screwed to the brackets"),
    ("base_plate", "B2_env/board", "B2 B face on the bosses"), ("base_plate", "speaker", "speaker in its ring"),
    ("face_shell", "base_plate", "shell sits on the base plate"), ("face_shell", "back_cover", "seam"),
    ("face_shell", "B4_env/board", "B4 F face on the shell bosses"), ("back_cover", "base_plate", "cover sits on the base"),
    ("spine", "fork_*", "bolted"), ("spine", "temple_arm_*", "bolted at the rail ends"),
    ("spine", "B1_env/board", "B1 B face on the bosses"), ("spine", "tongue_pin", "drive pin in the radial slot"),
    ("temple_arm_*", "servo_pan_*/body", "pan servo ears on the ledges"), ("temple_arm_*", "temporal_pin_*", "pressed"),
    ("temple_arm_R", "bearing_R", "pressed"), ("fork_*", "pole_pins_*", "pressed"),
    ("tilt_tongue", "nasal_pin_L", "pressed"), ("tilt_tongue", "tongue_pin", "pressed"),
    ("sclera_*/shell", "cornea_*", "glued in the limbus bore"), ("sclera_*/shell", "carrier_*", "glued"),
    ("sclera_*/shell", "iris_*", "slip fit in the bore"), ("sclera_*/bosses", "sclera_*/shell", "same part"),
    ("sclera_*/shell", "keel_stud_*", "screwed"), ("carrier_*", "camera", "camera in its pocket"),
    ("carrier_*", "B3_env_*/*", "B3 seated in the carrier"), ("iris_*", "B3_env_*/*", "cone ring clamps B3"),
    ("iris_*", "cornea_*", "cornea base on the iris disc"), ("iris_*", "camera", "pupil sleeve over the lens step"),
    ("camera", "B3_env_*/*", "B3 rests on the camera holder"), ("iris_*", "carrier_*", "cone ring on the carrier wall"),
    ("lid*_*/shell", "lid*_*/boss", "same part"), ("lid*_stud_*", "lid*_*/*", "stud screwed into the boss"),
    ("horn*_stud_*", "horn*_*", "stud screwed into the horn"), ("brow_*", "brow_hub_*", "keyed"),
    ("pan_crank_*", "crank_stud_*", "screwed"),
]

# Designed running fits between groups: (a, b, expected minimum, reason)
JOINTS = [
    ("sclera_*/bosses", "pole_pins_*", 0.0, "pan pivot: pin runs in the boss bore"),
    ("sclera_*/shell", "pole_pins_*", 0.0, "pole pin passes the shell bore"),
    ("sclera_*/bosses", "fork_*", 0.25, "pan pivot axial running gap (boss face to fork arm)"),
    ("keel_stud_*", "pan_coupler_*", 0.0, "ball joint"), ("crank_stud_*", "pan_coupler_*", 0.0, "ball joint"),
    ("pan_crank_*", "servo_pan_*/spline", 0.0, "crank on the spline"),
    ("lid*_*/*", "nasal_pin_*", 0.0, "lid hub on its pin"), ("lid*_*/*", "temporal_pin_*", 0.0, "lid hub on its pin"),
    ("lidU_*/shell", "lidL_*/shell", 0.15, "nested lid shells, designed 0.2 mm (spec 2.5)"),
    ("lid*_stud_*", "rod*_*", 0.0, "ball joint"), ("horn*_stud_*", "rod*_*", 0.0, "ball joint"),
    ("lidU_*/boss", "rodU_*", 0.15, "ball-link face on its own boss"), ("lidL_*/boss", "rodL_*", 0.15, "ball-link face on its own boss"),
    ("hornU_*", "rodU_*", 0.15, "ball-link face on its own horn"), ("hornL_*", "rodL_*", 0.15, "ball-link face on its own horn"),
    ("horn*_*", "servo_lid*/spline", 0.0, "horn on the spline"),
    ("brow_hub_*", "servo_brow_*/spline", 0.0, "hub on the spline"),
    ("tilt_tongue", "servo_tilt/spline", 0.0, "P8 clamps the tilt spline"),
    ("nasal_pin_L", "servo_tilt/spline", 0.0, "coaxial, both turn with the tilt output"),
    ("temple_arm_R", "temple_pin_R", 0.0, "MR63ZZ seat around the temple pin"),
    ("bearing_R", "temple_pin_R", 0.0, "bearing on the pin"),
    ("temple_arm_L", "temple_pin_L", 0.0, "loose bushing, 0.2 mm diametral play"),
]


def _m(name, pat):
    return fnmatch.fnmatchcase(name, pat)


def classify(a, b, same_group):
    for pa, pb, why in CONTACTS:
        if (_m(a, pa) and _m(b, pb)) or (_m(a, pb) and _m(b, pa)):
            return "contact", 0.0, why
    for pa, pb, emin, why in JOINTS:
        if (_m(a, pa) and _m(b, pb)) or (_m(a, pb) and _m(b, pa)):
            return "joint", emin, why
    return ("static", P.CLEAR_STATIC, "") if same_group else ("moving", P.CLEAR_MOVING, "")


# ------------------------------------------------------------------------------------- geometry
def to_manifold(mesh):
    mm = m3.Mesh(vert_properties=np.ascontiguousarray(mesh.vertices, dtype=np.float32),
                 tri_verts=np.ascontiguousarray(mesh.faces, dtype=np.uint32))
    man = m3.Manifold(mm)
    if man.status() != m3.Error.NoError:
        mesh = mesh.copy()
        mesh.merge_vertices()
        mesh.fix_normals()
        mm = m3.Mesh(vert_properties=np.ascontiguousarray(mesh.vertices, dtype=np.float32),
                     tri_verts=np.ascontiguousarray(mesh.faces, dtype=np.uint32))
        man = m3.Manifold(mm)
    return man


def _bbox(man, M):
    lo, hi = np.array(man.bounding_box()[:3]), np.array(man.bounding_box()[3:])
    c = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    c = c @ M[:3, :3].T + M[:3, 3]
    return c.min(0), c.max(0)


def _occ_dist(sa, sb, Ma, Mb):
    import cadquery as cq
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Trsf

    def mv(s, M):
        t = gp_Trsf()
        t.SetValues(*[float(M[i, j]) for i in range(3) for j in range(4)])
        return s.moved(cq.Location(t))
    d = BRepExtrema_DistShapeShape(mv(sa, Ma).wrapped, mv(sb, Mb).wrapped)
    d.Perform()
    return float(d.Value()) if d.IsDone() else None


# ------------------------------------------------------------------------------------- run
_CTX = None


def _sweep(job):
    """Sweep one pair of motion groups over its poses."""
    ga, gb, pl = job
    items, by_group = _CTX
    out, ne = {}, 0
    for q in pl:
        Ma, Mb = K.group_transform(ga, q), K.group_transform(gb, q)
        ta = {n: (items[n]["man"].transform(Ma[:3, :4]), _bbox(items[n]["man"], Ma)) for n in by_group[ga]}
        tb = {n: (items[n]["man"].transform(Mb[:3, :4]), _bbox(items[n]["man"], Mb)) for n in by_group[gb]}
        for na, (xa, (alo, ahi)) in ta.items():
            for nb, (xb, (blo, bhi)) in tb.items():
                if np.any(alo > bhi + SEARCH) or np.any(blo > ahi + SEARCH):
                    continue
                typ, req, _ = classify(na, nb, False)
                if typ == "contact" or (typ == "joint" and req == 0.0):
                    out.setdefault((na, nb), {"min": 0.0, "pose": q, "vol": 0.0, "vol_pose": None, "groups": (ga, gb),
                                              "designed": True})
                    continue
                ne += 1
                d = xa.min_gap(xb, SEARCH)
                vol = (xa ^ xb).volume() if d <= 1e-6 else 0.0
                r = out.get((na, nb))
                if r is None:
                    out[(na, nb)] = {"min": d, "pose": q, "vol": vol, "vol_pose": q if vol > 0 else None, "groups": (ga, gb)}
                else:
                    if d < r["min"]:
                        r["min"], r["pose"] = d, q
                    if vol > r["vol"]:
                        r["vol"], r["vol_pose"] = vol, q
    return out, ne


def run(quick=False, verbose=True):
    t0 = time.time()
    parts = A.build(verbose=verbose)
    meshes = A.meshes(parts, tol=TOL, ang=0.15)
    items = {}
    for mn, mesh in meshes.items():
        pn = mn.split("/")[0]
        p = parts[pn]
        if not p.check:
            continue
        items[mn] = {"part": pn, "group": p.group, "man": to_manifold(mesh),
                     "shape": p.subs[mn.split("/")[1]] if "/" in mn else p.shape}
    bad = [n for n, it in items.items() if it["man"].status() != m3.Error.NoError]
    G = grid(quick)
    groups = sorted({it["group"] for it in items.values()})
    by_group = {g: [n for n, it in items.items() if it["group"] == g] for g in groups}
    t1 = time.time()
    if verbose:
        print(f"  build + mesh {t1 - t0:.1f} s, {len(items)} solids", flush=True)
    jobs = []
    pose_count = {}
    for ga, gb in itertools.combinations(groups, 2):
        sides = {g.rpartition("_")[2] for g in (ga, gb) if g not in ("fixed", "cradle")}
        if len(sides) > 1:
            continue                     # groups of different eyes never meet
        pl = poses(set(dofs(ga)) | set(dofs(gb)), G)
        pose_count[f"{ga}|{gb}"] = len(pl)
        jobs.append((ga, gb, pl))
    global _CTX
    _CTX = (items, by_group)
    results = {}
    n_eval = 0
    for job in jobs:
        res, ne = _sweep(job)
        results.update(res)
        n_eval += ne
    if verbose:
        print(f"  moving sweep {time.time() - t1:.1f} s, {n_eval} evaluations", flush=True)
    # static pairs (same group, rest pose)
    for g in groups:
        for na, nb in itertools.combinations(by_group[g], 2):
            if items[na]["part"] == items[nb]["part"] and not any(
                    _m(na, a) and _m(nb, b) or _m(nb, a) and _m(na, b) for a, b, _ in CONTACTS):
                continue
            M = np.eye(4)
            xa, xb = items[na]["man"], items[nb]["man"]
            (alo, ahi), (blo, bhi) = _bbox(xa, M), _bbox(xb, M)
            if np.any(alo > bhi + SEARCH) or np.any(blo > ahi + SEARCH):
                continue
            n_eval += 1
            d = xa.min_gap(xb, SEARCH)
            typ, _, _ = classify(na, nb, True)
            vol = (xa ^ xb).volume() if d <= 1e-6 else 0.0
            results[(na, nb)] = {"min": d, "pose": {}, "vol": vol, "vol_pose": {} if vol > 0 else None, "groups": (g, g)}
    # classify + exact refinement
    rows = []
    for (na, nb), r in results.items():
        ga, gb = r["groups"]
        typ, req, why = classify(na, nb, ga == gb)
        row = {"a": na, "b": nb, "groups": [ga, gb], "type": typ, "required_mm": req, "reason": why,
               "mesh_min_mm": round(r["min"], 3), "pose": {k: round(v, 2) for k, v in r["pose"].items()},
               "overlap_mm3": round(r["vol"], 4)}
        if r["vol"] > 0:
            row["overlap_pose"] = {k: round(v, 2) for k, v in r["vol_pose"].items()}
        if (typ in ("moving", "static") or (typ == "joint" and req > 0)) and r["min"] < 1.5 and r["vol"] <= 0 and not r.get("designed"):
            Ma, Mb = K.group_transform(ga, r["pose"]), K.group_transform(gb, r["pose"])
            ex = _occ_dist(items[na]["shape"], items[nb]["shape"], Ma, Mb)
            row["exact_min_mm"] = None if ex is None else round(ex, 3)
        val = row.get("exact_min_mm", row["mesh_min_mm"])
        if val is None:
            val = row["mesh_min_mm"]
        row["min_mm"] = round(val, 3) if val < SEARCH - 1e-6 else None   # None = more than 3 mm
        if typ == "contact" or (typ == "joint" and req == 0.0):
            row["pass"] = True                       # designed contact / fit: envelopes may overlap
        elif typ == "joint":
            row["pass"] = r["vol"] <= 0.0 and val >= req - 1e-3
        else:
            row["pass"] = r["vol"] <= 0.0 and val >= req - 1e-3
        rows.append(row)
    rows.sort(key=lambda r: (r["min_mm"] if r["min_mm"] is not None else 99, r["a"]))
    collisions = [r for r in rows if r["type"] in ("moving", "static") and r["overlap_mm3"] > 0]
    below = [r for r in rows if r["type"] in ("moving", "static") and not r["pass"] and r["overlap_mm3"] <= 0]
    jbad = [r for r in rows if r["type"] in ("joint", "contact") and not r["pass"]]

    named = named_poses(items, by_group)
    negative = negative_controls(items, by_group)
    mech = mechanical_range(items, by_group, groups, verbose)

    def best(typ):
        rr = [r for r in rows if r["type"] == typ and r["min_mm"] is not None]
        return rr[0] if rr else None
    out = {
        "generated_by": "cad/check.py" + (" --quick" if quick else ""),
        "units": "mm, deg",
        "method": __doc__.split("Method")[1].strip(),
        "thresholds": {"moving_mm": P.CLEAR_MOVING, "static_mm": P.CLEAR_STATIC},
        "tessellation_tol_mm": TOL,
        "grid": G,
        "lid_envelope": {"upper": "clamp(UP_REST + tilt + [%g, %g], %s)" % (P.UP_FOLLOW["closed"], P.UP_FOLLOW["open_max"], list(P.UP_RANGE)),
                         "lower": "clamp(LO_REST + 0.5 tilt + [%g, %g], %s)" % (P.LO_FOLLOW["low"], P.LO_FOLLOW["high"], list(P.LO_RANGE))},
        "pose_evaluations": n_eval,
        "group_pairs_swept": len(pose_count),
        "non_manifold_meshes": bad,
        "summary": {
            "collisions": len(collisions),
            "below_threshold": len(below),
            "joint_or_contact_problems": len(jbad),
            "min_moving": best("moving"),
            "min_static": best("static"),
            "pairs_checked": len(rows),
        },
        "collisions": collisions,
        "below_threshold": below,
        "joint_or_contact_problems": jbad,
        "closest_moving_pairs": [r for r in rows if r["type"] == "moving" and r["min_mm"] is not None][:40],
        "closest_static_pairs": [r for r in rows if r["type"] == "static" and r["min_mm"] is not None][:25],
        "joints": [r for r in rows if r["type"] == "joint"],
        "named_poses": named,
        "mechanical_lid_range_outside_envelope": mech,
        "negative_controls": negative,
        "kinematics": K.table(),
        "runtime_s": round(time.time() - t0, 1),
    }
    os.makedirs(A.OUT, exist_ok=True)
    path = os.path.join(A.OUT, "check.json" if not quick else "check_quick.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    if verbose:
        print(f"pairs {len(rows)}, evaluations {n_eval}, collisions {len(collisions)}, below threshold {len(below)}, "
              f"joint/contact problems {len(jbad)}, {out['runtime_s']} s -> {path}")
        for r in collisions[:30]:
            print("  COLLISION %-24s %-24s %8.3f mm3 at %s" % (r["a"], r["b"], r["overlap_mm3"], r.get("overlap_pose")))
        for r in below[:30]:
            print("  BELOW     %-24s %-24s %6.3f mm (need %.1f) at %s" % (r["a"], r["b"], r["min_mm"], r["required_mm"], r["pose"]))
        for r in jbad[:30]:
            print("  JOINT/CONTACT %-20s %-24s min %.3f overlap %.4f (%s)" % (r["a"], r["b"], r["mesh_min_mm"], r["overlap_mm3"], r["reason"]))
        for typ in ("moving", "static"):
            b = best(typ)
            if b:
                print(f"  min {typ}: {b['min_mm']} mm  {b['a']} x {b['b']} at {b['pose']}")
    return out


SPEC_POSES = {   # spec 2.9 sweep extremes (tilt, pan both eyes, upper, lower) plus the render poses
    "rest": (0, 0, P.UP_REST, P.LO_REST),
    "down30_pan-35_blink": (-30, -35, -40, -35), "down30_pan+35_blink": (-30, 35, -40, -35),
    "up25_pan+35_wide": (25, 35, 55, -7.5), "up25_wide_open": (25, 0, 55, -6),
    "lids_closed_tucked": (0, 0, -12, -6), "lids_fully_open": (0, 0, 55, -50),
    "down30_blink_lower_low": (-30, 0, -12, -50),
    "up25_pan-35": (25, -35, 44, -7.5), "down30_pan+35": (-30, 35, -11, -35),
}


# hubs that turn coaxially above their own servo's gear cover: constant gap, left out of the per-pose
# minima so those show what the pose changes (they are still in the full sweep)
COAXIAL = [("horn*_*", "servo_lid*/body"), ("brow_hub_*", "servo_brow_*/body"), ("pan_crank_*", "servo_pan_*/body")]


def _pose(t, p, u, l, verge=False):
    return {"tilt": t, "pan_R": p, "pan_L": -p if verge else p, "up_R": u, "up_L": u, "lo_R": l, "lo_L": l}


def _all_moving_min(items, by_group, q):
    """Smallest clearance over all moving (non-designed) pairs at one full pose."""
    groups = sorted(by_group)
    T = {}
    for g in groups:
        M = K.group_transform(g, q)
        for n in by_group[g]:
            T[n] = (items[n]["man"].transform(M[:3, :4]), _bbox(items[n]["man"], M), g)
    found = []
    hits = []
    names = list(T)
    for i, na in enumerate(names):
        xa, (alo, ahi), ga = T[na]
        for nb in names[i + 1:]:
            xb, (blo, bhi), gb = T[nb]
            if ga == gb or np.any(alo > bhi + SEARCH) or np.any(blo > ahi + SEARCH):
                continue
            typ, req, _ = classify(na, nb, False)
            if typ != "moving" or any(_m(na, x) and _m(nb, y) or _m(nb, x) and _m(na, y) for x, y in COAXIAL):
                continue
            d = xa.min_gap(xb, SEARCH)
            if d <= 1e-6:
                hits.append((na, nb, round((xa ^ xb).volume(), 4)))
            if d < SEARCH:
                found.append((round(d, 3), na, nb))
    found.sort()
    return found, hits


def named_poses(items, by_group):
    out = {}
    for name, (t, p, u, l) in SPEC_POSES.items():
        for verge in (False, True):
            q = _pose(t, p, u, l, verge)
            found, hits = _all_moving_min(items, by_group, q)
            out[name + ("_vergence" if verge else "")] = {"pose": q, "min_moving_mm": found[0][0] if found else None,
                                                         "closest_pairs": found[:6], "collisions": hits}
            if p == 0:
                break
    return out


def negative_controls(items, by_group):
    """Poses outside the design range that must collide; proves the sweep detects contact."""
    cases = {
        "pan 55 deg (beyond +-35): fork arm vs sclera rim": _pose(0, 55, P.UP_REST, P.LO_REST),
        "tilt +45 deg (beyond +25): cradle vs frame": _pose(45, 0, 64, 2.5),
        "upper lid +85 deg (beyond +55): pushrod over the lid pin": _pose(0, 0, 85, P.LO_REST),
    }
    out = {}
    for name, q in cases.items():
        _, hits = _all_moving_min(items, by_group, q)
        out[name] = {"pose": q, "collisions_found": len(hits), "examples": hits[:5], "detected": bool(hits)}
    return out


def mechanical_range(items, by_group, groups, verbose):
    """Lid groups swept through their full mechanical ranges at every tilt (ignoring the firmware lid
    envelope). Lists the pairs that would then come closer than the moving threshold: these define
    the firmware lid limits."""
    G = grid(quick=True)
    G["up"] = [float(v) for v in np.linspace(-40, 55, 12)]
    G["lo"] = [float(v) for v in np.linspace(-50, -6, 7)]
    res = {}
    for ga, gb in itertools.combinations(groups, 2):
        lid = [g for g in (ga, gb) if g[:4] in ("lidU", "lidL", "horn", "rodU", "rodL")]
        if not lid or "tilt" not in set(dofs(ga)) | set(dofs(gb)):
            continue
        sides = {g.rpartition("_")[2] for g in (ga, gb) if g not in ("fixed", "cradle")}
        if len(sides) > 1:
            continue
        r, _ = _sweep((ga, gb, poses(set(dofs(ga)) | set(dofs(gb)), G, unrestricted=True)))
        res.update(r)
    issues = []
    for (na, nb), r in res.items():
        typ, req, _ = classify(na, nb, False)
        if typ == "moving" and (r["vol"] > 0 or r["min"] < req - 1e-3):
            issues.append({"a": na, "b": nb, "min_mm": round(r["min"], 3), "overlap_mm3": round(r["vol"], 3),
                           "pose": {k: round(v, 2) for k, v in (r["vol_pose"] or r["pose"]).items()}})
    issues.sort(key=lambda x: x["min_mm"])
    if verbose:
        print(f"  mechanical lid range outside the envelope: {len(issues)} pairs below threshold", flush=True)
    return {"note": "Lid angles swept over the full mechanical range at every tilt, ignoring the firmware "
                    "envelope. Pairs listed here are why firmware keeps the lids inside the envelope.",
            "issues": issues[:30], "n_issues": len(issues)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    run(quick=a.quick)
