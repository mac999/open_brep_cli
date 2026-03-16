from __future__ import annotations

from src.model.id_registry import IDRegistry
from src.model.micro_operators import MicroOperators
from src.model.topology import Edge, Face, HalfEdge, Loop, Solid, Vertex


class SampleModelError(ValueError):
    """Raised when sample model generation fails."""


def build_plane_sample(
    registry: IDRegistry,
    width: float = 1.0,
    depth: float = 1.0,
    reset_registry: bool = True,
) -> dict[str, object]:
    """Build a rectangular planar sample using micro operators."""
    if width <= 0 or depth <= 0:
        raise SampleModelError("Width and depth must be positive numbers.")

    if reset_registry:
        registry.reset()
    micro_ops = MicroOperators()

    solid, v1, face_seed, loop = micro_ops.mvfs(0.0, 0.0, 0.0)
    _, v2, _, _ = micro_ops.mev(loop.id, v1.id, width, 0.0, 0.0)
    _, v3, _, _ = micro_ops.mev(loop.id, v2.id, width, depth, 0.0)
    _, v4, _, _ = micro_ops.mev(loop.id, v3.id, 0.0, depth, 0.0)
    _, bounded_face, _, _ = micro_ops.mef(face_seed.id, v4.id, v1.id)

    return {
        "sample": "plane",
        "solid": solid,
        "bounded_face": bounded_face,
        "vertex_ids": [v1.id, v2.id, v3.id, v4.id],
        "width": width,
        "depth": depth,
    }


def build_cube_sample(
    registry: IDRegistry,
    size: float = 1.0,
    reset_registry: bool = True,
) -> dict[str, object]:
    """Build a closed cube B-Rep sample with 6 faces."""
    if size <= 0:
        raise SampleModelError("Size must be a positive number.")

    if reset_registry:
        registry.reset()

    solid = Solid()
    vertices = [
        Vertex(0.0, 0.0, 0.0),
        Vertex(size, 0.0, 0.0),
        Vertex(size, size, 0.0),
        Vertex(0.0, size, 0.0),
        Vertex(0.0, 0.0, size),
        Vertex(size, 0.0, size),
        Vertex(size, size, size),
        Vertex(0.0, size, size),
    ]

    face_cycles = [
        ("bottom", [0, 3, 2, 1]),
        ("top", [4, 5, 6, 7]),
        ("front", [0, 1, 5, 4]),
        ("back", [3, 7, 6, 2]),
        ("left", [0, 4, 7, 3]),
        ("right", [1, 2, 6, 5]),
    ]

    edges_by_key: dict[tuple[int, int], Edge] = {}
    directed_halfedges: dict[tuple[int, int], HalfEdge] = {}
    faces_by_name: dict[str, Face] = {}

    for face_name, cycle in face_cycles:
        face = Face(solid)
        loop = Loop(face)
        faces_by_name[face_name] = face

        face_halfedges: list[HalfEdge] = []
        cycle_len = len(cycle)

        for i in range(cycle_len):
            start = cycle[i]
            end = cycle[(i + 1) % cycle_len]
            directed_key = (start, end)

            if directed_key in directed_halfedges:
                raise SampleModelError(f"Duplicate directed edge in sample definition: {directed_key}")

            edge_key = tuple(sorted((start, end)))
            edge = edges_by_key.get(edge_key)
            if edge is None:
                edge = Edge()
                edges_by_key[edge_key] = edge

            halfedge = HalfEdge(vertices[end], edge, loop)
            directed_halfedges[directed_key] = halfedge
            face_halfedges.append(halfedge)

            if edge.he1 is None:
                edge.he1 = halfedge
            elif edge.he2 is None:
                edge.he2 = halfedge
            else:
                raise SampleModelError(f"Edge {edge.id} has more than two half-edges.")

            twin = directed_halfedges.get((end, start))
            if twin is not None:
                halfedge.htwin = twin
                twin.htwin = halfedge

        for i in range(cycle_len):
            current = face_halfedges[i]
            current.hnext = face_halfedges[(i + 1) % cycle_len]
            current.hprev = face_halfedges[(i - 1) % cycle_len]

        loop.ledges = face_halfedges[0]

    for edge in edges_by_key.values():
        if edge.he1 is None or edge.he2 is None:
            raise SampleModelError(f"Open edge detected in cube sample: {edge.id}")

    for halfedge in directed_halfedges.values():
        if halfedge.htwin is None:
            raise SampleModelError(f"Unpaired half-edge detected in cube sample: {halfedge.id}")

    for vertex_index, vertex in enumerate(vertices):
        outgoing_halfedge = _find_outgoing_halfedge(directed_halfedges, vertex_index)
        if outgoing_halfedge is None:
            raise SampleModelError(f"Vertex {vertex.id} has no outgoing half-edge.")
        vertex.vedge = outgoing_halfedge

    return {
        "sample": "cube",
        "solid": solid,
        "faces": faces_by_name,
        "vertex_ids": [vertex.id for vertex in vertices],
        "size": size,
    }


def _find_outgoing_halfedge(
    directed_halfedges: dict[tuple[int, int], HalfEdge],
    vertex_index: int,
) -> HalfEdge | None:
    for (start, _), halfedge in directed_halfedges.items():
        if start == vertex_index:
            return halfedge
    return None
