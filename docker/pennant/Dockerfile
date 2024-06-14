FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Build command
#  docker build -t ghcr.io/converged-computing/metrics-pennant:cpu .
#  docker build -t ghcr.io/converged-computing/metrics-pennant:c2d .

# Example command
# pennant /opt/pennant/test/sedovsmall/sedovsmall.pnt 

RUN apt-get update && \
    apt-get install -y fftw3-dev fftw3 pdsh libfabric-dev libfabric1 \
        openssh-client openssh-server \
        dnsutils telnet strace cmake git g++ \
        mpich unzip bzip2

WORKDIR /opt
RUN git clone https://github.com/lanl/PENNANT /opt/pennant
COPY ./Makefile /opt/pennant/Makefile
WORKDIR /opt/pennant
RUN make && mv ./build/pennant /usr/bin/pennant
EXPOSE 22
WORKDIR /opt/pennant/test
