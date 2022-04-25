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

    # stos = n.stores.groupby(["carrier"]).e_nom_opt.sum()
    buses = n.buses.query("carrier == 'AC'").index
    stos = n.links.groupby(["bus1", "carrier"]).p_nom_opt.sum()
    if not stos.empty:
        stos = stos.loc[buses].groupby("carrier").sum().drop("DC")
    return pd.concat([gens, stos]).rename(n.name)


def get_costs(n):
    gopex = n.generators_t.p.sum() * n.generators.marginal_cost
    gopex = gopex.groupby(n.generators.carrier).sum().drop("load")
    lopex = n.links_t.p0.sum() * n.links.marginal_cost
    lopex = lopex.groupby(n.links.carrier).sum().drop("DC")
    sopex = n.stores_t.e.sum() * n.stores.marginal_cost
    sopex = sopex.groupby(n.stores.carrier).sum()

    opex = pd.concat([gopex, lopex, sopex])

    gcapex = n.generators.p_nom_opt * n.generators.capital_cost
    gcapex = gcapex.groupby(n.generators.carrier).sum().drop("load")
    lcapex = n.links.p_nom_opt * n.links.capital_cost
    lcapex = lcapex.groupby(n.links.carrier).sum().drop("DC")
    scapex = n.stores.e_nom_opt * n.stores.capital_cost
    scapex = scapex.groupby(n.stores.carrier).sum()

    capex = pd.concat([gcapex, lcapex, scapex])

    costs = pd.concat({"OPEX": opex, "CAPEX": capex}, axis=1)
    costs = costs.groupby(n.carriers.group).sum()

    order = n.carriers.groupby("group").co2_emissions.mean().sort_values()
    costs = costs.reindex(order.index)
    costs = costs[costs.abs().sum(1) >= 5e6][::-1]

    return costs


def plot_capacity(ax, networks):
    capacities = pd.concat((get_capacity(n) for n in networks), axis=1)
    capacities /= 1000  # in GW
    capacities.sort_values(networks[0].name, ascending=False, inplace=True)
    capacities.plot(kind="barh", ax=ax, zorder=4)
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_yticklabels(slr.carriers.nice_name[capacities.index])
    ax.set_xlabel("Capacity in GW")
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


def plot_cost(ax, networks):
    costs = get_costs(networks[0]) - get_costs(networks[1])
    costs /= 1e6
    costs.plot.barh(stacked=True, ax=ax, zorder=4)
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_ylabel("")
    ax.set_xlabel("Cost [Million €]")
    # ax.axes.xaxis.set_ticks([])
    ax.set_title("Total Cost Savings")


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

    config = snakemake.config["plotting"]["bar"]

    for output in snakemake.output.keys():
        figconfig = config.get(output, {})

        fig, ax = plt.subplots(figsize=figconfig.get("figsize", (8, 5)))
        plot_func = eval(f"plot_{output}")
        plot_func(ax, networks)
        fig.tight_layout()
        fig.savefig(snakemake.output[output], bbox_inches="tight")
