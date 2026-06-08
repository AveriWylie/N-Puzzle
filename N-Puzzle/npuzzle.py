import heapq
import random
import visuals
# Optional[int] == Union[int, None]
from typing import Optional, Callable


"""
---------------------------------------------------------------------------
Nibble-packed board (internal representation)
---------------------------------------------------------------------------
Tile at flat index i occupies bits [4i, 4i+4).

pack: tuple - int (used once at A* entry and per neighbor)
unpack: int - tuple (used once when reconstructing the solution path)
pack_swap: swap two nibbles without unpacking, pure bit manipulation
packed_blank: scan nibbles for the zero tile
---------------------------------------------------------------------------
"""
def pack(state: tuple[int, ...]) -> int:
    bits = (len(state) - 1).bit_length()
    result = 0

    for i, v in enumerate(state):
        result |= v << (i * bits)

    return result


def unpack(packed: int, n: int) -> tuple[int, ...]:
    bits = (n * n - 1).bit_length()
    mask = (1 << bits) - 1
    return tuple((packed >> (i * bits)) & mask for i in range(n * n))


def pack_swap(packed: int, i: int, j: int, bits: int) -> int:
    mask = (1 << bits) - 1
    bi, bj = i * bits, j * bits
    vi = (packed >> bi) & mask
    vj = (packed >> bj) & mask
    # ~ bitwise not
    return (packed & ~((mask << bi) | (mask << bj))) | (vj << bi) | (vi << bj)


def packed_blank(packed: int, size: int, bits: int) -> int:
    mask = (1 << bits) - 1
    for i in range(size):
        if not ((packed >> (i * bits)) & mask):
            return i

    raise ValueError("board contains no blank tile")


# ---------------------------------------------------------------------------
# State representation helpers
# ---------------------------------------------------------------------------

def make_goal(n: int) -> tuple[int, ...]:
    return tuple(range(1, n * n)) + (0, )


def random_state(n: int) -> tuple[int, ...]:
    tiles = list(range(n * n))

    while True:
        random.shuffle(tiles)
        state = tuple(tiles)
        return state


EASY_MOVES = {4: 30, 5: 22, 6: 18}
# just to easily solve higher order n configurations, linear time in this problem very
# easily exponentiates
def easy_state(n: int) -> tuple[int, ...]:
    state = make_goal(n)
    prev = None
    moves = EASY_MOVES.get(n, 4 * n)

    for _ in range(moves):
        options = [s for s in get_neighbors(state, n) if s != prev]
        prev = state
        state = random.choice(options)

    return state


def find_blank(state: tuple[int, ...], n: int) -> tuple[int, int]:
    i = state.index(0)
    # in flattened 2d grid i = i //n and j = 1 % n
    return i // n, i % n


def swap(state: tuple[int, ...], i: int, j: int) -> tuple[int, ...]:
    lst = list(state)
    # all moves are transpositions
    lst[i], lst[j] = lst[j], lst[i]
    return lst

# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Move generation
# ---------------------------------------------------------------------------

"""
get_neighbors(state, n)
-----------------------------------------------------------------------------
Generates all board states reachable from the current state in exactly one
legal move. A move consists of sliding an adjacent tile into the blank cell,
which is equivalent to swapping the blank with that neighbor.

The four candidate directions and their (row_delta, col_delta) offsets:
    UP    (-1,  0)   blank moves up    = tile above slides down
    DOWN  (+1,  0)   blank moves down  = tile below slides up
    LEFT  ( 0, -1)   blank moves left  = tile to the left slides right
    RIGHT ( 0, +1)   blank moves right = tile to the right slides left

For each direction we compute the neighbor's (row, col), check that it
falls inside the grid (0 <= row < n and 0 <= col < n), then call swap
on the two flat indices to produce the child state.

Each edge in the search graph has cost 1 (one tile moved), so no weight
is attached to the returned states - the caller (astar) increments g by 1.

Parameters:
  state -- flat tuple of the current board
  n -- side length of the board

Returns:
  List of flat tuples, one per legal move (2 to 4 elements).
-----------------------------------------------------------------------------
"""
def get_neighbors(state: tuple[int, ...], n: int) -> list[tuple[int, ...]]:
    row, col = find_blank(state, n)
    blank    = row * n + col
    result   = []

    for (dr, dc) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = row + dr, col + dc

        if 0 <= nr < n and 0 <= nc < n:
            result.append(swap(state, blank, nr * n + nc))

    return result

# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

"""
manhattan_distance(state, n)
-----------------------------------------------------------------------------
For each non-blank tile, compute how many rows and columns it is away from
where it needs to be in the goal state, then sum all those distances.

For tile value v at flat index i:
    current row = i // n,   current col = i % n
    goal row    = (v-1) // n,  goal col = (v-1) % n     (since goal = 1,2,...,n²-1,0)
    contribution = |current_row - goal_row| + |current_col - goal_col|

Why this is admissible: each tile must move at least its Manhattan distance
steps to reach its goal, and no single move can reduce the total by more
than 1. Therefore h(state) <= true_cost(state) for every state, which is
the requirement for A* to guarantee an optimal solution.

Why this dominates misplaced_tiles: every misplaced tile contributes at
least 1 to manhattan_distance, but often more. A heuristic h1 dominates h2
when h1(s) >= h2(s) for all s, more informed heuristics prune more of the
search space, resulting in fewer node expansions.

Time complexity per call: O(n²)  - one pass over the board.

Parameters:
  state  -- flat tuple of the current board
  n -- side length of the board

Returns:
  Non-negative integer: sum of Manhattan distances of all tiles.
-----------------------------------------------------------------------------
"""
def manhattan_distance(state: tuple[int, ...], n: int) -> int:
    total = 0
    for i, v in enumerate(state):
        if v:
            total += abs(i // n - (v - 1) // n) + abs(i % n - (v - 1) % n)

    return total


"""
is_solvable(state, n)
-----------------------------------------------------------------------------
Not every permutation of an n×n board is reachable from the goal state.
Exactly half of all permutations are solvable; the rest form a disjoint
orbit under the legal move set. Running A* on an unsolvable input would
exhaust memory without ever finding a solution, so we check first.

An *inversion* is a pair (i, j) where i < j (in the flat tile ordering,
skipping the blank) but state[i] > state[j]. The parity of the inversion
count determines solvability:

  Odd grid width (n is odd):
      Solvable iff the total number of inversions is EVEN.
      The blank's row does not affect parity for odd-width grids.

  Even grid width (n is even):
      Define blank_row_from_bottom = n - (blank_flat_index // n).
      Solvable iff (inversion_count + blank_row_from_bottom) is ODD.
      The blank's row matters here because moving it vertically changes
      the parity differently on even-width boards.

Derivation sketch: each horizontal move of the blank does not change
inversion parity. Each vertical move on an n-wide board shifts the blank
past n-1 other tiles, changing parity by (n-1) mod 2.

Parameters:
  state - flat tuple of the starting board
  n - side length of the board

Returns:
  True if the puzzle can be solved, False otherwise.
-----------------------------------------------------------------------------
"""
def is_solvable(state: tuple[int, ...], n: int) -> bool:
    tiles      = [v for v in state if v]
    inversions = sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles)) if tiles[i] > tiles[j])

    if n % 2 == 1:                                   # odd-width grid
        return inversions % 2 == 0

    blank_row_from_bottom = n - state.index(0) // n  # even-width grid
    return (inversions + blank_row_from_bottom) % 2 == 1


"""
a*(start, n, heuristic)
-----------------------------------------------------------------------------
Finds the shortest sequence of moves from start to the goal state using
the A* graph-search algorithm.

Core data structures:
    open_set - min-heap of (f, g, packed_state) tuples. f = g + h, where g
               is the exact cost from start and h is the heuristic estimate
               to goal. heapq in Python is a min-heap, so the lowest-f
               state is always popped next. We store packed ints rather than
               tuples: integer comparison is faster than tuple comparison and
               Python integers hash in O(1).
      closed - set of packed ints already expanded (settled). Once a state
               is closed we have the optimal path to it; re-expansion can
               only produce equal or worse paths, so we skip them.
     g_score - dict packed_int -> int. Tracks the best g seen so far for
               each reached state. Used to discard stale heap entries (lazy
               deletion): if we pop a state whose recorded g is lower than
               the popped g, the entry is stale and is skipped.
   came_from - dict packed_int -> packed_int. Stores the predecessor of each
               state along the cheapest known path. Rebuilt into a tuple-list
               once the goal is popped.


Parameters:
  start - flat tuple of the initial board configuration
  n - side length of the board
  heuristic - callable (state, n) -> int; defaults to manhattan_distance

Returns:
  List of states from start to goal inclusive, or None if unsolvable.
-----------------------------------------------------------------------------
"""
def astar(start: tuple[int, ...],n: int, heuristic: Callable = manhattan_distance) -> Optional[list[tuple[int, ...]]]:
    goal_packed = pack(make_goal(n))
    start_packed = pack(start)
    size = n * n
    bits = (size - 1).bit_length()
    # Start at goal
    if start_packed == goal_packed:
        return [start]

    came_from: dict[int, int] = {}
    g_score: dict[int, int] = {start_packed: 0}
    closed: set[int] = set()
    h0 = heuristic(start, n)
    heap: list[tuple[int, int, int]] = [(h0, 0, start_packed)]
    # vectors
    DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))

    while heap:

        _, g, packed = heapq.heappop(heap)

        if packed == goal_packed:
            # Walk came_from (all packed ints) and unpack at reconstruction time.
            path, cur = [], packed

            while cur in came_from:
                path.append(unpack(cur, n))
                cur = came_from[cur]

            path.append(unpack(cur, n))
            path.reverse()

            return path

        if packed in closed:
            continue

        closed.add(packed)
        blank  = packed_blank(packed, size, bits)
        row, col = blank // n, blank % n

        for dr, dc in DIRS:

            nr, nc = row + dr, col + dc

            if not (0 <= nr < n and 0 <= nc < n):
                continue

            nb = pack_swap(packed, blank, nr * n + nc, bits)

            if nb in closed:
                continue

            tg = g + 1

            if tg < g_score.get(nb, 10 ** 9):
                g_score[nb]   = tg
                came_from[nb] = packed
                h = heuristic(unpack(nb, n), n)
                heapq.heappush(heap, (tg + h, tg, nb))

    return None

# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Console display
# ---------------------------------------------------------------------------

"""
print_board(state, n)
-----------------------------------------------------------------------------
Formats a single board state as a human-readable n×n grid. The blank tile
is displayed as '_' (one character) so it visually stands out from numbered
tiles and the grid columns stay aligned.

Rendering approach:
  Slice the flat tuple into n rows of n elements each, convert each tile
  to its string representation (or '_' for 0), right-justify to the width
  of the largest tile value (len(str(n*n - 1)) digits), then join with
  spaces and print each row.

Right-justifying to a consistent width keeps columns from shifting when
single-digit and double-digit tile numbers appear in the same puzzle (e.g.
the 15-puzzle has tiles 1–15).

Parameters:
  state  -- flat tuple of the board to render
  n      -- side length of the board

Returns:
  None  (prints directly to stdout)
-----------------------------------------------------------------------------
"""
def print_board(state: tuple[int, ...], n: int) -> None:
    w = len(str(n * n - 1))
    for r in range(n):
        row_str = "  ".join("_".center(w) if state[r * n + c] == 0 else str(state[r * n + c]).rjust(w) for c in range(n))
        print(row_str)


def print_solution(path: Optional[list[tuple[int, ...]]], n: int) -> None:
    if not path:
        print("No solution found.")
        return

    for step, state in enumerate(path):
        tag = " (initial)" if step == 0 else (" (goal)" if step == len(path) - 1 else "")
        print(f"\nStep {step}{tag}:")
        print_board(state, n)

    print(f"\nSolved in {len(path) - 1} move(s).")

# ---------------------------------------------------------------------------


def solve(initial: tuple[int, ...], n: int) -> None:
    if not is_solvable(initial, n):
        print("This configuration is not solvable.")
        return

    print("Solving...")
    path = astar(initial, n)
    print_solution(path, n)

    if path:
        visuals.visualize(path, n)

# Entry
if __name__ == "__main__":
    n = 3
    easy = True

    if n >= 4 and easy:
        state = easy_state(n)

    else:
        state = random_state(n)

    solve(state, n=n)