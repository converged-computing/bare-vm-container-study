#!/usr/bin/env python3

# Run an ebpf program by name, and wait for it to finish
# Usage:
#   sleep 60 &
#   sudo -E python3 time-calls.py --program sleep do_sys*

# TODO: this program is not done yet. What we need:
#  1. This needs to be run before our application, meaning we need to wait for it
#  2. We likely need retry if the process for some reason is not there yet
#  3. Some elegant way to run and handle capturing both outputs
#  4. Testing in different cases to ensure we don't

import argparse
import os
import subprocess
import sys
from time import sleep

from bcc import BPF

# This is the BPF program
# We are basically keeping track of start and end times
# and that way we can return an accumulated time.
# This is based on this example: https://github.com/iovisor/bcc/blob/master/tools/funclatency.py
# plus random Google searching because I'm a C idiot
bpf_text = """
#include <uapi/linux/ptrace.h>

struct stats_t {
    u64 time;
    u64 freq;
};
BPF_HASH(start, u32);
BPF_HASH(ipaddr, u32);
BPF_HASH(stats, u64, struct stats_t);

int start_timing(struct pt_regs *ctx) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid;
    u64 ts = bpf_ktime_get_ns();

    u64 ip = PT_REGS_IP(ctx);
    ipaddr.update(&pid, &ip);
    start.update(&pid, &ts);

    return 0;
}

int stop_timing(struct pt_regs *ctx) {
    u64 *tsp, delta;
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid;

    // calculate delta time
    tsp = start.lookup(&pid);
    if (tsp == 0) {
        return 0;   // missed start
    }
    delta = bpf_ktime_get_ns() - *tsp;
    start.delete(&pid);

    // store as histogram
    u64 ip, *ipp = ipaddr.lookup(&pid);
    if (ipp) {
        ip = *ipp;
        struct stats_t *stat = stats.lookup(&ip);
        if (stat) {
            stat->time += delta;
            stat->freq++;
        } else {
            struct stats_t s = {};
            s.time = delta;
            s.freq = 1;
            stats.update(&ip, &s);
        }
        ipaddr.delete(&pid);
    }

    return 0;
}
"""


def add_filter(args):
    """
    Add a filter to a tgid (thread group id) based on
    a program pid. A group of pids can belong to a tgid,
    and usually the first is the tgid. We can use a function
    to derive it.
    """
    global bpf_text
    if args.program is not None:
        # Take program name, and get one of the pids. There are likely multiple
        # The first pid is actually the tgid (thread group id)
        # This is also a bit janky, but given unique names for the apps it should work
        pid = get_pid(args.program)
        tgid = None
        while tgid is None:
            try:
                # I'm starting at the end to get the last one submit
                # This should still give us the group (and not one that
                # was running previously)
                tgid = os.getpgid(pid.pop())
            except:
                continue
        if not tgid:
            raise ValueError(f"Could not get task group id for {args.program}")
        bpf_text = bpf_text.replace("FILTER", "if (tgid != {tgid}) { return 0; }")

    elif args.pid is not None:
        bpf_text = bpf_text.replace("FILTER", "if (tgid != {args.pid}) { return 0; }")
        tgid = args.pid
    return tgid


def get_parser():
    parser = argparse.ArgumentParser(
        description="Time functions and print time spent in each function",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pid", type=int, help="trace a single PID only")
    parser.add_argument("-p", "--program", help="name of program to trace")
    parser.add_argument("pattern", help="search expression for functions")
    parser.add_argument(
        "-s",
        "--sleep",
        type=int,
        help="seconds to sleep seeing if pid exists",
        default=10,
    )
    return parser


def get_pid(program):
    """
    Get the pid(s) of a program by name.

    We could use psutil for this, but I would
    rather not install an extra thign.
    """
    pid = subprocess.check_output(["pidof", program])
    if not pid:
        raise ValueError(f"Cannot get pid for {program}")
    pid = pid.decode("utf-8").strip().split(" ")
    return [int(x) for x in pid]


def pid_exists(pid):
    """
    Check if a pid exists in the current process table.

    This is exactly how psutil words, minus the edge cases.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # (EINVAL, EPERM, ESRCH)
    else:
        return True


def main():
    """
    Run the ebpf program. Usage:
    sleep 10 &
    sudo -E python3 time-calls.py --program sleep do_sys*
    """
    parser = get_parser()
    args = parser.parse_args()

    # Since we wait on it, make sure we have one
    if not args.pid and not args.program:
        sys.exit("We need a --pid or --program, bro-shizzle.")

    # Filter by specific pid or tgid
    pid = add_filter(args)
    print(f"👀️ Watching tgid/pid {pid}...")

    # Load the ebpf program
    program = BPF(text=bpf_text)
    pattern = args.pattern.replace("*", ".*")
    pattern = "^" + pattern + "$"
    program.attach_kprobe(event_re=pattern, fn_name="start_timing")
    program.attach_kretprobe(event_re=pattern, fn_name="stop_timing")

    # This tells us the number of kprobes we match
    matched = program.num_open_kprobes()

    # We got a bad, bad pattern!
    if matched == 0:
        sys.exit('0 functions matched by "%s". Exiting.' % args.pattern)

    # We have to divide by two since we have a start/stop
    number_functions = matched / 2
    print(f'Timing {number_functions} functions for "{args.pattern}')

    # I'm not sure what overhead this adds
    while pid_exists(pid):
        sleep(args.sleep)

    print()
    print("%-36s %8s %16s" % ("FUNC", "COUNT", "TIME (nsecs)"))

    # Get a table from the program to print to the terminal
    stats = program.get_table("stats")
    for k, v in stats.items():
        print("%-36s %8s %16s" % (BPF.sym(k.value, -1).decode("utf-8"), v.freq, v.time))


if __name__ == "__main__":
    main()
