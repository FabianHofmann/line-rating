#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 10:20:17 2022.

@author: fabian
"""

from importlib import reload

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from common import add_carrier_legend, load_network, plot_shapes


def plot_operation(ax, n, bus_size_factor, line_width_factor, bounds):
    g = n.generators_t.p.mean()
    g = g.groupby([n.generators.bus, n.generators.carrier]).sum()

    f = pd.concat({c: n.pnl(c).p0.mean() for c in ["Line", "Link"]})

    n.plot(
        ax=ax,
        flow=f * line_width_factor,
        bus_sizes=g * bus_size_factor,
        color_geomap=False,
        boundaries=bounds,
        line_colors="purple",
    )


def plot_capacity(ax, n, bus_size_factor, line_width_factor, bounds):
    g = n.generators.p_nom_opt
    bus_sizes = g.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_sizes.drop("load", level=1, inplace=True)

    link_widths = n.links.p_nom_opt
    line_widths = n.lines.s_nom_opt
    if not n.lines_t.s_max_pu.empty:
        line_widths *= n.lines_t.s_max_pu.mean().reindex(n.lines.index, fill_value=1)

    n.plot(
        ax=ax,
        line_widths=line_widths * line_width_factor,
        link_widths=link_widths * line_width_factor,
        bus_sizes=bus_sizes * bus_size_factor,
        color_geomap=False,
        boundaries=bounds,
    )


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_maps",
            year="2030",
            clusters="all",
            opts="Co2L",
            ext="pdf",
        )

    config = snakemake.config["plotting"]["map"]
    bounds = config["boundaries"]

    dlr = load_network(snakemake.input.network_dlr)
    slr = load_network(snakemake.input.network_slr)
    networks = dlr, slr
    shapes = gpd.read_file(snakemake.input.shapes)

    for output in snakemake.output.keys():

        fig, axes = plt.subplots(
            1, 2, figsize=(10, 6), subplot_kw={"projection": ccrs.EqualEarth()}
        )

        bus_size_factor = config[output]["bus_size_factor"]
        line_width_factor = config[output]["line_width_factor"]
        refsize = config[output]["refsize"]

        for (n, ax) in zip(networks, axes):
            plot_func = eval(f"plot_{output}")
            plot_func(ax, n, bus_size_factor, line_width_factor, bounds)
            plot_shapes(ax, shapes, edgecolor="white", facecolor="#eeeeee")
            ax.set_title(n.name, fontsize=11)

        add_carrier_legend(
            ax,
            n.carriers.sort_index(),
            size=refsize,
            scale=bus_size_factor,
            bbox_to_anchor=(1, 1),
            loc="upper left",
            frameon=False,
        )
        refcirc = pd.Series(["white", "k"], index=["color", "edgecolor"])
        refcirc = refcirc.to_frame(f"{round(refsize/1000)} GW").T
        add_carrier_legend(
            ax,
            refcirc,
            size=refsize,
            scale=bus_size_factor,
            bbox_to_anchor=(1, 0),
            loc="lower left",
            frameon=False,
        )

        fig.tight_layout()
        fig.savefig(snakemake.output[output], bbox_inches="tight")
