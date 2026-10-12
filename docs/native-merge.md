# Native union / merge channels in Virtuoso Layout

Four ways to get a union out of overlapping same-layer shapes. Three of them change
data, one only changes the display. Sources are the IC6.1.8 offline manuals; a documented
command is not proof that a given installation has it.

## 1. Interactive: Merge — `Edit → Basic → Merge`, shortcut `Shift-m`

> "You can merge one or more objects created on the same layer into one object. This is
> sometimes referred to as performing a logical AND on the objects."

- Result of merging ROD objects stays a ROD object (net is kept only when the merged
  ROD objects share a net).
- Blockage objects merge like polygons; if the selected blockages belong to different
  instances you are asked which instance owns the result (or none).
- **Not supported:** P&R and snap boundary objects.
- Option "Skips via shapes during the Merge operation", default `t`.

Manual: *Virtuoso Layout Suite L User Guide* (`vlehelp`), Merge command, Edit – Basic menu.

## 2. SKILL: `leMergeShapes( list(fig1 fig2 fig3) )`

Merges the figures you pass in and returns the merged figure(s). Use it when a script
already holds the selected shapes.

Manual: *Virtuoso Layout Suite SKILL Reference* (`sklayoutref`), `leMergeShapes`.

## 3. SKILL: layer boolean — `dbLayerOr(cvId …)`

```skill
m3Out = dbLayerOr(cvId "metal3" m1Rect m2Rect)
```

Whole-layer union in one call — the fastest path when you want the union of a layer
rather than of a hand-picked selection. Companions in the same family:

```
dbLayerOr   dbLayerAnd   dbLayerAndNot   dbLayerXor
dbLayerSize dbLayerHoles dbLayerNoHoles  dbLayerEnclose
dbLayerInside dbLayerOutside dbLayerStraddle dbLayerTile
```

Manual: *Virtuoso Design Environment SKILL Reference* (`skdfref`), `dbLayerOr` and the
`dbLayer*` family.

## 4. Display only: Merge Shapes — `Display → Merge Shapes`

> "Merge Shapes makes the display more readable by hiding all the extra edges in the design."

- Environment variable: **`mergeEnable`**.
- Scope: `Pcells` / `Except current` / `All`.
- Changes **nothing** in the data — the ideal switch for fast reading of a dense layer.

Manual: *Virtuoso Layout Suite L User Guide* (`vlehelp`), Display Abstraction Controls.

## How they fit this repository

| Goal | Use | Touches data |
|---|---|---|
| Read a dense layer quickly | `Display → Merge Shapes` (`mergeEnable`) | no |
| Merge what you selected | `Shift-m` / `leMergeShapes` | yes |
| Extract the union of a whole layer | `dbLayerOr` | yes |
| Read from a text dump, no session | `scripts/identify.py --union` | no |

Whatever route produces a union, keep the **union area** as the invariant: compare it
before and after, and stop if it moved.

## Provenance

Local IC6.1.8 documentation snapshot, release `IC_06.18.030_lnx86`, registered library
`IC6.18`; books `vlehelp`, `sklayoutref`, `skdfref`. Quoted strings are the manual text.
The `Shift-m` binding was also confirmed in a live IC6.1.8 layout session by the user
(2026-10-12).
