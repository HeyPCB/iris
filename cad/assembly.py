"""Iris assembly registry: every part, its motion group, colour, BOM data and the solids the motion
check uses. Parts are built in the head frame H at the rest pose; cad/kinematics.py moves the groups.

Build results are cached as BREP + mesh files in cad/out/.cache (ignored by git), keyed on a hash of
the cad/ sources, so check.py and render.py do not rebuild unchanged geometry.
"""
import hashlib
import json
import os
from dataclasses import dataclass, field

import cadquery as cq
import numpy as np

from . import kinematics as K
from . import params as P
from .geom import fuse_all
from .parts import boards, cradle, eye, face, frame, lids, linkage, purchased

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CACHE = os.path.join(OUT, ".cache")

COL = {
    "frame": (0.78, 0.80, 0.84), "cradle": (0.89, 0.50, 0.35), "face": (0.94, 0.91, 0.86),
    "sclera": (0.97, 0.97, 0.95), "cornea": (0.85, 0.93, 1.0), "iris": (0.30, 0.52, 0.66),
    "carrier": (0.12, 0.12, 0.13), "lid": (0.90, 0.72, 0.62), "brow": (0.24, 0.18, 0.16),
    "servo": (0.17, 0.18, 0.26), "spline": (0.75, 0.75, 0.72), "steel": (0.72, 0.73, 0.75),
    "link": (0.10, 0.10, 0.10), "horn": (0.95, 0.80, 0.45), "pcb": (0.10, 0.45, 0.25),
    "pcb_env": (0.30, 0.70, 0.45), "camera": (0.20, 0.20, 0.22), "fpc": (0.85, 0.55, 0.15),
    "speaker": (0.25, 0.25, 0.25), "magnet": (0.60, 0.60, 0.65),
}


@dataclass
class Part:
    name: str
    group: str
    kind: str                     # printed | purchased | board
    color: tuple
    pnum: str = ""                # spec 7.1 number for printed parts
    label: str = ""
    material: str = ""
    qty_note: str = ""
    export_as: str = ""           # file stem for printed parts (shared by identical L/R parts)
    check: bool = True            # include in the motion check
    alpha: float = 1.0
    shape: object = None          # cq.Shape in H at rest
    subs: dict = field(default_factory=dict)   # name -> cq.Shape, used instead of `shape` by the check


GEOMETRY_SOURCES = ("params.py", "geom.py", "kinematics.py", "assembly.py")


def _src_hash():
    """Hash of the sources that define geometry (not of the check, render or export scripts)."""
    h = hashlib.sha1()
    files = [os.path.join(HERE, f) for f in GEOMETRY_SOURCES]
    pdir = os.path.join(HERE, "parts")
    files += [os.path.join(pdir, f) for f in sorted(os.listdir(pdir)) if f.endswith(".py")]
    for fn in files:
        with open(fn, "rb") as fh:
            h.update(os.path.basename(fn).encode() + fh.read())
    return h.hexdigest()[:16]


def _defs():
    """Ordered list of (Part template, builder). Builders return a cq.Shape or a dict of sub-shapes."""
    D = []

    def add(name, group, kind, color, build, **kw):
        D.append((Part(name=name, group=group, kind=kind, color=COL[color] if isinstance(color, str) else color, **kw), build))

    # ---- fixed frame
    add("column", "fixed", "printed", "frame", frame.column, pnum="P10", label="Centre column", material="PETG")
    add("nose_block", "fixed", "printed", "frame", frame.nose_block, pnum="P9", label="Nose-bridge block", material="PETG")
    for s in P.SIDES:
        add(f"side_plate_{s}", "fixed", "printed", "frame", (lambda s=s: frame.side_plate(s)), pnum="P15a",
            label=f"Skull side plate {s}", material="PETG")
    add("top_bridge", "fixed", "printed", "frame", frame.top_bridge, pnum="P15b", label="Skull top bridge + brow brackets", material="PETG")
    add("base_plate", "fixed", "printed", "frame", frame.base_plate, pnum="P16a", label="Base plate", material="PETG")
    add("back_cover", "fixed", "printed", "face", face.back_cover, pnum="P16b", label="Back cover", material="PETG", alpha=0.25)
    add("face_shell", "fixed", "printed", "face", face.face_shell, pnum="P14", label="Face shell (stylised, v1)", material="PLA/PETG, painted")
    for name in ("tilt", "lidU_R", "lidU_L", "lidL_R", "lidL_L", "brow_R", "brow_L"):
        add(f"servo_{name}", "fixed", "purchased", "servo", (lambda n=name: _servo(n)), label=f"SCS0009 envelope ({name}, ID {P.SERVO_IDS[name]})")
    add("temple_pin_R", "fixed", "purchased", "steel", lambda: purchased.pin_y(1.5, -84.0, -71.6), label="Dowel Dia 3 x 12 (right temple)")
    add("temple_pin_L", "fixed", "purchased", "steel", lambda: purchased.pin_y(1.5, 71.6, 84.0), label="Dowel Dia 3 x 12 (left loose bushing)")
    add("nasal_pin_R", "fixed", "purchased", "steel", lambda: linkage.nasal_pin("R"), label="Dowel Dia 3 x 8 (right nasal lid pin)")
    add("speaker", "fixed", "purchased", "speaker", purchased.speaker, label="Speaker 28 mm envelope")
    for b in ("B2", "B4"):
        add(b, "fixed", "board", "pcb_env", (lambda b=b: _board(b)), label=f"{b} envelope (spec 4)")
    add("brow_cable_frame", "fixed", "harness", "fpc", linkage.brow_cable_frame, label="BROW cable route, frame side (keep-out)")

    # ---- cradle
    add("spine", "cradle", "printed", "cradle", cradle.spine, pnum="P5", label="Cradle spine + rear plate", material="PETG")
    for s in P.SIDES:
        add(f"fork_{s}", "cradle", "printed", "cradle", (lambda s=s: cradle.fork(s)), pnum="P6", label="Fork", material="PETG or nylon", export_as="fork")
        add(f"temple_arm_{s}", "cradle", "printed", "cradle", (lambda s=s: cradle.temple_arm(s)), pnum="P7", label=f"Temple arm {s}", material="PETG")
        add(f"servo_pan_{s}", "cradle", "purchased", "servo", (lambda s=s: _servo("pan_" + s)), label=f"SCS0009 envelope (pan_{s}, ID {P.SERVO_IDS['pan_' + s]})")
        add(f"pole_pins_{s}", "cradle", "purchased", "steel", (lambda s=s: eye.pole_pins(s)), label="Dowel Dia 2 x 8 x2 (pole pins)")
        add(f"temporal_pin_{s}", "cradle", "purchased", "steel", (lambda s=s: linkage.temporal_pin(s)), label="Dowel Dia 3 x 16 (temporal lid pin)")
    add("tilt_tongue", "cradle", "printed", "cradle", linkage.tilt_tongue, pnum="P8", label="Tilt drive tongue", material="PETG")
    add("tongue_pin", "cradle", "purchased", "steel", linkage.tongue_drive_pin, label="Dowel Dia 3 x 6 (tongue drive pin)")
    add("nasal_pin_L", "cradle", "purchased", "steel", lambda: linkage.nasal_pin("L"), label="Dowel Dia 3 x 7 (left nasal lid pin)")
    add("bearing_R", "cradle", "purchased", "steel", lambda: purchased.mr63(-1.0), label="MR63ZZ")
    add("B1", "cradle", "board", "pcb_env", lambda: _board("B1"), label="B1 envelope (spec 4.1)")
    add("brow_cable_cradle", "cradle", "harness", "fpc", linkage.brow_cable_cradle, label="BROW cable route, cradle side (keep-out)")

    # ---- eyes
    for s in P.SIDES:
        g = "eye_" + s
        add(f"sclera_{s}", g, "printed", "sclera", (lambda s=s: _sclera(s)), pnum="P1", label="Sclera shell", material="SLA white or PLA 0.1 mm", export_as="sclera")
        add(f"cornea_{s}", g, "printed", "cornea", (lambda s=s: eye.cornea(s)), pnum="P2", label="Cornea", material="SLA clear", export_as="cornea", alpha=0.35)
        add(f"iris_{s}", g, "printed", "iris", (lambda s=s: eye.iris_disc(s)), pnum="P3", label="Iris disc + pupil sleeve", material="SLA translucent", export_as="iris_disc")
        add(f"carrier_{s}", g, "printed", "carrier", (lambda s=s: eye.carrier(s)), pnum="P4",
            label="Camera carrier (R)" if s == "R" else "Dummy carrier (L)", material="PLA/PETG black")
        add(f"B3_{s}", g, "board", "pcb_env", (lambda s=s: _board("B3", s)), label="B3 envelope (spec 4.4)")
        add(f"keel_stud_{s}", g, "purchased", "steel", (lambda s=s: eye.keel_stud(s)), label="M2 ball stud")
        if s == "R":
            add("camera", g, "purchased", "camera", eye.camera, label="OV2640 module envelope")
        # pan linkage
        add(f"pan_crank_{s}", "crank_" + s, "printed", "horn", (lambda s=s: linkage.pan_crank(s)), pnum="P12", label="Pan crank", material="PETG", export_as="pan_crank")
        add(f"crank_stud_{s}", "crank_" + s, "purchased", "steel", (lambda s=s: linkage.crank_stud(s)), label="M2 ball stud")
        add(f"pan_coupler_{s}", "pcoup_" + s, "purchased", "link", (lambda s=s: linkage.pan_coupler(s)), label="M2 ball links + rod (26 mm)")
        # lids
        for k in ("U", "L"):
            add(f"lid{k}_{s}", f"lid{k}_{s}", "printed", "lid", (lambda k=k, s=s: lids.lid(k, s)), pnum="P11",
                label=("Upper" if k == "U" else "Lower") + f" lid {s}", material="SLA or PLA, skin paint")
            add(f"lid{k}_stud_{s}", f"lid{k}_{s}", "purchased", "steel", (lambda k=k, s=s: lids.lid_stud(k, s)), label="M2 ball stud")
            add(f"horn{k}_{s}", f"horn{k}_{s}", "printed", "horn", (lambda k=k, s=s: linkage.lid_horn(k, s)), pnum="P17",
                label="Lid servo horn", material="PETG", export_as="lid_horn")
            add(f"horn{k}_stud_{s}", f"horn{k}_{s}", "purchased", "steel", (lambda k=k, s=s: linkage.horn_stud(k, s)), label="M2 ball stud")
            add(f"rod{k}_{s}", f"rod{k}_{s}", "purchased", "link", (lambda k=k, s=s: lids.lid_pushrod(k, s)), label="M2 ball links + rod")
        # brows
        add(f"brow_{s}", "brow_" + s, "printed", "brow", (lambda s=s: face.brow(s)), pnum="P13b", label=f"Brow {s}", material="PLA + flock")
        add(f"brow_hub_{s}", "brow_" + s, "printed", "horn", (lambda s=s: face.brow_hub(s)), pnum="P13a", label="Brow hub", material="PETG", export_as="brow_hub")
    return D


REAL_BOARDS = {}       # board -> STEP path; set by use_real_boards()
REAL_INFO = {}


def use_real_boards(paths):
    """Replace the spec envelopes by the real board STEP files (dict board -> path)."""
    REAL_BOARDS.clear()
    REAL_BOARDS.update(paths or {})


def resolve_boards(arg=None):
    """Board STEP files from --boards DIR, the IRIS_BOARDS environment variable, or board repositories
    cloned next to this one."""
    dirs = [arg, os.environ.get("IRIS_BOARDS"), os.path.dirname(os.path.dirname(HERE))]
    return boards.find_real(dirs) if any(dirs) else {}


def _board(b, side=None):
    if b in REAL_BOARDS:
        parts, info = boards.load_real(b, REAL_BOARDS[b])
        REAL_INFO[b] = info
        return boards.place_real(b, parts, side)
    if b == "B3":
        return eye.b3_envelope(side)
    return boards.envelope(b)


def _servo(name):
    sv = purchased.scs0009(name)
    return {"body": sv["body"], "spline": sv["spline"]}


def _sclera(side):
    shell, bos = eye.sclera_pieces()
    t = cq.Vector(0, P.Y_EYE[side], 0)
    return {"shell": shell.translate(t), "bosses": bos.translate(t)}


def _compound(d):
    if isinstance(d, dict):
        return cq.Compound.makeCompound([s for v in d.values() for s in (v.Solids() or [v])])
    return d


def build(use_cache=True, verbose=False):
    """Return an ordered dict name -> Part with shapes (and sub-shapes) filled in."""
    os.makedirs(CACHE, exist_ok=True)
    key = _src_hash() + "".join(f"|{b}:{os.path.getsize(f)}:{int(os.path.getmtime(f))}" for b, f in sorted(REAL_BOARDS.items()))
    stamp = os.path.join(CACHE, "stamp.json")
    cached = use_cache and os.path.exists(stamp) and json.load(open(stamp)).get("key") == key
    parts = {}
    for tpl, fn in _defs():
        p = tpl
        brep = os.path.join(CACHE, p.name)
        if cached and os.path.exists(brep + ".json"):
            meta = json.load(open(brep + ".json"))
            for sub in meta["subs"]:
                p.subs[sub] = cq.Shape.importBrep(f"{brep}.{sub}.brep")
            p.shape = cq.Shape.importBrep(brep + ".brep")
        else:
            if verbose:
                print("  build", p.name, flush=True)
            r = fn()
            if isinstance(r, dict):
                p.subs = dict(r)
                p.shape = fuse_all(list(r.values())) if p.kind == "printed" else _compound(r)
            else:
                p.shape = r
            p.shape.exportBrep(brep + ".brep")
            for sub, s in p.subs.items():
                s.exportBrep(f"{brep}.{sub}.brep")
            json.dump({"subs": list(p.subs)}, open(brep + ".json", "w"))
        if p.kind == "board" and p.name[:2] in REAL_BOARDS:
            p.label = f"{p.name[:2]} as built ({boards.REAL[p.name[:2]]['repo']})"
            p.color = COL["pcb"]
        parts[p.name] = p
    if not cached:
        json.dump({"key": key}, open(stamp, "w"))
    return parts


# ------------------------------------------------------------------------------------- meshes
def mesh_of(shape, tol=0.05, ang=0.2):
    """Tessellate a cq shape into (vertices Nx3, faces Mx3) with merged vertices."""
    import trimesh
    v, f = shape.tessellate(tol, ang)
    V = np.array([(p.x, p.y, p.z) for p in v], float)
    F = np.array(f, int)
    m = trimesh.Trimesh(V, F, process=True)
    m.merge_vertices()
    return m


def meshes(parts, tol=0.05, ang=0.2, only=None):
    """Cached meshes per part (and per sub-solid): dict name -> trimesh, with 'name/sub' keys for
    sub-solids."""
    import trimesh
    key = json.load(open(os.path.join(CACHE, "stamp.json")))["key"]
    out = {}
    for n, p in parts.items():
        if only and n not in only:
            continue
        items = {f"{n}/{k}": s for k, s in p.subs.items()} if p.subs else {n: p.shape}
        for mn, s in items.items():
            fn = os.path.join(CACHE, f"mesh_{mn.replace('/', '__')}_{tol}_{ang}.npz")
            if os.path.exists(fn) and np.load(fn)["key"] == key:
                d = np.load(fn)
                out[mn] = trimesh.Trimesh(d["v"], d["f"], process=False)
            else:
                m = mesh_of(s, tol, ang)
                np.savez(fn, v=m.vertices, f=m.faces, key=key)
                out[mn] = m
    return out


def posed_matrix(part, pose):
    return K.group_transform(part.group, pose)
