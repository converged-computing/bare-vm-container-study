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
