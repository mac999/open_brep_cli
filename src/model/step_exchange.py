from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.model.id_registry import IDRegistry
from src.model.topology import HalfEdge, Loop, Solid, Vertex


class StepExchangeError(ValueError):
    """Raised when exporting a topology to a standard STEP exchange file fails."""


def save_step_exchange(
    file_path: str,
    registry: IDRegistry,
    solid_id: str | None = None,
    unit: str = "m",
) -> list[str]:
    """Export one or more solids as AP214 ADVANCED_BREP for Rhino."""
    solids = _select_solids(registry, solid_id)
    builder = _StepBuilder()

    # ── product / unit boilerplate ──────────────────────────────────────────
    app_ctx = builder.add("APPLICATION_CONTEXT", [_s("automotive_design")])
    prod_ctx = builder.add("PRODUCT_CONTEXT", [_s(""), _r(app_ctx), _s("mechanical")])
    product_name = solids[0].id if len(solids) == 1 else "MULTI_SOLID"
    product_desc = "BRep CLI Solid" if len(solids) == 1 else f"BRep CLI Solids ({len(solids)})"
    product = builder.add("PRODUCT", [_s(product_name), _s(product_desc), _s(""), _l([_r(prod_ctx)])])
    formation = builder.add(
        "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE",
        [_s(""), _s(""), _r(product), ".NOT_KNOWN."],
    )
    def_ctx = builder.add(
        "PRODUCT_DEFINITION_CONTEXT",
        [_s("part definition"), _r(app_ctx), _s("design")],
    )
    definition = builder.add("PRODUCT_DEFINITION", [_s(""), _s(""), _r(formation), _r(def_ctx)])
    def_shape = builder.add("PRODUCT_DEFINITION_SHAPE", [_s(""), _s(""), _r(definition)])

    len_unit = builder.add_raw(_length_unit_expression(unit))
    ang_unit = builder.add_raw("(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.))")
    sol_unit = builder.add_raw("(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT())")
    uncertainty = builder.add(
        "UNCERTAINTY_MEASURE_WITH_UNIT",
        ["LENGTH_MEASURE(1.E-06)", _r(len_unit), _s("distance_accuracy_value"), _s("confusion accuracy")],
    )
    repr_ctx = builder.add_raw(
        "(GEOMETRIC_REPRESENTATION_CONTEXT(3) "
        f"GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT({_l([_r(uncertainty)])}) "
        f"GLOBAL_UNIT_ASSIGNED_CONTEXT({_l([_r(len_unit), _r(ang_unit), _r(sol_unit)])}) "
        "REPRESENTATION_CONTEXT('', ''))"
    )

    brep_ids: list[int] = []
    for solid in solids:
        if not solid.sfaces:
            raise StepExchangeError(f"Solid {solid.id} has no faces.")

        face_he_lists: list[tuple[object, list[HalfEdge]]] = []
        seen_v: set[str] = set()
        seen_e: set[str] = set()
        all_vertices: list[Vertex] = []
        all_edges: list[object] = []

        for face in solid.sfaces:
            if not face.floops:
                raise StepExchangeError(f"Face {face.id} has no loops.")
            he_list = _ordered_halfedges(face.floops[0])
            face_he_lists.append((face, he_list))
            for he in he_list:
                for v in (he.hprev.hvertex, he.hvertex):
                    if v.id not in seen_v:
                        all_vertices.append(v)
                        seen_v.add(v.id)
                if he.hedge.id not in seen_e:
                    all_edges.append(he.hedge)
                    seen_e.add(he.hedge.id)

        v_cp: dict[str, int] = {}
        v_vp: dict[str, int] = {}
        for v in all_vertices:
            cp = builder.add("CARTESIAN_POINT", [_s(""), _pt(v.vpoint)])
            vp = builder.add("VERTEX_POINT", [_s(""), _r(cp)])
            v_cp[v.id] = cp
            v_vp[v.id] = vp

        e_ec: dict[str, int] = {}
        e_sv: dict[str, str] = {}

        for edge in all_edges:
            he1 = edge.he1
            if he1 is None:
                raise StepExchangeError(f"Edge {edge.id} has no half-edge.")
            vs = he1.hprev.hvertex
            ve = he1.hvertex

            dx = ve.vpoint[0] - vs.vpoint[0]
            dy = ve.vpoint[1] - vs.vpoint[1]
            dz = ve.vpoint[2] - vs.vpoint[2]
            length = (dx * dx + dy * dy + dz * dz) ** 0.5
            if length < 1e-12:
                raise StepExchangeError(f"Degenerate edge {edge.id} has zero length.")

            dir_id = builder.add("DIRECTION", [_s(""), _pt((dx / length, dy / length, dz / length))])
            vec_id = builder.add("VECTOR", [_s(""), _r(dir_id), _ff(length)])
            line_id = builder.add("LINE", [_s(""), _r(v_cp[vs.id]), _r(vec_id)])
            ec_id = builder.add(
                "EDGE_CURVE",
                [_s(""), _r(v_vp[vs.id]), _r(v_vp[ve.id]), _r(line_id), ".T."],
            )
            e_ec[edge.id] = ec_id
            e_sv[edge.id] = vs.id

        af_ids: list[int] = []
        for _face, he_list in face_he_lists:
            oe_ids: list[int] = []
            for he in he_list:
                ec_id = e_ec[he.hedge.id]
                orientation = ".T." if he.hprev.hvertex.id == e_sv[he.hedge.id] else ".F."
                oe = builder.add("ORIENTED_EDGE", [_s(""), "*", "*", _r(ec_id), orientation])
                oe_ids.append(oe)

            el = builder.add("EDGE_LOOP", [_s(""), _l([_r(oid) for oid in oe_ids])])
            fob = builder.add("FACE_OUTER_BOUND", [_s(""), _r(el), ".T."])

            pts = [he.hprev.hvertex.vpoint for he in he_list]
            normal = _newell_normal_normalized(pts)

            p0 = he_list[0].hprev.hvertex.vpoint
            p1 = he_list[0].hvertex.vpoint
            ref = _norm3(_sub3(p1, p0))

            plane_cp = builder.add("CARTESIAN_POINT", [_s(""), _pt(pts[0])])
            norm_d = builder.add("DIRECTION", [_s(""), _pt(normal)])
            ref_d = builder.add("DIRECTION", [_s(""), _pt(ref)])
            axis2 = builder.add("AXIS2_PLACEMENT_3D", [_s(""), _r(plane_cp), _r(norm_d), _r(ref_d)])
            plane = builder.add("PLANE", [_s(""), _r(axis2)])

            af = builder.add("ADVANCED_FACE", [_s(""), _l([_r(fob)]), _r(plane), ".T."])
            af_ids.append(af)

        shell = builder.add("CLOSED_SHELL", [_s(""), _l([_r(af) for af in af_ids])])
        brep = builder.add("MANIFOLD_SOLID_BREP", [_s(solid.id), _r(shell)])
        brep_ids.append(brep)

    origin_pt = builder.add("CARTESIAN_POINT", [_s(""), "(0., 0., 0.)"])
    z_dir = builder.add("DIRECTION", [_s(""), "(0., 0., 1.)"])
    x_dir = builder.add("DIRECTION", [_s(""), "(1., 0., 0.)"])
    placement = builder.add("AXIS2_PLACEMENT_3D", [_s(""), _r(origin_pt), _r(z_dir), _r(x_dir)])
    shape_rep = builder.add(
        "ADVANCED_BREP_SHAPE_REPRESENTATION",
        [_s(""), _l([*[_r(brep_id) for brep_id in brep_ids], _r(placement)]), _r(repr_ctx)],
    )
    builder.add("SHAPE_DEFINITION_REPRESENTATION", [_r(def_shape), _r(shape_rep)])

    # ── write file ──────────────────────────────────────────────────────────
    utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = "\n".join([
        "ISO-10303-21;",
        "HEADER;",
        f"FILE_DESCRIPTION(('BRep CLI ADVANCED_BREP export ({unit})'),'2;1');",
        f"FILE_NAME('{Path(file_path).name}','{utc_now}',(''),(''),'brep_cli','brep_cli','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",
        "ENDSEC;",
        "DATA;",
        *builder.lines,
        "ENDSEC;",
        "END-ISO-10303-21;",
        "",
    ])
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return [solid.id for solid in solids]


def _ordered_halfedges(loop: Loop) -> list[HalfEdge]:
    if loop.ledges is None:
        raise StepExchangeError(f"Loop {loop.id} has no starting half-edge (ledges is None).")
    result: list[HalfEdge] = []
    current = loop.ledges
    start = loop.ledges
    guard = 0
    while True:
        if current.hprev is None or current.hprev.hvertex is None:
            raise StepExchangeError(f"Loop {loop.id} has a dangling hprev or vertex.")
        result.append(current)
        current = current.hnext
        guard += 1
        if current is None:
            raise StepExchangeError(f"Loop {loop.id} has a dangling hnext pointer.")
        if current is start:
            break
        if guard > 50_000:
            raise StepExchangeError(f"Loop traversal limit exceeded for {loop.id}.")
    return result


def _newell_normal_normalized(pts: list[tuple]) -> tuple:
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1, z1 = pts[i]
        x2, y2, z2 = pts[(i + 1) % n]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length < 1e-12:
        raise StepExchangeError("Degenerate face (zero-area polygon).")
    return nx / length, ny / length, nz / length


def _sub3(a: tuple, b: tuple) -> tuple:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _norm3(v: tuple) -> tuple:
    x, y, z = v
    length = (x * x + y * y + z * z) ** 0.5
    if length < 1e-12:
        raise StepExchangeError("Zero-length reference direction.")
    return x / length, y / length, z / length


def _select_solids(registry: IDRegistry, solid_id: str | None) -> list[Solid]:
    if solid_id:
        obj = registry.get_object(solid_id)
        if not isinstance(obj, Solid):
            raise StepExchangeError(f"Object {solid_id} is not a Solid.")
        return [obj]

    solids = [o for o in registry._registry.values() if isinstance(o, Solid)]
    if not solids:
        raise StepExchangeError("No solid found in registry.")

    solids.sort(key=lambda s: _id_sort_key(s.id))
    return solids


def _length_unit_expression(unit: str) -> str:
    normalized = unit.strip().lower()
    if normalized in ("m", "meter", "metre"):
        return "(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT($,.METRE.))"
    if normalized in ("mm", "millimeter", "millimetre"):
        return "(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.))"
    raise StepExchangeError("Unsupported STEP unit. Use --unit m or --unit mm.")



def _id_sort_key(oid: str) -> tuple:
    if oid.startswith("#") and oid[1:].isdigit():
        return (int(oid[1:]), oid)
    return (10 ** 9, oid)


def _s(v: str) -> str:
    return f"'{v.replace(chr(39), chr(39)+chr(39))}'"


def _r(eid: int) -> str:
    return f"#{eid}"


def _l(items: list[str]) -> str:
    return f"({','.join(items)})"


def _pt(p: tuple) -> str:
    return f"({_ff(p[0])},{_ff(p[1])},{_ff(p[2])})"


def _ff(v: float) -> str:
    text = format(v, ".10g")
    if "." not in text and "e" not in text.lower():
        text += "."
    return text


class _StepBuilder:
    def __init__(self):
        self._next = 1
        self.lines: list[str] = []

    def add(self, entity_name: str, args: list[str]) -> int:
        entity_id = self._next
        self._next += 1
        self.lines.append(f"#{entity_id} = {entity_name}({', '.join(args)});")
        return entity_id

    def add_raw(self, expression: str) -> int:
        entity_id = self._next
        self._next += 1
        self.lines.append(f"#{entity_id} = {expression};")
        return entity_id
