from fipy import LinearLUSolver
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from tensorflow.python.keras import Input
from tensorflow.python.keras.layers import Dense

from src.core.boundary_condition import NeumannCondition, DirichletCondition
from src.core.boundary_value_problem import BoundaryValueProblem
from src.core.differential_equation import DiffusionEquation
from src.core.differentiator import ThreePointCentralFiniteDifferenceMethod
from src.core.initial_condition import ContinuousInitialCondition
from src.core.initial_value_problem import InitialValueProblem
from src.core.integrator import CrankNicolsonMethod
from src.core.mesh import UniformGrid
from src.core.operator import FVMOperator, FDMOperator, \
    StatefulRegressionOperator
from src.core.parareal import PararealOperator
from src.utils.experiment import run_parareal_ml_experiment, \
    calculate_coarse_ml_operator_step_size
from src.utils.ml import create_keras_regressor, limit_visible_gpus
from src.utils.rand import SEEDS

limit_visible_gpus()

diff_eq = DiffusionEquation(2)
mesh = UniformGrid(((0., 20.), (0., 20.)), (.2, .2))
bcs = (
    (DirichletCondition(lambda x: (1.,)),
     DirichletCondition(lambda x: (-1.,))),
    (NeumannCondition(lambda x: (.1,)),
     NeumannCondition(lambda x: (.1,)))
)
bvp = BoundaryValueProblem(diff_eq, mesh, bcs)
ic = ContinuousInitialCondition(bvp, lambda _: (0.,))
ivp = InitialValueProblem(
    bvp,
    (0., 10.),
    ic)

f = FVMOperator(LinearLUSolver(), .01)
g = FDMOperator(
    CrankNicolsonMethod(), ThreePointCentralFiniteDifferenceMethod(), .01)
g_ml = StatefulRegressionOperator(
    calculate_coarse_ml_operator_step_size(ivp), f.vertex_oriented)

threshold = .1

parareal = PararealOperator(f, g, threshold)
parareal_ml = PararealOperator(f, g_ml, threshold)

models = [
    LinearRegression(),
    RandomForestRegressor(n_estimators=50),
    RandomForestRegressor(n_estimators=250),
    RandomForestRegressor(n_estimators=500),
    GradientBoostingRegressor(n_estimators=100),
    GradientBoostingRegressor(n_estimators=250),
    GradientBoostingRegressor(n_estimators=500),
    create_keras_regressor([
        Input(shape=g_ml.model_input_shape(ivp)),
        Dense(50, activation='relu'),
        Dense(g_ml.model_output_shape(ivp)[0])
    ]),
    create_keras_regressor([
        Input(shape=g_ml.model_input_shape(ivp)),
        Dense(50, activation='relu'),
        Dense(50, activation='relu'),
        Dense(50, activation='relu'),
        Dense(g_ml.model_output_shape(ivp)[0])
    ]),
    create_keras_regressor([
        Input(shape=g_ml.model_input_shape(ivp)),
        Dense(50, activation='relu'),
        Dense(50, activation='relu'),
        Dense(50, activation='relu'),
        Dense(50, activation='relu'),
        Dense(50, activation='relu'),
        Dense(g_ml.model_output_shape(ivp)[0])
    ])
]

model_names = [
    'lr',
    'rf50',
    'rf250',
    'rf500',
    'bt100',
    'bt250',
    'bt500',
    'fnn1',
    'fnn3',
    'fnn5'
]

run_parareal_ml_experiment(
    'diffusion',
    ivp,
    f,
    g,
    g_ml,
    models,
    threshold,
    SEEDS[:10],
    iterations=20,
    noise_sd=(0., 1.),
    model_names=model_names)