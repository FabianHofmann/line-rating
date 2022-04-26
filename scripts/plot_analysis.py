import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import seaborn as sns
from common import load_network

def plot_congestion_correlation(networks):
    '''
    This function plots the relation between congestion , overcapacity (renewable potential/load) and curtailment.
    This figure helps to understand how much energy is curtailed due to congestion and how much due to over supply.
    '''
    fig, axes = plt.subplots(
            1, 2, figsize=(10, 6), sharey=True
        )
    cmap = plt.get_cmap('viridis')
    max_curtailment=list()
    for (n, ax) in zip(networks, axes):
        curtailment = ((n.generators_t.p_max_pu * n.generators.p_nom_opt).subtract(n.generators_t.p, axis="columns")).sum(axis=1)
        max_curtailment.append(curtailment.max())
        congestion= ((n.pnl("Line").mu_lower.abs() + n.pnl("Line").mu_upper.abs()).round(3) != 0)
        print(f"The correlation is {curtailment.corr(congestion.sum(axis=1))}")
        curtailment_norm=curtailment.to_frame().apply(lambda x :(x-x.min())/(x.max()-x.min()))
        cogestion=congestion.sum(axis=1)
        over_capacity=(n.generators_t.p_max_pu * n.generators.p_nom_opt).sum(axis=1)/n.loads_t.p_set.sum(axis=1)
        sc=ax.scatter(x=over_capacity, y=cogestion, s=curtailment_norm*100, c=curtailment, cmap=cmap, zorder=5)
        ax.set_xlim(xmax=4)
        ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
        ax.set_xlabel("Potential / Load")
        ax.set_title(f"Congestion Correlation {n.name}")
        ax.yaxis.set_tick_params(which='both')
    axes[0].set_ylabel("Number of Lines Congested")
    norm = mpl.colors.Normalize(vmin=0,vmax=max(max_curtailment))
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    def formatter_func(x, pos):
        return f"{x/1000}"
    fig.colorbar(sm,orientation='vertical', format=formatter_func, label="Curtailment in GWh")
    return fig

def plot_wind_congestion_correlation(networks):
    '''
    This function plots the relation between congestion , wind overcapacity (renewable potential/load) and wind curtailment.
    This figure helps to understand how much wind is curtailed due to congestion and how much due to over supply.
    '''
    fig, axes = plt.subplots(
            1, 2, figsize=(10, 6), sharey=True
        )
    cmap = plt.get_cmap('viridis')
    max_curtailment=list()
    for (n, ax) in zip(networks, axes):
        filter_wind=n.generators.index[n.generators.index.str.contains("wind")]
        curtailment = ((n.generators_t.p_max_pu[filter_wind] * n.generators.p_nom_opt.loc[filter_wind]).subtract(n.generators_t.p[filter_wind], axis="columns")).sum(axis=1)
        max_curtailment.append(curtailment.max())
        congestion= ((n.pnl("Line").mu_lower.abs() + n.pnl("Line").mu_upper.abs()).round(3) != 0)
        print(f"The correlation is {curtailment.corr(congestion.sum(axis=1))}")
        curtailment_norm=curtailment.to_frame().apply(lambda x :(x-x.min())/(x.max()-x.min()))
        cogestion=congestion.sum(axis=1)
        over_capacity=(n.generators_t.p_max_pu[filter_wind] * n.generators.p_nom_opt.loc[filter_wind]).sum(axis=1)/n.loads_t.p_set.sum(axis=1)
        sc=ax.scatter(x=over_capacity, y=cogestion, s=curtailment_norm*100, c=curtailment, cmap=cmap, zorder=5)
        ax.set_xlim(xmax=4)
        ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
        ax.set_xlabel("Potential / Load")
        ax.set_title(f"Congestion Correlation Wind {n.name}")
        ax.yaxis.set_tick_params(which='both')
    axes[0].set_ylabel("Number of Lines Congested")
    norm = mpl.colors.Normalize(vmin=0,vmax=max(max_curtailment))
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    def formatter_func(x, pos):
        return f"{x/1000}"
    fig.colorbar(sm,orientation='vertical', format=formatter_func, label="Curtailment in GWh")
    return fig   

if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_analysis",
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
    
    fig=plot_congestion_correlation(networks)
    fig.tight_layout()
    fig.savefig(snakemake.output["congestion_correlation"], bbox_inches="tight")

    fig=plot_wind_congestion_correlation(networks)
    fig.tight_layout()
    fig.savefig(snakemake.output["congestion_wind_correlation"], bbox_inches="tight")
