# layout-rect-identification

A fast way to **read** and **modify** the shapes of any layer (METAL1, OD, PO, CONT, …) in a
Virtuoso layout cell, built around two complementary methods and one invariant.

| Method | Output | Use it for | Why |
|---|---|---|---|
| **A — rectangle list** | the identified rectangles, one per line | **fast modification** | a union has no editable rectangle edges; you need coordinates to move, delete or extend |
| **B — union** | the merged region (outline segments + area) | **fast reading** | one region replaces N rectangles; overlaps, subsets and internal edges disappear |

**The invariant:** both methods must report the **same union area**. Method A proves it by
keeping the union unchanged while it normalises the input; method B computes it directly.
If the two disagree, something is wrong — stop.

## Why it is fast

Identification is not "copy the shapes out". It is dimensionality reduction:

| Case | Before | After | Method |
|---|---|---|---|
| 12 cells, 4 variants | 372 rects | 276 rects (96 exact duplicates dropped) | A |
| one cell | 31 rects | 23 rects (8 duplicate groups collapsed) | A |
| one cell | 10 rects | 8 rects (2 true subsets not identified) | A |
| one cell, with inward extension | 10 rects | 4 rects, union area unchanged | A |
| one cell | 11 rects | 1 union region (142 outline segments) | B |

## Native merge commands

See [docs/native-merge.md](docs/native-merge.md) for the four native union channels
(`Edit → Basic → Merge` / `Shift-m`, `leMergeShapes`, `dbLayerOr`,
`Display → Merge Shapes` / `mergeEnable`) with manual citations.

## The three rules

1. **Exact duplicates** (identical edge coordinates, 1e-3 µm tolerance): identify one.
2. **True subset** (A completely inside B, both axes): identify the larger one only.
   One axis is not enough — that is a partial overlap, and both stay.
3. **Everything else is identified as is.** No classification, no new, deleted or trimmed
   geometry, and the cellview is not saved.

Internal edges inside an overlap are **not** our job. Virtuoso already does it:
`Edit → Basic → Merge` (**Shift-m**), `leMergeShapes(list(fig…))`, `dbLayerOr(cvId …)`,
and `Display → Merge Shapes` (`mergeEnable`) which only changes the display.

## Reading the layout

`scripts/read_layer.il` is loaded into a running Virtuoso session and writes one layer's
rectangles to a text file on the machine that runs Virtuoso:

```
virtuoso-bridge load scripts/read_layer.il -p <profile> --timeout 300
ssh <host> cat /tmp/layer_rects.txt
```

Set `LAYER_NAME`, `TARGET_LIB`, `TARGET_CELL` at the top of the file. Hierarchy depth is
capped at 2 on purpose: deeper walks produced phantom rectangles in testing (six shapes with
negative x plus four sub-micron copies, from a transform-composition mistake). Filter the
result by each instance's bounding box as a second guard.

Output format:

```
RECT <tag> x0 y0 x1 y1
```

## Identifying

```
python3 scripts/identify.py rects.txt              # method A (rect list) + union check
python3 scripts/identify.py rects.txt --union      # method B (union only)
python3 scripts/identify.py rects.txt --png a.png  # also write a black/white image
```

Example (10 rectangles, two of them subsets):

```
method A (rect list, for modification)
  input rects      : 10
  exact duplicates : 0 removed
  true subsets     : 2 not identified
  inward extensions: 5
  identified rects : 8
  union area       : 334.363 -> 334.363 um^2 (unchanged)
```

```
method B (union, for reading)
  input rects      : 10
  outline segments : 104
  union area       : 334.363 um^2
```

## Display

Black background, white outlines, one style, no legend, no colour coding, no classification.
Show only what was identified.

## Requirements

- `python3` (standard library only) for `scripts/identify.py`; Pillow only if you pass `--png`.
- A running Virtuoso session with the bridge for `scripts/read_layer.il`.

## 日本語の説明

**2 つの方法、1 つの不変量。**

- **方法 A（矩形リスト）→ 高速な修正**：完全一致は 1 つだけ残す。真部分集合は大きい方だけ残す。
  部分的な重なりは識別では触らない（内部の辺は下記のネイティブ Merge に任せる）。
- **方法 B（和集合）→ 高速な読解**：1 つの領域に統合し、輪郭と面積だけを出す。矩形リストは出さない。

**2 つの方法の和集合面積は一致しなければならない**（差 < 1e-6）。これが相互検証の判定条件である。
識別は図形の写しではなく**次元削減**である：実測で 372→276 個、11 個→1 つの和集合領域になった。
表示は常に黒背景・白枠、識別した図形のみ、分類はしない。

内部の辺を消したい場合は Virtuoso のネイティブ機能を使う：
`Edit → Basic → Merge`（`Shift-m`）、`leMergeShapes`、`dbLayerOr`。読み取り専用なら
`Display → Merge Shapes`（`mergeEnable`）。詳細は [docs/native-merge.md](docs/native-merge.md)。
