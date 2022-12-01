# -*- coding: utf-8 -*-
"""
Spyder Editor.

This is a temporary script file.
"""

import numpy as np
import pandas as pd
from common import load_network

slr2030 = load_network("../results/de2030_all_nodes_Co2L-RE0.8-Ep_dlr1.0_v.nc")
dlr2030 = load_network("../results/de2030_all_nodes_Co2L-RE0.8-Ep_dlr_v.nc")
slr2035 = load_network("../results/de2030_all_nodes_Co2L-RE1.0-Ep_dlr1.0_v.nc")
dlr2035 = load_network("../results/de2030_all_nodes_Co2L-RE1.0-Ep_dlr_v.nc")

rep = {"OCGT": "Natural Gas", "CCGT": "Natural Gas"}
slr2030.generators.carrier.replace(rep, inplace=True)
dlr2030.generators.carrier.replace(rep, inplace=True)

slr2035.generators.carrier.replace(rep, inplace=True)
dlr2035.generators.carrier.replace(rep, inplace=True)

# %% 80% VRES

today = {"Solar": 64, "Onshore Wind": 57.7, "Natural Gas": 32, "Offshore Wind": 8}
today = pd.Series(today)

df = pd.concat(
    [n.statistics.optimal_capacity() for n in [slr2030, dlr2030]],
    keys=["SLR", "DLR"],
    axis=1,
)

df["$\Delta$"] = df.DLR - df.SLR
df = df.div(1e3).round(1)
df["Unit"] = np.where(df.index.get_level_values(0) == "Store", "GWh", "GW")
df = df.loc[["Generator", "Link", "Store"]].droplevel(0)

df = pd.DataFrame({"Today": today, **df})
df = df.fillna("-")[df.SLR.ne(0) & df.DLR.ne(0)]

df = df.rename(index={"Battery Discharging": "Battery Discharge"})

idx = [
    "Solar",
    "Onshore Wind",
    "Offshore Wind",
    "Natural Gas",
    "Battery Discharge",
    "Battery Storage",
]

print(
    df.loc[idx]
    .style.to_latex(column_format="lrrrrc")
    .replace("00000", "")
    .replace(".0", "")
)

# %% 100% VRES

plan = {"Solar": 309, "Onshore Wind": 157, "Offshore Wind": 40}
plan = pd.Series(plan)

df = pd.concat(
    [n.statistics.optimal_capacity() for n in [slr2035, dlr2035]],
    keys=["SLR", "DLR"],
    axis=1,
)

df["$\Delta$"] = df.DLR - df.SLR
df = df.div(1e3).round(1)
df["Unit"] = np.where(df.index.get_level_values(0) == "Store", "GWh", "GW")
df = df.loc[["Generator", "Link", "Store"]].droplevel(0)

df = pd.DataFrame({"Plan": plan, **df})
df = df.fillna("-")[df.SLR.ne(0) & df.DLR.ne(0)]

df = df.rename(index={"Battery Discharging": "Battery Discharge"})

idx = [
    "Solar",
    "Onshore Wind",
    "Offshore Wind",
    "Battery Discharge",
    "Battery Storage",
    "Hydrogen Electrolysis",
    "Hydrogen Fuel Cell",
    "Hydrogen Storage",
]

print(
    df.loc[idx]
    .style.to_latex(column_format="lrrrrc")
    .replace("00000", "")
    .replace(".0", "")
)
