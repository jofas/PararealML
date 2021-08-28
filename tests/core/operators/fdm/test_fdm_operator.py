import numpy as np

from pararealml.core.boundary_condition import DirichletBoundaryCondition, \
    NeumannBoundaryCondition
from pararealml.core.constrained_problem import ConstrainedProblem
from pararealml.core.differential_equation import PopulationGrowthEquation, \
    LorenzEquation, DiffusionEquation, CahnHilliardEquation, BurgerEquation, \
    NavierStokesStreamFunctionVorticityEquation, ShallowWaterEquation
from pararealml.core.initial_condition import DiscreteInitialCondition, \
    ContinuousInitialCondition, GaussianInitialCondition
from pararealml.core.initial_value_problem import InitialValueProblem
from pararealml.core.mesh import Mesh, CoordinateSystem
from pararealml.core.operators.fdm.numerical_differentiator import \
    ThreePointCentralFiniteDifferenceMethod
from pararealml.core.operators.fdm.fdm_operator import FDMOperator
from pararealml.core.operators.fdm.numerical_integrator import \
    ForwardEulerMethod, RK4, CrankNicolsonMethod


def test_fdm_operator_on_ode_with_analytic_solution():
    r = .02
    y_0 = 100.

    diff_eq = PopulationGrowthEquation(r)
    cp = ConstrainedProblem(diff_eq)
    ic = ContinuousInitialCondition(cp, lambda _: (y_0,))
    ivp = InitialValueProblem(
        cp,
        (0., 10.),
        ic,
        lambda _ivp, t, x: (y_0 * np.e ** (r * t),))

    op = FDMOperator(
        RK4(), ThreePointCentralFiniteDifferenceMethod(), 1e-4)

    solution = op.solve(ivp)

    assert solution.d_t == 1e-4
    assert solution.discrete_y().shape == (1e5, 1)

    analytic_y = np.array([ivp.exact_y(t) for t in solution.t_coordinates])

    assert np.allclose(analytic_y, solution.discrete_y())


def test_fdm_operator_conserves_density_on_zero_flux_diffusion_equation():
    diff_eq = DiffusionEquation(1, 5.)
    mesh = Mesh(((0., 500.),), (.1,))
    bcs = (
        (NeumannBoundaryCondition(lambda x, t: (0.,), is_static=True),
         NeumannBoundaryCondition(lambda x, t: (0.,), is_static=True)),
    )
    cp = ConstrainedProblem(diff_eq, mesh, bcs)
    ic = GaussianInitialCondition(
        cp,
        ((np.array([250]), np.array([[250.]])),),
        (1000.,))
    ivp = InitialValueProblem(cp, (0., 20.), ic)

    y_0 = ic.discrete_y_0(True)
    y_0_sum = np.sum(y_0)

    fdm_op = FDMOperator(
        CrankNicolsonMethod(), ThreePointCentralFiniteDifferenceMethod(), 1e-3)
    solution = fdm_op.solve(ivp)
    y = solution.discrete_y()
    y_sums = np.sum(y, axis=tuple(range(1, y.ndim)))

    assert np.allclose(y_sums, y_0_sum)


def test_fdm_operator_on_ode():
    diff_eq = LorenzEquation()
    cp = ConstrainedProblem(diff_eq)
    ic = ContinuousInitialCondition(
        cp,
        lambda _: (1., 1., 1.))
    ivp = InitialValueProblem(cp, (0., 10.), ic)
    op = FDMOperator(
        ForwardEulerMethod(), ThreePointCentralFiniteDifferenceMethod(), .01)
    solution = op.solve(ivp)

    assert solution.vertex_oriented
    assert solution.d_t == .01
    assert solution.discrete_y().shape == (1000, 3)


def test_fdm_operator_on_1d_pde():
    diff_eq = BurgerEquation(1, 1000.)
    mesh = Mesh(((0., 10.),), (.1,))
    bcs = (
        (NeumannBoundaryCondition(lambda x, t: (0.,), is_static=True),
         NeumannBoundaryCondition(lambda x, t: (0.,), is_static=True)),
    )
    cp = ConstrainedProblem(diff_eq, mesh, bcs)
    ic = GaussianInitialCondition(
        cp,
        ((np.array([2.5]), np.array([[1.]])),))
    ivp = InitialValueProblem(cp, (0., 50.), ic)
    op = FDMOperator(RK4(), ThreePointCentralFiniteDifferenceMethod(), .25)
    solution = op.solve(ivp)

    assert solution.vertex_oriented
    assert solution.d_t == .25
    assert solution.discrete_y().shape == (200, 101, 1)
    assert solution.discrete_y(False).shape == (200, 100, 1)


def test_fdm_operator_on_2d_pde():
    diff_eq = NavierStokesStreamFunctionVorticityEquation(5000.)
    mesh = Mesh(((0., 10.), (0., 10.)), (1., 1.))
    bcs = (
        (DirichletBoundaryCondition(lambda x, t: (1., .1), is_static=True),
         DirichletBoundaryCondition(lambda x, t: (.0, .0), is_static=True)),
        (DirichletBoundaryCondition(lambda x, t: (.0, .0), is_static=True),
         DirichletBoundaryCondition(lambda x, t: (.0, .0), is_static=True))
    )
    cp = ConstrainedProblem(diff_eq, mesh, bcs)
    ic = ContinuousInitialCondition(cp, lambda x: (.0, .0))
    ivp = InitialValueProblem(cp, (0., 10.), ic)
    op = FDMOperator(RK4(), ThreePointCentralFiniteDifferenceMethod(), .25)
    solution = op.solve(ivp)

    assert solution.vertex_oriented
    assert solution.d_t == .25
    assert solution.discrete_y().shape == (40, 11, 11, 2)
    assert solution.discrete_y(False).shape == (40, 10, 10, 2)


def test_fdm_operator_on_3d_pde():
    diff_eq = CahnHilliardEquation(3)
    mesh = Mesh(((0., 5.), (0., 5.), (0., 10.)), (.5, 1., 2.))
    bcs = (
        (NeumannBoundaryCondition(lambda x, t: (0., 0.), is_static=True),
         NeumannBoundaryCondition(lambda x, t: (0., 0.), is_static=True)),
        (NeumannBoundaryCondition(lambda x, t: (0., 0.), is_static=True),
         NeumannBoundaryCondition(lambda x, t: (0., 0.), is_static=True)),
        (NeumannBoundaryCondition(lambda x, t: (0., 0.), is_static=True),
         NeumannBoundaryCondition(lambda x, t: (0., 0.), is_static=True))
    )
    cp = ConstrainedProblem(diff_eq, mesh, bcs)
    ic = DiscreteInitialCondition(
        cp,
        .05 * np.random.uniform(-1., 1., cp.y_shape(True)),
        True)
    ivp = InitialValueProblem(cp, (0., 5.), ic)
    op = FDMOperator(RK4(), ThreePointCentralFiniteDifferenceMethod(), .05)
    solution = op.solve(ivp)

    assert solution.vertex_oriented
    assert solution.d_t == .05
    assert solution.discrete_y().shape == (100, 11, 6, 6, 2)
    assert solution.discrete_y(False).shape == (100, 10, 5, 5, 2)


def test_fdm_operator_on_polar_pde():
    diff_eq = ShallowWaterEquation(.5)
    mesh = Mesh(
        [(1., 11.), (0., 2 * np.pi)],
        [2., np.pi / 5.],
        CoordinateSystem.POLAR)
    bcs = (
        (NeumannBoundaryCondition(
            lambda x, t: (.0, None, None), is_static=True),
         NeumannBoundaryCondition(
             lambda x, t: (.0, None, None), is_static=True)),
        (NeumannBoundaryCondition(
            lambda x, t: (.0, None, None), is_static=True),
         NeumannBoundaryCondition(
             lambda x, t: (.0, None, None), is_static=True))
    )
    cp = ConstrainedProblem(diff_eq, mesh, bcs)
    ic = GaussianInitialCondition(
        cp,
        ((np.array([-6., 0.]), np.array([[.25, 0.], [0., .25]])),) * 3,
        (1., .0, .0))
    ivp = InitialValueProblem(cp, (0., 5.), ic)
    op = FDMOperator(RK4(), ThreePointCentralFiniteDifferenceMethod(), .1)
    solution = op.solve(ivp)

    assert solution.vertex_oriented
    assert solution.d_t == .1
    assert solution.discrete_y().shape == (50, 6, 11, 3)
    assert solution.discrete_y(False).shape == (50, 5, 10, 3)


def test_fdm_operator_on_pde_with_dynamic_boundary_conditions():
    diff_eq = DiffusionEquation(1, 1.5)
    mesh = Mesh(((0., 10.),), (1.,))
    bcs = (
        (NeumannBoundaryCondition(lambda x, t: (0.,)),
         DirichletBoundaryCondition(lambda x, t: (t / 5.,))),
    )
    cp = ConstrainedProblem(diff_eq, mesh, bcs)
    ic = GaussianInitialCondition(
        cp,
        ((np.array([5.]), np.array([[2.5]])),),
        (20.,))
    ivp = InitialValueProblem(cp, (0., 10.), ic)
    op = FDMOperator(RK4(), ThreePointCentralFiniteDifferenceMethod(), .5)
    solution = op.solve(ivp)
    y = solution.discrete_y()

    assert solution.vertex_oriented
    assert solution.d_t == .5
    assert y.shape == (20, 11, 1)
    assert solution.discrete_y(False).shape == (20, 10, 1)

    assert np.isclose(y[0, -1, 0], .1)
    assert np.isclose(y[-1, -1, 0], 2.)
