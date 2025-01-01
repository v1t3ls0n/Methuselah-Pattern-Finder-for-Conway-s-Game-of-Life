
"""
Optimized_GameOfLife.py
-----------------------
    
This module implements Conway's Game of Life, optimized for performance while maintaining a
1D grid representation. It leverages NumPy's vectorized operations to efficiently compute
state transitions and uses multithreading for parallel computations where applicable. The
simulation retains the original logic, ensuring compatibility with the existing codebase.
    
Classes:
    GameOfLife: Handles the simulation of Conway's Game of Life, including state transitions,
    detecting static or periodic behavior, and tracking relevant statistics with optimized performance.
"""

import logging
import numpy as np
from scipy.signal import convolve2d
from threading import Thread
from queue import Queue


class GameOfLife:
    """
    The GameOfLife class simulates Conway's Game of Life on a 1D flattened NxN grid, optimized
    for large grids using NumPy for vectorized operations. It tracks the evolution of the grid
    through multiple generations, stopping when the grid becomes static (unchanging) or periodic
    (repeats a previously encountered state), or when a maximum iteration limit is exceeded.

    Attributes:
        grid_size (int): The dimension N of the NxN grid.
        grid (numpy.ndarray): A 1D NumPy array of length N*N, representing the grid's cells (0=dead, 1=alive).
        initial_state (tuple[int]): The initial configuration of the grid (immutable).
        history (list[tuple[int]]): A record of all states encountered during the simulation.
        game_iteration_limit (int): Maximum number of generations to simulate.
        stable_count (int): Tracks consecutive generations where the state is static or periodic.
        max_stable_generations (int): Threshold for terminating the simulation if stable_count is reached.
        lifespan (int): Number of unique states the grid has passed through before stopping.
        is_static (bool): Indicates whether the grid has become static.
        is_periodic (bool): Indicates whether the grid has entered a periodic cycle.
        max_alive_cells_count (int): Maximum number of alive cells observed during the simulation.
        alive_growth (float): Ratio between the maximum and minimum alive cell counts across generations.
        alive_history (list[int]): History of alive cell counts for each generation.
        stableness (float): Ratio indicating how often the grid reached stable behavior (static or periodic).
    """

    def __init__(self, grid_size, initial_state=None):
        """
        Initializes the GameOfLife simulation with a given grid size and optional initial state.

        Args:
            grid_size (int): Size of the NxN grid.
            initial_state (Iterable[int], optional): Flattened list of the grid's initial configuration.
                If None, the grid is initialized to all zeros (dead cells).

        The initial state is stored as an immutable tuple, and the simulation starts with
        an empty history except for the initial configuration.
        """
        self.grid_size = grid_size
        if initial_state is None:
            self.grid = np.zeros(grid_size * grid_size, dtype=int)
        else:
            if len(initial_state) != grid_size * grid_size:
                raise ValueError(f"Initial state must have {grid_size * grid_size} elements.")
            self.grid = np.array(initial_state, dtype=int)

        # Store the immutable initial state
        self.initial_state = tuple(self.grid)
        self.history = []
        self.game_iteration_limit = 150000
        self.stable_count = 0
        self.max_stable_generations = 10
        self.lifespan = 0
        self.is_static = False
        self.is_periodic = False
        self.alive_history = [np.sum(self.grid)]
        self.unique_states = set()
        self.unique_states.add(self.initial_state)

    def _grid_to_hashable(self, grid):
        """
        Converts a NumPy grid to a hashable tuple for state comparison.

        Args:
            grid (numpy.ndarray): The grid to convert.

        Returns:
            tuple: A tuple representation of the grid.
        """
        return tuple(grid.flatten())

    def _count_alive_neighbors(self, grid):
        """
        Counts the number of alive neighbors for each cell in the grid using convolution.

        Args:
            grid (numpy.ndarray): The current grid as a 1D NumPy array.

        Returns:
            numpy.ndarray: A 1D NumPy array with the count of alive neighbors for each cell.
        """
        # Reshape to 2D for convolution
        grid_2d = grid.reshape((self.grid_size, self.grid_size))

        # Define the convolution kernel to count alive neighbors
        kernel = np.array([[1, 1, 1],
                           [1, 0, 1],
                           [1, 1, 1]])

        # Count alive neighbors using convolution with periodic boundary conditions
        neighbor_count_2d = convolve2d(grid_2d, kernel, mode='same', boundary='wrap')

        # Flatten back to 1D
        neighbor_count = neighbor_count_2d.flatten()

        return neighbor_count

    def _compute_next_generation(self, current_grid, neighbor_count):
        """
        Computes the next generation of the grid based on the current grid and neighbor counts.

        Args:
            current_grid (numpy.ndarray): The current grid as a 1D NumPy array.
            neighbor_count (numpy.ndarray): A 1D NumPy array with the count of alive neighbors for each cell.

        Returns:
            numpy.ndarray: The next generation grid as a 1D NumPy array.
        """
        # Apply the Game of Life rules using NumPy's vectorized operations
        # Rule 1: A living cell with 2 or 3 neighbors survives.
        survive = (current_grid == 1) & ((neighbor_count == 2) | (neighbor_count == 3))
        # Rule 2: A dead cell with exactly 3 neighbors becomes alive.
        birth = (current_grid == 0) & (neighbor_count == 3)
        # Rule 3: All other cells die or remain dead.
        next_grid = np.where(survive | birth, 1, 0)
        return next_grid

    def step(self):
        """
        Executes one generation step in the Game of Life.
        Updates the grid based on neighbor counts and applies the Game of Life rules.
        Checks for static or periodic states after updating.
        """
        current_grid = self.grid.copy()
        neighbor_count = self._count_alive_neighbors(current_grid)
        next_grid = self._compute_next_generation(current_grid, neighbor_count)

        # Convert to tuple for hashing and state tracking
        new_state = tuple(next_grid)
        current_state = tuple(current_grid)

        # Static check: No change from the previous generation
        if np.array_equal(next_grid, current_grid):
            self.is_static = True
            logging.info("Grid has become static.")
        # Periodic check: If the new state matches any previous state (excluding the immediate last)
        elif new_state in self.unique_states:
            self.is_periodic = True
            logging.info("Grid has entered a periodic cycle.")
        else:
            # Update the grid
            self.grid = next_grid
            # Add the new state to history and unique states
            self.history.append(current_state)
            self.unique_states.add(new_state)

    def run(self):
        """
        Runs the Game of Life simulation until one of the following conditions is met:
            1. The grid becomes static.
            2. The grid enters a periodic cycle.
            3. The maximum number of iterations is exceeded.
            4. The stable_count exceeds max_stable_generations.

        During the simulation, the method tracks:
            - Alive cells in each generation.
            - Maximum alive cells observed.
            - Alive growth (max/min alive cells ratio).
            - Stableness (ratio of stable states to max_stable_generations).
        """
        limiter = self.game_iteration_limit

        while limiter > 0 and ((not self.is_static and not self.is_periodic) or self.stable_count < self.max_stable_generations):
            alive_cell_count = np.sum(self.grid)
            # If no cells are alive, mark as static
            if alive_cell_count == 0:
                self.is_static = True
                logging.info("All cells are dead. Grid has become static.")
                self.alive_history.append(0)
                break

            self.alive_history.append(alive_cell_count)
            # Append the current state to history
            self.history.append(tuple(self.grid))

            if self.is_periodic or self.is_static:
                self.stable_count += 1
            else:
                self.lifespan += 1

            self.step()
            limiter -= 1
