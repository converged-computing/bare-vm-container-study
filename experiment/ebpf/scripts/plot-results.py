#!/usr/bin/env python3

import argparse
import fnmatch
import json
import os

import matplotlib.pyplot as plt
import metricsoperator.utils as utils
import pandas
import seaborn as sns
from metricsoperator.metrics.app.lammps import parse_lammps
from scipy import stats
from statsmodels.sandbox.stats.multicomp import multipletests

plt.style.use("bmh")
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Plot Exploratory Results",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--results",
        help="directory with raw results data",
        default=os.path.join(here, "results", "test-1"),
    )
    parser.add_argument(
        "--out",
        help="directory to save parsed results",
        default=os.path.join(here, "img"),
    )
    return parser


def recursive_find(base, pattern="*.*"):
    """
    Recursively find and yield files matching a glob pattern.
    """
    for root, _, filenames in os.walk(base):
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)


def find_inputs(input_dir):
    """
    Find inputs (results files)
    """
    files = []
    for filename in recursive_find(input_dir, pattern="*.out"):
        # We only have data for small
        files.append(filename)
    return files


def main():
    """
    Run the main plotting operation!
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Output images and data
    outdir = os.path.abspath(args.out)
    indir = os.path.abspath(args.results)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input files (skip anything with test)
    files = find_inputs(indir)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # This does the actual parsing of data into a formatted variant
    # Has keys results, iters, and columns
    df, lammps = parse_data(files)

    # Show means grouped by experiment to sanity check plots
    df.to_csv(os.path.join(outdir, "testing-times.csv"))
    lammps.to_csv(os.path.join(outdir, "lammps-times.csv"))

    # Write unique functions to file
    funcs = df.function.unique().tolist()
    funcs.sort()
    print(f"There are {len(funcs)} relevant ebpf functions")
    utils.write_json(funcs, os.path.join(outdir, "ebpf-functions.json"))
    utils.write_file("\n".join(funcs), os.path.join(outdir, "ebpf-functions.txt"))
    plot_results(df, lammps, outdir)


def plot_lammps(lammps, outdir):
    """
    Plot lammps times
    """
    ax = sns.boxplot(
        data=lammps,
        x="ranks",
        y="time_seconds",
        whis=[5, 95],
        hue="experiment",
        palette="Set2",
    )
    plt.title("LAMMPS wall-time across sizes with/without eBPF")
    ax.set_xlabel("size (ranks)", fontsize=16)
    ax.set_ylabel("Time (seconds)", fontsize=16)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    plt.subplots_adjust(left=0.2, bottom=0.2)
    plt.savefig(os.path.join(outdir, "lammps-times.png"))
    plt.clf()
    plt.close()


def plot_distribution(singularity, bare_metal, norm_dist_out):
    sidx = 0
    histdf = pandas.DataFrame(columns=["experiment", "nanoseconds"])
    for value in singularity:
        histdf.loc[sidx] = ["singularity", value]
        sidx += 1
    for value in bare_metal:
        histdf.loc[sidx] = ["bare-metal", value]
        sidx += 1

    ax = sns.histplot(
        data=histdf,
        x="nanoseconds",
        hue="experiment",
        palette="Set2",
    )
    plt.title(f"Distribution times for {function} for size {size}")
    ax.set_xlabel("Time (nanoseconds)", fontsize=16)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    plt.subplots_adjust(left=0.2, bottom=0.2)
    plt.savefig(os.path.join(norm_dist_out, f"lammps-{function}-size-{size}.png"))
    plt.clf()
    plt.close()


def plot_results(df, lammps, outdir):
    """
    Plot results
    """
    # plot_lammps(lammps, outdir)

    # For each metric, see if there is significant difference between means
    # we would want to correct for multiple samples too.

    # Keep record of results for each
    diffs = pandas.DataFrame(columns=["function", "size", "pvalue", "statistic"])
    idx = 0
    not_used_singularity = {}
    not_used_bare_metal = {}

    # Check for normal distribution
    norm_dist_out = os.path.join(outdir, "check-normal")
    if not os.path.exists(norm_dist_out):
        os.makedirs(norm_dist_out)

    for function in df.function.unique():
        subset = df[df.function == function]
        for size in df.ranks.unique():
            sized = subset[subset.ranks == size]
            if sized.shape[0] == 0:
                continue

            # Do a t test! Two tailed means we can get a change in either direction
            singularity = sized[sized.experiment == "singularity"].time_nsecs.tolist()
            bare_metal = sized[sized.experiment == "bare-metal"].time_nsecs.tolist()

            # We would want to sanity check these and understand why!
            if len(singularity) == 0:
                if size not in not_used_singularity:
                    not_used_singularity[str(size)] = []
                not_used_singularity[str(size)].append(function)
                print(
                    f"Warning function {function} is not used for singularity size {size}."
                )
            if len(bare_metal) == 0:
                if size not in not_used_bare_metal:
                    not_used_bare_metal[str(size)] = []
                not_used_bare_metal[str(size)].append(function)
                print(
                    f"Warning function {function} is not used for bare metal size {size}."
                )
            if len(singularity) == 0 or len(bare_metal) == 0:
                continue

            # For now require >1 for both (we need more samples here)
            if len(singularity) <= 1 or len(bare_metal) <= 1:
                continue

            # plot_distribution(singularity, bare_metal, norm_dist_out)

            res = stats.ttest_ind(singularity, bare_metal)
            diffs.loc[idx, :] = [function, size, res.pvalue, res.statistic]
            idx += 1

    diffs = diffs.sort_values("pvalue")

    # Bonferonni correction
    rejected, p_adjusted, _, alpha_corrected = multipletests(
        diffs["pvalue"].tolist(), method="bonferroni"
    )
    diffs["pvalue"] = p_adjusted
    diffs["rejected"] = rejected
    sigs = diffs[diffs.rejected == True]

    # TODO add means / std for each
    diffs.to_csv(os.path.join(outdir, "two-sample-t.csv"))
    sigs.to_csv(os.path.join(outdir, "two-sample-t-reject-null.csv"))
    utils.write_json(
        not_used_singularity,
        os.path.join(outdir, "functions-not-used-singularity.json"),
    )
    utils.write_json(
        not_used_bare_metal,
        os.path.join(outdir, "functions-not-used-bare-metal.json"),
    )

    import IPython

    IPython.embed()


def plot_ebpf(df, outdir):
    for func in df.function.unique():
        subset = df[df.function == func]
        print(subset)
        ax = sns.lineplot(
            data=subset,
            x="ranks",
            y="time_nsecs",
            markers=True,
            dashes=True,
            errorbar=("ci", 95),
            hue="experiment",
            palette="Set2",
        )
        plt.title(f"eBPF function time for {func}")
        ax.set_xlabel("size (ranks)", fontsize=16)
        ax.set_ylabel("Time (log of nanoseconds)", fontsize=16)
        ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
        ax.set_yticklabels(ax.get_yticks(), fontsize=14)
        plt.subplots_adjust(left=0.2, bottom=0.2)
        plt.yscale("log")
        plt.savefig(os.path.join(outdir, f"ebpf-{func}.png"))
        plt.clf()
        plt.close()


def parse_data(files):
    """
    Given a listing of files, parse into results data frame
    """
    # Parse into data frame
    df = pandas.DataFrame(
        columns=[
            "ranks",
            "experiment",
            "iteration",
            "time_seconds",
            "nodes",
            "percent_cpu_utilization",
            "function",
            "count",
            "time_nsecs",
        ]
    )
    idx = 0

    # And only to compare lammps times
    lammps = pandas.DataFrame(
        columns=[
            "ranks",
            "experiment",
            "iteration",
            "time_seconds",
            "nodes",
            "percent_cpu_utilization",
        ]
    )
    idxl = 0

    total = len(files)
    for i, filename in enumerate(files):
        print(f"Parsing {i} of {total}", end="\r")
        parsed = os.path.relpath(filename, here)
        pieces = parsed.split(os.sep)
        experiment = pieces[-2]
        filebase = pieces[-1]
        _, iteration, _ = filebase.replace(".out", "").split("-")

        # Save CPU line
        # This is a list, each a json result, 20x
        item = utils.read_file(filename)

        # I think my session was killed
        if not item:
            continue

        line = [x for x in item.split("\n") if "CPU use" in x]
        percent_cpu_usage = float(line[0].split(" ")[0].replace("%", ""))

        # Full command is the first item
        result = parse_lammps(item)
        seconds = result["total_wall_time_seconds"]
        ranks = result["ranks"]

        # Save all lammps times
        lammps.loc[idxl, :] = [
            int(ranks),
            experiment,
            int(iteration),
            seconds,
            1,
            percent_cpu_usage,
        ]
        idxl += 1

        # These just have lammps times
        if "no-ebpf" in filename:
            continue

        # Json result is here
        ebpf = json.loads(
            item.split("=== RESULTS START", 1)[-1].split("=== RESULTS END", 1)[0]
        )

        for func in ebpf:
            df.loc[idx, :] = [
                int(ranks),
                experiment,
                iteration,
                seconds,
                1,
                percent_cpu_usage,
                func["func"],
                func["count"],
                func["time_nsecs"],
            ]
            idx += 1

    df.ranks = df.ranks.astype(int)
    df.nodes = df.nodes.astype(int)
    df.time_nsecs = df.time_nsecs.astype(int)
    df["count"] = df["count"].astype(int)
    return df, lammps


if __name__ == "__main__":
    main()
