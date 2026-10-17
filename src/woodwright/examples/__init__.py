"""Library of example assemblies, ready to resolve and view.

Each example is a function returning an unresolved `Assembly`, with the
design dimensions as keyword arguments, so it can be resolved as is or built
on. In a notebook:

    from woodwright.examples import frames
    frames.mortise_tenon_frame(rail_length=400).resolve().compound()
"""

from woodwright.examples import cuts, frames, joints

ALL = [
    cuts.dado,
    cuts.groove,
    cuts.rabbet,
    cuts.end_rabbet,
    joints.mortise_tenon,
    joints.bridle_corner,
    joints.tongue_and_groove_panel,
    joints.dovetail_corner,
    frames.mortise_tenon_frame,
]

__all__ = ["ALL", "cuts", "frames", "joints"]
