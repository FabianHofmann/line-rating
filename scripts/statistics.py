#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 25 15:52:30 2022.

@author: fabian
"""

import pandas as pd
import pypsa
from _helpers import mock_snakemake


def totals(df):
    df = df.div(1e6).round(3)
    return pd.concat(
        {"Total [TWh]": df, "Share [%]": (df / df.sum() * 100).round(3)},
        axis=1,
    )


if "snakemake" not in globals():
    snakemake = mock_snakemake(
        "describe_network",
        year=2030,
        clusters="all",
        opts="Co2L-RE0.8-Ep",
        rating="1.0",
        angle="",
        format="md",
    )


def out(key, df, fn):
    f = snakemake.wildcards["format"]
    if f == "tex":
        print("", key, "", df.to_latex(), sep="\n", file=fn)
    elif f == "md":
        print("", key, "", df.to_markdown(), sep="\n", file=fn)
    else:
        raise ValueError(f"Format {f} not supported")


n = pypsa.Network(snakemake.input.network)
fn = open(snakemake.output.description, "w")

kwargs = dict(aggregate_time="sum")
production = n.statistics.supply(**kwargs)

p = production.loc["Generator"]
out("Generation:", totals(p), fn)

fossils = ["Lignite", "Coal", "Open-Cycle Gas", "Combined-Cycle Gas"]
out("Fossil generation:", totals(p).reindex(index=fossils).sum(), fn)

offshore = ["Offshore Wind (AC)", "Offshore Wind (DC)"]
out("Offshore generation:", totals(p).loc[offshore].sum(), fn)


fn.close()
