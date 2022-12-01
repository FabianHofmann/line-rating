import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from common import load_network

font = font_manager.FontProperties(family="Times New Roman", style="normal", size=11)
sns.set(font="Times New Roman")


def get_operation(n):
    pg = (
        n.generators_t.p.sum()
        .groupby(n.generators.carrier)
        .sum()
        .drop("load", errors="ignore")
    )
    s = n.storage_units_t.p.sum().groupby(n.storage_units.carrier).sum()
    p = pd.concat([pg, s]).groupby(n.carriers.group).sum()
    return p.rename(n.name)


def get_capacity(n, storage_cap=True):
    gens = n.generators.groupby("carrier").p_nom_opt.sum().drop("load", errors="ignore")

    if storage_cap:
        stos = n.stores.groupby(["carrier"]).e_nom_opt.sum()
    else:
        buses = n.buses.query("carrier == 'AC'").index
        stos = n.links.groupby(["bus1", "carrier"]).p_nom_opt.sum()
        if not stos.empty:
            stos = stos.loc[buses].groupby("carrier").sum().drop("DC")
    return pd.concat([gens, stos]).rename(n.name)


def get_curtailment(n):
    renewables = n.generators[n.generators.carrier.str.contains(r"solar|wind")].index
    curtailment = (
        (n.generators_t.p_max_pu[renewables] * n.generators.p_nom_opt[renewables])
        .subtract(n.generators_t.p[renewables], axis="columns")
        .multiply(n.snapshot_weightings["generators"], axis=0)
        .sum()
    )
    curtailment = curtailment.groupby(n.generators.carrier).sum().rename(n.name)

    return curtailment / 1e6  # in TWh


def get_adapted_curtailment(n):
    renewables = n.generators[n.generators.carrier.str.contains(r"solar|wind")].index
    potential = n.generators_t.p_max_pu[renewables] * n.generators.p_nom_opt[renewables]
    curtailment = (
        potential.subtract(n.generators_t.p[renewables], axis="columns")
        .multiply(n.snapshot_weightings["generators"], axis=0)
        .sum(axis=1)
    )
    storage_unit_demand = (
        (
            n.storage_units.eval("p_nom_opt*max_hours")
            - n.storage_units_t.state_of_charge
        )
        .div(n.storage_units.efficiency_store)
        .replace(np.inf, np.nan)
    )
    store_demand = (n.stores.e_nom_opt - n.stores_t.e) / n.links.set_index("bus1").loc[
        n.stores.bus, "efficiency"
    ]
    demand = (
        storage_unit_demand.sum(axis=1)
        + store_demand.sum(axis=1)
        + n.loads_t.p.sum(axis=1)
    )
    over_supply = potential.sum(axis=1) - demand
    curtailment = (curtailment - over_supply.where(over_supply > 0)).sum()
    return curtailment / 1e6  # in TWh


def get_relative_curtailment(n):
    renewables = n.generators[n.generators.carrier.str.contains(r"solar|wind")].index
    curtailment = (
        (n.generators_t.p_max_pu[renewables] * n.generators.p_nom_opt[renewables])
        .subtract(n.generators_t.p[renewables], axis="columns")
        .multiply(n.snapshot_weightings["generators"], axis=0)
        .mean()
    )
    curtailment = curtailment / n.generators.p_nom_opt[renewables]

    curtailment = curtailment.groupby(n.generators.carrier).mean().rename(n.name)

    return curtailment * 100  # in %


def get_costs(n):
    gopex = n.generators_t.p.sum() * n.generators.marginal_cost
    gopex = gopex.groupby(n.generators.carrier).sum().drop("load", errors="ignore")
    lopex = n.links_t.p0.sum() * n.links.marginal_cost
    lopex = lopex.groupby(n.links.carrier).sum().drop("DC", errors="ignore")
    sopex = n.stores_t.e.sum() * n.stores.marginal_cost
    sopex = sopex.groupby(n.stores.carrier).sum()

    opex = pd.concat([gopex, lopex, sopex])

    gcapex = (n.generators.p_nom_opt - n.generators.p_nom) * n.generators.capital_cost
    gcapex = gcapex.groupby(n.generators.carrier).sum().drop("load", errors="ignore")
    lcapex = (n.links.p_nom_opt - n.links.p_nom) * n.links.capital_cost
    lcapex = lcapex.groupby(n.links.carrier).sum().drop("DC", errors="ignore")
    scapex = (n.stores.e_nom_opt - n.stores.e_nom) * n.stores.capital_cost
    scapex = scapex.groupby(n.stores.carrier).sum()

    capex = pd.concat([gcapex, lcapex, scapex])

    costs = pd.concat({"OPEX": opex, "CAPEX": capex}, axis=1)
    costs = costs.groupby(n.carriers.group).sum()

    order = n.carriers.groupby("group").co2_emissions.mean().sort_values()
    costs = costs.reindex(order.index)
    costs = costs[costs.abs().sum(1) >= 5e6][::-1]

    return costs


def plot_operation_difference(ax, networks):
    ref = networks[0]
    operation = pd.concat((get_operation(n) for n in networks), axis=1)
    operation /= 1e6  # in TWh
    operation = operation["Dynamic Line Rating"] - operation["Static Line Rating"]
    operation.sort_values(ascending=False, inplace=True)

    colors = ref.carriers.groupby("group").color.first()[operation.index]
    operation.plot(kind="barh", ax=ax, zorder=4, color=colors, alpha=0.7)
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_xlabel("Energy [TWh]")
    ax.set_ylabel("")
    ax.set_title("Supplied Energy: DLR vs. SLR ")


def plot_capacity(ax, networks):
    capacities = pd.concat((get_capacity(n) for n in networks), axis=1)
    capacities /= 1000  # in GW
    capacities.sort_values(networks[0].name, ascending=False, inplace=True)
    capacities.plot(kind="barh", ax=ax, zorder=4, legend="reverse")
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_yticklabels(slr.carriers.nice_name[capacities.index])
    ax.set_xlabel("Capacity [GW]")
    ax.set_ylabel("")
    ax.set_title("Installed Generation Capacities")


def plot_curtailment(ax, networks):
    curtailment = pd.concat([get_curtailment(n) for n in networks], axis=1)
    curtailment.plot(kind="bar", ax=ax, zorder=4, legend="reverse")
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_xticklabels(slr.carriers.nice_name[curtailment.index], rotation="horizontal")
    ax.set_ylabel("Curtailment in TWh")
    ax.set_xlabel("")
    ax.set_title("Curtailment of Renewable Energy")


def plot_relative_curtailment(ax, networks):
    curtailment = pd.concat([get_relative_curtailment(n) for n in networks], axis=1)
    curtailment.plot(kind="bar", ax=ax, zorder=4, legend="reverse")
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_xticklabels(slr.carriers.nice_name[curtailment.index], rotation="horizontal")
    ax.set_ylabel("Average Relative Curtailment in %")
    ax.set_xlabel("")
    ax.set_title("Relative Curtailment")


def plot_historical_curtailment(ax, networks):
    historical_curtailment = pd.read_csv(snakemake.input.curtailment_data, index_col=0)
    historical_curtailment = historical_curtailment["2019"]
    historical_curtailment = historical_curtailment.rename("Historical curtailment")
    historical_curtailment /= 1000  # in TWh

    modeled_curtailment = pd.concat([get_curtailment(n) for n in networks], axis=1)

    curtailment = pd.concat(
        [historical_curtailment, modeled_curtailment], axis=1, join="inner"
    )
    curtailment.plot(kind="bar", ax=ax, zorder=4)
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_xticklabels(slr.carriers.nice_name[curtailment.index], rotation="horizontal")
    ax.set_ylabel("Curtailment in TWh")
    ax.set_xlabel("")
    ax.set_title("Curtailment of energy")


def plot_cost(ax, networks):
    costs = get_costs(networks[0]) - get_costs(networks[1])
    costs /= 1e6
    costs.plot.barh(stacked=True, ax=ax, zorder=4, legend="reverse")
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_ylabel("")
    ax.set_xlabel("Cost [m€]")
    ax.set_title("Total Cost Savings")


def plot_capex_opex(ax, networks):
    costs = (
        pd.concat(
            [get_costs(networks[1]), get_costs(networks[0])],
            axis=1,
            keys=[networks[1].name, networks[0].name],
        )
        .dropna()
        .div(1e9)
    )
    ind = np.arange(len(costs.index))  # the x locations for the groups
    width = 0.35
    slr_color = "#4c72b0"
    dlr_color = "#dd8452"
    ax.bar(
        x=ind - width / 2,
        height=costs.loc[:, ("Dynamic Line Rating", "CAPEX")],
        width=width,
        color=dlr_color,
        label="DLR CAPEX",
    )
    ax.bar(
        x=ind - width / 2,
        height=costs.loc[:, ("Dynamic Line Rating", "OPEX")],
        bottom=costs.loc[:, ("Dynamic Line Rating", "CAPEX")],
        width=width,
        color=dlr_color,
        hatch="xx",
        label="DLR OPEX",
    )
    ax.bar(
        x=ind + width / 2,
        height=costs.loc[:, ("Static Line Rating", "CAPEX")],
        width=width,
        color=slr_color,
        label="SLR CAPEX",
    )
    ax.bar(
        x=ind + width / 2,
        height=costs.loc[:, ("Static Line Rating", "OPEX")],
        bottom=costs.loc[:, ("Static Line Rating", "CAPEX")],
        width=width,
        color=slr_color,
        hatch="xx",
        label="SLR OPEX",
    )
    ax.set_xticks(ind, costs.index)
    plt.setp(ax.get_xticklabels(), rotation=30, horizontalalignment="right")
    ax.legend()
    ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
    ax.set_xlabel("")
    ax.set_ylabel("Cost [bn€]")
    ax.set_title("Total Cost")


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_bars",
            year="2030",
            clusters="all",
            opts="Co2L-RE0.8-Ep",
            rating="",
            angle="",
            ext="pdf",
        )

    slr = load_network(snakemake.input.network_slr, name="Static Line Rating")
    dlr = load_network(snakemake.input.network_dlr, name="Dynamic Line Rating")
    networks = slr, dlr

    config = snakemake.config["plotting"]["bar"]

    for output in snakemake.output.keys():
        figconfig = config.get(output, {})

        fig, ax = plt.subplots(figsize=figconfig.get("figsize", (8, 5)))
        plot_func = eval(f"plot_{output}")
        plot_func(ax, networks)
        fig.tight_layout()
        fig.savefig(snakemake.output[output], bbox_inches="tight")
