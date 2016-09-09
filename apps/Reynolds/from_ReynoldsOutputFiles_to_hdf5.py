import numpy
from numpy import *
from mpi4py import MPI
import h5py
import os
import sys
import argparse
import shutil

HDF5file_path = sys.argv[1]
work_path = sys.argv[2]
REF_WORK_PATH = sys.argv[3]

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
root = 0

# Get start
start_file = os.path.join(REF_WORK_PATH, 'start.bin')
comm.Barrier()
if not os.path.exists(start_file):
    if rank == root:
        start = numpy.zeros((size+1, 1), dtype='i')
        for i in range(size):
            ref_data_file = os.path.join(REF_WORK_PATH, 'finalData' + str(i) + '.bin')
            start[i+1] = start[i] + len(frombuffer(open(ref_data_file, 'rb').read(), dtype='d'))
        with open(start_file, 'wb') as f:
            f.write(asarray(start, dtype='i').tobytes())
comm.Barrier()
start = frombuffer(open(start_file, 'rb').read(), dtype='i')

# Get solution from output binary file:
Reynolds_output_file = os.path.join(work_path, 'finalData' + str(rank) + '.bin')
arr = frombuffer(open(Reynolds_output_file, 'rb').read(), dtype='d')
arr = ravel(arr)

# Generate HDF5 file:
with h5py.File(HDF5file_path, 'w', driver='mpio', comm=comm) as handle:
    field = handle.create_dataset('field', shape=(start[size], 1), dtype='d')
    field[start[rank]:start[rank + 1]] = arr