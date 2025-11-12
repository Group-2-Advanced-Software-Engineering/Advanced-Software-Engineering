from django.test import TestCase
import hashlib

from .util import solverKanoodle

def board_hash(board):
	"""Stable hash of a 2D board array."""
	flat = ''.join(''.join(str(c) for c in row) for row in board)
	return hashlib.md5(flat.encode('utf-8')).hexdigest()

def brute_force_solutions(width, height, pieces):
	"""Brute force solver for tiny boards to validate DLX completeness.
	pieces: list of {id, shapeData} using relative coords.
	Returns list of board arrays.
	"""
	board = [[0 for _ in range(width)] for _ in range(height)]
	solutions = []

	def rotations_and_flips(cells):
		def normalize(shape):
			minx = min(p[0] for p in shape); miny = min(p[1] for p in shape)
			return tuple(sorted((x-minx, y-miny) for x,y in shape))
		out = []
		seen = set()
		for flip_flag in (False, True):
			base = [(-x, y) if flip_flag else (x, y) for (x,y) in cells]
			for r in range(4):
				rot = []
				for (x,y) in base:
					nx, ny = x, y
					for _ in range(r):
						nx, ny = ny, -nx
					rot.append((nx, ny))
				norm = normalize(rot)
				if norm not in seen:
					seen.add(norm)
					out.append(list(norm))
		return out

	oriented = {}
	for p in pieces:
		oriented[p['id']] = rotations_and_flips(p['shapeData'])

	def place(piece_id, shape, x0, y0):
		coords = []
		for (x,y) in shape:
			xx, yy = x0 + x, y0 + y
			if xx < 0 or yy < 0 or xx >= width or yy >= height: return None
			if board[yy][xx] != 0: return None
			coords.append((xx,yy))
		for (xx,yy) in coords:
			board[yy][xx] = piece_id
		return coords

	def unplace(coords):
		for (xx,yy) in coords:
			board[yy][xx] = 0

	remaining = [p['id'] for p in pieces]

	def search(idx):
		if idx == len(remaining):
			if all(c!=0 for row in board for c in row):
				solutions.append([row[:] for row in board])
			return
		pid = remaining[idx]
		for shape in oriented[pid]:
			maxx = max(x for x,_ in shape); maxy = max(y for _,y in shape)
			for y in range(height - maxy):
				for x in range(width - maxx):
					coords = place(pid, shape, x, y)
					if coords is None: continue
					search(idx+1)
					unplace(coords)
	search(0)
	return solutions

class CorrectnessTests(TestCase):
	def test_tiny_board_exhaustive(self):
		"""Compare DLX enumeration with brute-force on a tiny 3x3 board using three tromino-like pieces covering all 9 cells."""
		pieces = [
			{'id':1,'name':'I3','shapeData':[(0,0),(1,0),(2,0)]},         
			{'id':2,'name':'L3','shapeData':[(0,0),(0,1),(1,1)]},             
			{'id':3,'name':'V3','shapeData':[(0,0),(0,1),(0,2)]},            
		]
		width,height = 3,3
		dlx = solverKanoodle(width,height,pieces)
		result = dlx.solvePartial(board_state=None, max_samples=10000, max_time=0)
		dlx_solutions = [sol['board'] for sol in result.get('solutions', [])]
		dlx_hashes = {board_hash(b) for b in dlx_solutions}
		brute = brute_force_solutions(width,height,pieces)
		brute_hashes = {board_hash(b) for b in brute}
		self.assertEqual(dlx_hashes, brute_hashes, f"Mismatch: DLX={len(dlx_hashes)} brute={len(brute_hashes)}")

	def test_stability_and_uniqueness(self):
		"""Run DLX twice on same tiny puzzle and assert identical ordered hashes and no duplicates."""
		pieces = [
			{'id':1,'name':'I3','shapeData':[(0,0),(1,0),(2,0)]},
			{'id':2,'name':'L3','shapeData':[(0,0),(0,1),(1,1)]},
			{'id':3,'name':'V3','shapeData':[(0,0),(0,1),(0,2)]},
		]
		width,height = 3,3
		def run_once():
			dlx = solverKanoodle(width,height,pieces)
			result = dlx.solvePartial(board_state=None, max_samples=10000, max_time=0)
			return [board_hash(sol['board']) for sol in result.get('solutions', [])]
		a = run_once()
		b = run_once()
		self.assertEqual(a, b, "Solution order is not stable across runs")
		self.assertEqual(len(a), len(set(a)), "Duplicate solutions emitted in DLX run")

	def test_small_board_positive(self):
		"""Positive parity test: 1x4 board tiled by two 2-cell domino pieces should yield >0 solutions and DLX == brute-force set."""
		pieces = [
			{'id':1,'name':'DominoA','shapeData':[(0,0),(1,0)]},
			{'id':2,'name':'DominoB','shapeData':[(0,0),(1,0)]},
		]
		width,height = 4,1
		dlx = solverKanoodle(width,height,pieces)
		result = dlx.solvePartial(board_state=None, max_samples=1000, max_time=0)
		dlx_boards = [sol['board'] for sol in result.get('solutions', [])]
		dlx_hashes = {board_hash(b) for b in dlx_boards}
		brute = brute_force_solutions(width,height,pieces)
		brute_hashes = {board_hash(b) for b in brute}
		self.assertGreater(len(dlx_hashes), 0, "Expected >0 solutions for 1x4 with two dominoes")
		self.assertEqual(dlx_hashes, brute_hashes, f"Positive mismatch: DLX={len(dlx_hashes)} brute={len(brute_hashes)}")

	def test_no_identical_piece_shapes(self):
		"""Verify that in the main Kanoodle piece set no two distinct piece IDs are shape-identical under rotations/flips."""
		import json, os
		json_path = os.path.join(os.path.dirname(__file__), 'JSONs', 'piece_data.json')
		with open(json_path, 'r') as f:
			data = json.load(f)
		pieces = [d['fields'] | {'id': d['pk']} for d in data if d['model'].endswith('.piece')]

		def normalize(coords):
			minx = min(x for x,y in coords); miny = min(y for x,y in coords)
			return tuple(sorted(((x-minx, y-miny) for x,y in coords)))

		def rotations_flips(shape):
			shape = [tuple(c) for c in shape]
			out = set()
			for flip_flag in (False, True):
				base = [(-x if flip_flag else x, y) for x,y in shape]
				for r in range(4):
					rot = []
					for x,y in base:
						xr, yr = x, y
						for _ in range(r):
							xr, yr = yr, -xr
						rot.append((xr, yr))
					out.add(normalize(rot))
			return out

		canonical_map = {}
		for p in pieces:
			all_orients = rotations_flips(p['shapeData'])
			canon = min(all_orients)
			canonical_map.setdefault(canon, []).append(p['id'])

		duplicates = [grp for grp in canonical_map.values() if len(grp) > 1]
		self.assertEqual(duplicates, [], f"Found shape-identical piece groups: {duplicates}")

