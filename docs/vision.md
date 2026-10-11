# Vision (draft v1)

> Status: working draft, refined iteratively from [initial_vision.md](initial_vision.md).
> Sections marked **[OPEN]** are undecided and up for discussion.
> The concrete architecture and roadmap are in [plan.md](plan.md).

## 1. Goal

A Python library for describing furniture the way woodworkers think about
it: its parts, how they are joined, how their shapes are constrained, and
how they are made and assembled. From one design, the library should
produce:

- a 3D model (for viewing and rendering),
- a cut list and shopping list,
- 2D drawings of each part with its joinery,
- step-by-step manufacturing and assembly instructions.

Designs are plain Python: easy for humans and LLMs to read, write, diff, and
parametrize ("make it 20 cm wider", "use 25 mm oak instead"). They should be
**modular, composable and parametric**, so that woodworking knowledge
(joints, materials, rules of thumb, whole components) turns into a library
that anyone can extend, and so that people can share parts and whole pieces.

## 2. Two layers: shapes and semantics

We don't write a geometry kernel. [build123d](https://build123d.readthedocs.io)
(Python, on OpenCascade) is the **shape layer**: boxes, sketches, extrusions,
booleans, locations, export. The first experiments
([mortise_tenon.py](../examples/mortise_tenon.py),
[dovetail_corner.py](../examples/dovetail_corner.py)) show it can model
furniture well. They also show its cost: every coordinate is computed by
hand, the same intent (a tenon) is spelled out as boxes in global space, and
nothing knows that the result is a rail with a tenon.

woodwright is the **semantic layer** on top: it speaks the language of the
shop. Boards, faces and edges, cuts (rabbet, dado, mortise), joints,
assemblies, and later the process of making them. It is less verbose than
build123d at the cost of a narrower space of what can be represented, and
that narrowness is a feature: it is what lets the library compute cut
lists, place parts and write instructions.

The two layers are **not sealed off from each other**. woodwright depends on
build123d directly, with no kernel-neutral geometry language in between.
Whoever defines a new cut or joint writes its geometry in build123d right
there, in a coordinate frame woodwright provides (a face of a board, or the
frame of a joint). The rule is: *drop down to build123d inside a semantic
object, never around it*. Custom geometry always enters through a feature or
a joint, so it is still tracked, placed, listed and validated. See
[plan.md §3](plan.md#3-the-two-layers).

## 3. Core insight: woodworkers think in joints, not coordinates

In generic CAD you model solids and position them in space. A woodworker
works differently:

- starts from **stock** (a board of some thickness, later a dowel or a sheet),
- relates parts through **joints** ("the apron is tenoned into the leg,
  set back 5 mm from its outside face"),
- measures from **reference faces** and uses **flush/offset** relations,
  not absolute coordinates.

So the library should work the same way:

1. **A joint is a first-class relation that modifies *both* parts.** Declaring
   a mortise-and-tenon between rail and stile makes the library cut the
   mortise into the stile, form the tenon on the rail, and lengthen the rail
   by the tenon length. The user states intent; the library derives the
   features.
2. **Placement follows from joints and alignment relations.** If every part
   is connected to the assembly through joints, its position in 3D can be
   computed. Absolute coordinates should be rare.
3. **Design dimensions and cut dimensions are different.** The user says
   "the rail is 600 mm between the legs". The library works out that it is
   cut 600 + 2 × tenon length long.
4. **Wood is shaped by removing material.** A part is its stock blank minus
   the cuts made into it. Joints never "add" material; a tenon is what is
   left after cutting the shoulders and cheeks from a longer blank. This
   matches the shop and keeps the geometry model simple.

That is the gap between this library and CSG. CSG describes *what the solid
is*, while woodwright describes *why it is that shape*. build123d is still
what builds the actual geometry.

## 4. The pipeline

```
 ┌──────────────────────┐
 │ 1. Design            │  Python objects built by user code:
 │  stock, parts,       │  parameters are Python values,
 │  joints, alignments  │  components are Python functions/classes
 └─────────┬────────────┘
           │ resolve (kernel-free: defaults, allowances, placement, features)
 ┌─────────▼────────────┐
 │ 2. Resolved model    │  every part has cut dimensions, a list of
 │  parts + features +  │  features in its local frame, and a placement
 │  placements          │  in the assembly; serializable
 └─────────┬────────────┘
           │ realize (build123d: blank − cuts, placed)        │ plan (later)
 ┌─────────▼────────────┐                         ┌────────────▼─────────┐
 │ 3. Geometry          │                         │ 3'. Process plan     │
 │  solids, assembly    │                         │  operations, order,  │
 │                      │                         │  glue-up sequence    │
 └─────────┬────────────┘                         └────────────┬─────────┘
           │ export / check                                    │
 ┌─────────▼───────────────────────────────────────────────────▼─────────┐
 │ 4. Outputs: STEP/STL/glTF, part drawings (SVG), cut list (CSV/MD),    │
 │    interference and fit checks, later instructions (MD/HTML)          │
 └───────────────────────────────────────────────────────────────────────┘
```

The resolved model is computed without building any solids, so cut lists
and most checks are fast and testable without OpenCascade. Each layer should
be inspectable and serializable as text. That helps with debugging, testing,
and feeding the result to an LLM ("here's the resolved model, why is this
apron 3 mm too short?").

## 5. Who specifies what

| Concern | User specifies | Library computes |
|---|---|---|
| Overall size | Key dimensions and parameters, as Python values | Derived dimensions are ordinary Python expressions |
| Materials | Species, stock thickness | Grain direction defaults, volume / board length |
| Parts | Name, stock, design dimensions | Cut dimensions including joinery allowances |
| Joints | Type, which faces/ends meet, alignment (flush, offset, centered) | Joint geometry from rules of thumb (e.g. tenon ≈ ⅓ thickness), overridable |
| Placement | Almost nothing, only the root part or overall orientation | All part placements, from joint and alignment relations |
| Validation | Tolerances, warnings to ignore | Interference, joint fit, closed loops, cross-grain gluing, stock limits |
| Stock usage | Available stock or "buy standard" | Cut layout, waste, shopping list (later) |
| Process | Tools available, preferences | Operations per part, ordering, glue-up sequence (later) |

Rule of thumb: **the user writes decisions, and the library derives
consequences.** Every derived value should be overridable, so the library
suggests and the user can still decide.

## 6. Building blocks

- **Parameters and expressions**: plain Python variables and arithmetic.
  Python *is* the spreadsheet of §8, so there is no expression language to
  design.
- **Stock**: `Stock.board(thickness=20, species="oak")`; later a cylindrical
  rod/dowel. Carries grain direction and nominal vs actual sizes.
- **Parts**: an instance of stock with a name and design dimensions. Each
  part has a local frame tied to the grain and named faces (see §7).
- **Features (cuts)**: material removed from one part (rip, crosscut, mitre,
  chamfer, rabbet, dado, groove, slot mortise, mortise, tenon, ...). Joints
  generate most of them; users can add them directly and define their own.
- **Joints**: a relation between two parts (later more, e.g. kumiko) that
  generates features on each, adds allowances to their cut dimensions, and
  determines their relative placement. They come from a standard library
  (see [validation.md](validation.md)) and users can define their own.
- **Alignment relations**: `flush`, `offset`, `centered` between named faces.
- **Assemblies and components**: an assembly groups parts and joints and can
  be nested. A component is a Python function or class that builds a
  parametric assembly (a "frame-and-panel door", a "leg-and-apron end
  frame") and exposes faces for joining it to the rest. This is how a
  standard library and shared designs grow beyond primitives.
- **Workshop profile**: available tools (chisel widths, saw kerf, later drill
  bits), so that defaults round to sizes you can actually cut.
- **Process annotations** (later): sub-assembly grouping, operation
  overrides, finishing steps.

### Illustrative sketch (API not final)

A corner of a frame: a rail tenoned into a stile.

```python
import woodwright as ww

oak = ww.Stock.board(thickness=20, species="oak")

frame = ww.Assembly("frame corner")
stile = frame.add(ww.Board("stile", oak, length=600, width=60))
rail = frame.add(ww.Board("rail", oak, length=300, width=60))  # shoulder to shoulder

frame.join(
    ww.MortiseTenon(
        tenon=rail.end.left,
        mortise=stile.edge.back,
        position=ww.centered(),  # rail centered along the stile
        # tenon_thickness=8,     # override a library default
    )
)  # reference faces are flush by default

model = frame.resolve()
print(model.cut_list())  # rail: 340 x 60 x 20 (300 + 40 tenon)
model.export("frame.step")
```

The library works out the mortise in the stile and the tenon on the rail.
It places the rail relative to the stile and adds the tenon length to the
rail's cut length.

## 7. Coordinate system

Proposal: **named faces on a grain-aligned local frame, and no global
coordinates in normal use.**

- Each board has axes **L** (length, along grain), **W** (width), and
  **T** (thickness), mapped to the local x, y, z.
- Faces are named as if the board lies on the bench, length left to right,
  **reference face down and reference edge towards you**, as it would sit on
  a table saw against the fence:
  - `face.bottom` / `face.top`: the wide faces (`face.bottom` is the
    reference face),
  - `edge.front` / `edge.back`: the long narrow faces (`edge.front` is the
    reference edge),
  - `end.left` / `end.right`: the end grain (`end.left` is the reference end).
- The local origin is the corner where the three reference faces meet, so
  all measurements in the part frame are positive, as with a marking gauge.
- Names describe the board, not its position in the furniture: a leg's
  `end.left` is its foot. Components may add aliases (`leg.foot`). **[OPEN]**
  whether these names read well in practice.
- The whole assembly has one global frame (X = width, Y = depth, Z = height)
  that you only need for orienting the root and for export.
- Positions *along* a face are given as offsets from named faces/ends
  ("50 mm from `stile.end.left`").
- Units are millimetres (plain floats) and degrees. Imperial may come later
  as input helpers.

Internally, placements are ordinary rigid transforms (build123d `Location`).
Geometric algebra stays an idea to revisit only if transforms get awkward.

Rods (cylindrical stock) get the same treatment with a different base shape:
an axis along the grain, two ends and a round surface. **[OPEN]** naming
and reference marks for rods.

## 8. Constraints

Two levels:

1. **Directed expressions** (spreadsheet-like): `rail_length = opening`,
   with the joint adding `2 * tenon_length` to the cut length. In a Python
   library these are just Python. Covers most furniture.
2. **Declarative constraints** that need a solver: "these three shelves are
   equally spaced and the middle one is at elbow height". More powerful, but
   under- and over-constrained systems are hard to report in an
   understandable way.

Decision: only (1). Joints and alignment relations are themselves
*directed*: they propagate position from a parent part to a child along the
joint graph. When the joint graph has a cycle (a box, a frame), the library
checks that the loop closes and reports the mismatch otherwise ("the back
rail is 3 mm too short to reach the right leg"). Add (2) only if real
examples demand it.

## 9. Wood-specific concerns (where generic CAD falls short)

- Grain direction per part, and checks for cross-grain construction
  (wood movement: a solid top glued rigidly across an apron will crack).
- Nominal vs actual stock sizes; rough vs milled dimensions.
- Saw kerf, milling allowances, and tolerances for joint fit.
- Cuts that can actually be made with the tools at hand (see §11 scope).
- Stock yield: laying parts out on real boards (later).
- Assembly feasibility: can this part physically be inserted after that
  one? Glue open time and how many joints get glued at once (later).
- Finishing order (later).

## 10. Outputs

| Output | Approach |
|---|---|
| 3D model | build123d solids, exported to STEP/STL/glTF |
| Images | Hidden-line SVG projections (as in the examples); glTF for viewers and renderers |
| Part drawings | Orthographic projections per part with dimensions of its features (SVG/PDF) |
| Cut list | Parts with cut dimensions, material, grain, count (CSV/Markdown), from the resolved model |
| Stock layout | Nesting of parts onto boards (SVG), later |
| Instructions | Ordered steps built from the process plan, with images per step, later |
| Later | Structural analysis, cost estimate |

## 11. Scope

To keep the problem tractable, the first versions are limited to:

- **Stock**: rectangular boards; cylindrical rods/dowels after the first
  milestones.
- **Cuts** that can be made with hand tools (saws, hand plane, chisel) or a
  table saw: planar cuts, rabbets, dados, grooves, mortises, tenons,
  dovetails. **Drilling** (holes, dowels, round tenons, drawbores, wedges)
  comes later.
- **Joints held by glue or friction**: no screws, nails or hardware.
- **Binary joints** first (two parts per joint); joints of several parts
  (kumiko, three-way mitres) later.
- **Orthogonal assemblies** first; angled parts (splayed legs, angled laps)
  later.
- **Metric units.**

## 12. Language and syntax

The library is the language: designs are Python code using woodwright
objects, in the style of build123d. This is the fastest way to prototype,
gives full power and debugging for free, and makes extending the library
(a new joint, a new component) the same act as using it.

A declarative front-end (YAML or similar, or a custom syntax) may come later
on top of the same object model, once the model has settled. To keep that
door open, the core objects should be plain data (dataclasses with numeric
and string parameters and references to faces), with code needed only for
extensions such as custom geometry.

## 13. Validation ladder

Each step is a real example that must go end-to-end (design → 3D + cut
list, and later instructions) before we move on. Together these examples
become the test suite. The full catalogue of cuts, joints and pieces that
could eventually make up the standard library is in
[validation.md](validation.md); the order in which we tackle them is in
[plan.md §6](plan.md#6-roadmap).

1. **Single board** and **single cuts** on it.
2. **Butt joints**: two parts, placement derived from the joint.
3. **Rabbet / dado / groove joints**: a feature on one part only.
4. **Mortise and tenon, half-lap, bridle**: features on both parts, derived
   lengths, defaults + overrides.
5. **Box joint, dovetails, mitres**: interlocking joints defined in a shared
   joint frame.
6. **Box / frame**: a closed loop in the joint graph.
7. **Stool, table**: 3D structure, components, sub-assemblies.
8. **Build a real piece** from the generated outputs.

## 14. Non-goals (for now)

- Freeform/organic shapes (carving, steam bending, turned parts beyond
  simple profiles).
- CNC toolpath generation.
- A general constraint solver.
- A geometry backend other than build123d.
- Screws, nails, hardware; upholstery, metalwork.
- Sheet goods (plywood) and edge banding.

## 15. Open questions

- Which workshop do the generated instructions assume? A workshop profile
  (§6) is the likely answer; how detailed must it be?
- How are rods, and later non-rectangular parts (tapered legs, curved
  aprons), modelled and named?
- How much of the process plan is derived vs authored? Is the user's
  grouping of sub-assemblies input or output?
- Versioning of library defaults: a changed rule of thumb shouldn't silently
  change old designs.
- How are designs and components shared: Python packages, single files, a
  catalogue?

## 16. Prior art to study

- **OpenSCAD**: text-based CSG; the baseline for "furniture in text".
- **build123d / CadQuery**: Python CAD on OpenCascade; our shape layer.
  build123d's own joints (`RigidJoint.connect_to`) are prior art for placing
  parts by mating frames.
- **Zoo KCL**: a recent purpose-built CAD language.
- **FreeCAD** (incl. woodworking add-ons), **SketchUp + OpenCutList**: how
  woodworkers do cut lists today.
- **Tsugite** (Larsson et al., 2020): research on interactive design of wood
  joints.
- Parametric CAD assembly constraints (Fusion 360, Onshape mates): prior art
  for mate/alignment relations.
