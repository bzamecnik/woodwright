# Initial vision

Let's design a textual markup language to describe furniture design and construction. For a programmer and hobby woodworker it feels limiting that description of furniture to be designed or documented is purely visual - 2D sketches on paper or possibly 3D CAD models which take a lot work to make in specialized software. It makes it unsuitable to discuss with LLMs, to parametrize, easily work with programmatically, construct, modify or convert into other representations (2D plans, 3D models, images).

Furniture is typically composed of pieces which are first shaped from rough lumber to given size and shape, including joints, and then assembled together and surface-finished. Thus, it could be represented as a graph where the pieces are vertices and their joints are edges. Also the shaping process can be expressed this way: individual stages can be vertices, while the shaping operations (cutting, drilling, etc.) can be expressed as edges or a different kind of vertices connected by edges. Similarly for gluing, fastening with screws, nails, finishing, etc. The various vertices or edges can have properties, such as a kind of material, sizes, etc.

A crucial aspect is representing shapes. One possible paradigm could be constructive solid geometry (CSG), nicely represented e.g. by OpenSCAD, where shapes can be constructed using text-based representation language. Maybe that is too general for furniture. I guess there can be some standard library where common shapes (in a parametric form) can be represented and then applied in a composable way. For example, there can be a primitive "board" as a cuboid with 3 dimensions (length, width, thickness). It may be possible to apply operations, such as cutting through or partially in some way. Those could be combined to make a shape of a mortice or tenon. Those can be then applied on a board to make e.g. an apron for a table or with different parameter a stretcher. Typically multiple copies of the same shape (maybe with different parameters) may be needed. Then they can be assembled by orienting the pieces and connecting their joints.

A construction and assembly process could then be expressed by a graph of shaping and joining those primitive objects.

3D modeling software often allows using geometric constraints so that some properties of the shapes can be enforced and some dimensions can be calculated automatically, while others are fixed.

The language could be an application of an existing markup language, so that any infrastructure for it can be reused. It should be nicely readable and writable by human. YAML or something similar might be a nice basis. 

One of the open questions is a coordinate system. Either we can rely one some local cartesian coordinates or try a coordinate-free approach with Geometric Algebra but still keep it approachable for casual users.

This opens up door for more advances possibilities, such as static load analysis for safety and material optimization.

The original idea comes from 2025-12-11.
