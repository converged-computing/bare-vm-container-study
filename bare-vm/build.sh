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
    software-properties-common

# spack concretization will fail without clingo
sudo apt-get install -y python3-pip
sudo pip3 install clingo

# What we want to install and how we want to install it
# is specified in a manifest file (spack.yaml)
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
    curl \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Finally, install oras for saving artifacts
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
# export VERSION=1.21.0 OS=linux ARCH=amd64
# wget https://dl.google.com/go/go$VERSION.$OS-$ARCH.tar.gz
# sudo tar -C /usr/local -xzvf go$VERSION.$OS-$ARCH.tar.gz
# rm go$VERSION.$OS-$ARCH.tar.gz

# echo 'export PATH=/usr/local/go/bin:$PATH' >> ~/.bashrc
# . ~/.bashrc

# export VERSION=4.0.1
# export PATH=/usr/local/go/bin:$PATH
# wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz
# tar -xzf singularity-ce-${VERSION}.tar.gz
# cd singularity-ce-${VERSION}

# ./mconfig
# make -C builddir
# sudo make -C builddir install

# SINGULARITY

sudo apt-get install -y fuse2fs
wget https://github.com/sylabs/singularity/releases/download/v4.1.3/singularity-ce_4.1.3-jammy_amd64.deb
sudo dpkg -i singularity-ce_4.1.3-jammy_amd64.deb

# LAMMPS
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

sudo apt-get update
sudo apt-get -qq install -y \
	libboost-graph-dev \
	libboost-system-dev \
	libboost-filesystem-dev \
	libboost-regex-dev \
	libyaml-cpp-dev \
	libedit-dev \
        libboost-dev \
        libyaml-cpp-dev \
	curl

export CMAKE=3.23.1
curl -s -L https://github.com/Kitware/CMake/releases/download/v$CMAKE/cmake-$CMAKE-linux-x86_64.sh > cmake.sh && \
    sudo sh cmake.sh --prefix=/usr/local --skip-license
    
sudo apt-get install -y  libyaml-cpp-dev libedit-dev
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

# Install kripke
export PATH=$PATH:/opt/Kripke/build/bin:$PATH
echo "export PATH=$PATH:/opt/Kripke/build/bin:$PATH" >> ~/.bashrc

# Laghos
cd /opt
export MAKE_CXX_FLAG="MPICXX=mpic++"

# Install hypre
sudo apt-get install -y libc6-dev && \
    export hypre_options="--disable-fortran --without-fei" && \
    wget --no-verbose https://github.com/hypre-space/hypre/archive/v2.11.2.tar.gz && \
    tar -xzf v2.11.2.tar.gz && \
    mv hypre-2.11.2 hypre && \
    cd hypre/src && \
   ./configure ${hypre_options} CC=mpicc CXX=mpic++ && \
    make && sudo make install

unset MAKE_CXX_FLAG

# Metis
cd /opt
wget --no-verbose http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/OLD/metis-4.0.3.tar.gz && \
    tar -xzf metis-4.0.3.tar.gz && \
    mv metis-4.0.3 metis-4.0 && \
    make -C metis-4.0/Lib CC=mpicc OPTFLAGS="-Wno-error=implicit-function-declaration -O2"

cd /opt
git clone --single-branch --depth 1 https://github.com/mfem/mfem && \
#    unset LD_LIBRARY_PATH && \
    cd mfem && \
    make config MFEM_USE_MPI=YES MPICXX=mpiCC MFEM_MPI_NP=2 MFEM_DEBUG=${DEBUG} CPPFLAGS="${CPPFLAGS}" && \
    make

cd /opt       
git clone --depth 1 https://github.com/CEED/Laghos laghos
cd laghos && \ 
    make && sudo make install
