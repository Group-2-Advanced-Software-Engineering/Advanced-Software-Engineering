import time
import traceback
import threading
import json
import hashlib
try:
    import redis  
except Exception:
    redis = None



class DancingLinksNode:
    def __init__(self):
        self.left = self
        self.right = self
        self.up = self
        self.down = self
        self.column = None
        self.row_id = None


class ColumnNode(DancingLinksNode):
    def __init__(self, name):
        super().__init__()
        self.size = 0
        self.name = name
        self.column = self


class DancingLinks:

    def __init__(self, columns):
        self.header = ColumnNode("header")
        self.columns = {}

        prev = self.header
        for col_name in columns:
            col = ColumnNode(col_name)
            self.columns[col_name] = col

            col.left = prev
            col.right = prev.right
            prev.right.left = col
            prev.right = col
            prev = col

    def add_row(self, row_id, column_names):
        if not column_names:
            return

        nodes = []
        for col_name in column_names:
            if col_name not in self.columns:
                continue

            col = self.columns[col_name]
            node = DancingLinksNode()
            node.column = col
            node.row_id = row_id

            node.up = col.up
            node.down = col
            col.up.down = node
            col.up = node
            col.size += 1

            nodes.append(node)

        if nodes:
            for i in range(len(nodes)):
                nodes[i].left = nodes[i-1]
                nodes[i].right = nodes[(i+1) % len(nodes)]

    def cover(self, col):
        col.right.left = col.left
        col.left.right = col.right

        i = col.down
        while i != col:
            j = i.right
            while j != i:
                j.down.up = j.up
                j.up.down = j.down
                j.column.size -= 1
                j = j.right
            i = i.down

    def uncover(self, col):
        i = col.up
        while i != col:
            j = i.left
            while j != i:
                j.column.size += 1
                j.down.up = j
                j.up.down = j
                j = j.left
            i = i.up

        col.right.left = col
        col.left.right = col

    def search(self, solution, callback, max_solutions=None):
        if self.header.right == self.header:
            callback(solution[:])
            return 1

        col = None
        min_size = float('inf')
        c = self.header.right
        while c != self.header:
            if c.size < min_size:
                min_size = c.size
                col = c
            c = c.right

        if col is None or col.size == 0:
            return 0

        self.cover(col)
        solutions_found = 0

        r = col.down
        while r != col:
            solution.append(r.row_id)

            j = r.right
            while j != r:
                self.cover(j.column)
                j = j.right

            solutions_found += self.search(solution, callback, max_solutions)

            if max_solutions is not None and solutions_found >= max_solutions:
                j = r.left
                while j != r:
                    self.uncover(j.column)
                    j = j.left
                solution.pop()
                self.uncover(col)
                return solutions_found

            j = r.left
            while j != r:
                self.uncover(j.column)
                j = j.left

            solution.pop()
            r = r.down

        self.uncover(col)
        return solutions_found

    def search_generator(self):
        solution = []

        def choose_column():
            col = None
            min_size = float('inf')
            c = self.header.right
            while c != self.header:
                if c.size < min_size:
                    min_size = c.size
                    col = c
                c = c.right
            return col

        def _search_gen():
            if self.header.right == self.header:
                yield list(solution)
                return

            col = choose_column()
            if col is None or col.size == 0:
                return

            self.cover(col)
            r = col.down
            while r != col:
                solution.append(r.row_id)
                j = r.right
                while j != r:
                    self.cover(j.column)
                    j = j.right

                yield from _search_gen()

                j = r.left
                while j != r:
                    self.uncover(j.column)
                    j = j.left
                solution.pop()
                r = r.down

            self.uncover(col)

        yield from _search_gen()



def normalize_coords(coords):
    if not coords:
        return []

    if len(coords[0]) == 2:
        min_x = min(p[0] for p in coords)
        min_y = min(p[1] for p in coords)
        return tuple(sorted([(x - min_x, y - min_y) for x, y in coords]))
    else:
        min_x = min(p[0] for p in coords)
        min_y = min(p[1] for p in coords)
        min_z = min(p[2] for p in coords)
        return tuple(sorted([(x - min_x, y - min_y, z - min_z) for x, y, z in coords]))


def rotate_90_ccw(shape):
    return normalize_coords([(y, -x) for x, y in shape])


def reflect_vertical(shape):
    return normalize_coords([(x, -y) for x, y in shape])


def rotate_3d_x(shape):
    return normalize_coords([(x, -z, y) for x, y, z in shape])


def rotate_3d_y(shape):
    return normalize_coords([(z, y, -x) for x, y, z in shape])


def rotate_3d_z(shape):
    return normalize_coords([(-y, x, z) for x, y, z in shape])


def reflect_3d_xy(shape):
    return normalize_coords([(x, y, -z) for x, y, z in shape])


def generate_orientations(base_shape):
    seen = set()
    current = normalize_coords([tuple(c) for c in base_shape])
    for _ in range(2):
        for _ in range(4):
            if current not in seen:
                yield current
                seen.add(current)
            current = rotate_90_ccw(current)
        current = reflect_vertical(current)


def generate_3d_orientations(base_shape):
    seen = set()
    current = normalize_coords([tuple(c) for c in base_shape])

    to_check = [current]

    while to_check:
        shape = to_check.pop()
        if shape in seen:
            continue
        seen.add(shape)
        yield shape

        for rot_func in [rotate_3d_x, rotate_3d_y, rotate_3d_z]:
            rotated = shape
            for _ in range(4):
                rotated = rot_func(rotated)
                if rotated not in seen:
                    to_check.append(rotated)

        reflected = reflect_3d_xy(shape)
        if reflected not in seen:
            to_check.append(reflected)

normalise = normalize_coords
rotate = rotate_90_ccw
flip = reflect_vertical
versions = generate_orientations



class KanoodleSolver:
    def __init__(self, board_width, board_height, pieces):
        self.width = board_width
        self.height = board_height
        self.pieces_data = pieces
        self.id_to_name = {p['id']: p['name'] for p in pieces}

    def _get_placements(self, piece_data, occupied_positions):
        placements_list = []
        piece_id = piece_data['id']
        placement_counter = 0

        base_coords = [tuple(c) for c in piece_data['shapeData']]

        for shape_coords in generate_orientations(base_coords):
            if not shape_coords:
                continue

            xs, ys = zip(*shape_coords)
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            for dx in range(-min_x, self.width - max_x):
                for dy in range(-min_y, self.height - max_y):
                    placement = []
                    valid = True

                    for px, py in shape_coords:
                        x_abs, y_abs = px + dx, py + dy
                        pos = (x_abs, y_abs)

                        if pos in occupied_positions:
                            valid = False
                            break

                        placement.append(pos)

                    if valid:
                        placement_id = (piece_id, placement_counter)
                        placement_counter += 1
                        placements_list.append((placement_id, piece_id, tuple(sorted(placement))))

        return placements_list

    def solvePartial(self, board_state, max_samples=100, max_time=None, all_required_constraints=None):
        start_time_ms = time.time() * 1000

        occupied_positions = set()
        placed_piece_ids = set()

        if board_state is None or not isinstance(board_state, list) or not board_state:
            board_state = [[0] * self.width for _ in range(self.height)]

        for r in range(self.height):
            row = board_state[r] if r < len(board_state) else []
            for c in range(self.width):
                piece_id = row[c] if c < len(row) else 0
                if piece_id != 0:
                    occupied_positions.add((c, r))
                    placed_piece_ids.add(piece_id)

        remaining_pieces_data = [
            p for p in self.pieces_data if p['id'] not in placed_piece_ids
        ]

        required_positions = set()
        for x in range(self.width):
            for y in range(self.height):
                pos = (x, y)
                if pos not in occupied_positions:
                    required_positions.add(pos)

        total_unplaced_cells = len(required_positions)
        remaining_piece_cell_count = sum(len(p['shapeData']) for p in remaining_pieces_data)

        if remaining_piece_cell_count != total_unplaced_cells:
            return {
                'solutions': [], 'solutionCount': 0, 'solutionsReturned': 0, 'timedOut': False,
                'limitReached': False, 'message': "Unsolvable: Placed pieces do not leave a solvable empty space."
            }

        columns = []

        for piece_data in remaining_pieces_data:
            columns.append(f"piece_{piece_data['id']}")

        for pos in required_positions:
            columns.append(f"pos_{pos[0]}_{pos[1]}")

        print(f"DEBUG: Building DLX with {len(columns)} columns ({len(remaining_pieces_data)} pieces, {len(required_positions)} positions)")

        dlx = DancingLinks(columns)

        placement_info = {}

        for piece_data in remaining_pieces_data:
            placements = self._get_placements(piece_data, occupied_positions)

            for placement_id, piece_id, positions in placements:
                if all(pos in required_positions for pos in positions):
                    row_columns = [f"piece_{piece_id}"]
                    for pos in positions:
                        row_columns.append(f"pos_{pos[0]}_{pos[1]}")

                    dlx.add_row(placement_id, row_columns)
                    placement_info[placement_id] = (piece_id, positions)

        if not placement_info:
            return {
                'solutions': [], 'solutionCount': 0, 'solutionsReturned': 0, 'timedOut': False,
                'limitReached': False, 'message': "Unsolvable: No valid placements found."
            }

        print(f"DEBUG: Built DLX with {len(placement_info)} possible placements")

        solutions = []
        total_solutions_found = [0]
        limit_reached = [False]
        timed_out = [False]

        def solution_callback(solution_placement_ids):
            total_solutions_found[0] += 1

            final_board = [list(row) for row in board_state]

            for placement_id in solution_placement_ids:
                piece_id, positions = placement_info[placement_id]
                for x, y in positions:
                    final_board[y][x] = piece_id

            if len(solutions) < max_samples:
                solutions.append({'board': final_board})

            if len(solutions) >= max_samples:
               limit_reached[0] = True

            current_time_ms = time.time() * 1000
            if max_time and max_time > 0 and current_time_ms - start_time_ms >= max_time:
               timed_out[0] = True

        try:
            dlx.search([], solution_callback, max_samples if not timed_out[0] else None)

        except Exception as e:
            print(f"ERROR: Exception in DLX search: {e}")
            traceback.print_exc()
            raise

        print(f"DEBUG: Found {total_solutions_found[0]} total solutions, returning {len(solutions)}")

        if len(solutions) == 0:
            message = "No solutions found."
        elif timed_out[0]:
            message = f"Found {len(solutions)} solution(s) before time limit."
        elif limit_reached[0]:
            message = f"Found {len(solutions)} solution(s) (sample limit reached)."
        else:
            message = f"Found all {total_solutions_found[0]} solution(s)."

        return {
            'solutions': solutions,
            'solutionCount': total_solutions_found[0],
            'solutionsReturned': len(solutions),
            'timedOut': timed_out[0],
            'limitReached': limit_reached[0],
            'message': message
        }

    def solveIncremental(self, board_state, batch_size=24, max_time=None, skip_count=0):

        start_time_ms = time.time() * 1000

        occupied_positions = set()
        placed_piece_ids = set()

        if board_state is None or not isinstance(board_state, list) or not board_state:
            board_state = [[0] * self.width for _ in range(self.height)]

        for r in range(self.height):
            row = board_state[r] if r < len(board_state) else []
            for c in range(self.width):
                piece_id = row[c] if c < len(row) else 0
                if piece_id != 0:
                    occupied_positions.add((c, r))
                    placed_piece_ids.add(piece_id)

        remaining_pieces_data = [p for p in self.pieces_data if p['id'] not in placed_piece_ids]

        required_positions = set()
        for x in range(self.width):
            for y in range(self.height):
                pos = (x, y)
                if pos not in occupied_positions:
                    required_positions.add(pos)

        total_unplaced_cells = len(required_positions)
        remaining_piece_cell_count = sum(len(p['shapeData']) for p in remaining_pieces_data)

        if remaining_piece_cell_count != total_unplaced_cells:
            return {
                'solutions': [], 'solutionCount': 0, 'solutionsReturned': 0, 'timedOut': False,
                'exhausted': True, 'message': "Unsolvable: Placed pieces do not leave a solvable empty space.",
                'skipCount': skip_count
            }

        columns = []
        for piece_data in remaining_pieces_data:
            columns.append(f"piece_{piece_data['id']}")
        for pos in required_positions:
            columns.append(f"pos_{pos[0]}_{pos[1]}")

        dlx = DancingLinks(columns)
        placement_info = {}
        for piece_data in remaining_pieces_data:
            placements = self._get_placements(piece_data, occupied_positions)
            for placement_id, piece_id, positions in placements:
                if all(pos in required_positions for pos in positions):
                    row_columns = [f"piece_{piece_id}"] + [f"pos_{pos[0]}_{pos[1]}" for pos in positions]
                    dlx.add_row(placement_id, row_columns)
                    placement_info[placement_id] = (piece_id, positions)

        if not placement_info:
            return {
                'solutions': [], 'solutionCount': 0, 'solutionsReturned': 0, 'timedOut': False,
                'exhausted': True, 'message': "Unsolvable: No valid placements found.", 'skipCount': skip_count
            }

        batch_solutions = []
        total_solutions_found = 0
        timed_out = False
        exhausted = False

        def solution_callback(solution_placement_ids):
            nonlocal batch_solutions, total_solutions_found, timed_out, exhausted
            if timed_out or exhausted:
                return
            total_solutions_found += 1
            if total_solutions_found <= skip_count:
                return
            final_board = [list(row) for row in board_state]
            for placement_id in solution_placement_ids:
                piece_id, positions = placement_info[placement_id]
                for x, y in positions:
                    final_board[y][x] = piece_id
            batch_solutions.append({'board': final_board})
            if len(batch_solutions) >= batch_size:
                exhausted = False
                raise StopIteration()
            if max_time and max_time > 0 and (time.time() * 1000 - start_time_ms) >= max_time:
                timed_out = True
                raise StopIteration()

        try:
            dlx.search([], solution_callback, None)
            exhausted = True
        except StopIteration:
            if timed_out:
                exhausted = False
        except Exception as e:
            traceback.print_exc()
            return {
                'solutions': [], 'solutionCount': total_solutions_found, 'solutionsReturned': 0,
                'timedOut': True, 'exhausted': False, 'message': 'Internal solver error.', 'skipCount': skip_count
            }

        new_skip = skip_count + len(batch_solutions)
        message = (
            "No solutions found." if total_solutions_found == 0 else
            ("Batch complete, more available." if (not exhausted and not timed_out) else
             ("Time limit reached; partial batch." if timed_out else
              "All solutions found."))
        )

        return {
            'solutions': batch_solutions,
            'solutionCount': total_solutions_found,
            'solutionsReturned': len(batch_solutions),
            'timedOut': timed_out,
            'exhausted': exhausted,
            'message': message,
            'skipCount': new_skip
        }

    def build_incremental_session(self, board_state):
        occupied_positions = set()
        placed_piece_ids = set()

        if board_state is None or not isinstance(board_state, list) or not board_state:
            board_state = [[0] * self.width for _ in range(self.height)]

        for r in range(self.height):
            row = board_state[r] if r < len(board_state) else []
            for c in range(self.width):
                piece_id = row[c] if c < len(row) else 0
                if piece_id != 0:
                    occupied_positions.add((c, r))
                    placed_piece_ids.add(piece_id)

        remaining_pieces_data = [p for p in self.pieces_data if p['id'] not in placed_piece_ids]

        required_positions = set()
        for x in range(self.width):
            for y in range(self.height):
                pos = (x, y)
                if pos not in occupied_positions:
                    required_positions.add(pos)

        total_unplaced_cells = len(required_positions)
        remaining_piece_cell_count = sum(len(p['shapeData']) for p in remaining_pieces_data)

        if remaining_piece_cell_count != total_unplaced_cells:
            return None, None, {
                'unsolvable': True,
                'message': "Unsolvable: Placed pieces do not leave a solvable empty space."
            }

        columns = []
        for piece_data in remaining_pieces_data:
            columns.append(f"piece_{piece_data['id']}")
        for pos in required_positions:
            columns.append(f"pos_{pos[0]}_{pos[1]}")

        dlx = DancingLinks(columns)
        placement_info = {}
        for piece_data in remaining_pieces_data:
            placements = self._get_placements(piece_data, occupied_positions)
            for placement_id, piece_id, positions in placements:
                if all(pos in required_positions for pos in positions):
                    row_columns = [f"piece_{piece_id}"] + [f"pos_{pos[0]}_{pos[1]}" for pos in positions]
                    dlx.add_row(placement_id, row_columns)
                    placement_info[placement_id] = (piece_id, positions)

        if not placement_info:
            return None, None, {
                'unsolvable': True,
                'message': "Unsolvable: No valid placements found."
            }

        gen = dlx.search_generator()
        return gen, placement_info, {
            'unsolvable': False,
            'board_state': [list(row) for row in board_state]
        }

solverKanoodle = KanoodleSolver


class PyramidSolver:

    def __init__(self, levels, pieces):
        self.levels = levels
        self.pieces_data = pieces
        self.id_to_name = {p['id']: p['name'] for p in pieces}

    def get_all_pyramid_positions(self):
        positions = set()
        for z in range(self.levels):
            grid_size = z + 1
            for x in range(grid_size):
                for y in range(grid_size):
                    positions.add((x, y, z))
        return positions

    def is_valid_pyramid_position(self, x, y, z):
        if z < 0 or z >= self.levels:
            return False
        grid_size = z + 1
        return 0 <= x < grid_size and 0 <= y < grid_size

    def _get_placements(self, piece_data, occupied_positions):
        placements_list = []
        piece_id = piece_data['id']
        placement_counter = 0

        base_coords = [tuple(c) for c in piece_data['shapeData']]

        is_3d = len(base_coords[0]) == 3 if base_coords else False

        if is_3d:
            all_z_zero = all(c[2] == 0 for c in base_coords)
            if all_z_zero:
                base_2d = [(c[0], c[1]) for c in base_coords]
                flat_2d_orientations = list(generate_orientations(base_2d))
            else:
                flat_2d_orientations = None
            orientation_generator = generate_3d_orientations(base_coords)
        else:
            base_coords_3d = [(x, y, 0) for x, y in base_coords]
            flat_2d_orientations = list(generate_orientations(base_coords))
            orientation_generator = generate_3d_orientations(base_coords_3d)

        for shape_coords in orientation_generator:
            if not shape_coords:
                continue

            xs = [c[0] for c in shape_coords]
            ys = [c[1] for c in shape_coords]
            zs = [c[2] for c in shape_coords]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_z, max_z = min(zs), max(zs)

            for z_base in range(self.levels):
                grid_size = z_base + 1

                for dx in range(-min_x, grid_size - max_x):
                    for dy in range(-min_y, grid_size - max_y):
                        dz = z_base - min_z

                        placement = []
                        valid = True

                        for px, py, pz in shape_coords:
                            x_abs = px + dx
                            y_abs = py + dy
                            z_abs = pz + dz

                            if not self.is_valid_pyramid_position(x_abs, y_abs, z_abs):
                                valid = False
                                break

                            pos = (x_abs, y_abs, z_abs)
                            if pos in occupied_positions:
                                valid = False
                                break

                            placement.append(pos)

                        if valid and len(placement) == len(shape_coords):
                            placement_id = (piece_id, placement_counter)
                            placement_counter += 1
                            placements_list.append((placement_id, piece_id, tuple(sorted(placement))))

        if flat_2d_orientations:
            for shape_2d in flat_2d_orientations:
                if not shape_2d:
                    continue
                
                xs_2d = [c[0] for c in shape_2d]
                ys_2d = [c[1] for c in shape_2d]
                min_x_2d, max_x_2d = min(xs_2d), max(xs_2d)
                min_y_2d, max_y_2d = min(ys_2d), max(ys_2d)
                
                for target_z in range(self.levels):
                    grid_size = target_z + 1
                    
                    for dx in range(-min_x_2d, grid_size - max_x_2d):
                        for dy in range(-min_y_2d, grid_size - max_y_2d):
                            placement = []
                            valid = True
                            
                            for px, py in shape_2d:
                                x_abs = px + dx
                                y_abs = py + dy
                                z_abs = target_z
                                
                                if not self.is_valid_pyramid_position(x_abs, y_abs, z_abs):
                                    valid = False
                                    break
                                
                                pos = (x_abs, y_abs, z_abs)
                                if pos in occupied_positions:
                                    valid = False
                                    break
                                
                                placement.append(pos)
                            
                            if valid and len(placement) == len(shape_2d):
                                placement_id = (piece_id, placement_counter)
                                placement_counter += 1
                                placements_list.append((placement_id, piece_id, tuple(sorted(placement))))

        return placements_list

    def solvePartial(self, board_state, max_samples=100, max_time=None):
        start_time_ms = time.time() * 1000

        occupied_positions = set()
        placed_piece_ids = set()

        if board_state is None:
            board_state = {}
        elif isinstance(board_state, dict):
            converted = {}
            for key, val in board_state.items():
                try:
                    if isinstance(key, str):
                        key = key.strip('()')
                        parts = key.split(',')
                        if len(parts) != 3:
                            print(f"WARNING: Invalid key format '{key}', skipping")
                            continue
                        key = tuple(int(p.strip()) for p in parts)
                    converted[key] = val
                except Exception as e:
                    print(f"ERROR parsing key '{key}': {e}")
                    continue
            board_state = converted

        if isinstance(board_state, dict):
            for pos, piece_id in board_state.items():
                if piece_id != 0:
                    occupied_positions.add(pos)
                    placed_piece_ids.add(piece_id)

        remaining_pieces_data = [
            p for p in self.pieces_data if p['id'] not in placed_piece_ids
        ]

        all_positions = self.get_all_pyramid_positions()
        required_positions = all_positions - occupied_positions

        total_unplaced_cells = len(required_positions)
        remaining_piece_cell_count = sum(len(p['shapeData']) for p in remaining_pieces_data)

        if remaining_piece_cell_count != total_unplaced_cells:
            return {
                'solutions': [], 'solutionCount': 0, 'solutionsReturned': 0,
                'timedOut': False, 'limitReached': False,
                'message': f"Unsolvable: {remaining_piece_cell_count} cells in pieces, {total_unplaced_cells} empty positions."
            }

        columns = []
        for piece_data in remaining_pieces_data:
            columns.append(f"piece_{piece_data['id']}")
        for pos in required_positions:
            columns.append(f"pos_{pos[0]}_{pos[1]}_{pos[2]}")

        dlx = DancingLinks(columns)
        placement_info = {}

        for piece_data in remaining_pieces_data:
            placements = self._get_placements(piece_data, occupied_positions)

            for placement_id, piece_id, positions in placements:
                if all(pos in required_positions for pos in positions):
                    row_columns = [f"piece_{piece_id}"]
                    for pos in positions:
                        row_columns.append(f"pos_{pos[0]}_{pos[1]}_{pos[2]}")

                    dlx.add_row(placement_id, row_columns)
                    placement_info[placement_id] = (piece_id, positions)

        if not placement_info:
            return {
                'solutions': [], 'solutionCount': 0, 'solutionsReturned': 0,
                'timedOut': False, 'limitReached': False,
                'message': "Unsolvable: No valid placements found."
            }

        solutions = []
        total_solutions_found = [0]
        limit_reached = [False]
        timed_out = [False]

        def solution_callback(solution_placement_ids):
            total_solutions_found[0] += 1

            final_board = dict(board_state) if isinstance(board_state, dict) else {}

            for placement_id in solution_placement_ids:
                piece_id, positions = placement_info[placement_id]
                for pos in positions:
                    final_board[pos] = piece_id

            if len(solutions) < max_samples:
                solutions.append({'board': final_board})

            if len(solutions) >= max_samples:
                limit_reached[0] = True

            current_time_ms = time.time() * 1000
            if max_time and max_time > 0 and current_time_ms - start_time_ms >= max_time:
                timed_out[0] = True

        try:
            dlx.search([], solution_callback, max_samples if not timed_out[0] else None)
        except Exception as e:
            print(f"ERROR: Exception in DLX search: {e}")
            traceback.print_exc()
            raise

        if len(solutions) == 0:
            message = "No solutions found."
        elif timed_out[0]:
            message = f"Found {len(solutions)} solution(s) before time limit."
        elif limit_reached[0]:
            message = f"Found {len(solutions)} solution(s) (sample limit reached)."
        else:
            message = f"Found all {total_solutions_found[0]} solution(s)."

        return {
            'solutions': solutions,
            'solutionCount': total_solutions_found[0],
            'solutionsReturned': len(solutions),
            'timedOut': timed_out[0],
            'limitReached': limit_reached[0],
            'message': message
        }

    def build_incremental_session(self, board_state):
        occupied_positions = set()
        placed_piece_ids = set()

        if board_state is None:
            board_state = {}
        elif isinstance(board_state, dict):
            converted = {}
            for key, val in board_state.items():
                try:
                    if isinstance(key, str):
                        key = key.strip('()')
                        parts = key.split(',')
                        if len(parts) != 3:
                            continue
                        key = tuple(int(p.strip()) for p in parts)
                    converted[key] = val
                except Exception as e:
                    print(f"ERROR parsing key in session: {e}")
                    continue
            board_state = converted

        if isinstance(board_state, dict):
            for pos, piece_id in board_state.items():
                if piece_id != 0:
                    occupied_positions.add(pos)
                    placed_piece_ids.add(piece_id)

        remaining_pieces_data = [p for p in self.pieces_data if p['id'] not in placed_piece_ids]
        all_positions = self.get_all_pyramid_positions()
        required_positions = all_positions - occupied_positions

        total_unplaced_cells = len(required_positions)
        remaining_piece_cell_count = sum(len(p['shapeData']) for p in remaining_pieces_data)

        if remaining_piece_cell_count != total_unplaced_cells:
            return None, None, {
                'unsolvable': True,
                'message': "Unsolvable: Placed pieces do not leave a solvable empty space."
            }

        columns = []
        for piece_data in remaining_pieces_data:
            columns.append(f"piece_{piece_data['id']}")
        for pos in required_positions:
            columns.append(f"pos_{pos[0]}_{pos[1]}_{pos[2]}")

        dlx = DancingLinks(columns)
        placement_info = {}

        for piece_data in remaining_pieces_data:
            placements = self._get_placements(piece_data, occupied_positions)
            for placement_id, piece_id, positions in placements:
                if all(pos in required_positions for pos in positions):
                    row_columns = [f"piece_{piece_id}"] + [f"pos_{pos[0]}_{pos[1]}_{pos[2]}" for pos in positions]
                    dlx.add_row(placement_id, row_columns)
                    placement_info[placement_id] = (piece_id, positions)

        if not placement_info:
            return None, None, {
                'unsolvable': True,
                'message': "Unsolvable: No valid placements found."
            }

        gen = dlx.search_generator()
        return gen, placement_info, {
            'unsolvable': False,
            'board_state': dict(board_state) if isinstance(board_state, dict) else {}
        }


class PyramidSolverSession:

    def __init__(self, solver: PyramidSolver, board_state):
        gen, placement_info, meta = solver.build_incremental_session(board_state)
        if meta and meta.get('unsolvable'):
            raise ValueError(meta.get('message', 'Unsolvable'))
        self.solver = solver
        self.board_state = dict(board_state) if board_state else {}
        self.gen = gen
        self.placement_info = placement_info
        self.total_found = 0
        self.exhausted = False
        self.lock = threading.Lock()
        self.last_used_ms = time.time() * 1000

    def next_batch(self, batch_size=24, max_time=None):
        if self.exhausted:
            return [], self.total_found, True, False

        batch = []
        start_ms = time.time() * 1000
        timed_out = False

        with self.lock:
            while len(batch) < batch_size:
                if max_time and max_time > 0 and (time.time() * 1000 - start_ms) >= max_time:
                    timed_out = True
                    break
                try:
                    rows = next(self.gen)
                except StopIteration:
                    self.exhausted = True
                    break

                final_board = dict(self.board_state)
                for placement_id in rows:
                    piece_id, positions = self.placement_info[placement_id]
                    for pos in positions:
                        final_board[pos] = piece_id
                batch.append({'board': final_board})
                self.total_found += 1

            self.last_used_ms = time.time() * 1000

        return batch, self.total_found, self.exhausted, timed_out


solverKanoodle = KanoodleSolver

class SolverSession:
    def __init__(self, solver, board_state):
        gen, placement_info, meta = solver.build_incremental_session(board_state)
        if meta and meta.get('unsolvable'):
            raise ValueError(meta.get('message', 'Unsolvable'))
        self.solver = solver
        self.board_state = [list(row) for row in board_state] if board_state else [[0]*solver.width for _ in range(solver.height)]
        self.gen = gen
        self.placement_info = placement_info
        self.total_found = 0
        self.exhausted = False
        self.lock = threading.Lock()
        self.last_used_ms = time.time() * 1000

    def next_batch(self, batch_size=24, max_time=None):
        if self.exhausted:
            return [], self.total_found, True, False

        batch = []
        start_ms = time.time() * 1000
        timed_out = False

        with self.lock:
            while len(batch) < batch_size:
                if max_time and max_time > 0 and (time.time() * 1000 - start_ms) >= max_time:
                    timed_out = True
                    break
                try:
                    rows = next(self.gen)
                except StopIteration:
                    self.exhausted = True
                    break
                final_board = [list(row) for row in self.board_state]
                for placement_id in rows:
                    piece_id, positions = self.placement_info[placement_id]
                    for x, y in positions:
                        final_board[y][x] = piece_id
                batch.append({'board': final_board})
                self.total_found += 1

            self.last_used_ms = time.time() * 1000

        return batch, self.total_found, self.exhausted, timed_out


_SESSIONS = {}
_SESSIONS_MAX = 32

def _evict_old_sessions():
    if len(_SESSIONS) <= _SESSIONS_MAX:
        return
    oldest_key = None
    oldest_time = float('inf')
    for k, sess in _SESSIONS.items():
        if sess.last_used_ms < oldest_time:
            oldest_time = sess.last_used_ms
            oldest_key = k
    if oldest_key is not None:
        _SESSIONS.pop(oldest_key, None)

def get_session(session_key):
    return _SESSIONS.get(session_key)

def create_session(session_key, solver, board_state):
    if hasattr(solver, 'levels'):
        sess = PyramidSolverSession(solver, board_state)
    else:
        sess = SolverSession(solver, board_state)
    _SESSIONS[session_key] = sess
    _evict_old_sessions()
    return sess

def delete_session(session_key):
    _SESSIONS.pop(session_key, None)


def get_redis_client():
    if redis is None:
        return None
    try:
        client = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None

def _hash_json(obj):
    s = json.dumps(obj, separators=(',', ':'), sort_keys=True)
    return hashlib.sha1(s.encode('utf-8')).hexdigest()

def hash_board_state(width, height, board_state):
    if board_state is None:
        board_state = [[0]*width for _ in range(height)]
    return _hash_json({'w': width, 'h': height, 'b': board_state})

def hash_pieces(pieces_for_solver):
    minimal = sorted(((int(p['id']), p['shapeData']) for p in pieces_for_solver), key=lambda x: x[0])
    return _hash_json(minimal)

def make_cache_keys(width, height, board_state, pieces_for_solver):
    bh = hash_board_state(width, height, board_state)
    ph = hash_pieces(pieces_for_solver)
    base = f"kanoodle:solutions:{width}x{height}:{ph}:{bh}"
    return base, base+":meta"
