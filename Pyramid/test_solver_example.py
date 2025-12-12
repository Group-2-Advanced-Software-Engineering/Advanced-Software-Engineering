import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polysphere.settings')
django.setup()

from kanoodleApp.util import PyramidSolver
import json

test_pieces = [
    {'id': 1, 'name': 'Piece-1', 'color': '#ff595e', 'shapeData': [[0,0,0], [1,0,0], [0,1,0], [0,0,1]]},
    {'id': 2, 'name': 'Piece-2', 'color': '#4361ee', 'shapeData': [[0,0,0], [1,0,0], [2,0,0], [0,1,0], [0,0,1]]},
    {'id': 3, 'name': 'Piece-3', 'color': '#06ffa5', 'shapeData': [[0,0,0], [1,0,0], [0,1,0], [1,1,0], [0,0,1]]},
    {'id': 4, 'name': 'Piece-4', 'color': '#ffd60a', 'shapeData': [[0,0,0], [1,0,0], [0,1,0], [0,0,1], [0,1,1]]},
    {'id': 5, 'name': 'Piece-5', 'color': '#f72585', 'shapeData': [[0,0,0], [1,0,0], [2,0,0], [3,0,0], [0,1,0]]},
    {'id': 6, 'name': 'Piece-6', 'color': '#7209b7', 'shapeData': [[0,0,0], [1,0,0], [2,0,0], [1,1,0], [0,0,1]]},
    {'id': 7, 'name': 'Piece-7', 'color': '#fb5607', 'shapeData': [[0,0,0], [0,1,0], [0,2,0], [1,1,0], [0,0,1]]},
    {'id': 8, 'name': 'Piece-8', 'color': '#4cc9f0', 'shapeData': [[0,0,0], [1,0,0], [0,1,0], [1,1,0], [1,0,1]]},
    {'id': 9, 'name': 'Piece-9', 'color': '#3a86ff', 'shapeData': [[0,0,0], [1,0,0], [1,1,0], [2,1,0], [1,0,1]]},
    {'id': 10, 'name': 'Piece-10', 'color': '#8338ec', 'shapeData': [[0,0,0], [0,1,0], [0,2,0], [0,3,0], [0,0,1]]},
    {'id': 11, 'name': 'Piece-11', 'color': '#ff006e', 'shapeData': [[0,0,0], [1,0,0], [2,0,0], [2,1,0]]},
    {'id': 12, 'name': 'Piece-12', 'color': '#38b000', 'shapeData': [[0,0,0], [1,0,0]]}
]

print("STEP 1: Validate piece data")
print("=" * 60)
total_cells = sum(len(p['shapeData']) for p in test_pieces)
print(f"Number of pieces: {len(test_pieces)}")
print(f"Total cells: {total_cells}")
print(f"Required cells: 55 (for 5-level pyramid)")

if total_cells != 55:
    print(f"ERROR: Cell count mismatch! Need 55, have {total_cells}")
    exit(1)

print("✓ Cell count is correct!")
print()

print("STEP 2: Create solver instance")
print("=" * 60)
solver = PyramidSolver(levels=5, pieces=test_pieces)
pyramid_positions = solver.get_all_pyramid_positions()
print(f"Pyramid has {len(pyramid_positions)} positions")
print()

print("STEP 3: Run solver")
print("=" * 60)
print("Parameters:")
print("  - board_state: {} (empty board)")
print("  - max_samples: 10 (return up to 10 solutions)")
print("  - max_time: 60000 (60 second timeout)")
print()
print("Running solver...")

result = solver.solvePartial(
    board_state={}, 
    max_samples=10, 
    max_time=60000
)

print()
print("STEP 4: Check results")
print("=" * 60)
print(f"Solutions found: {result['solutionCount']}")
print(f"Solutions returned: {result['solutionsReturned']}")
print(f"Timed out: {result['timedOut']}")
print(f"Limit reached: {result['limitReached']}")
print(f"Message: {result['message']}")
print()

if result['solutions']:
    print("✓ SUCCESS! Solver found solutions")
    print()
    print("You can access solutions via result['solutions']")
    print("Each solution is a dict mapping (x,y,z) -> piece_id")
else:
    print("✗ No solutions found")
    print()
    print("Debugging: Check how many valid placements each piece has")
    for piece in test_pieces:
        placements = solver._get_placements(piece, set())
        print(f"  {piece['name']}: {len(placements)} valid placements")
