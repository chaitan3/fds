from __future__ import division

import os
import sys
import shutil
import tempfile
from subprocess import *

import numpy as np
from numpy import *

my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, '..'))

from fds.timeseries import windowed_mean_weights, windowed_mean
from fds.checkpoint import load_checkpoint
from fds.segment import run_segment, trapez_mean, adjoint_segment
from fds.fds import AdjointWrapper, RunWrapper
from fds.timedilation import TimeDilation, TimeDilationExact

from fds import *

solver_path = os.path.join(my_path, 'solvers', 'lorenz')
solver = os.path.join(solver_path, 'solver')
adj_solver = os.path.join(solver_path, 'adjoint')
tan_solver = os.path.join(solver_path, 'tangent')
u0 = loadtxt(os.path.join(solver_path, 'u0'))

def solve(u, s, nsteps):
    tmp_path = tempfile.mkdtemp()
    with open(os.path.join(tmp_path, 'input.bin'), 'wb') as f:
        f.write(asarray(u, dtype='>d').tobytes())
    with open(os.path.join(tmp_path, 'param.bin'), 'wb') as f:
        f.write(asarray([10, 28., 8./3, s], dtype='>d').tobytes())
    call([solver, str(int(nsteps))], cwd=tmp_path)
    with open(os.path.join(tmp_path, 'output.bin'), 'rb') as f:
        out = frombuffer(f.read(), dtype='>d')
    with open(os.path.join(tmp_path, 'objective.bin'), 'rb') as f:
        J = frombuffer(f.read(), dtype='>d')
    shutil.rmtree(tmp_path)
    return out, J

def tangent(u, s, v, ds, nsteps):
    tmp_path = tempfile.mkdtemp()
    with open(os.path.join(tmp_path, 'input.bin'), 'wb') as f:
        f.write(asarray(u, dtype='>d').tobytes())
    with open(os.path.join(tmp_path, 'param.bin'), 'wb') as f:
        f.write(asarray([10, 28., 8./3, s], dtype='>d').tobytes())
    with open(os.path.join(tmp_path, 'tan-input.bin'), 'wb') as f:
        f.write(asarray(v, dtype='>d').tobytes())
    with open(os.path.join(tmp_path, 'tan-param.bin'), 'wb') as f:
        f.write(asarray([0., 0., 0., ds], dtype='>d').tobytes())
    call([tan_solver, str(int(nsteps))], cwd=tmp_path)
    with open(os.path.join(tmp_path, 'output.bin'), 'rb') as f:
        u = frombuffer(f.read(), dtype='>d')
    with open(os.path.join(tmp_path, 'tan-output.bin'), 'rb') as f:
        v = frombuffer(f.read(), dtype='>d')
    with open(os.path.join(tmp_path, 'J.bin'), 'rb') as f:
        J = frombuffer(f.read(), dtype='>d')
    with open(os.path.join(tmp_path, 'dJ.bin'), 'rb') as f:
        dJ = frombuffer(f.read(), dtype='>d')
    shutil.rmtree(tmp_path)
    return u, v, J, dJ

def adjoint(u, s, nsteps, ua):
    tmp_path = tempfile.mkdtemp()
    with open(os.path.join(tmp_path, 'input.bin'), 'wb') as f:
        f.write(asarray(u, dtype='>d').tobytes())
    with open(os.path.join(tmp_path, 'param.bin'), 'wb') as f:
        f.write(asarray([10, 28., 8./3, s], dtype='>d').tobytes())
    with open(os.path.join(tmp_path, 'adj-input.bin'), 'wb') as f:
        f.write(asarray(ua, dtype='>d').tobytes())
    call([adj_solver, str(int(nsteps))], cwd=tmp_path)
    with open(os.path.join(tmp_path, 'adj-output.bin'), 'rb') as f:
        out = frombuffer(f.read(), dtype='>d')
    with open(os.path.join(tmp_path, 'dJds.bin'), 'rb') as f:
        dJds = frombuffer(f.read(), dtype='>d')
    shutil.rmtree(tmp_path)
    return out, dJds

if __name__ == '__main__':
    m = 1
    s = 28
    steps_per_segment = 1000
    cp_path = 'tests/lorenz_adj'
    if os.path.exists(cp_path):
        shutil.rmtree(cp_path)
    os.mkdir(cp_path)
    cp = shadowing(solve, u0, s, m, 3, steps_per_segment, 5000,
                   checkpoint_path=cp_path, return_checkpoint=True,
                   tangent_run=tangent)

    u0, _, _, lss, G_lss, g_lss, J, G_dil, g_dil = cp
    g_lss = np.array(g_lss)
    J = np.array(J)
    dJ = trapez_mean(J.mean(0), 0) - J[:,-1]
    assert dJ.ndim == 2 and dJ.shape[1] == 1

    win = windowed_mean_weights(dJ.shape[0])
    g_lss_adj = win[:,newaxis]
    alpha_adj_lss = win[:,newaxis] * np.array(G_lss)[:,:,0]

    dil_adj = win * ravel(dJ)
    g_dil_adj = dil_adj / steps_per_segment
    alpha_adj_dil = dil_adj[:,newaxis] * G_dil / steps_per_segment

    alpha_adj = alpha_adj_lss + alpha_adj_dil
    b_adj = lss.adjoint(alpha_adj)

    'verification'
    print()
    print((g_lss_adj * g_lss).sum() + (b_adj * np.array(lss.bs)).sum() + (g_dil_adj * g_dil).sum())
    alpha = lss.solve()
    print((g_lss_adj * g_lss).sum() + (alpha_adj * alpha).sum() + (g_dil_adj * g_dil).sum())
    grad_lss = (alpha[:,:,np.newaxis] * np.array(G_lss)).sum(1) + g_lss
    dil = ((alpha * G_dil).sum(1) + g_dil) / steps_per_segment
    grad_dil = dil[:,np.newaxis] * dJ
    print(windowed_mean(grad_lss) + windowed_mean(grad_dil))

    w = zeros_like(u0)
    k = cp.lss.K_segments() - 1
    cp_file = 'm{}_segment{}'.format(m, k)
    u0, V, v, _,_,_,_,_,_ = load_checkpoint(os.path.join(cp_path, cp_file))
    w, dJds = adjoint_segment(AdjointWrapper(adjoint),
                              u0, w, s, k, steps_per_segment)

    time_dil = TimeDilation(RunWrapper(solve), u0, s, 'time_dilation_test', 4)
    V = time_dil.project(V)
    v = time_dil.project(v)

    _, v1 = lss.checkpoint(V, v)

    #g_lss[-1] = 0
    grad_lss = (alpha[:,:,np.newaxis] * np.array(G_lss)).sum(1) + g_lss
    print(g_lss[-1] + dot(b_adj[-1], lss.bs[-1]))
    print(dJds[3] + dot(v1,w) + dot(b_adj[-1], lss.bs[-1]))

    w1 = lss.adjoint_checkpoint(V, w, b_adj[-1])
    print(dJds[3] + dot(v,w1))

