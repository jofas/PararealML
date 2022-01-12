from abc import ABC, abstractmethod
from typing import Union, List, Optional, Tuple, Sequence

import numpy as np

from pararealml.core.constraint import Constraint, \
    apply_constraints_along_last_axis
from pararealml.core.mesh import CoordinateSystem, Mesh

Slicer = List[Union[int, slice]]

BoundaryConstraintPair = Tuple[
    Optional[Constraint],
    Optional[Constraint]
]


class NumericalDifferentiator(ABC):
    """
    A base class for numerical differentiators.
    """

    def __init__(self, tol: float = 1e-3):
        """
        :param tol: the stopping criterion for the Jacobi algorithm when
            computing the anti-Laplacian; once the second norm of the
            difference of the estimate and the updated estimate drops below
            this threshold, the equation is considered to be solved
        """
        if tol < 0.:
            raise ValueError('tolerance must be non-negative')

        self._tol = tol

    @abstractmethod
    def _derivative(
            self,
            y: np.ndarray,
            d_x: float,
            x_axis: int,
            derivative_boundary_constraints:
            Sequence[Optional[BoundaryConstraintPair]]) -> np.ndarray:
        """
        Computes the derivative of y with respect to the spatial dimension
        defined by x_axis at every point of the mesh.

        :param y: the values of y at every point of the mesh
        :param d_x: the step size of the mesh along the specified axis
        :param x_axis: the spatial dimension that y is to be differentiated
            with respect to
        :param derivative_boundary_constraints: a sequence of boundary
            constraint pairs with an element for each component of y that
            allows for applying constraints to the calculated first
            derivatives at the boundaries normal to the axis that y is
            differentiated with respect to
        :return: the derivative of y with respect to the spatial dimension
            defined by x_axis
        """

    @abstractmethod
    def _second_derivative(
            self,
            y: np.ndarray,
            d_x1: float,
            d_x2: float,
            x_axis1: int,
            x_axis2: int,
            derivative_boundary_constraints:
            Sequence[Optional[BoundaryConstraintPair]]) -> np.ndarray:
        """
        Computes the second derivative of y with respect to the spatial
        dimensions defined by x_axis1 and x_axis2 at every point of the mesh.

        :param y: the values of y at every point of the mesh
        :param d_x1: the step size of the mesh along the axis defined by
            x_axis1
        :param d_x2: the step size of the mesh along the axis defined by
            x_axis2
        :param x_axis1: the first spatial dimension that y is to be
            differentiated with respect to
        :param x_axis2: the second spatial dimension that y is to be
            differentiated with respect to
        :param derivative_boundary_constraints: a sequence of boundary
            constraint pairs with an element for each component of y
            that allows for applying constraints to the calculated first
            derivatives at the boundaries normal to the first axis of
            differentiation before computing the second derivatives
        :return: the second derivative of y with respect to the spatial
            dimensions defined by x_axis1 and x_axis2
        """

    @abstractmethod
    def _next_anti_laplacian_estimate(
            self,
            y_hat: np.ndarray,
            laplacian: np.ndarray,
            mesh: Mesh,
            derivative_boundary_constraints: Optional[np.ndarray]
    ) -> np.ndarray:
        """
        Given an estimate of the anti-Laplacian, it computes an improved
        estimate.

        :param y_hat: the current estimated values of the solution at every
            point of the mesh
        :param laplacian: the Laplacian for which y is to be determined
        :param mesh: the mesh representing the discretized spatial domain
        :param derivative_boundary_constraints: an optional 2D array
            (x dimension, y dimension) of boundary constraint pairs that
            specify constraints on the first derivatives of the solution
        :return: an improved estimate of y_hat
        """

    def gradient(
            self,
            y: np.ndarray,
            mesh: Mesh,
            x_axis: int,
            derivative_boundary_constraints: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Computes the column of the Jacobian matrix of y corresponding to the
        spatial dimension specified by x_axis at every point of the mesh.

        :param y: the values of y at every point of the mesh
        :param mesh: the mesh representing the discretized spatial domain
        :param x_axis: the spatial dimension that y is to be differentiated
            with respect to
        :param derivative_boundary_constraints: a 2D array (x dimension,
            y dimension) of boundary constraint pairs that allow for applying
            constraints to the calculated first derivatives
        :return: the element(s) of the gradient of y corresponding to the
            specified axis
        """
        if y.shape[:-1] != mesh.vertices_shape:
            raise ValueError(
                f'y shape up to second to last axis {y.shape[:-1]} must match '
                f'mesh vertices shape {mesh.vertices_shape}')
        if not (0 <= x_axis < mesh.dimensions):
            raise ValueError(
                f'x axis ({x_axis}) must be non-negative and less than number '
                f'of x dimensions ({mesh.dimensions})')

        derivative_boundary_constraints = \
            self._verify_and_get_derivative_boundary_constraints(
                derivative_boundary_constraints,
                mesh.dimensions,
                y.shape[-1])

        derivative = self._derivative(
            y,
            mesh.d_x[x_axis],
            x_axis,
            derivative_boundary_constraints[x_axis])

        if mesh.coordinate_system_type == CoordinateSystem.CARTESIAN:
            return derivative

        elif mesh.coordinate_system_type == CoordinateSystem.POLAR \
                or mesh.coordinate_system_type == CoordinateSystem.CYLINDRICAL:
            if x_axis == 1:
                r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
                return derivative / r

            return derivative

        elif mesh.coordinate_system_type == CoordinateSystem.SPHERICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            phi = mesh.vertex_coordinate_grids[2][..., np.newaxis]

            if x_axis == 0:
                return derivative

            elif x_axis == 1:
                return derivative / (r * np.sin(phi))

            else:
                return derivative / r

        else:
            raise ValueError(
                'unsupported coordinate system type '
                f'({mesh.coordinate_system_type})')

    def hessian(
            self,
            y: np.ndarray,
            mesh: Mesh,
            x_axis1: int,
            x_axis2: int,
            derivative_boundary_constraints: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Computes the column of the Hessian tensor of y corresponding to the
        spatial dimensions defined by x_axis1 and x_axis2 at every point of
        the mesh.

        :param y: the values of y at every point of the mesh
        :param mesh: the mesh representing the discretized spatial domain
        :param x_axis1: the first spatial dimension that y is to be
            differentiated with respect to
        :param x_axis2: the second spatial dimension that y is to be
            differentiated with respect to
        :param derivative_boundary_constraints: a 2D array (x dimension,
            y dimension) of boundary constraint pairs that allow for applying
            constraints to the calculated first derivatives before using them
            to compute the second derivatives
        :return: the element(s) of the Hessian of y corresponding to the
            specified axes
        """
        if y.shape[:-1] != mesh.vertices_shape:
            raise ValueError(
                f'y shape up to second to last axis {y.shape[:-1]} must match '
                f'mesh vertices shape {mesh.vertices_shape}')
        if not (0 <= x_axis1 < mesh.dimensions) \
                or not (0 <= x_axis2 < mesh.dimensions):
            raise ValueError(
                f'both first x axis ({x_axis1}) and second x axis ({x_axis2}) '
                'must be non-negative and less than number of x dimensions '
                f'({mesh.dimensions})')

        derivative_boundary_constraints = \
            self._verify_and_get_derivative_boundary_constraints(
                derivative_boundary_constraints,
                mesh.dimensions,
                y.shape[-1])

        second_derivative = self._second_derivative(
                y,
                mesh.d_x[x_axis1],
                mesh.d_x[x_axis2],
                x_axis1,
                x_axis2,
                derivative_boundary_constraints[x_axis1])

        if mesh.coordinate_system_type == CoordinateSystem.CARTESIAN:
            return second_derivative

        elif mesh.coordinate_system_type == CoordinateSystem.POLAR \
                or mesh.coordinate_system_type == CoordinateSystem.CYLINDRICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]

            if (x_axis1 == 0 or x_axis1 == 2) \
                    or (x_axis2 == 0 or x_axis2 == 2):
                return second_derivative

            elif x_axis1 == 1 and x_axis2 == 1:
                d_y_over_d_r = self._derivative(
                    y,
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0])
                return (second_derivative / r + d_y_over_d_r) / r

            elif (x_axis1 == 1 and x_axis2 == 0) \
                    or (x_axis1 == 0 and x_axis2 == 1):
                d_y_over_d_theta = self._derivative(
                    y,
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1])
                return (second_derivative - d_y_over_d_theta / r) / r

            else:
                return second_derivative / r

        elif mesh.coordinate_system_type == CoordinateSystem.SPHERICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            phi = mesh.vertex_coordinate_grids[2][..., np.newaxis]

            if x_axis1 == 0 and x_axis2 == 0:
                return second_derivative

            elif x_axis1 == 1 and x_axis2 == 1:
                sin_phi = np.sin(phi)
                cos_phi = np.cos(phi)
                d_y_over_d_r = self._derivative(
                    y,
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0])
                d_y_over_d_phi = self._derivative(
                    y,
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2])
                return (
                    d_y_over_d_r +
                    (
                        second_derivative / sin_phi +
                        cos_phi * d_y_over_d_phi
                    ) / (r * sin_phi)
                ) / r

            if x_axis1 == 2 and x_axis2 == 2:
                d_y_over_d_r = self._derivative(
                    y,
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0])
                return (second_derivative / r + d_y_over_d_r) / r

            if (x_axis1 == 0 and x_axis2 == 1) \
                    or (x_axis1 == 1 and x_axis2 == 0):
                d_y_over_d_theta = self._derivative(
                    y,
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1])
                return (
                    second_derivative - d_y_over_d_theta / r
                ) / (r * np.sin(phi))

            if (x_axis1 == 0 and x_axis2 == 2) \
                    or (x_axis1 == 2 and x_axis2 == 0):
                d_y_over_d_phi = self._derivative(
                    y,
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2])
                return (second_derivative - d_y_over_d_phi / r) / r

            else:
                sin_phi = np.sin(phi)
                cos_phi = np.cos(phi)
                d_y_over_d_theta = self._derivative(
                    y,
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1])
                return (
                    sin_phi * second_derivative - cos_phi * d_y_over_d_theta
                ) / (r * sin_phi) ** 2

        else:
            raise ValueError(
                'unsupported coordinate system type '
                f'({mesh.coordinate_system_type})')

    def divergence(
            self,
            y: np.ndarray,
            mesh: Mesh,
            derivative_boundary_constraints: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Computes the divergence of y with respect to x at every point of the
        mesh.

        :param y: the values of y at every point of the mesh
        :param mesh: the mesh representing the discretized spatial domain
        :param derivative_boundary_constraints: a 2D array (x dimension,
            y dimension) of boundary constraint pairs that allow for applying
            constraints to the calculated first derivatives before using them
            to compute the divergence
        :return: the divergence of y
        """
        if y.shape[:-1] != mesh.vertices_shape:
            raise ValueError(
                f'y shape up to second to last axis {y.shape[:-1]} must match '
                f'mesh vertices shape {mesh.vertices_shape}')
        if y.shape[-1] != mesh.dimensions:
            raise ValueError(
                f'y value vector length ({y.shape[-1]}) must match number of '
                f'x dimensions ({mesh.dimensions})')

        derivative_boundary_constraints = \
            self._verify_and_get_derivative_boundary_constraints(
                derivative_boundary_constraints,
                mesh.dimensions,
                y.shape[-1])

        if mesh.coordinate_system_type == CoordinateSystem.CARTESIAN:
            div = np.zeros(y.shape[:-1] + (1,))
            for i in range(y.shape[-1]):
                div += self._derivative(
                    y[..., i:i + 1],
                    mesh.d_x[i],
                    i,
                    derivative_boundary_constraints[i, i:i + 1])

            return div

        elif mesh.coordinate_system_type == CoordinateSystem.POLAR \
                or mesh.coordinate_system_type == CoordinateSystem.CYLINDRICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            y_r = y[..., :1]
            y_theta = y[..., 1:2]
            d_y_r_over_d_r = self._derivative(
                y_r,
                mesh.d_x[0],
                0,
                derivative_boundary_constraints[0, :1])
            d_y_theta_over_d_theta = self._derivative(
                y_theta,
                mesh.d_x[1],
                1,
                derivative_boundary_constraints[1, 1:2])

            div = d_y_r_over_d_r + (y_r + d_y_theta_over_d_theta) / r
            if mesh.coordinate_system_type == CoordinateSystem.POLAR:
                return div

            y_z = y[..., 2:]
            d_y_z_over_d_z = self._derivative(
                y_z,
                mesh.d_x[2],
                2,
                derivative_boundary_constraints[2, 2:])
            return div + d_y_z_over_d_z

        elif mesh.coordinate_system_type == CoordinateSystem.SPHERICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            phi = mesh.vertex_coordinate_grids[2][..., np.newaxis]
            sin_phi = np.sin(phi)
            cos_phi = np.cos(phi)
            y_r = y[..., :1]
            y_theta = y[..., 1:2]
            y_phi = y[..., 2:]
            d_y_r_over_d_r = self._derivative(
                y_r,
                mesh.d_x[0],
                0,
                derivative_boundary_constraints[0, :1])
            d_y_theta_over_d_theta = self._derivative(
                y_theta,
                mesh.d_x[1],
                1,
                derivative_boundary_constraints[1, 1:2])
            d_y_phi_over_d_phi = self._derivative(
                y_phi,
                mesh.d_x[2],
                2,
                derivative_boundary_constraints[2, 2:])

            return d_y_r_over_d_r + (
                d_y_phi_over_d_phi + 2 * y_r +
                (d_y_theta_over_d_theta + cos_phi * y_phi) / sin_phi
            ) / r

        else:
            raise ValueError(
                'unsupported coordinate system type '
                f'({mesh.coordinate_system_type})')

    def curl(
            self,
            y: np.ndarray,
            mesh: Mesh,
            curl_ind: int = 0,
            derivative_boundary_constraints: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Computes the curl_ind-th component of the curl of y at every point of
        the mesh.

        :param y: the values of y at every point of the mesh
        :param mesh: the mesh representing the discretized spatial domain
        :param curl_ind: the index of the component of the curl of y to
            compute; if y is a two dimensional vector field, it must be 0
        :param derivative_boundary_constraints: a 2D array (x dimension,
            y dimension) of boundary constraint pairs that allow for applying
            constraints to the calculated first derivatives before using them
            to compute the curl
        :return: the curl of y
        """
        if y.shape[:-1] != mesh.vertices_shape:
            raise ValueError(
                f'y shape up to second to last axis {y.shape[:-1]} must match '
                f'mesh vertices shape {mesh.vertices_shape}')
        if y.shape[-1] != mesh.dimensions:
            raise ValueError(
                f'y value vector length ({y.shape[-1]}) must match number of '
                f'x dimensions ({mesh.dimensions})')
        if not (2 <= mesh.dimensions <= 3):
            raise ValueError(
                f'number of x dimensions ({mesh.dimensions}) must be 2 or 3')
        if mesh.dimensions == 2 and curl_ind != 0:
            raise ValueError(f'curl index ({curl_ind}) must be 0 for 2D curl')
        if not (0 <= curl_ind < mesh.dimensions):
            raise ValueError(
                f'curl index ({curl_ind}) must be non-negative and less than '
                f'number of x dimensions ({mesh.dimensions})')

        derivative_boundary_constraints = \
            self._verify_and_get_derivative_boundary_constraints(
                derivative_boundary_constraints,
                mesh.dimensions,
                y.shape[-1])

        if mesh.coordinate_system_type == CoordinateSystem.CARTESIAN:
            if mesh.dimensions == 2 or curl_ind == 2:
                return self._derivative(
                    y[..., 1:2],
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0, 1:2]
                ) - self._derivative(
                    y[..., :1],
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1, :1]
                )

            elif curl_ind == 0:
                return self._derivative(
                    y[..., 2:],
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1, 2:]
                ) - self._derivative(
                    y[..., 1:2],
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2, 1:2]
                )

            else:
                return self._derivative(
                    y[..., :1],
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2, :1]
                ) - self._derivative(
                    y[..., 2:],
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0, 2:]
                )

        elif mesh.coordinate_system_type == CoordinateSystem.POLAR \
                or (mesh.coordinate_system_type == CoordinateSystem.CYLINDRICAL
                    and curl_ind == 2):
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            y_r = y[..., :1]
            y_theta = y[..., 1:2]
            d_y_r_over_d_theta = self._derivative(
                y_r,
                mesh.d_x[1],
                1,
                derivative_boundary_constraints[1, :1])
            d_y_theta_over_d_r = self._derivative(
                y_theta,
                mesh.d_x[0],
                0,
                derivative_boundary_constraints[0, 1:2])
            return d_y_theta_over_d_r + (y_theta - d_y_r_over_d_theta) / r

        elif mesh.coordinate_system_type == CoordinateSystem.CYLINDRICAL:
            if curl_ind == 0:
                r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
                d_y_z_over_d_theta = self._derivative(
                    y[..., 2:],
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1, 2:])
                d_y_theta_over_d_z = self._derivative(
                    y[..., 1:2],
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2, 1:2])
                return d_y_z_over_d_theta / r - d_y_theta_over_d_z

            else:
                d_y_r_over_d_z = self._derivative(
                    y[..., :1],
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2, :1])
                d_y_z_over_d_r = self._derivative(
                    y[..., 2:],
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0, 2:])
                return d_y_r_over_d_z - d_y_z_over_d_r

        elif mesh.coordinate_system_type == CoordinateSystem.SPHERICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]

            if curl_ind == 0:
                phi = mesh.vertex_coordinate_grids[2][..., np.newaxis]
                sin_phi = np.sin(phi)
                cos_phi = np.cos(phi)
                y_theta = y[..., 1:2]
                y_phi = y[..., 2:]
                d_y_theta_over_d_phi = self._derivative(
                    y_theta,
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2, 1:2])
                d_y_phi_over_d_theta = self._derivative(
                    y_phi,
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1, 2:])

                return (
                    d_y_theta_over_d_phi +
                    (cos_phi * y_theta - d_y_phi_over_d_theta) / sin_phi
                ) / r

            elif curl_ind == 1:
                y_r = y[..., :1]
                y_phi = y[..., 2:]
                d_y_r_over_d_phi = self._derivative(
                    y_r,
                    mesh.d_x[2],
                    2,
                    derivative_boundary_constraints[2, :1])
                d_y_phi_over_d_r = self._derivative(
                    y_phi,
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0, 2:])

                return d_y_phi_over_d_r + (y_phi - d_y_r_over_d_phi) / r

            else:
                sin_phi = np.sin(
                    mesh.vertex_coordinate_grids[2][..., np.newaxis])
                y_r = y[..., :1]
                y_theta = y[..., 1:2]
                d_y_r_over_d_theta = self._derivative(
                    y_r,
                    mesh.d_x[1],
                    1,
                    derivative_boundary_constraints[1, :1])
                d_y_theta_over_d_r = self._derivative(
                    y_theta,
                    mesh.d_x[0],
                    0,
                    derivative_boundary_constraints[0, 1:2])

                return -d_y_theta_over_d_r + \
                    (d_y_r_over_d_theta / sin_phi - y_theta) / r

        else:
            raise ValueError(
                'unsupported coordinate system type '
                f'({mesh.coordinate_system_type})')

    def laplacian(
            self,
            y: np.ndarray,
            mesh: Mesh,
            derivative_boundary_constraints:
            Optional[np.ndarray] = None) -> np.ndarray:
        """
        Computes the Laplacian of y at every point of the mesh.

        If the last rank of y has a dimension greater than one, the
        element-wise scalar Laplacian is computed instead of the vector
        Laplacian (which only makes a difference in curvilinear coordinate
        systems).

        :param y: the values of y at every point of the mesh
        :param mesh: the mesh representing the discretized spatial domain
        :param derivative_boundary_constraints: a 2D array (x dimension,
            y dimension) of boundary constraint pairs that allow for applying
            constraints to the calculated first derivatives before using them
            to compute the second derivatives and the Laplacian
        :return: the Laplacian of y
        """
        if y.shape[:-1] != mesh.vertices_shape:
            raise ValueError(
                f'y shape up to second to last axis {y.shape[:-1]} must match '
                f'mesh vertices shape {mesh.vertices_shape}')

        derivative_boundary_constraints = \
            self._verify_and_get_derivative_boundary_constraints(
                derivative_boundary_constraints,
                mesh.dimensions,
                y.shape[-1])

        if mesh.coordinate_system_type == CoordinateSystem.CARTESIAN:
            laplacian = np.zeros_like(y)
            for axis in range(y.ndim - 1):
                laplacian += self._second_derivative(
                    y,
                    mesh.d_x[axis],
                    mesh.d_x[axis],
                    axis,
                    axis,
                    derivative_boundary_constraints[axis, :])

            return laplacian

        elif mesh.coordinate_system_type == CoordinateSystem.POLAR \
                or mesh.coordinate_system_type == CoordinateSystem.CYLINDRICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            d_y_over_d_r = self._derivative(
                y, mesh.d_x[0], 0, derivative_boundary_constraints[0])
            d_sqr_y_over_d_r_sqr = self._second_derivative(
                y,
                mesh.d_x[0],
                mesh.d_x[0],
                0,
                0,
                derivative_boundary_constraints[0])
            d_sqr_y_over_d_theta_sqr = self._second_derivative(
                y,
                mesh.d_x[1],
                mesh.d_x[1],
                1,
                1,
                derivative_boundary_constraints[1])

            laplacian = d_sqr_y_over_d_r_sqr + \
                (d_sqr_y_over_d_theta_sqr / r + d_y_over_d_r) / r
            if mesh.coordinate_system_type == CoordinateSystem.POLAR:
                return laplacian

            d_sqr_y_over_d_z_sqr = self._second_derivative(
                y,
                mesh.d_x[2],
                mesh.d_x[2],
                2,
                2,
                derivative_boundary_constraints[2])
            return laplacian + d_sqr_y_over_d_z_sqr

        elif mesh.coordinate_system_type == CoordinateSystem.SPHERICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            phi = mesh.vertex_coordinate_grids[2][..., np.newaxis]
            sin_phi = np.sin(phi)
            cos_phi = np.cos(phi)
            d_y_over_d_r = self._derivative(
                y, mesh.d_x[0], 0, derivative_boundary_constraints[0])
            d_y_over_d_phi = self._derivative(
                y, mesh.d_x[2], 2, derivative_boundary_constraints[2])
            d_sqr_y_over_d_r_sqr = self._second_derivative(
                y,
                mesh.d_x[0],
                mesh.d_x[0],
                0,
                0,
                derivative_boundary_constraints[0])
            d_sqr_y_over_d_theta_sqr = self._second_derivative(
                y,
                mesh.d_x[1],
                mesh.d_x[1],
                1,
                1,
                derivative_boundary_constraints[1])
            d_sqr_y_over_d_phi_sqr = self._second_derivative(
                y,
                mesh.d_x[2],
                mesh.d_x[2],
                2,
                2,
                derivative_boundary_constraints[2])

            return d_sqr_y_over_d_r_sqr + (
                2 * d_y_over_d_r + (
                    d_sqr_y_over_d_phi_sqr + (
                        cos_phi * d_y_over_d_phi +
                        d_sqr_y_over_d_theta_sqr / sin_phi
                    ) / sin_phi
                ) / r
            ) / r

        else:
            raise ValueError(
                'unsupported coordinate system type '
                f'({mesh.coordinate_system_type})')

    def anti_laplacian(
            self,
            laplacian: np.ndarray,
            mesh: Mesh,
            y_constraints: Sequence[Optional[Constraint]],
            derivative_boundary_constraints: Optional[np.ndarray] = None,
            y_init: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Computes the anti-Laplacian using the Jacobi method.

        :param laplacian: the right-hand side of the equation
        :param mesh: the mesh representing the discretized spatial domain
        :param y_constraints: a sequence of constraints on the values of the
            solution containing a constraint for each element of y; each
            constraint must constrain the boundary values of corresponding
            element of y for the system to be solvable
        :param derivative_boundary_constraints: an optional 2D array
            (x dimension, y dimension) of boundary constraint pairs that
            specify constraints on the first derivatives of the solution
        :param y_init: an optional initial estimate of the solution; if it is
            None, a random array is used
        :return: the array representing the solution to Poisson's equation at
            every point of the mesh
        """
        if laplacian.shape[:-1] != mesh.vertices_shape:
            raise ValueError(
                'Laplacian shape up to second to last axis '
                f'{laplacian.shape[:-1]} must match mesh vertices shape '
                f'{mesh.vertices_shape}')

        derivative_boundary_constraints = \
            self._verify_and_get_derivative_boundary_constraints(
                derivative_boundary_constraints,
                mesh.dimensions,
                laplacian.shape[-1])

        if y_init is None:
            y = np.random.random(laplacian.shape)
        else:
            if y_init.shape != laplacian.shape:
                raise ValueError
            y = y_init

        apply_constraints_along_last_axis(y_constraints, y)

        diff = np.inf
        while diff > self._tol:
            y_old = y
            y = self._next_anti_laplacian_estimate(
                y_old,
                laplacian,
                mesh,
                derivative_boundary_constraints)
            apply_constraints_along_last_axis(y_constraints, y)

            diff = np.linalg.norm(y - y_old)

        return y

    @staticmethod
    def _verify_and_get_derivative_boundary_constraints(
            derivative_boundary_constraints: Optional[np.ndarray],
            x_axes: int,
            y_elements: int) -> np.ndarray:
        """
        If the provided derivative boundary constraints are not None, it just
        asserts that the input array's shape matches expectations and returns
        it. Otherwise it creates an array of empty objects of the correct
        shape and returns that.

        :param derivative_boundary_constraints: an array of derivative boundary
            constraint pairs
        :param x_axes: the number of spatial dimensions
        :param y_elements: the number of elements y has
        :return: an array of derivative boundary constraint pairs or empty
            objects depending on whether the input array is None
        """
        if derivative_boundary_constraints is None:
            return np.empty((x_axes, y_elements), dtype=object)

        if derivative_boundary_constraints.shape != (x_axes, y_elements):
            raise ValueError(
                'expected derivative boundary constraints shape to be '
                f'{(x_axes, y_elements)} but got '
                f'{derivative_boundary_constraints.shape}')

        return derivative_boundary_constraints


class ThreePointCentralDifferenceMethod(NumericalDifferentiator):
    """
    A numerical differentiator using a three-point (second order) central
    difference approximation.
    """

    def __init__(self, tol: float = 1e-3):
        """
        :param tol: the stopping criterion for the Jacobi algorithm when
            computing the anti-Laplacian
        """
        super(ThreePointCentralDifferenceMethod, self).__init__(tol)

    def _derivative(
            self,
            y: np.ndarray,
            d_x: float,
            x_axis: int,
            derivative_boundary_constraints:
            Sequence[Optional[BoundaryConstraintPair]]) -> np.ndarray:
        if y.shape[x_axis] <= 2:
            raise ValueError(
                f'y must contain at least 3 points along x axis ({x_axis})')
        if len(derivative_boundary_constraints) != y.shape[-1]:
            raise ValueError(
                'length of derivative boundary constraints '
                f'({len(derivative_boundary_constraints)}) must match y value '
                f'vector length ({y.shape[-1]})')

        derivative = np.empty_like(y)

        y_slicer: Slicer = [slice(None)] * y.ndim
        derivative_slicer: Slicer = [slice(None)] * len(y.shape)

        two_d_x = 2. * d_x

        # Lower boundary.
        y_slicer[x_axis] = 1
        y_next = y[tuple(y_slicer)]

        y_diff = y_next / two_d_x

        derivative_slicer[x_axis] = 0
        derivative[tuple(derivative_slicer)] = y_diff

        # Internal points.
        y_slicer[x_axis] = slice(0, -2)
        y_prev = y[tuple(y_slicer)]
        y_slicer[x_axis] = slice(2, None)
        y_next = y[tuple(y_slicer)]

        y_diff = (y_next - y_prev) / two_d_x

        derivative_slicer[x_axis] = slice(1, -1)
        derivative[tuple(derivative_slicer)] = y_diff

        # Upper boundary.
        y_slicer[x_axis] = -2
        y_prev = y[tuple(y_slicer)]

        y_diff = -y_prev / two_d_x

        derivative_slicer[x_axis] = -1
        derivative[tuple(derivative_slicer)] = y_diff

        # Derivative boundary constraints.
        for y_ind, constraint_pair in \
                enumerate(derivative_boundary_constraints):
            if constraint_pair is None:
                continue

            derivative_slicer[-1] = slice(y_ind, y_ind + 1)

            lower_boundary_constraint = constraint_pair[0]
            if lower_boundary_constraint is not None:
                derivative_slicer[x_axis] = 0
                lower_boundary_constraint.apply(
                    derivative[tuple(derivative_slicer)])

            upper_boundary_constraint = constraint_pair[1]
            if upper_boundary_constraint is not None:
                derivative_slicer[x_axis] = -1
                upper_boundary_constraint.apply(
                    derivative[tuple(derivative_slicer)])

        return derivative

    def _second_derivative(
            self,
            y: np.ndarray,
            d_x1: float,
            d_x2: float,
            x_axis1: int,
            x_axis2: int,
            derivative_boundary_constraints:
            Sequence[Optional[BoundaryConstraintPair]]) -> np.ndarray:
        if x_axis1 != x_axis2:
            first_derivative = self._derivative(
                y,
                d_x1,
                x_axis1,
                derivative_boundary_constraints)
            return self._derivative(
                first_derivative,
                d_x2,
                x_axis2,
                [None] * y.shape[-1])

        if y.shape[x_axis1] <= 2:
            raise ValueError(
                f'y must contain at least 3 points along x axis ({x_axis1})')

        second_derivative = np.empty_like(y)

        y_slicer: Slicer = [slice(None)] * y.ndim
        second_derivative_slicer: Slicer = [slice(None)] * len(y.shape)

        d_x_squared = d_x1 * d_x2

        y_slicer[x_axis1] = 1
        y_lower_boundary_adjacent = y[tuple(y_slicer)]
        y_slicer[x_axis1] = -2
        y_upper_boundary_adjacent = y[tuple(y_slicer)]
        y_lower_halo, y_upper_halo = \
            self._halos_from_derivative_boundary_constraints(
                y_lower_boundary_adjacent,
                y_upper_boundary_adjacent,
                d_x1,
                derivative_boundary_constraints)

        # Lower boundary.
        y_slicer[x_axis1] = 0
        y_curr = y[tuple(y_slicer)]

        y_diff = (
            y_lower_boundary_adjacent - 2. * y_curr + y_lower_halo
        ) / d_x_squared

        second_derivative_slicer[x_axis1] = 0
        second_derivative[tuple(second_derivative_slicer)] = y_diff

        # Internal points.
        y_slicer[x_axis1] = slice(0, -2)
        y_prev = y[tuple(y_slicer)]
        y_slicer[x_axis1] = slice(1, -1)
        y_curr = y[tuple(y_slicer)]
        y_slicer[x_axis1] = slice(2, None)
        y_next = y[tuple(y_slicer)]

        y_diff = (y_next - 2. * y_curr + y_prev) / d_x_squared

        second_derivative_slicer[x_axis1] = slice(1, -1)
        second_derivative[tuple(second_derivative_slicer)] = y_diff

        # Upper boundary.
        y_slicer[x_axis1] = -1
        y_curr = y[tuple(y_slicer)]

        y_diff = (
            y_upper_halo - 2. * y_curr + y_upper_boundary_adjacent
        ) / d_x_squared

        second_derivative_slicer[x_axis1] = -1
        second_derivative[tuple(second_derivative_slicer)] = y_diff

        return second_derivative

    def _next_anti_laplacian_estimate(
            self,
            y_hat: np.ndarray,
            laplacian: np.ndarray,
            mesh: Mesh,
            derivative_boundary_constraints: Optional[np.ndarray]
    ) -> np.ndarray:
        if not np.all(np.array(y_hat.shape[:-1]) > 2):
            raise ValueError(
                'y must contain at least 3 points along all x axes')

        anti_laplacian = np.zeros_like(y_hat)

        d_x = np.array(mesh.d_x)
        d_x_sqr = np.square(d_x)

        slicer: Slicer = [slice(None)] * y_hat.ndim

        if mesh.coordinate_system_type == CoordinateSystem.CARTESIAN:
            step_size_coefficient_sum = 0.

            for axis, d_x in enumerate(mesh.d_x):
                step_size_coefficient = d_x_sqr[:axis].prod() * \
                    d_x_sqr[axis + 1:].prod()
                step_size_coefficient_sum += step_size_coefficient

                # Halo values from derivative boundary constraints.
                slicer[axis] = 1
                y_lower_boundary_adjacent = y_hat[tuple(slicer)]
                slicer[axis] = -2
                y_upper_boundary_adjacent = y_hat[tuple(slicer)]
                y_lower_halo, y_upper_halo = \
                    self._halos_from_derivative_boundary_constraints(
                        y_lower_boundary_adjacent,
                        y_upper_boundary_adjacent,
                        d_x,
                        derivative_boundary_constraints[axis])

                # Lower boundary.
                slicer[axis] = 0
                anti_laplacian[tuple(slicer)] += \
                    step_size_coefficient * \
                    (y_lower_halo + y_lower_boundary_adjacent)

                # Internal points.
                slicer[axis] = slice(0, -2)
                y_prev = y_hat[tuple(slicer)]
                slicer[axis] = slice(2, None)
                y_next = y_hat[tuple(slicer)]

                slicer[axis] = slice(1, -1)
                anti_laplacian[tuple(slicer)] += \
                    step_size_coefficient * (y_prev + y_next)

                # Upper boundary.
                slicer[axis] = -1
                anti_laplacian[tuple(slicer)] += \
                    step_size_coefficient * \
                    (y_upper_boundary_adjacent + y_upper_halo)

                slicer[axis] = slice(None)

            anti_laplacian -= d_x_sqr.prod() * laplacian
            anti_laplacian /= 2. * step_size_coefficient_sum
            return anti_laplacian

        elif mesh.coordinate_system_type == CoordinateSystem.POLAR or \
                mesh.coordinate_system_type == CoordinateSystem.CYLINDRICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            r_sqr = r ** 2

            # The r axis.
            d_r = d_x[0]
            d_r_sqr = d_x_sqr[0]

            slicer[0] = 1
            y_lower_boundary_adjacent_r = y_hat[tuple(slicer)]
            slicer[0] = -2
            y_upper_boundary_adjacent_r = y_hat[tuple(slicer)]
            y_lower_halo_r, y_upper_halo_r = \
                self._halos_from_derivative_boundary_constraints(
                    y_lower_boundary_adjacent_r,
                    y_upper_boundary_adjacent_r,
                    d_r,
                    derivative_boundary_constraints[0])
            slicer[0] = slice(0, -2)
            y_prev_r = y_hat[tuple(slicer)]
            slicer[0] = slice(2, None)
            y_next_r = y_hat[tuple(slicer)]

            # Lower boundary.
            slicer[0] = 0
            anti_laplacian[tuple(slicer)] += \
                (y_lower_boundary_adjacent_r + y_lower_halo_r) / d_r_sqr + \
                (
                    y_lower_boundary_adjacent_r - y_lower_halo_r
                ) / (2. * d_r * r[1, ...])

            # Internal points.
            slicer[0] = slice(1, -1)
            anti_laplacian[tuple(slicer)] += \
                (y_next_r + y_prev_r) / d_r_sqr + \
                (y_next_r - y_prev_r) / (2. * d_r * r[1:-1, ...])

            # Upper boundary.
            slicer[0] = -1
            anti_laplacian[tuple(slicer)] += \
                (y_upper_halo_r + y_upper_boundary_adjacent_r) / d_r_sqr + \
                (
                    y_upper_halo_r - y_upper_boundary_adjacent_r
                ) / (2. * d_r * r[-1, ...])

            slicer[0] = slice(None)

            # The theta axis.
            d_theta = d_x[1]
            d_theta_sqr = d_x_sqr[1]

            slicer[1] = 1
            y_lower_boundary_adjacent_theta = y_hat[tuple(slicer)]
            slicer[1] = -2
            y_upper_boundary_adjacent_theta = y_hat[tuple(slicer)]
            y_lower_halo_theta, y_upper_halo_theta = \
                self._halos_from_derivative_boundary_constraints(
                    y_lower_boundary_adjacent_theta,
                    y_upper_boundary_adjacent_theta,
                    d_theta,
                    derivative_boundary_constraints[1])
            slicer[1] = slice(0, -2)
            y_prev_theta = y_hat[tuple(slicer)]
            slicer[1] = slice(2, None)
            y_next_theta = y_hat[tuple(slicer)]

            # Lower boundary.
            slicer[1] = 0
            anti_laplacian[tuple(slicer)] += (
                y_lower_boundary_adjacent_theta + y_lower_halo_theta
            ) / (d_theta_sqr * r_sqr[:, 1, ...])

            # Internal points.
            slicer[1] = slice(1, -1)
            anti_laplacian[tuple(slicer)] += (
                y_next_theta + y_prev_theta
            ) / (d_theta_sqr * r_sqr[:, 1:-1, ...])

            # Upper boundary.
            slicer[1] = -1
            anti_laplacian[tuple(slicer)] += (
                y_upper_halo_theta + y_upper_boundary_adjacent_theta
            ) / (d_theta_sqr * r_sqr[:, -1, ...])

            anti_laplacian -= laplacian
            step_size_coefficient = 1. / d_r_sqr + 1. / (d_theta_sqr * r_sqr)

            if mesh.coordinate_system_type == CoordinateSystem.POLAR:
                return anti_laplacian / (2. * step_size_coefficient)

            slicer[1] = slice(None)

            # The z axis.
            d_z = d_x[2]
            d_z_sqr = d_x_sqr[2]

            slicer[2] = 1
            y_lower_boundary_adjacent_z = y_hat[tuple(slicer)]
            slicer[2] = -2
            y_upper_boundary_adjacent_z = y_hat[tuple(slicer)]
            y_lower_halo_z, y_upper_halo_z = \
                self._halos_from_derivative_boundary_constraints(
                    y_lower_boundary_adjacent_z,
                    y_upper_boundary_adjacent_z,
                    d_z,
                    derivative_boundary_constraints[2])
            slicer[2] = slice(0, -2)
            y_prev_z = y_hat[tuple(slicer)]
            slicer[2] = slice(2, None)
            y_next_z = y_hat[tuple(slicer)]

            # Lower boundary.
            slicer[2] = 0
            anti_laplacian[tuple(slicer)] += \
                (y_lower_boundary_adjacent_z + y_lower_halo_z) / d_z_sqr

            # Internal points.
            slicer[2] = slice(1, -1)
            anti_laplacian[tuple(slicer)] += (y_next_z + y_prev_z) / d_z_sqr

            # Upper boundary.
            slicer[2] = -1
            anti_laplacian[tuple(slicer)] += \
                (y_upper_halo_z + y_upper_boundary_adjacent_z) / d_z_sqr

            step_size_coefficient += 1. / d_z_sqr
            return anti_laplacian / (2. * step_size_coefficient)

        elif mesh.coordinate_system_type == CoordinateSystem.SPHERICAL:
            r = mesh.vertex_coordinate_grids[0][..., np.newaxis]
            r_sqr = r ** 2
            phi = mesh.vertex_coordinate_grids[2][..., np.newaxis]
            cos_phi = np.cos(phi)
            sin_phi = np.sin(phi)
            sin_phi_sqr = sin_phi ** 2
            r_sqr_sin_phi_sqr = r_sqr * sin_phi_sqr

            # The r axis.
            d_r = d_x[0]
            d_r_sqr = d_x_sqr[0]

            slicer[0] = 1
            y_lower_boundary_adjacent_r = y_hat[tuple(slicer)]
            slicer[0] = -2
            y_upper_boundary_adjacent_r = y_hat[tuple(slicer)]
            y_lower_halo_r, y_upper_halo_r = \
                self._halos_from_derivative_boundary_constraints(
                    y_lower_boundary_adjacent_r,
                    y_upper_boundary_adjacent_r,
                    d_r,
                    derivative_boundary_constraints[0])
            slicer[0] = slice(0, -2)
            y_prev_r = y_hat[tuple(slicer)]
            slicer[0] = slice(2, None)
            y_next_r = y_hat[tuple(slicer)]

            # Lower boundary.
            slicer[0] = 0
            anti_laplacian[tuple(slicer)] += \
                (y_lower_boundary_adjacent_r + y_lower_halo_r) / d_r_sqr + \
                (
                    y_lower_boundary_adjacent_r - y_lower_halo_r
                ) / (d_r * r[1, ...])

            # Internal points.
            slicer[0] = slice(1, -1)
            anti_laplacian[tuple(slicer)] += \
                (y_next_r + y_prev_r) / d_r_sqr + \
                (y_next_r - y_prev_r) / (d_r * r[1:-1, ...])

            # Upper boundary.
            slicer[0] = -1
            anti_laplacian[tuple(slicer)] += \
                (y_upper_halo_r + y_upper_boundary_adjacent_r) / d_r_sqr + \
                (
                    y_upper_halo_r - y_upper_boundary_adjacent_r
                ) / (d_r * r[-1, ...])

            slicer[0] = slice(None)

            # The theta axis.
            d_theta = d_x[1]
            d_theta_sqr = d_x_sqr[1]

            slicer[1] = 1
            y_lower_boundary_adjacent_theta = y_hat[tuple(slicer)]
            slicer[1] = -2
            y_upper_boundary_adjacent_theta = y_hat[tuple(slicer)]
            y_lower_halo_theta, y_upper_halo_theta = \
                self._halos_from_derivative_boundary_constraints(
                    y_lower_boundary_adjacent_theta,
                    y_upper_boundary_adjacent_theta,
                    d_theta,
                    derivative_boundary_constraints[1])
            slicer[1] = slice(0, -2)
            y_prev_theta = y_hat[tuple(slicer)]
            slicer[1] = slice(2, None)
            y_next_theta = y_hat[tuple(slicer)]

            # Lower boundary.
            slicer[1] = 0
            anti_laplacian[tuple(slicer)] += (
                y_lower_boundary_adjacent_theta + y_lower_halo_theta
            ) / (d_theta_sqr * r_sqr_sin_phi_sqr[:, 1, ...])

            # Internal points.
            slicer[1] = slice(1, -1)
            anti_laplacian[tuple(slicer)] += (
                y_next_theta + y_prev_theta
            ) / (d_theta_sqr * r_sqr_sin_phi_sqr[:, 1:-1, ...])

            # Upper boundary.
            slicer[1] = -1
            anti_laplacian[tuple(slicer)] += (
                y_upper_halo_theta + y_upper_boundary_adjacent_theta
            ) / (d_theta_sqr * r_sqr_sin_phi_sqr[:, -1, ...])

            slicer[1] = slice(None)

            # The phi axis.
            d_phi = d_x[2]
            d_phi_sqr = d_x_sqr[2]

            slicer[2] = 1
            y_lower_boundary_adjacent_phi = y_hat[tuple(slicer)]
            slicer[2] = -2
            y_upper_boundary_adjacent_phi = y_hat[tuple(slicer)]
            y_lower_halo_phi, y_upper_halo_phi = \
                self._halos_from_derivative_boundary_constraints(
                    y_lower_boundary_adjacent_phi,
                    y_upper_boundary_adjacent_phi,
                    d_phi,
                    derivative_boundary_constraints[2])
            slicer[2] = slice(0, -2)
            y_prev_phi = y_hat[tuple(slicer)]
            slicer[2] = slice(2, None)
            y_next_phi = y_hat[tuple(slicer)]

            # Lower boundary.
            slicer[2] = 0
            anti_laplacian[tuple(slicer)] += (
                (
                    y_lower_boundary_adjacent_phi + y_lower_halo_phi
                ) / d_phi_sqr +
                cos_phi[:, :, 1, :] * (
                    y_lower_boundary_adjacent_phi - y_lower_halo_phi
                ) / (2. * d_phi * sin_phi[:, :, 1, :])
            ) / r_sqr[:, :, 1, :]

            # Internal points.
            slicer[2] = slice(1, -1)
            anti_laplacian[tuple(slicer)] += (
                (y_next_phi + y_prev_phi) / d_phi_sqr +
                cos_phi[:, :, 1:-1, :] * (
                    y_next_phi - y_prev_phi
                ) / (2. * d_phi * sin_phi[:, :, 1:-1, :])
            ) / r_sqr[:, :, 1:-1, :]

            # Upper boundary.
            slicer[2] = -1
            anti_laplacian[tuple(slicer)] += (
                (
                    y_upper_halo_phi + y_upper_boundary_adjacent_phi
                ) / d_phi_sqr +
                cos_phi[:, :, -1, :] * (
                    y_upper_halo_phi - y_upper_boundary_adjacent_phi
                ) / (2. * d_phi * sin_phi[:, :, -1, :])
            ) / r_sqr[:, :, -1, :]

            anti_laplacian -= laplacian
            return anti_laplacian / (
                2. * (
                    1. / d_r_sqr +
                    1. / (d_theta_sqr * r_sqr_sin_phi_sqr) +
                    1. / (d_phi_sqr * r_sqr)
                )
            )

        else:
            raise ValueError(
                'unsupported coordinate system type '
                f'({mesh.coordinate_system_type})')

    @staticmethod
    def _halos_from_derivative_boundary_constraints(
            y_lower_boundary_adjacent: np.ndarray,
            y_upper_boundary_adjacent: np.ndarray,
            d_x: float,
            derivative_boundary_constraints:
            Sequence[Optional[BoundaryConstraintPair]]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculates the values of y at the halo vertices of the mesh based on
        the derivative boundary constraints and the values at the vertices
        adjacent to the boundary vertices.

        :param y_lower_boundary_adjacent: the values of y at the second
            lowermost set of vertices along the axis
        :param y_upper_boundary_adjacent: the values of y at the second
            uppermost set of vertices along the axis
        :param d_x: the spatial step size
        :param derivative_boundary_constraints: the derivative boundary
            constraints
        :return: a tuple of the lower and upper halo values.
        """
        y_lower_halo = np.zeros_like(y_lower_boundary_adjacent)
        y_upper_halo = np.zeros_like(y_upper_boundary_adjacent)

        for y_ind, boundary_constraint_pair in \
                enumerate(derivative_boundary_constraints):
            if boundary_constraint_pair is None:
                continue

            lower_boundary_constraint = boundary_constraint_pair[0]
            if lower_boundary_constraint is not None:
                lower_boundary_constraint.multiply_and_add(
                    y_lower_boundary_adjacent[..., y_ind:y_ind + 1],
                    -2. * d_x,
                    y_lower_halo[..., y_ind:y_ind + 1])

            upper_boundary_constraint = boundary_constraint_pair[1]
            if upper_boundary_constraint is not None:
                upper_boundary_constraint.multiply_and_add(
                    y_upper_boundary_adjacent[..., y_ind:y_ind + 1],
                    2. * d_x,
                    y_upper_halo[..., y_ind:y_ind + 1])

        return y_lower_halo, y_upper_halo
