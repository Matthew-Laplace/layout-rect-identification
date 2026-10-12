---
name: layout-rect-identification
description: Read and identify rectangles of ANY layer (or a layer set) in a Virtuoso layout cell as a rectangle list, without changing geometry. Use when the user asks to identify the shapes of a layer (METAL1, METAL2, OD, PO, CONT, NBL, HVNW, …) in a pcell or cell, to report exact-copy duplicates, true subsets and overlapping rectangles, and to give the union area as an invariant. The layer is a parameter, not a constant. Covers the read path (bridge load + remote file), the three rules, the native merge channels, the forbidden operations, and the black-background white-outline display format.
---

# レイヤ矩形の識別（任意レイヤ。識別であり、修正ではない）

識別とは**指定レイヤの幾何を出力すること**。追加・削除・トリム・分類・座標変更はしない。

## 0. 2 つの方法（どちらを使うか先に決める）

| 方法 | 出力 | 用途 | 特徴 | きっかけの言葉 |
|---|---|---|---|---|
| **A 矩形リスト**（既定）| 矩形を 1 本ずつ | **高速な修正** | 各矩形の座標を 1 本ずつ照合できる。OA に戻せる | 「M1 を識別」「このレイヤを識別」|
| **B 和集合のみ** | 統合後の領域（外輪郭／多角形、内部の辺なし）| **高速な読解** | **矩形リストは出さない**。重なりと包含は自動的に消える。面積 = 各矩形の和集合 | 「和集合だけ出して」「和集合を取って」「統合後の形」|

**用途で選ぶ**：

- **理解したい**（形・接続・被覆面積・他レイヤとの関係）→ **B**。N 本の矩形が 1 領域になり、重なり・包含・内部の辺が消えて読みやすい。
- **修正したい**（移動・削除・延長・OA への書き戻し）→ **A**。和集合には編集できる矩形の辺がない。
- 典型的な流れ：**まず B で和集合を読む**（定性＋不変量としての和集合面積を取得）→ **A で矩形を取って修正** → 修正後に和集合面積で照合する（面積が変わる指示がない限り、修正前と一致すること）。

**2 つの方法の目的は共通で、人が（または次の読み取りが）扱う実体の数を減らすこと。** 実測：

| 場面 | 前 | 後 | 方法 |
|---|---|---|---|
| 12 セル・4 変種 | 372 本 | **276 本**（完全一致 96 本を圧縮）| A |
| 1 セル | 31 本 | **23 本**（完全一致 8 組を 1 本に）| A |
| 1 セル | 10 本 | **8 本**（真部分集合 2 本を識別しない）| A |
| 1 セル | 11 本 | **1 つの和集合領域**（輪郭 142 セグメント）| B |

### ネイティブの和集合チャネル（IC6.1.8 マニュアルで確認済み。自前のアルゴリズムは書かない）

| チャネル | コマンド / メニュー | 性質 | 用途 |
|---|---|---|---|
| 対話マージ | **Edit → Basic → Merge**、ショートカット **`Shift-m`**（2026-10-12 実機で確認）| **データ変更** | 同レイヤのオブジェクトを 1 つに統合（blockage も可。P&R と snap boundary は非対応。via を飛ばすオプションの既定は `t`）|
| SKILL マージ | `leMergeShapes( list(fig1 fig2 fig3) )` | **データ変更** | 指定した図形の和集合 |
| レイヤ演算 | `dbLayerOr(cvId …)`、ほかに `dbLayerAnd / dbLayerAndNot / dbLayerXor / dbLayerSize / dbLayerHoles / dbLayerNoHoles / dbLayerEnclose / dbLayerTile` | **データ変更**（新しい図形を返す）| **レイヤ全体の和集合**を取る最速の経路 |
| 表示のみ | **Display → Merge Shapes**（Display Abstraction Controls、環境変数 **`mergeEnable`**、Scope: Pcells / Except current / All）| **表示のみ**（"hiding all the extra edges"）| 方法 B の「高速な読解」。データを触らず重なりを統合して見せる |

## 1. 読み取り

- 対象は `library/cell/view` の 3 段表記＋**レイヤ名**で報告に書く。ユーザーは**別の cell** を見ていることがある（実際に踏んだ：ウィンドウ表題は `<lib> <cell>` なのに、こちらは別の cell を読み続けていた）。
- インスタンスから読む：`inst~>master~>shapes` のうち当該レイヤの `drawing` 図形を `dbTransformBBox(shape~>bBox inst~>transform)` で最上位の絶対座標へ変換する。最上位自身の図形は `cv~>shapes` から直接取る。
- **走査の深さは 2 以下**。それより深いと**幻の矩形**が出る：実測で深さ 5 まで辿ると `x` が負の 6 本とサブミクロンずれの 4 本（変換合成の誤り）が混入した。
- **インスタンスの bbox で濾す**：`inst~>bBox` を外れる矩形は取得エラーとして捨てる。この判定は毎回先に走らせる。
- 同じ pcell でもパラメータ変種（幅・高さ）がある。**セルごとに自分の座標を使う**。あるセルの数値を別のセルに流用しない。
- 確実な取得経路：`.il` を書く → `virtuoso-bridge load <file> -p <profile>` → SKILL が `outfile` で遠隔の `/tmp/...` に落とす → `ssh cat` で回収する。`eval --stdin` に複数のフォームを送ると**最初のフォームの結果しか返らない**ので、トランザクションや取得には使わない。
- 読み取り専用（`"r"`）で開く。識別の段階では `dbSave` しない。

## 2. 完全一致（辺の座標が同一、許容 1e-3 µm）

**1 本だけ**識別する。

## 3. 真部分集合（A が B に完全に入る、両軸とも）

**大きい方だけ**識別し、部分集合は**識別しない**。判定：

```
B.x0 ≤ A.x0  かつ  A.x1 ≤ B.x1  かつ  B.y0 ≤ A.y0  かつ  A.y1 ≤ B.y1
```

片軸だけなら（部分的な重なり）**部分集合ではない**。両方を識別する。

## 4. 部分的な重なり：識別では触らない。内部の辺はネイティブ Merge に任せる

識別は**重なりに触らない**。内部の辺を消したい場合は Virtuoso のネイティブ機能を使い、延長アルゴリズムを自作しない：

- データ変更：`Edit → Basic → Merge`（**`Shift-m`**）、`leMergeShapes( list(fig…) )`、`dbLayerOr(cvId …)`
- 読み取り専用：`Display → Merge Shapes`（`mergeEnable`）—— 余分な辺を隠すだけでデータは変えない

## 5. 禁止事項

- 矩形を**分類**しない（「これはソース／ドレイン／ゲート」「これは枠」「これは欠陥」などと言わない）。
- 図形の追加・削除・トリムをしない。識別段階で OA に保存しない（`dbSave` は識別ではない）。
- 重なりを「欠陥」と解釈して大改造しない。内部の辺は第 4 節のネイティブ機能に任せる。
- ガードリングなどの構造もそのまま識別し、用途の分類はしない。
- 指示なくレイヤを差し替えない（`METAL2` を求められて `METAL1` の結果を出さない）。

## 6. 表示

- **黒背景・白枠**、識別した矩形のみ、1 つのスタイル。塗りつぶし・色分け・分類はしない。
- 文字は重ねない（多くても 1 行の個数）。「識別したものだけ見せて」と言われたら、凡例・矢印・前後比較を付けない。
- 明細が必要なときは座標表（`# / x0 / y0 / x1 / y1 / W×H`）を別に付け、CSV にもできる。

## 7. 検証（必須）

- 和集合面積を座標圧縮で厳密に計算し、識別の前後で一致することを示す（差 < 1e-6）。一致しなければ停止して報告する。
- **入力本数 / 一意本数 / 識別本数**の 3 つを報告し、併せて「除いた完全一致」と「識別しない部分集合」の本数を出す。

## 8. 報告の形式

1 回の識別で、`library/cell/view` ＋ **レイヤ名** ＋ 3 つの本数 ＋ 識別した矩形のリスト ＋ 和集合面積の検証結果を出す。
状態語は `読み取り | 識別 | OA 未変更` を使い、識別を「修正済み／修復済み」と言わない。
