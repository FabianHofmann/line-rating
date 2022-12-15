import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pypsa
from common import load_network


def normed(s):
    return s / s.sum()


def run_power_flow(network):
    # calculate voltage angles
    v_ang = network.buses_t.v_ang
    v_ang_diff = v_ang[network.lines.bus0].values - v_ang[network.lines.bus1].values
    v_ang_diff = pd.DataFrame(
        v_ang_diff, index=v_ang.index, columns=network.lines.index
    )

    # For the PF, set the P to the optimised P
    network.generators_t.p_set = network.generators_t.p
    network.stores_t.p_set = network.stores_t.p

    # set all buses to PV, since we don't know what Q set points are
    network.generators.control = "PV"

    # neglect storage buses
    # storage_filter=network.buses.index[network.buses.carrier != "AC"]
    # network.buses.drop(storage_filter, axis=0, inplace=True)

    # Need some PQ buses so that Jacobian doesn't break
    f = network.generators[network.generators.bus == network.generators.bus.iloc[0]]
    network.generators.loc[f.index, "control"] = "PQ"

    # by dispatch
    return network.pf(distribute_slack=True, slack_weights="p_set")


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "run_power_flow",
            year="2030",
            clusters="all",
            opts="Co2L-RE1.0-Ep",
            rating="",
            angle="",
            ext="pdf",
        )

    res = {}
    losses_pf = {}
    total_transmission_lpf = {}
    total_transmission_pf = {}
    for name in ["network_slr", "network_dlr"]:
        n = load_network(snakemake.input[name])
        total_transmission_lpf[name] = (n.lines_t.p0).abs().div(1e6).sum().sum()
        r = run_power_flow(n)
        res[n.name] = r["converged"]
        losses_pf[name] = (n.lines_t.p0 + n.lines_t.p1).abs().div(1e6).sum().sum()
        total_transmission_pf[name] = (
            (n.lines_t.p0.clip(lower=0) + n.lines_t.p1.clip(lower=0))
            .div(1e6)
            .sum()
            .sum()
        )
    res = pd.concat(res, axis=1).droplevel(1, axis=1)
    results = pd.DataFrame(
        [total_transmission_lpf, total_transmission_pf, losses_pf],
        index=["total_lpf", "total_pf", "losses_pf"],
    )

    fig, ax = plt.subplots(figsize=(5, 3.5))
    res.sum().plot(kind="line", ax=ax)
    fig.tight_layout()
    fig.savefig(snakemake.output[0])

    results.to_csv(snakemake.output[1])
