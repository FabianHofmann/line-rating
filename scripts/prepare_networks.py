"""
This script changes the network file such that the parameters of the dynamic
line rating are deleted.

Afterwards the solve_network script can be rerun to obtain a solution
with the same grid without line raitng.
"""

import pandas as pd
import numpy as np
import pypsa

if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "prepare_networks",
            year="2030",
            clusters="all",
            opts="Co2L-RE0.8-Ep",
            rating="1.3",
            angle="45"
        )

    n = pypsa.Network(snakemake.input.network)

    max_rating = snakemake.wildcards["rating"]
    max_voltage_difference=snakemake.wildcards["angle"]
    if max_rating:
        max_rating = float(max_rating)
        if max_rating == 1:
            n.lines_t.s_max_pu.drop(n.lines_t.s_max_pu.columns, axis=1, inplace=True)
        else:
            n.lines_t.s_max_pu = n.lines_t.s_max_pu.clip(upper=max_rating)
    if max_voltage_difference:
        max_voltage_difference=float(max_voltage_difference)
        n.calculate_dependent_values()
        x_pu = n.lines.x_pu
        s_max_pu_cap = (np.deg2rad(max_voltage_difference) / (x_pu * n.lines.s_nom)).clip(lower=1)
        n.lines_t.s_max_pu = n.lines_t.s_max_pu.clip(upper=s_max_pu_cap, axis=1)

    n.export_to_netcdf(snakemake.output.network)
