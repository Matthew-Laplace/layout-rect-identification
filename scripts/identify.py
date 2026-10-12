#!/usr/bin/env python3
"""Identify the shapes of one layout layer: reduce first, then report.

Three rules, one invariant.

  exact duplicate (same edges)      -> identify one
  true subset (A inside B, 2 axes)  -> identify the larger, drop the subset
  everything else                   -> identify as is

  invariant: the union area is the same before and after identification.

Internal edges inside an overlap are NOT our job: Virtuoso does it natively
(Edit - Basic - Merge, Shift-m; or leMergeShapes / dbLayerOr in SKILL), and
Display - Merge Shapes (mergeEnable) hides them without touching the data.

Two outputs:
  --union   merged region only (outline segments + area)   -> fast reading
  default   identified rectangle list                      -> fast modification

Input on stdin: lines "RECT <tag> x0 y0 x1 y1"; other lines are ignored.
  python3 identify.py rects.txt [--union] [--png out.png]
"""
import sys

EPS = 1e-6


def load(path):
    out = []
    for line in open(path):
        p = line.split()
        if p and p[0] == "RECT":
            x0, y0, x1, y1 = (round(float(v), 3) for v in p[-4:])
            if x1 > x0 and y1 > y0:
                out.append((x0, y0, x1, y1))
    return out


def grid(rs):
    xs = sorted({r[0] for r in rs} | {r[2] for r in rs})
    ys = sorted({r[1] for r in rs} | {r[3] for r in rs})
    cov = {(i, j): False for i in range(len(xs) - 1) for j in range(len(ys) - 1)}
    for (a, b, c, d) in rs:
        for i in range(xs.index(a), xs.index(c)):
            for j in range(ys.index(b), ys.index(d)):
                cov[(i, j)] = True
    return xs, ys, cov


def union_area(rs):
    xs, ys, cov = grid(rs)
    return sum((xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
               for (i, j), on in cov.items() if on)


def outline(rs):
    """Union boundary as axis-aligned segments (holes included)."""
    xs, ys, cov = grid(rs)
    nx, ny = len(xs) - 1, len(ys) - 1
    segs = []
    for j in range(ny):
        for i in range(nx):
            if not cov[(i, j)]:
                continue
            if j == 0 or not cov[(i, j - 1)]:
                segs.append((xs[i], ys[j], xs[i + 1], ys[j]))
            if j == ny - 1 or not cov[(i, j + 1)]:
                segs.append((xs[i], ys[j + 1], xs[i + 1], ys[j + 1]))
            if i == 0 or not cov[(i - 1, j)]:
                segs.append((xs[i], ys[j], xs[i], ys[j + 1]))
            if i == nx - 1 or not cov[(i + 1, j)]:
                segs.append((xs[i + 1], ys[j], xs[i + 1], ys[j + 1]))
    return segs


def reduce_rects(rs):
    uniq = sorted(set(rs))
    dups = len(rs) - len(uniq)
    def sub(a, b):
        return (a[0] >= b[0] - EPS and a[1] >= b[1] - EPS
                and a[2] <= b[2] + EPS and a[3] <= b[3] + EPS)
    keep = [r for r in uniq if not any(o != r and sub(r, o) for o in uniq)]
    return keep, dups, len(uniq) - len(keep)


def draw(rects, path, union=False):
    from PIL import Image, ImageDraw
    segs = outline(rects) if union else None
    xs = [s[0] for s in segs] + [s[2] for s in segs] if union else [r[0] for r in rects] + [r[2] for r in rects]
    ys = [s[1] for s in segs] + [s[3] for s in segs] if union else [r[1] for r in rects] + [r[3] for r in rects]
    x0, y0, x1, y1 = min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2
    w = 1300
    sc = w / (x1 - x0)
    h = max(60, int((y1 - y0) * sc))
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    at = lambda x, y: ((x - x0) * sc, h - (y - y0) * sc)
    if union:
        for (a, b, c, e) in segs:
            d.line([at(a, b), at(c, e)], fill=(255, 255, 255), width=2)
    else:
        for r in rects:
            p, q = at(r[0], r[1]), at(r[2], r[3])
            d.rectangle([p[0], q[1], q[0], p[1]], outline=(255, 255, 255))
    img.save(path)
    return path


def main():
    args = sys.argv[1:]
    png = args[args.index("--png") + 1] if "--png" in args else None
    src = [a for a in args if not a.startswith("--")][:1]
    if not src:
        print(__doc__)
        return 2
    rects = load(src[0])
    if not rects:
        print("no RECT lines found")
        return 1
    area = union_area(rects)

    if "--union" in args:                     # method B: fast reading
        print("union (reading)")
        print("  input rects      : %d" % len(rects))
        print("  outline segments : %d" % len(outline(rects)))
        print("  union area       : %.3f um^2" % area)
        if png:
            print("  png              : %s" % draw(rects, png, union=True))
        return 0

    keep, dups, subs = reduce_rects(rects)    # method A: fast modification
    print("rect list (modification)")
    print("  input rects      : %d" % len(rects))
    print("  exact duplicates : %d removed" % dups)
    print("  true subsets     : %d not identified" % subs)
    print("  identified rects : %d" % len(keep))
    print("  union area       : %.3f (unchanged)" % area)
    print()
    print("  #      x0        y0        x1        y1        W x H")
    for i, r in enumerate(sorted(keep, key=lambda z: (z[1], z[0])), 1):
        print("  %-5d %9.3f %9.3f %9.3f %9.3f  %6.2f x %.2f"
              % (i, r[0], r[1], r[2], r[3], r[2] - r[0], r[3] - r[1]))
    if png:
        print("\n  png: %s" % draw(keep, png))
    assert abs(union_area(keep) - area) < 1e-6, "union changed"
    return 0


if __name__ == "__main__":
    sys.exit(main())
