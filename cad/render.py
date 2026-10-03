"""Headless renders (VTK offscreen) to media/.

  python -m cad.render            # all images and the GIF
  python -m cad.render --only hero

Images: hero.png, mechanism.png, exploded.png, gaze_<pose>.png, gaze_poses.png, gaze_blink.gif
"""
import argparse
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import assembly as A
from . import kinematics as K
from .viz import Scene

MEDIA = os.path.join(os.path.dirname(A.HERE), "media")

PUPIL = (0.05, 0.05, 0.06)


def _load():
    parts = A.build()
    ms = A.meshes(parts, tol=0.05, ang=0.2)
    return parts, ms


def _scene_add(sc, parts, ms, pose, hide=(), alpha=None, explode=None, color=None):
    for mn, m in ms.items():
        pn = mn.split("/")[0]
        p = parts[pn]
        if pn in hide or p.group in hide:
            continue
        mm = m.copy()
        mm.apply_transform(K.group_transform(p.group, pose))
        if explode:
            mm.apply_translation(explode(pn, p))
        a = p.alpha if alpha is None else alpha.get(pn, p.alpha)
        c = p.color if color is None else color.get(pn, p.color)
        sc.add(mm, c, a)


def gaze_pose(name):
    """Named gaze poses used by the renders (degrees)."""
    t, pr, pl, du, dl = {
        "rest": (0, 0, 0, 0, 0), "left": (0, 28, 28, 0, 0), "right": (0, -28, -28, 0, 0),
        "up": (22, 0, 0, 4, 0), "down": (-25, 0, 0, 0, 0), "converged": (0, 14.6, -14.6, 0, 0),
        "blink": (0, 0, 0, -37, 8),
    }[name]
    u, l = K.follow(t, du, dl)
    return {"tilt": t, "pan_R": pr, "pan_L": pl, "up_R": u, "up_L": u, "lo_R": l, "lo_L": l}


def _half_face(ms, keep_sign=-1.0):
    """Face shell cut at Y = 0 (keeps the robot-right half for keep_sign -1)."""
    import manifold3d as m3
    import trimesh
    m = ms["face_shell"]
    man = m3.Manifold(m3.Mesh(vert_properties=np.ascontiguousarray(m.vertices, dtype=np.float32),
                              tri_verts=np.ascontiguousarray(m.faces, dtype=np.uint32)))
    out = man.trim_by_plane((0.0, keep_sign, 0.0), 0.0).to_mesh()
    return trimesh.Trimesh(np.asarray(out.vert_properties)[:, :3], np.asarray(out.tri_verts), process=False)


def _frame(sc, direction, focal, zoom=1.0, up=(0, 0, 1)):
    sc.camera(focal, direction, up=up, dist=600, view_angle=28)
    sc.ren.ResetCamera()
    cam = sc.ren.GetActiveCamera()
    cam.SetFocalPoint(*focal)
    cam.Zoom(zoom)
    sc.ren.ResetCameraClippingRange()


def hero(parts, ms, path):
    """Two panels from the same viewpoint: the finished head, and the mechanism with the face shell,
    back cover and the near skull plate removed."""
    pose = {"tilt": 4.0, "pan_R": 10.0, "pan_L": 16.0}
    u, l = K.follow(4.0)
    pose.update({"up_R": u, "up_L": u, "lo_R": l, "lo_L": l, "brow_R": 5.0, "brow_L": 5.0})
    view, focal = (1.0, -0.62, 0.30), (-40, 0, 2)
    panels = []
    for full in (True, False):
        sc = Scene(size=(1300, 1150), bg=(0.98, 0.98, 0.99), bg2=(0.84, 0.87, 0.91))
        if full:
            _scene_add(sc, parts, ms, pose, alpha={"back_cover": 1.0})
        else:
            _scene_add(sc, parts, ms, pose, hide=("back_cover", "face_shell", "side_plate_R", "B4_env", "top_bridge"))
        _frame(sc, view, focal, zoom=1.3)
        panels.append(sc.image())
    img = np.concatenate(panels, axis=1)
    Image.fromarray(img).save(path)


def mechanism(parts, ms, path):
    sc = Scene(size=(2000, 1400), bg=(0.98, 0.98, 0.99), bg2=(0.84, 0.87, 0.91))
    pose = gaze_pose("rest")
    _scene_add(sc, parts, ms, pose, hide=("back_cover", "face_shell", "top_bridge", "side_plate_L", "B4_env"))
    _frame(sc, (0.8, 1.0, 0.6), (-30, 0, -5), zoom=1.2)
    sc.save(path)


def _explode_vec(pn, p):
    g = p.group
    s = -1.0 if (pn.endswith("_R") or g.endswith("_R") or "_R/" in pn) else 1.0
    fixed = {"face_shell": (195, 0, 0), "B4_env": (112, 0, 18), "back_cover": (-150, 0, 0),
             "top_bridge": (0, 0, 85), "base_plate": (0, 0, -75), "B2_env": (-15, 0, -48), "speaker": (35, 0, -60),
             "nose_block": (0, -18, 0), "temple_pin_R": (-20, -110, 0), "temple_pin_L": (-20, 110, 0),
             "nasal_pin_R": (6, -26, 0)}
    if pn in fixed:
        return np.array(fixed[pn], float)
    if pn.startswith("side_plate"):
        return np.array([-20.0, s * 110.0, 0])
    if pn.startswith("servo_brow"):
        return np.array([0.0, 0, 50.0])
    if g == "fixed":
        return np.zeros(3)
    if g == "cradle":
        if pn.startswith("B1"):
            return np.array([-95.0, 0, 0])
        if pn.startswith("spine"):
            return np.array([-60.0, 0, 0])
        if pn.startswith(("fork", "pole_pins")):
            return np.array([-28.0, 0, 0])
        if pn.startswith(("temple_arm", "servo_pan", "temporal_pin", "bearing")):
            return np.array([-35.0, s * 50.0, -8.0])
        return np.array([-22.0, 12.0, 0])            # tongue, its pins
    if g.startswith(("crank", "pcoup")):
        return np.array([-35.0, s * 50.0, 2.0])
    if g.startswith("eye"):
        x = {"cornea": 82, "iris": 72, "B3": 63, "carrier": 52, "camera": 52}.get(pn.split("_")[0], 40)
        return np.array([float(x), s * 6.0, 0])
    if g.startswith("lidU"):
        return np.array([100.0, s * 6.0, 22.0])
    if g.startswith("lidL"):
        return np.array([100.0, s * 6.0, -22.0])
    if g.startswith("rod"):
        return np.array([30.0, s * 4.0, 0])
    if g.startswith("horn"):
        return np.array([14.0, s * 4.0, 0])
    if g.startswith("brow"):
        return np.array([135.0, 0, 18.0])
    return np.zeros(3)


def exploded(parts, ms, path):
    sc = Scene(size=(2400, 1350), bg=(0.98, 0.98, 0.99), bg2=(0.86, 0.88, 0.92))
    _scene_add(sc, parts, ms, gaze_pose("rest"), explode=_explode_vec, alpha={"face_shell": 0.5, "back_cover": 0.4})
    _frame(sc, (0.55, -1.0, 0.45), (0, 0, 0), zoom=1.75)
    sc.save(path)


def gaze_scene(parts, ms, name, size=(1200, 520)):
    sc = Scene(size=size, bg=(0.96, 0.96, 0.97))
    pose = gaze_pose(name) if isinstance(name, str) else name
    _scene_add(sc, parts, ms, pose, hide=("back_cover",))
    sc.camera((0, 0, 4), (1, 0, 0.0), dist=420, parallel=37)
    return sc


def gaze_set(parts, ms):
    names = ["left", "right", "up", "down", "converged", "blink"]
    tiles = []
    for n in names:
        sc = gaze_scene(parts, ms, n)
        img = sc.image()
        Image.fromarray(img).save(os.path.join(MEDIA, f"gaze_{n}.png"))
        tiles.append((n, img))
    h, w = tiles[0][1].shape[:2]
    sheet = Image.new("RGB", (2 * w, 3 * h + 3 * 34), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
    except Exception:
        font = ImageFont.load_default()
    for i, (n, img) in enumerate(tiles):
        x, y = (i % 2) * w, (i // 2) * (h + 34)
        sheet.paste(Image.fromarray(img), (x, y + 34))
        dr.text((x + 16, y + 4), n, fill=(40, 40, 40), font=font)
    sheet.save(os.path.join(MEDIA, "gaze_poses.png"))


def _ease(a):
    return 0.5 - 0.5 * math.cos(math.pi * a)


def gif(parts, ms, path, size=(720, 312)):
    """Gaze-and-blink sequence: saccades left/right/up/down, a vergence, two blinks."""
    keys = [("rest", 4), ("left", 6), ("left", 6), ("right", 8), ("right", 5), ("up", 6), ("up", 4), ("down", 7),
            ("down", 4), ("rest", 5), ("blink", 2), ("rest", 5), ("converged", 6), ("converged", 6), ("rest", 5),
            ("blink", 2), ("rest", 6)]
    frames = []
    sc = Scene(size=size, bg=(0.96, 0.96, 0.97))
    prev = gaze_pose("rest")
    for name, n in keys:
        tgt = gaze_pose(name)
        for i in range(n):
            a = _ease((i + 1) / n)
            q = {k: prev[k] + (tgt[k] - prev[k]) * a for k in tgt}
            sc.clear()
            _scene_add(sc, parts, ms, q, hide=("back_cover",))
            sc.camera((0, 0, 4), (1, 0, 0.0), dist=420, parallel=37)
            frames.append(Image.fromarray(sc.image()).quantize(colors=128, method=Image.Quantize.MEDIANCUT))
        prev = tgt
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=70, loop=0, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    os.makedirs(MEDIA, exist_ok=True)
    parts, ms = _load()
    todo = a.only.split(",") if a.only else ["hero", "mechanism", "exploded", "gaze", "gif"]
    if "hero" in todo:
        hero(parts, ms, os.path.join(MEDIA, "hero.png"))
    if "mechanism" in todo:
        mechanism(parts, ms, os.path.join(MEDIA, "mechanism.png"))
    if "exploded" in todo:
        exploded(parts, ms, os.path.join(MEDIA, "exploded.png"))
    if "gaze" in todo:
        gaze_set(parts, ms)
    if "gif" in todo:
        gif(parts, ms, os.path.join(MEDIA, "gaze_blink.gif"))
    print("renders written to", MEDIA)


if __name__ == "__main__":
    main()
