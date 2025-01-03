
import logging
import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")  # Ensure Qt5Agg is available
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from PyQt5.QtWidgets import QPushButton


class InteractiveSimulation:
    """
    InteractiveSimulation Class:
    
    Manages the visualization of GeneticAlgorithm results across three UI windows:
        - Grid Window: Displays the NxN Game of Life grid.
        - Stats Window: Shows various metrics including fitness, lifespan, growth rate, alive cells, and diversity.
        - Run Parameters Window: Displays the parameters used in the GA run.
    """

    def __init__(
        self,
        configurations,
        grid_size,
        generations_statistics,
        mutation_rate_history,
        diversity_history,  # New metric
        initial_configurations_start_index,
        run_params=None
    ):
        """
        Initialize the InteractiveSimulation with necessary data.

        Args:
            configurations (list[tuple[int]]): Configurations to visualize.
            grid_size (int): Size of the NxN grid.
            generations_statistics (dict): Fitness and other metrics per generation.
            mutation_rate_history (list[float]): History of mutation rates.
            diversity_history (list[float]): History of diversity metrics.
            initial_configurations_start_index (int): Index to differentiate initial configurations.
            run_params (dict, optional): Parameters used in the GA run.
        """
        logging.info("""Initializing InteractiveSimulation with THREE windows.""")
        self.configurations = configurations
        self.grid_size = grid_size
        self.generations_statistics = generations_statistics
        self.mutation_rate_history = mutation_rate_history
        self.diversity_history = diversity_history  # New metric
        self.initial_configurations_start_index = initial_configurations_start_index
        self.run_params = run_params or {}
        # Navigation state
        self.current_config_index = 0
        self.current_generation = 0

        # Create the separate "Grid Window"
        self.grid_fig = plt.figure(figsize=(5, 5))
        self.grid_ax = self.grid_fig.add_subplot(111)
        self.grid_ax.set_title("""Grid Window""")
        # If user closes the grid window => close everything
        self.grid_fig.canvas.mpl_connect("close_event", self.on_close)

        # Create the separate "Run Parameters Window"
        self.run_params_fig = plt.figure(figsize=(5, 5))
        gs_run_params = GridSpec(1, 1, figure=self.run_params_fig)
        self.run_params_plot = self.run_params_fig.add_subplot(gs_run_params[0, 0])
        self.run_params_plot.set_title("""Run Parameters Window""")
        # If user closes the run parameters window => close everything
        self.run_params_fig.canvas.mpl_connect("close_event", self.on_close)

        # Create the "Stats Window"
        self.stats_fig = plt.figure(figsize=(18, 8))
        gs = GridSpec(3, 3, figure=self.stats_fig)

        # Connect close event => kill entire app if user closes stats
        self.stats_fig.canvas.mpl_connect("close_event", self.on_close)

        # Create subplots in row 0
        self.standardized_initial_size_plot = self.stats_fig.add_subplot(gs[0, 0])
        self.standardized_lifespan_plot = self.stats_fig.add_subplot(gs[0, 1])
        self.standardized_growth_rate_plot = self.stats_fig.add_subplot(gs[0, 2])

        # Create subplots in row 1
        self.standardized_alive_cells_plot = self.stats_fig.add_subplot(gs[1, 0])
        self.mutation_rate_plot = self.stats_fig.add_subplot(gs[1, 1])
        self.standardized_fitness_plot = self.stats_fig.add_subplot(gs[1, 2])

        # Create subplot in row 2 for diversity
        self.diversity_plot = self.stats_fig.add_subplot(gs[2, :])
        self.diversity_plot.set_title("""Diversity Over Generations""")

        # Also connect arrow-key events in the grid figure
        self.grid_fig.canvas.mpl_connect('key_press_event', self.on_key)

        # Add buttons to Stats Window
        self.add_focus_button_to_toolbar(
            figure=self.stats_fig,
            button_text="""Focus Grid Window""",
            on_click=self.bring_grid_to_front
        )

        self.add_focus_button_to_toolbar(
            figure=self.stats_fig,
            button_text="""Focus Run Parameters Window""",
            on_click=self.bring_run_parameters_to_front
        )

        # Add buttons to Grid Window
        self.add_focus_button_to_toolbar(
            figure=self.grid_fig,
            button_text="""Focus Stats Window""",
            on_click=self.bring_stats_to_front
        )

        self.add_focus_button_to_toolbar(
            figure=self.grid_fig,
            button_text="""Focus Run Parameters Window""",
            on_click=self.bring_run_parameters_to_front
        )

        # Add buttons to Run Parameters Window
        self.add_focus_button_to_toolbar(
            figure=self.run_params_fig,
            button_text="""Focus Stats Window""",
            on_click=self.bring_stats_to_front
        )

        self.add_focus_button_to_toolbar(
            figure=self.run_params_fig,
            button_text="""Focus Grid Window""",
            on_click=self.bring_grid_to_front
        )

        self.update_grid()
        self.render_statistics()
        self.update_run_params_window()

    def on_close(self, event):
        """
        Called when ANY window is closed. Closes all plots and exits.
        """
        logging.info("""A window was closed. Exiting program.""")
        plt.close('all')
        exit()

    def add_focus_button_to_toolbar(self, figure, button_text, on_click):
        """
        Insert a custom button in the given figure's Qt toolbar.

        Args:
            figure (matplotlib.figure.Figure): The figure to add the button to.
            button_text (str): The text displayed on the button.
            on_click (callable): The function to call when the button is clicked.
        """
        try:
            toolbar = figure.canvas.manager.toolbar
            button = QPushButton(button_text)
            button.setStyleSheet(
                """
                QPushButton {
                    margin: 8px;        /* space around the button in the toolbar */
                    padding: 6px 10px;  /* inside spacing around the text */
                    font-size: 12px;    /* bigger font */
                    font-weight: bold;  /* make it stand out */
                }
                """
            )
            toolbar.addWidget(button)
            button.clicked.connect(on_click)
        except Exception as e:
            logging.warning(f"""Could not add custom button '{button_text}' to toolbar: {e}""")

    def bring_grid_to_front(self, e=None):
        """
        Attempt to bring the 'Grid Window' to the front (Qt-based).
        Some OS/WM can block focus-stealing, so this may not always succeed.
        """
        try:
            self.grid_fig.canvas.manager.window.activateWindow()
            self.grid_fig.canvas.manager.window.raise_()
            self.grid_fig.canvas.manager.window.showMaximized()
        except Exception as e:
            logging.warning(f"""Could not bring the Grid window to the front: {e}""")

    def bring_stats_to_front(self, e=None):
        """
        Attempt to bring the 'Stats Window' to the front (Qt-based).
        Some OS/WM can block focus-stealing, so this may not always succeed.
        """
        try:
            self.stats_fig.canvas.manager.window.showNormal()
            self.stats_fig.canvas.manager.window.activateWindow()
            self.stats_fig.canvas.manager.window.raise_()
        except Exception as e:
            logging.warning(f"""Could not bring the Stats window to the front: {e}""")

    def bring_run_parameters_to_front(self, e=None):
        """
        Attempt to bring the 'Run Parameters Window' to the front (Qt-based).
        Some OS/WM can block focus-stealing, so this may not always succeed.
        """
        try:
            self.run_params_fig.canvas.manager.window.showNormal()
            self.run_params_fig.canvas.manager.window.activateWindow()
            self.run_params_fig.canvas.manager.window.raise_()
        except Exception as e:
            logging.warning(f"""Could not bring the Run Parameters window to the front: {e}""")

    def on_key(self, event):
        """
        Keyboard navigation for the Grid Window:
            UP -> next configuration
            DOWN -> previous configuration
            RIGHT -> next generation
            LEFT -> previous generation
        """
        if event.key == 'up':
            self.next_configuration()
        elif event.key == 'down':
            self.previous_configuration()
        elif event.key == 'right':
            self.next_generation()
        elif event.key == 'left':
            self.previous_generation()

    def next_configuration(self):
        """Move to the next configuration."""
        self.current_config_index = (
            self.current_config_index + 1) % len(self.configurations)
        self.current_generation = 0
        self.update_grid()

    def previous_configuration(self):
        """Move to the previous configuration."""
        self.current_config_index = (
            self.current_config_index - 1) % len(self.configurations)
        self.current_generation = 0
        self.update_grid()

    def next_generation(self):
        """
        Advance one generation in the current config's history, if available.
        """
        hist_len = len(
            self.configurations[self.current_config_index]['history'])
        if self.current_generation + 1 < hist_len:
            self.current_generation += 1
            self.update_grid()

    def previous_generation(self):
        """
        Go back one generation in the current config's history, if possible.
        """
        if self.current_generation > 0:
            self.current_generation -= 1
            self.update_grid()

    def update_grid(self):
        """
        Redraw the NxN grid in the "Grid Window" for the current config/generation.
        """
        param_dict = self.configurations[self.current_config_index]

        fitness_score = param_dict.get('fitness_score', 0)
        normalized_fitness_score = param_dict.get('normalized_fitness_score', 0)
        lifespan = param_dict.get('lifespan', 0)
        max_alive = param_dict.get('max_alive_cells_count', 0)
        growth = param_dict.get('alive_growth', 1.0)
        stableness = param_dict.get('stableness', 0.0)
        initial_living_cells_count = param_dict.get('initial_living_cells_count', 0.0)
        is_first_generation = param_dict.get('is_first_generation')

        title_txt = (f"""Config From First Generation #{self.current_config_index - self.initial_configurations_start_index + 1}""" 
                     if is_first_generation 
                     else f"""Top Config #{self.current_config_index + 1}""")

        grid_2d = [
            self.configurations[self.current_config_index]['history'][self.current_generation][
                i * self.grid_size:(i+1) * self.grid_size
            ]
            for i in range(self.grid_size)
        ]
        self.grid_ax.clear()
        self.grid_ax.imshow(grid_2d, cmap="binary")
        self.grid_ax.set_title(
            f"""{title_txt} Day (Of Game Of Life) {self.current_generation}"""
        )
        self.grid_ax.set_ylabel("""ARROWS: UP/DOWN=configs, LEFT/RIGHT=gens""")

        text_str = (
            f"""fitness score = {fitness_score:.2f} | normalized fitness score = {normalized_fitness_score:.4f}\n"""
            f"""lifespan = {lifespan} | initial_size = {initial_living_cells_count} | """
            f"""max_alive = {max_alive} | growth = {growth:.2f} | stableness = {stableness:.2f}"""
        )

        self.grid_ax.set_xlabel(text_str)
        self.grid_fig.canvas.draw_idle()

    def render_statistics(self):
        """
        Fill in each subplot with the relevant data, including the run_params in self.run_params_plot.
        Also includes the diversity metric.
        """
        gens = sorted(self.generations_statistics.keys())

        # ---------------- Fitness ----------------
        avg_fitness = [self.generations_statistics[g]['avg_fitness'] for g in gens]
        std_fitness = [self.generations_statistics[g]['std_fitness'] for g in gens]
        self.standardized_fitness_plot.clear()
        self.standardized_fitness_plot.plot(
            gens, avg_fitness, label="""Standardized Fitness""", color='blue')
        self.standardized_fitness_plot.fill_between(
            gens,
            np.subtract(avg_fitness, std_fitness),
            np.add(avg_fitness, std_fitness),
            color='blue', alpha=0.2, label="""Std Dev"""
        )
        self.standardized_fitness_plot.set_title("""Standardized Fitness""")
        self.standardized_fitness_plot.legend()

        # ---------------- Initial Size (initial living cells count) ----------------
        avg_initial_size = [self.generations_statistics[g]['avg_initial_living_cells_count']
                            for g in gens]
        std_initial_size = [self.generations_statistics[g]['std_initial_living_cells_count']
                            for g in gens]

        self.standardized_initial_size_plot.clear()
        self.standardized_initial_size_plot.plot(
            gens, avg_initial_size, label="""Standardized Initial Size""", color='cyan')
        self.standardized_initial_size_plot.fill_between(
            gens,
            np.subtract(avg_initial_size, std_initial_size),
            np.add(avg_initial_size, std_initial_size),
            color='cyan', alpha=0.2, label="""Std Dev"""
        )
        self.standardized_initial_size_plot.set_title("""Standardized Initial Size""")

        # ---------------- Lifespan ----------------
        avg_lifespan = [self.generations_statistics[g]['avg_lifespan']
                        for g in gens]
        std_lifespan = [self.generations_statistics[g]['std_lifespan']
                        for g in gens]
        self.standardized_lifespan_plot.clear()
        self.standardized_lifespan_plot.plot(
            gens, avg_lifespan, label="""Standardized Lifespan""", color='green')

        self.standardized_lifespan_plot.fill_between(
            gens,
            np.subtract(avg_lifespan, std_lifespan),
            np.add(avg_lifespan, std_lifespan),
            color='green', alpha=0.2, label="""Std Dev"""
        )
        self.standardized_lifespan_plot.set_title("""Standardized Lifespan""")

        # ---------------- Growth Rate ----------------
        avg_growth = [self.generations_statistics[g]['avg_alive_growth_rate'] for g in gens]
        std_growth = [self.generations_statistics[g]['std_alive_growth_rate'] for g in gens]
        self.standardized_growth_rate_plot.clear()
        self.standardized_growth_rate_plot.plot(
            gens, avg_growth, label="""Std Growth""", color='red')
        self.standardized_growth_rate_plot.fill_between(
            gens,
            np.subtract(avg_growth, std_growth),
            np.add(avg_growth, std_growth),
            color='red', alpha=0.2, label="""Std Dev"""
        )
        self.standardized_growth_rate_plot.set_title("""Standardized Growth Rate""")

        # ---------------- Alive Cells ----------------
        avg_alive_cells = [self.generations_statistics[g]['avg_max_alive_cells_count'] for g in gens]
        std_alive_cells = [self.generations_statistics[g]['std_max_alive_cells_count'] for g in gens]
        self.standardized_alive_cells_plot.clear()
        self.standardized_alive_cells_plot.plot(
            gens, avg_alive_cells, label="""Std Alive""", color='purple')
        self.standardized_alive_cells_plot.fill_between(
            gens,
            np.subtract(avg_alive_cells, std_alive_cells),
            np.add(avg_alive_cells, std_alive_cells),
            color='purple', alpha=0.2, label="""Std Dev"""
        )
        self.standardized_alive_cells_plot.set_title("""Standardized Alive Cells""")

        # ---------------- Mutation Rate ----------------
        self.mutation_rate_plot.clear()
        self.mutation_rate_plot.plot(
            gens, self.mutation_rate_history, label="""Mutation Rate""", color='orange')
        self.mutation_rate_plot.set_title("""Mutation Rate""")
        self.mutation_rate_plot.legend()

        # ---------------- Diversity ----------------
        self.diversity_plot.clear()
        self.diversity_plot.plot(
            gens, self.diversity_history, label="""Diversity""", color='magenta')
        self.diversity_plot.set_title("""Genetic Diversity Over Generations""")
        self.diversity_plot.set_xlabel("""Generation""")
        self.diversity_plot.set_ylabel("""Average Hamming Distance""")
        self.diversity_plot.legend()

        # Optionally adjust spacing:
        self.stats_fig.tight_layout()

    def update_run_params_window(self):
        """
        Update the Run Parameters Window with the parameters used in the GA run.
        """
        # ---------------- Params (text) ----------------
        self.run_params_plot.clear()
        self.run_params_plot.set_title("""Run Parameters""")
        self.run_params_plot.axis("off")

        lines = ["Genetic Algorithm Custom Parameters used in this run:"]
        for k, v in self.run_params.items():
            lines.append(f"""• {k} = {v}""")
        text_str = "\n".join(lines)

        self.run_params_plot.text(
            0.0, 1.0,
            text_str,
            transform=self.run_params_plot.transAxes,
            fontsize=10,
            va='top'
        )

        # Optionally adjust spacing:
        self.run_params_fig.tight_layout()

    def run(self):
        """
        Show all three windows. plt.show() blocks until user closes them.
        """
        logging.info("""Running interactive simulation with separate Grid, Stats, and Run Parameters windows.""")
        plt.show()