import unittest
from src.model.micro_operators import MicroOperators
from src.model.topology import Solid, Vertex, Face, Loop, Edge, HalfEdge
from src.model.id_registry import IDRegistry

class TestMicroOperators(unittest.TestCase):

    def setUp(self):
        IDRegistry().reset()
        self.micro_ops = MicroOperators()

    def test_mvfs(self):
        x, y, z = 1.0, 2.0, 3.0
        solid, vertex, face, loop = self.micro_ops.mvfs(x, y, z)

        # Verify types
        self.assertIsInstance(solid, Solid)
        self.assertIsInstance(vertex, Vertex)
        self.assertIsInstance(face, Face)
        self.assertIsInstance(loop, Loop)

        # Verify IDs (assuming IDRegistry starts from #100)
        self.assertEqual(solid.id, "#100")
        self.assertEqual(vertex.id, "#101")
        self.assertEqual(face.id, "#102")
        self.assertEqual(loop.id, "#103")

        # Verify relationships
        self.assertIn(face, solid.sfaces)
        self.assertEqual(face.fsolid, solid)
        self.assertIn(loop, face.floops)
        self.assertEqual(loop.lface, face)

        # Verify vertex coordinates
        self.assertEqual(vertex.vpoint, (x, y, z))

        # Check initial state of related attributes
        self.assertIsNone(vertex.vedge)
        self.assertIsNone(loop.ledges)

    def test_mev_first_edge(self):
        # 1. MVFS to create initial state
        solid, v1, face, loop = self.micro_ops.mvfs(0.0, 0.0, 0.0)

        # 2. MEV to add the first edge
        x2, y2, z2 = 1.0, 0.0, 0.0
        edge, v2, he1, he2 = self.micro_ops.mev(loop.id, v1.id, x2, y2, z2)

        # Verify types
        self.assertIsInstance(edge, Edge)
        self.assertIsInstance(v2, Vertex)
        self.assertIsInstance(he1, HalfEdge)
        self.assertIsInstance(he2, HalfEdge)

        # Verify IDs
        self.assertEqual(v2.id, "#104")
        self.assertEqual(edge.id, "#105")
        self.assertEqual(he1.id, "#106")
        self.assertEqual(he2.id, "#107")

        # Verify edge-halfedge relationships
        self.assertIs(edge.he1, he1)
        self.assertIs(edge.he2, he2)

        # Verify halfedge-twin relationships
        self.assertIs(he1.htwin, he2)
        self.assertIs(he2.htwin, he1)

        # Verify halfedge-vertex relationships
        self.assertIs(he1.hvertex, v2) # he1 goes to v2
        self.assertIs(he2.hvertex, v1) # he2 goes to v1

        # Verify halfedge-edge relationships
        self.assertIs(he1.hedge, edge)
        self.assertIs(he2.hedge, edge)

        # Verify halfedge-loop relationships
        self.assertIs(he1.hloop, loop)
        self.assertIs(he2.hloop, loop)

        # Verify vertex vedge
        self.assertIs(v1.vedge, he1) # v1's outgoing edge is he1
        self.assertIs(v2.vedge, he2) # v2's outgoing edge is he2 (the twin)

        # Verify loop ledges and half-edge next/prev for the first edge
        self.assertIs(loop.ledges, he1)
        self.assertIs(he1.hnext, he2)
        self.assertIs(he1.hprev, he2)
        self.assertIs(he2.hnext, he1)
        self.assertIs(he2.hprev, he1)

        # Verify new vertex coordinates
        self.assertEqual(v2.vpoint, (x2, y2, z2))

    def test_mev_second_edge(self):
        # 1. MVFS to create initial state
        solid, v1, face, loop = self.micro_ops.mvfs(0.0, 0.0, 0.0)

        # 2. MEV to add the first edge (v1 -> v2)
        edge1, v2, he1_1, he1_2 = self.micro_ops.mev(loop.id, v1.id, 1.0, 0.0, 0.0)

        # 3. MEV to add the second edge (v2 -> v3)
        x3, y3, z3 = 1.0, 1.0, 0.0
        edge2, v3, he2_1, he2_2 = self.micro_ops.mev(loop.id, v2.id, x3, y3, z3)

        # Verify IDs
        self.assertEqual(v3.id, "#108")
        self.assertEqual(edge2.id, "#109")
        self.assertEqual(he2_1.id, "#110")
        self.assertEqual(he2_2.id, "#111")

        # Verify loop structure after adding second edge
        # Loop should be: he1_1 (v1->v2) -> he2_1 (v2->v3) -> he2_2 (v3->v2) -> he1_2 (v2->v1) -> he1_1
        
        # Check next/prev pointers
        self.assertIs(he1_1.hnext, he2_1)
        self.assertIs(he2_1.hprev, he1_1)

        self.assertIs(he2_1.hnext, he2_2)
        self.assertIs(he2_2.hprev, he2_1)

        self.assertIs(he2_2.hnext, he1_2)
        self.assertIs(he1_2.hprev, he2_2)

        self.assertIs(he1_2.hnext, he1_1)
        self.assertIs(he1_1.hprev, he1_2)

        # Verify vertex vedge
        self.assertIs(v1.vedge, he1_1)
        self.assertIs(v2.vedge, he2_1) # v2's outgoing edge is now he2_1
        self.assertIs(v3.vedge, he2_2) # v3's outgoing edge is he2_2

        # Verify loop.ledges still points to he1_1
        self.assertIs(loop.ledges, he1_1)

    def test_mef_triangle(self):
        # Build a simple triangle using MVFS, MEV, MEF
        # 1. MVFS (0,0,0) -> v1, face, loop
        solid, v1, face, loop = self.micro_ops.mvfs(0.0, 0.0, 0.0) # v1: #101, loop: #103

        # 2. MEV (loop, v1, 1,0,0) -> v2, edge1, he1_1(v1->v2), he1_2(v2->v1)
        edge1, v2, he1_1, he1_2 = self.micro_ops.mev(loop.id, v1.id, 1.0, 0.0, 0.0) # v2: #104

        # 3. MEV (loop, v2, 0,1,0) -> v3, edge2, he2_1(v2->v3), he2_2(v3->v2)
        edge2, v3, he2_1, he2_2 = self.micro_ops.mev(loop.id, v2.id, 0.0, 1.0, 0.0) # v3: #108

        # At this point, the next ID to be generated is #112.

        # 4. MEF (face.id, v3.id, v1.id)
        new_edge, new_face, he_new1, he_new2 = self.micro_ops.mef(face.id, v3.id, v1.id)

        # Verify IDs
        self.assertEqual(new_edge.id, "#112")
        self.assertEqual(he_new1.id, "#113") # v3 -> v1
        self.assertEqual(he_new2.id, "#114") # v1 -> v3
        self.assertEqual(new_face.id, "#115") # Corrected
        # new_loop will be #116, but we don't assert its ID directly here.

        # Verify new face and loop
        self.assertIsInstance(new_face, Face)
        self.assertIsInstance(new_face.floops[0], Loop) # new_face should have one loop
        new_loop = new_face.floops[0]
        self.assertIs(new_loop.lface, new_face)
        self.assertIs(new_face.fsolid, solid)
        self.assertIn(new_face, solid.sfaces)
        self.assertEqual(len(solid.sfaces), 2) # Original face + new face

        # Verify half-edge relationships for new edge
        self.assertIs(new_edge.he1, he_new1)
        self.assertIs(new_edge.he2, he_new2)
        self.assertIs(he_new1.htwin, he_new2)
        self.assertIs(he_new2.htwin, he_new1)
        self.assertIs(he_new1.hedge, new_edge)
        self.assertIs(he_new2.hedge, new_edge)
        self.assertIs(he_new1.hvertex, v1) # he_new1 (v3->v1) ends at v1
        self.assertIs(he_new2.hvertex, v3) # he_new2 (v1->v3) ends at v3

        # Verify the two new loops
        # Original loop (loop): he1_1 (v1->v2) -> he2_1 (v2->v3) -> he_new1 (v3->v1) -> he1_1
        # New loop (new_loop): he_new2 (v1->v3) -> he2_2 (v3->v2) -> he1_2 (v2->v1) -> he_new2

        # Check original loop
        self.assertIs(loop.ledges, he1_1)
        self.assertIs(he1_1.hnext, he2_1)
        self.assertIs(he2_1.hnext, he_new1)
        self.assertIs(he_new1.hnext, he1_1)

        self.assertIs(he1_1.hprev, he_new1)
        self.assertIs(he_new1.hprev, he2_1)
        self.assertIs(he2_1.hprev, he1_1)

        # Check new loop
        self.assertIs(new_loop.ledges, he_new2)
        self.assertIs(he_new2.hnext, he2_2)
        self.assertIs(he2_2.hnext, he1_2)
        self.assertIs(he1_2.hnext, he_new2)

        self.assertIs(he_new2.hprev, he1_2)
        self.assertIs(he1_2.hprev, he2_2)
        self.assertIs(he2_2.hprev, he_new2)

        # Verify hloop references
        self.assertIs(he1_1.hloop, loop)
        self.assertIs(he2_1.hloop, loop)
        self.assertIs(he_new1.hloop, loop)

        self.assertIs(he_new2.hloop, new_loop)
        self.assertIs(he2_2.hloop, new_loop)
        self.assertIs(he1_2.hloop, new_loop)

        # Verify vertex vedge updates
        self.assertIs(v1.vedge, he_new2) # v1's outgoing edge is now he_new2 (v1->v3)
        self.assertIs(v3.vedge, he_new1) # v3's outgoing edge is now he_new1 (v3->v1)

    def test_mekr_create_hole(self):
        # Build a square face (v1-v2-v3-v4-v1)
        # 1. MVFS (0,0,0) -> v1, face, loop
        solid, v1, face, loop = self.micro_ops.mvfs(0.0, 0.0, 0.0) # v1: #101, loop: #103

        # 2. MEV (loop, v1, 1,0,0) -> v2
        edge1, v2, he1_1, he1_2 = self.micro_ops.mev(loop.id, v1.id, 1.0, 0.0, 0.0) # v2: #104

        # 3. MEV (loop, v2, 1,1,0) -> v3
        edge2, v3, he2_1, he2_2 = self.micro_ops.mev(loop.id, v2.id, 1.0, 1.0, 0.0) # v3: #108

        # 4. MEV (loop, v3, 0,1,0) -> v4
        edge3, v4, he3_1, he3_2 = self.micro_ops.mev(loop.id, v3.id, 0.0, 1.0, 0.0) # v4: #112

        # 5. MEF (face.id, v4.id, v1.id) to close the square
        # This creates a square face.
        edge4, square_face, he4_1, he4_2 = self.micro_ops.mef(face.id, v4.id, v1.id)
        # edge4: #116, square_face: #119, he4_1: #117 (v4->v1), he4_2: #118 (v1->v4)
        
        # At this point, the solid should have 2 faces (original 'face' and 'square_face').
        self.assertEqual(len(solid.sfaces), 2)
        self.assertIs(solid.sfaces[1], square_face) 
        self.assertEqual(len(square_face.floops), 1)
        square_outer_loop = square_face.floops[0]
        self.assertEqual(square_outer_loop.id, "#120")

        # Now, create an inner loop (hole) using MEKR (v1 to v3)
        # This will split the square_outer_loop into two loops.
        # One will remain the outer loop, the other will become the inner loop.
        inner_edge, inner_loop, he_inner1, he_inner2 = self.micro_ops.mekr(square_face.id, v3.id, v1.id)
        # inner_edge: #121, inner_loop: #124, he_inner1: #122 (v3->v1), he_inner2: #123 (v1->v3)

        # Verify IDs
        self.assertEqual(inner_edge.id, "#121")
        self.assertEqual(inner_loop.id, "#124")
        self.assertEqual(he_inner1.id, "#122")
        self.assertEqual(he_inner2.id, "#123")

        # Verify new inner loop
        self.assertIsInstance(inner_loop, Loop)
        self.assertIs(inner_loop.lface, square_face)
        self.assertIn(inner_loop, square_face.floops)
        self.assertEqual(len(square_face.floops), 2) # Outer loop + inner loop

        # Verify half-edge relationships for inner edge
        self.assertIs(inner_edge.he1, he_inner1)
        self.assertIs(inner_edge.he2, he_inner2)
        self.assertIs(he_inner1.htwin, he_inner2)
        self.assertIs(he_inner2.htwin, he_inner1)
        self.assertIs(he_inner1.hedge, inner_edge)
        self.assertIs(he_inner2.hedge, inner_edge)
        self.assertIs(he_inner1.hvertex, v1) # he_inner1 (v3->v1) ends at v1
        self.assertIs(he_inner2.hvertex, v3) # he_inner2 (v1->v3) ends at v3

        # Verify the two loops in square_face
        # Outer loop (square_outer_loop): he4_2 (v1->v4) -> he3_1 (v4->v3) -> he_inner1 (v3->v1) -> he4_2
        # Inner loop (inner_loop): he_inner2 (v1->v3) -> he2_1 (v3->v2) -> he1_1 (v2->v1) -> he_inner2
        
        # Check outer loop
        self.assertIs(square_outer_loop.ledges, he4_2)
        self.assertIs(he4_2.hnext, he3_1)
        self.assertIs(he3_1.hnext, he_inner1)
        self.assertIs(he_inner1.hnext, he4_2)

        self.assertIs(he4_2.hprev, he_inner1)
        self.assertIs(he_inner1.hprev, he3_1)
        self.assertIs(he3_1.hprev, he4_2)

        # Check inner loop
        self.assertIs(inner_loop.ledges, he_inner2)
        self.assertIs(he_inner2.hnext, he2_1)
        self.assertIs(he2_1.hnext, he1_1)
        self.assertIs(he1_1.hnext, he_inner2)

        self.assertIs(he_inner2.hprev, he1_1)
        self.assertIs(he1_1.hprev, he2_1)
        self.assertIs(he2_1.hprev, he_inner2)

        # Verify hloop references
        self.assertIs(he4_2.hloop, square_outer_loop)
        self.assertIs(he3_1.hloop, square_outer_loop)
        self.assertIs(he_inner1.hloop, square_outer_loop)

        self.assertIs(he_inner2.hloop, inner_loop)
        self.assertIs(he2_1.hloop, inner_loop)
        self.assertIs(he1_1.hloop, inner_loop)

        # Verify vertex vedge updates
        self.assertIs(v1.vedge, he_inner2) # v1's outgoing edge is now he_inner2 (v1->v3)
        self.assertIs(v3.vedge, he_inner1) # v3's outgoing edge is now he_inner1 (v3->v1)

    def test_kemr_close_hole(self):
        # Build a square face (v1-v2-v3-v4-v1) and create an inner loop (hole)
        # 1. MVFS (0,0,0) -> v1, face, loop
        solid, v1, face, loop = self.micro_ops.mvfs(0.0, 0.0, 0.0) # v1: #101, loop: #103

        # 2. MEV (loop, v1, 1,0,0) -> v2
        edge1, v2, he1_1, he1_2 = self.micro_ops.mev(loop.id, v1.id, 1.0, 0.0, 0.0) # v2: #104

        # 3. MEV (loop, v2, 1,1,0) -> v3
        edge2, v3, he2_1, he2_2 = self.micro_ops.mev(loop.id, v2.id, 1.0, 1.0, 0.0) # v3: #108

        # 4. MEV (loop, v3, 0,1,0) -> v4
        edge3, v4, he3_1, he3_2 = self.micro_ops.mev(loop.id, v3.id, 0.0, 1.0, 0.0) # v4: #112

        # 5. MEF (face.id, v4.id, v1.id) to close the square
        edge4, square_face, he4_1, he4_2 = self.micro_ops.mef(face.id, v4.id, v1.id)
        
        # At this point, the solid should have 2 faces (original 'face' and 'square_face').
        self.assertEqual(len(solid.sfaces), 2)
        square_outer_loop = square_face.floops[0]

        # Now, create an inner loop (hole) using MEKR (v1 to v3)
        inner_edge, inner_loop, he_inner1, he_inner2 = self.micro_ops.mekr(square_face.id, v3.id, v1.id)
        
        # Verify that square_face now has two loops (outer and inner)
        self.assertEqual(len(square_face.floops), 2)

        # Perform KEMR on the inner_edge to close the hole
        modified_loop = self.micro_ops.kemr(inner_edge.id)

        # Verify KEMR results
        # The square_face should now have only one loop (the outer loop)
        self.assertEqual(len(square_face.floops), 1)
        
        # The modified loop should be the original square outer loop.
        self.assertIs(modified_loop, square_outer_loop)
        
        # Check if the inner_edge, its half-edges, and the inner_loop are removed from registry
        self.assertIsNone(self.registry.get_object(inner_edge.id))
        self.assertIsNone(self.registry.get_object(he_inner1.id))
        self.assertIsNone(self.registry.get_object(he_inner2.id))
        self.assertIsNone(self.registry.get_object(inner_loop.id))

        # Verify the outer loop is restored to its original square state
        # The half-edges should be: he4_2 (v1->v4) -> he3_1 (v4->v3) -> he2_1 (v3->v2) -> he1_1 (v2->v1) -> he4_2
        
        # Check the sequence of half-edges in the modified loop
        self.assertIs(square_outer_loop.ledges, he4_2) # The loop should start with he4_2 (v1->v4)

        self.assertIs(he4_2.hnext, he3_1)
        self.assertIs(he3_1.hnext, he2_1)
        self.assertIs(he2_1.hnext, he1_1)
        self.assertIs(he1_1.hnext, he4_2) # Loop closes

        self.assertIs(he4_2.hprev, he1_1)
        self.assertIs(he1_1.hprev, he2_1)
        self.assertIs(he2_1.hprev, he3_1)
        self.assertIs(he3_1.hprev, he4_2)

        # Verify hloop references for all remaining half-edges
        self.assertIs(he1_1.hloop, square_outer_loop)
        self.assertIs(he2_1.hloop, square_outer_loop)
        self.assertIs(he3_1.hloop, square_outer_loop)
        self.assertIs(he4_1.hloop, square_outer_loop)
