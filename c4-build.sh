#!/bin/bash

# This is on a c4 preview instance
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

# Install bcc 
sudo apt-get install -y bpfcc-tools libbpfcc libbpfcc-dev linux-headers-$(uname -r)
sudo chown -R $USER /opt
git clone https://github.com/iovisor/bcc /opt/bcc
sudo ln -s /usr/bin/python3 /usr/bin/python

# Login to ghcr.io
docker login ghcr.io

# Clone the container builds
git clone https://github.com/converged-computing/bare-vm-container-study

# You probably want to use screen
# screen /bin/bash

# amg2023
cd bare-vm-container-study/docker
cd amg2023
docker build --network host -t ghcr.io/converged-computing/metric-amg2023:spack-c4 .
docker push ghcr.io/converged-computing/metric-amg2023:spack-c4

# kripke
cd ../kripke
docker build --network host -t ghcr.io/converged-computing/metric-kripke-cpu:c4 .
docker push ghcr.io/converged-computing/metric-kripke-cpu:c4

# Laghos
cd ../laghos
docker build --network host -t ghcr.io/converged-computing/metric-laghos:c4 .
docker push ghcr.io/converged-computing/metric-laghos:c4

# LAMMPS
cd ../lammps
docker build --network host -t ghcr.io/converged-computing/metric-lammps-cpu:c4 .
docker push ghcr.io/converged-computing/metric-lammps-cpu:c4

# Linpack
cd ../linpack
docker build --network host -t ghcr.io/converged-computing/metric-linpack-cpu:c4 .
docker push ghcr.io/converged-computing/metric-linpack-cpu:c4

# Minife
cd ../minife
docker build --network host -t ghcr.io/converged-computing/metric-minife:c4 .
docker push ghcr.io/converged-computing/metric-minife:c4

# Mixbench
cd ../mixbench
docker build --network host -t ghcr.io/converged-computing/metric-mixbench:c4 .
docker push ghcr.io/converged-computing/metric-mixbench:c4

# mt-gem
cd ../mt-gemm-base
docker build --network host -t ghcr.io/converged-computing/mt-gemm:c4 .
docker push ghcr.io/converged-computing/mt-gemm:c4


# Nek5000
cd ../nek5000
docker build --network host -t ghcr.io/converged-computing/metric-nek5000:c4 .
docker push ghcr.io/converged-computing/metric-nek5000:c4

# OSU
cd ../osu
docker build --network host -t ghcr.io/converged-computing/metric-osu-cpu:c4 .
docker push ghcr.io/converged-computing/metric-osu-cpu:c4

# pennant
cd ../pennant
docker build --network host -t ghcr.io/converged-computing/metrics-pennant:c4 .
docker push ghcr.io/converged-computing/metrics-pennant:c4

# Quicksilver
cd ../quicksilver
docker build --network host -t ghcr.io/converged-computing/metric-quicksilver-cpu:c4 .
docker push ghcr.io/converged-computing/metric-quicksilver-cpu:c4

# Resnet(requires different base / GPU)
# cd ../resnet
# docker build -t ghcr.io/converged-computing/pytorch-resnet-experiment:c2d .
# docker push ghcr.io/converged-computing/pytorch-resnet-experiment:c2d

# stream
cd ../stream
docker build --network host -t ghcr.io/converged-computing/metric-stream:c4 .
docker push ghcr.io/converged-computing/metric-stream:c4
