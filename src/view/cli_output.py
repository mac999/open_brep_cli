from src.model.topology import Solid, Face, Loop, Edge, HalfEdge, Vertex

def display_topology(solid: Solid):
    """
    Prints the full Half-Edge pointer tree for a given solid.
    """
    print(f"Solid: {solid.id}")
    for face in solid.sfaces:
        print(f"  Face: {face.id}")
        for loop in face.floops:
            print(f"    Loop: {loop.id}")
            if loop.ledges:
                current_he = loop.ledges
                start_he = loop.ledges
                he_count = 0
                while True:
                    print(f"      HalfEdge: {current_he.id} (from {current_he.hprev.hvertex.id if current_he.hprev else 'None'} to {current_he.hvertex.id})")
                    print(f"        Edge: {current_he.hedge.id}")
                    print(f"        Twin: {current_he.htwin.id}")
                    print(f"        Next: {current_he.hnext.id}")
                    print(f"        Prev: {current_he.hprev.id}")
                    print(f"        Vertex (end): {current_he.hvertex.id} at {current_he.hvertex.vpoint}")
                    
                    # To avoid infinite loops in case of malformed topology
                    he_count += 1
                    if he_count > 100: # Arbitrary limit
                        print("        (Loop traversal limit reached, potential malformed loop)")
                        break

                    current_he = current_he.hnext
                    if current_he == start_he:
                        break
            else:
                print("      (Empty Loop)")
    
    # Also print all vertices for completeness
    # This requires iterating through all objects in the registry or collecting them during traversal
    # For now, let's just print the vertices that are part of the solid's faces/loops
    # A better approach would be to have a way to get all vertices in the solid.
    # For now, we can collect them during traversal.
    
    all_vertices = set()
    for face in solid.sfaces:
        for loop in face.floops:
            if loop.ledges:
                current_he = loop.ledges
                start_he = loop.ledges
                while True:
                    all_vertices.add(current_he.hvertex)
                    current_he = current_he.hnext
                    if current_he == start_he:
                        break
    
    print("\nVertices in Solid:")
    for vertex in all_vertices:
        print(f"  Vertex: {vertex.id} at {vertex.vpoint}")
