# Containers

## Local Machine

These are containers that have been built on my local machine.

| Container                                                      | Cloud      | Dockerfile                          | Notes             |
|----------------------------------------------------------------|-----------|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu | Google |[Dockerfile](amg2023) |  |
| ghcr.io/converged-computing/metric-lammps-cpu             | Google |[Dockerfile](lammps) | |
| ghcr.io/converged-computing/metric-kripke-cpu             | Google |[Dockerfile](kripke)  | |
| ghcr.io/converged-computing/metric-laghos:cpu             | Google |[Dockerfile](laghos)  | |
| ghcr.io/converged-computing/metric-minife:cpu             | Google |[Dockerfile](minife)  | | 
| ghcr.io/converged-computing/metric-mixbench:cpu           | Google |[Dockerfile](mixbench)| |
| ghcr.io/converged-computing/metric-nek5000:cpu            | Google |[Dockerfile](nek5000) | |
| ghcr.io/converged-computing/metric-osu-cpu                | Google |[Dockerfile](osu) | |
| ghcr.io/converged-computing/metric-quicksilver-cpu        | Google |[Dockerfile](quicksilver) | |
| ghcr.io/converged-computing/metric-stream:cpu             | Google |[Dockerfile](stream) | |
| ghcr.io/converged-computing/mt-gemm:cpu                   | Google |[Dockerfile](mt-gemm-base)| |
| ghcr.io/converged-computing/metric-linpack-cpu            | Google |[Dockerfile](linpack) | |  
| ghcr.io/converged-computing/metrics-pennant:cpu           | Google |[Dockerfile](pennant) | |  

## c2d-standard family

These containers have been built on c2d-standard with ubuntu 22.04. See [build-c2d.sh](build-c2d.sh) that was run on:

- Instance: c2d-standard-56
- Type: New balanced persistent disk
- Size: 100 GB
- Image: Ubuntu 22.04 LTS

| Container                                                 | Cloud      | Dockerfile                          | Notes             |
|-----------------------------------------------------------|-----------|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-amg2023:spack-c2d      | Google |[Dockerfile](amg2023) |  |
| ghcr.io/converged-computing/metric-lammps-cpu:c2d         | Google |[Dockerfile](lammps) | |
| ghcr.io/converged-computing/metric-kripke-cpu:c2d         | Google |[Dockerfile](kripke)  | |
| ghcr.io/converged-computing/metric-laghos:c2d             | Google |[Dockerfile](laghos)  | |
| ghcr.io/converged-computing/metric-minife:c2d             | Google |[Dockerfile](minife)  | | 
| ghcr.io/converged-computing/metric-mixbench:c2d           | Google |[Dockerfile](mixbench)| |
| ghcr.io/converged-computing/metric-nek5000:c2d            | Google |[Dockerfile](nek5000) | |
| ghcr.io/converged-computing/metric-osu-cpu:c2d            | Google |[Dockerfile](osu) | |
| ghcr.io/converged-computing/metric-quicksilver-cpu:c2d    | Google |[Dockerfile](quicksilver) | |
| ghcr.io/converged-computing/metric-stream:c2d             | Google |[Dockerfile](stream) | |
| ghcr.io/converged-computing/mt-gemm:c2d                   | Google |[Dockerfile](mt-gemm-base)| |
| ghcr.io/converged-computing/metric-linpack-cpu:c2d        | Google |[Dockerfile](linpack) | |  
| ghcr.io/converged-computing/metrics-pennant:c2d           | Google |[Dockerfile](pennant) | |  


## hpc7g (arm)


- Instance: hpc7g
- Size: 200 GB
- Image: custom built ebpf (build instructions here)

| Container                                                 | Cloud      | Dockerfile                          | Notes             |
|-----------------------------------------------------------|-----------|------------------------------------|--------------------|
| ghcr.io/converged-computing/metric-amg2023:hpc7g            | AWS |[Dockerfile](amg2023/Dockerfile.arm) |  |
| ghcr.io/converged-computing/metric-lammps-cpu:hpc7g         | AWS |[Dockerfile](lammps/Dockerfile.arm) | |
| ghcr.io/converged-computing/metric-kripke-cpu:hpc7g         | AWS |[Dockerfile](kripke/Dockerfile.arm)  | |
| ghcr.io/converged-computing/metric-laghos:hpc7g             | AWS |[Dockerfile](laghos/Dockerfile.arm)  | |
| ghcr.io/converged-computing/metric-minife:hpc7g             | AWS |[Dockerfile](minife/Dockerfile.arm)  | | 
| ghcr.io/converged-computing/metric-mixbench:hpc7g           | AWS |[Dockerfile](mixbench/Dockerfile.arm)| |
| ghcr.io/converged-computing/metric-nek5000:hpc7g            | AWS |[Dockerfile](nek5000/Dockerfile.arm) | |
| ghcr.io/converged-computing/metric-osu-cpu:hpc7g            | AWS |[Dockerfile](osu/Dockerfile.arm) | |
| ghcr.io/converged-computing/metric-quicksilver-cpu:hpc7g    | AWS |[Dockerfile](quicksilver/Dockerfile.arm) | |
| ghcr.io/converged-computing/metric-stream:hpc7g             | AWS |[Dockerfile](stream/Dockerfile.arm) | |
| ghcr.io/converged-computing/mt-gemm:hpc7g                   | AWS |[Dockerfile](mt-gemm-base/Dockerfile.arm)| |
| ghcr.io/converged-computing/metric-linpack-cpu:hpc7g        | AWS |[Dockerfile](linpack/Dockerfile.arm) | |  
| ghcr.io/converged-computing/metrics-pennant:hpc7g           | AWS |[Dockerfile](pennant/Dockerfile.arm) | |  



