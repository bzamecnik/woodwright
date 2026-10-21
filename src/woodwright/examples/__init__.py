"""Library of example assemblies, ready to resolve and view.

Each example is a function returning an unresolved `Assembly`, with the
design dimensions as keyword arguments, so it can be resolved as is or built
on. In a notebook:

    from woodwright.examples import frames
    frames.mortise_tenon_frame(rail_length=400).resolve().compound()

From the command line (see `woodwright --help`):

    woodwright list
    woodwright export frames.mortise_tenon_frame
    woodwright export --all
"""

from collections.abc import Callable

from woodwright.assembly import Assembly
from woodwright.examples import cuts, frames, joints, projects

Example = Callable[[], Assembly]

ALL: list[Example] = [
    cuts.dado,
    cuts.groove,
    cuts.stopped_groove,
    cuts.rabbet,
    cuts.stopped_rabbet,
    cuts.end_rabbet,
    cuts.slot_mortise,
    cuts.mortise,
    cuts.tenon,
    cuts.tongue,
    cuts.chamfer,
    cuts.mitre,
    cuts.edge_mitre,
    cuts.rabbeted_panel,
    cuts.tapered_panel,
    cuts.wedge,
    cuts.tapered_leg,
    cuts.through_hole,
    cuts.blind_hole,
    cuts.counterbored_hole,
    cuts.countersunk_hole,
    cuts.tapered_hole,
    cuts.shelf_pin_holes,
    cuts.dowel_holes,
    cuts.chamfered_foot,
    cuts.rod,
    cuts.dowel,
    cuts.peg,
    cuts.round_tapered_leg,
    cuts.tapered_rod,
    cuts.flat_tapered_dowel,
    cuts.half_dowel,
    cuts.rod_with_flats,
    cuts.mitred_rod,
    cuts.drilled_rod,
    cuts.round_tenon,
    cuts.round_tenon_on_square,
    joints.butt_panel,
    joints.laminated_leg,
    joints.butt_corner,
    joints.dado_shelf,
    joints.stopped_dado_shelf,
    joints.rabbet_corner,
    joints.sliding_dovetail_shelf,
    joints.interlocking_rabbet_corner,
    joints.panel_in_groove,
    joints.tongue_and_groove_panel,
    joints.loose_tongue_panel,
    joints.shiplap_panel,
    joints.half_lap_corner,
    joints.half_lap_t,
    joints.dovetail_half_lap,
    joints.let_in_rail,
    joints.let_in_dovetail_rail,
    joints.bridle_corner,
    joints.bridle_t,
    joints.mortise_tenon,
    joints.stub_tenon_corner,
    joints.haunched_mortise_tenon_corner,
    joints.haunched_stub_tenon_corner,
    joints.twin_tenon_corner,
    joints.thick_rail_tenons,
    joints.square_rail_four_tenons,
    joints.leg_and_aprons,
    joints.leg_and_aprons_mitred,
    joints.through_mortise_tenon,
    joints.protruding_through_mortise_tenon,
    joints.chamfered_through_mortise_tenon,
    joints.wedged_through_tenon,
    joints.tusk_tenon,
    joints.tusk_tenon_flat,
    joints.dowel_tusk_tenon,
    joints.mortise_tenon_thin_rail,
    joints.mitred_shoulder_tenon,
    joints.mitred_shoulder_corner,
    joints.loose_tenon,
    joints.box_joint_corner,
    joints.dovetail_corner,
    joints.half_blind_dovetail_corner,
    joints.mitred_dovetail_corner,
    joints.blind_mitred_dovetail_corner,
    joints.butt_frame_corner,
    joints.mitre_corner,
    joints.keyed_mitre_corner,
    joints.dovetail_keyed_mitre_corner,
    joints.keyed_box_corner,
    joints.slanted_keys_box_corner,
    joints.splined_mitre_corner,
    joints.splined_box_corner,
    joints.splined_shelf_corner,
    joints.mitred_half_lap,
    joints.mitred_face_tenon_corner,
    joints.edge_mitre_corner,
    joints.hollow_leg,
    joints.mitre_splice,
    joints.cross_lap,
    joints.rod_in_hole,
    joints.round_mortise_tenon,
    joints.round_tenon_in_round_leg,
    joints.through_round_tenon,
    joints.tapered_round_tenon,
    joints.wedged_round_tenon,
    joints.dowelled_edge_joint,
    joints.dowelled_frame_corner,
    joints.pinned_mortise_tenon,
    joints.drawbored_mortise_tenon,
    joints.screwed_batten,
    joints.plugged_screws,
    frames.mortise_tenon_frame,
    frames.bridle_frame,
    frames.half_lap_frame,
    frames.frame_and_panel,
    frames.butt_frame_and_panel,
    frames.mitred_frame_and_panel,
    frames.shoji_frame,
    frames.ladder,
    projects.try_square,
    projects.mallet,
    projects.shooting_board,
    projects.bench_hook,
    projects.stepstool_seat,
    projects.ledged_door,
    projects.ledged_and_braced_door,
    projects.frame_and_panel_door,
    projects.cabinet_door,
    projects.bow_saw_frame,
    projects.butt_box,
    projects.bookshelf,
    projects.butt_shelf,
    projects.dovetail_shelf,
    projects.rabbeted_box,
    projects.dovetail_drawer,
    projects.drawer,
    projects.picture_frame,
    projects.table_frame,
    projects.table,
    projects.side_table,
    projects.chair,
    projects.stool,
    projects.stepstool,
    projects.coat_rack,
    projects.workbench,
]


def name(example: Example) -> str:
    """Name of an example as `module.function`, e.g. `frames.mortise_tenon_frame`."""
    return f"{example.__module__.rsplit('.', 1)[-1]}.{example.__name__}"


def get(example_name: str) -> Example:
    for example in ALL:
        if name(example) == example_name:
            return example
    raise KeyError(f"no example named {example_name}")


__all__ = ["ALL", "cuts", "frames", "get", "joints", "name", "projects"]
