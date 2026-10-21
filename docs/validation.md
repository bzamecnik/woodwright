# Validation catalogue

Cuts, joints and pieces that could eventually make up the standard library.
Not every item needs an example; see [plan.md](plan.md#6-roadmap) for the order
in which they are tackled and [vision.md](vision.md#11-scope) for the current scope.

Done items name their example in `woodwright.examples`
(`woodwright list`).

- single piece in different dimensions
  - [x] rectangular board
  - [x] cylindrical dowel/rod – `Rod`, `Stock.rod`: `cuts.rod`
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
  - stopped cuts - stopping short of one or both ends, so they don't show there
    - [x] stopped groove – `cuts.stopped_groove`, in the stiles of `frames.butt_frame_and_panel`
    - [x] stopped dado – `joints.stopped_dado_shelf`
    - [x] stopped rabbet – `cuts.stopped_rabbet`
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
  - [x] end chamfer - around the end of a board or a rod (a cone) – `cuts.chamfered_foot`,
    `cuts.dowel`
  - drilled hole – `Hole`
    - [x] through – `cuts.through_hole`
    - [x] blind – flat-bottomed or with a drill point: `cuts.blind_hole`, `cuts.shelf_pin_holes`,
      in an edge and an end: `cuts.dowel_holes`
    - [x] chamfered hole (countersink) – `cuts.countersunk_hole`
    - [x] counterbored hole - for a screw head and a plug – `cuts.counterbored_hole`
    - [x] tapered (reamed) hole – `cuts.tapered_hole` (straight; splayed holes later)
    - [x] holes in a rod - a cross hole and one into its end – `cuts.drilled_rod`
  - cuts on round stock
    - [x] round taper - a cone, as turned – `cuts.round_tapered_leg`, `cuts.tapered_rod`
    - [x] point - a peg or a stake – `cuts.peg`
    - [x] flat taper - a sloping plane on one side – `cuts.flat_tapered_dowel`
    - [x] flat - a rod ripped or planed flat along its length – `cuts.half_dowel`,
      stopped: `cuts.rod_with_flats`
    - [x] end mitre – `cuts.mitred_rod`
- joints
  - butt joint (glued)
    - [x] edges - panel – `joints.butt_panel`
    - [x] faces - thick leg – `joints.laminated_leg`; a laminated board cut as one after the
      glue-up, its plies in the model and the cut list – `Board(plies=2)`, the legs and rails
      in `projects.workbench`
    - perpendicular
      - [x] face on face - bench hook (across the grain) – `projects.bench_hook`
      - [x] edge on face - corner – `joints.butt_corner`, `joints.butt_frame_corner`
    - [x] box - four corner joint + bottom – `projects.butt_box`
    - [x] shelf with just butt joints – `projects.butt_shelf` (screws not modelled)
    - [x] ledged and braced door - boards butted edge to edge, two ledges and a diagonal brace
      face to face on the back, the brace's ends cut level against the ledges' edges –
      `projects.ledged_and_braced_door` (nails not modelled)
  - dado
    - [x] T-joint with a dado – `joints.dado_shelf`, `projects.shooting_board`
    - [x] T-joint with a stopped dado, the shelf's front corner notched to the stop –
      `joints.stopped_dado_shelf`
    - [x] shelf with dados – `projects.bookshelf`
  - groove
    - [x] tongue and groove panel - tongue + groove – `joints.tongue_and_groove_panel`,
      V-chamfered boards on two ledges: `projects.ledged_door`
    - [x] tongue and groove panel - two grooves + inserted tongue – `LooseTongue`,
      `joints.loose_tongue_panel` (the tongues' grain along the joints, in stopped grooves)
    - [x] frame panel - butt-joint frame with a groove inside, panel with a tongue on all edges –
      `frames.butt_frame_and_panel` (the grooves in the stiles stopped where the rails' end;
      a mortise-and-tenon frame with a plain panel: `frames.frame_and_panel`,
      `joints.panel_in_groove`)
    - [x] frame-and-panel door, 2 x 2 raised panels - stiles, three rails and two muntins,
      haunched mortise and tenons, grooves through along the inside edges, panels bevelled on
      the front right out to the edges, as thick as the grooves are wide at their mouths,
      floating in the grooves – `projects.frame_and_panel_door`
    - [x] small cabinet door, 2 x 3 cm stock - stiles and three rails with mitred shoulder
      tenons (through at the corners, a stub in the middle), grooves through along the inside
      edges meeting at the mitres and hidden in the notches, panels of plywood and glass as
      thick as the grooves are wide – `projects.cabinet_door`
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
    - keyed mitre (slip feathers) - kerfs across the outside corner, square to its arris, thin
      keys glued in and trimmed flush (showing as triangles)
      - [ ] picture frame corner, one key; box corner, several keys
      - [ ] kerfs tilted, of varying depths
      - [ ] dovetail keys
    - splined mitre - a loose tongue across the mitre, in grooves square to the mitre faces
      - [ ] along the corner: through in a box corner, several in a row on a wide shelf corner
      - [ ] along the mitre line: hidden in a picture frame corner
  - butterfly key (bow tie) - a shallow bow-tie mortise in a face, a key inlaid flush
    - [ ] across a crack in a board
    - [ ] across the joint of two boards
  - lap joint
    - [x] two boards with overlapping rabbets to make panel – `joints.shiplap_panel` (three boards)
    - [x] half-lap corner - two perpendicular boards with "endgrain rabbet" – `joints.half_lap_corner`
    - [x] half-lap T - one board with dado, other board with "endgrain rabbet" – `joints.half_lap_t`
    - [x] partly let in: a square rail lapped to half its thickness across a leg of the same
      section, the leg notched a quarter, the rail standing out by a quarter –
      `HalfLap(proud=...)`, `joints.let_in_rail`
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
      - [x] four pieces - hollow leg – `joints.hollow_leg` (edges mitred along the grain,
        `MitreCorner` of two edges)
  - dowel joint – `Dowels`
    - [x] two boards with blind drill holes + dowel – `joints.dowelled_edge_joint`,
      `joints.dowelled_frame_corner`
    - [ ] one board with a blind hole, one with open hole + dowel
    - [x] board with a hole + bigger rod – `RoundMortiseTenon`, `joints.rod_in_hole`,
      `frames.ladder`
  - mitred half-lap
    - [x] like a half-lap corner, but one side is mitred – `MitredHalfLap`,
      `joints.mitred_half_lap` (the front half mitred, the back half lapped)
  - dovetailed half-lap
    - [x] like a half-lap T-joint, but the open tenon side is dovetailed out, not straight –
      `DovetailHalfLap`, `joints.dovetail_half_lap` (at a corner a half dovetail, sloped at
      the inner edge)
    - [x] partly let in, the lap a half dovetail (flat at the bottom, sloped at the top), in a
      notch open at the end of the leg – `joints.let_in_dovetail_rail`; stopped short of the
      end of the leg, the tail cut back from the rail's edge – `DovetailHalfLap(stopped=...)`,
      in `projects.workbench`
  - wedged mortise and tenon
    - [x] through half-dovetail mortise with edges angled outward – `WedgedMortiseTenon`,
      `joints.wedged_through_tenon`
    - [x] tenon with one or two slots ended with a drilled hole + wedge – one or two kerfs per
      tenon, the wedges as parts, in `joints.wedged_through_tenon` (the drilled hole not yet)
  - pegged mortise and tenon – `PeggedMortiseTenon`
    - [x] pinned: a peg through the mortised part and the tenon – `joints.pinned_mortise_tenon`
    - [x] drawbored: the hole in the tenon slightly offset towards the shoulder (noted, shown
      assembled) – `joints.drawbored_mortise_tenon`
  - [x] tusk mortise and tenon – `TuskTenon`
    - tenon extends out of the through mortise
    - there's another smaller mortise going through the tenon
    - a wedge goes through the second mortise
    - [x] the wedge parallel to the stile (upright, through the tenon's width) –
      `joints.tusk_tenon`
    - [x] the wedge perpendicular to the stile (level, through the tenon's thickness) –
      `joints.tusk_tenon_flat`
    - the second mortise can go through the face or through the edge
    - [x] dowel tusks (after Rex Krueger): dowels with a flat tapered at their tips through
      straight holes in the tenon (two in its second and fourth fifth), the flats bearing on the
      round top of a half dowel glued flat side down across the leg – `DowelTuskTenon`,
      `joints.dowel_tusk_tenon`
  - [x] stub tenon - L-joint, mortise offset from the endgrain, tenon has three shoulders –
    `joints.stub_tenon_corner` (no inner shoulder, a plain outer one, no haunch)
  - [x] haunched tenon - a short, shallow continuation of the tenon in a haunch mortise running
    out of the end of the mortised part – `joints.haunched_mortise_tenon_corner` (a small inner
    shoulder, the haunch on the outer edge), `frames.frame_and_panel` (filling the groove)
  - [x] haunched stub tenon - combination of stub tenon and haunched tenon –
    `joints.haunched_stub_tenon_corner` (no inner shoulder, the haunch on the outer edge)
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
    - [x] L-joint (mitred face tenon) – `MitredFaceTenon`, `joints.mitred_face_tenon_corner`
      (the front third mitred; behind it the rail butts square against the stile, with a
      hidden tenon centered in the layer behind the mitre, in a blind mortise)
    - [ ] 3-way joint: two outer tenons, the outer one pointed, the inner one mitred at its edge
      so the two perpendicular rails don't clash
  - round tenon – `RoundTenon`, `RoundMortiseTenon`
    - [x] mortise is a drilled hole, tenon is round – on a rod: `cuts.round_tenon`,
      `joints.round_mortise_tenon`, into a round leg: `joints.round_tenon_in_round_leg`; on
      square stock: `cuts.round_tenon_on_square`, through: `joints.through_round_tenon`
    - [x] tapered, in a reamed hole (Windsor) – `joints.tapered_round_tenon` (not splayed yet)
    - [x] can be wedged – `WedgedRoundMortiseTenon`, `joints.wedged_round_tenon`
  - screws (the screws themselves not modelled) – `Screw`
    - [x] countersunk clearance hole + pilot hole – `joints.screwed_batten`
    - [x] counterbored for a plug – `joints.plugged_screws`
    - [x] in projects: buttons screwed to a table's top (`projects.table`,
      `projects.side_table`), the ledges of a door to its boards (`projects.ledged_door`)
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
  - [x] step stool with sliding dovetail cross pieces and legs with wedged round tenons –
    `projects.stepstool` (straight round legs through the battens and the seat, round
    stretchers at the sides)
    - [ ] angled (splayed) legs
  - [x] stool with round legs wedged through a solid seat, round stretchers – `projects.stool`
    (straight legs)
  - [x] coat rack with round pegs in blind holes, counterbored screw holes for the wall –
    `projects.coat_rack`
  - [x] workbench, after Rex Krueger's Quick Stack – `projects.workbench`
    - two leg assemblies, beams glued up from boards, then half-laps (legs and rails each
      laminated from two 45 mm boards, the legs' glue lines on the sides, the rails' upright;
      rails lapped and let in partly, the upper ones half-dovetailed)
    - stretchers with through tusk tenons (dowel tusks, big chamfers at the tenons' corners –
      `MortiseTenon(tenon_corner_chamfer=...)`)
    - desk (covering the front half) made of beams glued up by face
    - drawer (covering the back half): a tray with the bottom between its walls, flush with
      their lower edges, to be used either way up
    - top and tray located on the upper rails by dowels (holes in both edges of the tray's
      walls for turning it over)
