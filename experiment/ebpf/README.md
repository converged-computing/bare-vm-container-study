# Testing eBPF

This will be the eBPF portion of the experiment. For learning and how I arrived here, see [learning](learning).

## Automating Discovery

You can use the [LIMA](https://github.com/lima-vm/lima) virtual machine to do this, and you'll need to install your application there. 

```bash
limactl start ./ebpf.yaml
limactl shell ebpf
```

If you need more extensive resources, you need to setup this same suite and your application on those resources. Once you have that, here is a simple way to automate what I did manually. First, define your command.

```bash
command="sleep 2"
```

Then make a directory where we will put files for each set of N linux probes. We can measure up to 1K at once, so let's do 800 in each set.

```bash
mkdir kprobes
cd kprobes
sudo -E bpftrace -l | grep "kprobe:" | split --lines=600 - kprobes.
cd ../
```

This will create files in the PWD. Note that in the last line above we go back up! For the loop below, you can find [determine-kprobes.py](scripts/determine-kprobes.py) in the scripts directory here.

```bash
# Save the time when we start
date > start-time.txt

for filename in $(ls kprobes)
  do
  echo $filename
  time sudo -E python3 determine-kprobes.py --file kprobes/$filename $command
done
# Print the time when you finish
date
```

In the above, we write all the kprobes to temporary files, and remove them as we finish and append output to our matches file (`--out`) that defaults to `kprobes-present.txt` in the present working directory. If you want to cleanup as you go, then remove the temporary files after you use them. Otherwise, move them somewhere else. This exercise runs 69 files with 800 kprobes each.

## Preparing Application Function Sets

Ensure you've prepared the kprobes directory first (above).
We will want to run each application in a container and on bare metal to compare. 
Let's also make an application kprobes directory.

```bash
mkdir -p applications
```

### Lammps

```bash
singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:hpc7g
oras pull ghcr.io/converged-computing/metric-lammps-cpu:libfabric-data
```

Clone the repository and branch with our code.

```bash
git clone -b update-hari https://github.com/converged-computing/bare-vm-container-study
cp bare-vm-container-study/experiment/ebpf/scripts/determine-kprobes.py .
```

Prepare the kprobes. Note that we can run 1000 at once, but I'm being super conservative here, since the kernel VM is limited in space.

```bash
mkdir kprobes
cd kprobes
sudo -E bpftrace -l | grep "kprobe:" | split --lines=200 - kprobes.
cd ../
```

#### Kprobes for LAMMPS

```console
cd common

for filename in $(ls kprobes)
  do
  echo $filename
  time sudo -E python3 determine-kprobes.py --file kprobes/$filename --out ../applications/lammps-bare-metal.txt /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):64 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000
  time sudo -E python3 determine-kprobes.py --file kprobes/$filename --out ../applications/lammps-singularity.txt /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):64 singularity exec ../metric-lammps-cpu_hpc7g.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000
done
# Print the time when you finish
date
```

#### Experiment Runs for LAMMPS

We are going to make a directory just for lammps input files. Since this set needs to run 2/recording, we will try for 400 total.
The files will be prefixed based on the application, and numbered so we can use the filename in the output.

```console
mkdir kprobes
cd kprobes
cat ../applications/lammps-bare-metal.txt ../applications/lammps-singularity.txt | uniq | sort | split --numeric-suffixes=1 --lines=200 - lammps.
cd ../
```

And then to run lammps across sizes. We do 32 iterations to approach normal.

```bash
# bare metal times:
# 64: 4 seconds
# 32: 8 seconds
# 16: 15 seconds
# This is for ring buffers
cd common/
results=../results/lammps/bare-metal
sresults=../results/lammps/singularity
mkdir -p ${results} ${sresults}
for iter in $(seq 6 32); do
  for filename in $(ls ../kprobes); do
      for proc in 16 32 64; do
       prefix="${results}/group-${filename}-size-${proc}-iter-${iter}"
       if [[ ! -f "${prefix}.out" ]]; then
         time sudo -E python3 ./wrapped-time-ring-buffers.py --file ../kprobes/$filename --outfile ${prefix}.pfw /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out
         ps -aef | grep mpirun | awk {'print $2'} | xargs sudo kill -9 || echo "mpirun already killed"
         sudo pkill -9 starter || echo "starter already killed"
       fi
       prefix="${sresults}/group-${filename}-size-${proc}-iter-${iter}"
       if [[ ! -f "${prefix}.out" ]]; then
         time sudo -E python3 ./wrapped-time-ring-buffers.py --file ../kprobes/$filename --outfile ${prefix}.pfw /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_hpc7g.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out
         ps -aef | grep mpirun | awk {'print $2'} | xargs sudo kill -9 || echo "mpirun already killed"
         sudo pkill -9 singularity || echo "singularity already killed"
         sudo pkill -9 starter || echo "starter already killed"
      fi
      done
   done
done
```

Other testing commands:

```
         time sudo -E python3 ./wrapped-time-ring-buffers.py --file ../kprobes/$filename --outfile ${prefix}.pfw /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out


         time sudo -E python3 ../wrapped-time.py --file ../kprobes/$filename /opt/amazon/openmpi/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out

         time sudo -E python3 ./ring-buffers/main.py --so-path ./ring-buffers/build/libtracer_ebpf.so --file ../kprobes/$filename --outfile ${prefix}.pfw /opt/amazon/openmpi/bin/mpirun --allow-run-as-root --host $(hostname):$proc -x LD_PRELOAD=./ring-buffers/build/libtracer_ebpf.so lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out

# This is for wrapped-time.py, no ring buffers
cd common/
results=../results/lammps/bare-metal
sresults=../results/lammps/singularity
mkdir -p ${results} ${sresults}
for iter in $(seq 1 5); do
  for filename in $(ls ../kprobes); do
      for proc in 16 32 64; do
       prefix="${results}/group-${filename}-size-${proc}-iter-${iter}"
       if [[ ! -f "${prefix}.out" ]]; then
         time sudo -E python3 ../wrapped-time.py --file ../kprobes/$filename /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out
       fi
       prefix="${sresults}/group-${filename}-size-${proc}-iter-${iter}"
       if [[ ! -f "${prefix}.out" ]]; then
         time sudo -E python3 ../wrapped-time.py --file ../kprobes/$filename /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_hpc7g.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out
      fi
      done
   done
done


# This is for without ebpf
cd common/
results=../results/lammps-no-ebpf/bare-metal
sresults=../results/lammps-no-ebpf/singularity
mkdir -p ${results} ${sresults}
for iter in $(seq 1 105); do
    for proc in 16 32 64; do
       prefix="${results}/group-${filename}-size-${proc}-iter-${iter}"
       if [[ ! -f "${prefix}.out" ]]; then
         time sudo -E /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out
       fi
       prefix="${sresults}/group-${filename}-size-${proc}-iter-${iter}"
       if [[ ! -f "${prefix}.out" ]]; then
         time sudo -E /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_hpc7g.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out
      fi
    done
done


mkdir group4
cd kprobes
cat ../kprobes/lammps.04 | split --lines=10 - group.04.
cd ../


# Doing just one file
cd common/
for iter in $(seq 1); do
    for proc in 64; do
      for func in $(cat ../kprobes/lammps.04); do
       prefix="test/${func}"
       if [[ ! -f "${prefix}.out" ]]; then
       echo "$func" > ./function.txt
       time sudo -E python3 ./wrapped-time-ring-buffers.py --file function.txt --outfile ${prefix}.pfw /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_hpc7g.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${prefix}.out
       ps -aef | grep mpirun | awk {'print $2'} | xargs sudo kill -9
       sudo pkill -9 singularity
       sudo pkill -9 starter
       fi
      done
    done
done

```

#### AMG2023

```bash
singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu
```

Since this container requires sourcing spack, we need to write a bash script to run on the host.

```bash
#!/bin/bash
# run_amg.sh
. /etc/profile.d/z10_spack_environment.sh
amg -P 8 6 4 -n 64 64 128
```

```console
date > start-time.txt
app=amg

for filename in $(ls kprobes)
  do
  echo $filename
  time sudo -E python3 determine-kprobes.py --file kprobes/$filename --out applications/$app-singularity.txt /usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 singularity exec metric-amg2023_spack-slim-cpu.sif /bin/bash ./run_amg.sh
done

# Print the time when you finish
date

```

We will do the spack environment separately.

```
cd /opt/spack-environment/spack.yaml
spack env activate .
cd -
```

Generate the kprobes files again, then:


```console
date > start-time.txt
app=amg

for filename in $(ls kprobes)
  do
  echo $filename
  time sudo -E python3 determine-kprobes.py --file kprobes/$filename --out applications/$app-bare-metal.txt /opt/view/bin/mpirun --allow-run-as-root --host container-testing:56 /opt/view/bin/amg -P 2 4 7 -n 64 128 128

done

# Print the time when you finish
date
```

