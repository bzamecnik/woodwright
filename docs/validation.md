# Validation catalogue

Cuts, joints and pieces that could eventually make up the standard library.
Not every item needs an example; see [plan.md](plan.md#6-roadmap) for the order
in which they are tackled and [vision.md](vision.md#11-scope) for the current scope.

Done items name their example in `woodwright.examples`
(`python -m woodwright.examples list`).

- single piece in different dimensions
  - [x] rectangular board
  - [ ] cylindrical dowel/rod
- cuts
  - [x] cross - across the grain (implicit: a `Board` is cut to size)
  - [x] rip - along the grain (implicit: a `Board` is cut to size)
  - [x] mitre - angled cross cut – `cuts.mitre`, `cuts.edge_mitre`
  - [x] chamfer - angled rip cut – `cuts.chamfer`
  - [x] taper - a face or an edge planed at a slope – `cuts.wedge`, `cuts.tapered_leg`
  - [x] groove - partial rip cut – `cuts.groove`
  - [x] dado - partial cross cut – `cuts.dado`
  - [x] rabbet - groove at the edge of the board, groove from two faces – `cuts.rabbet`,
    `cuts.rabbeted_panel`
  - [x] "endgrain rabbet" - dado at the end of the board – `cuts.end_rabbet`
  - [x] slot mortise - "endgrain groove", like a groove but open at the endgrain side –
    `cuts.slot_mortise`
  - [x] tongue - rabbets at the edge from two opposite faces – `cuts.tongue`
  - mortise - a hole through the board across the grain
    - [x] through mortice – `cuts.mortise(depth=60)`, `joints.through_mortise_tenon`
    - [x] blind mortice - not all the way through the board – `cuts.mortise`
  - [x] tenon - "endgrain rabbet" from multiple sides at once – `cuts.tenon`
  - [x] dovetail dado - dado where the sides are not perpendicular, but angled inward –
    derived by `SlidingDovetail`, in `joints.sliding_dovetail_shelf`
  - [x] dovetail tongue - tongue where the sides are not perpendicular, but angled outward –
    `DovetailTongue`, in `joints.sliding_dovetail_shelf`
  - drilled hole
    - [ ] through
    - [ ] blind
    - [ ] chamfered hole (countersink)
- joints
  - butt joint (glued)
    - [x] edges - panel – `joints.butt_panel`
    - [x] faces - thick leg – `joints.laminated_leg`
    - perpendicular
      - [ ] face on face - bench hook
      - [x] edge on face - corner – `joints.butt_corner`, `joints.butt_frame_corner`
    - [x] box - four corner joint + bottom – `projects.butt_box`
    - [ ] shelf with just butt joints
  - dado
    - [x] T-joint with a dado – `joints.dado_shelf`, `projects.shooting_board`
    - [x] shelf with dados – `projects.bookshelf`
  - groove
    - [x] tongue and groove panel - tongue + groove – `joints.tongue_and_groove_panel`
    - [ ] tongue and groove panel - two grooves + inserted tongue
    - [ ] frame panel - butt-joint frame with a groove inside, panel with a tongue on all edges
      (so far `frames.frame_and_panel`: a mortise-and-tenon frame, a plain panel;
      `joints.panel_in_groove`)
  - rabbet
    - [x] corner with rabbet and plain board – `joints.rabbet_corner`, `projects.bookshelf`
    - [x] corner with two interlocking rabbets – `joints.interlocking_rabbet_corner`
    - [ ] box with rabbet corners and rabbetted bottom
  - mitre joint - "butt" joint of two mitred boards
    - two pieces
      - [x] perpendicular L corner – `joints.mitre_corner`
      - [x] splice (mitre along the face, mitre along the edge) – `joints.mitre_splice`
    - [x] four pieces - picture frame – `projects.picture_frame`
  - lap joint
    - [ ] two boards with overlapping rabbets to make panel
    - [x] half-lap corner - two perpendicular boards with "endgrain rabbet" – `joints.half_lap_corner`
    - [x] half-lap T - one board with dado, other board with "endgrain rabbet" – `joints.half_lap_t`
    - [x] picture frame – `frames.half_lap_frame`
    - [x] cross lap - two boards crossing, each with a dado – `joints.cross_lap`
    - [ ] shoji frame
    - [ ] angled half-lap joint
  - bridle joint
    - [x] L-joint - one board with a deep slot mortise, one board with a two-sided tenon –
      `joints.bridle_corner`, `frames.bridle_frame`
      - [x] shop square – `projects.try_square`
    - [ ] T-joint - slot mortise, two dados
  - mortise and tenon - one board with a tenon mortise, another with tenon
    - [x] mallet – `projects.mallet`
    - [ ] frame for a bow saw (two tenons)
    - [x] blind mortice – `joints.mortise_tenon`, `frames.mortise_tenon_frame`
    - [ ] tenon extending out of the through mortice
    - [ ] multiple tenon
    - [x] table leg accepting two perpendicular tenons with mitred ends –
      `joints.leg_and_aprons_mitred` (short tenons without mitres: `joints.leg_and_aprons`)
  - [ ] box joint - both boards have a set of shallow regular slot motrices of equal widths
  - [x] sliding dovetail - one board with dovetail groove, another with dovetail tongue –
    `joints.sliding_dovetail_shelf`
  - dovetail - similar to box joint, but the slot mortices are angled
    - [x] two boards (corner) – `joints.dovetail_corner`
    - [ ] shelf with dovetailed corners
    - [ ] drawer with dovetailed corners with a groove and rabbeted bottom
      (so far `projects.dovetail_drawer`: pins on the front and back, tails on the sides,
      without a groove and a bottom)
    - [ ] dovetail with mitred corner
  - chamfer joint
    - full 45˚ chamfer
      - [x] two pieces - long L-shaped piece – `joints.edge_mitre_corner`
      - [ ] four pieces - hollow leg
  - dowel joint
    - [ ] two boards with blind drill holes + dowel
    - [ ] one board with a blind hole, one with open hole + dowel
    - [ ] board with a hole + bigger rod
  - half-lap mitre
    - [ ] like a half-lap corner, but one side is mitred
  - half-lap dovetail
    - [ ] like a half-lap T-joint, but the
  - wedged mortice and tenon
    - [ ] through half-dovetail mortice with edges angled outward
    - [ ] tenon with one or two slots ended with a drilled hole + wedge
  - drawbore mortice and tenon
    - [ ] mortice and tenon plus each has a drill hole which is slightly offset + dowel
  - [ ] tusk mortice and tenon
    - tenon extends out of the through mortice
    - there's another smaller mortice going through the tenon
    - a wedge goes through the second mortice
    - the second mortice can go through the face or through the edge
  - [ ] stub tenon - L-joint, mortice offset from the endgrain, tenon has three shoulders
  - [x] haunched tenon - a stub filling a groove that runs out of the mortised part –
    `joints.haunched_mortise_tenon_corner`, `frames.frame_and_panel`
  - [ ] haunched stub tenon - tenon
  - [ ] loose tenon - two blind mortices, tenon is a separate piece
  - shouldered tenon
    - [ ] T-joint, tenon board extends into the board with the mortice as variants of a triangle
    - [ ] L-joint
  - [ ] mitred face tenon
  - round tenon
    - [ ] mortice is a drilled hole, tenon is round
    - [ ] can be wedged
  - [ ] half-blind dovetail
  - [ ] blind mitred dovetail
  - kumiko asanoha pattern
    - [ ] 3-way mitre joint
- furniture (besides example above)
  - [ ] table with four legs, wide aprons with stub tenon joint, panel desk
    (so far `projects.table_frame`: legs and aprons with mitred tenons, without a top)
  - [ ] side table with aprons and stretchers, desk made as mitre frame with panel inside
  - [ ] step stool with sliding dovetail cross pieces and angled legs with wedged round tenons
  - [ ] workbench
    - two leg assemblies, beams glued up from boards, then half-laps
    - stretchers with trough tusk tenons
    - desk (covering the front half) made of beams glued up by face
    - drawer (covering the back half)
