from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from src.model.id_registry import IDRegistry
from src.model.topology import Edge, Face, HalfEdge, Loop, Solid, Vertex


_ID_PATTERN = re.compile(r"^#\d+$")
_ENTITY_LINE_PATTERN = re.compile(r"^\s*#\d+\s*=\s*([A-Z0-9_]+)\((.*)\);\s*$")


class StepIOError(ValueError):
    """Raised when STEP save/load fails due to invalid topology or file format."""


def save_step(file_path: str, registry: IDRegistry, solid_id: str | None = None) -> str:
    """Save one solid from the registry to a STEP-like text file."""
    solid = _select_solid(registry, solid_id)

    faces = list(solid.sfaces)
    loops: dict[str, Loop] = {}
    halfedges: dict[str, HalfEdge] = {}
    edges: dict[str, Edge] = {}
    vertices: dict[str, Vertex] = {}

    for face in faces:
        for loop in face.floops:
            loops[loop.id] = loop
            if loop.ledges is None:
                continue

            current = loop.ledges
            start = loop.ledges
            traversal_count = 0

            while True:
                halfedges[current.id] = current
                if current.hedge is not None:
                    edges[current.hedge.id] = current.hedge
                if current.hvertex is not None:
                    vertices[current.hvertex.id] = current.hvertex

                current = current.hnext
                traversal_count += 1

                if current is None:
                    raise StepIOError(f"Loop {loop.id} has a dangling hnext pointer.")
                if current == start:
                    break
                if traversal_count > 50000:
                    raise StepIOError(
                        f"Loop traversal limit exceeded for {loop.id}. "
                        "Topology may be malformed."
                    )

    step_lines: list[str] = []
    record_no = 1

    def add_record(entity_name: str, args: list[str]) -> None:
        nonlocal record_no
        step_lines.append(f"#{record_no} = {entity_name}({', '.join(args)});")
        record_no += 1

    add_record("BREP_SOLID", [_step_string(solid.id)])

    for face in _sorted_by_id(faces):
        add_record("BREP_FACE", [_step_string(face.id), _step_string(face.fsolid.id)])

    for loop in _sorted_by_id(loops.values()):
        add_record(
            "BREP_LOOP",
            [
                _step_string(loop.id),
                _step_string(loop.lface.id),
                _step_optional_string(loop.ledges.id if loop.ledges else None),
            ],
        )

    for vertex in _sorted_by_id(vertices.values()):
        x, y, z = vertex.vpoint
        add_record(
            "BREP_VERTEX",
            [
                _step_string(vertex.id),
                _format_float(x),
                _format_float(y),
                _format_float(z),
                _step_optional_string(vertex.vedge.id if vertex.vedge else None),
            ],
        )

    for edge in _sorted_by_id(edges.values()):
        add_record(
            "BREP_EDGE",
            [
                _step_string(edge.id),
                _step_optional_string(edge.he1.id if edge.he1 else None),
                _step_optional_string(edge.he2.id if edge.he2 else None),
            ],
        )

    for halfedge in _sorted_by_id(halfedges.values()):
        add_record(
            "BREP_HALFEDGE",
            [
                _step_string(halfedge.id),
                _step_string(halfedge.hvertex.id),
                _step_string(halfedge.hedge.id),
                _step_string(halfedge.hloop.id),
                _step_optional_string(halfedge.hnext.id if halfedge.hnext else None),
                _step_optional_string(halfedge.hprev.id if halfedge.hprev else None),
                _step_optional_string(halfedge.htwin.id if halfedge.htwin else None),
            ],
        )

    utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = "\n".join(
        [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('BRep CLI topology export'),'2;1');",
            f"FILE_NAME('{Path(file_path).name}','{utc_now}',(''),(''),'brep_cli','brep_cli','');",
            "FILE_SCHEMA(('BREP_CLI_SCHEMA'));",
            "ENDSEC;",
            "DATA;",
            *step_lines,
            "ENDSEC;",
            "END-ISO-10303-21;",
            "",
        ]
    )

    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")

    return solid.id


def load_step(file_path: str, registry: IDRegistry) -> list[str]:
    """Load topology entities from a STEP-like text file into the registry."""
    path = Path(file_path)
    if not path.exists():
        raise StepIOError(f"File not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    solid_specs: set[str] = set()
    face_specs: dict[str, str] = {}
    loop_specs: dict[str, tuple[str, str | None]] = {}
    vertex_specs: dict[str, tuple[float, float, float, str | None]] = {}
    edge_specs: dict[str, tuple[str | None, str | None]] = {}
    halfedge_specs: dict[str, tuple[str, str, str, str | None, str | None, str | None]] = {}

    in_data_section = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        upper = line.upper()
        if upper == "DATA;":
            in_data_section = True
            continue
        if in_data_section and upper == "ENDSEC;":
            break
        if not in_data_section:
            continue

        match = _ENTITY_LINE_PATTERN.match(line)
        if not match:
            continue

        entity = match.group(1).upper()
        args = _split_step_args(match.group(2))

        if entity == "BREP_SOLID":
            if len(args) != 1:
                raise StepIOError("BREP_SOLID expects 1 argument.")
            solid_id = _parse_required_id(args[0])
            if solid_id in solid_specs:
                raise StepIOError(f"Duplicate solid ID in file: {solid_id}")
            solid_specs.add(solid_id)

        elif entity == "BREP_FACE":
            if len(args) != 2:
                raise StepIOError("BREP_FACE expects 2 arguments.")
            face_id = _parse_required_id(args[0])
            parent_solid_id = _parse_required_id(args[1])
            _raise_if_duplicate(face_specs, face_id, "face")
            face_specs[face_id] = parent_solid_id

        elif entity == "BREP_LOOP":
            if len(args) != 3:
                raise StepIOError("BREP_LOOP expects 3 arguments.")
            loop_id = _parse_required_id(args[0])
            parent_face_id = _parse_required_id(args[1])
            ledges_id = _parse_optional_id(args[2])
            _raise_if_duplicate(loop_specs, loop_id, "loop")
            loop_specs[loop_id] = (parent_face_id, ledges_id)

        elif entity == "BREP_VERTEX":
            if len(args) != 5:
                raise StepIOError("BREP_VERTEX expects 5 arguments.")
            vertex_id = _parse_required_id(args[0])
            x = _parse_float(args[1])
            y = _parse_float(args[2])
            z = _parse_float(args[3])
            vedge_id = _parse_optional_id(args[4])
            _raise_if_duplicate(vertex_specs, vertex_id, "vertex")
            vertex_specs[vertex_id] = (x, y, z, vedge_id)

        elif entity == "BREP_EDGE":
            if len(args) != 3:
                raise StepIOError("BREP_EDGE expects 3 arguments.")
            edge_id = _parse_required_id(args[0])
            he1_id = _parse_optional_id(args[1])
            he2_id = _parse_optional_id(args[2])
            _raise_if_duplicate(edge_specs, edge_id, "edge")
            edge_specs[edge_id] = (he1_id, he2_id)

        elif entity == "BREP_HALFEDGE":
            if len(args) != 7:
                raise StepIOError("BREP_HALFEDGE expects 7 arguments.")
            halfedge_id = _parse_required_id(args[0])
            hvertex_id = _parse_required_id(args[1])
            hedge_id = _parse_required_id(args[2])
            hloop_id = _parse_required_id(args[3])
            hnext_id = _parse_optional_id(args[4])
            hprev_id = _parse_optional_id(args[5])
            htwin_id = _parse_optional_id(args[6])
            _raise_if_duplicate(halfedge_specs, halfedge_id, "half-edge")
            halfedge_specs[halfedge_id] = (hvertex_id, hedge_id, hloop_id, hnext_id, hprev_id, htwin_id)

    if not solid_specs:
        raise StepIOError("No BREP_SOLID records found in STEP data section.")

    for face_id, solid_id in face_specs.items():
        if solid_id not in solid_specs:
            raise StepIOError(f"Face {face_id} references missing Solid {solid_id}.")

    for loop_id, (face_id, _) in loop_specs.items():
        if face_id not in face_specs:
            raise StepIOError(f"Loop {loop_id} references missing Face {face_id}.")

    for halfedge_id, (hvertex_id, hedge_id, hloop_id, hnext_id, hprev_id, htwin_id) in halfedge_specs.items():
        if hvertex_id not in vertex_specs:
            raise StepIOError(f"HalfEdge {halfedge_id} references missing Vertex {hvertex_id}.")
        if hedge_id not in edge_specs:
            raise StepIOError(f"HalfEdge {halfedge_id} references missing Edge {hedge_id}.")
        if hloop_id not in loop_specs:
            raise StepIOError(f"HalfEdge {halfedge_id} references missing Loop {hloop_id}.")
        if hnext_id and hnext_id not in halfedge_specs:
            raise StepIOError(f"HalfEdge {halfedge_id} references missing hnext {hnext_id}.")
        if hprev_id and hprev_id not in halfedge_specs:
            raise StepIOError(f"HalfEdge {halfedge_id} references missing hprev {hprev_id}.")
        if htwin_id and htwin_id not in halfedge_specs:
            raise StepIOError(f"HalfEdge {halfedge_id} references missing htwin {htwin_id}.")

    for edge_id, (he1_id, he2_id) in edge_specs.items():
        if he1_id and he1_id not in halfedge_specs:
            raise StepIOError(f"Edge {edge_id} references missing he1 {he1_id}.")
        if he2_id and he2_id not in halfedge_specs:
            raise StepIOError(f"Edge {edge_id} references missing he2 {he2_id}.")

    for loop_id, (_, ledges_id) in loop_specs.items():
        if ledges_id and ledges_id not in halfedge_specs:
            raise StepIOError(f"Loop {loop_id} references missing ledges {ledges_id}.")

    for vertex_id, (_, _, _, vedge_id) in vertex_specs.items():
        if vedge_id and vedge_id not in halfedge_specs:
            raise StepIOError(f"Vertex {vertex_id} references missing vedge {vedge_id}.")

    registry.reset()

    solids: dict[str, Solid] = {}
    for solid_id in sorted(solid_specs, key=_id_sort_key):
        solids[solid_id] = Solid()

    faces: dict[str, Face] = {}
    for face_id in sorted(face_specs, key=_id_sort_key):
        faces[face_id] = Face(solids[face_specs[face_id]])

    loops: dict[str, Loop] = {}
    for loop_id in sorted(loop_specs, key=_id_sort_key):
        parent_face_id, _ = loop_specs[loop_id]
        loops[loop_id] = Loop(faces[parent_face_id])

    vertices: dict[str, Vertex] = {}
    for vertex_id in sorted(vertex_specs, key=_id_sort_key):
        x, y, z, _ = vertex_specs[vertex_id]
        vertices[vertex_id] = Vertex(x, y, z)

    edges: dict[str, Edge] = {}
    for edge_id in sorted(edge_specs, key=_id_sort_key):
        edges[edge_id] = Edge()

    halfedges: dict[str, HalfEdge] = {}
    for halfedge_id in sorted(halfedge_specs, key=_id_sort_key):
        hvertex_id, hedge_id, hloop_id, _, _, _ = halfedge_specs[halfedge_id]
        halfedges[halfedge_id] = HalfEdge(vertices[hvertex_id], edges[hedge_id], loops[hloop_id])

    for loop_id, (_, ledges_id) in loop_specs.items():
        loops[loop_id].ledges = halfedges[ledges_id] if ledges_id else None

    for vertex_id, (_, _, _, vedge_id) in vertex_specs.items():
        vertices[vertex_id].vedge = halfedges[vedge_id] if vedge_id else None

    for edge_id, (he1_id, he2_id) in edge_specs.items():
        edges[edge_id].he1 = halfedges[he1_id] if he1_id else None
        edges[edge_id].he2 = halfedges[he2_id] if he2_id else None

    for halfedge_id, (_, _, _, hnext_id, hprev_id, htwin_id) in halfedge_specs.items():
        halfedge = halfedges[halfedge_id]
        halfedge.hnext = halfedges[hnext_id] if hnext_id else None
        halfedge.hprev = halfedges[hprev_id] if hprev_id else None
        halfedge.htwin = halfedges[htwin_id] if htwin_id else None

    all_objects = _combine_object_maps(solids, faces, loops, vertices, edges, halfedges)
    for object_id, obj in all_objects.items():
        obj.id = object_id

    registry._registry = all_objects
    registry._next_id = _next_available_id(all_objects)

    return sorted(solids.keys(), key=_id_sort_key)


def _select_solid(registry: IDRegistry, solid_id: str | None) -> Solid:
    if solid_id:
        solid = registry.get_object(solid_id)
        if not isinstance(solid, Solid):
            raise StepIOError(f"Object with ID {solid_id} is not a Solid.")
        return solid

    solids = [obj for obj in registry._registry.values() if isinstance(obj, Solid)]
    if not solids:
        raise StepIOError("No solid found in registry. Create one before saving.")

    solids.sort(key=lambda solid_obj: _id_sort_key(solid_obj.id))
    return solids[0]


def _combine_object_maps(*maps: dict[str, object]) -> dict[str, object]:
    combined: dict[str, object] = {}
    for mapping in maps:
        for object_id, obj in mapping.items():
            if object_id in combined:
                raise StepIOError(f"Duplicate object ID while rebuilding registry: {object_id}")
            combined[object_id] = obj
    return combined


def _split_step_args(raw_args: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    in_string = False

    for char in raw_args:
        if char == "'":
            in_string = not in_string
            current.append(char)
            continue

        if char == "," and not in_string:
            args.append("".join(current).strip())
            current = []
            continue

        current.append(char)

    if current:
        args.append("".join(current).strip())

    return args


def _parse_required_id(token: str) -> str:
    value = _parse_step_string(token)
    if not _ID_PATTERN.match(value):
        raise StepIOError(f"Invalid internal ID: {value}")
    return value


def _parse_optional_id(token: str) -> str | None:
    token = token.strip()
    if token == "$":
        return None
    return _parse_required_id(token)


def _parse_step_string(token: str) -> str:
    stripped = token.strip()
    if len(stripped) < 2 or stripped[0] != "'" or stripped[-1] != "'":
        raise StepIOError(f"Expected STEP string token, got: {token}")
    return stripped[1:-1]


def _parse_float(token: str) -> float:
    try:
        return float(token.strip())
    except ValueError as exc:
        raise StepIOError(f"Invalid float token: {token}") from exc


def _raise_if_duplicate(mapping: dict[str, object], object_id: str, object_type: str) -> None:
    if object_id in mapping:
        raise StepIOError(f"Duplicate {object_type} ID in file: {object_id}")


def _format_float(value: float) -> str:
    return format(value, ".17g")


def _step_string(value: str) -> str:
    return f"'{value}'"


def _step_optional_string(value: str | None) -> str:
    if value is None:
        return "$"
    return _step_string(value)


def _next_available_id(objects_by_id: dict[str, object]) -> int:
    if not objects_by_id:
        return 100

    max_number = max(int(object_id[1:]) for object_id in objects_by_id)
    return max(100, max_number + 1)


def _id_sort_key(object_id: str) -> tuple[int, str]:
    if _ID_PATTERN.match(object_id):
        return int(object_id[1:]), object_id
    return 10**9, object_id


def _sorted_by_id(objects: list[object] | dict[str, object] | tuple[object, ...]):
    return sorted(objects, key=lambda obj: _id_sort_key(obj.id))
