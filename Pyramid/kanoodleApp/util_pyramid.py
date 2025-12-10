import time
from typing import List, Tuple, Dict


class PyramidStructure:
    """Represents the 3D pyramid structure using lattice coordinates"""

    def __init__(self, levels=5):
        self.base = levels
        self.limit = levels * 2 - 1
        self.valid_positions = self._generate_lattice_positions()
        self.position_to_index = {pos: idx for idx, pos in enumerate(self.valid_positions)}

    def _generate_lattice_positions(self) -> List[Tuple[int, int, int]]:
        """Generate all valid lattice positions in the pyramid"""
        positions = []
        for z in range(self.base):
            min_xy = z
            max_xy = self.limit - z
            odd = z & 1

            for x in range(min_xy, max_xy + 1, 2):
                if (x & 1) != odd:
                    continue
                for y in range(min_xy, max_xy + 1, 2):
                    if (y & 1) != odd:
                        continue
                    positions.append((z, x, y))

        return sorted(positions)

    def in_lattice(self, z: int, x: int, y: int) -> bool:
        """Check if a lattice position is valid"""
        min_xy = z
        limit_xy = self.limit - z
        odd = z & 1

        return (
                z >= 0 and z < self.base and
                odd == (x & 1) and
                odd == (y & 1) and
                min_xy <= x <= limit_xy and
                min_xy <= y <= limit_xy
        )

    def grid_to_lattice(self, grid_x: int, grid_y: int, grid_z: int) -> Tuple[int, int, int]:
        """Convert frontend grid coordinates to backend lattice coordinates"""
        # Frontend: grid coordinates (0-4 range)
        # Backend: lattice coordinates (doubled, with z offset)
        backend_z = (self.base - 1) - grid_z

        x = grid_x * 2 + backend_z
        y = grid_y * 2 + backend_z
        return (backend_z, x, y)

    def lattice_to_grid(self, lat_z: int, lat_x: int, lat_y: int) -> Tuple[int, int, int]:
        """Convert backend lattice coordinates to frontend grid coordinates"""
        # Backend: lattice coordinates
        # Frontend: grid coordinates
        backend_z = lat_z
        grid_z = (self.base - 1) - backend_z

        x = (lat_x - backend_z) // 2
        y = (lat_y - backend_z) // 2
        return (x, y, grid_z)


class PolyspherePiece:
    """Represents a polysphere piece in lattice coordinates"""

    def __init__(self, piece_id: int, name: str, color: str, shape: List[List[int]]):
        self.id = piece_id
        self.name = name
        self.color = color

        # Convert 2D shape to lattice coordinates (z=0, doubled coordinates)
        self.base_points = []
        for coord in shape:
            if len(coord) == 2:
                # 2D: double coordinates for lattice
                self.base_points.append((0, coord[0] * 2, coord[1] * 2))
            else:
                # 3D: convert to lattice
                x, y, z = coord[0], coord[1], coord[2] if len(coord) > 2 else 0
                self.base_points.append((z, x * 2, y * 2))

        self.base_points.sort()
        self.size = len(self.base_points)

        # Calculate dimensions
        if self.base_points:
            self.width = max(p[1] for p in self.base_points) + 1
            self.depth = max(p[2] for p in self.base_points) + 1
            self.height = max(p[0] for p in self.base_points) + 1
        else:
            self.width = self.depth = self.height = 0

        # Generate all rotations
        self.rotations = self._generate_rotations()
        print(f"Piece {self.id} ({self.name}): {len(self.rotations)} rotations")

    def _rotate_right(self, points: List[Tuple], width: int) -> List[Tuple]:
        """Rotate piece 90° clockwise"""
        wo = width
        if wo & 1:
            wo -= 1
        return sorted([(z, y, wo - x) for z, x, y in points])

    def _rotate_xy_z(self, point: Tuple) -> Tuple:
        """Rotate in XY-Z space"""
        z, x, y = point
        x2 = x // 2
        y2 = y // 2
        xy = x2 + y2
        z_ = x2 - y2
        return (z_, xy, xy)

    def _rotate_up(self, points: List[Tuple]) -> Tuple:
        """Rotate piece up"""
        rs = sorted([self._rotate_xy_z(p) for p in points])

        if not rs:
            return (0, 0, 0, [])

        min_z = rs[0][0]
        min_xy = min(p[1] for p in rs)
        xyo = -(min_z & 1)

        if min_xy + xyo < 0:
            xyo += 2

        rsa = [(z - min_z, x + xyo, y + xyo) for z, x, y in rs]
        max_z = max(p[0] for p in rs)
        wd = max(p[1] for p in rsa) + 1

        return (wd, wd, max_z - min_z + 1, rsa)

    def _generate_rotations(self) -> List[Tuple]:
        """Generate all unique rotations"""
        all_rots = []
        current = (self.width, self.depth, self.height, self.base_points)

        for _ in range(4):
            w, d, h, pts = current
            all_rots.append((w, d, h, pts))

            # Rotate up
            ru = self._rotate_up(pts)
            all_rots.append(ru)

            # Rotate right after up
            w_ru, d_ru, h_ru, pts_ru = ru
            if pts_ru:
                rr = self._rotate_right(pts_ru, w_ru)
                wd_rr = max(p[1] for p in rr) + 1 if rr else 0
                dd_rr = max(p[2] for p in rr) + 1 if rr else 0
                all_rots.append((wd_rr, dd_rr, h_ru, rr))

            # Rotate right for next iteration
            current = (d, w, h, self._rotate_right(pts, w))

        # Deduplicate
        all_rots.sort()
        unique = [all_rots[0]]
        for rot in all_rots[1:]:
            if rot != unique[-1]:
                unique.append(rot)

        return unique


class DancingLinksPyramid:
    """Dancing Links for exact cover"""
    #changed to mark pieces so that is should be able to solve for different sizes
    #by ignoring pieces that dont fit

    class Node:
        def __init__(self, row_id=None):
            self.left = self.right = self.up = self.down = self
            self.column = None
            self.row_id = row_id
            self.size = 0

    def __init__(self, columns):
        self.header = self.Node()
        self.columns = {}
        self.solutions = []
        self.start_time = None
        self.max_time = None
        self.timed_out = False

        prev = self.header
        for col_name in columns:
            col = self.Node()
            col.size = 0
            col.name = col_name
            col.column = col
            self.columns[col_name] = col

            if col_name.startswith("pos_"):
                col.is_primary = True
            else:
                col.is_primary = False

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
            node = self.Node(row_id=row_id)
            node.column = col

            node.up = col.up
            node.down = col
            col.up.down = node
            col.up = node
            col.size += 1

            nodes.append(node)

        if nodes:
            for i in range(len(nodes)):
                nodes[i].left = nodes[i - 1]
                nodes[i].right = nodes[(i + 1) % len(nodes)]

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
        if self.max_time and self.max_time > 0:
            elapsed = (time.time() - self.start_time) * 1000
            if elapsed >= self.max_time:
                self.timed_out = True
                return len(self.solutions)

        if max_solutions and len(self.solutions) >= max_solutions:
            return len(self.solutions)

        if self.header.right == self.header:
            callback(solution[:])
            return len(self.solutions)

        min_col = None
        min_size = float('inf')
        col = self.header.right
        while col != self.header:
            if getattr(col, "is_primary", True):
                if col.size < min_size:
                    min_size = col.size
                    min_col = col
            col = col.right

        if min_col is None or min_col.size == 0:
            return len(self.solutions)

        self.cover(min_col)
        row = min_col.down

        while row != min_col:
            solution.append(row.row_id)

            j = row.right
            while j != row:
                self.cover(j.column)
                j = j.right

            self.search(solution, callback, max_solutions)

            j = row.left
            while j != row:
                self.uncover(j.column)
                j = j.left

            solution.pop()
            row = row.down

        self.uncover(min_col)
        return len(self.solutions)


class PyramidSolver:
    """Main solver for 3D Kanoodle Pyramid"""

    def __init__(self, pieces_data: List[Dict], levels=5):
        self.pyramid = PyramidStructure(levels)
        self.pieces_data = pieces_data
        self.locked_positions = set()
        self.placed_pieces = []

    def set_locked_positions(self, board_state: Dict):
        """Extract locked positions from board state (frontend format)"""
        self.locked_positions = set()
        piece_positions = {}


        for key, piece_id in board_state.items():
            if not piece_id:
                continue

            parts = key.replace('(', '').replace(')', '').split(',')
            grid_x, grid_y, grid_z = int(parts[0]), int(parts[1]), int(parts[2])

            # Convert frontend grid to backend lattice
            lat_z, lat_x, lat_y = self.pyramid.grid_to_lattice(grid_x, grid_y, grid_z)

            self.locked_positions.add((lat_z, lat_x, lat_y))

            if piece_id not in piece_positions:
                piece_positions[piece_id] = []
            piece_positions[piece_id].append((lat_z, lat_x, lat_y))

        self.placed_pieces = []
        for piece_id, positions in piece_positions.items():
            piece_data = next((p for p in self.pieces_data if p['id'] == piece_id), None)
            if piece_data:
                self.placed_pieces.append({
                    'piece_id': piece_id,
                    'piece_name': piece_data['name'],
                    'color': piece_data['color'],
                    'positions': positions
                })

    def solve(self, max_solutions=100, max_time=None):
        """
        Solve the pyramid puzzle
        Returns: (solutions, exhausted, timed_out)
        """
        placed_ids = {p['piece_id'] for p in self.placed_pieces}
        available_pieces = [p for p in self.pieces_data if p['id'] not in placed_ids]

        polyspheres = []
        for piece_data in available_pieces:
            polysphere = PolyspherePiece(
                piece_id=piece_data['id'],
                name=piece_data['name'],
                color=piece_data['color'],
                shape=piece_data['shapeData']
            )
            polyspheres.append(polysphere)

        available_positions = [
            pos for pos in self.pyramid.valid_positions
            if pos not in self.locked_positions
        ]

        capacity = len(available_positions)
        print("DEBUG: Pyramid capacity:", capacity)

        usable_pieces = []
        piece_placements = {}  # cache placements

        for poly in polyspheres:
            placements = self._generate_placements(poly, available_positions)
            piece_placements[poly.id] = placements

            if len(placements) == 0:
                print(f"Skipping {poly.name}: cannot place in this pyramid size")
            else:
                usable_pieces.append(poly)

        print(f"DEBUG: {len(usable_pieces)} pieces can physically fit this pyramid.")

        # If all pieces fit and capacity matches 55, just solve normally
        if len(usable_pieces) == len(polyspheres) and capacity == 55:
            print("DEBUG: Standard 12-piece pyramid, solving normally.")
            return self._solve_with_piece_set(usable_pieces, available_positions, piece_placements, max_solutions,max_time)
        import itertools

        valid_subsets = []
        for r in range(1, len(usable_pieces) + 1):
            for subset in itertools.combinations(usable_pieces, r):
                total_size = sum(p.size for p in subset)
                if total_size == capacity:
                    valid_subsets.append(subset)

        print(f"DEBUG: {len(valid_subsets)} valid piece subsets match the required cell count.")

        if not valid_subsets:
            print("No possible set of pieces can fill this pyramid exactly.")
            return [], True, False

        all_solutions = []
        timed_out = False
        exhausted = True

        for subset in valid_subsets:
            subset_solutions, sub_exhausted, sub_timeout = self._solve_with_piece_set(
                subset, available_positions, piece_placements, max_solutions, max_time
            )
            all_solutions.extend(subset_solutions)

            if sub_timeout:
                timed_out = True
            if not sub_exhausted:
                exhausted = False

            if len(all_solutions) >= max_solutions:
                break

        print(f"DEBUG: Total solutions from all subsets: {len(all_solutions)}")
        return all_solutions, exhausted, timed_out

    def _solve_with_piece_set(self, piece_set, available_positions, piece_placements, max_solutions, max_time):
        """Run DLX for a single selected subset of pieces."""

        # Build DLX columns
        columns = []
        for pos in available_positions:
            columns.append(f"pos_{pos[0]}_{pos[1]}_{pos[2]}")
        for poly in piece_set:
            columns.append(f"piece_{poly.id}")

        dlx = DancingLinksPyramid(columns)
        placement_info = {}

        # Add rows for the selected pieces ONLY
        for poly in piece_set:
            for placement_id, positions in piece_placements[poly.id]:
                row_columns = [f"piece_{poly.id}"]
                for pos in positions:
                    row_columns.append(f"pos_{pos[0]}_{pos[1]}_{pos[2]}")
                dlx.add_row((poly.id, placement_id), row_columns)
                placement_info[(poly.id, placement_id)] = {
                    'piece_id': poly.id,
                    'piece_name': poly.name,
                    'color': poly.color,
                    'positions': positions
                }

        solutions = []
        dlx.start_time = time.time()
        dlx.max_time = max_time

        def callback(placement_ids):
            sol = [placement_info[pid] for pid in placement_ids]
            solutions.append(sol)

        dlx.search([], callback, max_solutions)

        return solutions, len(solutions) < max_solutions, dlx.timed_out

    def _generate_placements(self, polysphere: PolyspherePiece, available_positions: List[Tuple]):
        """Generate all valid placements"""
        placements = []
        placement_id = 0

        for rotation in polysphere.rotations:
            w, d, h, points = rotation

            if not points:
                continue
            fz, fx, fy = points[0]

            for place_pos in available_positions:
                if place_pos in self.locked_positions:
                    continue

                z, x, y = place_pos
                zo = z - fz
                xo = x - fx
                yo = y - fy

                absolute_positions = []
                valid = True

                for pz, px, py in points:
                    abs_z = pz + zo
                    abs_x = px + xo
                    abs_y = py + yo

                    if not self.pyramid.in_lattice(abs_z, abs_x, abs_y):
                        valid = False
                        break

                    abs_pos = (abs_z, abs_x, abs_y)
                    if abs_pos in self.locked_positions:
                        valid = False
                        break

                    absolute_positions.append(abs_pos)

                if valid:
                    placements.append(((polysphere.id, placement_id), absolute_positions))
                    placement_id += 1

        return placements