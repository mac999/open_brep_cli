class IDRegistry:
    _instance = None
    _next_id = 100
    _registry = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IDRegistry, cls).__new__(cls)
        return cls._instance

    def generate_id(self, obj):
        """Generates a unique ID for an object and registers it."""
        new_id = f"#{self._next_id}"
        self._next_id += 1
        self._registry[new_id] = obj
        return new_id

    def get_object(self, obj_id):
        """Retrieves an object by its ID."""
        return self._registry.get(obj_id)

    def remove_object(self, obj_id):
        """Removes an object from the registry by its ID."""
        if obj_id in self._registry:
            del self._registry[obj_id]
            return True
        return False

    def reset(self):
        """Resets the registry for testing purposes."""
        self._next_id = 100
        self._registry = {}
