"""PNG app icons from the same arch outline as the in-app SVG logo.

    python arch_icons.py <arch_pts.json> <out_dir> <theme>
"""
import json
import sys
from PIL import Image, ImageDraw

PALETTES = {   # tile, arch_hi, arch_lo, road, road_line, road_edge
    'chrome': ('#0a0b0e', '#ffffff', '#7d8796', '#1c1f26', '#d7dde6', '#2a2e37'),
    'steel':  ('#0f1e3d', '#ffffff', '#8b97a6', '#1e2f55', '#e2e8f0', '#2c3f6b'),
    'neon':   ('#0b0f24', '#ffffff', '#ff3ea5', '#1b2349', '#22d3ee', '#2a3466'),
    'violet': ('#0f0a1a', '#ffffff', '#9d7bd8', '#21183a', '#ff6fb5', '#33264f'),
}
pts = json.load(open(sys.argv[1]))
out, theme = sys.argv[2], sys.argv[3]
tile, hi, lo, road, line, edge = PALETTES[theme]
SS = 4


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def draw(size, maskable):
    S = size * SS
    # maskable icons keep the art inside the central 80% safe zone
    k = S / 100 * (0.78 if maskable else 1.0)
    off = (S - 100 * k) / 2
    T = lambda x, y: (off + x * k, off + y * k)
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if maskable:
        d.rectangle([0, 0, S, S], fill=tile)
    else:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=tile)
    # road: below the horizon, out to the bottom edge of the canvas
    bottom = S if maskable else off + 100 * k
    d.polygon([T(50, 72), (off + 92 * k, bottom), (off + 8 * k, bottom)], fill=road)
    y = 74
    while y < 100 + (off / k if maskable else 0):
        d.line([T(50, y), T(50, min(y + 4.5, 100 + off / k))], fill=line, width=max(1, int(2.6 * k)))
        y += 8
    d.rectangle([0 if maskable else off, off + 71 * k, S if maskable else off + 100 * k, off + 73 * k], fill=edge)
    # arch: horizontal lo-hi-lo gradient, masked by the outline, clipped at the horizon
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).polygon([T(x, y) for x, y in pts], fill=255)
    ImageDraw.Draw(mask).rectangle([0, off + 72 * k, S, S], fill=0)
    grad = Image.new('RGBA', (S, S))
    gd = ImageDraw.Draw(grad)
    a, b = hexrgb(lo), hexrgb(hi)
    x0, x1 = off + 22 * k, off + 78 * k
    for x in range(S):
        t = min(1, max(0, (x - x0) / (x1 - x0)))
        f = t / 0.45 if t < 0.45 else (1 - t) / 0.55
        gd.line([(x, 0), (x, S)], fill=tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3)) + (255,))
    img.paste(grad, (0, 0), mask)
    if not maskable:   # trim the road/edge to the rounded tile
        tm = Image.new('L', (S, S), 0)
        ImageDraw.Draw(tm).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
        img.putalpha(tm)
    return img.resize((size, size), Image.LANCZOS)


draw(192, False).save(f'{out}/icon-192.png')
draw(512, False).save(f'{out}/icon-512.png')
draw(512, True).save(f'{out}/icon-maskable-512.png')
print('icons', theme)
