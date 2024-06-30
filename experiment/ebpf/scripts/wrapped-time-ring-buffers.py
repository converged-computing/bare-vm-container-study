#!/usr/bin/env python3

import argparse
import ctypes
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta

from bcc import BPF

INTERVAL_VALUE = 1e9  # this is 1 second

# This is the BPF program
# We are basically keeping track of start and end times
# and that way we can return an accumulated time.
# This is based on this example: https://github.com/iovisor/bcc/blob/master/tools/funclatency.py
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct stats_key_t {
    u64 interval;
    u32 pid_tgid;
    u32 host_pid;
    u64 ip;
};

struct stats_t {
    u64 time;
    u64 freq;
};
struct event_t {
    u64 interval;
    u32 pid_tgid;
    u32 host_pid;
    u64 ip;
    u64 time;
    u64 freq;
};

struct func_t {
    u64 ts;
    u64 ip;
};
BPF_HASH(ip_map, u32, struct func_t);
BPF_HASH(stats_map, struct stats_key_t, struct stats_t);
BPF_RINGBUF_OUTPUT(events, 2 << 16);

int start_timing(struct pt_regs *ctx) {

    // This is the pid on the host.
    // https://mozillazg.com/2022/05/ebpf-libbpfgo-get-process-info-en.html
    u32 host_pid = bpf_get_current_pid_tgid() >> 32;
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u32 pid_tgid = task->real_parent->tgid;

    FILTER

    struct func_t func = {};
    func.ip =  PT_REGS_IP(ctx);
    func.ts = bpf_ktime_get_ns();
    ip_map.update(&host_pid, &func);
    return 0;
}

int stop_timing(struct pt_regs *ctx) {
    u64 *tsp, delta;

    u32 host_pid = bpf_get_current_pid_tgid() >> 32;
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    u32 pid_tgid = task->real_parent->tgid;

    FILTER

    struct func_t *func = ip_map.lookup(&host_pid);
    
    // This means we missed the start
    if (func == 0) {
        return 0;
    }

    struct stats_key_t skey = {};
    skey.interval = func->ts / INTERVAL_VALUE;
    skey.pid_tgid = pid_tgid;
    skey.ip = func->ip;
    skey.host_pid = host_pid;

    struct stats_t zero = {};
    struct stats_t* stats = stats_map.lookup_or_init(&skey, &zero); 
    stats->time += bpf_ktime_get_ns() - func->ts;
    stats->freq++;

    if (skey.interval > 0) {
        // look for previous interval if present emit
        skey.interval--;
        stats = stats_map.lookup(&skey);
        if (stats != 0) {
            struct event_t event = {};
            event.interval = skey.interval;
            event.pid_tgid = skey.pid_tgid;
            event.host_pid = skey.host_pid;
            event.ip = skey.ip;
            event.time = stats->time;
            event.freq = stats->freq;
            events.ringbuf_output(&event, sizeof(struct event_t), 0);
            stats_map.delete(&skey);
        } 
    }
    ip_map.delete(&host_pid);
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
    parser.add_argument(
        "--outfile",
        help="Write matches to this output file",
        default="targeted_kprobes.pfw",
    )
    return parser


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
    kprobes = [x for x in kprobes if not x.startswith("_")]
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
    return bpf_text.replace(
        "FILTER", f"if (pid_tgid != {pid})" + "{ return 0; }"
    ).replace("INTERVAL_VALUE", str(int(INTERVAL_VALUE)))


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
    print(f"👉️ Output: {args.outfile}")

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
    print(f"Setting up eBPF took {end-start} seconds.")

    # We have to divide by two since we have a start/stop
    number_functions = int(matched / 2)
    print(f"Timing {number_functions} functions.")

    # Wait for the application to finish running
    print()

    last_updated = datetime.now()

    class Stats(ctypes.Structure):
        _fields_ = [
            ("interval", ctypes.c_uint64),
            ("pid_tgid", ctypes.c_uint64),
            ("ip", ctypes.c_uint64),
            ("time", ctypes.c_uint64),
            ("freq", ctypes.c_uint64),
        ]

    def print_event(cpu, data, size):
        global last_updated
        last_updated = datetime.now()
        stats = ctypes.cast(data, ctypes.POINTER(Stats)).contents
        obj = {
            "pid": ctypes.c_uint32(stats.pid_tgid).value,
            "tid": ctypes.c_uint32(stats.pid_tgid >> 32).value,
        }
        fname = program.sym(stats.ip, obj["pid"], show_module=True).decode()
        if "unknown" in fname:
            fname = program.ksym(stats.ip, show_module=True).decode()
        if "unknown" in fname:
            cat = "unknown"
        else:
            cat = fname.split(" ")[1]
        obj = {
            "pid": ctypes.c_uint32(stats.pid_tgid).value,
            "tid": ctypes.c_uint32(stats.pid_tgid >> 32).value,
            "name": fname,
            "cat": cat,
            "ph": "C",
            "ts": stats.interval,
            "args": {"time": stats.time, "freq": stats.freq},
        }
        logging.info(json.dumps(obj))

    outdir = os.path.dirname(args.outfile)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler(args.outfile, mode="a", encoding="utf-8"),
        ],
        format="%(message)s",
    )
    logging.info("[")
    program["events"].open_ring_buffer(print_event)
    timeout_interval_secs = 30
    interval = timedelta(seconds=int(timeout_interval_secs))

    def exit_function():
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

    while True:
        try:
            program.ring_buffer_consume()
            time.sleep(0.5)
            if datetime.now() - last_updated > interval:
                print(f"No events received for {timeout_interval_secs} secs. Exiting.")
                exit_function()
                exit()
        except KeyboardInterrupt:
            exit_function()
            exit()


if __name__ == "__main__":
    main()
