import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json
import uuid
from .models import (KanoodleBoard, Piece, partialSolution,
                     PyramidBoard)
from .util import solverKanoodle

def normalize_shape_for_2d(shape_data):
    """Ensure coordinates are 2D by dropping any z component."""
    normalized = []
    for cell in shape_data:
        if len(cell) >= 2:
            normalized.append([cell[0], cell[1]])
    return normalized


def normalize_shape_for_3d(shape_data):
    """Ensure coordinates are 3D by adding z=0 when missing."""
    normalized = []
    for cell in shape_data:
        if len(cell) == 3:
            normalized.append([cell[0], cell[1], cell[2]])
        elif len(cell) == 2:
            normalized.append([cell[0], cell[1], 0])
    return normalized


def kanoodle_solver(request):
    """Render the main solver page"""
    board = KanoodleBoard.objects.first()
    pieces = Piece.objects.all()

    solution, created = partialSolution.objects.get_or_create(board=board, defaults={'state_data': {}})

    context = {'board': board, 'pieces': pieces, 'solution_id': solution.id}

    return render(request, 'index.html', context)


@csrf_exempt
def solvePartialSolution(request, solution_id):
    """Solve the puzzle using DLX algorithm"""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required."}, status=405)

    try:
        data = json.loads(request.body)
        partial_board = data.get('partialBoard')
        sample_limit = data.get('sampleLimit')
        max_time = data.get('maxTime')

        # Get the solution and board
        parSolution = partialSolution.objects.get(pk=solution_id)
        board = parSolution.board

        # Build pieces data with ALL fields including color
        pieces_for_solver = []
        for p in Piece.objects.all():
            pieces_for_solver.append({
                'id': p.pk,
                'name': p.name,
                'shapeData': normalize_shape_for_2d(p.shapeData),
                'color': p.color,
            })

        # Run the solver
        solver = solverKanoodle(board.width, board.height, pieces_for_solver)
        result = solver.solvePartial(partial_board, sample_limit, max_time)

        # Check if unsolvable
        if 'message' in result and result.get('solutionCount', 0) == 0:
            result['success'] = False
            return JsonResponse(result, status=200)

        # Success case
        result['success'] = True
        return JsonResponse(result, safe=False)

    except partialSolution.DoesNotExist:
        return JsonResponse({"error": "No solution found.", "success": False}, status=404)
    except Exception as e:
        print("--- CRITICAL SOLVER ERROR TRACEBACK ---")
        traceback.print_exc()
        print("---------------------------------------")
        return JsonResponse(
            {"error": f"An internal error occurred while solving. Check server logs for details.",
             "success": False}, status=500)


@csrf_exempt
def getPiecesApi(request):
    """Retrieves all Kanoodle pieces and returns them as a JSON list with color data"""
    if request.method != 'GET':
        return JsonResponse({"error": "GET required."}, status=405)

    try:
        pieces = Piece.objects.all()
        piece_type = str(request.GET.get('type', '2d')).lower()

        piece_data = [
            {
                'id': p.pk,
                'name': p.name,
                'shapeData': normalize_shape_for_2d(p.shapeData) if piece_type == '2d'
                else normalize_shape_for_3d(p.shapeData),
                'color': p.color,
            } for p in pieces
        ]

        return JsonResponse({"pieces": piece_data}, safe=False)

    except Exception as e:
        return JsonResponse({"error": f"Error fetching pieces: {str(e)}"}, status=500)

def pyramid_solver(request):
        """Render the 3D pyramid solver page"""
        # Get or create pyramid board
        pyramid, created = PyramidBoard.objects.get_or_create(
            levels=5,
            defaults={'name': '5-Level Pyramid'}
        )

        # Generate unique session ID
        session_key = str(uuid.uuid4())

        print(session_key)

        return render(request, 'pyramid.html', {
            'solution_id': session_key,
            'pyramid': {'levels': pyramid.levels}
        })


@csrf_exempt
def solve_pyramid(request, solution_id):
    """Solve 3D pyramid puzzle"""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required."}, status=405)

    try:
        data = json.loads(request.body)
        levels = int(data.get('levels', 5))
        partial_board = data.get('partialBoard', {})
        batch_size = int(data.get('batchSize', 100))
        max_time = data.get('maxTime', 10000)

        if levels < 1 or levels > 7:
            levels = 5

        # Get pieces
        pieces_for_solver = []
        for p in Piece.objects.all():
            pieces_for_solver.append({
                'id': p.pk,
                'name': p.name,
                'shapeData': p.shapeData,
                'color': p.color,
            })

        # Create solver
        from .util_pyramid import PyramidSolver
        solver = PyramidSolver(pieces_for_solver, levels=levels)
        solver.set_locked_positions(partial_board)

        # Solve
        solutions, exhausted, timed_out = solver.solve(batch_size, max_time)

        # Convert solutions from lattice back to grid coordinates
        frontend_solutions = []
        for solution in solutions:
            board = {}
            for placement in solution:
                for lat_pos in placement['positions']:
                    lat_z, lat_x, lat_y = lat_pos
                    # Convert lattice to grid
                    grid_x, grid_y, grid_z = solver.pyramid.lattice_to_grid(lat_z, lat_x, lat_y)
                    key = f"{grid_x},{grid_y},{grid_z}"
                    board[key] = placement['piece_id']

            frontend_solutions.append({'board': board})

        return JsonResponse({
            'success': True,
            'solutions': frontend_solutions,
            'solutionCount': len(frontend_solutions),
            'exhausted': exhausted,
            'timedOut': timed_out,
            'message': f'Found {len(frontend_solutions)} solutions'
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)