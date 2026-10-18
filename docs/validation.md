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
  - [x] taper - a face or an edge planed at a slope – `cuts.wedge`, `cuts.tapered_leg`,
    a drawer bottom tapered on its underside to fit grooves: `cuts.tapered_panel`
  - [x] groove - partial rip cut – `cuts.groove`
  - [x] dado - partial cross cut – `cuts.dado`
  - [x] rabbet - groove at the edge of the board, groove from two faces – `cuts.rabbet`,
    `cuts.rabbeted_panel`
  - [x] "endgrain rabbet" - dado at the end of the board – `cuts.end_rabbet`
  - [x] slot mortise - "endgrain groove", like a groove but open at the endgrain side –
    `cuts.slot_mortise`
  - [x] tongue - rabbets at the edge from two opposite faces – `cuts.tongue`
  - mortise - a hole through the board across the grain
    - [x] through mortise – `cuts.mortise(depth=60)`, `joints.through_mortise_tenon`
    - [x] blind mortise - not all the way through the board – `cuts.mortise`
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
      - [x] face on face - bench hook (across the grain) – `projects.bench_hook`
      - [x] edge on face - corner – `joints.butt_corner`, `joints.butt_frame_corner`
    - [x] box - four corner joint + bottom – `projects.butt_box`
    - [x] shelf with just butt joints – `projects.butt_shelf` (screws not modelled)
  - dado
    - [x] T-joint with a dado – `joints.dado_shelf`, `projects.shooting_board`
    - [x] shelf with dados – `projects.bookshelf`
  - groove
    - [x] tongue and groove panel - tongue + groove – `joints.tongue_and_groove_panel`,
      V-chamfered boards on two ledges: `projects.ledged_door`
    - [ ] tongue and groove panel - two grooves + inserted tongue
    - [x] frame panel - butt-joint frame with a groove inside, panel with a tongue on all edges –
      `frames.butt_frame_and_panel` (the grooves through, showing at the stiles' ends;
      a mortise-and-tenon frame with a plain panel: `frames.frame_and_panel`,
      `joints.panel_in_groove`)
  - rabbet
    - [x] corner with rabbet and plain board – `joints.rabbet_corner`, `projects.bookshelf`
    - [x] corner with two interlocking rabbets – `joints.interlocking_rabbet_corner`
    - [x] box with rabbet corners and rabbetted bottom – `projects.rabbeted_box`
  - mitre joint - "butt" joint of two mitred boards
    - two pieces
      - [x] perpendicular L corner – `joints.mitre_corner`
      - [x] splice (mitre along the face, mitre along the edge) – `joints.mitre_splice`
    - [x] four pieces - picture frame – `projects.picture_frame`
    - [x] mitred frame with a panel glued up from boards, tongued into a groove along the
      inside edges (the grooves run out at the mitres) – `frames.mitred_frame_and_panel`
  - lap joint
    - [x] two boards with overlapping rabbets to make panel – `joints.shiplap_panel` (three boards)
    - [x] half-lap corner - two perpendicular boards with "endgrain rabbet" – `joints.half_lap_corner`
    - [x] half-lap T - one board with dado, other board with "endgrain rabbet" – `joints.half_lap_t`
    - [x] picture frame – `frames.half_lap_frame`
    - [x] cross lap - two boards crossing, each with a dado – `joints.cross_lap`
    - [x] shoji frame – `frames.shoji_frame` (3 x 3 bars, 5 x 20 mm, nine cross laps)
    - [ ] angled half-lap joint
  - bridle joint
    - [x] L-joint - one board with a deep slot mortise, one board with a two-sided tenon –
      `joints.bridle_corner`, `frames.bridle_frame`
      - [x] shop square – `projects.try_square`
    - [x] T-joint - slot mortise, two dados – `TeeBridle`, `joints.bridle_t`
  - mortise and tenon - one board with a tenon mortise, another with tenon
    - [x] mallet – `projects.mallet`
    - [x] frame for a bow saw (two tenons) – `projects.bow_saw_frame`
    - [x] blind mortise – `joints.mortise_tenon`, `frames.mortise_tenon_frame`
    - [x] tenon extending out of the through mortise – `joints.protruding_through_mortise_tenon`,
      only its chamfered end proud: `joints.chamfered_through_mortise_tenon`
    - [x] multiple tenon – `MortiseTenon(tenons=2)`, twin tenons on a wide rail:
      `joints.twin_tenon_corner`; across the thickness (`thickness_tenons=2`) on a thick,
      square rail: `joints.thick_rail_tenons`, a 2 x 2 grid: `joints.square_rail_four_tenons`
    - [x] table leg accepting two perpendicular tenons with mitred ends –
      `joints.leg_and_aprons_mitred` (short tenons without mitres: `joints.leg_and_aprons`)
  - [x] box joint - both boards have a set of shallow regular slot mortises of equal widths –
    `BoxJoint`, `joints.box_joint_corner`
  - [x] sliding dovetail - one board with dovetail groove, another with dovetail tongue –
    `joints.sliding_dovetail_shelf`
    - [x] two butt-joined boards with a two sliding dovetail cross-pieces (seat of a stepstool) –
      `projects.stepstool_seat` (wide battens lying flat, their whole width in a shallow
      housing with bevelled edges, each housed in both boards, the housings through)
  - dovetail - similar to box joint, but the slot mortises are angled
    - [x] two boards (corner) – `joints.dovetail_corner`
    - [x] shelf with dovetailed corners – `projects.dovetail_shelf` (two stories)
    - [x] drawer with dovetailed corners with a groove and rabbeted bottom – `projects.drawer`
      (half-blind at the front, through at the back; through at all four corners without a
      bottom: `projects.dovetail_drawer`)
    - [x] dovetail with mitred corner – `MitredCornerDovetail`, `joints.mitred_dovetail_corner`
      (mitred at both edges, hiding the grooves for the top and the bottom of a box)
  - chamfer joint
    - full 45˚ chamfer
      - [x] two pieces - long L-shaped piece – `joints.edge_mitre_corner`
      - [ ] four pieces - hollow leg
  - dowel joint
    - [ ] two boards with blind drill holes + dowel
    - [ ] one board with a blind hole, one with open hole + dowel
    - [ ] board with a hole + bigger rod
  - mitred half-lap
    - [x] like a half-lap corner, but one side is mitred – `MitredHalfLap`,
      `joints.mitred_half_lap` (the front half mitred, the back half lapped)
  - dovetailed half-lap
    - [x] like a half-lap T-joint, but the open tenon side is dovetailed out, not straight –
      `DovetailHalfLap`, `joints.dovetail_half_lap` (at a corner a half dovetail, sloped at
      the inner edge)
  - wedged mortise and tenon
    - [x] through half-dovetail mortise with edges angled outward – `WedgedMortiseTenon`,
      `joints.wedged_through_tenon`
    - [x] tenon with one or two slots ended with a drilled hole + wedge – one or two kerfs per
      tenon, the wedges as parts, in `joints.wedged_through_tenon` (the drilled hole not yet)
  - drawbore mortise and tenon
    - [ ] mortise and tenon plus each has a drill hole which is slightly offset + dowel
  - [ ] tusk mortise and tenon
    - tenon extends out of the through mortise
    - there's another smaller mortise going through the tenon
    - a wedge goes through the second mortise
    - the second mortise can go through the face or through the edge
  - [x] stub tenon - L-joint, mortise offset from the endgrain, tenon has three shoulders –
    `joints.stub_tenon_corner`
  - [x] haunched tenon - a stub filling a groove that runs out of the mortised part –
    `joints.haunched_mortise_tenon_corner` (a small inner shoulder, the haunch on the outer edge),
    `frames.frame_and_panel`
  - [x] haunched stub tenon - combination of stub tenon and haunched tenon –
    `joints.haunched_stub_tenon_corner` (a short tenon, a wide haunched outer shoulder)
  - [x] loose tenon - two blind mortises, tenon is a separate piece – `LooseTenon`,
    `joints.loose_tenon`
  - mitred shoulder tenon - the tenoned board reaches into a notch in the mortised one, mitred
    at 45° part way (e.g. a third) into it; for square-ish stock
    - [x] T-joint, mitred at both edges, stub tenon – `joints.mitred_shoulder_tenon`
    - [x] L-joint, mitred at the inner edge, through tenon – `joints.mitred_shoulder_corner`
  - sword-hilt tenon ("ken-dome"; Western: mitred face tenon) - the outer cheeks of the tenoned
    board pointed into the face of the mortised one, like a bridle with an inner (twin) tenon;
    for square stock. Postponed until Japanese joinery is tackled (a first attempt with a pointed
    face layer is kept on the branch `joint/sword-hilt`)
    - [ ] T-joint, pointed on both faces, inner tenon or twin tenon ("nimai-hozo")
    - [ ] pointed on one face only, the inner tenon off-center (the rest in thirds)
    - [ ] L-joint (mitred face tenon)
    - [ ] 3-way joint: two outer tenons, the outer one pointed, the inner one mitred at its edge
      so the two perpendicular rails don't clash
  - round tenon
    - [ ] mortise is a drilled hole, tenon is round
    - [ ] can be wedged
  - [x] half-blind dovetail – `joints.half_blind_dovetail_corner`, `projects.drawer`
  - [x] blind mitred dovetail – `BlindMitredDovetail`, `joints.blind_mitred_dovetail_corner`
    (secret mitre: mitred lips on both boards, the edges mitred through)
  - kumiko asanoha pattern
    - [ ] 3-way mitre joint
- furniture (besides example above)
  - [x] table with four legs, wide aprons with stub tenon joint, panel desk
    (so far `projects.table`: wide aprons with haunched, mitred tenons, a top glued up from
    boards held by buttons in short mortises in the aprons; `projects.table_frame` without a top)
  - [x] side table with aprons and stretchers – `projects.side_table` (aprons as in
    `projects.table`, stretchers at the same level with blind, mitred tenons meeting inside the
    legs, a top glued up from boards held by buttons)
  - [x] simple square chair frame: seat rails as in a table, stretchers and back rails with
    chamfered through tenons, chamfered tops of the back legs – `projects.chair` (a seat glued up
    from two boards, notched around the back legs and chamfered, splats with blind tenons
    between the back rails, legs tapered on the inside)
  - [ ] step stool with sliding dovetail cross pieces and angled legs with wedged round tenons
  - [ ] workbench
    - two leg assemblies, beams glued up from boards, then half-laps
    - stretchers with trough tusk tenons
    - desk (covering the front half) made of beams glued up by face
    - drawer (covering the back half)
