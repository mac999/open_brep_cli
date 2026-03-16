import tempfile
import unittest
from pathlib import Path

from src.model.id_registry import IDRegistry
from src.model.micro_operators import MicroOperators
from src.model.step_io import load_step, save_step
from src.model.topology import Edge, Face, HalfEdge, Loop, Solid, Vertex


class TestStepIO(unittest.TestCase):
    def setUp(self):
        IDRegistry().reset()
        self.registry = IDRegistry()
        self.micro_ops = MicroOperators()

    def _build_single_edge_model(self):
        solid, v1, face, loop = self.micro_ops.mvfs(0.0, 0.0, 0.0)
        edge, v2, he1, he2 = self.micro_ops.mev(loop.id, v1.id, 1.0, 0.0, 0.0)
        return {
            "solid": solid,
            "v1": v1,
            "v2": v2,
            "face": face,
            "loop": loop,
            "edge": edge,
            "he1": he1,
            "he2": he2,
        }

    def test_save_and_load_round_trip(self):
        model = self._build_single_edge_model()
        original_solid_id = model["solid"].id

        with tempfile.TemporaryDirectory() as temp_dir:
            step_path = Path(temp_dir) / "round_trip.step"

            saved_solid_id = save_step(str(step_path), self.registry)
            self.assertEqual(saved_solid_id, original_solid_id)
            self.assertTrue(step_path.exists())

            step_text = step_path.read_text(encoding="utf-8")
            self.assertIn("ISO-10303-21", step_text)
            self.assertIn("BREP_HALFEDGE", step_text)

            loaded_solid_ids = load_step(str(step_path), self.registry)
            self.assertEqual(loaded_solid_ids, [original_solid_id])

            loaded_solid = self.registry.get_object(original_solid_id)
            self.assertIsInstance(loaded_solid, Solid)
            self.assertEqual(len(loaded_solid.sfaces), 1)

            loaded_face = loaded_solid.sfaces[0]
            self.assertIsInstance(loaded_face, Face)
            self.assertEqual(len(loaded_face.floops), 1)

            loaded_loop = loaded_face.floops[0]
            self.assertIsInstance(loaded_loop, Loop)
            self.assertIsNotNone(loaded_loop.ledges)

            he_a = loaded_loop.ledges
            he_b = he_a.hnext

            self.assertIsInstance(he_a, HalfEdge)
            self.assertIsInstance(he_b, HalfEdge)
            self.assertIs(he_b.hnext, he_a)
            self.assertIs(he_a.hprev, he_b)
            self.assertIs(he_b.hprev, he_a)
            self.assertIs(he_a.htwin, he_b)
            self.assertIs(he_b.htwin, he_a)

            counts = {
                "solid": 0,
                "face": 0,
                "loop": 0,
                "vertex": 0,
                "edge": 0,
                "halfedge": 0,
            }

            for obj in self.registry._registry.values():
                if isinstance(obj, Solid):
                    counts["solid"] += 1
                elif isinstance(obj, Face):
                    counts["face"] += 1
                elif isinstance(obj, Loop):
                    counts["loop"] += 1
                elif isinstance(obj, Vertex):
                    counts["vertex"] += 1
                elif isinstance(obj, Edge):
                    counts["edge"] += 1
                elif isinstance(obj, HalfEdge):
                    counts["halfedge"] += 1

            self.assertEqual(counts["solid"], 1)
            self.assertEqual(counts["face"], 1)
            self.assertEqual(counts["loop"], 1)
            self.assertEqual(counts["vertex"], 2)
            self.assertEqual(counts["edge"], 1)
            self.assertEqual(counts["halfedge"], 2)

    def test_next_id_continues_after_load(self):
        self._build_single_edge_model()

        with tempfile.TemporaryDirectory() as temp_dir:
            step_path = Path(temp_dir) / "id_continuity.step"
            save_step(str(step_path), self.registry)
            load_step(str(step_path), self.registry)

            max_loaded_id = max(int(obj_id[1:]) for obj_id in self.registry._registry)
            new_vertex = Vertex(9.0, 9.0, 9.0)

            self.assertEqual(int(new_vertex.id[1:]), max_loaded_id + 1)


if __name__ == "__main__":
    unittest.main()
