import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polysphere.settings')
django.setup()

from kanoodleApp.models import Piece
from kanoodleApp.util import PyramidSolver

pieces_queryset = Piece.objects.filter(pk__lte=12).all()
pieces_for_solver = []
for p in pieces_queryset:
    pieces_for_solver.append({
        'id': p.pk,
        'name': p.name,
        'shapeData': p.shapeData,
        'color': p.color,
    })

print(f"Loaded {len(pieces_for_solver)} pieces")
total_cells = sum(len(p['shapeData']) for p in pieces_for_solver)
print(f"Total cells: {total_cells}")
print(f"Pyramid needs: 55 cells (1+4+9+16+25)")

solver = PyramidSolver(5, pieces_for_solver)

print("\nTesting solver with empty board (5 minute timeout)...")
result = solver.solvePartial({}, max_samples=1, max_time=300000)

print(f"Solutions found: {result['solutionCount']}")
print(f"Solutions returned: {result['solutionsReturned']}")
print(f"Message: {result['message']}")
print(f"Timed out: {result.get('timedOut', False)}")

if result['solutionCount'] > 0:
    print("\nFirst solution found!")
    print(result['solutions'][0])
else:
    print("\nNo solutions found. Checking placements...")
    
    total_placements = 0
    for piece in pieces_for_solver:
        placements = solver._get_placements(piece, set())
        print(f"{piece['name']}: {len(placements)} placements")
        total_placements += len(placements)
    
    print(f"\nTotal placements across all pieces: {total_placements}")
    print("\nThis suggests the constraint system might be too restrictive.")
    print("The pieces might not fit together to fill the exact pyramid shape.")

