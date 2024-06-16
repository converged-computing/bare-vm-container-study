#!/bin/bash

# RECOMMENDED to use screen
# screen /bin/bash
# I wanted to use ubuntu 22.04 instead of container os so we install docker

sudo apt-get update && \
sudo apt-get install ca-certificates curl && \
sudo install -m 0755 -d /etc/apt/keyrings && \
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && \
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo groupadd docker
sudo usermod -aG docker $USER

# Then log in and out

# Login to ghcr.io
docker login ghcr.io

# Clone the container builds
git clone https://github.com/converged-computing/bare-vm-container-study

# amg2023
cd bare-vm-container-study/docker
cd amg2023
docker build  -t ghcr.io/converged-computing/metric-amg2023:spack-c2d .
docker push ghcr.io/converged-computing/metric-amg2023:spack-c2d

# kripke
cd ../kripke
docker build -t ghcr.io/converged-computing/metric-kripke-cpu:c2d .
docker push ghcr.io/converged-computing/metric-kripke-cpu:c2d

# Laghos
cd ../laghos
docker build -t ghcr.io/converged-computing/metric-laghos:c2d .
docker push ghcr.io/converged-computing/metric-laghos:c2d

# LAMMPS
cd ../lammps
docker build -t ghcr.io/converged-computing/metric-lammps-cpu:c2d .
docker push ghcr.io/converged-computing/metric-lammps-cpu:c2d

# Linpack
cd ../linpack
docker build -t ghcr.io/converged-computing/metric-linpack-cpu:c2d .
docker push ghcr.io/converged-computing/metric-linpack-cpu:c2d

# Minife
cd ../minife
docker build -t ghcr.io/converged-computing/metric-minife:c2d .
docker push ghcr.io/converged-computing/metric-minife:c2d

# Mixbench
cd ../mixbench
docker build -t ghcr.io/converged-computing/metric-mixbench:c2d .
docker push ghcr.io/converged-computing/metric-mixbench:c2d

# mt-gem
cd ../mt-gemm-base
docker build -t ghcr.io/converged-computing/mt-gemm:c2d .
docker push ghcr.io/converged-computing/mt-gemm:c2d

# Nek5000
cd ../nek5000
docker build -t ghcr.io/converged-computing/metric-nek5000:c2d .
docker push ghcr.io/converged-computing/metric-nek5000:c2d

# OSU
cd ../osu
docker build -t ghcr.io/converged-computing/metric-osu-cpu:c2d .
docker push ghcr.io/converged-computing/metric-osu-cpu:c2d

# pennant
cd ../pennant
docker build -t ghcr.io/converged-computing/metrics-pennant:c2d .
docker push ghcr.io/converged-computing/metrics-pennant:c2d

# Quicksilver
cd ../quicksilver
docker build -t ghcr.io/converged-computing/metric-quicksilver-cpu:c2d .
docker push ghcr.io/converged-computing/metric-quicksilver-cpu:c2d

# Resnet(requires different base / GPU)
# cd ../resnet
# docker build -t ghcr.io/converged-computing/pytorch-resnet-experiment:c2d .
# docker push ghcr.io/converged-computing/pytorch-resnet-experiment:c2d

# stream
cd ../stream
docker build -t ghcr.io/converged-computing/metric-stream:c2d .
docker push ghcr.io/converged-computing/metric-stream:c2d
