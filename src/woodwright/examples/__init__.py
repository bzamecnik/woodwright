"""Library of example assemblies, ready to resolve and view.

Each example is a function returning an unresolved `Assembly`, with the
design dimensions as keyword arguments, so it can be resolved as is or built
on. In a notebook:

    from woodwright.examples import frames
    frames.mortise_tenon_frame(rail_length=400).resolve().compound()

From the command line (see `python -m woodwright.examples --help`):

    uv run python -m woodwright.examples list
    uv run python -m woodwright.examples export frames.mortise_tenon_frame
    uv run python -m woodwright.examples export --all
"""

from collections.abc import Callable

from woodwright.assembly import Assembly
from woodwright.examples import cuts, frames, joints, projects

Example = Callable[[], Assembly]

ALL: list[Example] = [
    cuts.dado,
    cuts.groove,
    cuts.rabbet,
    cuts.end_rabbet,
    cuts.slot_mortise,
    cuts.mortise,
    cuts.tenon,
    cuts.tongue,
    cuts.chamfer,
    cuts.mitre,
    cuts.edge_mitre,
    cuts.rabbeted_panel,
    cuts.wedge,
    cuts.tapered_leg,
    joints.butt_panel,
    joints.laminated_leg,
    joints.butt_corner,
    joints.dado_shelf,
    joints.rabbet_corner,
    joints.sliding_dovetail_shelf,
    joints.interlocking_rabbet_corner,
    joints.panel_in_groove,
    joints.tongue_and_groove_panel,
    joints.half_lap_corner,
    joints.half_lap_t,
    joints.bridle_corner,
    joints.mortise_tenon,
    joints.haunched_mortise_tenon_corner,
    joints.leg_and_aprons,
    joints.leg_and_aprons_mitred,
    joints.through_mortise_tenon,
    joints.mortise_tenon_thin_rail,
    joints.mitred_shoulder_tenon,
    joints.mitred_shoulder_corner,
    joints.dovetail_corner,
    joints.half_blind_dovetail_corner,
    joints.butt_frame_corner,
    joints.mitre_corner,
    joints.edge_mitre_corner,
    joints.mitre_splice,
    joints.cross_lap,
    frames.mortise_tenon_frame,
    frames.bridle_frame,
    frames.half_lap_frame,
    frames.frame_and_panel,
    projects.try_square,
    projects.mallet,
    projects.shooting_board,
    projects.butt_box,
    projects.bookshelf,
    projects.dovetail_drawer,
    projects.drawer,
    projects.picture_frame,
    projects.table_frame,
    projects.table,
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
