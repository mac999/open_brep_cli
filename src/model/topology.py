from src.model.id_registry import IDRegistry

class Solid:
    def __init__(self):
        self.sfaces = []  # List of faces in the solid
        self.id = IDRegistry().generate_id(self)

    def __repr__(self):
        return f"Solid(id={self.id}, faces={len(self.sfaces)})"

class Face:
    def __init__(self, solid):
        self.floops = []  # List of loops in the face (outer loop and inner loops/holes)
        self.fsolid = solid # Reference to the parent solid
        self.id = IDRegistry().generate_id(self)
        solid.sfaces.append(self)

    def __repr__(self):
        return f"Face(id={self.id}, loops={len(self.floops)})"

class Loop:
    def __init__(self, face):
        self.ledges = None  # Reference to one of the half-edges in the loop
        self.lface = face # Reference to the parent face
        self.id = IDRegistry().generate_id(self)
        face.floops.append(self)

    def __repr__(self):
        return f"Loop(id={self.id})"

class Edge:
    def __init__(self):
        self.he1 = None  # Reference to one of the half-edges
        self.he2 = None  # Reference to the other half-edge (twin)
        self.id = IDRegistry().generate_id(self)

    def __repr__(self):
        return f"Edge(id={self.id})"

class HalfEdge:
    def __init__(self, vertex, edge, loop):
        self.hvertex = vertex  # Vertex at the end of this half-edge
        self.hedge = edge      # Reference to the parent edge
        self.hloop = loop      # Reference to the parent loop
        self.hnext = None      # Next half-edge in the loop
        self.hprev = None      # Previous half-edge in the loop
        self.htwin = None      # Twin half-edge
        self.id = IDRegistry().generate_id(self)

    def __repr__(self):
        return f"HalfEdge(id={self.id}, vertex={self.hvertex.id if self.hvertex else 'None'})"

class Vertex:
    def __init__(self, x, y, z):
        self.vpoint = (x, y, z) # Geometric coordinates
        self.vedge = None      # One of the half-edges originating from this vertex
        self.id = IDRegistry().generate_id(self)

    def __repr__(self):
        return f"Vertex(id={self.id}, point={self.vpoint})"
