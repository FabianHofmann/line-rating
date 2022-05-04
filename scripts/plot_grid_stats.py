import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from common import keys, load_network
from matplotlib.style import available
from plot_maps import scale_bus_sizes, scale_line_widths


def get_absolute_potential(n):
    renewables = n.generators[n.generators.carrier.str.contains(r"solar|wind")].index
    potential = (
        n.generators.p_nom_opt[renewables] * n.generators_t.p_max_pu[renewables]
    ) / 1e3  # in GW
    potential = potential.groupby(n.generators.carrier, axis=1).sum(1)
    potential = potential.reset_index().melt(
        id_vars="snapshot", value_name="generation"
    )

    capacity = n.generators.loc[renewables].groupby("carrier").p_nom_opt.sum() / 1e3
    potential = potential.join(capacity.rename("capacity"), on="carrier")

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


def get_congestion_hours_price(n):
    c = "Line"
    congestion_price = (n.pnl(c).mu_lower.abs() + n.pnl(c).mu_upper.abs()).sum(axis=1)
    number_lines_congested = (n.pnl(c).mu_lower.abs() + n.pnl(c).mu_upper.abs()).round(
        2
    ) != 0
    number_lines_congested = number_lines_congested.sum(axis=1)
    congestion = pd.concat(
        [number_lines_congested, congestion_price],
        keys=["Number of congested lines", "Shadow price"],
        axis=1,
    )
    congestion = congestion.sort_values(
        "Number of congested lines", ascending=False
    ).reset_index(drop=True)
    return congestion.reset_index()


def plot_line_overlay(networks, line_width_factor=None, bus_size_factor=None):
    config = snakemake.config["plotting"]["map"]
    line_width_factor = config["capacity"]["line_width_factor"]

    bounds = config["boundaries"]
    fig, ax = plt.subplots(
        1,
        1,
        figsize=config["figsize"],
        subplot_kw={"projection": ccrs.EqualEarth()},
    )

    for n in networks[::-1]:
        link_widths = n.links.p_nom_opt
        line_widths = n.lines.s_nom_opt
        line_widths *= n.get_switchable_as_dense("Line", "s_max_pu").mean()

        if "Static" in n.name:
            alpha = 1
            line_color = "orange"
            g = n.generators.p_nom_opt
            bus_sizes = g.groupby([n.generators.bus, n.generators.carrier]).sum()
            bus_sizes.drop("load", level=1, inplace=True)
            bus_sizes = 0.002
        else:
            alpha = 1
            line_color = "purple"
            bus_sizes = 0

        collection = n.plot(
            ax=ax,
            line_widths=line_widths * line_width_factor,
            link_widths=link_widths * line_width_factor,
            bus_alpha=0.3,
            bus_sizes=bus_sizes,
            line_colors=line_color,
            boundaries=bounds,
        )
        collection[1].set_alpha(alpha)
    fig.tight_layout()
    return fig


def plot_potential_correlation(n):
    potential = get_absolute_potential(n)

    potential["normed"] = potential.generation / potential.capacity
    new = []
    for carrier in potential.carrier.unique():
        cpotential = potential[potential.carrier == carrier].sort_values("normed")
        cpotential["order"] = np.arange(len(cpotential))
        cpotential["order_groups"] = pd.cut(cpotential.order, 73)
        cpotential["normed_groups"] = cpotential.groupby(
            "order_groups"
        ).normed.transform("mean")
        new.append(cpotential)
    potential = pd.concat(new, ignore_index=True)

    carriers = n.carriers.loc[potential.carrier.unique()]
    color = carriers.set_index("nice_name").color.to_dict()
    potential.replace(dict(carrier=n.carriers.nice_name), inplace=True)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    sns.lineplot(
        data=potential,
        x="normed_groups",
        y="transmission",
        hue="carrier",
        style="carrier",
        estimator="mean",
        ax=ax,
    )
    ax.legend(title="")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Capacity-Weighted Capacity Factor")
    ax.set_ylabel("Total DLR / Total SLR")
    ax.grid(True, linestyle="--", linewidth=0.5)
    fig.tight_layout()
    return fig


def plot_congestion_correlation(n):
    df = pd.concat(
        [get_congestion_correlation(n).assign(Scenario=n.name) for n in networks],
        ignore_index=True,
    )
    fig, axes = plt.subplots(1, 2, figsize=(5, 6), sharey=True)
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
        ax.set_title(key)
        ax.grid(True, axis="both", linestyle="--", linewidth=0.5, zorder=0)
        ax.set_xlim(left=0)
    fig.tight_layout()
    fig.colorbar(
        sm, ax=axes, orientation="horizontal", label="Curtailment [GW]", fraction=0.1
    )
    return fig


def plot_congestion_duration_curve(networks):
    fig, ax = plt.subplots(figsize=(5, 3.5))
    data = pd.concat(
        [get_congestion_hours_price(n).assign(Scenario=n.name) for n in networks],
        ignore_index=True,
    ).rename({"index": "Hour"}, axis=1)
    sns.lineplot(
        data=data,
        x="Hour",
        y="Number of congested lines",
        style="Scenario",
        # hue="Shadow price",
        ax=ax,
        #estimator="sum",
    )
    fig.tight_layout()
    return fig


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_grid_stats",
            year="2030",
            clusters="all",
            opts="Co2L-RE0.8-Ep",
            ext="pdf",
        )

    slr = load_network(snakemake.input.network_slr)
    dlr = load_network(snakemake.input.network_dlr)
    networks = [slr, dlr]

    fig = plot_potential_correlation(dlr)
    fig.savefig(snakemake.output.potential_correlation, bbox_inches="tight")

    fig = plot_congestion_correlation(networks)
    fig.savefig(snakemake.output.congestion_correlation, bbox_inches="tight")

    fig = plot_line_overlay(networks)
    fig.savefig(snakemake.output["line_capacity_overlay"], bbox_inches="tight")

    fig = plot_congestion_duration_curve(networks)
    fig.savefig(snakemake.output["congestion_duration_curve"], bbox_inches="tight")
