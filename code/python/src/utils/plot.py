import math
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from matplotlib.animation import FuncAnimation
from matplotlib.colors import Colormap
from mpl_toolkits.mplot3d import Axes3D

from src.core.differential_equation import NBodyGravitationalEquation, \
    WaveEquation, DiffusionEquation, NavierStokesEquation
from src.core.solution import Solution


def plot_y_against_t(
        solution: Solution,
        file_name: str):
    """
    Plots the value of y against t.

    :param solution: a solution to an IVP
    :param file_name: the name of the file to save the plot to
    """
    diff_eq = solution.boundary_value_problem.differential_equation
    assert not diff_eq.x_dimension

    t = solution.t_coordinates
    y = solution.discrete_y(solution.vertex_oriented)

    plt.xlabel('t')
    plt.ylabel('y')

    if diff_eq.y_dimension == 1:
        plt.plot(t, y[..., 0])
    else:
        for i in range(y.shape[1]):
            plt.plot(t, y[:, i])

    plt.savefig(f'{file_name}.pdf')
    plt.clf()


def plot_phase_space(solution: Solution, file_name: str):
    """
    Creates a phase-space plot.

    :param solution: a solution to an IVP
    :param file_name: the name of the file to save the plot to
    """
    y = solution.discrete_y(solution.vertex_oriented)

    assert len(y.shape) == 2
    assert 2 <= y.shape[1] <= 3

    if y.shape[1] == 2:
        plt.xlabel('y 0')
        plt.ylabel('y 1')

        plt.plot(y[:, 0], y[:, 1])

        plt.axis('scaled')
    elif y.shape[1] == 3:
        fig = plt.figure()
        ax = Axes3D(fig)
        ax.set_xlabel('y 0')
        ax.set_ylabel('y 1')
        ax.set_zlabel('y 2')

        ax.plot3D(y[:, 0], y[:, 1], y[:, 2])

    plt.savefig(f'{file_name}.pdf')
    plt.clf()


def plot_n_body_simulation(
        solution: Solution,
        frames_between_updates: int,
        interval: int,
        smallest_marker_size: int,
        file_name: str):
    """
    Plots an n-body gravitational simulation in the form of a GIF.

    :param solution: the solution of an n-body gravitational IVP
    :param frames_between_updates: the number of frames to skip in between
    plotted frames
    :param interval: the number of milliseconds between each frame of the GIF
    :param smallest_marker_size: the size of the marker representing the
    smallest mass
    :param file_name: the name of the file to save the plot to
    """
    diff_eq: NBodyGravitationalEquation = \
        solution.boundary_value_problem.differential_equation

    assert isinstance(diff_eq, NBodyGravitationalEquation)

    n_obj_by_dims = diff_eq.n_objects * diff_eq.spatial_dimension

    span_scaling_factor = .25

    masses = np.asarray(diff_eq.masses)
    scaled_masses = (smallest_marker_size / np.min(masses)) * masses
    radii = np.power(3. * scaled_masses / (4 * np.pi), 1. / 3.)
    marker_sizes = np.power(radii, 2) * np.pi

    colors = cm.rainbow(np.linspace(0., 1., diff_eq.n_objects))

    y = solution.discrete_y(solution.vertex_oriented)

    if diff_eq.spatial_dimension == 2:
        fig, ax = plt.subplots()
        ax.set_xlabel('x')
        ax.set_ylabel('y')

        x_coordinates = y[:, :n_obj_by_dims:2]
        y_coordinates = y[:, 1:n_obj_by_dims:2]
        coordinates = np.stack((x_coordinates, y_coordinates), axis=2)

        x_max = x_coordinates.max()
        x_min = x_coordinates.min()
        y_max = y_coordinates.max()
        y_min = y_coordinates.min()

        x_span = x_max - x_min
        y_span = y_max - y_min

        x_max += span_scaling_factor * x_span
        x_min -= span_scaling_factor * x_span
        y_max += span_scaling_factor * y_span
        y_min -= span_scaling_factor * y_span

        scatter_plot = ax.scatter(
            x_coordinates[0, :],
            y_coordinates[0, :],
            s=marker_sizes,
            c=colors)

        plt.axis('scaled')

        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)

        def update_plot(time_step: int):
            scatter_plot.set_offsets(coordinates[time_step, ...])
            return scatter_plot, ax
    else:
        fig = plt.figure()
        ax = Axes3D(fig)

        x_label = 'x'
        y_label = 'y'
        z_label = 'z'

        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_zlabel(z_label)

        pane_edge_color = 'k'
        ax.xaxis.pane.set_edgecolor(pane_edge_color)
        ax.yaxis.pane.set_edgecolor(pane_edge_color)
        ax.zaxis.pane.set_edgecolor(pane_edge_color)

        ax.grid(False)

        x_coordinates = y[:, :n_obj_by_dims:3]
        y_coordinates = y[:, 1:n_obj_by_dims:3]
        z_coordinates = y[:, 2:n_obj_by_dims:3]

        x_max = x_coordinates.max()
        x_min = x_coordinates.min()
        y_max = y_coordinates.max()
        y_min = y_coordinates.min()
        z_max = z_coordinates.max()
        z_min = z_coordinates.min()

        x_span = x_max - x_min
        y_span = y_max - y_min
        z_span = z_max - z_min

        x_max += span_scaling_factor * x_span
        x_min -= span_scaling_factor * x_span
        y_max += span_scaling_factor * y_span
        y_min -= span_scaling_factor * y_span
        z_max += span_scaling_factor * z_span
        z_min -= span_scaling_factor * z_span

        scatter_plot = ax.scatter(
            x_coordinates[0, :],
            y_coordinates[0, :],
            z_coordinates[0, :],
            s=marker_sizes,
            c=colors,
            depthshade=False)

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_zlim(z_min, z_max)

        def update_plot(time_step: int):
            scatter_plot._offsets3d = (
                x_coordinates[time_step, ...],
                y_coordinates[time_step, ...],
                z_coordinates[time_step, ...]
            )
            return scatter_plot, ax

    animation = FuncAnimation(
        fig,
        update_plot,
        frames=range(0, y.shape[0], frames_between_updates),
        interval=interval)
    animation.save(f'{file_name}.gif', writer='imagemagick')
    plt.clf()


def plot_evolution_of_y(
        solution: Solution,
        y_ind: int,
        frames_between_updates: int,
        interval: int,
        file_name: str,
        three_d: bool = False,
        color_map: Colormap = cm.viridis):
    """
    Plots the solution of an IVP based on a PDE in 1 or 2 spatial dimensions as
    a GIF.

    :param solution: a solution to an IVP based on a PDE in 1 or 2 spatial
    dimensions
    :param y_ind: the component of y to plot (in case y is vector-valued)
    :param frames_between_updates: the number of frames to skip in between
    plotted frames
    :param interval: the number of milliseconds between each frame of the GIF
    :param file_name: the name of the file to save the plot to
    :param three_d: whether a 3D surface plot or a 2D contour plot should be
    used for IVPs based on PDEs in 2 spatial dimensions
    :param color_map: the color map to use for IVPs based on PDEs in 2 spatial
    dimensions
    """
    x_coordinates = solution.x_coordinates(solution.vertex_oriented)
    y = solution.discrete_y(solution.vertex_oriented)[..., y_ind]

    v_min = np.min(y)
    v_max = np.max(y)

    if solution.boundary_value_problem.differential_equation.x_dimension == 1:
        fig, ax = plt.subplots()
        ax.set_xlabel('x')
        ax.set_ylabel('y')

        x = x_coordinates[0]
        line_plot, = ax.plot(x, y[0, ...])

        plt.ylim(v_min, v_max)
        plt.axis('scaled')

        def update_plot(time_step: int):
            line_plot.set_ydata(y[time_step, ...])
            return line_plot, ax
    else:
        x0_label = 'x 0'
        x1_label = 'x 1'

        x_0 = x_coordinates[0]
        x_1 = x_coordinates[1]
        x_0, x_1 = np.meshgrid(x_0, x_1)

        if three_d:
            fig = plt.figure()
            ax = Axes3D(fig)
            y_label = 'y'
            ax.set_xlabel(x0_label)
            ax.set_ylabel(x1_label)
            ax.set_zlabel(y_label)

            plot_args = {
                'rstride': 1,
                'cstride': 1,
                'linewidth': 0,
                'antialiased': False,
                'camp': color_map
            }

            ax.plot_surface(x_0, x_1, y[0, ...].T, **plot_args)
            ax.set_zlim(v_min, v_max)

            def update_plot(time_step: int):
                ax.clear()
                ax.set_xlabel(x0_label)
                ax.set_ylabel(x1_label)
                ax.set_zlabel(y_label)

                _plot = ax.plot_surface(
                    x_0, x_1, y[time_step, ...].T, **plot_args)
                ax.set_zlim(v_min, v_max)
                return _plot,
        else:
            fig, ax = plt.subplots(1, 1)
            ax.contourf(
                x_0,
                x_1,
                y[0, ...].T,
                vmin=v_min,
                vmax=v_max,
                cmap=color_map)
            ax.set_xlabel(x0_label)
            ax.set_ylabel(x1_label)
            plt.axis('scaled')

            mappable = plt.cm.ScalarMappable()
            mappable.set_array(y[0, ...])
            mappable.set_clim(v_min, v_max)
            plt.colorbar(mappable)

            def update_plot(time_step: int):
                return plt.contourf(
                    x_0,
                    x_1,
                    y[time_step, ...].T,
                    vmin=v_min,
                    vmax=v_max,
                    cmap=color_map)

    animation = FuncAnimation(
        fig,
        update_plot,
        frames=range(0, y.shape[0], frames_between_updates),
        interval=interval)
    animation.save(f'{file_name}.gif', writer='imagemagick')
    plt.clf()


def plot_ivp_solution(
        solution: Solution,
        solution_name: str,
        n_images: int = 20,
        interval: int = 100,
        smallest_marker_size: int = 8,
        three_d: Optional[bool] = None,
        color_map: Optional[Colormap] = None):
    """
    Plots the solution of an IVP. The kind of plot generated depends on the
    type of the differential equation the IVP is based on.

    :param solution: a solution to an IVP
    :param solution_name: the name of the solution appended to the name of the
    file the plot is saved to
    :param n_images: the number of frames to generate for the GIF if the IVP is
    based on an n-body problem or a PDE in 2 spatial dimensions
    :param interval: the number of milliseconds between each frame of the GIF
    if the IVP is based on an n-body problem or a PDE in 2 spatial dimensions
    :param smallest_marker_size: the size of the marker representing the
    smallest mass if the IVP is based on an n-body proble
    :param three_d: whether a 3D surface plot or a 2D contour plot should be
    used for IVPs based on PDEs in 2 spatial dimensions
    :param color_map: the color map to use for IVPs based on PDEs in 2 spatial
    dimensions
    """
    diff_eq = solution.boundary_value_problem.differential_equation
    
    if diff_eq.x_dimension:
        if three_d is None:
            three_d = isinstance(diff_eq, (DiffusionEquation, WaveEquation))

        if color_map is None:
            if isinstance(diff_eq, (DiffusionEquation, WaveEquation)):
                color_map = cm.coolwarm
            elif isinstance(diff_eq, NavierStokesEquation):
                color_map = cm.cool
            else:
                color_map = cm.viridis

        for y_ind in range(diff_eq.y_dimension):
            plot_evolution_of_y(
                solution,
                y_ind,
                math.ceil(len(solution.t_coordinates) / float(n_images)),
                interval,
                f'evolution_{solution_name}_{y_ind}',
                three_d,
                color_map)
    else:
        if isinstance(diff_eq, NBodyGravitationalEquation):
            plot_n_body_simulation(
                solution,
                math.ceil(len(solution.t_coordinates) / float(n_images)),
                interval,
                smallest_marker_size,
                f'nbody_{solution_name}')
        else:
            plot_y_against_t(solution, solution_name)

            if 2 <= diff_eq.y_dimension <= 3:
                plot_phase_space(solution, f'phase_space_{solution_name}')
