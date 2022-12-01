#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 14:23:57 2022.

@author: fabian
"""

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from common import load_network
from plot_bars import get_adapted_curtailment
from plot_sensitivity_dlr_cap import get_data


def get_congestion(networks):
    def get_congestion_hours(n):
        c = "Line"
        number_lines_congested = (
            n.pnl(c).mu_lower.abs() + n.pnl(c).mu_upper.abs()
        ).round(0) != 0
        return number_lines_congested.sum(axis=1).mean()

    df = pd.DataFrame(
        {name: [get_congestion_hours(n)] for name, n in networks.items()},
        index=["congestion"],
    ).T
    return df


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_sensitivity_renewable_share",
            year="2030",
            opts="Co2L-RE0.8-Ep",
            clusters="all",
            rating="",
            dlr="",
            angle="",
            ext="pdf",
        )
    year = snakemake.wildcards["year"]
    opts = snakemake.config["scenario_2035"]["opts"]
    keys = [float(k.split("-")[1][len("RE") :]) for k in opts]

    slr = snakemake.input.networks_slr
    slr = {k: load_network(p) for k, p in zip(keys, slr)}

    dlr = snakemake.input.networks_dlr
    dlr = {k: load_network(p) for k, p in zip(keys, dlr)}

    ref = slr[keys[0]]

    sorter = [
        "Offshore Wind",
        "Onshore Wind",
        "Solar",
        "Other Renewables",
        "Fossil Carriers",
        "Battery Infrastructure",
        "Hydrogen Infrastructure",
    ]
    slr_data = get_data(slr).loc[:, sorter]
    dlr_data = get_data(dlr).loc[:, sorter]
    diff = dlr_data - slr_data
    colors = ref.carriers.groupby("group").color.first()[diff.columns]
    percentage_index = lambda ind: int(ind * 100)
    percentage = lambda ind: ind * 100

    # adapted_curtailment_dlr = {name: get_adapted_curtailment(n) for name, n in dlr.items()}
    # adapted_curtailment_slr = {name: get_adapted_curtailment(n) for name, n in slr.items()}

    costs = diff.loc["costs"].rename(percentage_index)
    costs["Total"] = costs.sum(1)
    colors.loc["Total"] = "grey"

    costs.div(-1e9).plot(
        color=colors,
        title=list(costs.columns),
        legend=False,
        subplots=True,
        figsize=(7, 5),
        layout=(4, 2),
        sharex=True,
        xlabel="Renewable production share [%]",
    )
    fig = plt.gcf()
    fig.supylabel("Cost savings [bn€]")
    plt.xticks(costs.index)

    plt.tight_layout()
    plt.savefig(snakemake.output.sensitivity_costs, bbox_inches="tight")

    def line_break_long_labels(label):
        return label.replace(" ", "\n") if len(label) > 20 else label

    # %%
    fig = plt.figure(tight_layout=True, figsize=(7, 3.5))
    gs = gridspec.GridSpec(4, 3)

    capacity_change_absolute = (
        diff.loc["capacity"]
        .div(1e3)
        .where(lambda x: x != 0)
        .dropna(axis=1, how="all")
        .rename(columns=line_break_long_labels)
    )
    mask_gen = np.row_stack(
        capacity_change_absolute.apply(
            lambda x: x.index.str.contains("Infrastructure"), axis=1
        ).values
    )
    ax = fig.add_subplot(gs[:, :2])
    gen_cap = capacity_change_absolute.mask(mask_gen).dropna(axis=1, how="all").T
    gen_cap.plot(
        ax=ax,
        kind="bar",
        bottom=0,
        xlabel="",
        ylabel="$\Delta$ Generation capacity [GW]",
        color=sns.color_palette("viridis", n_colors=len(capacity_change_absolute)),
        legend=False,
    )

    ax = fig.add_subplot(gs[:3, 2])
    sts_cap = (
        capacity_change_absolute.mask(~mask_gen).div(1e3).dropna(axis=1, how="all").T
    )
    sts_cap.plot(
        ax=ax,
        kind="bar",
        sharex=True,
        bottom=0,
        xlabel="",
        ylabel="",
        color=sns.color_palette("viridis", n_colors=len(capacity_change_absolute)),
        ylim=(-0.5, None),
        legend=False,
    )
    ax.set_ylabel("$\Delta$ Storage capacity [TWh]     ", loc="top")
    ax = fig.add_subplot(gs[3, 2])
    sts_cap.plot(
        ax=ax,
        kind="bar",
        sharex=True,
        bottom=0,
        xlabel="",
        color=sns.color_palette("viridis", n_colors=len(capacity_change_absolute)),
        ylim=(None, -0.5),
        legend=False,
    )

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Renewable production share [%]",
        loc="upper center",
        bbox_to_anchor=(0.5, 1.12),
        ncol=5,
    )
    fig.savefig(snakemake.output.sensitivity_capacity, bbox_inches="tight")

    # %%
    fig, axes = plt.subplots(2, 1, figsize=(5, 3), sharex=True)
    diff.loc["costs"].mul(-1).sum(1).div(1e9).T.plot(
        ax=axes[0],
        linestyle="--",
        marker="o",
        ylabel="Savings [bn€]",
        title="System cost savings through DLR",
    )
    axes[0].margins(y=0.1)
    congestion_diff = get_congestion(slr) - get_congestion(dlr)
    congestion_diff.plot(
        ax=axes[1],
        linestyle="--",
        marker="o",
        title="Average number of relieved line congestions",
        ylabel="# Congestions",
        xlabel="Renewable share [%]",
        xticks=congestion_diff.index,
        legend=False,
    )
    axes[1].margins(y=0.1)
    axes[1].set_xticklabels(congestion_diff.rename(percentage_index).index)
    fig.tight_layout()
    fig.savefig(snakemake.output.sensitivity_costs_curtailment, bbox_inches="tight")
