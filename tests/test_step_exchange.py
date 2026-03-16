import tempfile
import unittest
from pathlib import Path

from src.model.id_registry import IDRegistry
from src.model.sample_models import build_cube_sample, build_plane_sample
from src.model.step_exchange import save_step_exchange


class TestStepExchange(unittest.TestCase):
    def setUp(self):
        self.registry = IDRegistry()
        self.registry.reset()

    def tearDown(self):
        self.registry.reset()

    def test_save_step_exchange_writes_advanced_brep_file(self):
        result = build_cube_sample(self.registry, size=10.0)
        solid = result["solid"]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "cube.step"

            saved_solid_ids = save_step_exchange(str(output_path), self.registry)

            self.assertEqual(saved_solid_ids, [solid.id])
            self.assertTrue(output_path.exists())

            text = output_path.read_text(encoding="utf-8")
            self.assertIn("ISO-10303-21;", text)
            self.assertIn("FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));", text)
            self.assertIn("ADVANCED_BREP_SHAPE_REPRESENTATION", text)
            self.assertIn("MANIFOLD_SOLID_BREP", text)
            self.assertIn("ADVANCED_FACE", text)
            self.assertIn("EDGE_CURVE", text)
            self.assertIn("PLANE", text)
            self.assertIn("CLOSED_SHELL", text)
            self.assertIn("FACE_OUTER_BOUND", text)
            self.assertIn("SI_UNIT($,.METRE.)", text)

            point_line_count = text.count("= CARTESIAN_POINT(")
            self.assertGreaterEqual(point_line_count, 8)

    def test_save_step_exchange_exports_multiple_solids_by_default(self):
        first = build_cube_sample(self.registry, size=10.0, reset_registry=True)
        second = build_plane_sample(self.registry, width=5.0, depth=3.0, reset_registry=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "multi.step"

            saved_solid_ids = save_step_exchange(str(output_path), self.registry)

            self.assertEqual(saved_solid_ids, [first["solid"].id, second["solid"].id])
            text = output_path.read_text(encoding="utf-8")
            self.assertGreaterEqual(text.count("= MANIFOLD_SOLID_BREP("), 2)

    def test_save_step_exchange_mm_unit(self):
        build_cube_sample(self.registry, size=10.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "cube_mm.step"

            save_step_exchange(str(output_path), self.registry, unit="mm")

            text = output_path.read_text(encoding="utf-8")
            self.assertIn("SI_UNIT(.MILLI.,.METRE.)", text)


if __name__ == "__main__":
    unittest.main()
