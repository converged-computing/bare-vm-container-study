#!/usr/bin/env python3

# This has exactly the functions we want to call written here, so our regular expression matches exactly
# them!

import argparse
import os
import re
import tempfile
import subprocess
import sys
import json
import time

from bcc import BPF

# This is the BPF program
# We are basically keeping track of start and end times
# and that way we can return an accumulated time.
# This is based on this example: https://github.com/iovisor/bcc/blob/master/tools/funclatency.py
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

// pid here is the host pid (with children)
struct stats_t {
    u64 time;
    u64 freq;
    u32 host_pid;
    u64 thread_pid;
};

// thread pid here is the host thread id (the child)
struct key_t {
    u64 ip;
    u32 host_pid;
    u64 thread_pid;
};

BPF_HASH(start, u64);
BPF_HASH(ipaddr, u64);
BPF_HASH(stats, struct key_t, struct stats_t);

int start_timing(struct pt_regs *ctx) {

    // This is the pid on the host.
    // https://mozillazg.com/2022/05/ebpf-libbpfgo-get-process-info-en.html
    u64 thread_pid = bpf_get_current_pid_tgid();
    u32 host_pid = bpf_get_current_pid_tgid() >> 32;
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u32 pid_tgid = task->real_parent->tgid;

    FILTER

    u64 timestamp = bpf_ktime_get_ns();

    // This is used later to look up function name
    u64 ip = PT_REGS_IP(ctx);
    
    // The single thread has to finish a function call before
    // doing another one
    ipaddr.update(&thread_pid, &ip);
    start.update(&thread_pid, &timestamp);
    return 0;
}

int stop_timing(struct pt_regs *ctx) {
    u64 *timestamp, delta;

    u64 thread_pid = bpf_get_current_pid_tgid();
    u32 host_pid = bpf_get_current_pid_tgid() >> 32;
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u32 pid_tgid = task->real_parent->tgid;

    FILTER

    // calculate delta time - this is the start
    timestamp = start.lookup(&thread_pid);

    // This means we missed the start
    if (timestamp == 0) {
        return 0;
    }

    // Convert from nano to microseconds
    delta = bpf_ktime_get_ns() - *timestamp;
    
    // Convert nanoseconds to microseconds
    // I think nanonseconds gives us up to 600 years
    // 2^64 / 10^9 (number of seconds) / 3600 (hours) / 24 (days) / 365 (years)
    // delta /= 1000;
    
    // Make more room!
    start.delete(&thread_pid);

    u64 ip, *ipp = ipaddr.lookup(&thread_pid);
    if (ipp) {
        ip = *ipp;

        // Make the key associated with the ip and thread pid
        // Those should be unique to the map for a call
        struct key_t skey = {};
        skey.host_pid = host_pid;
        skey.thread_pid = thread_pid;
        skey.ip = ip;   

        struct stats_t *stat = stats.lookup(&skey);
        if (stat) {
            stat->time += delta;
            stat->freq++;
        } else {
            struct stats_t s = {};
            s.time = delta;
            s.freq = 1;
            s.thread_pid = thread_pid;
            s.host_pid = host_pid;
            stats.update(&skey, &s);
        }
        ipaddr.delete(&thread_pid);
    }
    return 0;
}
"""


def read_file(path):
    with open(path, "r") as fd:
        content = fd.read()
    return content


def write_file(path, content):
    """
    Write content to file.
    """
    with open(path, "w") as fd:
        fd.write(content)


def get_parser():
    parser = argparse.ArgumentParser(
        description="Time functions and print time spent in each function",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", help="function file with kprobe list")
    return parser

# These functions interfere with lammps running:
skips = ["decay_load"]
skips_regex = "(%s)" % "|".join(skips)


wrapper_template = """#!/bin/bash

echo "Program running has pid $$"

# This is probably too big, be conservative
sleep 5

# This ensures our command inherits the same parent id
exec %s
"""


def get_tmpfile():
    """
    Get a temporary file name
    """
    tmpdir = tempfile.gettempdir()
    temp_name = "wrapper-" + next(tempfile._get_candidate_names()) + ".sh"
    return os.path.join(tmpdir, temp_name)


def read_kprobes(args):
    """
    Read n kprobes and form regular expression
    Don't use private functions
    """
    kprobes = [
        x.replace("kprobe:", "", 1) for x in read_file(args.file).split("\n") if x
    ]
    kprobes = [x for x in kprobes if not x.startswith("_") and not re.search(skips_regex, x)]
    if not kprobes:
        sys.exit("No kprobes found after filter.")
    print(f"Looking at {len(kprobes)} contenders...")
    return kprobes


def add_filter(pid):
    """
    Add a filter to a tgid (thread group id) based on
    a program pid. A group of pids can belong to a tgid,
    and usually the first is the tgid. We can use a function
    to derive it.
    """
    return bpf_text.replace("FILTER", f"if (pid_tgid != {pid})" + "{ return 0; }")


def main():
    """
    Run the ebpf program. Usage:

    sudo -E python3 time-calls.py sleep 10
    """
    parser = get_parser()
    args, command = parser.parse_known_args()

    # If we don't have a command or pid, no go
    if not command:
        sys.exit("We need a command to follow the script, bro-shizzle.")

    if not args.file:
        sys.exit("Please provide a --file with one kprobe per line.")

    print(f"👉️  Input: {args.file}")

    # Prepare the wrapper template for our program
    wrapper = wrapper_template % " ".join(command)
    print(wrapper)
    tmp_file = get_tmpfile()
    write_file(tmp_file, wrapper)

    command = ["/bin/bash", tmp_file]
    start = time.time()
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    program_text = add_filter(p.pid)
    print(f"👀️ Watching pid {p.pid}...")

    # Read in kprobes
    kprobes = read_kprobes(args)

    # Load the ebpf program
    program = BPF(text=program_text)

    # patterns should be regular expression oriented
    pattern = "^(" + "|".join(kprobes) + ").*$"
    program.attach_kprobe(event_re=pattern, fn_name="start_timing")
    program.attach_kretprobe(event_re=pattern, fn_name="stop_timing")

    # This tells us the number of kprobes we match
    matched = program.num_open_kprobes()

    # This should not happen
    if matched == 0:
        sys.exit('0 functions matched by "{pattern}". Exiting.')

    end = time.time()
    elapsed = end - start
    print(f"Setting up eBPF took {elapsed} seconds.")

    # We have to divide by two since we have a start/stop
    number_functions = int(matched / 2)
    print(f"Timing {number_functions} functions.")

    # Wait for the application to finish running
    print()

    # Wait for application to finish running
    p.wait()

    # Print output - for the experiments we will save it to file
    # Better would be to open an sqlite database, and save to a table
    # based on the program, pid, and iteration.
    out, err = p.communicate()
    if p.returncode == 0:
        out = out.decode("utf-8")
        print(out)
        print("Run was successful.")
    else:
        err = err.decode("utf-8")
        print(err)
        print("Run was not successful.")

    print()
    print("%-36s %8s %16s" % ("FUNC", "COUNT", "TIME (nsecs)"))

    # Get a table from the program to print to the terminal
    stats = program.get_table("stats")
    results = []
    for k, v in stats.items():
        function = BPF.sym(k.ip, -1).decode("utf-8")
        results.append(
            {
                "thread_pid": v.thread_pid,
                "host_pid": v.host_pid,
                "func": function,
                "count": v.freq,
                "time_ns": v.time,
            }
        )
        print("%-36s %8s %16s" % (function, v.freq, v.time))
    print("\n=== RESULTS START")
    print(json.dumps(results))
    print("=== RESULTS END")
    stats.clear()

    # In case someone deleted it...
    if os.path.exists(tmp_file):
        os.remove(tmp_file)


if __name__ == "__main__":
    main()
