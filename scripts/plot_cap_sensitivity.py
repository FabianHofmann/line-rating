#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 12 10:25:36 2022.

@author: fabian
"""

import matplotlib.pyplot as plt
import pandas as pd
from common import load_network
from plot_bars import get_capacity, get_costs, get_curtailment

year = snakemake.wildcards["year"]
keys = snakemake.config[f"scenario_{year}"]["rating"]
networks = {k: load_network(p) for k, p in zip(keys, snakemake.input.networks)}

ref = networks[keys[0]]
gcolors = ref.carriers.groupby("group").color.first()
ccolors = ref.carriers.set_index("nice_name").color

costs = pd.DataFrame({name: get_costs(n).sum(1) for name, n in networks.items()}).T

curtailment = pd.DataFrame({name: get_curtailment(n) for name, n in networks.items()}).T
curtailment = curtailment.rename(columns=ref.carriers.nice_name)

capacity = pd.DataFrame({name: get_capacity(n) for name, n in networks.items()}).T
capacity = capacity.rename(columns=ref.carriers.nice_name)

# %%

fig, ax = plt.subplots()
costs.div(1e9).plot.area(ax=ax, color=gcolors[costs.columns], legend="reverse")
ax.legend(title="", bbox_to_anchor=(1, 1), loc="upper left")
ax.set_xlabel("Maximally allowed rating")
ax.set_ylabel("System Costs [bn€]")
# fig.savefig(snakemake.output.sensitivity_cost)


fig, ax = plt.subplots()
curtailment.plot.area(ax=ax, color=ccolors[curtailment.columns], legend="reverse")
ax.legend(title="", bbox_to_anchor=(1, 1), loc="upper left")
ax.set_xlabel("Maximally allowed rating")
ax.set_ylabel("Curtailment [TWh]")
# fig.savefig(snakemake.output.sensitivity_curtailment)


fig, ax = plt.subplots()
capacity.plot.area(ax=ax, color=ccolors[capacity.columns], legend="reverse")
ax.legend(title="", bbox_to_anchor=(1, 1), loc="upper left")
ax.set_xlabel("Maximally allowed rating")
ax.set_ylabel("Curtailment [TWh]")
# fig.savefig(snakemake.output.sensitivity_capacity)
