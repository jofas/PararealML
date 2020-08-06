import numpy as np
from fipy import LinearCGSSolver
from mpi4py import MPI
from sklearn.ensemble import RandomForestRegressor

from src.experiment import Experiment
from src.core.boundary_condition import NeumannCondition
from src.core.boundary_value_problem import BoundaryValueProblem
from src.core.differential_equation import CahnHilliardEquation
from src.core.differentiator import ThreePointCentralFiniteDifferenceMethod
from src.core.initial_condition import DiscreteInitialCondition
from src.core.initial_value_problem import InitialValueProblem
from src.core.integrator import RK4
from src.core.mesh import UniformGrid
from src.core.operator import FVMOperator, FDMOperator, PINNOperator, \
    SolutionRegressionOperator, OperatorRegressionOperator
from src.utils.print import print_on_first_rank
from src.utils.rand import set_random_seed, SEEDS

diff_eq = CahnHilliardEquation(2, 1., .01)
mesh = UniformGrid(((0., 10.), (0., 10.)), (.1, .1))
bvp = BoundaryValueProblem(
    diff_eq,
    mesh,
    ((NeumannCondition(lambda x: (0., 0.)),
      NeumannCondition(lambda x: (0., 0.))),
     (NeumannCondition(lambda x: (0., 0.)),
      NeumannCondition(lambda x: (0., 0.)))))
ic = DiscreteInitialCondition(
    bvp,
    .05 * np.random.uniform(-1., 1., bvp.y_shape(False)),
    False)
ivp = InitialValueProblem(
    bvp,
    (0., 2.),
    ic)

ml_operator_step_size = \
    (ivp.t_interval[1] - ivp.t_interval[0]) / MPI.COMM_WORLD.size

f = FVMOperator(LinearCGSSolver(), .01)
g = FDMOperator(RK4(), ThreePointCentralFiniteDifferenceMethod(), .01)
g_pinn = PINNOperator(ml_operator_step_size, f.vertex_oriented)
g_sol_reg = SolutionRegressionOperator(
    ml_operator_step_size, f.vertex_oriented)
g_op_reg = OperatorRegressionOperator(ml_operator_step_size, f.vertex_oriented)

threshold = .1

experiment = Experiment(ivp, f, g, g_pinn, g_sol_reg, g_op_reg, threshold)

sol_reg_models = [RandomForestRegressor()]
op_reg_models = [RandomForestRegressor()]

for i in range(5):
    seed = SEEDS[i]

    print_on_first_rank(f'Round {i}; seed = {seed}')

    set_random_seed(seed)

    experiment.solve_serial_fine()
    experiment.solve_serial_coarse()
    experiment.solve_parallel()

    experiment.train_coarse_pinn(
        (50,) * 4, 'tanh', 'Glorot normal',
        n_domain=2000,
        n_initial=200,
        n_boundary=100,
        n_test=400,
        n_epochs=5000,
        optimiser='adam',
        learning_rate=.001)
    experiment.solve_serial_coarse_pinn()
    experiment.solve_parallel_pinn()

    for j, model in enumerate(sol_reg_models):
        print(f'Solution regression model {j}')

        experiment.train_coarse_sol_reg(model, subsampling_factor=.01)
        experiment.solve_serial_coarse_sol_reg()
        experiment.solve_parallel_sol_reg()

    for j, model in enumerate(op_reg_models):
        print(f'Operator regression model {j}')

        experiment.train_coarse_op_reg(
            model, iterations=20, noise_sd=(0., .1))
        experiment.solve_serial_coarse_op_reg()
        experiment.solve_parallel_op_reg()