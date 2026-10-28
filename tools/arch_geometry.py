"""Gateway Arch logo geometry.

Centroid curve is the real one (NPS): y = 693.8597 - 68.7672 cosh(0.0100333 x), ft,
|x| <= 299.2239. The leg tapers from 54 ft at the base to 17 ft at the top; the
silhouette half-width is taken as half the triangle side.

Writes: arch_path.txt (SVG path in a 100x100 logo box) and, if given an output
dir, PNG icons for one colour set.
"""
import math
import sys
import json

A, B, C, L = 693.8597, 68.7672, 0.0100333, 299.2239
TOP = A - B


def centroid(x):
    return A - B * math.cosh(C * x)


def slope(x):
    return -B * C * math.sinh(C * x)


def outline(n=70, overshoot=20):
    outer, inner = [], []
    for i in range(n + 1):
        x = -L - overshoot + (2 * (L + overshoot)) * i / n
        y = centroid(x)
        m = slope(x)
        nx, ny = -m, 1.0
        k = math.hypot(nx, ny)
        nx, ny = nx / k, ny / k
        w = 1.8 * (8.5 + (27 - 8.5) * (1 - max(0.0, y) / TOP))
        outer.append((x + w * nx, y + w * ny))
        inner.append((x - w * nx, y - w * ny))
    return outer + inner[::-1]


# Map feet -> logo box: arch spans x 16..84, ground at y 70, top near y 12.
GROUND, LEFT, RIGHT = 72.0, 22.0, 78.0
S = (RIGHT - LEFT) / (2 * (L + 1.8 * 27))


def to_box(p):
    x, y = p
    return (50 + x * S, GROUND - y * S)


pts = [to_box(p) for p in outline()]
path = 'M' + ' L'.join(f'{x:.2f} {y:.2f}' for x, y in pts) + ' Z'
open(sys.argv[1] + '/arch_path.txt', 'w').write(path)
open(sys.argv[1] + '/arch_pts.json', 'w').write(json.dumps(pts))
print('top y', min(y for _, y in pts), 'points', len(pts))
