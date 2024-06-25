FROM ubuntu:22.04

# docker build -t ebpf .

# These commands typically result in errors
# grep -i BPF /boot/config-`uname -r`
# sudo apt-get install -y bpfcc-tools libbpfcc libbpfcc-dev linux-headers-$(uname -r)

RUN apt-get update && \
    apt-get install -y \
      arping \
      bison \
      build-essential \
      clang \
      cmake \
      flex \
      git \
      iperf3 \
      kmod \
      libcereal-dev \
      libedit-dev \
      libpcap-dev \ 
      llvm \
      llvm-dev \
      libclang-dev \
      linux-headers-$(uname -r) \      
      netperf \
      python3-pip \
      zlib1g-dev \
      libelf-dev \
      zip && \
      apt-get clean

RUN git clone https://github.com/iovisor/bcc /opt/bcc 
WORKDIR /opt/bcc
RUN mkdir build && \
    cd build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr && \
    make && make install && \
    cp -r /opt/bcc/build/src/python/bcc-python3/bcc/ /usr/lib/python3/dist-packages/bcc/

RUN git clone --depth 1 https://github.com/libbpf/libbpf /opt/libbpf && \
    cd /opt/libbpf/src && \
    make install

RUN git clone https://github.com/bpftrace/bpftrace /opt/bpftrace && \
    cd /opt/bpftrace && \
    mkdir build && \
    cmake -B ./build -DBUILD_TESTING=OFF && \
    make -C ./build && \
    make -C ./build/ install

# Add to LD_LIBRARY_PATH (for one off use)
ENV LD_LIBRARY_PATH=/opt/libbpf/src:$LD_LIBRARY_PATH
RUN cp /opt/libbpf/src/*.so /usr/lib/ && ldconfig
