import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from pararealml.core.boundary_condition import DirichletBoundaryCondition
from pararealml.core.constrained_problem import ConstrainedProblem
from pararealml.core.differential_equation import LorenzEquation, WaveEquation
from pararealml.core.initial_condition import ContinuousInitialCondition, \
    GaussianInitialCondition
from pararealml.core.initial_value_problem import InitialValueProblem
from pararealml.core.mesh import Mesh
from pararealml.core.operators.fdm.numerical_differentiator import \
    ThreePointCentralFiniteDifferenceMethod
from pararealml.core.operators.fdm.fdm_operator import FDMOperator
from pararealml.core.operators.fdm.numerical_integrator import RK4
from pararealml.core.operators.ode.ode_operator import ODEOperator
from pararealml.core.operators.auto_regression.auto_regression_operator \
    import AutoRegressionOperator
from pararealml.utils.rand import set_random_seed


def test_auto_regression_operator_with_wrong_perturbed_initial_value_shape():
    set_random_seed(0)

    diff_eq = LorenzEquation()
    cp = ConstrainedProblem(diff_eq)
    ic = ContinuousInitialCondition(cp, lambda _: np.ones(3))
    ivp = InitialValueProblem(cp, (0., 10.), ic)
    oracle = ODEOperator('DOP853', .001)
    ml_op = AutoRegressionOperator(2.5, True)

    with pytest.raises(ValueError):
        ml_op.train(
            ivp,
            oracle,
            LinearRegression(),
            25,
            lambda t, y: np.array([1.]))


def test_auto_regression_operator_on_ode():
    set_random_seed(0)

    diff_eq = LorenzEquation()
    cp = ConstrainedProblem(diff_eq)
    ic = ContinuousInitialCondition(cp, lambda _: np.ones(3))
    ivp = InitialValueProblem(cp, (0., 10.), ic)

    oracle = ODEOperator('DOP853', .001)
    ref_solution = oracle.solve(ivp)

    ml_op = AutoRegressionOperator(2.5, True)
    ml_op.train(
        ivp,
        oracle,
        RandomForestRegressor(),
        25,
        lambda t, y: y + np.random.normal(0., .01, size=y.shape))
    ml_solution = ml_op.solve(ivp)

    assert ml_solution.vertex_oriented
    assert ml_solution.d_t == 2.5
    assert ml_solution.discrete_y().shape == (4, 3)

    diff = ref_solution.diff([ml_solution])
    assert np.all(diff.matching_time_points == np.linspace(2.5, 10., 4))
    assert np.max(np.abs(diff.differences[0])) < .2


def test_auto_regression_operator_on_pde():
    set_random_seed(0)

    diff_eq = WaveEquation(2)
    mesh = Mesh([(-5., 5.), (-5., 5.)], [1., 1.])
    bcs = [
        (DirichletBoundaryCondition(
            lambda x, t: np.zeros((len(x), 2)), is_static=True),
         DirichletBoundaryCondition(
             lambda x, t: np.zeros((len(x), 2)), is_static=True))
    ] * 2
    cp = ConstrainedProblem(diff_eq, mesh, bcs)
    ic = GaussianInitialCondition(
        cp,
        [(np.array([0., 2.5]), np.array([[.1, 0.], [0., .1]]))] * 2,
        [3., .0]
    )
    ivp = InitialValueProblem(cp, (0., 10.), ic)

    oracle = FDMOperator(
        RK4(), ThreePointCentralFiniteDifferenceMethod(), .1)
    ref_solution = oracle.solve(ivp)

    ml_op = AutoRegressionOperator(2.5, True)
    ml_op.train(
        ivp,
        oracle,
        RandomForestRegressor(),
        20,
        lambda t, y: y + np.random.normal(0., t / 75., size=y.shape))
    ml_solution = ml_op.solve(ivp)

    assert ml_solution.vertex_oriented
    assert ml_solution.d_t == 2.5
    assert ml_solution.discrete_y().shape == (4, 11, 11, 2)

    diff = ref_solution.diff([ml_solution])
    assert np.all(diff.matching_time_points == np.linspace(2.5, 10., 4))
    assert np.max(np.abs(diff.differences[0])) < .5
