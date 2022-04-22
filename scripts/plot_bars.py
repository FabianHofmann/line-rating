import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from common import load_network


def get_curtail_data(n):
    variables = n.generators_t.p_max_pu.columns
    curtailment = (
        (n.generators_t.p_max_pu * n.generators.p_nom_opt[variables])
        .subtract(n.generators_t.p[variables], axis="columns")
        .multiply(n.snapshot_weightings["generators"], axis=0)
        .sum()
    )
    # curtailment.index = (
    #     n.generators.loc[variables].set_index(["bus", "carrier"]).index
    # )
    curtailment = curtailment.groupby(n.generators.carrier).sum().rename(n.name)
    return curtailment / 1e6  # in TWh


def get_capacity(n):
    gens = n.generators.groupby("carrier").p_nom_opt.sum().drop("load", errors="ignore")

    #stos = n.stores.groupby(["carrier"]).e_nom_opt.sum()
    buses = n.buses.query("carrier == 'AC'").index
    stos = n.links.groupby(["bus1", "carrier"]).p_nom_opt.sum().loc[buses].groupby("carrier").sum().drop("DC")
    stos.rename(index={"H2 fuel cell":"H2","battery discharger":"battery"}, inplace=True)
    return pd.concat([gens, stos]).rename(n.name)


def plot_capacity(ax, networks):
    capacities = pd.concat((get_capacity(n) for n in networks), axis=1)
    capacities /= 1000  # in GW(h)
    capacities.sort_values(networks[0].name, ascending=False, inplace=True)
    capacities.plot(kind="barh", ax=ax, zorder=4)
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_yticklabels(slr.carriers.nice_name[capacities.index])
    ax.set_xlabel("Capacity in GW/GWh")
    ax.set_ylabel("")
    ax.set_title("Capacity of generators")


def plot_curtailment(ax, networks):
    curtailment = pd.concat([get_curtail_data(n) for n in networks], axis=1)
    curtailment.plot(kind="bar", ax=ax, zorder=4)
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_xticklabels(slr.carriers.nice_name[curtailment.index], rotation="horizontal")
    ax.set_ylabel("Curtailment in TWh")
    ax.set_xlabel("")
    ax.set_title("Curtailment of energy")


def plot_historical_curtailment(ax, networks):
    historical_curtailment = pd.read_csv(snakemake.input.curtailment_data, index_col=0)
    historical_curtailment = historical_curtailment["2019"]
    historical_curtailment = historical_curtailment.rename("Historical curtailment")
    historical_curtailment /= 1000  # in TWh

    modeled_curtailment = pd.concat([get_curtail_data(n) for n in networks], axis=1)

    curtailment = pd.concat(
        [historical_curtailment, modeled_curtailment], axis=1, join="inner"
    )
    curtailment.plot(kind="bar", ax=ax, zorder=4)
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_xticklabels(slr.carriers.nice_name[curtailment.index], rotation="horizontal")
    ax.set_ylabel("Curtailment in TWh")
    ax.set_xlabel("")
    ax.set_title("Curtailment of energy")


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_bars",
            year="2030",
            clusters="all",
            opts="Co2L-RE0.8",
            ext="pdf",
        )

    plt.style.use("seaborn-colorblind")
    sns.set_context(
        "paper",
        rc={
            "font.size": 12,
            "axes.titlesize": 12,
            "axes.labelsize": 12,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
        },
    )
    slr = load_network(snakemake.input.network_slr)
    dlr = load_network(snakemake.input.network_dlr)
    networks = slr, dlr

    fig, ax = plt.subplots(figsize=(5, 8))
    plot_capacity(ax, networks)
    fig.tight_layout()
    fig.savefig(snakemake.output["capacity"], bbox_inches="tight")

    fig, ax = plt.subplots(figsize=(8, 5))
    plot_curtailment(ax, networks)
    fig.tight_layout()
    fig.savefig(snakemake.output["curtailment"], bbox_inches="tight")

    fig, ax = plt.subplots(figsize=(8, 5))
    plot_historical_curtailment(ax, networks)
    fig.tight_layout()
    fig.savefig(snakemake.output["historical_curtailment"], bbox_inches="tight")
