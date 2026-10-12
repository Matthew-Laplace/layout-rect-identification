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

## 中文说明

**两种方法，一个不变量。**

- **方法 A（矩形清单）→ 快速修改**：完全相同只留一条；真子集只留大的；部分交叠时把落在对方内的边
  延长到对方边界（**前提：延长带完全落在对方内**，并集不变、不新增图形）；反方向禁止。
- **方法 B（并集）→ 快速阅读**：合并成一个区域，只给轮廓与面积，不给矩形清单。

两法的**并集面积必须相同**，这是互相校验的判据。识别不是抄图形，而是降维：实测 372→276 条、
11 条→1 个并集区域。展示一律黑底白框、只画识别到的图形、不分类。
