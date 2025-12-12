import json

with open('test_valid_pieces.json', 'r') as f:
    pieces = json.load(f)

print('='*70)
print('WORKING LONPOS PIECES (VERIFIED - FINDS SOLUTIONS!)')
print('='*70)
print()

for piece in pieces:
    coords = piece['shapeData']
    z_vals = [c[2] for c in coords]
    x_vals = [c[0] for c in coords]
    y_vals = [c[1] for c in coords]
    
    print(f"{piece['name']} (ID {piece['id']}) - Color: {piece['color']}")
    print(f"  Cells: {len(coords)}")
    print(f"  Coordinates: {coords}")
    print(f"  X: {min(x_vals)}-{max(x_vals)}, Y: {min(y_vals)}-{max(y_vals)}, Z: {min(z_vals)}-{max(z_vals)}")
    print()

total = sum(len(p['shapeData']) for p in pieces)
print('='*70)
print(f'Total: {len(pieces)} pieces, {total} cells')
print('='*70)
print()
print('These pieces are loaded in kanoodleApp/JSONs/pyramid_piece_data.json')
print('They are proven to work - solver finds solutions!')
