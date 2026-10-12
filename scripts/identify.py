#!/usr/bin/env python3
"""Rectangle identification for IC layout layers.

Two methods, one invariant.

  Method A (rect list, for fast MODIFICATION)
      - exact duplicates       -> keep one
      - true subsets (A in B)  -> keep the larger only
      - partial overlap        -> extend the inside edge to the neighbour edge,
                                  but only when the swept strip stays inside the
                                  neighbour (union unchanged)
      -> prints the rectangle list

  Method B (union, for fast READING)
      - merges all rectangles into one region, prints the outline segments
      -> no rectangle list

Both methods must report the SAME union area.  That equality is the check.

Input on stdin: lines "RECT <tag> x0 y0 x1 y1" (extra header lines are ignored).
Usage:
  python3 identify.py rects.txt            # method A + union check
  python3 identify.py rects.txt --union    # method B only
  python3 identify.py rects.txt --png out.png [--union]
"""
import sys

EPS = 1e-6


def load(path):
    rects = []
    for line in open(path):
        p = line.split()
        if p and p[0] == "RECT":
            x0, y0, x1, y1 = (round(float(v), 3) for v in p[-4:])
            if x1 > x0 and y1 > y0:
                rects.append((x0, y0, x1, y1))
    return rects


def union_area(rs):
    """Exact union area by coordinate compression."""
    xs = sorted({r[0] for r in rs} | {r[2] for r in rs})
    ys = sorted({r[1] for r in rs} | {r[3] for r in rs})
    total = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx = (xs[i] + xs[i + 1]) / 2
            cy = (ys[j] + ys[j + 1]) / 2
            if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rs):
                total += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return total


def outline(rs):
    """Union boundary as axis-aligned segments (holes included)."""
    xs = sorted({r[0] for r in rs} | {r[2] for r in rs})
    ys = sorted({r[1] for r in rs} | {r[3] for r in rs})
    nx, ny = len(xs) - 1, len(ys) - 1
    cov = [[False] * nx for _ in range(ny)]
    for (a, b, c, d) in rs:
        for i in range(xs.index(a), xs.index(c)):
            for j in range(ys.index(b), ys.index(d)):
                cov[j][i] = True
    segs = []
    for j in range(ny):
        for i in range(nx):
            if not cov[j][i]:
                continue
            if j == 0 or not cov[j - 1][i]:
                segs.append((xs[i], ys[j], xs[i + 1], ys[j]))
            if j == ny - 1 or not cov[j + 1][i]:
                segs.append((xs[i], ys[j + 1], xs[i + 1], ys[j + 1]))
            if i == 0 or not cov[j][i - 1]:
                segs.append((xs[i], ys[j], xs[i], ys[j + 1]))
            if i == nx - 1 or not cov[j][i + 1]:
                segs.append((xs[i + 1], ys[j], xs[i + 1], ys[j + 1]))
    return segs


def is_subset(a, b):
    return (a[0] >= b[0] - EPS and a[1] >= b[1] - EPS
            and a[2] <= b[2] + EPS and a[3] <= b[3] + EPS)


def method_a(rects):
    uniq = sorted(set(rects))
    n_exact = len(rects) - len(uniq)
    subs = [r for r in uniq if any(o != r and is_subset(r, o) for o in uniq)]
    work = [list(r) for r in uniq if r not in subs]
    before = union_area(work)
    extensions = 0
    for _ in range(20):
        changed = 0
        for a in work:
            for b in work:
                if a is b:
                    continue
                if (min(a[2], b[2]) - max(a[0], b[0]) <= EPS
                        or min(a[3], b[3]) - max(a[1], b[1]) <= EPS):
                    continue
                # extend only when the swept strip stays inside b
                if b[1] < a[1] - EPS and b[0] <= a[0] + EPS and a[2] <= b[2] + EPS:
                    a[1] = b[1]; changed += 1
                if b[3] > a[3] + EPS and b[0] <= a[0] + EPS and a[2] <= b[2] + EPS:
                    a[3] = b[3]; changed += 1
                if b[0] < a[0] - EPS and b[1] <= a[1] + EPS and a[3] <= b[3] + EPS:
                    a[0] = b[0]; changed += 1
                if b[2] > a[2] + EPS and b[1] <= a[1] + EPS and a[3] <= b[3] + EPS:
                    a[2] = b[2]; changed += 1
        extensions += changed
        if changed == 0:
            break
    after = union_area(work)
    return work, n_exact, len(subs), extensions, before, after


def draw(rects, path, union=False):
    from PIL import Image, ImageDraw
    segs = outline(rects) if union else None
    if union:
        xs = [s[0] for s in segs] + [s[2] for s in segs]
        ys = [s[1] for s in segs] + [s[3] for s in segs]
    else:
        xs = [r[0] for r in rects] + [r[2] for r in rects]
        ys = [r[1] for r in rects] + [r[3] for r in rects]
    x0, y0, x1, y1 = min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2
    w = 1300
    sc = w / (x1 - x0)
    h = max(60, int((y1 - y0) * sc))
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    m = lambda x, y: ((x - x0) * sc, h - (y - y0) * sc)
    if union:
        for (a, b, c, e) in segs:
            d.line([m(a, b), m(c, e)], fill=(255, 255, 255), width=2)
    else:
        for r in rects:
            p, q = m(r[0], r[1]), m(r[2], r[3])
            d.rectangle([p[0], q[1], q[0], p[1]], outline=(255, 255, 255))
    img.save(path)
    return path


def main():
    args = [a for a in sys.argv[1:]]
    want_union = "--union" in args
    png = None
    if "--png" in args:
        png = args[args.index("--png") + 1]
    src = [a for a in args if not a.startswith("--")][:1]
    if not src:
        print(__doc__)
        return 2
    rects = load(src[0])
    if not rects:
        print("no RECT lines found")
        return 1

    if want_union:
        area = union_area(rects)
        segs = outline(rects)
        print("method B (union, for reading)")
        print("  input rects      : %d" % len(rects))
        print("  outline segments : %d" % len(segs))
        print("  union area       : %.3f um^2" % area)
        if png:
            print("  png              : %s" % draw(rects, png, union=True))
        return 0

    keep, n_exact, n_sub, n_ext, before, after = method_a(rects)
    print("method A (rect list, for modification)")
    print("  input rects      : %d" % len(rects))
    print("  exact duplicates : %d removed" % n_exact)
    print("  true subsets     : %d not identified" % n_sub)
    print("  inward extensions: %d" % n_ext)
    print("  identified rects : %d" % len(keep))
    print("  union area       : %.3f -> %.3f um^2 (%s)"
          % (before, after, "unchanged" if abs(after - before) < 1e-6 else "CHANGED - check the extensions"))
    print()
    print("  #      x0        y0        x1        y1        W x H")
    for i, r in enumerate(sorted(keep, key=lambda z: (z[1], z[0])), 1):
        print("  %-5d %9.3f %9.3f %9.3f %9.3f  %6.2f x %.2f"
              % (i, r[0], r[1], r[2], r[3], r[2] - r[0], r[3] - r[1]))
    if png:
        print("\n  png: %s" % draw([tuple(r) for r in keep], png))
    ua = union_area([tuple(r) for r in keep])
    if abs(ua - after) > 1e-6:
        print("union check FAILED: %.6f vs %.6f" % (ua, after))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
