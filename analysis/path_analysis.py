#!/usr/bin/env python3
"""
Offline path-ordering and double-edge analysis for the AI-Robot-Artist drawing pipeline.

Re-implements, step for step, the vectorisation used in harrymartens/AI-Robot-Artist
(image_utils.py, path_planning_service.py, movement_service.py @ a4ae078) so that the
numbers below describe the system as it was drawn with, and then measures three changes
that leave the drawn marks unchanged or nearly so:

  (A) ordering of segments between strokes (greedy nearest-endpoint + 2-opt)   -> pen-up travel
  (B) merging of doubled Canny edges (3x3 close + skeletonise before tracing)  -> pen-down length
  (C) a kinematic time estimate for the robot's stop-at-every-waypoint execution

Usage:
  python3 path_analysis.py --out <dir> [--images img1.png img2.jpg ...] [--no-builtin]

Without --images it runs on 6 scikit-image sample photographs and 5 synthetic outline
drawings (thick black strokes on white, mimicking marker-style generated images).
With --images it runs on the files given (e.g. your saved GPT-Image-1 outputs).
"""
import argparse, csv, math, os, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree

# ------------------------------------------------------------------ system constants (from repo)
CANVAS_W_MM, CANVAS_H_MM = 180.0, 380.0      # canvas_config.py: x 235..415, y -190..190
BLUR_K, BLUR_SIGMA = (5, 5), 1               # image_utils.apply_gaussian_blur
CANNY_LO, CANNY_HI = 50, 100                 # image_utils.apply_canny_edge_detection
MAX_DIST_SQ = 5                              # path_planning_service.reorder_contour
RDP_EPS = 2.0                                # movement_service._simplify_segment
Z_LIFT_MM = 125.0 - 118.0                    # robot_config: marker raised - lowered
V_MAX, ACC = 100.0, 100.0                    # robot_config: NORMAL speed, mvacc (mm/s, mm/s^2)

# ------------------------------------------------------------------ faithful pipeline
def scale_image(image, target_dimensions=(CANVAS_W_MM, CANVAS_H_MM)):
    tw, th = target_dimensions
    oh, ow = image.shape[:2]
    s = min(tw / ow, th / oh)
    return cv2.resize(image, (int(ow * s), int(oh * s)), interpolation=cv2.INTER_AREA)

def to_line_image(image_bgr):
    g = cv2.cvtColor(scale_image(image_bgr), cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, BLUR_K, BLUR_SIGMA)
    return cv2.Canny(g, CANNY_LO, CANNY_HI)

def extract_contours(edge):
    """DFS components over 8-connected edge pixels, then greedy nearest-neighbour re-ordering
    with chain breaks at distance > sqrt(MAX_DIST_SQ). Identical semantics to the repo."""
    h, w = edge.shape
    visited = np.zeros((h, w), dtype=bool)
    offs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    contours = []
    def dfs(si, sj):
        pts = []; stack = [(si, sj)]
        while stack:
            i, j = stack.pop()
            if visited[i, j]: continue
            visited[i, j] = True
            pts.append((j, i))
            for di, dj in offs:
                ni, nj = i+di, j+dj
                if 0 <= ni < h and 0 <= nj < w and not visited[ni, nj] and edge[ni, nj] != 0:
                    stack.append((ni, nj))
        return pts
    def reorder(points):
        P = np.asarray(points, dtype=np.int64)
        alive = np.ones(len(P), dtype=bool)
        segs = []
        while alive.any():
            cur = int(np.argmax(alive)); alive[cur] = False
            seg = [tuple(P[cur])]
            while alive.any():
                idx = np.flatnonzero(alive)
                d = ((P[idx] - P[cur])**2).sum(1)
                k = int(np.argmin(d))                      # first minimum, as in the repo loop
                if d[k] <= MAX_DIST_SQ:
                    cur = int(idx[k]); alive[cur] = False; seg.append(tuple(P[cur]))
                else:
                    break
            segs.append(seg)
        return segs
    for i in range(h):
        for j in range(w):
            if edge[i, j] != 0 and not visited[i, j]:
                raw = dfs(i, j)
                if len(raw) > 1:
                    for seg in reorder(raw):
                        if len(seg) > 1: contours.append(seg)
    return contours

def simplify(seg, eps=RDP_EPS):
    if len(seg) < 3: return [tuple(map(int, p)) for p in seg]
    pts = np.array(seg, dtype=np.int32).reshape((-1, 1, 2))
    return [tuple(int(v) for v in p[0]) for p in cv2.approxPolyDP(pts, epsilon=eps, closed=False)]

# ------------------------------------------------------------------ metrics
def seg_len(seg):
    a = np.asarray(seg, float)
    return float(np.linalg.norm(np.diff(a, axis=0), axis=1).sum()) if len(a) > 1 else 0.0

def penup_travel(order_segs):
    t = 0.0
    for a, b in zip(order_segs[:-1], order_segs[1:]):
        t += math.dist(a[-1], b[0])
    return t

def move_time(d):
    """Time for one MoveLine of distance d with trapezoidal profile, stop at both ends."""
    if d <= 0: return 0.0
    d_full = V_MAX**2 / ACC                      # distance needed to reach V_MAX and stop
    return 2*math.sqrt(d/ACC) if d < d_full else d/V_MAX + V_MAX/ACC

def exec_time(order_segs, per_cmd_overhead=0.0):
    """Mirror movement_service.follow_vectors: travel (raised, 3D) -> lower -> waypoints -> dup last."""
    t = 0.0; ncmd = 0
    prev_end = None
    for seg in order_segs:
        if prev_end is not None:
            dxy = math.dist(prev_end, seg[0])
            t += move_time(math.hypot(dxy, Z_LIFT_MM)); ncmd += 1   # raise + travel in one linear move
        t += move_time(Z_LIFT_MM); ncmd += 1                         # lower onto first point
        for a, b in zip(seg[:-1], seg[1:]):
            t += move_time(math.dist(a, b)); ncmd += 1
        ncmd += 1                                                    # duplicated final point (zero-length)
        prev_end = seg[-1]
    return t + ncmd * per_cmd_overhead, ncmd

# ------------------------------------------------------------------ (A) segment ordering
def order_segments(segs, two_opt_seconds=20.0, seed=0):
    """Greedy nearest-endpoint ordering with orientation flips, then 2-opt on the open tour."""
    n = len(segs)
    if n < 2: return list(segs)
    S = [np.asarray(s, float) for s in segs]
    ends = np.array([[s[0], s[-1]] for s in S])               # (n,2,2)
    pts = ends.reshape(-1, 2)                                 # endpoint k -> seg k//2, end k%2
    tree = cKDTree(pts)
    used = np.zeros(n, bool)
    cur_seg, cur_end = 0, 1                                   # start with repo's first segment, forward
    order = [(0, False)]; used[0] = True
    pos = ends[0, 1]
    while not used.all():
        k = 2
        while True:
            dd, ii = tree.query(pos, k=min(k, 2*n))
            cand = [(d, i) for d, i in zip(np.atleast_1d(dd), np.atleast_1d(ii)) if not used[i // 2]]
            if cand: break
            k *= 2
        d, i = min(cand)
        sidx, end = i // 2, i % 2
        rev = (end == 1)                                      # nearest is the segment's tail -> reverse it
        order.append((sidx, rev)); used[sidx] = True
        pos = ends[sidx, 0] if rev else ends[sidx, 1]
    # 2-opt on open path with oriented nodes: reversing tour[i..j] also flips each node's orientation
    def node_pts(o):
        s, r = o
        return (ends[s,1], ends[s,0]) if r else (ends[s,0], ends[s,1])   # (entry, exit)
    def gap(a, b):
        return math.dist(node_pts(a)[1], node_pts(b)[0])
    t0 = time.time(); improved = True
    while improved and time.time() - t0 < two_opt_seconds:
        improved = False
        for i in range(0, n - 2):
            if time.time() - t0 > two_opt_seconds: break
            a = order[i]
            for j in range(i + 2, n):
                b, c = order[i+1], order[j]
                d = order[j+1] if j + 1 < n else None
                before = gap(a, b) + (gap(c, d) if d else 0.0)
                cf = (c[0], not c[1]); bf = (b[0], not b[1])
                after = gap(a, cf) + (gap(bf, d) if d else 0.0)
                if after < before - 1e-9:
                    order[i+1:j+1] = [(s, not r) for (s, r) in reversed(order[i+1:j+1])]
                    improved = True
    out = []
    for s, r in order:
        seg = segs[s]
        out.append(list(reversed(seg)) if r else list(seg))
    return out

# ------------------------------------------------------------------ (B) doubled-edge merging
def merge_double_edges(edge):
    from skimage.morphology import skeletonize
    closed = cv2.morphologyEx(edge, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    sk = skeletonize(closed > 0)
    return (sk.astype(np.uint8) * 255)

# ------------------------------------------------------------------ test images
def synthetic_outlines(seed=1):
    """Thick black strokes on white at the generator's 1024x1536 size (marker-style outlines)."""
    rng = np.random.default_rng(seed)
    imgs = []
    W, H = 1024, 1536
    def canvas(): return np.full((H, W, 3), 255, np.uint8)
    # 1 cartoon face
    im = canvas(); cv2.circle(im, (512, 700), 330, 0, 12)
    cv2.circle(im, (400, 620), 40, 0, 12); cv2.circle(im, (624, 620), 40, 0, 12)
    cv2.ellipse(im, (512, 820), (150, 80), 0, 10, 170, 0, 12); imgs.append(("synth_face", im))
    # 2 house + sun
    im = canvas(); cv2.rectangle(im, (250, 800), (780, 1300), 0, 12)
    cv2.polylines(im, [np.array([[220, 800], [515, 520], [810, 800]])], True, 0, 12)
    cv2.rectangle(im, (460, 1050), (570, 1300), 0, 12); cv2.circle(im, (860, 300), 90, 0, 12)
    for a in range(0, 360, 45):
        cv2.line(im, (int(860+120*math.cos(math.radians(a))), int(300+120*math.sin(math.radians(a)))),
                 (int(860+180*math.cos(math.radians(a))), int(300+180*math.sin(math.radians(a)))), 0, 12)
    imgs.append(("synth_house", im))
    # 3 flower
    im = canvas(); c = (512, 640)
    for a in range(0, 360, 60):
        cv2.ellipse(im, (int(c[0]+140*math.cos(math.radians(a))), int(c[1]+140*math.sin(math.radians(a)))), (140, 70), a, 0, 360, 0, 12)
    cv2.circle(im, c, 80, 0, 12); cv2.line(im, (512, 780), (512, 1350), 0, 12)
    cv2.ellipse(im, (430, 1100), (120, 50), -40, 0, 360, 0, 12); imgs.append(("synth_flower", im))
    # 4 random polylines (scribble)
    im = canvas()
    for _ in range(14):
        p = rng.integers([80, 80], [W-80, H-80], size=(6, 2)).astype(np.int32)
        cv2.polylines(im, [p], False, 0, 12)
    imgs.append(("synth_scribble", im))
    # 5 cat-like
    im = canvas(); cv2.ellipse(im, (512, 760), (260, 230), 0, 0, 360, 0, 12)
    cv2.polylines(im, [np.array([[300, 620], [340, 380], [470, 560]])], False, 0, 12)
    cv2.polylines(im, [np.array([[724, 620], [684, 380], [554, 560]])], False, 0, 12)
    cv2.ellipse(im, (420, 720), (40, 60), 0, 0, 360, 0, 12); cv2.ellipse(im, (604, 720), (40, 60), 0, 0, 360, 0, 12)
    cv2.polylines(im, [np.array([[480, 840], [512, 870], [544, 840]])], False, 0, 12)
    for y in (880, 910, 940):
        cv2.line(im, (330, y), (470, y+10), 0, 10); cv2.line(im, (694, y), (554, y+10), 0, 10)
    cv2.ellipse(im, (512, 1150), (210, 160), 0, 0, 360, 0, 12); imgs.append(("synth_cat", im))
    return imgs

def builtin_photos():
    import skimage.data as d
    out = []
    for name in ["astronaut", "chelsea", "coffee", "camera", "horse", "rocket"]:
        im = getattr(d, name)()
        if im.dtype == bool: im = (~im).astype(np.uint8) * 255      # horse: True = foreground -> black on white
        if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        elif im.shape[2] == 4: im = cv2.cvtColor(im, cv2.COLOR_RGBA2BGR)
        else: im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
        out.append(("photo_" + name, im))
    return out

# ------------------------------------------------------------------ main
def analyse(name, img, outdir, two_opt_seconds):
    edge = to_line_image(img)
    rows = {}
    for variant, E in (("baseline", edge), ("merged", merge_double_edges(edge))):
        segs = [simplify(s) for s in extract_contours(E)]
        segs = [s for s in segs if len(s) > 1]
        pendown = sum(seg_len(s) for s in segs)
        npts = sum(len(s) for s in segs)
        up0 = penup_travel(segs); t0, n0 = exec_time(segs)
        ordered = order_segments(segs, two_opt_seconds)
        up1 = penup_travel(ordered); t1, n1 = exec_time(ordered)
        assert abs(sum(seg_len(s) for s in ordered) - pendown) < 1e-6
        rows[variant] = dict(segments=len(segs), waypoints=npts, pendown_mm=pendown,
                             penup_raster_mm=up0, penup_ordered_mm=up1,
                             t_raster_s=t0, t_ordered_s=t1, commands=n0)
        if variant == "baseline":
            draw_order_figure(ordered, segs, E.shape, os.path.join(outdir, f"{name}_order.png"))
    b, m = rows["baseline"], rows["merged"]
    return dict(image=name, px=f"{edge.shape[1]}x{edge.shape[0]}",
                segments=b["segments"], waypoints=b["waypoints"], commands=b["commands"],
                pendown_mm=round(b["pendown_mm"], 1),
                penup_raster_mm=round(b["penup_raster_mm"], 1), penup_ordered_mm=round(b["penup_ordered_mm"], 1),
                penup_reduction_pct=round(100*(1 - b["penup_ordered_mm"]/max(b["penup_raster_mm"], 1e-9)), 1),
                t_raster_min=round(b["t_raster_s"]/60, 2), t_ordered_min=round(b["t_ordered_s"]/60, 2),
                time_reduction_pct=round(100*(1 - b["t_ordered_s"]/b["t_raster_s"]), 1),
                merged_segments=m["segments"], merged_pendown_mm=round(m["pendown_mm"], 1),
                pendown_reduction_pct=round(100*(1 - m["pendown_mm"]/max(b["pendown_mm"], 1e-9)), 1),
                t_merged_ordered_min=round(m["t_ordered_s"]/60, 2),
                total_time_reduction_pct=round(100*(1 - m["t_ordered_s"]/b["t_raster_s"]), 1))

def draw_order_figure(ordered, raster, shape, path):
    """Two panels: pen-up moves (red) under raster order vs optimised order."""
    h, w = shape; sc = 3
    def panel(segs):
        im = np.full((h*sc, w*sc, 3), 255, np.uint8)
        for a, b in zip(segs[:-1], segs[1:]):
            cv2.line(im, (int(a[-1][0]*sc), int(a[-1][1]*sc)), (int(b[0][0]*sc), int(b[0][1]*sc)), (60, 60, 230), 1, cv2.LINE_AA)
        for s in segs:
            cv2.polylines(im, [np.array(s, np.int32)*sc], False, (30, 30, 30), 2, cv2.LINE_AA)
        return im
    gap = np.full((h*sc, 12, 3), 255, np.uint8)
    cv2.imwrite(path, np.hstack([panel(raster), gap, panel(ordered)]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--no-builtin", action="store_true")
    ap.add_argument("--two-opt-seconds", type=float, default=20.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    items = []
    if not a.no_builtin:
        items += synthetic_outlines() + builtin_photos()
    for p in a.images:
        im = cv2.imread(p)
        if im is None: print("skip (unreadable):", p); continue
        items.append((os.path.splitext(os.path.basename(p))[0], im))
    results = []
    for name, im in items:
        t = time.time()
        r = analyse(name, im, a.out, a.two_opt_seconds)
        results.append(r)
        print(f"{name:18s} segs={r['segments']:5d} wp={r['waypoints']:6d} pen-down={r['pendown_mm']:8.0f}mm "
              f"pen-up {r['penup_raster_mm']:8.0f}->{r['penup_ordered_mm']:7.0f}mm ({r['penup_reduction_pct']:5.1f}%) "
              f"t {r['t_raster_min']:6.2f}->{r['t_ordered_min']:6.2f}min ({r['time_reduction_pct']:4.1f}%) "
              f"merged pen-down -{r['pendown_reduction_pct']:4.1f}%  total -{r['total_time_reduction_pct']:4.1f}%  [{time.time()-t:.0f}s]")
    with open(os.path.join(a.out, "results.csv"), "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=list(results[0].keys())); wtr.writeheader(); wtr.writerows(results)
    # summary
    def stats(key):
        v = np.array([r[key] for r in results], float)
        return v.mean(), v.std(ddof=1) if len(v) > 1 else 0.0, v.min(), v.max()
    with open(os.path.join(a.out, "summary.txt"), "w") as f:
        f.write(f"n = {len(results)} images\n")
        for key in ("segments", "waypoints", "pendown_mm", "penup_raster_mm", "penup_ordered_mm",
                    "penup_reduction_pct", "t_raster_min", "t_ordered_min", "time_reduction_pct",
                    "pendown_reduction_pct", "total_time_reduction_pct"):
            m, s, lo, hi = stats(key)
            f.write(f"{key:26s} mean {m:9.1f}  sd {s:8.1f}  min {lo:9.1f}  max {hi:9.1f}\n")
    print(open(os.path.join(a.out, "summary.txt")).read())

if __name__ == "__main__":
    main()
