#!/bin/bash

# AMG2023
export DEBIAN_FRONTEND="noninteractive"
sudo apt-get update && \
sudo apt-get -y install \
    autotools-dev \
    autoconf \
    automake \
    cmake \
    git \
    python3 \
    dnsutils \
    libatomic1 \
    libnuma-dev \
    libgomp1 \
    openssh-server \
    openssh-client \
    apt-utils \
    gcc \
    unzip \
    gfortran \
    g++ \
    build-essential \
    python3-pip \
    software-properties-common

# spack concretization will fail without clingo
sudo pip3 install clingo

# This is a spack environment definition
sudo chown -R $USER /opt
mkdir /opt/spack-environment \
    &&  (echo "spack:" \
    &&   echo "  specs:" \
    &&   echo "  - openmpi@4.1.4 fabrics=ofi +legacylaunchers" \
    &&   echo "  - libfabric@1.19.0 fabrics=efa,tcp,udp,sockets,verbs,shm,mrail,rxd,rxm" \
    &&   echo "  - flux-sched" \
    &&   echo "  - flux-core" \
    &&   echo "  - pmix@4.2.2" \
    &&   echo "  - flux-pmix@0.4.0" \
    &&   echo "  - amg2023 +mpi" \
    &&   echo "  - hypre" \
    &&   echo "  concretizer:" \
    &&	 echo "    unify: true" \
    &&   echo "  config:" \
    &&   echo "    install_tree: /opt/software" \
    &&   echo "  view: /opt/view") > /opt/spack-environment/spack.yaml


cd /tmp
wget https://github.com/spack/spack/archive/refs/tags/v0.22.0.tar.gz && \
    tar -xzvf v0.22.0.tar.gz && \
    mv spack-0.22.0/ /opt/spack
 
# Install the software, remove unnecessary deps
cd /opt/spack-environment \
    && git clone https://github.com/spack/spack.git \
    && . spack/share/spack/setup-env.sh \
    && spack env activate . \
    && spack external find openssh \
    && spack external find cmake \
    && spack install --reuse --fail-fast \
    && spack gc -y

cd /opt

sudo apt-get update && \
sudo apt-get -y install \
    libatomic1 \
    libnuma-dev \
    libgomp1 \
    ca-certificates \
    openssh-server \
    openssh-client \
    dnsutils \
    curl

# oras for saving artifacts
cd /tmp
export VERSION="1.1.0" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    sudo mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/
cd -    
    
# Singularity
sudo apt-get update && \
sudo apt-get install -y \
   autoconf \
   automake \
   cryptsetup \
   git \
   libfuse-dev \
   libglib2.0 \
   libglib2.0-dev \
   libseccomp-dev \
   libtool \
   pkg-config \
   runc \
   squashfs-tools \
   squashfs-tools-ng \
   uidmap \
   wget \
   zlib1g-dev
   
# Go
export VERSION=1.21.0 OS=linux ARCH=amd64
wget https://dl.google.com/go/go$VERSION.$OS-$ARCH.tar.gz
sudo tar -C /usr/local -xzvf go$VERSION.$OS-$ARCH.tar.gz
rm go$VERSION.$OS-$ARCH.tar.gz

echo 'export PATH=/usr/local/go/bin:$PATH' >> ~/.bashrc
. ~/.bashrc

export VERSION=4.0.1
export PATH=/usr/local/go/bin:$PATH
wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz
tar -xzf singularity-ce-${VERSION}.tar.gz
cd singularity-ce-${VERSION}

./mconfig
make -C builddir
sudo make -C builddir install

# Singularity (if you want another way)
# sudo apt-get install -y fuse2fs
# wget https://github.com/sylabs/singularity/releases/download/v4.1.3/singularity-ce_4.1.3-jammy_amd64.deb
# sudo dpkg -i singularity-ce_4.1.3-jammy_amd64.deb

# LAMMPS
# This is the first "flux base" so we install all-the-things that are shared between the
# rest of the containers
# data: oras pull ghcr.io/converged-computing/metric-lammps-cpu:libfabric-data
sudo apt-get update && \
    sudo apt-get -qq install -y \
        apt-utils \
        locales \
        ca-certificates \
        wget \
        man \
        git \
        flex \
        ssh \
        sudo \
        vim \
        luarocks \
        munge \
        lcov \
        ccache \
        lua5.2 \
        python3-dev \
        python3-pip \
        valgrind \
        jq && \
   sudo rm -rf /var/lib/apt/lists/*

# Compilers, autotools
sudo apt-get update && \
    sudo apt-get -qq install -y \
        build-essential \
        pkg-config \
        autotools-dev \
        libtool \
	libffi-dev \
        autoconf \
        automake \
        make \
        clang \
        clang-tidy \
        gcc \
        g++ && \
   sudo rm -rf /var/lib/apt/lists/*

sudo pip3 install --upgrade --ignore-installed \
        "markupsafe==2.0.0" \
        coverage cffi ply six pyyaml "jsonschema>=2.6,<4.0" \
        sphinx sphinx-rtd-theme sphinxcontrib-spelling 
        
sudo apt-get update && \
    sudo apt-get -qq install -y \
        libsodium-dev \
        libzmq3-dev \
        libczmq-dev \
        libjansson-dev \
        libmunge-dev \
        libncursesw5-dev \
        liblua5.2-dev \
        liblz4-dev \
        libsqlite3-dev \
        uuid-dev \
        libhwloc-dev \
        libs3-dev \
        libevent-dev \
        libarchive-dev \
        libpam-dev && \
    sudo rm -rf /var/lib/apt/lists/*

# Testing utils and libs
sudo apt-get update && \
    sudo apt-get -qq install -y \
        faketime \
        libfaketime \
        pylint \
        cppcheck \
        enchant-2 \
        aspell \
        aspell-en && \
    sudo rm -rf /var/lib/apt/lists/*

sudo locale-gen en_US.UTF-8
sudo luarocks install luaposix

# Install openpmix, prrte
mkdir -p /opt/prrte
git clone https://github.com/openpmix/openpmix.git && \
    git clone https://github.com/openpmix/prrte.git && \
    ls -l && \
    cd openpmix && \
    git checkout fefaed568f33bf86f28afb6e45237f1ec5e4de93 && \
    ./autogen.pl && \
    ./configure --prefix=/usr --disable-static && sudo make -j 4 install && \
    sudo ldconfig && \
    cd .. && \
    cd prrte && \
    git checkout 477894f4720d822b15cab56eee7665107832921c && \
    ./autogen.pl && \
    ./configure --prefix=/usr && sudo make -j 4 install && \
    cd ../.. && \
    rm -rf prrte

export LANG=C.UTF-8

export FLUX_SECURITY_VERSION=0.11.0

cd /opt
export CCACHE_DISABLE=1 && \
    V=$FLUX_SECURITY_VERSION && \
    PKG=flux-security-$V && \
    URL=https://github.com/flux-framework/flux-security/releases/download && \
    wget ${URL}/v${V}/${PKG}.tar.gz && \
    tar xvfz ${PKG}.tar.gz && \
    cd ${PKG} && \
    sudo ./configure --prefix=/usr --sysconfdir=/etc || cat config.log && \
    sudo make -j 4 && \
    sudo make install && \
    cd .. && \
    sudo rm -rf flux-security-*

# Setup MUNGE directories & key
sudo mkdir -p /var/run/munge && \
    sudo dd if=/dev/urandom bs=1 count=1024 > munge.key && \
    sudo mv munge.key /etc/munge/munge.key && \
    sudo chown -R munge /etc/munge/munge.key /var/run/munge && \
    sudo chmod 600 /etc/munge/munge.key

wget https://github.com/flux-framework/flux-core/releases/download/v0.61.2/flux-core-0.61.2.tar.gz && \
    tar xzvf flux-core-0.61.2.tar.gz && \
    cd flux-core-0.61.2 && \
    sudo ./configure --prefix=/usr --sysconfdir=/etc && \
    sudo make clean && \
    sudo make && \
    sudo make install


sudo apt-get update && \
sudo apt-get install -y \
	libboost-graph-dev \
	libboost-system-dev \
	libboost-filesystem-dev \
	libboost-regex-dev \
	libyaml-cpp-dev \
	libedit-dev \
        libboost-dev \
        libyaml-cpp-dev \
	curl

# I skipped this - we have it already 3.22.1
# export CMAKE=3.23.1
# curl -s -L https://github.com/Kitware/CMake/releases/download/v$CMAKE/cmake-$CMAKE-linux-x86_64.sh > cmake.sh && \
#    sudo sh cmake.sh --prefix=/usr/local --skip-license
    
sudo apt-get install -y  libyaml-cpp-dev libedit-dev && \
wget https://github.com/flux-framework/flux-sched/releases/download/v0.33.1/flux-sched-0.33.1.tar.gz && \
    tar -xzvf flux-sched-0.33.1.tar.gz && \
    cd flux-sched-0.33.1 && \
    sudo ./configure --prefix=/usr --sysconfdir=/etc && \
    sudo make && \
    sudo make install && \
    sudo ldconfig


sudo apt-get update && \
    sudo apt-get install -y fftw3-dev fftw3 pdsh libfabric-dev libfabric1 \
        openssh-client openssh-server \
        dnsutils telnet strace git g++ \
        unzip bzip2

cd /opt
wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.2.tar.gz && \
    tar -xzvf openmpi-4.1.2.tar.gz && \
    cd openmpi-4.1.2 && \
    ./configure && \
    make && sudo make install && sudo ldconfig

cd /opt
sudo python3 -m pip install clang-format && \
   git clone --depth 1 https://github.com/lammps/lammps.git && \
    cd lammps && \
    mkdir build && \
    cd build && \
    cmake \
  -D CMAKE_INSTALL_PREFIX=/usr \
  -D CMAKE_BUILD_TYPE=Release \
  -D MPI_CXX_COMPILER=mpicxx \
  -D BUILD_MPI=yes \
  -D PKG_ML-SNAP=yes \
  -D PKG_GPU=no \
  -D PKG_REAXFF=on \
  -D PKG_KOKKOS=yes \
  ../cmake && make && sudo make install
  
# Note that docker needs refresh
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Kripke
cd /opt
git clone https://github.com/LLNL/Kripke && \
    cd Kripke && \
    git submodule update --init --recursive && \
    mkdir build 


wget -O /opt/Kripke/host-configs/gke.cmake https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/kripke/gke.cmake
cd /opt/Kripke/build && \
    cmake  -C../host-configs/gke.cmake ../ && make && \
    mv /opt/Kripke/build/kripke.exe /opt/Kripke/build/bin/kripke

# install kripke
export PATH=$PATH:/opt/Kripke/build/bin:$PATH
echo "export PATH=$PATH:/opt/Kripke/build/bin:$PATH" >> ~/.bashrc

# laghos
cd /opt
export MAKE_CXX_FLAG="MPICXX=mpic++"

# hypre
sudo apt-get install -y libc6-dev && \
    export hypre_options="--disable-fortran --without-fei" && \
    wget --no-verbose https://github.com/hypre-space/hypre/archive/v2.11.2.tar.gz && \
    tar -xzf v2.11.2.tar.gz && \
    mv hypre-2.11.2 hypre && \
    cd hypre/src && \
   ./configure ${hypre_options} CC=mpicc CXX=mpic++ && \
    make && sudo make install

unset MAKE_CXX_FLAG

# metis
cd /opt
wget --no-verbose http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/OLD/metis-4.0.3.tar.gz && \
    tar -xzf metis-4.0.3.tar.gz && \
    mv metis-4.0.3 metis-4.0 && \
    make -C metis-4.0/Lib CC=mpicc OPTFLAGS="-Wno-error=implicit-function-declaration -O2"

cd /opt
git clone --single-branch --depth 1 https://github.com/mfem/mfem && \
    cd mfem && \
    make config MFEM_USE_MPI=YES MPICXX=mpiCC MFEM_MPI_NP=2 MFEM_DEBUG=${DEBUG} CPPFLAGS="${CPPFLAGS}" && \
    make

cd /opt       
git clone --depth 1 https://github.com/CEED/Laghos laghos
cd laghos && \ 
    make && sudo make install
sudo mv laghos /usr/local/bin/

# linpack/hpl
cd /opt
sudo apt-get update && sudo apt-get install -y libgtk2.0-dev \
    net-tools hwloc libhwloc-dev libevent-dev gfortran libopenblas-dev \
    bc

git clone --depth 1 https://github.com/ULHPC/tutorials /opt/tutorials && \
    mkdir -p /opt/hpl && \
    cd /opt/hpl && \
    ln -s /opt/tutorials/parallel/mpi/HPL ref.d && \
    ln -s ref.d/Makefile . && \   
    mkdir src && \
    cd src && \
    export HPL_VERSION=2.3 && \
    wget --no-check-certificate http://www.netlib.org/benchmark/hpl/hpl-${HPL_VERSION}.tar.gz && \
    tar xvzf hpl-${HPL_VERSION}.tar.gz && \
    mv hpl-${HPL_VERSION} /opt/hpl


cd /opt/hpl
wet -O ./Make.linux https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/linpack/Makefile
make arch=linux && \
 cd ./hpl-2.3 && \
 ./configure --prefix=/usr/local && \
 make && sudo make install

# which xhpl
export PATH=/opt/hpl/bin/linux:$PATH
echo "PATH=/opt/hpl/bin/linux:$PATH" >> ~/.bashrc

# miniFe
cd /opt
git clone https://github.com/Mantevo/minife
cd /opt/minife/openmp/src && make && sudo cp miniFE.x /usr/local/bin/miniFE.x

# mixbench
cd /opt
git clone https://github.com/ekondis/mixbench
cd /opt/mixbench/mixbench-cpu && \
    mkdir build && \
    cd build && \
    cmake ../ && \
    cmake --build ./ && make && \
    sudo cp mixbench-cpu /usr/local/bin

# gemm
# /usr/local/bin/1_dense_gemm_mpi
cd /opt
git clone https://repository.prace-ri.eu/git/CodeVault/hpc-kernels/dense_linear_algebra.git
cd /opt/dense_linear_algebra/gemm/mpi/src/
wget https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/mt-gemm-base/gemm_mpi.cpp
cd /opt/dense_linear_algebra/gemm/mpi && \
    mkdir build && cd build && \
    cmake ../ && make && sudo make install

# nekrs
cd /opt
export NRSCONFIG_NOBUILD=1
git clone https://github.com/Nek5000/nekRS nekrs && \
    cd nekrs && \
    sudo CC=mpicc CXX=mpic++ FC=mpif77 ./nrsconfig -DCMAKE_INSTALL_PREFIX=/usr && \
    sudo cmake --build ./build --target install     

export NEKRS_HOME=/usr
echo "export NEKRS_HOME=/usr" >> ~/.bashrc

# data for experiment
# oras pull ghcr.io/converged-computing/metric-nek5000:libfabric-cpu-data

# OSU
# benchmarks in:
# /opt/osu-benchmark/build.openmpi/pt2pt
# /opt/osu-benchmark/build.openmpi/collective
# /opt/osu-benchmark/build.openmpi/one-sided
# /opt/osu-benchmark/build.openmpi/startup

cd /opt/tutorials && \
    mkdir -p /opt/osu-benchmark && \
    cd /opt/osu-benchmark && \
    ln -s /opt/tutorials/parallel/mpi/OSU_MicroBenchmarks ref.d && \
    ln -s ref.d/Makefile . && \
    ln -s ref.d/scripts  . && \
    mkdir src && \
    cd src && \
    export OSU_VERSION=5.8 && \
    wget --no-check-certificate http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-${OSU_VERSION}.tgz && \
    tar xf osu-micro-benchmarks-${OSU_VERSION}.tgz && \
    cd /opt/osu-benchmark && \
    # Compile based on openmpi
    mkdir -p build.openmpi && cd build.openmpi && \
    ../src/osu-micro-benchmarks-${OSU_VERSION}/configure CC=mpicc CXX=mpicxx CFLAGS=-I$(pwd)/../src/osu-micro-benchmarks-${OSU_VERSION}/util --prefix=$(pwd) && \
    make && sudo make install

# Pennant
sudo apt-get update && \
    sudo apt-get install -y fftw3-dev fftw3 pdsh libfabric-dev libfabric1 \
        openssh-client openssh-server \
        dnsutils telnet strace cmake git g++ \
        unzip bzip2

cd /opt
git clone https://github.com/lanl/PENNANT /opt/pennant
cd /opt/pennant
rm Makefile
wget https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/pennant/Makefile
make && sudo mv ./build/pennant /usr/bin/pennant

# Quicksilver
cd /opt
git clone https://github.com/LLNL/Quicksilver quicksilver
cd /opt/quicksilver/src
rm Makefile
wget https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/quicksilver/Makefile
make && sudo cp qs /usr/bin/qs

mkdir -p /opt/stream
cd /opt/stream

# Being very lazy
wget https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/stream/src/Makefile
wget https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/stream/src/mysecond.c
wget https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/stream/src/stream.c
wget https://raw.githubusercontent.com/converged-computing/bare-vm-container-study/main/docker/stream/src/stream.f
sudo apt-get install -y gfortran && \
    make && sudo cp stream_c.exe /usr/local/bin && sudo cp stream_f.exe /usr/local/bin
