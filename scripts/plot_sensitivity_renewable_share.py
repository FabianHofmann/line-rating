#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 14:23:57 2022.

@author: fabian
"""

import matplotlib.pyplot as plt
from common import load_network
from plot_sensitivity_dlr_cap import get_data

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

    diff = get_data(slr) - get_data(dlr)
    colors = ref.carriers.groupby("group").color.first()[diff.columns]
    percentage_index = lambda ind: int(ind * 100)

    # %%
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
