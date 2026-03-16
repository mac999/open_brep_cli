import unittest
from src.model.id_registry import IDRegistry

class TestIDRegistry(unittest.TestCase):

    def setUp(self):
        # Ensure a clean state before each test
        IDRegistry().reset()

    def test_singleton(self):
        registry1 = IDRegistry()
        registry2 = IDRegistry()
        self.assertIs(registry1, registry2)

    def test_generate_id_and_get_object(self):
        registry = IDRegistry()
        obj1 = {"name": "Object 1"}
        obj2 = {"name": "Object 2"}

        id1 = registry.generate_id(obj1)
        id2 = registry.generate_id(obj2)

        self.assertEqual(id1, "#100")
        self.assertEqual(id2, "#101")
        self.assertIsNot(id1, id2)

        self.assertIs(registry.get_object(id1), obj1)
        self.assertIs(registry.get_object(id2), obj2)
        self.assertIsNone(registry.get_object("#999")) # Non-existent ID

    def test_remove_object(self):
        registry = IDRegistry()
        obj1 = {"name": "Object to remove"}
        id1 = registry.generate_id(obj1)

        self.assertIs(registry.get_object(id1), obj1)
        self.assertTrue(registry.remove_object(id1))
        self.assertIsNone(registry.get_object(id1))
        self.assertFalse(registry.remove_object("#999")) # Removing non-existent ID

    def test_reset(self):
        registry = IDRegistry()
        obj1 = {"name": "Object for reset"}
        registry.generate_id(obj1)
        
        self.assertIsNotNone(registry.get_object("#100"))
        registry.reset()
        self.assertIsNone(registry.get_object("#100"))
        
        obj2 = {"name": "Object after reset"}
        id2 = registry.generate_id(obj2)
        self.assertEqual(id2, "#100") # IDs should restart from #100

if __name__ == '__main__':
    unittest.main()
