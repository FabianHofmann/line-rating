#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  7 12:36:38 2022.

@author: fabian
"""

import pandas as pd
import pypsa

slr = pypsa.Network(
    "/home/fabian/papers/line-rating/results/de2030_all_nodes_Co2L-RE0.8-Ep_dlr1.0_v.nc"
)
dlr = pypsa.Network(
    "/home/fabian/papers/line-rating/results/de2030_all_nodes_Co2L-RE0.8-Ep_dlr_v.nc"
)


today = slr.statistics.installed_capacity()
slr_capacity = slr.statistics.optimal_capacity()
dlr_capacity = dlr.statistics.optimal_capacity()

keys = ["Pre-Installed", "Static Line Rating", "Dynamic Line Rating"]
df = pd.concat([today, slr_capacity, dlr_capacity], keys=keys, axis=1)

cfs = [slr.statistics.capacity_factor(), dlr.statistics.capacity_factor()]
cfs = pd.concat(cfs, axis=1, keys=["SLR", "DLR"])

cfs.loc["Generator"].plot.bar()

supply = [
    slr.statistics.supply(aggregate_time="sum"),
    dlr.statistics.supply(aggregate_time="sum"),
]
supply = pd.concat(supply, axis=1, keys=["SLR", "DLR"])

supply.loc["Generator"].plot.bar()

curtailment = [
    slr.statistics.curtailment(aggregate_time="sum"),
    dlr.statistics.curtailment(aggregate_time="sum"),
]
curtailment = -pd.concat(curtailment, axis=1, keys=["SLR", "DLR"])

curtailment.loc["Generator"].plot.bar()
