#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 21 17:37:55 2022.

@author: fabian
"""
import atlite
import cartopy.crs as ccrs
import common
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pypsa
import seaborn as sns

sns.set(font="Times New Roman")

from shapely.geometry import LineString as Line
from shapely.geometry import Point

if "snakemake" not in globals():
    from _helpers import mock_snakemake

    snakemake = mock_snakemake("plot_line_rating_calculation", ext="pdf")

n = pypsa.Network(snakemake.input.network)

cutout = atlite.Cutout(snakemake.input.cutout)


# %%

t = n.snapshots[100]

nlargest = 8
line = n.lines.length.sort_values(ascending=False).index[nlargest]
sub = n[n.lines.loc[line, ["bus0", "bus1"]].values]

(x0, y0), (x1, y1) = pypsa.plot.compute_bbox_with_margins(0.2, sub.buses.x, sub.buses.y)
# bounds = np.ravel(bounds)[[0,2,1,3]]
scutout = cutout.sel(time=[t], x=slice(x0, x1), y=slice(y0, y1))

buses = n.lines[["bus0", "bus1"]].values
x = n.buses.x
y = n.buses.y
shapes = [Line([Point(x[b0], y[b0]), Point(x[b1], y[b1])]) for (b0, b1) in buses]
shapes = gpd.GeoSeries(shapes, index=n.lines.index, crs=4326)
nodes = gpd.GeoSeries([Point(x[b], y[b]) for b in n.buses.index], crs=4326)

overlap_shapes = gpd.overlay(shapes.to_frame(), scutout.grid)
overlap_nodes = gpd.overlay(nodes.to_frame(), scutout.grid)
line_shapes = gpd.overlay(shapes.to_frame().loc[[line]], scutout.grid)

rating = scutout.line_rating(line_shapes.geometry, 9.39e-5)

line_shapes["rating"] = rating.sel(time=t).to_series()

# %%
cbar_kwargs = {
    "ticks": [],
    "orientation": "horizontal",
    "drawedges": False,
    "pad": 0.04,
    "aspect": 40,
}

fig, ax = plt.subplots(figsize=(5, 3.5), subplot_kw={"projection": ccrs.EqualEarth()})
overlap_nodes.plot(ax=ax, zorder=6, color="lightgrey", lw=4, alpha=1)
# overlap_shapes.plot(ax=ax, color='grey', zorder=0)
ckwargs = {**cbar_kwargs, "label": "Line Rating"}
line_shapes.plot(
    zorder=5,
    column="rating",
    ax=ax,
    legend=True,
    lw=3,
    legend_kwds=ckwargs,
    cmap="viridis",
    vmin=rating.min() - 50,
)
ckwargs = {**cbar_kwargs, "label": "Wind Speed"}
wind = scutout.data.wnd100m.sel(time=t)
vmin = wind.min().compute().item() - 5
wind.plot(
    ax=ax,
    alpha=0.8,
    cmap="Blues",
    cbar_kwargs=ckwargs,
    vmin=vmin,
    edgecolor="None",
    zorder=1,
)

ax.set_title("")
fig.tight_layout()
fig.savefig(snakemake.output.figure)
