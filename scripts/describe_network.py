#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 25 15:52:30 2022.

@author: fabian
"""

import numpy as np
import pandas as pd
import pypsa
from _helpers import mock_snakemake
from common import load_network


def totals(df):
    df = df.div(1e6).round(3)
    return pd.concat(
        {"Total [TWh]": df, "Share [%]": (df / df.sum() * 100).round(3)},
        axis=1,
    )


if "snakemake" not in globals():
    snakemake = mock_snakemake(
        "describe_network",
        year=2020,
        clusters="all",
        opts="Co2L-BL-Ep",
        rating="1.0",
        angle="",
        format="md",
    )


n = load_network(snakemake.input.network)
fn = open(snakemake.output.description, "w")


def out(key, df):
    f = snakemake.wildcards["format"]
    if f == "tex":
        print("", key, "", df.to_latex(), sep="\n", file=fn)
    elif f == "md":
        print("", key, "", df.to_markdown(), sep="\n", file=fn)
    else:
        raise ValueError(f"Format {f} not supported")


kwargs = dict(aggregate_time="sum")
production = n.statistics.supply(**kwargs)

p = production.loc["Generator"]
out("Generation:", totals(p))

fossils = ["Lignite", "Coal", "Open-Cycle Gas", "Combined-Cycle Gas"]
out("Fossil generation:", totals(p).loc[fossils].sum())

opex = n.statistics.opex(**kwargs).sum() / 1e6
print("", "OPEX [m€]", "", opex, sep="\n", file=fn)

capex = n.statistics.capex().sum() / 1e6
print("", "CAPEX [m€]", "", capex, sep="\n", file=fn)

out("Installed Capacity [GW]", n.statistics.installed_capacity() / 1e3)

out("Optimized Capacity [GW]", n.statistics.optimal_capacity() / 1e3)

supply = n.statistics.supply(**kwargs).Generator
ef = n.carriers.set_index("nice_name").co2_emissions[supply.index]
emissions = supply @ ef / 1e6
print("", "CO2 emissions [Mt]:", "", emissions, sep="\n", file=fn)

np.rad2deg(n.lines_t.p0 * n.lines.x_pu).max().max()
print("", "Maximum Voltage Difference [deg]:", "", emissions, sep="\n", file=fn)


fn.close()
