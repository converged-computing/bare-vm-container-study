#!/usr/bin/env python3

import argparse
import fnmatch
import json
import os
import random

import matplotlib.pyplot as plt
import metricsoperator.utils as utils
import pandas
import seaborn as sns
import dask
import dask.dataframe as dd
import numpy
from metricsoperator.metrics.app.lammps import parse_lammps
from scipy import stats
from statsmodels.sandbox.stats.multicomp import multipletests
from glob import glob
from dask.distributed import Client, LocalCluster, progress, wait, get_client
import logging

loglevel = logging.INFO
logging.basicConfig(
    level=loglevel,
    handlers=[logging.StreamHandler()],
    format="[%(levelname)s] [%(asctime)s] %(message)s [%(pathname)s:%(lineno)d]",
    datefmt="%H:%M:%S",
)


workers = 4
is_initialized = False

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

    # This does the actual parsing of data into a formatted variant
    # Has keys results, iters, and columns
    # lammps = parse_data(files)
    # lammps.to_csv(os.path.join(outdir, "lammps-times.csv"))

    # Find the perfetto files
    # perfetto_files = find_inputs(indir, pattern="*.pfw")
    # df = parse_timing_dask(perfetto_files)
    # df.to_parquet(os.path.join(outdir, 'lammps-events.parquet'))  

    # Being lazy = compute to pandas (7.1 million and change rows)
    import IPython
    IPython.embed()
    sys.exit()
    # df.to_csv(os.path.join(outdir, "testing-times.csv"))

    # Write unique functions to file
    df = df.compute()
    funcs = df.name.unique().tolist()
    funcs.sort()
    # There are 1719 relevant ebpf functions
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


def plot_distribution(function, size, singularity, bare_metal, norm_dist_out):
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

    # We need mins, maxes, and medians for each iteration
    mins = pandas.DataFrame(columns=["function", "experiment", "size", "iter", "value"])
    maxes = pandas.DataFrame(columns=["function", "experiment", "size", "iter", "value"])
    meds = pandas.DataFrame(columns=["function", "experiment", "size", "iter", "value"])
    sums = pandas.DataFrame(columns=["function", "experiment", "size", "iter", "value"])
    
    idx = 0
    not_used_singularity = {}
    not_used_bare_metal = {}

    # Check for normal distribution
    norm_dist_out = os.path.join(outdir, "check-normal")
    if not os.path.exists(norm_dist_out):
        os.makedirs(norm_dist_out)

    for function in df.name.unique():
        subset = df[df.name == function]
        for size in df['size'].unique():
            sized = subset[subset['size'] == size]
            if sized.shape[0] == 0:
                continue

            # This sized is across all iterations! We need to get min/max/medium per iteration
            for i in sized.iter.unique():
                isubset = sized[sized.iter == i]

                scount = isubset[isubset.experiment=="singularity"].name.count()
                bare_metal_count = isubset[isubset.experiment=="bare-metal"].name.count()

                # We would want to sanity check these and understand why!
                if scount == 0:
                    if size not in not_used_singularity:
                        not_used_singularity[str(size)] = []
                    not_used_singularity[str(size)].append(function)
                if bare_metal_count == 0:
                    if size not in not_used_bare_metal:
                        not_used_bare_metal[str(size)] = []
                    not_used_bare_metal[str(size)].append(function)
                if scount == 0 or bare_metal_count == 0:
                    continue

                # Take total sum for iteration
                singularity_total_sum = isubset[isubset.experiment == "singularity"].time.sum()
                bare_metal_total_sum = isubset[isubset.experiment == "bare-metal"].time.sum() 

                # There should only be one parent task for lammps
                # Sum the times across the individual task ids 
                singularity_task_sums = isubset[isubset.experiment == "singularity"].groupby(['tid'])['time'].sum().tolist()
                bare_metal_task_sums = isubset[isubset.experiment == "bare-metal"].groupby(['tid'])['time'].sum().tolist()
                
                # Now we get the min, max, and medium across the summed records above
                smin = numpy.min(singularity_task_sums)
                smax = numpy.max(singularity_task_sums)
                smed = numpy.median(singularity_task_sums)

                bmin = numpy.min(bare_metal_task_sums)
                bmax = numpy.max(bare_metal_task_sums)
                bmed = numpy.median(bare_metal_task_sums)
                                
                # Save to data frames - we need to assemble all of them before doing t tests
                mins.loc[idx, :] = [function, "singularity", size, i, smin]
                maxes.loc[idx, :] = [function, "singularity", size, i, smax]
                meds.loc[idx, :] = [function, "singularity", size, i, smed]
                sums.loc[idx, :] = [function, "singularity", size, i, singularity_total_sum]
                idx += 1

                mins.loc[idx, :] = [function, "bare-metal", size, i, bmin]
                maxes.loc[idx, :] = [function, "bare-metal", size, i, bmax]
                meds.loc[idx, :] = [function, "bare-metal", size, i, bmed]
                sums.loc[idx, :] = [function, "bare-metal", size, i, bare_metal_total_sum]
                idx +=1 
                

    # Save values
    meds.to_csv(os.path.join(outdir, 'lammps-function-medians.csv'))
    mins.to_csv(os.path.join(outdir, 'lammps-function-mins.csv'))
    maxes.to_csv(os.path.join(outdir, 'lammps-function-maxes.csv'))
    sums.to_csv(os.path.join(outdir, 'lammps-function-sums.csv'))

    # Now for each group, do a 2 sample t test and plot
    # Keep record of results for each
    diffs = pandas.DataFrame(columns=["function", "size", "pvalue", "statistic", "metric", "singularity_samples", "bare_metal_samples"])
    idx = 0
    for function in sums.function.unique():
        subset = sums[sums.function == function]
        for size in subset['size'].unique():
            sized = subset[subset['size'] == size]
            
            # Do a t test! Two tailed means we can get a change in either direction
            singularity = sized[sized.experiment == "singularity"].value.tolist()
            bare_metal = sized[sized.experiment == "bare-metal"].value.tolist()

            # For now require >1 for both (we need more samples here)
            if len(singularity) <= 1 or len(bare_metal) <= 1:
                continue

            # Plot a subset
            #if random.choice(list(range(1,10))) < 2:
            #    plot_distribution(function, size, singularity, bare_metal, norm_dist_out)
            res = stats.ttest_ind(singularity, bare_metal)
            diffs.loc[idx, :] = [function, size, res.pvalue, res.statistic, "median", len(singularity), len(bare_metal)]
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
    bad_files = set()
    for i, filename in enumerate(files):
        print(f"Parsing {i} of {total}", end="\r")
        parsed = os.path.relpath(filename, here)
        pieces = parsed.split(os.sep)
        experiment = pieces[-2]
        filebase = pieces[-1].replace("lammps.", "")
       
        # Bare metal runs don't have lammps files associated.
        if not "lammps" in pieces[-1]:
            _, _, size, _, iteration = filebase.replace(".out", "").split("-")
            group = None
        else:
            # "group", $number, "size", $size, $iteration
            if "iter" in filebase:
                _, group, _, size, _, iteration = filebase.replace(".out", "").split("-")
            else:
                _, group, _, size, iteration = filebase.replace(".out", "").split("-")

        item = utils.read_file(filename)
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

    return lammps


def parse_timings(perfetto_files):
    """
    This function is not suited for large results using pandas!
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
        item = item.replace("[", "", 1)
        for line in item.split("\n"):
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
                func["cat"],
                func["args"]["freq"],
                func["args"]["time"],
                func["ts"],
            ]
            idx += 1

    df.ranks = df.ranks.astype(int)
    df.nodes = df.nodes.astype(int)
    df.time_nsecs = df.time_nsecs.astype(int)
    df["count"] = df["count"].astype(int)
    return df


def parse_timing_dask(files):
    """
    Parse timing files using Dask
    """
    global is_initialized
    if not is_initialized:
        cluster = LocalCluster(
            n_workers=workers
        )  # Launches a scheduler and workers locally
        client = Client(cluster)  # Connect to distributed cluster and override default
        logging.info(
            f"Initialized Client with {workers} workers and link {client.dashboard_link}"
        )
    else:
        client = Client.current()
        client.restart()
        logging.info("Restarting all workers")

    pfw_bag = dask.bag.read_text(files, include_path=True).map(load_objects).filter(lambda x: "name" in x)
    columns = {
        "name": "string[pyarrow]",
        "cat": "string[pyarrow]",
        "pid": "uint64[pyarrow]",
        "tid": "uint64[pyarrow]",
        "ts": "uint64[pyarrow]",
        "time": "uint64[pyarrow]",
        "freq": "uint64[pyarrow]",
        "experiment": "string[pyarrow]",
        "group": "string[pyarrow]",
        "iter": "int32[pyarrow]",
        "size": "int32[pyarrow]",
    }
    events = pfw_bag.to_dataframe(meta=columns)
    events = events.persist()
    _ = wait(events)
    events.head()
    return events


def load_objects(args):
    """
    Function from Hari to load data in via dask!
    """
    line, path = args
    d = {}

    # Cut out early if our line is emptuy
    if line is None or not line.strip() or line.strip() in ["[", "\n"]:
        return d

    val = {}
    unicode_line = "".join([i if ord(i) < 128 else "#" for i in line])
    val = json.loads(unicode_line)

    # Again return early if missing a name
    if "name" not in val:
        return d

    # Parse the filename and parameters
    parsed = os.path.relpath(path, here)
    pieces = parsed.split(os.sep)
    experiment = pieces[-2]
    filebase = pieces[-1].replace("lammps.", "")

    # "group", $number, "size", $size, $iteration
    _, group, _, size, _, iteration = filebase.replace(".pfw", "").split("-")

    d['experiment'] = experiment
    d['iter'] = int(iteration)
    d['size'] = int(size)
    d['group'] = group
    d["name"] = val["name"]
    d["cat"] = val["cat"]
    d["pid"] = val["pid"]
    d["tid"] = val["tid"]
    d["ts"] = int(val["ts"])
    if "args" in val:
        d["time"] = int(val["args"]["time"])
        d["freq"] = int(val["args"]["freq"])
    return d


# input here should be lammps
def test_outliers(df, lammps):
    diffs = pandas.DataFrame(columns=["function", "size", "pvalue", "statistic"])
    idx = 0

    # Filter out singularity
    sing = lammps[lammps.experiment == "singularity"]

    # Identify outliers including bare metal times
    thresholds = {}
    for size in sing.ranks.unique():
        mean_time = (
            lammps[lammps.ranks == int(size)]
            .groupby(["ranks"])
            .time_seconds.mean()
            .values[0]
        )
        std_time = (
            lammps[lammps.ranks == int(size)]
            .groupby(["ranks"])
            .time_seconds.std()
            .values[0]
        )

        # Say an outlier is 3x the std, this is the 3 sigma rule
        thresh = mean_time + (3 * std_time)
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
    sing["is_outlier"] = values

    # Let's just consider singularity cases
    ss = df[df.experiment == "singularity"]

    # Default all are not outliers
    df["is_outlier"] = False

    # Set outlier on the main data frame depending on iteration and ranks
    for row in sing.iterrows():
        if not row[1].is_outlier:
            continue
        index = ss[
            (ss.ranks == row[1].ranks)
            & (ss.group == row[1].group)
            & (ss.iteration == str(row[1].iteration))
        ].index
        ss.loc[index, "is_outlier"] = True

    # Just look at mean of outliers and difference
    outlier_df = pandas.DataFrame(
        columns=["function", "size", "outlier", "no_outlier", "difference"]
    )
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
            if (
                len(sized.is_outlier.unique()) == 1
                and sized.is_outlier.unique().tolist()[0] is False
            ):
                continue

            # Every run for the group is an outlier
            if (
                len(sized.is_outlier.unique()) == 1
                and sized.is_outlier.unique().tolist()[0] is True
            ):
                if size not in all_outliers:
                    all_outliers[size] = set()
                all_outliers[size].add(function)

            # Do a t test! Two tailed means we can get a change in either direction
            outlier = sized[sized.is_outlier == True].time_nsecs.tolist()
            not_outlier = df_subset[df_subset.is_outlier == False].time_nsecs.tolist()

            # Difference as a percentage of not outlier, across entire experiment (bare metal too)
            difference = (numpy.mean(not_outlier) - numpy.mean(outlier)) / numpy.mean(
                not_outlier
            )
            if difference == 0:
                continue

            outlier_df.loc[idx2, :] = [
                function,
                size,
                numpy.mean(outlier),
                numpy.mean(not_outlier),
                difference,
            ]
            idx2 += 1

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
