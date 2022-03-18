from importlib import reload

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from common import add_carrier_legend, load_network, plot_shapes


def plot_capacity_bar(ax, networks):
    capacities=pd.concat([n.generators.groupby("carrier").p_nom_opt.sum().drop("load", errors='ignore').rename(n.name) for n in networks], axis=1)/1000 #in GW
    capacities.plot(kind='bar', ax=ax)
    ax.set_xticklabels(list(slr.carriers.nice_name.loc[capacities.index]))
    ax.set_ylabel("Capacity in GW")
    ax.set_xlabel("Generator")
    ax.set_title("Capacity of generators")
    

def plot_curtailment_bar(ax, networks):
    def get_curtail_data(n):
        relevant_generators=n.generators_t.p_max_pu.columns
        curtailment=(n.generators_t.p_max_pu * n.generators.p_nom_opt.loc[relevant_generators]).subtract(n.generators_t.p.loc[:,relevant_generators], axis="columns").sum()
        curtailment.index = n.generators.loc[relevant_generators].set_index(['bus','carrier']).index
        curtailment=curtailment.groupby("carrier").sum().rename(n.name)
        return curtailment
    curtailment=pd.concat([get_curtail_data(n) for n in networks], axis=1)
    curtailment.plot(kind='bar', ax=ax)
    ax.set_xticklabels(list(slr.carriers.nice_name.loc[curtailment.index]))
    ax.set_ylabel("Curtailment in MWh")
    ax.set_xlabel("Generator")
    ax.set_title("Curtailment of energy")
    



if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_analysis",
            year="2020",
            clusters="40",
            opts="Co2L-4H",
            ext="png",
        )


    slr = load_network(snakemake.input.network_slr)
    dlr = load_network(snakemake.input.network_dlr)
    shapes = gpd.read_file(snakemake.input.shapes)
    networks = slr, dlr

    for output in snakemake.output.keys():

        fig, ax = plt.subplots(
            1, 1, figsize=(10, 6)
        )

        plot_func = eval(f"plot_{output}")
        plot_func(ax, networks)


        fig.tight_layout()
        fig.savefig(snakemake.output[output], bbox_inches="tight")
