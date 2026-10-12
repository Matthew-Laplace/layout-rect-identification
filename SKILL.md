---
name: layout-rect-identification
description: Read and identify rectangles of ANY layer (or a layer set) in a Virtuoso layout cell as a rectangle list, without changing geometry. Use when the user asks to "识别" the shapes of a layer (METAL1, METAL2, OD, PO, CONT, NBL, HVNW, …) in a pcell or cell, to report exact-copy duplicates, true subsets and overlapping rectangles, and to normalise inward edges while proving the union area is unchanged. The layer is a parameter, not a constant. Covers the read path (bridge load + remote file), the rules, the inward-extension rule, the forbidden operations, and the black-background white-outline display format.
---

# 图层矩形识别（任意图层；识别，不是修改）

识别 = **输出指定图层的几何**。不新增、不删除、不裁剪、不分类、不改坐标（唯一例外见第 4 条）。

## 0. 两种方法（先确认用哪种）

| 方法 | 输出 | 用途 | 特征 | 触发说法 |
|---|---|---|---|---|
| **A 矩形清单**（默认）| 逐条矩形，含第 4 条的向内延长 | **快速修改** | 保留每条矩形；条数、坐标可逐条核对；可回填 OA | "识别 M1 / 识别某层" |
| **B 只提并集** | 合并后的区域（外轮廓／多边形，无内部边）| **快速阅读** | **不给矩形清单**；重叠与包含关系自动消失；面积 = 各矩形并集 | "只提并集"、"提并集"、"合并后的形状"、"读并集识别" |

**用途决定选哪种方法**：

- 要**看懂**（形状、连通、覆盖面积、与别的层的关系）→ 用 **B**。一个区域替代 N 条矩形，读得快；重叠、包含、内部边全部消失，不会被细节误导。
- 要**修改**（移动、删除、延长、回填 OA）→ 用 **A**。并集没有可编辑的矩形边界，改不了；必须逐条拿到矩形坐标。
- 典型流程：**先用 B 读并集**（定性 + 拿到并集面积作为不变量），**再切 A 拿矩形**去改，改完用并集面积复核（必须与改前相等，除非用户要求改变面积）。

### 原生并集通道（IC6.1.8 文档已核，省掉自己写并集算法）

| 通道 | 命令 / 菜单 | 性质 | 用途 |
|---|---|---|---|
| 交互合并 | **Edit → Basic → Merge**，快捷键 **`Shift-m`**（2026-10-12 用户实测可用）| **改数据** | 同层对象合并成一个（也支持 blockage；不支持 P&R 与 snap boundary 对象；默认跳过 via，选项默认 `t`）|
| SKILL 合并 | `leMergeShapes( list(fig1 fig2 fig3) )` | **改数据** | 对指定图形做并集 |
| 层布尔 | `dbLayerOr(cvId …)`，同类还有 `dbLayerAnd / dbLayerAndNot / dbLayerXor / dbLayerSize / dbLayerHoles / dbLayerNoHoles / dbLayerEnclose / dbLayerTile` | **改数据**（返回新图形）| **整层提取并集**最快路径 |
| 只读显示 | **Display → Merge Shapes**（Display Abstraction Controls，环境变量 **`mergeEnable`**，Scope: Pcells / Except current / All）| **只改显示**（"hiding all the extra edges"）| 方法 B 的"快速阅读"：不改数据就让重叠看起来合并 |

文档出处（本地镜像 `IC618/doc`，release `IC_06.18.030_lnx86`，注册库 `IC6.18`；同样内容也在 Obsidian 知识库 `<vault>/Raw/<converted>/` 的 IC618 转换稿里，转换稿更好搜）：`vlehelp`（Merge 命令、`Shift-m`、Merge Shapes/`mergeEnable`）、`sklayoutref/layout.html`（`leMergeShapes`）、`skdfref`（`dbLayer*`）。
注意：前三条会**创建/修改 OA 对象**，属于修改而不是识别；用之前必须有明确的写授权。文档证据不等于 live 会话已具备这些命令。

- 两法必须给出**相同的并集面积**（差 < 1e-6），这是互相校验的判据：先用 A 的矩形算并集面积，再用 B 的轮廓算一遍，两者不等即报错停止。
- 选择不明时按 A 并询问；用户说"只提并集"就只给 B，不要附赠矩形清单。
- B 允许出现孔洞（内部空洞）—— 外轮廓 + 孔洞一起报，孔洞面积从并集面积里扣除。

**两种方法的共同目的：减少需要人（或下一次读取）处理的实例数量。** 记录实测效果：

| 场景 | 处理前 | 处理后 | 方法 |
|---|---|---|---|
| `<lib>/<cellB>/layout` 12 个单元 | 372 条矩形 | **276 条**（完全重复 96 条被压掉）| A |
| `<lib>/<cellB>/layout` 左下角单元 | 31 条原始 | **23 条**（8 组完全重复各留一条；子集 0）| A |
| `<lib>/<cell>/layout` 一例 | 10 条矩形 | **8 条**（真子集 2 条不识别）| A |
| 另一例（含向内延长）| 10 条矩形 | **4 条**（子集 2 + 延长消内部边），并集面积不变 | A |
| `<lib>/<cell>/layout` METAL1 | 11 条矩形 | **1 个并集区域**（142 段轮廓）| B |

所以识别不是"把图形抄一遍"，而是**降维**：A 压条数，B 压对象个数。报告里要有处理前后的数量对比，让降维幅度可验证。

**图层是参数**：先问清或读到你被要求识别的图层名（`layerName` + `purpose`，例如 `METAL1 drawing`、`METAL2 drawing`、`OD drawing`、`PO drawing`、`CONT drawing`、`NBL drawing`、`HVNW drawing`）。一次只识别一个图层，除非用户明确要一组；一组时逐层分开报告，不要混在一起。

## 1. 读取

- 目标写成完整三级标识 `library/cell/view` + **图层名**，写进报告；用户可能正在看**另一个 cell**（实测踩过：窗口标题是 `codex test_only`，而我一直在读 `<lib>/<cellB>`）。
- 从实例读：`inst~>master~>shapes` 中该图层的 `drawing` 图形，用 `dbTransformBBox(shape~>bBox inst~>transform)` 换算到顶层绝对坐标；顶层自身的图形直接取 `cv~>shapes`。
- **遍历深度 ≤ 2**。再深会产生**幻影矩形**：实测深度 ≤5 时出现 6 条 `x` 为负、4 条亚微米偏移的假副本（变换合成错误）。
- **用实例 bbox 过滤**：任何超出 `inst~>bBox` 的矩形一律判为采集错误并丢弃。这条判据每次先跑。
- 同一个 pcell 有多个参数变体（宽/高不同），**逐单元用各自坐标**，不要把一个单元的数值套到另一个。
- 可靠取数路径：写 `.il` → `virtuoso-bridge load <file> -p <profile>` → SKILL 用 `outfile` 落到远端 `/tmp/...` → `ssh cat` 取回。`<bridge-cli> eval --stdin` 送多表单时**只回第一个表单的结果**，不要用它做事务或取数。
- 只读打开（`"r"`），识别阶段不 `dbSave`。

## 2. 完全相同（边坐标一致，容差 1e-3 µm）

只识别其中**一条**。

## 3. 真子集（A 完全落在 B 内，两轴都满足）

只识别**更大**的那条，子集**不识别**。判据：

```
B.x0 ≤ A.x0  且  A.x1 ≤ B.x1  且  B.y0 ≤ A.y0  且  A.y1 ≤ B.y1
```

只有一轴满足（部分交叠）**不是**子集，两条都要识别。

## 4. 部分交叠：向内延长（唯一允许改坐标的操作）

把某条**落在对方内部**的边，延长到**对方的边界**，前提是：

> 延长带（这条边扫到对方边界形成的矩形）必须**完全落在对方矩形内** —— 即该方向上的垂直跨度 ⊆ 对方跨度。

这样并集**不变**（不新增图形），只是消除内部边。**反向延长一律禁止** —— 延长部分会伸到对方外面，那属于新增图形。

实例（`<lib>/<cell>/layout`，METAL1）：

```
竖条 (2.605,-3.515)-(5.775, 7.525)   下边 -3.515 → -7.705   延长带落在横条内 ✓
横条 (-9.380,-7.705)-(10.695,1.255)  不动
并集面积 199.748 → 199.748  不变 ✓
```

## 5. 禁止

- 禁止对矩形**分类**（不要说"这是源/漏/栅""这是框""这是缺陷"）。
- 禁止新增、删除、裁剪几何；识别阶段不落 OA（`dbSave` 不属于识别）。
- 禁止把交叠解释成"缺陷"去大改；第 4 条的向内延长是唯一例外。
- 环框（guard ring）等结构照原样识别，不做用途分类。
- 不要擅自把图层换成别的层（例如被要求识别 `METAL2` 时不要给 `METAL1` 的结果）。

## 6. 展示

- **黑底白框**，只画识别到的矩形，一个样式，不填充、不标色、不分类。
- 不叠文字说明（最多一行计数）。用户明确说"只展示你识别到的"时，不要加图例、箭头、前后对照。
- 需要给明细时另附坐标表（`# / x0 / y0 / x1 / y1 / W×H`），并可存 CSV。

## 7. 校验（必做）

- 每次向内延长后，用坐标压缩法重算**并集面积**：延长前后必须相等（差 < 1e-6）。不等 → 停止并报告，说明延长带越界。
- 报告三个数：**原始条数 / 唯一条数 / 识别条数**，外加"去掉的完全重复"与"不识别的子集"条数。

## 8. 报告口径

一次识别输出：`library/cell/view` + **图层名** + 三个条数 + 识别矩形清单 + 并集面积校验结果。
状态词用 `读回 | 识别 | 未修改 OA`，不要把识别说成"已修改/已修复"。
