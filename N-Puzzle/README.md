# (n²-1)-Puzzle A* Visualizer

An A* search solver for the sliding-tile puzzle (the 8-puzzle, 15-puzzle, and beyond), generalized to arbitrary board size `n`, with a pygame visualization that animates the optimal solution one move at a time.

## What it shows

Solving a sliding puzzle has two very different difficulty profiles, and this project is built to make that contrast visible:

- **Deciding solvability is linear time.** Whether a scramble can reach the goal is settled by a single inversion-count parity check.
- **Finding the *optimal* (shortest) solution is NP-hard** for the generalized (n²-1)-puzzle (Ratner and Warmuth, 1990). A* with the Manhattan-distance heuristic finds optimal solutions, but its time and memory grow exponentially with the optimal solution depth.

As `n` scales, you can watch A* go from solving instantly (3×3, 4×4) to choking on the exponential growth of the search frontier (5×5, 6×6). To keep larger boards demonstrable, the generator offers two modes:

- **Easy mode** (`easy_state`): a depth-bounded random walk from the goal, capping the optimal solution length so A* stays tractable even on 5×5 and 6×6.
- **Random mode** (`random_state`): a uniformly shuffled, solvability-filtered state, which on large boards pushes A* into exponential blowup, the behavior the project is meant to expose.

## How it works

- **Board representation:** states are nibble-packed into a single integer, using `(n²-1).bit_length()` bits per tile, for compact storage and fast swaps.
- **Search:** A* over a `heapq` min-heap keyed by `(f, g, state)`, with Manhattan distance as the admissible heuristic.
- **Solvability:** inversion-parity test, accounting for grid width and the blank-row position.
- **Visualization:** the reconstructed solution path is replayed move by move in pygame, with smoothstep tile-slide animation; transitions are driven as the path is consumed, not as it is generated.

## Usage

Set `n` and the `easy` flag in `__main__`. For `n >= 4`, `easy = True` uses the bounded scramble; `easy = False` uses a full random state. For `n < 4` it always uses a random state.

```bash
python npuzzle.py
```

### Controls

- `SPACE` / `ENTER` skip the intro pause and start the animation
- `ESC` or closing the window quits

## Files

- `npuzzle.py` solver, board representation, A* search, and entry point
- `visuals.py` pygame rendering and animation
