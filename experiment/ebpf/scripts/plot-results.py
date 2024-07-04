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
        default=os.path.join(here, "results", "lammps"),
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


def find_inputs(input_dir, pattern="*.out"):
    """
    Find inputs (results files)
    """
    files = []
    for filename in recursive_find(input_dir, pattern=pattern):
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
        raise ValueError(f"There are no lammps input files in {indir}")

    # Find the perfetto files
    perfetto_files = find_inputs(indir, pattern="*.pfw")

    # This does the actual parsing of data into a formatted variant
    # Has keys results, iters, and columns
    df, lammps = parse_data(files, perfetto_files)

    import IPython
    IPython.embed()
    sys.exit()
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


def parse_data(files, perfetto_files):
    """
    Given a listing of files, parse into results data frame
    """
    # Parse into data frame
    df = pandas.DataFrame(
        columns=[
            "ranks",
            "experiment",
            "group",
            "iteration",
            "nodes",
            "function",
            "category",
            "count",
            "time_nsecs",
            "interval",
        ]
    )
    idx = 0

    # And only to compare lammps times
    lammps = pandas.DataFrame(
        columns=[
            "ranks",
            "experiment",
            "group",
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
        filebase = pieces[-1].replace("lammps.", "")

        # "group", $number, "size", $size, $iteration
        if "iter" in filebase:
            _, group, _, size, _, iteration = filebase.replace(".out", "").split("-")
        else:
            _, group, _, size, iteration = filebase.replace(".out", "").split("-")

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
            group,
            int(iteration),
            seconds,
            1,
            percent_cpu_usage,
        ]
        idxl += 1
        continue

    import IPython
    IPython.embed()
           
        # Json result is here
   #     ebpf = json.loads(
    #        item.split("=== RESULTS START", 1)[-1].split("=== RESULTS END", 1)[0]
   #     )

    total = len(perfetto_files)
    for i, filename in enumerate(perfetto_files):

        print(f"Parsing {i} of {total}", end="\r")
        parsed = os.path.relpath(filename, here)
        pieces = parsed.split(os.sep)
        experiment = pieces[-2]
        filebase = pieces[-1].replace("lammps.", "")

        # "group", $number, "size", $size, $iteration
        if "iter" in filebase:
            _, group, _, size, _, iteration = filebase.replace(".pfw", "").split("-")
        else:
            _, group, _, size, iteration = filebase.replace(".pfw", "").split("-")

        group = int(group)
        size = int(size)
        if group != 4 or size != 64:
            continue

        item = utils.read_file(filename)
        item = item.replace('[', '', 1)
        for line in item.split('\n'):
            if not line:
                continue
            func = json.loads(line)
            df.loc[idx, :] = [
                int(ranks),
                experiment,
                group,
                iteration,
                1,
                func["name"],
                func['cat'],
                func['args']["freq"],
                func["args"]['time'],
                func['ts']
            ]
            idx += 1

    import IPython
    IPython.embed()
    sys.exit()
    df.ranks = df.ranks.astype(int)
    df.nodes = df.nodes.astype(int)
    df.time_nsecs = df.time_nsecs.astype(int)
    df["count"] = df["count"].astype(int)
    return df, lammps


# input here should be lammps
def test_outliers(df, lammps):
    diffs = pandas.DataFrame(columns=["function", "size", "pvalue", "statistic"])
    idx = 0

    # Filter out singularity
    sing = lammps[lammps.experiment == 'singularity']

    # Identify outliers including bare metal times
    thresholds = {}
    for size in sing.ranks.unique():
        mean_time = lammps[lammps.ranks==int(size)].groupby(['ranks']).time_seconds.mean().values[0]
        std_time = lammps[lammps.ranks==int(size)].groupby(['ranks']).time_seconds.std().values[0]
        
        # Say an outlier is 3x the std, this is the 3 sigma rule
        thresh = mean_time + (3* std_time)       
        thresholds[int(size)] = thresh
        
    values = []
    for row in sing.iterrows():
        thresh = thresholds[row[1].ranks]
        if row[1].time_seconds >= thresh:
            values.append(True)
        else:
            values.append(False)

    # 31 outliers out of 271 
    # len([x for x in values if x==True])
    sing['is_outlier'] = values

    # Let's just consider singularity cases
    ss = df[df.experiment == 'singularity']

    # Default all are not outliers
    df['is_outlier'] = False

    # Set outlier on the main data frame depending on iteration and ranks
    for row in sing.iterrows():
        if not row[1].is_outlier:
            continue
        index = ss[(ss.ranks == row[1].ranks) & (ss.group == row[1].group) & (ss.iteration == str(row[1].iteration))].index
        ss.loc[index, "is_outlier"] = True

    # Just look at mean of outliers and difference
    outlier_df = pandas.DataFrame(columns=['function', 'size', 'outlier', 'no_outlier', 'difference'])
    idx2 = 0

    all_outliers = {}
    for function in ss.function.unique():
        subset = ss[ss.function == function]
        for size in ss.ranks.unique():
            sized = subset[subset.ranks == size]
            if sized.shape[0] == 0:
                continue

            df_subset = df[df.function == function]
            df_subset = df_subset[df_subset.ranks == size]
            if df_subset.shape[0] == 0:
                continue

            # If we don't have any outliers
            if len(sized.is_outlier.unique()) == 1 and sized.is_outlier.unique().tolist()[0] is False:
                continue

            # Every run for the group is an outlier
            if len(sized.is_outlier.unique()) == 1 and sized.is_outlier.unique().tolist()[0] is True:
                if size not in all_outliers:
                    all_outliers[size] = set()
                all_outliers[size].add(function)

            # Do a t test! Two tailed means we can get a change in either direction
            outlier = sized[sized.is_outlier == True].time_nsecs.tolist()
            not_outlier = df_subset[df_subset.is_outlier == False].time_nsecs.tolist()

            # Difference as a percentage of not outlier, across entire experiment (bare metal too)
            difference = (numpy.mean(not_outlier) - numpy.mean(outlier)) / numpy.mean(not_outlier)
            if difference == 0:
                continue
 
            outlier_df.loc[idx2, :] = [function, size, numpy.mean(outlier), numpy.mean(not_outlier), difference]
            idx2 +=1

            # For now require >1 for both (we need more samples here)
            if len(outlier) <= 1 or len(not_outlier) <= 1:
                continue

            # plot_distribution(singularity, bare_metal, norm_dist_out)
            res = stats.ttest_ind(outlier, not_outlier)
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


if __name__ == "__main__":
    main()
