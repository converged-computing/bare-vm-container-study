# Bare Metal (VM) vs. Container

We want to test the difference between:

 - building an application on bare metal
 - building with a container on the same instruction set (the instance)
 - building with a container on a different instruction set (my host)
 - for each container build:
   - running on bare metal
   - running with singularity
   - running with docker

 - [docker](docker): includes Docker builds for:
  - host machine "a different machines" instances for 14 applications
  - a similar build script [c2d-build.sh](c2d-build.sh) to build the "same" containers on c2d instances (I don't expect these to be different)
 - [bare-vm](bare-vm): includes a monster script for that combines each previous docker build to build on bare metal, along with installing Singularity.
 - [experiment](experiment): runs the experiment, once all the software is ready!
 
I was going to add Podman, but I think I hate it too much and I'm worried it has a conflicting dependency with docker.
I'm going to be consistent and build flux / mpi into the containers. I don't know if I'll wind up using flux or MPI
to run on one node, but it's worth having it.

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](https://github.com/converged-computing/cloud-select/blob/main/LICENSE),
[COPYRIGHT](https://github.com/converged-computing/cloud-select/blob/main/COPYRIGHT), and
[NOTICE](https://github.com/converged-computing/cloud-select/blob/main/NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614

