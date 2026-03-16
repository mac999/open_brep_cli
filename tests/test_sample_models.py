import unittest

from src.model.id_registry import IDRegistry
from src.model.sample_models import SampleModelError, build_cube_sample, build_plane_sample
from src.model.topology import Edge, Face, HalfEdge, Loop, Solid, Vertex


class TestSampleModels(unittest.TestCase):
    def setUp(self):
        IDRegistry().reset()
        self.registry = IDRegistry()

    def _count_entities(self):
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

        return counts

    def test_build_plane_sample_default(self):
        result = build_plane_sample(self.registry)

        solid = result["solid"]
        bounded_face = result["bounded_face"]

        self.assertIsInstance(solid, Solid)
        self.assertIsInstance(bounded_face, Face)
        self.assertIn(bounded_face, solid.sfaces)

        counts = self._count_entities()
        self.assertEqual(counts["solid"], 1)
        self.assertEqual(counts["face"], 2)
        self.assertEqual(counts["loop"], 2)
        self.assertEqual(counts["vertex"], 4)
        self.assertEqual(counts["edge"], 4)
        self.assertEqual(counts["halfedge"], 8)

    def test_build_cube_sample_default(self):
        result = build_cube_sample(self.registry)

        solid = result["solid"]
        self.assertIsInstance(solid, Solid)
        self.assertEqual(len(solid.sfaces), 6)

        counts = self._count_entities()
        self.assertEqual(counts["solid"], 1)
        self.assertEqual(counts["face"], 6)
        self.assertEqual(counts["loop"], 6)
        self.assertEqual(counts["vertex"], 8)
        self.assertEqual(counts["edge"], 12)
        self.assertEqual(counts["halfedge"], 24)

        for face in solid.sfaces:
            self.assertEqual(len(face.floops), 1)
            loop = face.floops[0]
            self.assertIsNotNone(loop.ledges)

            start = loop.ledges
            current = start
            he_count = 0
            while True:
                self.assertIsNotNone(current.hnext)
                self.assertIsNotNone(current.hprev)
                self.assertIsNotNone(current.htwin)
                self.assertIs(current.htwin.htwin, current)
                current = current.hnext
                he_count += 1
                if current == start:
                    break
                self.assertLess(he_count, 10)

            self.assertEqual(he_count, 4)

    def test_invalid_sample_dimensions(self):
        with self.assertRaises(SampleModelError):
            build_plane_sample(self.registry, width=0.0, depth=1.0)

        with self.assertRaises(SampleModelError):
            build_cube_sample(self.registry, size=-1.0)

    def test_append_mode_does_not_reset_registry(self):
        first = build_cube_sample(self.registry, size=2.0, reset_registry=True)
        second = build_plane_sample(self.registry, width=4.0, depth=3.0, reset_registry=False)

        self.assertIsInstance(first["solid"], Solid)
        self.assertIsInstance(second["solid"], Solid)

        counts = self._count_entities()
        self.assertEqual(counts["solid"], 2)
        self.assertEqual(counts["face"], 8)


if __name__ == "__main__":
    unittest.main()
