#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 12 10:25:36 2022.

@author: fabian
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from common import load_network
from plot_bars import get_capacity, get_costs, get_curtailment


def get_data(networks):
    data = []
    for f in get_curtailment, get_capacity:
        df = pd.DataFrame(
            {name: f(n).groupby(n.carriers.group).sum() for name, n in networks.items()}
        ).T.sort_index(axis=1)
        data.append(df)
    df = pd.DataFrame(
        {name: get_costs(n).sum(1) for name, n in networks.items()}
    ).T.sort_index(axis=1)
    data.append(df)
    return pd.concat(data, keys=["curtailment", "capacity", "costs"])


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_sensitivity_dlr_cap",
            year="2030",
            clusters="all",
            opts="Co2L-RE0.8-Ep",
            rating="",
            angle="",
            ext="pdf",
        )
    year = snakemake.wildcards["year"]
    keys = snakemake.config[f"scenario_{year}"]["rating"]
    keys[-1] = "no limit"
    ref = load_network(snakemake.input.network_slr)
    networks = {k: load_network(p) for k, p in zip(keys, snakemake.input.networks_dlr)}

    data = get_data(networks)
    gcolors = ref.carriers.groupby("group").color.first()[data.columns]

    # %%
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(5, 7))
    axes = iter(axes)

    with sns.axes_style("white", rc={"font.family": "Times New Roman"}):
        ax = next(axes)
        data.loc["costs"].div(1e9).plot.area(
            ax=ax,
            color=gcolors,
            lw=0,
            alpha=0.7,
        )
        ax.legend(
            title="",
            bbox_to_anchor=(0.5, 1),
            loc="lower center",
            ncol=2,
            frameon=False,
        )
        ax.set_xlabel("Maximally allowed rating")
        ax.set_ylabel("System cost [bn€]")
        ax.spines[["top", "right"]].set_visible(False)

        ax = next(axes)
        data.loc["capacity"].div(1e3).plot.area(
            ax=ax,
            color=gcolors,
            legend=False,
            lw=0,
            alpha=0.7,
        )
        ax.set_xlabel("Maximally allowed rating")
        ax.set_ylabel("Capacity [GW]")
        ax.spines[["top", "right"]].set_visible(False)

        ax = next(axes)
        data.loc["curtailment"].plot.area(
            ax=ax,
            color=gcolors,
            legend=False,
            lw=0,
            alpha=0.7,
        )
        ax.set_xlabel("Maximally allowed rating")
        ax.set_ylabel("Curtailment [TWh]")
        ax.spines[["top", "right"]].set_visible(False)

    ax = next(axes)
    data.loc[("costs", 1.0)].sub(data.loc["costs"]).sum(1).div(1e9).plot(ax=ax)
    ax.set_xlabel("Maximally allowed rating")
    ax.set_ylabel("Cost savings [bn€]")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(left=0)

    fig.tight_layout()
    fig.savefig(snakemake.output.sensitivity_combined, bbox_inches="tight")
