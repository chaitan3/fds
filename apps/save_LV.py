from numpy import *
import fds
import sys
case = sys.argv[1]
N_homo = int(sys.argv[2])

from adFVM.interface import SerialRunner

# compute djds v.s. # segment
cp = fds.checkpoint.load_last_checkpoint(case, N_homo)
v = cp.lss.lyapunov_covariant_vectors()
v = rollaxis(rollaxis(v, 2), 2)
V = array(cp.V)
CLV = dot(V.T, v[-1,:,:]).T

base = case + '/../'
runner = SerialRunner(base, 2.0, None, None, nProcs=16)
#for i in range(N_homo):
for i in range(0, 1):
    print('writing clv', i, 'at', 10 + i)
    runner.writeFields(CLV[i], base, 10.0 + i)
