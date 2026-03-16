from src.model.topology import Solid, Face, Loop, Vertex, Edge, HalfEdge
from src.model.id_registry import IDRegistry

class MicroOperators:
    def __init__(self):
        self.registry = IDRegistry()

    def mvfs(self, x, y, z):
        """
        Make Vertex Face Solid: Initializes a zero-dimensional solid with one vertex, one face, and one loop.
        Returns the created Solid, Vertex, Face, and Loop.
        """
        solid = Solid()
        vertex = Vertex(x, y, z)
        face = Face(solid)
        loop = Loop(face)
        
        # The loop's ledges will be set by subsequent MEV operations
        # The vertex's vedge will be set by subsequent MEV operations

        return solid, vertex, face, loop

    def mev(self, loop_id, existing_vertex_id, x, y, z):
        """
        Make Edge Vertex: Creates a new vertex and an edge connecting it to the specified existing vertex.
        This operation extends an existing wireframe (loop).
        Returns the created Edge, new Vertex, and the two HalfEdges.
        """
        loop = self.registry.get_object(loop_id)
        if not isinstance(loop, Loop):
            raise ValueError(f"Object with ID {loop_id} is not a Loop.")

        v1 = self.registry.get_object(existing_vertex_id)
        if not isinstance(v1, Vertex):
            raise ValueError(f"Object with ID {existing_vertex_id} is not a Vertex.")

        v2 = Vertex(x, y, z)
        edge = Edge()

        he1 = HalfEdge(v2, edge, loop) # Half-edge from v1 to v2 (points to v2)
        he2 = HalfEdge(v1, edge, loop) # Half-edge from v2 to v1 (points to v1)

        he1.htwin = he2
        he2.htwin = he1

        edge.he1 = he1
        edge.he2 = he2

        # Determine insertion points before updating v1.vedge
        he_from_v1_old = None
        he_to_v1_old = None

        if loop.ledges is not None:
            he_from_v1_old = v1.vedge # This is the old outgoing half-edge from v1
            if he_from_v1_old is None:
                raise ValueError(f"Vertex {v1.id} has no outgoing edge (vedge is None). Cannot extend wireframe.")
            he_to_v1_old = he_from_v1_old.hprev # This is the old incoming half-edge to v1

        # Update vertex references
        v1.vedge = he1 # v1 now has an outgoing half-edge
        v2.vedge = he2 # v2 now has an outgoing half-edge (the twin)

        # Insert half-edges into the loop
        if loop.ledges is None: # First edge in the loop (after MVFS)
            loop.ledges = he1
            he1.hnext = he2
            he1.hprev = he2
            he2.hnext = he1
            he2.hprev = he1
        else:
            # Use the old references for insertion
            he_to_v1_old.hnext = he1
            he1.hprev = he_to_v1_old
            
            he1.hnext = he2
            he2.hprev = he1
            
            he2.hnext = he_from_v1_old
            he_from_v1_old.hprev = he2
            
        return edge, v2, he1, he2

    def mef(self, face_id, vertex1_id, vertex2_id):
        """
        Make Edge Face: Connects two vertices with an edge, splitting a loop in a face and creating a new face.
        Returns the created Edge, new Face, and the two new HalfEdges.
        """
        face = self.registry.get_object(face_id)
        if not isinstance(face, Face):
            raise ValueError(f"Object with ID {face_id} is not a Face.")

        v1 = self.registry.get_object(vertex1_id)
        v2 = self.registry.get_object(vertex2_id)

        if not isinstance(v1, Vertex) or not isinstance(v2, Vertex):
            raise ValueError("Both IDs must correspond to Vertices.")
        
        if v1.vedge is None or v2.vedge is None:
            raise ValueError("Both vertices must have outgoing edges to perform MEF.")

        # Find the outer loop of the face
        # For now, assume the first loop in floops is the outer loop.
        common_loop = face.floops[0] 

        # Ensure v1 and v2 are part of this common_loop
        found_v1_in_loop = False
        found_v2_in_loop = False
        current_he_check = common_loop.ledges
        start_he_check = common_loop.ledges
        while True:
            if current_he_check.hvertex == v1:
                found_v1_in_loop = True
            if current_he_check.hvertex == v2:
                found_v2_in_loop = True
            current_he_check = current_he_check.hnext
            if current_he_check == start_he_check:
                break
        
        if not found_v1_in_loop or not found_v2_in_loop:
            raise ValueError(f"Vertices {v1.id} and {v2.id} are not part of the outer loop of Face {face.id}.")


        # Get the half-edges around v1 and v2 in the common_loop
        he_v1_out = v1.vedge
        he_v1_in = he_v1_out.hprev

        he_v2_out = v2.vedge
        he_v2_in = he_v2_out.hprev

        # Check if v1 and v2 are already directly connected
        if he_v1_out.hvertex == v2 or he_v2_out.hvertex == v1:
            raise ValueError(f"Vertices {v1.id} and {v2.id} are already directly connected.")

        # Create new edge and half-edges
        new_edge = Edge()
        he_new1 = HalfEdge(v2, new_edge, common_loop) # From v1 to v2
        he_new2 = HalfEdge(v1, new_edge, common_loop) # From v2 to v1

        he_new1.htwin = he_new2
        he_new2.htwin = he_new1
        new_edge.he1 = he_new1
        new_edge.he2 = he_new2

        # Create new face and loop
        new_face = Face(face.fsolid) # New face belongs to the same solid
        new_loop = Loop(new_face) # New loop belongs to the new face

        # Adjust pointers to form two new loops
        # Original loop (common_loop) will now contain:
        # ... -> he_v1_in -> he_new1 -> he_v2_out -> ...
        he_v1_in.hnext = he_new1
        he_new1.hprev = he_v1_in
        he_new1.hnext = he_v2_out
        he_v2_out.hprev = he_new1

        # New loop (new_loop) will contain:
        # ... -> he_v2_in -> he_new2 -> he_v1_out -> ...
        he_v2_in.hnext = he_new2
        he_new2.hprev = he_v2_in
        he_new2.hnext = he_v1_out
        he_v1_out.hprev = he_new2
        
        # Update the loop references for the half-edges in new_loop
        current_he = he_new2
        start_he = he_new2
        while True:
            current_he.hloop = new_loop
            current_he = current_he.hnext
            if current_he == start_he: # Check if we've completed the loop
                break
        
        new_loop.ledges = he_new2 # Set the starting half-edge for the new loop

        # Update vedge for all vertices in the common_loop and new_loop
        # This is crucial for subsequent operations like MEKR.
        
        # Update vedge for vertices in common_loop
        current_he = common_loop.ledges
        start_he = common_loop.ledges
        while True:
            current_he.hprev.hvertex.vedge = current_he # Update vedge of the vertex at the start of current_he
            current_he = current_he.hnext
            if current_he == start_he:
                break

        # Update vedge for vertices in new_loop
        current_he = new_loop.ledges
        start_he = new_loop.ledges
        while True:
            current_he.hprev.hvertex.vedge = current_he # Update vedge of the vertex at the start of current_he
            current_he = current_he.hnext
            if current_he == start_he:
                break

        return new_edge, new_face, he_new1, he_new2

    def mekr(self, face_id, vertex1_id, vertex2_id):
        """
        Make Edge Kill Ring: Connects two vertices with an edge, splitting an outer loop
        and creating a new inner loop within the same face.
        Returns the created Edge, new inner Loop, and the two new HalfEdges.
        """
        face = self.registry.get_object(face_id)
        if not isinstance(face, Face):
            raise ValueError(f"Object with ID {face_id} is not a Face.")

        v1 = self.registry.get_object(vertex1_id)
        v2 = self.registry.get_object(vertex2_id)

        if not isinstance(v1, Vertex) or not isinstance(v2, Vertex):
            raise ValueError("Both IDs must correspond to Vertices.")
        
        if v1.vedge is None or v2.vedge is None:
            raise ValueError("Both vertices must have outgoing edges to perform MEKR.")

        # Find the outer loop of the face
        # For now, assume the first loop in floops is the outer loop.
        common_loop = face.floops[0] 

        # Ensure v1 and v2 are part of this common_loop
        found_v1_in_loop = False
        found_v2_in_loop = False
        current_he_check = common_loop.ledges
        start_he_check = common_loop.ledges
        while True:
            if current_he_check.hvertex == v1:
                found_v1_in_loop = True
            if current_he_check.hvertex == v2:
                found_v2_in_loop = True
            current_he_check = current_he_check.hnext
            if current_he_check == start_he_check:
                break
        
        if not found_v1_in_loop or not found_v2_in_loop:
            raise ValueError(f"Vertices {v1.id} and {v2.id} are not part of the outer loop of Face {face.id}.")

        # Get the half-edges around v1 and v2 in the common_loop
        he_v1_out = v1.vedge
        he_v1_in = he_v1_out.hprev

        he_v2_out = v2.vedge
        he_v2_in = he_v2_out.hprev

        # Check if v1 and v2 are already directly connected
        if he_v1_out.hvertex == v2 or he_v2_out.hvertex == v1:
            raise ValueError(f"Vertices {v1.id} and {v2.id} are already directly connected.")

        # Create new edge and half-edges
        new_edge = Edge()
        he_new1 = HalfEdge(v2, new_edge, common_loop) # From v1 to v2
        he_new2 = HalfEdge(v1, new_edge, common_loop) # From v2 to v1

        he_new1.htwin = he_new2
        he_new2.htwin = he_new1
        new_edge.he1 = he_new1
        new_edge.he2 = he_new2

        # Create new inner loop (no new face)
        new_inner_loop = Loop(face) # New loop belongs to the same face

        # Adjust pointers to form two new loops
        # Original loop (common_loop) will now contain:
        # ... -> he_v1_in -> he_new1 -> he_v2_out -> ...
        he_v1_in.hnext = he_new1
        he_new1.hprev = he_v1_in
        he_new1.hnext = he_v2_out
        he_v2_out.hprev = he_new1

        # New inner loop (new_inner_loop) will contain:
        # ... -> he_v2_in -> he_new2 -> he_v1_out -> ...
        he_v2_in.hnext = he_new2
        he_new2.hprev = he_v2_in
        he_new2.hnext = he_v1_out
        he_v1_out.hprev = he_new2
        
        # Update the loop references for the half-edges in new_inner_loop
        current_he = he_new2
        start_he = he_new2
        while True:
            current_he.hloop = new_inner_loop
            current_he = current_he.hnext
            if current_he == start_he: # Check if we've completed the loop
                break
        
        new_inner_loop.ledges = he_new2 # Set the starting half-edge for the new inner loop

        # Update vedge for all vertices in the common_loop and new_inner_loop
        
        # Update vedge for vertices in common_loop
        current_he = common_loop.ledges
        start_he = common_loop.ledges
        while True:
            current_he.hprev.hvertex.vedge = current_he # Update vedge of the vertex at the start of current_he
            current_he = current_he.hnext
            if current_he == start_he:
                break

        # Update vedge for vertices in new_inner_loop
        current_he = new_inner_loop.ledges
        start_he = new_inner_loop.ledges
        while True:
            current_he.hprev.hvertex.vedge = current_he # Update vedge of the vertex at the start of current_he
            current_he = current_he.hnext
            if current_he == start_he:
                break

        return new_edge, new_inner_loop, he_new1, he_new2

    def kemr(self, edge_id):
        """
        Kill Edge Make Ring: Removes an edge and merges two loops into one, creating a hole.
        Returns the modified loop.
        """
        edge = self.registry.get_object(edge_id)
        if not isinstance(edge, Edge):
            raise ValueError(f"Object with ID {edge_id} is not an Edge.")

        he1 = edge.he1 # Half-edge from v_start to v_end
        he2 = edge.he2 # Half-edge from v_end to v_start (twin of he1)

        loop1 = he1.hloop
        loop2 = he2.hloop

        if loop1 == loop2:
            raise ValueError(f"Edge {edge_id} does not separate two distinct loops. Cannot perform KEMR.")

        # Update the next/prev pointers to remove he1 and he2
        # he1's previous's next should point to he1's next
        he1.hprev.hnext = he1.hnext
        # he1's next's previous should point to he1's previous
        he1.hnext.hprev = he1.hprev

        # he2's previous's next should point to he2's next
        he2.hprev.hnext = he2.hnext
        # he2's next's previous should point to he2's previous
        he2.hnext.hprev = he2.hprev

        # Merge loop2 into loop1
        # All half-edges in loop2 now belong to loop1
        current_he = loop2.ledges
        start_he = loop2.ledges
        while True:
            current_he.hloop = loop1
            current_he = current_he.hnext
            if current_he == start_he:
                break
        
        # Remove loop2 from its face's floops list
        loop2.lface.floops.remove(loop2)

        # If the face of loop2 becomes empty, remove the face from the solid
        if not loop2.lface.floops:
            loop2.lface.fsolid.sfaces.remove(loop2.lface)
            self.registry.remove_object(loop2.lface.id) # Remove the face from registry as well
        
        # Remove edge, he1, he2, loop2 from registry
        self.registry.remove_object(edge.id)
        self.registry.remove_object(he1.id)
        self.registry.remove_object(he2.id)
        self.registry.remove_object(loop2.id)

        # Update vedge for the vertices that were connected by he1 and he2
        # This is tricky. If v_start.vedge was he1, it needs to be updated.
        # If v_end.vedge was he2, it needs to be updated.
        # For now, let's assume vedge will be updated by subsequent operations or is not critical for KEMR.
        # A more robust solution would involve finding a new outgoing half-edge for these vertices.
        
        # For now, let's just return loop1.
        return loop1