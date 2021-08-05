from abc import ABC, abstractmethod
from copy import copy
from enum import Enum
from typing import Optional, Sequence, Dict, List
from typing import Tuple

import numpy as np
from sympy import symarray, Expr, Symbol


class Symbols:
    """
    A class containing the symbols for expressing a coordinate system agnostic
    differential equation system with a specified number of unknown variables
    and spatial dimensions.
    """

    def __init__(self, x_dimension: int, y_dimension: int):
        """
        :param x_dimension: the number spatial dimensions
        :param y_dimension: the number of unknown variables
        """
        self._t = Symbol('t')
        self._y = symarray('y', (y_dimension,))

        if x_dimension:
            self._y_gradient = symarray(
                'y-gradient', (y_dimension, x_dimension))
            self._y_hessian = symarray(
                'y-hessian', (y_dimension, x_dimension, x_dimension))
            self._y_divergence = symarray(
                'y-divergence', (y_dimension,) * x_dimension)
            if x_dimension == 2:
                self._y_curl = symarray('y-curl', (y_dimension,) * x_dimension)
            elif x_dimension == 3:
                self._y_curl = symarray(
                    'y-curl', ((y_dimension,) * x_dimension) + (x_dimension,))
            else:
                self._y_curl = None
            self._y_laplacian = symarray('y-laplacian', (y_dimension,))
        else:
            self._y_gradient = None
            self._y_hessian = None
            self._y_divergence = None
            self._y_curl = None
            self._y_laplacian = None

    @property
    def t(self) -> Symbol:
        """
        The temporal position.
        """
        return self._t

    @property
    def y(self) -> np.ndarray:
        """
        An array of symbols denoting the elements of the solution of the
        differential equation.
        """
        return np.copy(self._y)

    @property
    def y_gradient(self) -> Optional[np.ndarray]:
        """
        A 2D array of symbols denoting the first spatial derivatives of the
        solution where the first rank is the element of the solution and the
        second rank is the spatial axis.
        """
        return np.copy(self._y_gradient)

    @property
    def y_hessian(self) -> Optional[np.ndarray]:
        """
        A 3D array of symbols denoting the second spatial derivatives of the
        solution where the first rank is the element of the solution, the
        second rank is the first spatial axis, and the third rank is the second
        spatial axis.
        """
        return np.copy(self._y_hessian)

    @property
    def y_divergence(self) -> Optional[np.ndarray]:
        """
        A multidimensional array of symbols denoting the spatial divergence of
        the corresponding elements of the differential equation's solution.
        """
        return np.copy(self._y_divergence)

    @property
    def y_curl(self) -> Optional[np.ndarray]:
        """
        A multidimensional array of symbols denoting the spatial curl of
        the corresponding elements of the differential equation's solution.

        For two spatial dimensions, this corresponds to a scalar field.
        However, for three spatial dimensions, it corresponds to a vector
        field, therefore an additional axis is appended to this
        multidimensional array to allow for indexing the components of this
        vector field. For differential equations with less than two or more
        than three spatial dimensions, the curl is not defined.
        """
        return np.copy(self._y_curl)

    @property
    def y_laplacian(self) -> Optional[np.ndarray]:
        """
        An array of symbols denoting the spatial Laplacians of the elements of
        the differential equation's solution.
        """
        return np.copy(self._y_laplacian)


class Lhs(Enum):
    """
    An enumeration defining the types of the left hand sides of symbolic
    equations making up systems of differential equations.
    """
    D_Y_OVER_D_T = 0,
    Y = 1,
    Y_LAPLACIAN = 2


class SymbolicEquationSystem:
    """
    A system of symbolic equations for defining differential equations.
    """

    def __init__(
            self,
            rhs: Sequence[Expr],
            lhs_types: Optional[Sequence[Lhs]] = None):
        """
        :param rhs: the right hand side of the symbolic equation system
        :param lhs_types: the types of the left hand side of the symbolic
        equation system
        """
        if len(rhs) < 1:
            raise ValueError

        if lhs_types is None:
            lhs_types = [Lhs.D_Y_OVER_D_T] * len(rhs)

        if len(rhs) != len(lhs_types):
            raise ValueError

        self._rhs = copy(rhs)
        self._lhs_types = copy(lhs_types)

        self._equation_indices_by_type: Dict[Lhs, List[int]] = \
            {lhs_type: [] for lhs_type in Lhs}
        for i, (lhs_type, rhs_element) in enumerate(zip(lhs_types, rhs)):
            self._equation_indices_by_type[lhs_type].append(i)

    @property
    def rhs(self) -> Sequence[Expr]:
        """
        The right hand side of the symbolic equation system.
        """
        return copy(self._rhs)

    @property
    def lhs_types(self) -> Sequence[Lhs]:
        """
        The types of the left hand side of the symbolic equation system.
        """
        return copy(self._lhs_types)

    def equation_indices_by_type(self, lhs_type: Lhs) -> Sequence[int]:
        """
        Returns a sequence of integers denoting the indices of all equations of
        the equation system with the specified type of left hand side.

        :param lhs_type: the type of left hand side
        :return: the sequence of indices
        """
        return copy(self._equation_indices_by_type[lhs_type])


class DifferentialEquation(ABC):
    """
    A representation of a time-dependent differential equation.
    """

    def __init__(self, x_dimension: int, y_dimension: int):
        """
        :param x_dimension: the number spatial dimensions
        :param y_dimension: the number of unknown variables
        """
        if x_dimension < 0:
            raise ValueError
        if y_dimension < 1:
            raise ValueError

        self._x_dimension = x_dimension
        self._y_dimension = y_dimension

        self._symbols = Symbols(x_dimension, y_dimension)

        self._validate_equations()

    @property
    def x_dimension(self) -> int:
        """
        The dimension of the non-temporal domain of the differential equation's
        solution. If the differential equation is an ODE, it is 0.
        """
        return self._x_dimension

    @property
    def y_dimension(self) -> int:
        """
        The dimension of the image of the differential equation's solution. If
        the solution is not vector-valued, its dimension is 1.
        """
        return self._y_dimension

    @property
    def symbols(self) -> Symbols:
        """
        All valid symbols that can be used to define a differential equation of
        this many spatial dimensions and unknown variables.
        """
        return self._symbols

    @property
    @abstractmethod
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        """
        A system of symbolic equations defining the differential equation
        system. Every element of the right hand side of the returned system
        defines the first time derivative, the direct value, or the spatial
        Laplacian of the respective element of the vector-valued solution of
        the differential equation system depending on the type of the left hand
        side of the equation.
        """

    def _validate_equations(self):
        """
        Validates the symbolic equations defining the differential equation.
        """
        equation_system = self.symbolic_equation_system
        if len(equation_system.rhs) != self._y_dimension:
            raise ValueError

        all_symbols = set()
        all_symbols.add(self._symbols.t)
        all_symbols.update(self._symbols.y)

        if self._x_dimension:
            all_symbols.update(self._symbols.y_gradient.flatten())
            all_symbols.update(self._symbols.y_hessian.flatten())
            all_symbols.update(self._symbols.y_divergence.flatten())
            if 2 <= self._x_dimension <= 3:
                all_symbols.update(self._symbols.y_curl.flatten())
            all_symbols.update(self._symbols.y_laplacian)

        for rhs_element in self.symbolic_equation_system.rhs:
            rhs_symbols = rhs_element.free_symbols
            if not rhs_symbols.issubset(all_symbols):
                raise ValueError

        if self.x_dimension:
            if Lhs.D_Y_OVER_D_T not in equation_system.lhs_types:
                raise ValueError
        elif Lhs.Y in equation_system.lhs_types \
                or Lhs.Y_LAPLACIAN in equation_system.lhs_types:
            raise ValueError


class PopulationGrowthEquation(DifferentialEquation):
    """
    A simple ordinary differential equation modelling the growth of a
    population over time.
    """

    def __init__(self, r: float = .01):
        """
        :param r: the population growth rate
        """
        self._r = r
        super(PopulationGrowthEquation, self).__init__(0, 1)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        return SymbolicEquationSystem([self._r * self._symbols.y[0]])


class LotkaVolterraEquation(DifferentialEquation):
    """
    A system of two ordinary differential equations modelling the dynamics of
    populations of preys and predators.
    """

    def __init__(
            self,
            alpha: float = 2.,
            beta: float = .04,
            gamma: float = 1.06,
            delta: float = .02):
        """
        :param alpha: the preys' birthrate
        :param beta: a coefficient of the decrease of the prey population
        :param gamma: the predators' mortality rate
        :param delta: a coefficient of the increase of the predator population
        """
        if alpha < 0. or beta < 0. or gamma < 0. or delta < 0.:
            raise ValueError

        self._alpha = alpha
        self._beta = beta
        self._gamma = gamma
        self._delta = delta

        super(LotkaVolterraEquation, self).__init__(0, 2)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        r = self._symbols.y[0]
        p = self._symbols.y[1]
        return SymbolicEquationSystem([
            self._alpha * r - self._beta * r * p,
            self._delta * r * p - self._gamma * p
        ])


class LorenzEquation(DifferentialEquation):
    """
    A system of three ordinary differential equations modelling atmospheric
    convection.
    """

    def __init__(
            self,
            sigma: float = 10.,
            rho: float = 28.,
            beta: float = 8. / 3.):
        """
        :param sigma: the first system coefficient
        :param rho: the second system coefficient
        :param beta: the third system coefficient
        """
        if sigma < .0 or rho < .0 or beta < .0:
            raise ValueError

        self._sigma = sigma
        self._rho = rho
        self._beta = beta

        super(LorenzEquation, self).__init__(0, 3)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        c = self._symbols.y[0]
        h = self._symbols.y[1]
        v = self._symbols.y[2]
        return SymbolicEquationSystem([
            self._sigma * (h - c),
            c * (self._rho - v) - h,
            c * h - self._beta * v
        ])


class NBodyGravitationalEquation(DifferentialEquation):
    """
    A system of ordinary differential equations modelling the motion of
    planetary objects.
    """

    def __init__(
            self,
            n_dims: int,
            masses: Sequence[float],
            g: float = 6.6743e-11):
        """
        :param n_dims: the spatial dimensionality the motion of the objects is
            to be considered in (must be either 2 or 3)
        :param masses: a list of the masses of the objects (kg)
        :param g: the gravitational constant (m^3 * kg^-1 * s^-2)
        """
        if n_dims < 2 or n_dims > 3:
            raise ValueError
        if masses is None or len(masses) < 2 or np.any(np.array(masses) <= 0.):
            raise ValueError

        self._dims = n_dims
        self._masses = tuple(masses)
        self._n_objects = len(masses)
        self._g = g

        super(NBodyGravitationalEquation, self).__init__(
            0, 2 * len(masses) * n_dims)

    @property
    def spatial_dimension(self) -> int:
        """
        Returns the number of spatial dimensions.
        """
        return self._dims

    @property
    def masses(self) -> Tuple[float, ...]:
        """
        Returns the masses of the planetary objects.
        """
        return copy(self._masses)

    @property
    def n_objects(self) -> int:
        """
        Returns the number of planetary objects.
        """
        return self._n_objects

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        y = np.array(self._symbols.y, dtype=object)

        n_obj_by_dims = self._n_objects * self._dims

        d_y_over_d_t = np.empty(self._y_dimension, dtype=object)
        d_y_over_d_t[:n_obj_by_dims] = y[n_obj_by_dims:]

        forces_shape = (self._n_objects, self._n_objects, self._dims)
        forces = np.zeros(forces_shape, dtype=object)

        for i in range(self._n_objects):
            position_offset_i = i * self._dims
            position_i = y[position_offset_i:position_offset_i + self._dims]
            mass_i = self._masses[i]

            for j in range(i + 1, self._n_objects):
                position_offset_j = j * self._dims
                position_j = y[position_offset_j:
                               position_offset_j + self._dims]
                mass_j = self._masses[j]
                displacement = position_j - position_i
                distance = np.power(np.power(displacement, 2).sum(axis=-1), .5)
                force = (self._g * mass_i * mass_j) * \
                    (displacement / np.power(distance, 3))
                forces[i, j, :] = force
                forces[j, i, :] = -force

            acceleration = forces[i, :, :].sum(axis=0) / mass_i
            velocity_offset = n_obj_by_dims + position_offset_i
            d_y_over_d_t[velocity_offset:velocity_offset + self._dims] = \
                acceleration

        return SymbolicEquationSystem(d_y_over_d_t)


class DiffusionEquation(DifferentialEquation):
    """
    A partial differential equation modelling the diffusion of particles.
    """

    def __init__(self, x_dimension: int, d: float = 1.):
        """
        :param x_dimension: the dimensionality of the spatial domain of the
            differential equation's solution
        :param d: the diffusion coefficient
        """
        if x_dimension <= 0:
            raise ValueError

        self._d = d

        super(DiffusionEquation, self).__init__(x_dimension, 1)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        return SymbolicEquationSystem([self._d * self._symbols.y_laplacian[0]])


class ConvectionDiffusionEquation(DifferentialEquation):
    """
    A partial differential equation modelling the convection and diffusion of
    particles.
    """

    def __init__(
            self,
            x_dimension: int,
            velocity: Sequence[float],
            d: float = 1.):
        """
        :param x_dimension: the dimensionality of the spatial domain of the
            differential equation's solution
        :param velocity: the convection velocity vector
        :param d: the diffusion coefficient
        """
        if x_dimension <= 0:
            raise ValueError
        if len(velocity) != x_dimension:
            raise ValueError

        self._velocity = copy(velocity)
        self._d = d

        super(ConvectionDiffusionEquation, self).__init__(x_dimension, 1)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        return SymbolicEquationSystem([
            self._d * self._symbols.y_laplacian[0] -
            np.dot(self._velocity, self._symbols.y_gradient[0, :])
        ])


class WaveEquation(DifferentialEquation):
    """
    A partial differential equation modelling the propagation of waves.
    """

    def __init__(self, x_dimension: int, c: float = 1.):
        """
        :param x_dimension: the dimensionality of the spatial domain of the
            differential equation's solution
        :param c: the propagation speed coefficient
        """
        if x_dimension <= 0:
            raise ValueError

        self._c = c

        super(WaveEquation, self).__init__(x_dimension, 2)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        return SymbolicEquationSystem([
            self._symbols.y[1],
            (self._c ** 2) * self._symbols.y_laplacian[0]
        ])


class CahnHilliardEquation(DifferentialEquation):
    """
    A partial differential equation modelling phase separation.
    """

    def __init__(self, x_dimension: int, d: float = .1, gamma: float = .01):
        """
        :param x_dimension: the dimensionality of the spatial domain of the
            differential equation's solution
        :param d: the potential diffusion coefficient
        :param gamma: the concentration diffusion coefficient
        """
        if x_dimension <= 0:
            raise ValueError

        self._d = d
        self._gamma = gamma

        super(CahnHilliardEquation, self).__init__(x_dimension, 2)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        sym = self._symbols
        return SymbolicEquationSystem(
            [
                sym.y[1] ** 3 - sym.y[1] - self._gamma * sym.y_laplacian[1],
                self._d * sym.y_laplacian[0]
            ],
            [
                Lhs.Y,
                Lhs.D_Y_OVER_D_T
            ]
        )


class BurgerEquation(DifferentialEquation):
    """
    A system of partial differential equations providing a simplified model
    of fluid flow.
    """

    def __init__(self, x_dimension: int, re: float = 4000.):
        """
        :param x_dimension: the dimensionality of the spatial domain of the
            differential equation's solution
        :param re: the Reynolds number
        """
        if x_dimension <= 0:
            raise ValueError

        self._re = re

        super(BurgerEquation, self).__init__(x_dimension, x_dimension)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        return SymbolicEquationSystem([
            (1. / self._re) * self._symbols.y_laplacian[i] -
            np.dot(self._symbols.y, self._symbols.y_gradient[i, :])
            for i in range(self._x_dimension)
        ])


class ShallowWaterEquation(DifferentialEquation):
    """
    A system of partial differential equations providing a non-conservative
    model of fluid flow below a pressure surface.
    """

    def __init__(
            self,
            h: float,
            b: float = .01,
            v: float = .1,
            f: float = 0.,
            g: float = 9.80665):
        """
        :param h: the mean height of the pressure surface
        :param b: the viscous drag coefficient
        :param v: the kinematic viscosity coefficient
        :param f: the Coriolis coefficient
        :param g: the gravitational acceleration coefficient
        """
        self._h = h
        self._b = b
        self._v = v
        self._f = f
        self._g = g

        super(ShallowWaterEquation, self).__init__(2, 3)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        return SymbolicEquationSystem([
            -self._h * self._symbols.y_divergence[1, 2] -
            self._symbols.y[0] * self._symbols.y_gradient[1, 0] -
            self._symbols.y[1] * self._symbols.y_gradient[0, 0] -
            self._symbols.y[0] * self._symbols.y_gradient[2, 1] -
            self._symbols.y[2] * self._symbols.y_gradient[0, 1],
            -np.dot(self._symbols.y[1:3], self._symbols.y_gradient[1, :]) +
            self._f * self._symbols.y[2] -
            self._g * self._symbols.y_gradient[0, 0] -
            self._b * self._symbols.y[1] +
            self._v * self._symbols.y_laplacian[1],
            -np.dot(self._symbols.y[1:3], self._symbols.y_gradient[2, :]) -
            self._f * self._symbols.y[1] -
            self._g * self._symbols.y_gradient[0, 1] -
            self._b * self._symbols.y[2] +
            self._v * self._symbols.y_laplacian[2]
        ])


class NavierStokesStreamFunctionVorticityEquation(DifferentialEquation):
    """
    A system of two partial differential equations modelling the vorticity and
    the stream function of incompressible fluids in two spatial dimensions.
    """

    def __init__(self, re: float = 4000.):
        """
        :param re: the Reynolds number
        """
        self._re = re
        super(NavierStokesStreamFunctionVorticityEquation, self).__init__(2, 2)

    @property
    def symbolic_equation_system(self) -> SymbolicEquationSystem:
        return SymbolicEquationSystem(
            [
                (1. / self._re) * self._symbols.y_laplacian[0] -
                np.cross(
                    self._symbols.y_gradient[0, :],
                    self._symbols.y_gradient[1, :]
                ),
                -self._symbols.y[0]
            ],
            [
                Lhs.D_Y_OVER_D_T,
                Lhs.Y_LAPLACIAN
            ]
        )
