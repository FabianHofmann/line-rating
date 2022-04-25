import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from common import load_network

def plot_congestion_correlation(networks):
    fig, axes = plt.subplots(
            1, 2, figsize=(10, 6), sharey=True
        )
    
    for (n, ax) in zip(networks, axes):
        curtailment = ((n.generators_t.p_max_pu * n.generators.p_nom_opt).subtract(n.generators_t.p, axis="columns")).sum(axis=1)
        congestion= ((n.pnl("Line").mu_lower.abs() + n.pnl("Line").mu_upper.abs()).round(3) != 0)
        print(f"The correlation is {curtailment.corr(congestion.sum(axis=1))}")
        curtailment_norm=curtailment.to_frame().apply(lambda x :(x-x.min())/(x.max()-x.min()))
        cogestion=congestion.sum(axis=1)
        over_capacity=(n.generators_t.p_max_pu * n.generators.p_nom_opt).sum(axis=1)/n.loads_t.p_set.sum(axis=1)
        sc=ax.scatter(x=over_capacity, y=cogestion, s=curtailment_norm*100, c=curtailment, cmap="viridis", zorder=5)
        ax.set_xlim(xmax=4)
        ax.grid(linestyle="--", linewidth=0.5, alpha=0.5, zorder=2)
        
        ax.set_xlabel("Potential / Load")
        ax.set_title(f"Congestion Correlation {n.name}")
        ax.yaxis.set_tick_params(which='both')
    axes[0].set_ylabel("Number of Lines Congested")
    fig.colorbar(sc,orientation='vertical')
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
