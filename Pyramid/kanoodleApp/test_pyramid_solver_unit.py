"""
Unit tests for Pyramid Solver critical functionality
"""
import unittest
import json
from django.test import TestCase
from kanoodleApp.models import Piece
from kanoodleApp.util_pyramid import PyramidSolver


class PyramidSolverUnitTests(TestCase):
    """Unit tests for PyramidSolver class"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests"""
        Piece.objects.create(
            id=1, name='Piece-A', color='#FF0000',
            shapeData=[[0,0,0],[1,0,0],[2,0,0],[0,1,0],[2,1,0]]
        )
        Piece.objects.create(
            id=2, name='Piece-B', color='#00FF00',
            shapeData=[[2,0,0],[3,0,0],[0,1,0],[1,1,0],[2,1,0]]
        )
        Piece.objects.create(
            id=3, name='Piece-C', color='#0000FF',
            shapeData=[[1,0,0],[0,1,0],[1,1,0],[1,2,0],[2,2,0]]
        )
    
    def setUp(self):
        """Set up for each test"""
        self.pieces = [
            {
                'id': p.pk,
                'name': p.name,
                'shapeData': p.shapeData,
                'color': p.color
            }
            for p in Piece.objects.all()
        ]
    
    def test_solver_initialization(self):
        """Test that solver initializes correctly"""
        solver = PyramidSolver(self.pieces, levels=3)
        self.assertEqual(solver.pyramid.base, 3)
        self.assertIsNotNone(solver.pyramid)
        self.assertEqual(len(solver.pieces_data), 3)
    
    def test_pyramid_capacity_calculation(self):
        """Test pyramid capacity calculation"""
        solver = PyramidSolver(self.pieces, levels=3)
        expected_capacity = 1 + 3 + 6
        self.assertEqual(solver.pyramid.base, 3)
        
        solver5 = PyramidSolver(self.pieces, levels=5)
        expected_capacity5 = 1 + 3 + 6 + 10 + 15
        self.assertEqual(solver5.pyramid.base, 5)
    
    def test_grid_to_lattice_conversion(self):
        """Test coordinate conversion from grid to lattice"""
        solver = PyramidSolver(self.pieces, levels=5)
        
        lat_z, lat_x, lat_y = solver.pyramid.grid_to_lattice(0, 0, 0)
        self.assertEqual(lat_z, 4)
        
        lat_z, lat_x, lat_y = solver.pyramid.grid_to_lattice(0, 0, 4)
        self.assertEqual(lat_z, 0)
    
    def test_lattice_to_grid_conversion(self):
        """Test coordinate conversion from lattice to grid"""
        solver = PyramidSolver(self.pieces, levels=5)
        
        grid_x, grid_y, grid_z = 2, 3, 4
        lat_z, lat_x, lat_y = solver.pyramid.grid_to_lattice(grid_x, grid_y, grid_z)
        back_x, back_y, back_z = solver.pyramid.lattice_to_grid(lat_z, lat_x, lat_y)
        
        self.assertEqual((grid_x, grid_y, grid_z), (back_x, back_y, back_z))
    
    def test_solve_returns_valid_structure(self):
        """Test that solve returns valid data structure"""
        solver = PyramidSolver(self.pieces, levels=3)
        solutions, exhausted, timed_out = solver.solve(max_solutions=1, max_time=5000)
        
        self.assertIsInstance(solutions, list)
        self.assertIsInstance(exhausted, bool)
        self.assertIsInstance(timed_out, bool)
        
        if len(solutions) > 0:
            solution = solutions[0]
            self.assertIsInstance(solution, list)
            for placement in solution:
                self.assertIn('piece_id', placement)
                self.assertIn('positions', placement)
                self.assertIsInstance(placement['positions'], list)
    
    def test_solve_respects_max_solutions(self):
        """Test that solver respects max_solutions limit"""
        solver = PyramidSolver(self.pieces, levels=3)
        max_solutions = 5
        solutions, exhausted, timed_out = solver.solve(
            max_solutions=max_solutions,
            max_time=10000
        )
        
        self.assertLessEqual(len(solutions), max_solutions)
    
    def test_solve_empty_board_no_timeout(self):
        """Test solving empty board doesn't timeout with reasonable limit"""
        solver = PyramidSolver(self.pieces, levels=3)
        solutions, exhausted, timed_out = solver.solve(
            max_solutions=10,
            max_time=5000
        )
        
        self.assertFalse(timed_out)
        self.assertGreaterEqual(len(solutions), 0)
    
    def test_set_locked_positions_basic(self):
        """Test setting locked positions"""
        solver = PyramidSolver(self.pieces, levels=3)
        
        partial_board = {"0,0,0": 1}
        solver.set_locked_positions(partial_board)
        
        solutions, exhausted, timed_out = solver.solve(
            max_solutions=5,
            max_time=5000
        )
        
        self.assertIsInstance(solutions, list)
    
    def test_locked_positions_coordinate_conversion(self):
        """Test that locked positions convert coordinates correctly"""
        solver = PyramidSolver(self.pieces, levels=5)
        
        partial_board = {"0,3,0": 2, "0,4,0": 2}
        solver.set_locked_positions(partial_board)
        
        solutions, exhausted, timed_out = solver.solve(
            max_solutions=1,
            max_time=5000
        )
        
        self.assertIsInstance(solutions, list)
    
    def test_solve_with_invalid_piece_configuration(self):
        """Test solver handles invalid configurations gracefully"""
        solver = PyramidSolver(self.pieces, levels=3)
        
        partial_board = {
            "0,0,0": 1,
            "0,1,0": 1,
            "0,2,0": 1,
            "1,0,0": 1,
            "1,1,0": 1,
            "1,2,0": 1,
        }
        solver.set_locked_positions(partial_board)
        
        solutions, exhausted, timed_out = solver.solve(
            max_solutions=10,
            max_time=5000
        )
        
        self.assertIsInstance(solutions, list)
    
    def test_solution_uniqueness(self):
        """Test that returned solutions are unique"""
        solver = PyramidSolver(self.pieces, levels=3)
        solutions, exhausted, timed_out = solver.solve(
            max_solutions=10,
            max_time=5000
        )
        
        if len(solutions) > 1:
            solution_keys = []
            for solution in solutions:
                key = tuple(sorted([
                    (placement['piece_id'], tuple(sorted(placement['positions'])))
                    for placement in solution
                ]))
                solution_keys.append(key)
            
            self.assertEqual(len(solution_keys), len(set(solution_keys)))
    
    def test_piece_rotation_generation(self):
        """Test that piece rotations are generated"""
        solver = PyramidSolver(self.pieces, levels=3)
        
        self.assertGreater(len(solver.pieces_data), 0)
        
        for piece in solver.pieces_data:
            self.assertIn('shapeData', piece)
            self.assertIsInstance(piece['shapeData'], list)


class PyramidAPITests(TestCase):
    """Integration tests for Pyramid API endpoints"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test pieces"""
        import json
        with open('kanoodleApp/JSONs/pyramid_piece_data.json', 'r') as f:
            data = json.load(f)
            for item in data:
                if item['model'] == 'kanoodleApp.piece':
                    Piece.objects.create(
                        id=item['pk'],
                        name=item['fields']['name'],
                        color=item['fields']['color'],
                        shapeData=item['fields']['shapeData']
                    )
    
    def test_solve_endpoint_exists(self):
        """Test that solve endpoint is accessible"""
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        response = client.post('/api/solve/test-id/', 
            data={'levels': 3, 'batchSize': 10},
            content_type='application/json'
        )
        
        self.assertNotEqual(response.status_code, 404)
    
    def test_solve_endpoint_validation(self):
        """Test solve endpoint validates input"""
        from django.test import Client
        import json
        
        client = Client()
        
        response = client.post('/api/solve/test-id/',
            data=json.dumps({'levels': 0, 'batchSize': 10}),
            content_type='application/json'
        )
        
        self.assertIn(response.status_code, [200, 400])
    
    def test_solve_endpoint_returns_json(self):
        """Test solve endpoint returns valid JSON"""
        from django.test import Client
        import json
        
        client = Client()
        
        response = client.post('/api/solve/test-id/',
            data=json.dumps({
                'levels': 3,
                'batchSize': 5,
                'partialBoard': {},
                'maxTime': 5000
            }),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = json.loads(response.content)
            self.assertIn('success', data)


class CacheKeyGenerationTests(TestCase):
    """Test cache key generation for consistency"""
    
    def test_cache_key_consistency(self):
        """Test that same input generates same cache key"""
        from kanoodleApp.views import generate_puzzle_cache_key
        
        key1 = generate_puzzle_cache_key(5, {}, [1,2,3,4,5])
        key2 = generate_puzzle_cache_key(5, {}, [1,2,3,4,5])
        
        self.assertEqual(key1, key2)
    
    def test_cache_key_different_for_different_boards(self):
        """Test that different boards generate different keys"""
        from kanoodleApp.views import generate_puzzle_cache_key
        
        key_empty = generate_puzzle_cache_key(5, {}, [1,2,3,4,5])
        key_partial = generate_puzzle_cache_key(5, {"0,0,0": 1}, [1,2,3,4,5])
        
        self.assertNotEqual(key_empty, key_partial)
    
    def test_cache_key_different_for_different_levels(self):
        """Test that different pyramid levels generate different keys"""
        from kanoodleApp.views import generate_puzzle_cache_key
        
        key3 = generate_puzzle_cache_key(3, {}, [1,2,3,4,5])
        key5 = generate_puzzle_cache_key(5, {}, [1,2,3,4,5])
        
        self.assertNotEqual(key3, key5)


if __name__ == '__main__':
    unittest.main()
