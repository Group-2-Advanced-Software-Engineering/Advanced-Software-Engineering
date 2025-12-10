# Pyramid Solver Testing Guide

## Quick Start

Run the example test:

```bash
python test_solver_example.py
```

## Understanding the Solver

### Input: Pieces

Each piece is a dictionary with:

- `id`: Unique integer identifier
- `name`: String name for the piece
- `color`: Hex color code (e.g., '#ff595e')
- `shapeData`: List of 3D coordinates `[x, y, z]`

Example:

```python
{
    'id': 1,
    'name': 'Piece-1',
    'color': '#ff595e',
    'shapeData': [[0,0,0], [1,0,0], [0,1,0], [0,0,1]]  # 4 cells
}
```

### Coordinate System

For a 5-level pyramid:

- **z** = pyramid level (0 = bottom, 4 = top)
- **x, y** = position within that level's grid
- Level z has grid size (z+1) × (z+1)

```
Level 0 (bottom): 1×1 grid  = 1 position   → (0,0,0)
Level 1:          2×2 grid  = 4 positions  → (0,0,1) to (1,1,1)
Level 2:          3×3 grid  = 9 positions  → (0,0,2) to (2,2,2)
Level 3:          4×4 grid  = 16 positions → (0,0,3) to (3,3,3)
Level 4 (top):    5×5 grid  = 25 positions → (0,0,4) to (4,4,4)
Total: 1+4+9+16+25 = 55 positions
```

### Cell Count Requirement

**CRITICAL**: Total cells across all pieces **MUST equal 55**

```python
total_cells = sum(len(piece['shapeData']) for piece in pieces)
assert total_cells == 55, "Must have exactly 55 cells!"
```

## Testing Steps

### 1. Create Your Pieces

```python
my_pieces = [
    {
        'id': 1,
        'name': 'L-Shape',
        'color': '#ff0000',
        'shapeData': [[0,0,0], [1,0,0], [0,1,0], [0,0,1]]  # 4 cells
    },
    # ... 11 more pieces totaling 55 cells
]
```

### 2. Import and Initialize

```python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polysphere.settings')
django.setup()

from kanoodleApp.util import PyramidSolver

solver = PyramidSolver(levels=5, pieces=my_pieces)
```

### 3. Run Solver

```python
result = solver.solvePartial(
    board_state={},      # Empty board (or partial solution)
    max_samples=10,      # Return up to 10 solutions
    max_time=60000       # Timeout in milliseconds (60 seconds)
)
```

### 4. Check Results

```python
print(f"Solutions found: {result['solutionCount']}")
print(f"Solutions returned: {result['solutionsReturned']}")
print(f"Timed out: {result['timedOut']}")

if result['solutions']:
    # Success! Access solutions
    first_solution = result['solutions'][0]
    # first_solution is dict: {(x,y,z): piece_id, ...}
```

## Result Object

The solver returns a dictionary with:

```python
{
    'solutions': [         # List of solution dictionaries
        {
            (0,0,0): 1,   # Position (x,y,z) -> piece_id
            (1,0,0): 1,
            # ... all 55 positions mapped
        },
        # ... more solutions
    ],
    'solutionCount': 20,        # Total solutions found
    'solutionsReturned': 10,    # Number returned (limited by max_samples)
    'timedOut': False,          # Whether solver hit time limit
    'limitReached': True,       # Whether max_samples was reached
    'message': 'Found 10 solution(s) (sample limit reached).'
}
```

## Testing with Partial Board

You can test with some pieces already placed:

```python
partial_board = {
    (0,0,0): 5,    # Piece ID 5 at position (0,0,0)
    (1,0,0): 5,
    (0,1,0): 5,
}

result = solver.solvePartial(
    board_state=partial_board,
    max_samples=10,
    max_time=60000
)
```

The solver will find how to place remaining pieces around the fixed ones.

## Debugging

### No Solutions Found?

Check placement counts:

```python
for piece in my_pieces:
    placements = solver._get_placements(piece, set())
    print(f"{piece['name']}: {len(placements)} valid placements")
```

If any piece has 0 placements, its coordinates don't fit the pyramid structure.

### Common Issues

1. **Wrong cell count**: Must be exactly 55
2. **Invalid coordinates**: z must be 0-4, x and y must fit within level grid
3. **Duplicate positions**: Each cell in a piece must have unique coordinates
4. **Pieces too large**: A piece at level 0 can only use positions like (0,0,0)

### Example Valid Check

```python
def validate_piece(piece, levels=5):
    coords = piece['shapeData']

    # Check for duplicates
    if len(coords) != len(set(map(tuple, coords))):
        return False, "Duplicate coordinates in piece"

    # Check each coordinate
    for x, y, z in coords:
        if z < 0 or z >= levels:
            return False, f"Invalid z={z} (must be 0-{levels-1})"

        grid_size = z + 1
        if x < 0 or x >= grid_size or y < 0 or y >= grid_size:
            return False, f"Invalid ({x},{y}) for level {z} (grid size {grid_size})"

    return True, "Valid"

# Test each piece
for piece in my_pieces:
    valid, message = validate_piece(piece)
    print(f"{piece['name']}: {message}")
```

## Performance Tips

1. **Start with small max_samples** (like 10) to test quickly
2. **Use timeout** to prevent infinite runs on unsolvable puzzles
3. **Check cell count first** - saves time if pieces are invalid
4. **Test individual pieces** - validate coordinates before full solve

## Example Test Script

See `test_solver_example.py` for a complete working example.

## Command Line Testing

```bash
# Quick test with example pieces
python test_solver_example.py

# Test with your own pieces file
python -c "
import json
from kanoodleApp.util import PyramidSolver
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polysphere.settings')
django.setup()

with open('my_pieces.json', 'r') as f:
    pieces = json.load(f)

solver = PyramidSolver(levels=5, pieces=pieces)
result = solver.solvePartial({}, max_samples=5, max_time=30000)
print(f\"Found {result['solutionCount']} solutions\")
"
```
