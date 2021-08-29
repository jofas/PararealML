from pararealml import *
from pararealml.core.operators.fdm import *

diff_eq = NavierStokesEquation(5000.)
mesh = Mesh(((-2.5, 2.5), (0., 4.)), (.05, .05))
bcs = (
    (DirichletBoundaryCondition(
        lambda x, t: (1., .1, None, None), is_static=True),
     DirichletBoundaryCondition(
         lambda x, t: (.0, .0, None, None), is_static=True)),
    (DirichletBoundaryCondition(
        lambda x, t: (.0, .0, None, None), is_static=True),
     DirichletBoundaryCondition(
         lambda x, t: (.0, .0, None, None), is_static=True))
)
cp = ConstrainedProblem(diff_eq, mesh, bcs)
ic = ContinuousInitialCondition(cp, lambda x: (.0, .0, .0, .0))
ivp = InitialValueProblem(cp, (0., 100.), ic)

solver = FDMOperator(RK4(), ThreePointCentralFiniteDifferenceMethod(), .05)
solution = solver.solve(ivp)
solution.plot('navier_stokes', n_images=50, quiver_scale=.1)
