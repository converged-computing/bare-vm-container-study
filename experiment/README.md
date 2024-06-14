# Experiment

We are going to run all the applications on bare metal, with docker, and with singularity. So far I've only installed amg (with spack) so we will test that quickly.

```console
mkdir -p $HOME/containers
cd $HOME/containers
```

## AMG

```bash
time singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-c2d
time singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu
```

Since this container requires sourcing spack, we need to write a bash script to run on the host.

```bash
#!/bin/bash
# run_amg.sh
. /etc/profile.d/z10_spack_environment.sh
amg -P 2 4 7 -n 64 128 128
```

And now the runs! These are just tests.

```console
# Bare metal: 33.866 seconds
time /opt/view/bin/mpirun --host $(hostname):56 /opt/view/bin/amg -P 2 4 7 -n 64 128 128

# Singularity "my computer" : 37.091 seconds (from outside the container) - it seems like the delay is in the startup
time mpirun --host $(hostname):56 singularity exec metric-amg2023_spack-slim-cpu.sif /bin/bash ./run_amg.sh

# Singularity "c2d": 36.89 seconds
time mpirun --host $(hostname):56 singularity exec metric-amg2023_spack-c2d.sif /bin/bash ./run_amg.sh
```

Thoughts: if we profile the application once it starts in the container, I suspect it's exactly the same. The overhead
seems to be a brief pause at the start of the container. It's hard to say with one run (only 36 seconds) if the difference
between c2d and my computer is real or just variation. If we do single node benchmarks that don't require mpi, we can run
them entirely in the container and not need the external MPI. My hypotheses right now:

- communication dependent things (that need interaction with the host or other nodes) cannot be in an isolated environment (e.g., docker)
- but those environments (singularity) have some overhead (akin to pulling) we need to understand
- I'd like to map out the entire set of steps / tradeoff to using containers (manual build time vs pull and small overhead)
  - I suspect its worth it, build once and use everywhere vs. "lots of pain every time"
- if we just consider inside the container, it's likely the same (see with lammps)

## LAMMPS

I'll quickly test lammps since we don't need mpirun (for a run in docker)

```bash
time singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu
time singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:c2d

# pull the data
oras pull ghcr.io/converged-computing/metric-lammps-cpu:libfabric-data
```

And time! We are going to consider total wrapped time AND wall time. Each has two runs.

```console
cd ./common

# Bare metal with mpirun: 
# wrapped: 30.46, 30.527 seconds
# wall time: 28, 28 seconds
time /usr/local/bin/mpirun --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# Bare metal without mpirun (note fewer number of steps)
# wrapped: 24.826, 24.856 seconds
# wall time: 23, 23 seconds
time lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 1000

# "My computer" singularity: 
# wrapped: 32.55, 32.989 seconds
# wall times: 29, 28 seconds (tie breaker 28 seconds)
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# "My computer" singularity, in shell: 
# wrapped: 25.235, 25.286 seconds
# wall times: 23, 23 seconds
singularity shell --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_latest.sif
time lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 1000

# "c2d" singularity, in shell: 
# wrapped:  25.091, 25.103 seconds
# wall times: 23, 23 seconds
singularity shell --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_c2d.sif
time lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 1000

# "c2d" singularity
# wrapped: 33.124, 32.627 seconds
# wall times: 28, 29 seconds
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_c2d.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# docker "my computer": 
# wrapped: 25.142, 25.183 seconds
# wall time: 23 and 23 seconds, 
docker run -it ghcr.io/converged-computing/metric-lammps-cpu
time lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 1000

# docker "c2d":
# wrapped: 25.185, 25.163
# wall time: 23, 23 seconds
docker run -it ghcr.io/converged-computing/metric-lammps-cpu:c2d
time lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 1000
```

My conclusions - the wall times are (mostly) the same! Since the granularity is by the second it's hard to tell if 28 vs. 29 is significantly different. But if not, the application doesn't "see" anything different, at least in this tiny set of runs.
But there is some overhead to starting things up I think. It would be fun to profile just that.

I would also like a consistent way to always get a time for a run, or other metrics, maybe ebpf can help there.

That was very satisfying - I think we can learn a lot without spending too much. I'm going to bed and will pick up tomorrow.


## Kripke

```bash
time singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu
time singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:c2d
```

And time! We are going to consider total wrapped time AND wall time. Each has two runs.

```console
# Bare metal with mpirun: 
time /usr/local/bin/mpirun --host $(hostname):56 kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
TIMER_NAMES:Generate,LPlusTimes,LTimes,Population,Scattering,Solve,Source,SweepSolver,SweepSubdomain
TIMER_DATA:0.040797,3.802591,7.491424,0.060380,87.039040,108.981689,0.005787,8.194255,0.261393

Figures of Merit
================

  Throughput:         8.250505e+06 [unknowns/(second/iteration)]
  Grind time :        1.212047e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  3.18995 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m51.126s
user	101m33.193s
sys	0m39.193s
```

And "My computer" singularity: 

```console
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-kripke-cpu_latest.sif kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
Figures of Merit
================

  Throughput:         8.254216e+06 [unknowns/(second/iteration)]
  Grind time :        1.211502e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  3.71224 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m53.323s
user	101m34.642s
sys	0m45.859s
```

And  "c2d" singularity

```console
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-kripke-cpu_c2d.sif kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
TIMER_NAMES:Generate,LPlusTimes,LTimes,Population,Scattering,Solve,Source,SweepSolver,SweepSubdomain
TIMER_DATA:0.169121,2.694554,8.321639,0.058425,92.294044,108.623195,0.005598,2.720175,0.254447

Figures of Merit
================

  Throughput:         8.277734e+06 [unknowns/(second/iteration)]
  Grind time :        1.208060e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  9.35405 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m53.195s
user	101m23.758s
sys	0m45.484s
```
