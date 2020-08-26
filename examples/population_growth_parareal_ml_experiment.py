from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from tensorflow.python.keras import Input
from tensorflow.python.keras.layers import Dense

from pararealml import *
from pararealml.utils.experiment import run_parareal_ml_experiment, \
    calculate_coarse_ml_operator_step_size
from pararealml.utils.ml import create_keras_regressor, limit_visible_gpus
from pararealml.utils.rand import SEEDS

limit_visible_gpus()

diff_eq = PopulationGrowthEquation(2e-2)
cp = ConstrainedProblem(diff_eq)
ic = ContinuousInitialCondition(cp, lambda _: (100,))
ivp = InitialValueProblem(cp, (0., 100.), ic)

f = ODEOperator('DOP853', 1e-6)
g = ODEOperator('RK45', 1e-4)
g_ml = StatefulRegressionOperator(
    calculate_coarse_ml_operator_step_size(ivp), True)

threshold = .1

models = [
    LinearRegression(),
    RandomForestRegressor(n_estimators=10),
    RandomForestRegressor(n_estimators=100),
    RandomForestRegressor(n_estimators=250),
    GradientBoostingRegressor(n_estimators=50),
    GradientBoostingRegressor(n_estimators=100),
    GradientBoostingRegressor(n_estimators=250),
    create_keras_regressor([
        Input(shape=g_ml.model_input_shape(ivp)),
        Dense(50, activation='relu'),
        Dense(g_ml.model_output_shape(ivp)[0])
    ]),
    create_keras_regressor([
        Dense(50, activation='relu'),
        Dense(50, activation='relu'),
        Dense(g_ml.model_output_shape(ivp)[0])
    ])
]

model_names = [
    'lr',
    'rf10',
    'rf100',
    'rf250',
    'bt50',
    'bt100',
    'bt250',
    'fnn1',
    'fnn2'
]

run_parareal_ml_experiment(
    'population_growth',
    ivp,
    f,
    g,
    g_ml,
    models,
    threshold,
    SEEDS[:20],
    iterations=100,
    noise_sd=(0., 50.),
    model_names=model_names)