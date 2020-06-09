from __future__ import annotations

from copy import copy
from typing import Callable, Optional, Tuple

import numpy as np

from src.core.boundary_value_problem import BoundaryValueProblem
from src.core.initial_condition import InitialCondition

TemporalDomainInterval = Tuple[float, float]


class InitialValueProblem:
    """
    A representation of an initial value problem around a boundary value
    problem.
    """

    def __init__(
            self,
            bvp: BoundaryValueProblem,
            t_interval: TemporalDomainInterval,
            initial_condition: InitialCondition,
            exact_y: Optional[Callable[
                [InitialValueProblem, float, np.ndarray], np.ndarray]] = None):
        """
        :param bvp: the boundary value problem instance
        :param t_interval: the bounds of the time domain of the initial value
        problem
        :param initial_condition: the initial condition of the problem
        :param exact_y: the function returning the exact solution to the
        initial value problem at time step t and point x. If it is None, the
        problem is assumed to have no analytical solution.
        """
        assert bvp is not None
        self._bvp = bvp

        assert len(t_interval) == 2
        assert t_interval[0] <= t_interval[1]
        self._t_interval = copy(t_interval)

        assert initial_condition is not None
        self._initial_condition = initial_condition

        self._exact_y = exact_y

    def boundary_value_problem(self) -> BoundaryValueProblem:
        """
        Returns the boundary value problem instance.
        """
        return self._bvp

    def t_interval(self) -> TemporalDomainInterval:
        """
        Returns the bounds of the temporal domain of the differential equation.
        """
        return copy(self._t_interval)

    def initial_condition(self) -> InitialCondition:
        """
        Returns the initial condition of the IVP.
        """
        return self._initial_condition

    def has_exact_solution(self) -> bool:
        """
        Returns whether the differential equation has an analytic solution
        """
        return self._exact_y is not None

    def exact_y(
            self,
            t: float,
            x: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        """
        Returns the exact value of y(t, x).

        :param t: the point in the temporal domain
        :param x: the point in the non-temporal domain. If the differential
        equation is an ODE, it is None.
        :return: the value of y(t, x) or y(t) if it is an ODE.
        """
        return self._exact_y(self, t, x)
