#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct  2 16:28:34 2021.

@author: fabian
"""

import atlite
import geopandas as gpd
import numpy as np
import pypsa
import xarray as xr
from shapely.geometry import LineString as Line
from shapely.geometry import Point

# n = pypsa.examples.ac_dc_meshed()
n = pypsa.Network("/home/fabian/vres/py/pypsa-eur/networks/elec.nc")
n.calculate_dependent_values()
x = n.buses.x
y = n.buses.y
buses = n.lines[["bus0", "bus1"]].values

shapes = [Line([Point(x[b0], y[b0]), Point(x[b1], y[b1])]) for (b0, b1) in buses]
shapes = gpd.GeoSeries(shapes, index=n.lines.index)

cutout = atlite.Cutout(
    "test",
    x=slice(x.min(), x.max()),
    y=slice(y.min(), y.max()),
    time="2020-01-01",
    module="era5",
    dx=1,
    dy=1,
)
cutout.prepare()

i = cutout.line_rating(shapes, n.lines.r / 1e3)
v = xr.DataArray(n.lines.v_nom, dims="name")
s = np.sqrt(3) * i * v / 1e3  # in MW

# Alternatively, the units nicely play out when we use the per unit system
# while scaling the resistance with a factor 1000.

s = np.sqrt(3) * cutout.line_rating(shapes, n.lines.r_pu * 1e3)  # in MW
