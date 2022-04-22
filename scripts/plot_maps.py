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
import seaborn as sns
from common import (
    add_carrier_legend,
    get_line_congestion,
    get_line_utilization,
    load_network,
    plot_shapes,
)
from pypsa.descriptors import get_switchable_as_dense as get_as_dense

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
    bus_size_factor = 0.001
    collection=n.plot(
        ax=ax,
        line_widths=line_width_factor,
        line_colors=f.get("Line"),
        line_cmap="viridis",
        link_widths=line_width_factor,
        link_colors=f.get("Link"),
        link_cmap="viridis",
        bus_sizes=bus_size_factor,
        bus_alpha=0.7,
        color_geomap=False,
        boundaries=bounds,
    )
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


def plot_capacity(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    # Plots capacity of all generators in MW, existing and newly built
    g = n.generators.p_nom_opt
    bus_sizes = g.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_sizes.drop("load", level=1, inplace=True)
    bus_size_factor = scale_bus_sizes(bus_sizes, bus_size_factor)
    link_widths = n.links.p_nom_opt
    line_widths = n.lines.s_nom_opt
    line_width_factor = scale_line_widths(line_widths, line_width_factor)
    if not n.lines_t.s_max_pu.empty:
        line_widths *= n.lines_t.s_max_pu.mean().reindex(n.lines.index, fill_value=1)

    n.plot(
        ax=ax,
        line_widths=line_widths * line_width_factor,
        link_widths=link_widths * line_width_factor,
        bus_sizes=bus_sizes * bus_size_factor,
        bus_alpha=0.7,
        color_geomap=False,
        boundaries=bounds,
    )
    return bus_size_factor, line_width_factor


def plot_curtailment(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    # Plots total curtailment in MWh of each generator over each time step
    curtailment = (
        (n.generators_t.p_max_pu * n.generators.p_nom_opt)
        .subtract(n.generators_t.p, axis="columns")
        .sum()
    )
    bus_sizes = curtailment.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_sizes.drop("load", level=1, inplace=True)
    bus_size_factor = scale_bus_sizes(bus_sizes, bus_size_factor)
    link_widths = n.links.p_nom_opt
    line_widths = n.lines.s_nom_opt
    line_width_factor = scale_line_widths(line_widths, line_width_factor)
    line_widths *= get_as_dense(n, "Line", "s_max_pu").mean()

    n.plot(
        ax=ax,
        line_widths=line_widths * line_width_factor,
        link_widths=link_widths * line_width_factor,
        bus_sizes=bus_sizes * bus_size_factor,
        bus_alpha=0.7,
        color_geomap=False,
        boundaries=bounds,
    )
    return bus_size_factor, line_width_factor


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_maps",
            year="2030",
            clusters="all",
            opts="Co2L-BL",
            ext="pdf",
        )
    plt.style.use("seaborn-colorblind")
    sns.set_context(
        "paper",
        rc={
            "font.size": 12,
            "axes.titlesize": 16,
            "axes.labelsize": 14,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
        },
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
            1, 2, figsize=(10, 6), subplot_kw={"projection": ccrs.EqualEarth()}
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
            n.carriers.sort_index(),
            size=refsize,
            scale=bus_size_factor,
            bbox_to_anchor=(1, 1),
            loc="upper left",
            frameon=False,
        )

        if output != "curtailment":
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
            loc="lower left",
            frameon=False,
        )

        fig.tight_layout()
        fig.savefig(snakemake.output[output], bbox_inches="tight")
