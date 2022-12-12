#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 16 13:53:32 2021.

@author: fabian
"""

import common
import matplotlib.font_manager as font_manager
import numpy as np
import pandas as pd
import seaborn as sns
import xarray as xr
from atlite.convert import convert_line_rating as line_rating
from xarray import DataArray, Dataset

font = font_manager.FontProperties(family="Times New Roman", style="normal", size=11)
sns.set(font="Times New Roman")

if "snakemake" not in globals():
    from _helpers import mock_snakemake

    snakemake = mock_snakemake("plot_parameter_space", kind="reduced")

t = np.arange(-10, 40, 0.5)
celsius = xr.IndexVariable("Temperature", t, {"units": "°C"})
T = DataArray(t + 273.15, coords={"Temperature": celsius}, dims="Temperature")

w = np.arange(0, 25, 0.1).round(2)
speed = xr.IndexVariable("Wind speed", w, attrs={"units": "m/s"})
W = DataArray(w, coords={"Wind speed": speed}, dims="Wind speed")

if snakemake.wildcards.kind == "full":
    angle = np.arange(0, 100, 10)
    col_wrap = 3
else:
    angle = [0, 45, 90]
    col_wrap = 1

degree = xr.IndexVariable("Wind angle", angle, attrs={"units": "°"})
degree_str = degree.round(0).astype(int).astype(str).astype(object) + "°"
A = DataArray(
    np.deg2rad(angle),
    coords={"Wind angle": degree_str},
    dims="Wind angle",
)

ds = Dataset(
    {
        "height": 0,
        "influx_direct": 1027,
        "wnd100m": W,
        "wnd_azimuth": A,
        "temperature": T,
    }
)

ds = ds.expand_dims("spatial")
ds = ds.assign_coords(time=pd.DatetimeIndex(["2020-01-01 13:00"]), lat=35, lon=0)

R = 9.39e-5  # resistance per meter at 80°C
psi = 0
i = line_rating(ds, psi, R, Ts=353)
v = 380  # kV
s = np.sqrt(3) * i * v / 1e3  # in MW
s = s.squeeze()

F = s.plot.contourf(
    x="Wind speed",
    y="Temperature",
    col="Wind angle",
    col_wrap=col_wrap,
    aspect=1.2,
    size=3,
    cbar_kwargs={
        "orientation": "horizontal",
        "label": "Line power capacity [MW]",
        "aspect": 20,
        "location": "top",
        "shrink": 1,
        "pad": 0.07,
    },
)
F.fig.savefig(snakemake.output.figure, bbox_inches="tight")
