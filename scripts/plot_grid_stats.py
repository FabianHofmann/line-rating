import pandas as pd
import seaborn as sns
from common import keys, load_network


def absolute_potential(n):
    renewables = n.generators_t.p_max_pu.columns
    potential = (
        n.generators.p_nom_opt[renewables] * n.generators_t.p_max_pu
    ) / 1e3  # in GW
    potential = potential.groupby(n.generators.carrier, axis=1).sum(1)
    potential = potential.reset_index().melt(
        id_vars="snapshot", value_name="generation"
    )

    line_potential = (n.lines.s_nom_opt * n.lines_t.s_max_pu).sum(
        1
    ) / n.lines.s_nom_opt.sum()
    potential["transmission"] = potential.snapshot.map(line_potential)
    return potential


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_grid_stats",
            year="2020",
            clusters="5",
            opts="Co2L-4H",
            ext="pdf",
        )

    # config = snakemake.config["plotting"]["map"]
    slr = load_network(snakemake.input.network_slr)
    dlr = load_network(snakemake.input.network_dlr)

    # %% Potential Correlation
    n = dlr
    potential = absolute_potential(n)
    carriers = n.carriers.loc[potential.carrier.unique()]
    potential.replace(dict(carrier=n.carriers.nice_name), inplace=True)
    g = sns.FacetGrid(
        potential, col="carrier", hue="carrier", palette=carriers.color, sharex=False
    )
    g.map(sns.scatterplot, "generation", "transmission")
    g.set_titles("{col_name}")
    g.set_xlabels("Generation potential [GW]")
    g.set_ylabels("Total DLR / Total SLR")
    g.figure.savefig(snakemake.output.potential_correlation)
