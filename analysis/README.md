# Offline drawing-path analysis

Supporting material for Section 5.3 of

> Martens, Meng, Sandoval, Green, Akmal, Cruz. *Human-Robot Creative Interactions 2.0:
> A Technical and Research Through Design Report on a Robotic Drawing System.* ACRA 2026.

`path_analysis.py` re-implements, step for step, the vectorisation used by this repository
(`image_utils.py`, `path_planning_service.py`, `movement_service.py` at commit `a4ae078`):
resize to the 180 x 380 mm canvas, 5x5 Gaussian blur (sigma 1), Canny 50/100, depth-first
contour tracing, greedy nearest-neighbour ordering with a sqrt(5)-pixel chain break, and
Ramer-Douglas-Peucker simplification at epsilon = 2 px. It then measures, per image:

- **pen-down length** of the drawn polylines;
- **pen-up travel** between segments in the order the system executes them (raster order of
  each component's first pixel) versus a greedy nearest-endpoint order improved by 2-opt;
- **pen-down length after doubled-edge merging** (3x3 morphological closing + thinning before
  tracing), which collapses the two Canny edges of a thick stroke into one centre line;
- an **execution-time estimate** from the arm's configuration (100 mm/s, 100 mm/s^2, 7 mm lift,
  stop at every waypoint, no blending radius), which is why a 2 mm move costs ~0.28 s
  regardless of the speed setting.

## Running it

```bash
pip install numpy opencv-python scipy scikit-image
python3 path_analysis.py --out results                       # 5 synthetic outlines + 6 scikit-image photos
python3 path_analysis.py --out results --no-builtin --images img1.png img2.png   # your own images
```

Outputs: `results/results.csv` (one row per image), `results/summary.txt` (mean / SD / min / max),
and `<image>_order.png` (pen-up moves in red: raster order on the left, optimised order on the right).

## Results reported in the paper (n = 11 images)

| Measure | Mean ± SD | Range |
|---|---|---|
| Pen-up travel reduction (ordering) | 63 ± 26 % | 0–85 % |
| Estimated time reduction (ordering only) | 12 ± 8 % | 0–24 % |
| Pen-down reduction (doubled-edge merging) | 28 ± 17 % | 7–51 % |
| Estimated time reduction (merging + ordering) | 33 ± 17 % | −14–49 % |

The one negative case (`photo_horse`, +14 % time) is thinning fragmenting a single thin
silhouette contour; spur pruning before tracing is the obvious fix and is not yet implemented.
Neither optimisation is wired into the live pipeline yet.
