import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json
from .models import KanoodleBoard, Piece, partialSolution
logger = logging.getLogger(__name__)
from .util import (
    KanoodleSolver,
    get_session,
    create_session,
    delete_session,
    get_redis_client,
    make_cache_keys,
)


def render_puzzle(request):
    board = KanoodleBoard.objects.first()
    pieces = Piece.objects.all()
    solution, _ = partialSolution.objects.get_or_create(board=board, defaults={'state_data': {}})
    context = {'board': board, 'pieces': pieces, 'solution_id': solution.id}
    return render(request, 'index.html', context)

kanoodle_solver = render_puzzle


@csrf_exempt
def solve_partial_batch(request, solution_id):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required."}, status=405)

    try:
        data = json.loads(request.body)
        partial_board = data.get('partialBoard') or data.get('partial_board')
        sample_limit = data.get('sampleLimit') or data.get('max_samples')
        max_time = data.get('maxTime') or data.get('max_time')
        action = data.get('action')
        batch_size = data.get('batchSize', 24)

        solution_record = partialSolution.objects.get(pk=solution_id)
        board = solution_record.board

        pieces_for_solver = []
        for p in Piece.objects.all():
            pieces_for_solver.append({
                'id': p.pk,
                'name': p.name,
                'shapeData': p.shapeData,
                'color': p.color,
            })

        solver = KanoodleSolver(board.width, board.height, pieces_for_solver)

        if action in ('init', 'next'):
            session_key = f"solve:{solution_id}"
            if action == 'init':
                delete_session(session_key)
                solution_record.state_data = {'mode': 'incremental', 'cursor': 0}
                solution_record.save(update_fields=['state_data'])

            session = get_session(session_key)
            if session is None:
                try:
                    session = create_session(session_key, solver, partial_board)
                except ValueError as ve:
                    return JsonResponse({'success': True, 'solutions': [], 'solutionsReturned': 0, 'solutionCount': 0, 'timedOut': False, 'exhausted': True, 'message': str(ve)}, status=200)

            redis_client = get_redis_client()
            out_batch = []
            served_from_cache = False
            total_found = 0
            exhausted = False
            timed_out = False
            if redis_client is not None:
                base_key, meta_key = make_cache_keys(board.width, board.height, partial_board, pieces_for_solver)
                try:
                    meta = redis_client.hgetall(meta_key)
                    cursor = int(solution_record.state_data.get('cursor', 0))
                    total = int(meta.get('total', '0')) if meta else 0
                    exists = redis_client.exists(base_key)
                    available_len = redis_client.llen(base_key) if exists else 0
                    if exists:
                        rng = redis_client.lrange(base_key, cursor, cursor + batch_size - 1)
                    else:
                        rng = []
                    for item in rng:
                        try:
                            out_batch.append({'board': json.loads(item)})
                        except Exception:
                            break
                    if out_batch:
                        served_from_cache = True
                        next_cursor = cursor + len(out_batch)
                        solution_record.state_data['cursor'] = next_cursor
                        solution_record.save(update_fields=['state_data'])
                        total_found = max(total, available_len, next_cursor)
                        meta_exhausted = bool(meta.get('exhausted', '0') == '1') if meta else False
                        exhausted = (next_cursor >= available_len) and meta_exhausted
                        try:
                            logger.info("CACHE HIT key=%s cursor=%d +%d ->%d total=%d avail=%d exhausted=%s", base_key, cursor, len(out_batch), next_cursor, total_found, available_len, exhausted)
                        except Exception:
                            pass
                except Exception:
                    out_batch = []

            if not out_batch:
                batch, total_found, exhausted, timed_out = session.next_batch(batch_size=batch_size, max_time=max_time)
                if redis_client is not None and batch:
                    base_key, meta_key = make_cache_keys(board.width, board.height, partial_board, pieces_for_solver)
                    pipe = redis_client.pipeline()
                    for sol in batch:
                        try:
                            pipe.rpush(base_key, json.dumps(sol['board'], separators=(',', ':')))
                        except Exception:
                            pass
                    pipe.hset(meta_key, mapping={'total': str(total_found), 'exhausted': '1' if exhausted else '0'})
                    pipe.expire(base_key, 24*3600)
                    pipe.expire(meta_key, 24*3600)
                    pipe.execute()
                    try:
                        logger.info("CACHE MISS key=%s produced +%d cursor->%d total=%d exhausted=%s", base_key, len(batch), int(solution_record.state_data.get('cursor', 0)) + len(batch), total_found, exhausted)
                    except Exception:
                        pass
                cursor = int(solution_record.state_data.get('cursor', 0))
                solution_record.state_data['cursor'] = cursor + len(batch)
                solution_record.save(update_fields=['state_data'])
                out_batch = batch
                served_from_cache = False

            
            if len(out_batch) == 0 and not timed_out and (exhausted or total_found == 0):
                msg = 'No solutions found.'
            elif exhausted:
                msg = 'All solutions found.'
            elif timed_out:
                msg = 'Time limit reached; partial batch.'
            else:
                msg = 'Batch complete, more available.'
            response_payload = {
                'success': True,
                'solutions': out_batch,
                'solutionsReturned': len(out_batch),
                'solutionCount': total_found,
                'timedOut': timed_out,
                'exhausted': exhausted,
                'message': msg,
                'cache': ('hit' if served_from_cache else 'miss')
            }
            resp = JsonResponse(response_payload, status=200)
            try:
                resp['X-Kanoodle-Cache'] = 'HIT' if served_from_cache else 'MISS'
            except Exception:
                pass
            return resp

        result = solver.solvePartial(partial_board, sample_limit, max_time)
        result['success'] = True
        if (result.get('solutionCount', 0) == 0) and not result.get('timedOut'):
            result['message'] = 'No solutions found.'
        return JsonResponse(result, safe=False)

    except partialSolution.DoesNotExist:
        return JsonResponse({"error": "No solution found.", "success": False}, status=404)
    except Exception as e:
        return JsonResponse(
            {"error": f"An internal error occurred while solving. Check server logs for details.",
             "success": False}, status=500)


@csrf_exempt
def get_pieces(request):
    if request.method != 'GET':
        return JsonResponse({"error": "GET required."}, status=405)

    try:
        pieces = Piece.objects.all()

        piece_data = [
            {
                'id': p.pk,
                'name': p.name,
                'shapeData': p.shapeData,
                'color': p.color,
            } for p in pieces
        ]

        return JsonResponse({"pieces": piece_data}, safe=False)

    except Exception as e:
        return JsonResponse({"error": f"Error fetching pieces: {str(e)}"}, status=500)

solvePartialSolution = solve_partial_batch
getPiecesApi = get_pieces