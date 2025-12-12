import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polysphere.settings')
django.setup()

from kanoodleApp.models import Piece
from kanoodleApp.util import PyramidSolver

pieces_queryset = Piece.objects.filter(pk__gte=100).all()
pieces_for_solver = []
for p in pieces_queryset:
    pieces_for_solver.append({
        'id': p.pk,
        'name': p.name,
        'shapeData': p.shapeData,
        'color': p.color,
    })

solver = PyramidSolver(5, pieces_for_solver)

all_positions = solver.get_all_pyramid_positions()
print(f"Total pyramid positions: {len(all_positions)}")
print(f"Total piece cells: {sum(len(p['shapeData']) for p in pieces_for_solver)}")

gen, placement_info, meta = solver.build_incremental_session({})

if meta and meta.get('unsolvable'):
    print(f"\nSolver detected unsolvable: {meta.get('message')}")
else:
    print(f"\nSolver accepted the puzzle")
    print(f"Total placements: {len(placement_info)}")
    print(f"Columns in exact cover matrix: {len(placement_info)}")
    
    print("\nFirst 5 placements:")
    for i, (placement_id, (piece_id, positions)) in enumerate(list(placement_info.items())[:5]):
        piece_name = next((p['name'] for p in pieces_for_solver if p['id'] == piece_id), 'Unknown')
        print(f"  {piece_name}: {len(positions)} positions")
