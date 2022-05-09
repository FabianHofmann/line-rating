#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  3 10:20:17 2022.

@author: fabian
"""

from importlib import reload

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from common import (
    add_carrier_legend,
    get_line_congestion,
    get_line_utilization,
    load_network,
    plot_shapes,
)
from pypsa.descriptors import get_switchable_as_dense as get_as_dense

font = font_manager.FontProperties(family="Times New Roman", style="normal", size=11)

# ---------------------------------------------------------------------------- #
#    Functions to automatically scale line width and bus sizes in map plots    #
# ---------------------------------------------------------------------------- #


def scale_bus_sizes(bus_sizes, bus_size_factor):
    if bus_size_factor is None:
        max_size_factor = 0.16
        bus_size_factor = max_size_factor / bus_sizes.groupby("bus").sum().max()
    return bus_size_factor


def scale_line_widths(line_widths, line_width_factor):
    if line_width_factor is None:
        max_line_factor = 5
        line_width_factor = max_line_factor / line_widths.max()
    return line_width_factor


# ---------------------------------------------------------------------------- #
#                               Helper functions                               #
# ---------------------------------------------------------------------------- #
# def get_line_utilization(n):
#     if n.name=="Static Line Rating":
#         f=np.abs(n.lines_t.p0).divide(n.lines.s_nom_opt * n.lines.s_max_pu, axis=1).mean()
#     elif n.name=="Dynamic Line Rating":
#         f=np.abs((n.lines_t.p0 / n.lines_t.s_max_pu)).divide(n.lines.s_nom_opt, axis=1).mean()
#     f=(f-f.min())/(f.max()-f.min())
#     return
#
def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=100):
    new_cmap = colors.LinearSegmentedColormap.from_list(
        "trunc({n},{a:.2f},{b:.2f})".format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n)),
    )
    return new_cmap


# ---------------------------------------------------------------------------- #
#                              Plotting functions                              #
# ---------------------------------------------------------------------------- #


def plot_utilization(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    g = n.generators_t.p.mean()
    g = g.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_size_factor = scale_bus_sizes(g, bus_size_factor)
    f = pd.concat({"Line": line_util[n.name + "_mean_nom"]})
    line_width_factor = scale_line_widths(f, line_width_factor)
    n.plot(
        ax=ax,
        flow=f * line_width_factor * 2,
        bus_sizes=g * bus_size_factor,
        bus_alpha=0.7,
        color_geomap=False,
        boundaries=bounds,
    )
    return bus_size_factor, line_width_factor


def plot_congestion(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    comps = ["Line", "Link"]
    f = pd.concat(
        {
            c: ((n.pnl(c).mu_lower.abs() + n.pnl(c).mu_upper.abs()).round(3) != 0).sum()
            for c in comps
        }
    )
    f = f.where(n.branches().carrier.isin(["AC", "DC"]).reindex_like(f), 0)
    line_width_factor = scale_line_widths(f, line_width_factor)

    curtailment = (
        (n.generators_t.p_max_pu * n.generators.p_nom_opt)
        .subtract(n.generators_t.p, axis="columns")
        .sum()
    )
    bus_sizes = curtailment.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_sizes.drop("load", level=1, inplace=True)
    bus_size_factor = scale_bus_sizes(bus_sizes, bus_size_factor)

    # Scale colorbar
    cmap = cm.get_cmap("viridis", 256)
    vmin = 0  # minimum value to show on colobar
    vmax = 5000  # maximum value to show on colobar
    norm = colors.Normalize(vmin=vmin, vmax=vmax)

    collection = n.plot(
        ax=ax,
        line_widths=line_width_factor,
        line_colors=f.get("Line"),
        line_cmap=cmap,
        link_widths=line_width_factor,
        bus_sizes=bus_sizes * bus_size_factor,
        bus_alpha=0.7,
        color_geomap=False,
        boundaries=bounds,
    )
    collection[1].set(norm=norm)

    if "Dynamic" in n.name:
        plt.colorbar(collection[1], ax=ax, fraction=0.046, pad=0.004)

    return bus_size_factor, line_width_factor


def plot_operation(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    # Plots mean power generation over all time steps in MW
    g = n.generators_t.p.mean()
    g = g.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_size_factor = scale_bus_sizes(g, bus_size_factor)
    f = pd.concat({c: n.pnl(c).p0.mean() for c in ["Line", "Link"]})
    line_width_factor = scale_line_widths(f, line_width_factor)
    n.plot(
        ax=ax,
        flow=f * line_width_factor,
        bus_sizes=g * bus_size_factor,
        bus_alpha=0.7,
        color_geomap=False,
        boundaries=bounds,
        line_colors="purple",
    )
    return bus_size_factor, line_width_factor


def plot_capacity(
    ax, n, bounds, bus_size_factor=None, line_width_factor=None, with_colormap=False
):
    # Plots capacity of all generators in MW, existing and newly built
    g = n.generators.p_nom_opt
    bus_sizes = g.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_sizes.drop("load", level=1, inplace=True)
    bus_size_factor = scale_bus_sizes(bus_sizes, bus_size_factor)
    link_widths = n.links.p_nom_opt
    line_widths = n.lines.s_nom_opt
    line_width_factor = scale_line_widths(line_widths, line_width_factor)
    if with_colormap:
        cmap = cm.get_cmap("viridis", 256)
        line_colors = n.get_switchable_as_dense("Line", "s_max_pu").mean() / 0.7
        norm = colors.Normalize(vmin=line_colors.min(), vmax=line_colors.max())
    else:
        cmap = None
        line_colors = "purple"
        line_widths *= n.get_switchable_as_dense("Line", "s_max_pu").mean() / 0.7

    collection = n.plot(
        ax=ax,
        line_widths=line_widths * line_width_factor,
        link_widths=link_widths * line_width_factor,
        line_colors=line_colors,
        line_cmap=cmap,
        bus_sizes=bus_sizes * bus_size_factor,
        bus_alpha=0.7,
        color_geomap=False,
        boundaries=bounds,
    )

    if with_colormap:
        collection[1].set(norm=norm)
        plt.colorbar(collection[1], ax=ax, fraction=0.04, pad=0.004, label="DLR / SLR")

    return bus_size_factor, line_width_factor


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_maps",
            year="2020",
            clusters="all",
            opts="Co2L-BL-Ep",
            ext="pdf",
        )

    config = snakemake.config["plotting"]["map"]
    bounds = config["boundaries"]

    slr = load_network(snakemake.input.network_slr)
    dlr = load_network(snakemake.input.network_dlr)
    networks = slr, dlr
    shapes = gpd.read_file(snakemake.input.shapes)

    line_util = get_line_utilization(networks)
    line_congestion = get_line_congestion(networks)

    for output in snakemake.output.keys():

        fig, axes = plt.subplots(
            1,
            2,
            figsize=config["figsize"],
            subplot_kw={"projection": ccrs.EqualEarth()},
        )

        refsize = config[output]["refsize"]
        bus_size_factor = config[output].get("bus_size_factor", None)
        line_width_factor = config[output].get("line_width_factor", None)

        for (n, ax) in zip(networks, axes):
            plot_func = eval(f"plot_{output}")
            bus_size_factor, line_width_factor = plot_func(
                ax, n, bounds, bus_size_factor, line_width_factor
            )
            plot_shapes(ax, shapes, edgecolor="white", facecolor="#eeeeee")
            ax.set_title(n.name, fontsize=11)
        add_carrier_legend(
            ax,
            n.carriers.query('color != ""').sort_index(),
            size=refsize,
            ncol=4,
            scale=bus_size_factor,
            prop=font,
            bbox_to_anchor=(0, 0),
            loc="upper left",
            frameon=False,
        )

        if output != "curtailment" and output != "congestion":
            unit = "GW"
        else:
            unit = "GWh"
        refcirc = pd.Series(["white", "k"], index=["color", "edgecolor"])
        refcirc = refcirc.to_frame(f"{round(refsize/1000)} {unit}").T
        add_carrier_legend(
            ax,
            refcirc,
            size=refsize,
            scale=bus_size_factor,
            bbox_to_anchor=(1, 0),
            loc="lower right",
            prop=font,
            frameon=False,
            framealpha=0.2,
            edgecolor="grey",
        )

        fig.tight_layout(pad=0)
        fig.savefig(snakemake.output[output], bbox_inches="tight")

        if output == "capacity":

            n = dlr
            fig, ax = plt.subplots(
                figsize=(4.5, 4), subplot_kw={"projection": ccrs.EqualEarth()}
            )
            bus_size_factor, line_width_factor = plot_capacity(
                ax, n, bounds, bus_size_factor, line_width_factor, with_colormap=True
            )
            plot_shapes(ax, shapes, edgecolor="white", facecolor="#eeeeee")
            add_carrier_legend(
                ax,
                n.carriers.query('color != ""').sort_index(),
                prop=font,
                size=refsize,
                ncol=2,
                scale=bus_size_factor,
                bbox_to_anchor=(0, 0.03),
                loc="upper left",
                frameon=False,
            )

            refcirc = pd.Series(["white", "k"], index=["color", "edgecolor"])
            refcirc = refcirc.to_frame(f"{round(refsize/1000)} {unit}").T
            add_carrier_legend(
                ax,
                refcirc,
                prop=font,
                size=refsize,
                scale=bus_size_factor,
                bbox_to_anchor=(0, 0),
                loc="lower left",
                frameon=False,
                framealpha=0.2,
                edgecolor="grey",
            )

            fig.tight_layout(pad=0)
            path = snakemake.output[output].rsplit(".", 1)
            path = path[0] + f"_dlr." + path[1]
            fig.savefig(path, bbox_inches="tight")
