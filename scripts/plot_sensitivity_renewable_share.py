#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 14:23:57 2022.

@author: fabian
"""

import matplotlib.pyplot as plt
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
        ).round(2) != 0
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

    slr_data = get_data(slr)
    dlr_data = get_data(dlr)
    diff = dlr_data - slr_data
    colors = ref.carriers.groupby("group").color.first()[diff.columns]
    percentage_index = lambda ind: int(ind * 100)
    percentage = lambda ind: ind * 100

    # adapted_curtailment_dlr = {name: get_adapted_curtailment(n) for name, n in dlr.items()}
    # adapted_curtailment_slr = {name: get_adapted_curtailment(n) for name, n in slr.items()}

    costs = diff.loc["costs"].rename(percentage_index)
    costs["Total"] = costs.sum(1)
    colors.loc["Total"] = "grey"

    costs.div(1e6).plot(
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
    fig.supylabel("Cost savings [m€]")
    plt.xticks(costs.index)

    plt.tight_layout()
    plt.savefig(snakemake.output.sensitivity_costs, bbox_inches="tight")

    fig, ax = plt.subplots(1, 1, figsize=(5, 5.5))
    capacity_change = (
        (dlr_data.loc["capacity"] / slr_data.loc["capacity"] - 1)
        .where(lambda x: x != 0)
        .dropna(axis=1)
    )
    capacity_change_absolute = (
        (dlr_data.loc["capacity"] - slr_data.loc["capacity"])
        .where(lambda x: x != 0)
        .dropna(axis=1)
    )
    capacity_change.rename(percentage_index).applymap(percentage).T.plot(
        ax=ax,
        kind="bar",
        bottom=0,
        xlabel="",
        ylabel="Relative capacity change\nfrom SLR to DLR [%]",
        rot=45,
        color=sns.color_palette("viridis", n_colors=len(capacity_change)),
    )
    ax.legend(title="Renewable production share [%]")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(snakemake.output.sensitivity_capacity, bbox_inches="tight")

    fig, axes = plt.subplots(2, 1, figsize=(7, 5.5), sharex=True)
    diff.loc["costs"].sum(1).div(1e6).T.plot(
        ax=axes[0],
        linestyle="--",
        marker="o",
        ylabel="Cost change\nfrom SLR to DLR [M€]",
    )
    congestion_diff = get_congestion(dlr) - get_congestion(slr)
    congestion_diff.plot(
        ax=axes[1],
        linestyle="--",
        marker="o",
        ylabel="Average number of\ncongested lines per hour\nfrom SLR to DLR [#/h]",
        xlabel="Renewable share [%]",
        xticks=congestion_diff.index,
        legend=False,
    )
    axes[1].set_xticklabels(congestion_diff.rename(percentage_index).index)

    plt.tight_layout()
    plt.savefig(snakemake.output.sensitivity_costs_curtailment, bbox_inches="tight")
