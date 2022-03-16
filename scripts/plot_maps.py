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

def scale_bus_sizes(bus_sizes, bus_size_factor):
    if bus_size_factor is None:
        max_size_factor = 0.16
        bus_size_factor = max_size_factor/bus_sizes.groupby("bus").sum().max()
    return bus_size_factor

def scale_line_widths(line_widths, line_width_factor):
    if line_width_factor is None:
        max_line_factor = 5
        line_width_factor = max_line_factor/line_widths.max()
    return line_width_factor

def plot_operation(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    #Plots mean power generation over all time steps in MW
    g = n.generators_t.p.mean()
    g = g.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_size_factor=scale_bus_sizes(g, bus_size_factor)
    f = pd.concat({c: n.pnl(c).p0.mean() for c in ["Line", "Link"]})
    line_width_factor=scale_line_widths(f, line_width_factor)
    n.plot(
        ax=ax,
        flow=f * line_width_factor,
        bus_sizes=g * bus_size_factor,
        color_geomap=False,
        boundaries=bounds,
    )
    return bus_size_factor, line_width_factor


def plot_capacity(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    #Plots capacity of all generators in MW, existing and newly built
    g = n.generators.p_nom_opt
    bus_sizes = g.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_sizes.drop("load", level=1, inplace=True)
    bus_size_factor=scale_bus_sizes(bus_sizes, bus_size_factor)
    link_widths = n.links.p_nom_opt
    line_widths = n.lines.s_nom_opt
    line_width_factor=scale_line_widths(line_widths, line_width_factor)
    if not n.lines_t.s_max_pu.empty:
        line_widths *= n.lines_t.s_max_pu.mean()

    n.plot(
        ax=ax,
        line_widths=line_widths * line_width_factor,
        link_widths=link_widths * line_width_factor,
        bus_sizes=bus_sizes * bus_size_factor,
        color_geomap=False,
        boundaries=bounds,
    )
    return bus_size_factor, line_width_factor

def plot_curtailment(ax, n, bounds, bus_size_factor=None, line_width_factor=None):
    #Plots total curtailment in MWh of each generator over each time step
    curtailment=(n.generators_t.p_max_pu * n.generators.p_nom_opt).subtract(n.generators_t.p, axis="columns").sum()
    bus_sizes = curtailment.groupby([n.generators.bus, n.generators.carrier]).sum()
    bus_sizes.drop("load", level=1, inplace=True)
    bus_size_factor=scale_bus_sizes(bus_sizes, bus_size_factor)
    link_widths = n.links.p_nom_opt
    line_widths = n.lines.s_nom_opt
    line_width_factor=scale_line_widths(line_widths, line_width_factor)
    if not n.lines_t.s_max_pu.empty:
        line_widths *= n.lines_t.s_max_pu.mean()

    n.plot(
        ax=ax,
        line_widths=line_widths * line_width_factor,
        link_widths=link_widths * line_width_factor,
        bus_sizes=bus_sizes * bus_size_factor,
        color_geomap=False,
        boundaries=bounds,
    )
    return bus_size_factor, line_width_factor

if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_maps",
            year="2020",
            clusters="40",
            opts="Co2L-4H",
            ext="png",
        )

    config = snakemake.config["plotting"]["map"]
    bounds = config["boundaries"]

    slr = load_network(snakemake.input.network_slr)
    dlr = load_network(snakemake.input.network_dlr)
    networks = slr, dlr
    shapes = gpd.read_file(snakemake.input.shapes)

    for output in snakemake.output.keys():

        fig, axes = plt.subplots(
            1, 2, figsize=(10, 6), subplot_kw={"projection": ccrs.EqualEarth()}
        )

        refsize = config[output]["refsize"]
        bus_size_factor = None
        line_width_factor = None

        for (n, ax) in zip(networks, axes):
            plot_func = eval(f"plot_{output}")
            bus_size_factor, line_width_factor = plot_func(ax, n, bounds, bus_size_factor, line_width_factor)
            plot_shapes(ax, shapes)
            ax.set_title(n.name)

        add_carrier_legend(
            ax,
            n.carriers,
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
