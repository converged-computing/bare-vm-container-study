#!/usr/bin/env python3

# Read a function file to profile if a particular set of functions has any hits.

import argparse
import os
import tempfile
import subprocess
import sys
import time

from bcc import BPF

wrapper_template = """#!/bin/bash

echo "Program running has pid $$"

# This is probably too big, be conservative
sleep 5

# This ensures our command inherits the same parent id
exec %s
"""

# This is the BPF program
# We are basically keeping track of start and end times
# and that way we can return an accumulated time.
# This is based on this example: https://github.com/iovisor/bcc/blob/master/tools/funclatency.py
bpf_text = """
#include <uapi/linux/ptrace.h>

struct key_t {
    u64 ip;
};

BPF_HASH(counts, struct key_t, u64, 256);

int do_count(struct pt_regs *ctx) {
    struct key_t key = {};
    key.ip = PT_REGS_IP(ctx);
    counts.atomic_increment(key);
    return 0;
}
"""


def write_file(path, content):
    with open(path, "w") as fd:
        fd.write(content)


def append_file(path, content):
    with open(path, "a") as fd:
        fd.write(content)


def read_file(path):
    with open(path, "r") as fd:
        content = fd.read()
    return content


def get_parser():
    parser = argparse.ArgumentParser(
        description="Time functions and print time spent in each function",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", help="function file with kprobe list")
    parser.add_argument(
        "--out", help="Write matches to this output file", default="kprobes-present.txt"
    )
    return parser


def get_tmpfile():
    """
    Get a temporary file name
    """
    tmpdir = tempfile.gettempdir()
    temp_name = "wrapper-" + next(tempfile._get_candidate_names()) + ".sh"
    return os.path.join(tmpdir, temp_name)


def add_filter(pid):
    """
    Add a filter to a tgid (thread group id) based on
    a program pid. A group of pids can belong to a tgid,
    and usually the first is the tgid. We can use a function
    to derive it.
    """
    return bpf_text.replace("FILTER", f"if (pid != {pid})" + "{ return 0; }")


def main():
    """
    Run the ebpf program. Usage:

    sudo -E python3 determine-kprobes.py sleep 10
    """
    parser = get_parser()
    args, command = parser.parse_known_args()

    # If we don't have a command or pid, no go
    if not command:
        sys.exit("We need a command to follow the script.")

    if not args.file:
        sys.exit("Please provide a --file with one kprobe per line.")

    print(f"👉️  Input: {args.file}")
    print(f"👉️ Output: {args.out}")

    # Read n kprobes and form regular expression
    # Don't use private functions
    kprobes = [
        x.replace("kprobe:", "", 1) for x in read_file(args.file).split("\n") if x
    ]
    kprobes = [x for x in kprobes if not x.startswith("_")]
    if not kprobes:
        sys.exit("No kprobes found after filter.")
    print(f"Looking at {len(kprobes)} contenders...")

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

    # Load the ebpf program
    program = BPF(text=program_text)

    # patterns should be regular expression oriented
    pattern = "^(" + "|".join(kprobes) + ").*$"
    program.attach_kprobe(event_re=pattern, fn_name="do_count")

    # This tells us the number of kprobes we match
    matched = program.num_open_kprobes()

    # This should not happen
    if matched == 0:
        sys.exit('0 functions matched by "{pattern}". Exiting.')

    end = time.time()
    print(f"Setting up eBPF took {end-start} seconds.")

    # We have to divide by two since we have a start/stop
    number_functions = int(matched)
    print(f"Counting {number_functions} functions.")

    # Wait for lammps to finish running
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
    print("%-36s %8s" % ("FUNC", "COUNT"))

    # Get a table from the program to print to the terminal
    stats = program.get_table("counts")
    results = []

    # We only care if count != 0
    for k, v in stats.items():
        if v.value == 0:
            continue

        # k.ip is a number, and we convert to a symbol here
        results.append(BPF.sym(k.ip, -1).decode("utf-8"))
        print("%-36s %8s" % (BPF.sym(k.ip, -1).decode("utf-8"), v.value))

    print(f"Found {len(results)} utilized kprobe functions.")
    if len(results) > 0:
        append_file(args.out, "\n".join(results))

    os.remove(tmp_file)
    stats.clear()


if __name__ == "__main__":
    main()
