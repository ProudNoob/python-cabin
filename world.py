# world.py
from typing import List, Tuple

# Map is a fixed 7x7 grid:
# - Outer ring (y=0 and y=6, x=0 and x=6) = trees (impassable)
# - North fence at y=1, South fence at y=5
# - Ground elsewhere; Cabin center at (3,3)

TREE = "🌲"
FENCE = "#"
GROUND = "."
CABIN = "C"
PLAYER = "@"

WIDTH = 7
HEIGHT = 7

CABIN_POS = (3, 3)

def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < WIDTH and 0 <= y < HEIGHT

def is_tree(x: int, y: int) -> bool:
    return x == 0 or x == WIDTH - 1 or y == 0 or y == HEIGHT - 1

def is_fence(x: int, y: int) -> bool:
    return (y == 1 or y == HEIGHT - 2) and (0 < x < WIDTH - 1)

def is_cabin(x: int, y: int) -> bool:
    return (x, y) == CABIN_POS

def is_walkable(x: int, y: int) -> bool:
    # You can walk on ground and the cabin tile. Fences/trees are walls.
    if not in_bounds(x, y):
        return False
    if is_tree(x, y):
        return False
    if is_fence(x, y):
        return False
    return True  # includes GROUND and CABIN

def neighbors4(x: int, y: int) -> List[Tuple[int, int]]:
    cand = [(x, y-1), (x, y+1), (x-1, y), (x+1, y)]
    return [(nx, ny) for nx, ny in cand if in_bounds(nx, ny)]

def tile_char(x: int, y: int) -> str:
    if is_tree(x, y):
        return TREE
    if is_fence(x, y):
        return FENCE
    if is_cabin(x, y):
        return CABIN
    return GROUND

def render(player_xy: Tuple[int, int]) -> str:
    px, py = player_xy
    rows = []
    for y in range(HEIGHT):
        line = []
        for x in range(WIDTH):
            if (x, y) == (px, py):
                line.append(PLAYER)
            else:
                line.append(tile_char(x, y))
        rows.append("".join(line))
    # Add a small legend below
    rows.append("")
    rows.append("Legend: @ You   C Cabin   # Fence   🌲 Trees   . Ground")
    return "\n".join(rows)

def near_trees(x: int, y: int) -> bool:
    # True if any adjacent tile (4-dir) is a TREE
    for nx, ny in neighbors4(x, y):
        if is_tree(nx, ny):
            return True
    return False

def at_cabin(x: int, y: int) -> bool:
    return is_cabin(x, y)

def near_fence(x: int, y: int) -> bool:
    # True if any adjacent tile is a fence
    for nx, ny in neighbors4(x, y):
        if is_fence(nx, ny):
            return True
    return False