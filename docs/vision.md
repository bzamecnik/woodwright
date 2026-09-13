# Vision (draft v0)

> Status: working draft, refined iteratively from [initial_vision.md](initial_vision.md).
> Sections marked **[OPEN]** are undecided and up for discussion.

## 1. Goal

A textual language for describing furniture: its parts, how they are joined,
how their shapes are constrained, and how they are made and assembled.
From one source file, a tool should produce:

- a 3D model (for viewing and rendering),
- a cut list and shopping list,
- 2D drawings of each part with its joinery,
- step-by-step manufacturing and assembly instructions.

The text should be easy for humans and LLMs to read, write, diff, and
parametrize ("make it 20 cm wider", "use 18 mm plywood instead").

## 2. Core insight: woodworkers think in joints, not coordinates

In generic CAD you model solids and position them in space. A woodworker
works differently:

- starts from **stock** (a board of some thickness, a sheet of plywood),
- relates parts through **joints** ("the apron is tenoned into the leg,
  set back 5 mm from its outside face"),
- measures from **reference faces** and uses **flush/offset** relations,
  not absolute coordinates.

So the language should work the same way:

1. **A joint is a first-class relation that modifies *both* parts.** Declaring
   a mortise-and-tenon between rail and stile makes the tool cut the mortise
   into the stile, form the tenon on the rail, and lengthen the rail by the
   tenon length. The user states intent; the tool derives the features.
2. **Placement follows from joints and alignment relations.** If every part
   is connected to the assembly through joints, its position in 3D can be
   computed. Absolute coordinates should be rare.
3. **Visible dimensions and cut dimensions are different.** The user says
   "opening between legs is 600 mm". The tool works out that the apron is
   600 + 2 × tenon length long.

That is the gap between this language and CSG/OpenSCAD. CSG describes *what
the solid is*, while this language should describe *why it is that shape*.
CSG (or a B-rep kernel) is still what the tool uses to build the actual
geometry.

## 3. The pipeline: four layers

```
 ┌──────────────────────┐
 │ 1. Design intent     │  authored by the user (text)
 │  params, parts,      │
 │  joints, relations   │
 └─────────┬────────────┘
           │ resolve (evaluate expressions, apply joint rules, place parts)
 ┌─────────▼────────────┐
 │ 2. Resolved model    │  computed; every part has concrete cut dimensions,
 │  parts + features +  │  features (mortise, tenon, hole, dado...),
 │  placements          │  and a transform in the assembly
 └─────────┬────────────┘
           │ plan (derive operations, order them, lay out stock)
 ┌─────────▼────────────┐
 │ 3. Process plan      │  computed, with user overrides: stock layout,
 │  operations graph    │  per-part operations, sub-assemblies,
 │                      │  glue-up order, finishing
 └─────────┬────────────┘
           │ export
 ┌─────────▼────────────┐
 │ 4. Outputs           │  3D (STEP/glTF/STL), renders, part drawings (SVG/PDF),
 │                      │  cut list (CSV), instructions (Markdown/HTML)
 └──────────────────────┘
```

Each layer should be inspectable and serializable, as a text file too.
That helps with debugging, testing, and feeding the result to an LLM
("here's the resolved model, why is this apron 3 mm too short?").

## 4. Who specifies what

| Concern | User specifies | Tool computes |
|---|---|---|
| Overall size | Key dimensions and parameters (height, width, depth, overhang) | Derived dimensions via expressions |
| Materials | Species, stock thickness, sheet goods | Grain direction defaults, board feet / area |
| Parts | Role, stock, key dimensions, which face is the reference | Final cut dimensions including joinery allowances |
| Joints | Type, which faces/ends meet, alignment (flush, offset, centered) | Joint geometry from rules of thumb (e.g. tenon = ⅓ thickness), overridable |
| Placement | Almost nothing, only the root part or overall orientation | All part transforms, from joint and alignment relations |
| Validation | Tolerances, warnings to ignore | Interference, joint fit, cross-grain gluing, stock limits, assembly feasibility |
| Stock usage | Available stock (board sizes, sheets) or "buy standard" | Cut layout / nesting, waste, shopping list |
| Process | Tools available (hand/power/CNC), preferences, sub-assembly grouping if desired | Operations per part, ordering, glue-up sequence, dry-fit points |
| Finish | Finish type, which surfaces | When to finish (e.g. before glue-up for inside corners) |

Rule of thumb: **the user writes decisions, and the tool derives consequences.**
Every derived value should be overridable, so the tool suggests and the user
can still decide.

## 5. Language building blocks (tentative)

- **Parameters and expressions**: named values with units
  (`leg_thickness: 45mm`, `apron.length: width - 2*leg_inset`). They are
  evaluated in one direction, like a spreadsheet. See §7.
- **Materials / stock**: `board(thickness: 20mm, species: oak)`,
  `sheet(plywood, 18mm)`. They carry grain direction and nominal vs actual sizes.
- **Parts**: an instance of stock with a role and dimensions. Each part has
  a local frame tied to the grain (see §6).
- **Features**: shape modifications on one part (hole, chamfer, rebate,
  dado, taper, arbitrary cut). Joints generate most of them, and users can
  add their own.
- **Joints**: a relation between two (or more) parts that generates features
  on each. They come from a standard library: butt, dowel, screw, pocket
  screw, rebate, dado, groove, mortise-and-tenon, bridle, half-lap,
  dovetail, box joint, biscuit/domino, hardware (hinges, slides).
- **Alignment relations**: `flush`, `offset`, `centered`, `inset`, and
  `reveal` between named faces.
- **Components / modules**: reusable, parametric groups (a "frame-and-panel
  door", a "drawer box", a "leg-and-apron end frame"). This is how a standard
  library grows beyond primitives.
- **Process annotations** (optional): sub-assembly grouping, operation
  overrides ("cut this mortise with a router"), finishing steps.

### Illustrative sketch (syntax not decided)

A corner of a frame: a rail tenoned into a stile.

```yaml
params:
  stock_t: 20mm

parts:
  stile: { stock: board, size: [600mm, 60mm, stock_t] }   # L × W × T
  rail:  { stock: board, width: 60mm, thickness: stock_t } # length derived

joints:
  corner:
    type: mortise_tenon
    tenon:   rail.end.left
    mortise: stile.edge.right
    align:
      - flush: [rail.face.front, stile.face.front]
      - flush: [rail.edge.top,   stile.end.top]
    # tenon thickness, length, shoulders: library defaults, overridable
```

The tool then works out the mortise in the stile and the tenon on the rail.
It places the rail relative to the stile and adds the tenon length to the
rail's cut length.

## 6. Coordinate system

Proposal: **named faces on a grain-aligned local frame, and no global
coordinates in normal use.**

- Each board-like part has axes **L** (length, along grain), **W** (width),
  and **T** (thickness).
- Its six faces use woodworking names: `face.front/back` (the wide faces),
  `edge.top/bottom` (the long narrow faces), and `end.left/right` (end grain).
  The user can choose a **reference face/edge**, the same idea as the pencil
  marks in the shop.
- The whole assembly has one global frame (X = width, Y = depth, Z = height)
  that you only need for orienting the root and for export.
- Positions *along* a face are given as offsets from named faces/ends
  ("50 mm from `stile.end.left`").

Geometric algebra could be a clean internal representation for transforms
and incidence. Users don't need to see it, though. **[OPEN]** Start with
ordinary rigid transforms internally and revisit if they get awkward.

Sheet goods (plywood) and non-rectangular parts (tapered legs, curved
aprons) need the same naming idea applied to a different base shape.
**[OPEN]**

## 7. Constraints

Two levels:

1. **Directed expressions** (spreadsheet-like): `rail.length = opening + 2*tenon.length`.
   Simple to implement, predictable, and easy to explain. Covers most
   furniture.
2. **Declarative constraints** that need a solver: "these three shelves are
   equally spaced and the middle one is at elbow height". This is more
   powerful, but under- and over-constrained systems are hard to report
   to users in an understandable way.

Proposal: start with (1). Joints and alignment relations are themselves
*directed*, because they propagate position from a parent part to a child
along the joint graph. Add (2) only if real examples demand it.
**[OPEN]** What happens when the joint graph has cycles (a box, a frame)?
The loop must close consistently. That makes a good early test of the design.

## 8. Wood-specific concerns (where generic CAD falls short)

- Grain direction per part, and checks for cross-grain construction
  (wood movement: a solid top glued rigidly across an apron will crack).
- Nominal vs actual stock sizes; rough vs milled dimensions.
- Saw kerf, milling allowances, and tolerances for joint fit.
- Stock yield: laying parts out on real boards, including matching
  grain/colour for visible parts.
- Assembly feasibility: can this part physically be inserted after that
  one? Glue open time and how many joints get glued at once.
- Finishing order (some surfaces are easier to finish before assembly).

## 9. Outputs

| Output | Approach (tentative) |
|---|---|
| 3D model | Generate geometry with an existing B-rep/CSG kernel (e.g. build123d/CadQuery on OpenCascade, or OpenSCAD), export STEP/STL/glTF |
| Images | Render glTF (Blender, three.js viewer) |
| Part drawings | Orthographic projections per part with dimensions (SVG/PDF) |
| Cut list | Table of parts with cut dimensions, material, grain, count (CSV/Markdown) |
| Stock layout | Nesting of parts onto boards/sheets (SVG) |
| Instructions | Ordered steps built from the process graph, with images per step (Markdown/HTML) |
| Later | CNC toolpaths, structural analysis, cost estimate |

We don't write a geometry kernel.

## 10. Syntax **[OPEN]**

The semantic model (§5) matters more than surface syntax. Design the model
first, then choose a syntax. Options:

| Option | Pros | Cons |
|---|---|---|
| YAML + expression strings | Familiar, tooling and JSON Schema exist, LLMs write it well | Expressions and references live inside strings; YAML quirks; no reuse or loops without templating |
| Config languages with expressions (CUE, Pkl, Jsonnet, KCL-style) | Expressions, references, validation built in | Less familiar, extra dependency |
| Embedded DSL in Python (like build123d) | Fastest to prototype, full power, easy debugging | Not a "document"; harder to analyse, less friendly to non-programmers |
| Custom syntax | Can be exactly right | Parser, editor support, and error messages are all on us |

Current lean: build the core as a **Python library** (the semantic model +
resolver + exporters) and put a **YAML front-end** with a small expression
language on top. Revisit after writing the example corpus in more than one
syntax.

## 11. Validation ladder

Each step is a real example that must go end-to-end (text → 3D + cut list,
and later instructions) before we move on. Together these examples become
the test suite.

1. **Single board**: stock, dimensions, cut list entry, 3D box.
2. **Butt joint with screws**: two parts, placement derived from the joint.
3. **Rebate / dado / groove**: a joint that generates a feature on one part only.
4. **Mortise and tenon**: features on both parts, derived lengths, defaults + overrides.
5. **Half-lap, bridle, dovetail**: more joint types; checks the joint abstraction.
6. **Box / frame**: a closed loop in the joint graph.
7. **Stool**: first 3D structure, sub-assemblies, glue-up order.
8. **Table**: legs, aprons, top attached with wood movement in mind.
9. **Cabinet**: carcass (sheet goods), shelves, back panel, door, drawer.
10. **Build a real piece** from the generated instructions.

## 12. Non-goals (for now)

- Freeform/organic shapes (carving, steam bending, turned parts beyond simple profiles).
- CNC toolpath generation.
- A general constraint solver.
- Upholstery, metalwork, hardware beyond a small catalog.

## 13. Open questions

- Hand tools, power tools, CNC: which workshop do the generated instructions assume? Configurable?
- Units: metric first? Imperial fractions (`3/4"`)?
- How are non-board parts (turned legs, curved parts, plywood with edge banding) modelled?
- Should joints be binary (two parts), or can one joint connect several (a three-way leg-apron corner)?
- How much of the process plan is derived vs authored? Is the user's grouping of sub-assemblies input or output?
- How does the standard library get extended? In the language itself, or in Python?
- Versioning of the language and library defaults (a changed default shouldn't silently change old designs).

## 14. Prior art to study

- **OpenSCAD**: text-based CSG; the baseline for "furniture in text".
- **CadQuery / build123d**: Python CAD on OpenCascade; likely geometry backend.
- **Zoo KCL**: a recent purpose-built CAD language.
- **FreeCAD** (incl. woodworking add-ons), **SketchUp + OpenCutList**: how woodworkers do cut lists today.
- **Tsugite** (Larsson et al., 2020): research on interactive design of wood joints.
- Parametric CAD assembly constraints (Fusion 360, Onshape mates): prior art for mate/alignment relations.
