import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json
import uuid
import hashlib
from django.core.cache import cache
import threading
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


def generate_puzzle_cache_key(levels, partial_board, piece_ids):
    """Generate a unique cache key for a puzzle configuration"""
    # Sort partial board positions for consistent hashing
    sorted_board = sorted(partial_board.items()) if partial_board else []
    sorted_pieces = sorted(piece_ids)
    
    # Create a deterministic string representation
    key_data = f"pyramid_v1_{levels}_{sorted_board}_{sorted_pieces}"
    
    # Hash it to create a reasonable key length
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"pyramid_solutions_{key_hash}"


@csrf_exempt
def solve_pyramid(request, solution_id):
    """Solve 3D pyramid puzzle with Redis caching"""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required."}, status=405)

    try:
        data = json.loads(request.body)
        levels = int(data.get('levels', 5))
        partial_board = data.get('partialBoard', {})
        batch_size = int(data.get('batchSize', 100))
        max_time = data.get('maxTime', 10000)
        offset = int(data.get('offset', 0))  # Get offset for pagination

        if levels < 1 or levels > 7:
            levels = 5

        # Get pieces
        pieces_for_solver = []
        piece_ids = []
        for p in Piece.objects.all():
            pieces_for_solver.append({
                'id': p.pk,
                'name': p.name,
                'shapeData': p.shapeData,
                'color': p.color,
            })
            piece_ids.append(p.pk)

        # Generate cache key based on puzzle configuration
        cache_key = generate_puzzle_cache_key(levels, partial_board, piece_ids)
        
        # Try to get from cache
        cached_data = cache.get(cache_key)
        
        if cached_data:
            print(f"✅ Cache HIT for key: {cache_key} (offset: {offset})")
            # We have cached solutions, return requested batch with offset
            all_solutions = cached_data['solutions']
            cache_exhausted = cached_data.get('exhausted', False)
            cache_timed_out = cached_data.get('timed_out', False)
            
            # Check if background job is still computing
            inprogress_key = f"{cache_key}:in_progress"
            is_computing = cache.get(inprogress_key, False)
            
            # Check if we need more solutions beyond what's cached
            if offset >= len(all_solutions):
                if cache_exhausted or is_computing:
                    # Either all solutions are found, or background is still working
                    print(f"⚠️  Offset {offset} beyond cached {len(all_solutions)} solutions (computing={is_computing}, exhausted={cache_exhausted})")
                    return JsonResponse({
                        'success': True,
                        'solutions': [],
                        'solutionCount': 0,
                        'exhausted': cache_exhausted,  # Use cache's exhausted status
                        'timedOut': cache_timed_out,
                        'message': 'Computing more solutions...' if is_computing else 'No more solutions',
                        'cached': True,
                        'totalCached': len(all_solutions),
                        'computing': is_computing
                    })
                else:
                    print(f"⚠️  Offset {offset} beyond cached {len(all_solutions)} solutions - computing more")
                    # Fall through to computation logic below
            else:
                # Return batch starting from offset
                start_idx = offset
                end_idx = offset + batch_size
                frontend_solutions = all_solutions[start_idx:end_idx]
                
                # Only mark exhausted if cache is complete AND we've returned everything
                truly_exhausted = (end_idx >= len(all_solutions)) and cache_exhausted and not is_computing
                
                return JsonResponse({
                    'success': True,
                    'solutions': frontend_solutions,
                    'solutionCount': len(frontend_solutions),
                    'exhausted': truly_exhausted,
                    'timedOut': cache_timed_out,
                    'message': f'Found {len(frontend_solutions)} solutions',
                    'cached': True,
                    'totalCached': len(all_solutions),
                    'computing': is_computing
                })
        
        print(f"❌ Cache MISS for key: {cache_key} - Computing solutions...")
        
        # Get existing cached solutions if any
        existing_solutions = []
        if cached_data and 'solutions' in cached_data:
            existing_solutions = cached_data['solutions']
            print(f"   Found {len(existing_solutions)} existing solutions in cache")
        
        # Create solver
        from .util_pyramid import PyramidSolver
        solver = PyramidSolver(pieces_for_solver, levels=levels)
        solver.set_locked_positions(partial_board)

        # Smart batch sizing based on context
        if offset == 0:
            # First request - return quickly: compute only requested batch
            compute_count = batch_size
            print(f"   First request: computing {compute_count} solutions for fast response")

            # Quick synchronous solve for UI responsiveness (cap to 5s)
            immediate_max_time = min(max_time or 5000, 5000)
            quick_solutions, quick_exhausted, quick_timed_out = solver.solve(compute_count, immediate_max_time)

            # Convert quick results to frontend format AND include pre-placed pieces
            frontend_quick = []
            for solution in quick_solutions:
                board = {}
                # First, add the pre-placed pieces - convert from frontend format to backend grid, then back to frontend
                for key, piece_id in partial_board.items():
                    if piece_id:
                        parts = key.replace('(', '').replace(')', '').split(',')
                        frontend_x, frontend_y, frontend_z = int(parts[0]), int(parts[1]), int(parts[2])
                        # Convert frontend inverted z to backend grid z
                        grid_z = (solver.pyramid.base - 1) - frontend_z
                        # Store in frontend format (which is what the frontend expects)
                        board[f"{frontend_x},{frontend_y},{grid_z}"] = piece_id
                
                # Then add the solution pieces (already in backend grid format, need to keep as-is)
                for placement in solution:
                    for lat_pos in placement['positions']:
                        lat_z, lat_x, lat_y = lat_pos
                        grid_x, grid_y, grid_z = solver.pyramid.lattice_to_grid(lat_z, lat_x, lat_y)
                        key = f"{grid_x},{grid_y},{grid_z}"
                        board[key] = placement['piece_id']
                frontend_quick.append({'board': board})

            # Start background computation to build larger cache (if not already running)
            inprogress_key = f"{cache_key}:in_progress"
            if not cache.get(inprogress_key):
                cache.set(inprogress_key, True, timeout=300)

                def build_cache_job():
                    try:
                        # Try to compute all solutions (no time cap). Use a high limit.
                        all_sols, all_exhausted, all_timed_out = solver.solve(200000, None)
                        full_frontend = []
                        for solution in all_sols:
                            board = {}
                            # Include pre-placed pieces - convert properly
                            for key, piece_id in partial_board.items():
                                if piece_id:
                                    parts = key.replace('(', '').replace(')', '').split(',')
                                    frontend_x, frontend_y, frontend_z = int(parts[0]), int(parts[1]), int(parts[2])
                                    grid_z = (solver.pyramid.base - 1) - frontend_z
                                    board[f"{frontend_x},{frontend_y},{grid_z}"] = piece_id
                            
                            # Add solution pieces
                            for placement in solution:
                                for lat_pos in placement['positions']:
                                    lat_z, lat_x, lat_y = lat_pos
                                    gx, gy, gz = solver.pyramid.lattice_to_grid(lat_z, lat_x, lat_y)
                                    board[f"{gx},{gy},{gz}"] = placement['piece_id']
                            full_frontend.append({'board': board})
                        cache.set(cache_key, {
                            'solutions': full_frontend,
                            'exhausted': bool(all_exhausted) and not bool(all_timed_out),
                            'timed_out': bool(all_timed_out)
                        }, timeout=86400)
                        print(f"💾 Background cached {len(full_frontend)} solutions for {cache_key} (timed_out={all_timed_out})")
                    finally:
                        cache.delete(inprogress_key)

                t = threading.Thread(target=build_cache_job, daemon=True)
                t.start()

            # Merge quick results with any existing cached solutions (deduplicate)
            merged = []
            seen = set()
            for s in existing_solutions:
                # create a canonical key for the board
                k = '|'.join(sorted([f"{pos}:{pid}" for pos, pid in s['board'].items()]))
                seen.add(k)
                merged.append(s)
            for s in frontend_quick:
                k = '|'.join(sorted([f"{pos}:{pid}" for pos, pid in s['board'].items()]))
                if k not in seen:
                    seen.add(k)
                    merged.append(s)

            # Cache the initial results immediately so scroll requests can access them
            if len(merged) > 0:
                cache.set(cache_key, {
                    'solutions': merged,
                    'exhausted': False,  # Not exhausted yet, background is computing
                    'timed_out': False
                }, timeout=86400)
                print(f"💾 Cached initial {len(merged)} solutions (background computing more)")

            # Return the quick batch to client
            return JsonResponse({
                'success': True,
                'solutions': merged[:batch_size],
                'solutionCount': len(merged[:batch_size]),
                # exhausted true only when solver finished without timing out
                'exhausted': False,  # Never exhausted on first request (background is computing)
                'timedOut': bool(quick_timed_out),
                'message': f'Found {len(merged[:batch_size])} solutions (computing more...)',
                'cached': False,
                'totalCached': len(merged),
                'computing': True
            })
        else:
            # User is scrolling - check if background job is still running
            inprogress_key = f"{cache_key}:in_progress"
            if cache.get(inprogress_key):
                # Background job is still running, return what we have
                print(f"   Scroll request: background job still running, returning cached solutions")
                if offset >= len(existing_solutions):
                    # No more solutions available yet
                    return JsonResponse({
                        'success': True,
                        'solutions': [],
                        'solutionCount': 0,
                        'exhausted': False,
                        'timedOut': False,
                        'message': 'Computing solutions in background...',
                        'cached': True,
                        'totalCached': len(existing_solutions)
                    })
                else:
                    # Return next batch from existing cache
                    start_idx = offset
                    end_idx = offset + batch_size
                    return_batch = existing_solutions[start_idx:end_idx]
                    return JsonResponse({
                        'success': True,
                        'solutions': return_batch,
                        'solutionCount': len(return_batch),
                        'exhausted': end_idx >= len(existing_solutions),
                        'timedOut': False,
                        'message': f'Found {len(return_batch)} solutions (computing more...)',
                        'cached': True,
                        'totalCached': len(existing_solutions)
                    })
            else:
                # Background job finished or never started, compute ALL remaining solutions
                print(f"   Scroll request: computing ALL remaining solutions")
                compute_count = 200000  # High limit to get all solutions

        # Skip solutions we already have cached
        skip_count = len(existing_solutions)
        total_needed = skip_count + compute_count

        solutions, exhausted, timed_out = solver.solve(total_needed, max_time)

        # Convert solutions from lattice back to grid coordinates AND include pre-placed pieces
        frontend_solutions = []
        for solution in solutions:
            board = {}
            # Include pre-placed pieces - convert properly
            for key, piece_id in partial_board.items():
                if piece_id:
                    parts = key.replace('(', '').replace(')', '').split(',')
                    frontend_x, frontend_y, frontend_z = int(parts[0]), int(parts[1]), int(parts[2])
                    grid_z = (solver.pyramid.base - 1) - frontend_z
                    board[f"{frontend_x},{frontend_y},{grid_z}"] = piece_id
            
            # Add solution pieces
            for placement in solution:
                for lat_pos in placement['positions']:
                    lat_z, lat_x, lat_y = lat_pos
                    # Convert lattice to grid
                    grid_x, grid_y, grid_z = solver.pyramid.lattice_to_grid(lat_z, lat_x, lat_y)
                    key = f"{grid_x},{grid_y},{grid_z}"
                    board[key] = placement['piece_id']

            frontend_solutions.append({'board': board})

        # Merge with existing cached solutions (avoid duplicates)
        # Deduplicate merged solutions: prefer existing order then append new unique ones
        all_solutions = []
        seen = set()
        for s in existing_solutions:
            k = '|'.join(sorted([f"{pos}:{pid}" for pos, pid in s['board'].items()]))
            seen.add(k)
            all_solutions.append(s)
        for s in frontend_solutions:
            k = '|'.join(sorted([f"{pos}:{pid}" for pos, pid in s['board'].items()]))
            if k not in seen:
                seen.add(k)
                all_solutions.append(s)
        
        # Cache all found solutions for 24 hours (86400 seconds)
        if len(all_solutions) > 0:
            cache.set(cache_key, {
                'solutions': all_solutions,
                'exhausted': bool(exhausted) and not bool(timed_out),
                'timed_out': bool(timed_out)
            }, timeout=86400)
            print(f"💾 Cached {len(all_solutions)} total solutions (added {len(frontend_solutions) - len(existing_solutions)} new) (timed_out={timed_out})")

        # Return only the requested batch size starting from offset
        start_idx = offset
        end_idx = offset + batch_size
        return_solutions = all_solutions[start_idx:end_idx]

        return JsonResponse({
            'success': True,
            'solutions': return_solutions,
            'solutionCount': len(return_solutions),
            # exhausted true only when we have no more solutions and solver didn't time out
            'exhausted': (end_idx >= len(all_solutions)) and bool(exhausted) and not bool(timed_out),
            'timedOut': timed_out,
            'message': f'Found {len(return_solutions)} solutions',
            'cached': False,
            'totalCached': len(all_solutions)
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)