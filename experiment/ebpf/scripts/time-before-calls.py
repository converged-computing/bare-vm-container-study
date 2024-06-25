#!/usr/bin/env python3

# Run an ebpf program by name, and wait for it to finish
# Usage:
#   sudo -E python3 time-calls.py --pattern do_sys* <program> <options> <args>

import argparse
import subprocess
import sys
import json

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

    // This should be the pid of the task group
    // I think this is what subprocess gives back
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

    // This means we missed the start
    if (tsp == 0) {
        return 0;
    }
    delta = bpf_ktime_get_ns() - *tsp;
    start.delete(&pid);

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


def get_parser():
    parser = argparse.ArgumentParser(
        description="Time functions and print time spent in each function",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-p", "--pattern", help="search expression for functions", default="do_sys*"
    )
    return parser


def main():
    """
    Run the ebpf program. Usage:

    sudo -E python3 time-calls.py sleep 10
    """
    parser = get_parser()
    args, command = parser.parse_known_args()

    # If we don't have a command or pid, no go
    if not command:
        sys.exit("We need a --pid or command to follow the script, bro-shizzle.")

    # Start the program first so we capture everything
    print(f"👀️ Watching command {' '.join(command)}...")

    # Load the ebpf program
    program = BPF(text=bpf_text)

    # patterns should be regular expression oriented
    program.attach_kprobe(event_re=args.pattern, fn_name="start_timing")
    program.attach_kretprobe(event_re=args.pattern, fn_name="stop_timing")

    # This tells us the number of kprobes we match
    matched = program.num_open_kprobes()

    # We got a bad, bad pattern!
    if matched == 0:
        sys.exit('0 functions matched by "{args.pattern}". Exiting.')

    # Now launch subprocess
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # We have to divide by two since we have a start/stop
    number_functions = int(matched / 2)
    print(f'Timing {number_functions} functions for "{args.pattern}')

    # I'm not sure what overhead this adds
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
        results.append(
            {
                "func": BPF.sym(k.value, -1).decode("utf-8"),
                "count": v.freq,
                "time_nsecs": v.time,
            }
        )
        print("%-36s %8s %16s" % (BPF.sym(k.value, -1).decode("utf-8"), v.freq, v.time))
    print("\n=== RESULTS START")
    print(json.dumps(results))
    print("=== RESULTS END")

    # This only works for one function
    # program.detach_kprobe(event_re=pattern, fn_name="start_timing")
    # program.detach_kretprobe(event_re=pattern, fn_name="stop_timing")


if __name__ == "__main__":
    main()
