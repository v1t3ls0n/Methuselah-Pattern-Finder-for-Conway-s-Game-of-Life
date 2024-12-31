"""
GeneticAlgorithm.py
-------------------

Implements a genetic algorithm to evolve initial configurations for Conway's Game of Life,
optimizing for extended lifespan, higher maximum living cells, greater growth ratio, etc.

Classes:
    GeneticAlgorithm: Manages population evolution through selection, crossover, and mutation
    to optimize Game of Life configurations.
"""

import logging
from GameOfLife import GameOfLife
import random
import math
import numpy as np
import collections


class GeneticAlgorithm:
    """
    GeneticAlgorithm manages the evolution of GameOfLife configurations using genetic principles.
    It iteratively optimizes configurations over multiple generations using fitness evaluation,
    selection, crossover, and mutation.

    Attributes:
        grid_size (int): The NxN grid size for GameOfLife configurations.
        population_size (int): Number of individuals in each population.
        generations (int): Total number of generations to simulate.
        initial_mutation_rate (float): Initial probability of mutation per cell.
        mutation_rate_lower_limit (float): Minimum mutation rate value.
        alive_cells_weight (float): Weight for the maximum number of alive cells in fitness.
        lifespan_weight (float): Weight for lifespan in the fitness score.
        alive_growth_weight (float): Weight for alive cell growth ratio in fitness.
        stableness_weight (float): Weight for stability of configurations in fitness.
        initial_living_cells_count_penalty_weight (float): Weight for penalizing large initial configurations.
        predefined_configurations (optional): Allows injecting pre-made Game of Life configurations.
        population (set[tuple]): Current population of configurations (unique).
        configuration_cache (dict): Stores previously evaluated configurations and results.
        generations_cache (dict): Tracks statistics (e.g., fitness) for each generation.
        mutation_rate_history (list): Tracks mutation rate changes across generations.
    """

    def __init__(self, grid_size, population_size, generations, initial_mutation_rate, mutation_rate_lower_limit,
                 alive_cells_weight, lifespan_weight, alive_growth_weight, stableness_weight, initial_living_cells_count_penalty_weight,
                 predefined_configurations=None):
        """
        Initialize the GeneticAlgorithm class with key parameters.

        Args:
            grid_size (int): NxN grid size.
            population_size (int): Number of individuals per generation.
            generations (int): Total generations to simulate.
            initial_mutation_rate (float): Initial probability of mutation.
            mutation_rate_lower_limit (float): Minimum mutation rate value.
            alive_cells_weight (float): Weight factor for alive cells in fitness.
            lifespan_weight (float): Weight factor for lifespan in fitness.
            alive_growth_weight (float): Weight factor for alive cell growth ratio in fitness.
            stableness_weight (float): Weight factor for configuration stability.
            initial_living_cells_count_penalty_weight (float): Penalizes larger initial configurations.
            alive_cells_per_block (int): Maximum alive cells per block for random initialization.
            alive_blocks (int): Number of blocks to initialize with alive cells.
            predefined_configurations (optional): Allows using predefined patterns for initialization.
        """
        print("Initializing GeneticAlgorithm.")
        self.grid_size = grid_size
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate_lower_limit = mutation_rate_lower_limit
        self.mutation_rate = initial_mutation_rate
        self.alive_cells_weight = alive_cells_weight
        self.lifespan_weight = lifespan_weight
        self.initial_living_cells_count_penalty_weight = initial_living_cells_count_penalty_weight
        self.alive_growth_weight = alive_growth_weight
        self.stableness_weight = stableness_weight
        self.configuration_cache = collections.defaultdict(
            collections.defaultdict)
        self.generations_cache = collections.defaultdict(
            collections.defaultdict)
        self.predefined_configurations = predefined_configurations
        self.population = set()
        self.initial_population = []
        self.mutation_rate_history = []

    def calc_fitness(self, lifespan, max_alive_cells_count, alive_growth, stableness, initial_living_cells_count):
        """
        Calculates the fitness score of a configuration by combining key metrics
        weighted by their respective coefficients.

        Args:
            lifespan (int): Total number of unique states before stopping.
            max_alive_cells_count (int): Maximum living cells in any generation.
            alive_growth (float): Ratio of max to min living cells across generations.
            stableness (float): Stability score based on repeated static or periodic patterns.
            initial_living_cells_count (int): Number of alive cells in the initial configuration.

        Returns:
            float: A fitness score computed as a weighted sum of the provided metrics.
        """
        lifespan_score = lifespan * self.lifespan_weight
        alive_cells_score = max_alive_cells_count * self.alive_cells_weight
        growth_score = alive_growth * self.alive_growth_weight
        stableness_score = stableness * self.stableness_weight
        large_configuration_penalty = (
            1 / max(1, initial_living_cells_count * self.initial_living_cells_count_penalty_weight))
        return ((lifespan_score + alive_cells_score + growth_score + stableness_score) * (large_configuration_penalty))

    def evaluate(self, configuration):
        """
        Evaluates a configuration by simulating its evolution in GameOfLife
        and calculating its fitness score. Results are cached to avoid redundant calculations.

        Args:
            configuration (tuple[int]): Flattened 1D representation of NxN GameOfLife grid.

        Returns:
            dict: Simulation results including fitness, lifespan, and other statistics.
        """

        configuration_tuple = tuple(configuration)

        if configuration_tuple in self.configuration_cache:
            return self.configuration_cache[configuration_tuple]

        def max_difference_with_distance(lst):
            max_value = float('-inf')
            dis = 0
            min_index = 0
            for j in range(1, len(lst)):
                diff = (lst[j] - lst[min_index]) * (j - min_index)
                if diff > max_value:
                    dis = j - min_index
                    max_value = diff
                if lst[j] < lst[min_index]:
                    min_index = j
            return max(max_value, 0) / dis

        expected_size = self.grid_size * self.grid_size
        if len(configuration_tuple) != expected_size:
            raise ValueError(f"""Configuration size must be {
                             expected_size}, but got {len(configuration_tuple)}""")

        # Create and run a GameOfLife instance
        game = GameOfLife(self.grid_size, configuration_tuple)
        game.run()
        max_alive_cells_count = max(game.alive_history)
        initial_living_cells_count = sum(configuration_tuple)
        alive_growth = max_difference_with_distance(game.alive_history)
        stableness = game.stable_count / game.max_stable_generations
        fitness_score = self.calc_fitness(
            lifespan=game.lifespan,
            max_alive_cells_count=max_alive_cells_count,
            alive_growth=alive_growth,
            stableness=stableness,
            initial_living_cells_count=initial_living_cells_count
        )

        self.configuration_cache[configuration_tuple] = {
            'fitness_score': fitness_score,
            'history': tuple(game.history),
            'lifespan': game.lifespan,
            'alive_growth': alive_growth,
            'max_alive_cells_count': max_alive_cells_count,
            'is_static': game.is_static,
            'is periodic': game.is_periodic,
            'stableness': stableness,
            'initial_living_cells_count': initial_living_cells_count
        }
        return self.configuration_cache[configuration_tuple]

    def populate(self):
        """
        Generate a new generation of configurations for the population.

        Process:
            1. Select two parent configurations from the current population based on fitness.
            2. Create a child configuration using crossover between the two parents.
            3. Apply mutation to the child with a probability determined by the mutation rate.
            4. Enrich the population with new individuals periodically.
            5. Evaluate all configurations and retain only the top `population_size` individuals.

        Returns:
            None: Updates the `population` attribute in place.
        """
        new_population = set()

        # Step 1: Generate children from the current population
        for _ in range(self.population_size):
            parent1, parent2 = self.select_parents()
            child = self.crossover(parent1, parent2)
            if random.uniform(0, 1) < self.mutation_rate:
                child = self.mutate(child)

            new_population.add(child)

        # Step 2: Enrich population with new individuals periodically
        if len(self.generations_cache) % 5 == 0:  # Every 10 generations
            logging.info("Enriching population with new individuals.")
            enriched_population = set()
            num_new_individuals = self.population_size // 4  # Add 25% new individuals
            self.enrich_population_with_variety(
                clusters_type_amount=num_new_individuals // 3,
                scatter_type_amount=num_new_individuals // 3,
                basic_patterns_type_amount=num_new_individuals // 3
            )
            enriched_population = self.population.difference(new_population)

            # Boost new individuals' chances by adding them directly to the new population
            new_population.update(enriched_population)

        # Step 3: Combine old and new populations, then evaluate
        combined_population = list(self.population) + list(new_population)
        fitness_scores = [
            (config, self.evaluate(config)['fitness_score'])
            for config in combined_population
        ]
        fitness_scores.sort(key=lambda x: x[1], reverse=True)

        # Step 4: Retain only the top `population_size` configurations
        self.population = {
            config for config, _ in fitness_scores[:self.population_size]
        }

        logging.info(f"Population size after enrichment and filtering: {len(self.population)}")

    def mutate_basic(self, configuration):
        """
        Perform mutation on a given configuration by flipping some cells.

        Mutation Process:
            - The chance of flipping is determined by `self.mutation_rate`.
        Args:
            configuration (tuple[int]): A flattened NxN grid of 0s and 1s representing the configuration.

        Returns:
            tuple[int]: A new configuration with mutations applied.
        """
        new_configuration = list(configuration)
        for i in range(len(configuration)):
            if random.uniform(0, 1) < min(0.5, self.mutation_rate * 5):
                new_configuration[i] = 0 if configuration[i] else 1
        return tuple(new_configuration)

    def mutate_harsh(self, configuration):
        new_configuration = list(configuration)
        cluster_size = random.randint(1, len(new_configuration))
        start = random.randint(0, len(new_configuration) - 1)
        for j in range(cluster_size):
            idx = (start + j) % len(new_configuration)
            new_configuration[idx] = random.randint(0, 1)

        return tuple(new_configuration)

    def mutate_clusters(self, configuration):
        """
        Mutate a configuration by flipping cells in random clusters.
        """
        N = self.grid_size
        new_configuration = list(configuration)
        cluster_size = self.grid_size

        for _ in range(cluster_size):
            if random.uniform(0, 1) < min(0.5, self.mutation_rate * 5):
                center_row = random.randint(0, N - 1)
                center_col = random.randint(0, N - 1)
                for i in range(-1, 2):
                    for j in range(-1, 2):
                        row = (center_row + i) % N
                        col = (center_col + j) % N
                        index = row * N + col
                        new_configuration[index] = 1 if new_configuration[index] == 0 else 0
        return tuple(new_configuration)

    def mutate(self, configuration):
        mutation_methods = [self.mutate_basic, self.mutate_clusters, self.mutate_harsh]
        mutate_func = random.choices(mutation_methods, [0.3, 0.3, 0.4], k=1)[0]
        return mutate_func(configuration)
    # Tournament Selection
    def tournament_selection(self, tournament_size=3):
        """
        Select a parent using tournament selection.
        Args:
            population (list): List of individuals.
            evaluate_func (callable): Function to compute fitness for an individual.
            tournament_size (int): Number of individuals in the tournament.
        Returns:
            Individual selected as a parent.
        """
        candidates = random.sample(list(self.population), k=tournament_size)
        candidates_with_fitness = [(candidate, self.evaluate(candidate)['fitness_score']) for candidate in candidates]
        return max(candidates_with_fitness, key=lambda x: x[1])[0]

    # Roulette Wheel Selection
    def roulette_wheel_selection(self):
        """
        Select a parent using roulette wheel selection.
        Args:
            population (list): List of individuals.
            evaluate_func (callable): Function to compute fitness for an individual.
        Returns:
            Individual selected as a parent.
        """
        fitness_scores = [self.evaluate(individual)['fitness_score'] for individual in self.population]
        total_fitness = sum(fitness_scores)

        if total_fitness == 0:
            return random.choice(self.population)  # Random selection if all fitness is 0

        probabilities = [score / total_fitness for score in fitness_scores]
        return random.choices(list(self.population), weights=probabilities, k=1)[0]

    # Rank-Based Selection
    def rank_based_selection(self):
        """
        Select a parent using rank-based selection.
        Args:
            population (list): List of individuals.
            evaluate_func (callable): Function to compute fitness for an individual.
        Returns:
            Individual selected as a parent.
        """
        sorted_population = sorted(list(self.population), key=lambda x: self.evaluate(x)['fitness_score'], reverse=True)
        ranks = range(1, len(sorted_population) + 1)  # Assign ranks
        total_rank = sum(ranks)
        probabilities = [rank / total_rank for rank in ranks]
        return random.choices(sorted_population, weights=probabilities, k=1)[0]

    # Main Selection Function
    def select_parents(self):
        """
        Select two parents using one of the three methods: tournament, roulette, or rank-based.
        Args:
            population (list): List of individuals.
            evaluate_func (callable): Function to compute fitness for an individual.
        Returns:
            tuple: Two parent individuals selected.
        """
        selection_methods = [self.tournament_selection, self.roulette_wheel_selection, self.rank_based_selection]
        selected_method = random.choices(selection_methods,[0.3, 0.3, 0.4], k=1)[0]  # Randomly select a method

        parent1 = selected_method()
        parent2 = selected_method()

        return parent1, parent2

    def crossover_basic(self, parent1, parent2):
        N = self.grid_size
        total_cells = N * N
        child = []
        for i in range(total_cells):
            if i % 2 == 0:
                child.append(parent1[i])
            else:
                child.append(parent2[i])

        return tuple(child)

    def crossover_simple(self, parent1, parent2):
        N = self.grid_size
        total_cells = N * N

        if len(parent1) != total_cells or len(parent2) != total_cells:
            logging.error(f"""Parent configurations must be {total_cells}, but got sizes: {
                          len(parent1)} and {len(parent2)}""")
            raise ValueError(f"""Parent configurations must be {
                             total_cells}, but got sizes: {len(parent1)} and {len(parent2)}""")

        blocks_parent1 = [
            parent1[i * N: (i + 1) * N] for i in range(N)]
        blocks_parent2 = [
            parent2[i * N: (i + 1) * N] for i in range(N)]

        child_blocks = []
        for i in range(N):
            if i % 2 == 0:
                child_blocks.extend(blocks_parent2[i])
            else:
                child_blocks.extend(blocks_parent1[i])

        if len(child_blocks) != total_cells:
            logging.debug(f"""Child size mismatch, expected {
                          total_cells}, got {len(child_blocks)}""")
            child_blocks = child_blocks + [0] * \
                (total_cells - len(child_blocks))

        return tuple(child_blocks)

    def crossover_complex(self, parent1, parent2):
        """
        Create a child configuration by combining blocks from two parent configurations.

        Crossover Process:
            - Divide each parent's configuration into blocks of size `block_size`.
            - Select blocks from each parent based on the ratio of living cells in each block.
            - Combine selected blocks to form a new child configuration.
            - If a block is not chosen from either parent, randomly select one parent for that block.

        Args:
            parent1 (tuple[int]): A flattened NxN configuration (first parent).
            parent2 (tuple[int]): A flattened NxN configuration (second parent).

        Returns:
            tuple[int]: A new child configuration created by combining blocks from both parents.
        """
        N = self.grid_size
        total_cells = N*N
        reminder = N % 2

        if len(parent1) != total_cells or len(parent2) != total_cells:
            logging.info(f"""Parent configurations must be {total_cells}, but got sizes: {
                         len(parent1)} and {len(parent2)}""")
            raise ValueError(f"""Parent configurations must be {
                             total_cells}, but got sizes: {len(parent1)} and {len(parent2)}""")

        block_size = N
        blocks_parent1 = [
            parent1[i*block_size:(i+1)*block_size] for i in range(N)]
        blocks_parent2 = [
            parent2[i*block_size:(i+1)*block_size] for i in range(N)]

        block_alive_counts_parent1 = [sum(block) for block in blocks_parent1]
        block_alive_counts_parent2 = [sum(block) for block in blocks_parent2]
        max_alive_cells_parent1 = sum(block_alive_counts_parent1)
        max_alive_cells_parent2 = sum(block_alive_counts_parent2)

        # Probability assignment
        if max_alive_cells_parent1 > 0:
            probabilities_parent1 = [(alive_count / max_alive_cells_parent1) if alive_count > 0 else (1/total_cells)
                                     for alive_count in block_alive_counts_parent1]
        else:
            probabilities_parent1 = [1/total_cells]*N

        if max_alive_cells_parent2 > 0:
            probabilities_parent2 = [(alive_count / max_alive_cells_parent2) if alive_count > 0 else (1/total_cells)
                                     for alive_count in block_alive_counts_parent2]
        else:
            probabilities_parent2 = [1/total_cells]*N

        selected_blocks_parent1 = random.choices(
            range(N), weights=probabilities_parent1, k=(N//2)+reminder)
        remaining_blocks_parent2 = [i for i in range(
            N) if i not in selected_blocks_parent1]
        selected_blocks_parent2 = random.choices(
            remaining_blocks_parent2,
            weights=[probabilities_parent2[i]
                     for i in remaining_blocks_parent2],
            k=N//2
        )

        child_blocks = []
        for i in range(N):
            if i in selected_blocks_parent1:
                child_blocks.extend(blocks_parent1[i])
            elif i in selected_blocks_parent2:
                child_blocks.extend(blocks_parent2[i])
            else:
                # If not chosen from either, pick randomly
                selected_parent = random.choices(
                    [1, 2], weights=[0.5, 0.5], k=1)[0]
                if selected_parent == 1:
                    child_blocks.extend(blocks_parent1[i])
                else:
                    child_blocks.extend(blocks_parent2[i])

        # Fix length if needed
        if len(child_blocks) != total_cells:
            logging.info(f"""Child size mismatch, expected {
                         total_cells}, got {len(child_blocks)}""")
            child_blocks = child_blocks + [0]*(total_cells - len(child_blocks))
        return tuple(child_blocks)

    def crossover(self, parent1, parent2):
        crossover_methods = [self.crossover_basic, self.crossover_simple, self.crossover_complex]
        selected_crossover_method = random.choices(crossover_methods, [0.3, 0.3, 0.4], k=1)[0]
        return selected_crossover_method(parent1,parent2)


    def enrich_population_with_variety(self, clusters_type_amount, scatter_type_amount, basic_patterns_type_amount):
        """
        Initialize the population with equal parts of clusters, scattered cells, and simple random patterns.
        The number of clusters is dynamically adjusted based on the grid size.

        Args:
            initial_live_cells (int): Total number of live cells to distribute in each configuration.

        Returns:
            list[tuple[int]]: A diverse initial population.
        """

        total_cells = self.grid_size * self.grid_size
        initial_live_cells = total_cells // 3

        # Adjust number of clusters based on grid size
        max_cluster_amount = self.grid_size // 3
        min_clusters_amount = 1
        max_cluster_size = self.grid_size
        min_cluster_size = min(2, self.grid_size)

        max_scattered_cells = (initial_live_cells // 4) * 2
        min_scattered_cells = 1

        max_pattern_cells = (initial_live_cells // 4) * 2
        min_pattern_cells = 1

        # Generate Cluster Configurations
        for _ in range(clusters_type_amount):
            configuration = [0] * total_cells
            num_clusters = random.randint(
                min_clusters_amount, max_cluster_amount)
            cluster_size = random.randint(min_cluster_size, max_cluster_size)

            for _ in range(num_clusters):
                center_row = random.randint(0, self.grid_size - 1)
                center_col = random.randint(0, self.grid_size - 1)
                for _ in range(cluster_size):
                    offset_row = random.randint(-1, 1)
                    offset_col = random.randint(-1, 1)
                    row = (center_row + offset_row) % self.grid_size
                    col = (center_col + offset_col) % self.grid_size
                    index = row * self.grid_size + col
                    configuration[index] = 1

            self.population.add(tuple(configuration))

        # Generate Scattered Configurations
        for _ in range(scatter_type_amount):
            configuration = [0] * total_cells
            scattered_cells = random.randint(
                min_scattered_cells, max_scattered_cells)
            scattered_indices = random.sample(
                range(total_cells), scattered_cells)
            for index in scattered_indices:
                configuration[index] = 1

            self.population.add(tuple(configuration))

        # Generate Simple Patterns Configuration
        for _ in range(basic_patterns_type_amount):
            configuration = [0] * total_cells
            pattern_cells = random.randint(
                min_pattern_cells, max_pattern_cells)
            start_row = random.randint(0, self.grid_size - 3)
            start_col = random.randint(0, self.grid_size - 3)

            for i in range(self.grid_size):
                for j in range(self.grid_size):
                    if random.uniform(0, 1) < 0.5:  #
                        row = (start_row + i) % self.grid_size
                        col = (start_col + j) % self.grid_size
                        index = row * self.grid_size + col
                        configuration[index] = 1

            current_live_cells = sum(configuration)
            if current_live_cells < pattern_cells:
                additional_cells = random.sample([i for i in range(total_cells) if configuration[i] == 0],
                                                 pattern_cells - current_live_cells)
                for index in additional_cells:
                    configuration[index] = 1

            self.population.add(tuple(configuration))

    def initialize(self):
        """
        Initialize the population with random configurations and evaluate their fitness.

        Initialization Process:
            - Create `population_size` random configurations.
            - Evaluate the fitness of each configuration using the `evaluate` method.
            - Calculate and store initial statistics (average fitness, lifespan, etc.) for generation 0.

        Returns:
            None: Updates the `population` attribute and initializes the first generation's statistics.
        """

        uniform_amount = self.population_size // 3
        rem_amount = self.population_size % 3
        self.enrich_population_with_variety(clusters_type_amount=uniform_amount+rem_amount,
                                            scatter_type_amount=uniform_amount, basic_patterns_type_amount=uniform_amount)
        self.initial_population = list(self.population)
        self.compute_generation(generation=0)

    def adjust_mutation_rate(self, generation):
        """
        Dynamically adjust the mutation rate based on changes in average fitness between generations.

        Purpose:
            - Increase mutation rate if no improvement in average fitness is observed, 
            to encourage exploration and escape local minima.
            - Reduce mutation rate gently if improvement is observed, promoting stability in the evolution.

        Process:
            - Compare the average fitness of the current generation with the previous generation.
            - If there is no improvement in average fitness for more than 10 generations, the mutation rate is increased.
            - If fitness improves, the mutation rate is decreased, but it is always kept above `mutation_rate_lower_limit`.

        Args:
            generation (int): The current generation index.

        Adjustments:
            - Increase mutation rate: Mutation rate is multiplied by 1.2, but capped at the mutation rate's lower limit.
            - Decrease mutation rate: Mutation rate is multiplied by 0.9, but not reduced below `mutation_rate_lower_limit`.
        """
        improvement_ratio = self.generations_cache[generation-1]['avg_fitness'] / max(
            1, self.generations_cache[generation]['avg_fitness'])
        self.mutation_rate = max(self.mutation_rate_lower_limit, min(
            1, improvement_ratio * self.mutation_rate))

    def check_for_stagnation(self, last_generation):
        """
        Detects stagnation in the evolution process over the last 10 generations.

        If the average fitness scores for the last 10 generations are identical (or nearly so),
        it adjusts the mutation rate to encourage diversity.

        Args:
            last_generation (int): Index of the most recent generation.

        Adjustments:
            - If stagnation is detected, increase mutation rate to explore more configurations.
        """
        # Check only if there are at least 10 generations
        if last_generation < 10:
            return

        # Retrieve average fitness scores for the last 10 generations
        avg_fitness = [
            self.generations_cache[g]['avg_fitness']
            for g in range(last_generation - 10, last_generation)
        ]

        # Calculate the number of unique fitness scores
        unique_fitness_scores = len(set(avg_fitness))
        total_generations = len(avg_fitness)

        # If fitness scores are stagnant (low diversity)
        if unique_fitness_scores == 1:
            logging.warning(f"""Stagnation detected in last {
                            total_generations} generations.""")
            self.mutation_rate = min(
                0.5, self.mutation_rate * 1.5)  # Increase mutation rate

        elif unique_fitness_scores < total_generations / 2:
            # Partial stagnation - gentle increase
            logging.info(
                f"""Partial stagnation detected. Increasing mutation rate slightly.""")
            self.mutation_rate = min(0.5, self.mutation_rate * 1.2)

        # Ensure mutation rate does not fall below the lower limit
        self.mutation_rate = max(
            self.mutation_rate, self.mutation_rate_lower_limit)

    def compute_generation(self, generation):

        print(f"""Computing Generation {generation+1} started.""")
        scores = []
        lifespans = []
        alive_growth_rates = []
        max_alive_cells_count = []
        stableness = []
        initial_living_cells_count = []

        for configuration in self.population:
            self.evaluate(configuration)
            scores.append(
                self.configuration_cache[configuration]['fitness_score'])
            lifespans.append(
                self.configuration_cache[configuration]['lifespan'])
            alive_growth_rates.append(
                self.configuration_cache[configuration]['alive_growth'])
            max_alive_cells_count.append(
                self.configuration_cache[configuration]['max_alive_cells_count'])
            stableness.append(
                self.configuration_cache[configuration]['stableness'])
            initial_living_cells_count.append(
                self.configuration_cache[configuration]['initial_living_cells_count'])

        self.mutation_rate_history.append(self.mutation_rate)
        self.calc_statistics(generation=generation,
                             scores=scores,
                             lifespans=lifespans,
                             alive_growth_rates=alive_growth_rates,
                             max_alive_cells_count=max_alive_cells_count,
                             stableness=stableness,
                             initial_living_cells_count=initial_living_cells_count

                             )

    def run(self):
        """
        Execute the genetic algorithm over the specified number of generations.

        Process:
            1. Initialize the population with random configurations.
            2. For each generation:
                - Generate a new population using `populate`.
                - Evaluate the fitness of all configurations.
                - Record statistics for the current generation.
                - Adjust the mutation rate dynamically based on fitness trends.
                - Check for stagnation and adjust parameters if necessary.
            3. At the end, select the top 5 configurations based on fitness and store their histories.

        Returns:
            tuple:
                - List of top 10 configurations with the highest fitness.
                - List of dictionaries containing detailed metrics for each top configuration.
        """
        self.initialize()
        for generation in range(1, self.generations):
            self.populate()
            self.compute_generation(generation=generation)
            self.adjust_mutation_rate(generation)
            self.check_for_stagnation(generation)

    def calc_statistics(self, generation, scores, lifespans, alive_growth_rates, stableness, max_alive_cells_count, initial_living_cells_count):
        """
        Record the average and standard deviation of each metric for the population at this generation.

        Args:
            generation (int): Which generation we're recording.
            scores (list[float]): Fitness values of all individuals in the population.
            lifespans (list[int]): Lifespan (unique states) for each individual.
            alive_growth_rates (list[float]): alive_growth metric for each individual.
            stableness (list[float]): how stable or unstable each individual ended up.
            max_alive_cells_count (list[int]): maximum number of living cells encountered for each.
        """
        scores = np.array(scores)
        lifespans = np.array(lifespans)
        alive_growth_rates = np.array(alive_growth_rates)
        stableness = np.array(stableness)
        max_alive_cells_count = np.array(max_alive_cells_count)

        self.generations_cache[generation]['avg_fitness'] = np.mean(scores)
        self.generations_cache[generation]['avg_lifespan'] = np.mean(lifespans)
        self.generations_cache[generation]['avg_alive_growth_rate'] = np.mean(
            alive_growth_rates)
        self.generations_cache[generation]['avg_max_alive_cells_count'] = np.mean(
            max_alive_cells_count)
        self.generations_cache[generation]['avg_stableness'] = np.mean(
            stableness)
        self.generations_cache[generation]['avg_initial_living_cells_count'] = np.mean(
            initial_living_cells_count)

        self.generations_cache[generation]['std_fitness'] = np.std(scores)
        self.generations_cache[generation]['std_lifespan'] = np.std(lifespans)
        self.generations_cache[generation]['std_alive_growth_rate'] = np.std(
            alive_growth_rates)
        self.generations_cache[generation]['std_max_alive_cells_count'] = np.std(
            max_alive_cells_count)
        self.generations_cache[generation]['std_initial_living_cells_count'] = np.std(
            initial_living_cells_count)

    def get_experiment_results(self):
        # Final selection of best configurations
        fitness_scores = [(config, self.configuration_cache[config]['fitness_score'])
                          for config in self.population]

        fitness_scores_initial_population = [(config, self.configuration_cache[config]['fitness_score'])
                                             for config in self.initial_population]

        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        fitness_scores_initial_population.sort(
            key=lambda x: x[1], reverse=True)

        top_ten_configs = fitness_scores[:min(10, len(fitness_scores))]

        results = []

        # Store their histories for later viewing
        for config, _ in top_ten_configs:

            # logging.info("Top Configuration:")
            # logging.info(f"  Configuration: {config}")
            # logging.info(f"""Fitness Score: {
            #              self.configuration_cache[config]['fitness_score']}""")
            # logging.info(f"""Lifespan: {
            #              self.configuration_cache[config]['lifespan']}""")
            # logging.info(f"""Total Alive Cells: {
            #              self.configuration_cache[config]['max_alive_cells_count']}""")
            # logging.info(f"""Alive Growth: {
            #              self.configuration_cache[config]['alive_growth']}""")
            # logging.info(f"""Initial Configuration Living Cells Count: {
            #              self.configuration_cache[config]['initial_living_cells_count']}""")
            params_dict = {
                'fitness_score': self.configuration_cache[config]['fitness_score'],
                'lifespan': self.configuration_cache[config]['lifespan'],
                'max_alive_cells_count': self.configuration_cache[config]['max_alive_cells_count'],
                'alive_growth': self.configuration_cache[config]['alive_growth'],
                'stableness': self.configuration_cache[config]['stableness'],
                'initial_living_cells_count': self.configuration_cache[config]['initial_living_cells_count'],
                'history': list(self.configuration_cache[config]['history']),
                'config': config,
                'is_first_generation': False

            }
            results.append(params_dict)

        for config, _ in fitness_scores_initial_population:

            # logging.info("Top Configuration:")
            # logging.info(f"  Configuration: {config}")
            # logging.info(f"""Fitness Score: {
            #              self.configuration_cache[config]['fitness_score']}""")
            # logging.info(f"""Lifespan: {
            #              self.configuration_cache[config]['lifespan']}""")
            # logging.info(f"""Total Alive Cells: {
            #              self.configuration_cache[config]['max_alive_cells_count']}""")
            # logging.info(f"""Alive Growth: {
            #              self.configuration_cache[config]['alive_growth']}""")
            # logging.info(f"""Initial Configuration Living Cells Count: {
            #              self.configuration_cache[config]['initial_living_cells_count']}""")
            params_dict = {
                'fitness_score': self.configuration_cache[config]['fitness_score'],
                'lifespan': self.configuration_cache[config]['lifespan'],
                'max_alive_cells_count': self.configuration_cache[config]['max_alive_cells_count'],
                'alive_growth': self.configuration_cache[config]['alive_growth'],
                'stableness': self.configuration_cache[config]['stableness'],
                'initial_living_cells_count': self.configuration_cache[config]['initial_living_cells_count'],
                'history': list(self.configuration_cache[config]['history']),
                'config': config,
                'is_first_generation': True

            }
            results.append(params_dict)

        return results
