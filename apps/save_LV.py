from numpy import *
import fds
import sys
case = sys.argv[1]
N_homo = int(sys.argv[2])

# compute djds v.s. # segment
cp = fds.checkpoint.load_last_checkpoint(case, N_homo)
v = cp.lss.lyapunov_covariant_vectors()
V = cp.V
import pdb;pdb.set_trace()
