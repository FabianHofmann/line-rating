import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from common import keys, load_network
from matplotlib.style import available


def get_absolute_potential(n):
    renewables = n.generators[n.generators.carrier.str.contains(r"solar|wind")].index
    potential = (
        n.generators.p_nom_opt[renewables] * n.generators_t.p_max_pu[renewables]
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


def get_congestion_correlation(n):
    """
    This function plots the relation between congestion , overcapacity
    (renewable potential/load) and curtailment.

    This figure helps to understand how much energy is curtailed due to
    congestion and how much due to over supply.
    """
    c = "Generator"
    cols = n.pnl(c).p_max_pu.columns
    available = n.pnl(c).p_max_pu * n.df(c).p_nom_opt[cols]

    curtailment = (available - n.pnl(c).p[cols]).sum(axis=1)
    # max_curtailment.append(curtailment.max())

    over_capacity = available.sum(axis=1) / n.loads_t.p_set.sum(axis=1)

    c = "Line"
    congestion = (n.pnl(c).mu_lower.abs() + n.pnl(c).mu_upper.abs()).round(3) != 0
    cogestion = congestion.sum(axis=1)

    keys = ["Potential / Load", "Number of congested lines", "Curtailment [GW]"]
    df = pd.concat([over_capacity, cogestion, curtailment / 1e3], axis=1, keys=keys)
    return df.reset_index()


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_grid_stats",
            year="2020",
            clusters="all",
            opts="Co2L-BL",
            ext="pdf",
        )

    slr = load_network(snakemake.input.network_slr)
    dlr = load_network(snakemake.input.network_dlr)
    networks = [slr, dlr]

    # %% Potential Correlation
    n = dlr
    potential = get_absolute_potential(n)

    maximal_generation = potential.groupby("carrier").generation.transform(max)
    potential["normed"] = potential.generation / maximal_generation
    potential["normed_rounded"] = potential.normed.round(1)

    carriers = n.carriers.loc[potential.carrier.unique()]
    potential.replace(dict(carrier=n.carriers.nice_name), inplace=True)

    color = carriers.set_index("nice_name").color.to_dict()

    # %%
    fig, ax = plt.subplots(figsize=(5, 3.5))
    sns.lineplot(
        data=potential,
        x="normed_rounded",
        y="transmission",
        hue="carrier",
        style="carrier",
        # palette=color,
        # ci='sd',
        estimator="mean",
        ax=ax,
    )
    ax.legend(title="")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Weighted-Average Capacity Factor")
    ax.set_ylabel("Total DLR / Total SLR")
    ax.grid(True, linestyle="--", linewidth=0.5)
    fig.tight_layout()
    fig.savefig(snakemake.output.potential_correlation, bbox_inches="tight")

    # %%
    df = pd.concat(
        [get_congestion_correlation(n).assign(Scenario=n.name) for n in networks],
        ignore_index=True,
    )
    fig, axes = plt.subplots(1, 2, figsize=(4.5, 6), sharey=True)
    norm = plt.Normalize(df["Curtailment [GW]"].min(), df["Curtailment [GW]"].max())
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    for key, ax in zip(["Static Line Rating", "Dynamic Line Rating"], axes):
        sns.scatterplot(
            data=df.query("Scenario == @key"),
            x="Potential / Load",
            y="Number of congested lines",
            hue="Curtailment [GW]",
            hue_norm=norm,
            size="Curtailment [GW]",
            size_norm=norm,
            sizes=(0, 100),
            linewidth=0,
            ax=ax,
            palette="viridis",
            legend=False,
            zorder=3,
        )
        ax.grid(True, axis="both", linestyle="--", linewidth=0.5, zorder=0)
        ax.set_xlim(left=0)
    fig.tight_layout()
    fig.colorbar(
        sm, ax=axes, orientation="horizontal", label="Curtailment [GW]", fraction=0.1
    )
    fig.savefig(snakemake.output.congestion_correlation, bbox_inches="tight")


# %%
