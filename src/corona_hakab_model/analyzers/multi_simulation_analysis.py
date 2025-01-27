from typing import List, Callable, Dict
import os
from pathlib import Path

from analyzers.config import TIME_OUTPUT_PATH
import pandas as pd
from datetime import datetime
from itertools import chain

import numpy as np
import matplotlib.pyplot as plt


def create_comparison_files(files: list = None):
    """

    :param files: Files to compare. If not given, takes all the files in the output folder.
    :return: result_folder_name: a path to the directory created containing:
        for each parameter creates a file combining the information from each file given.
    """
    if files is None:
        files = Path(TIME_OUTPUT_PATH).glob("*.csv")
    dfs_dict = dict(map(lambda f: (os.path.basename(f),
                                   pd.read_csv(f).drop(["Unnamed: 0"], axis=1, errors='ignore')),
                        files))
    dfs_columns = map(lambda f: f.columns.tolist(), dfs_dict.values())
    parameters_to_compare = set(chain.from_iterable(dfs_columns))
    result_folder_name = Path(TIME_OUTPUT_PATH) / datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    os.mkdir(result_folder_name)
    for parameter in parameters_to_compare:
        result_df = pd.DataFrame(columns=dfs_dict.keys())
        for file_name, file_df in dfs_dict.items():
            if parameter in file_df.columns:
                result_df.loc[:, file_name] = file_df.loc[:, parameter]
            else:
                result_df.loc[:, file_name] = pd.nan
        result_df.to_csv(Path(result_folder_name) / f"{parameter}.csv")
    return result_folder_name


def plot_minmax_barchart_single_param(param_csvfile_path):
    """
    see example_script.py for usage
    :param param_csvfile_path: a path to csv file to aggregate the data from,
                                assumes generated by create_comparison_files
    :return: return None and plot a matplotlib bar-chart
    """
    plot_aggregations_from_csv(param_csvfile_path, {"min": np.min, "max": np.max})


def plot_aggregations_from_csv(csv_file_path: Path, aggregation_funcs: Dict[str, Callable]):
    """

    :param csv_file_path: a path to csv file to aggregate the data from assumes generated by create_comparison_files
    :param aggregation_funcs: dict of all the aggregation functions  to be applied per column
    :return: return None and plot a matplotlib bar-chart
    """
    source_df = pd.read_csv(csv_file_path).drop(["Unnamed: 0"], axis=1, errors='ignore')
    agg_df = source_df.agg(list(aggregation_funcs.values()))

    n_aggregations = len(aggregation_funcs)
    n_runs = source_df.shape[1]

    runs_labels = list(agg_df.columns)
    x = np.arange(n_runs)  # the label locations
    width = 1/(n_aggregations+1)  # the width of the bars

    fig, ax = plt.subplots()
    rects_list = []
    for i, (agg_name, (_, agg_values)) in enumerate(zip(aggregation_funcs.keys(), agg_df.iterrows())):
        rects_list.append(ax.bar(x - width * (- n_aggregations + 2 * i) / 2, list(agg_values), width, label=agg_name))

    ax.set_title(f"aggregation of {csv_file_path.stem}")
    ax.set_xticks(x)
    ax.set_xticklabels(runs_labels)
    ax.legend()

    def label_rects_with_height(rects):
        """Attach a text label above each bar in *rects*, displaying its height."""
        for rect in rects:
            height = round(rect.get_height(), 2)
            ax.annotate('{}'.format(height),
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    for rects in rects_list:
        label_rects_with_height(rects)

    fig.tight_layout()
    plt.show()


def create_time_avg_std(comparison_dir_path) -> Dict[str, pd.DataFrame]:
    """
    see example_script.py for usage
    :param comparison_dir_path: path to the directory created by create_comparison_files to work on
    :return: a dictionary with to keys: "mean", "std" with the compatible DataFrames as values
    """
    return create_time_step_aggregation(comparison_dir_path, agg_funcs_dict={"mean": np.mean, "std": np.std})


def create_time_step_aggregation(parameters_dir_path, agg_funcs_dict: Dict[str, Callable]) -> Dict[str, pd.DataFrame]:
    """

    :param parameters_dir_path: path to the directory created by create_comparison_files to work on
    :param agg_funcs_dict: dict of all the aggregation functions that want to be applied across multiple simulation runs
    :return: a dictionary with keys the same as agg_funcs_dict but values the df corresponding to the aggregation
    """
    files = (Path(TIME_OUTPUT_PATH)/parameters_dir_path).glob("*.csv")

    dfs_dict = {os.path.basename(f).replace('.csv', ''):
             pd.read_csv(f).drop(["Unnamed: 0"], axis=1, errors='ignore') for f in files}
    result_folder_name = Path(TIME_OUTPUT_PATH) / (datetime.now().strftime("%Y_%m_%d-%H_%M_%S")+"_time_agg")
    os.mkdir(result_folder_name)
    results_df_dict = {}
    for agg_name, agg_func in agg_funcs_dict.items():
        columns = {}
        for param_name, df in dfs_dict.items():
            param_name = param_name.replace('.csv', '')
            columns[param_name] = df.agg(agg_func, axis=1)
        results_df_dict[agg_name] = pd.DataFrame.from_dict(columns)
        results_df_dict[agg_name].to_csv(Path(result_folder_name) / f"{agg_name}.csv")
    return results_df_dict


def plot_parameter_propagation_aggregated(mean_df: pd.DataFrame, std_df: pd.DataFrame,
                                          parameter_names: List[str] = None):
    """

    :param mean_df: a DataFrame containing all the means of the parameters across some simulation runs
    :param std_df: a DataFrame containing all the stand deviations of the parameters across some simulation runs
    :param parameter_names: optional list of all the parameter names to plot, if not given plot all parameters
    :return:
    """
    if parameter_names is None:
        parameter_names = list(mean_df.columns)
    else:
        for param_name in parameter_names:
            if param_name not in mean_df.columns or param_name not in std_df.columns:
                print(f"{param_name} is not a column in both mean_df and std_df")
                parameter_names.remove(param_name)
        if len(parameter_names) == 0:
            parameter_names = [mean_df.columns[0]]
            print(f"none of given parameters exist plotting for the first parameter - {parameter_names[0]}")

    # plotting
    time = np.array(mean_df.index)
    fig, ax = plt.subplots()
    for parameter_name in parameter_names:
        param_mean = mean_df[parameter_name].to_numpy()
        param_std = std_df[parameter_name].to_numpy()

        ax.plot(time, param_mean, '-', label=parameter_name)
        ax.fill_between(time, param_mean - param_std, param_mean + param_std, alpha=0.2)
    ax.legend()
    plt.show()
