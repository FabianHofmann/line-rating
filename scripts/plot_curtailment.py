"""
Only preliminary code for plotting the line data.

Not working yet with the snakemake workflow.
Path to results with line rating and without line rating has to specified.
TODO: Find a way how to automate the workflow. So far only idea using wildcards instead of config.
"""

import matplotlib.pyplot as plt
import pypsa

plt.style.use("bmh")
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.mpl.geoaxes
import numpy as np
import pandas as pd


def add_subplot_axes(fig, ax, rect):  # ,axisbg='w'):
    box = ax.get_position(original=False)
    width = box.width
    height = box.height
    axis_to_data = ax.transAxes + ax.transData.inverted()
    data_to_axis = axis_to_data.inverted()
    inax_position = data_to_axis.transform(rect[0:2])
    fig_to_ax = fig.transFigure + ax.transAxes.inverted()
    ax_to_fig = fig_to_ax.inverted()
    infig_position = ax_to_fig.transform(inax_position)
    x = infig_position[0]
    y = infig_position[1]
    width *= rect[2]
    height *= rect[3]
    subax = fig.add_axes([x, y, width, height])  # ,axisbg=axisbg)
    x_labelsize = subax.get_xticklabels()[0].get_size()
    y_labelsize = subax.get_yticklabels()[0].get_size()
    x_labelsize *= rect[2] ** 0.5
    y_labelsize *= rect[3] ** 0.5
    subax.xaxis.set_tick_params(labelsize=x_labelsize)
    subax.yaxis.set_tick_params(labelsize=y_labelsize)
    subax.axis("off")
    return subax


def get_arrow_parameters(plot_data_lines, line, figure):
    x0 = plot_data_lines.loc[line]["x0"]
    x1 = plot_data_lines.loc[line]["x1"]
    y0 = plot_data_lines.loc[line]["y0"]
    y1 = plot_data_lines.loc[line]["y1"]

    x = (x0 + x1) / 2
    y = (y0 + y1) / 2
    dx = (x1 - x0) / 100
    if plot_data_lines.loc[line][f"flow_direction_{figure}"] > 0:
        dy = (y1 - y0) / (x1 - x0) * dx
    elif plot_data_lines.loc[line][f"flow_direction_{figure}"] < 0:
        dy = -(y1 - y0) / (x1 - x0) * dx
        dx = -dx
    else:
        dx = 0
        dy = 0
    return x, y, dx, dy


if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "plot_curtailment",
            network="elec",
            simpl="",
            clusters="40",
            ll="v1.0",
            opts="Co2L-4H",
            ext="png",
        )

    n = {
        "lr": pypsa.Network(snakemake.input.lr),
        "nolr": pypsa.Network(snakemake.input.nolr),
    }

    ### Line and Bus Location Data

    def sign(x):
        return np.sign(x)

    plot_data_buses = (
        n["nolr"].buses[n["nolr"].buses.carrier == "AC"].loc[:, ["x", "y"]]
    )

    plot_data_lines = pd.DataFrame(
        index=n["nolr"].lines.index, columns=["x0", "x1", "y0", "y1"]
    )
    for line in n["nolr"].lines.index:
        bus0 = n["nolr"].lines.loc[line]["bus0"]
        bus1 = n["nolr"].lines.loc[line]["bus1"]
        plot_data_lines.loc[line]["x0"] = n["nolr"].buses.loc[bus0]["x"]
        plot_data_lines.loc[line]["x1"] = n["nolr"].buses.loc[bus1]["x"]
        plot_data_lines.loc[line]["y0"] = n["nolr"].buses.loc[bus0]["y"]
        plot_data_lines.loc[line]["y1"] = n["nolr"].buses.loc[bus1]["y"]

    ### Line Flow Data
    plot_data_lines["mean_p_nolr"] = np.abs(n["nolr"].lines_t["p0"].mean(axis=0))
    plot_data_lines["mean_p_lr"] = np.abs(n["lr"].lines_t["p0"].mean(axis=0))
    plot_data_lines["flow_direction_nolr"] = (
        n["nolr"].lines_t["p0"].mean(axis=0).transform(sign)
    )
    plot_data_lines["flow_direction_lr"] = (
        n["lr"].lines_t["p0"].mean(axis=0).transform(sign)
    )

    ###Curtailment Data

    results = ["nolr", "lr"]
    gen_curtail = {}
    for result in results:
        # first curtailment is summed over all snapshots-> for single snap shot do not use .sum() and overwrite columns instead of index in next row
        curtail = (
            (n[result].generators_t.p_max_pu * n[result].generators.p_nom_opt)
            .subtract(n[result].generators_t.p, axis="columns")
            .sum()
        )
        # ignore generator dummy
        curtail = curtail.drop("dummy", axis=0, errors="ignore")
        curtail.index = (
            n[result].generators.groupby(["bus", "carrier"]).p_nom_opt.sum().index
        )
        curtail.dropna(inplace=True)
        gen_curtail.update({result: curtail})

    max_bus_curtail = max(
        [
            gen_curtail["nolr"].groupby("bus").sum().max(),
            gen_curtail["lr"].groupby("bus").sum().max(),
        ]
    )
    # max_wind_curtail=max([gen_curtail["nolr"][gen_curtail["nolr"].index.get_level_values("carrier").str.contains("wind")].groupby("bus").sum().max(),gen_curtail["lr"][gen_curtail["lr"].index.get_level_values("carrier").str.contains("wind")].groupby("bus").sum().max()])

    ### Plots
    figures_name = {"nolr": "Static line rating", "lr": "Dynamic line rating"}
    figures = ["nolr", "lr"]
    # used to scale all wind extension at buses with the max_wind_expansion

    fig, ax = plt.subplots(
        1, 2, figsize=(25, 10), subplot_kw={"projection": ccrs.PlateCarree()}
    )
    divider = np.max([plot_data_lines[f"mean_p_{figure}"].max() for figure in figures])
    fig.suptitle(
        "Nodal curtailment comparison between power system with static and dynamic line rating",
        fontsize=20,
    )
    fig.subplots_adjust(
        top=0.9, bottom=0.05, left=0.05, right=0.95, hspace=0.01, wspace=0.01
    )
    for i, figure in enumerate(figures):
        ax[i].set_extent([4, 16, 47, 56], ccrs.PlateCarree())
        ax[i].coastlines(resolution="10m")
        ax[i].add_feature(cartopy.feature.OCEAN, color="steelblue")
        ax[i].add_feature(cartopy.feature.LAND, edgecolor="black", color="burlywood")
        ax[i].add_feature(cartopy.feature.BORDERS)
        ax[i].scatter(x=plot_data_buses["x"], y=plot_data_buses["y"], color="black")
        ax[i].set_title(figures_name[figure], fontsize=15)
        subax = []
        for j, bus in enumerate(plot_data_buses.index):
            # Plots the wind expansion data at each bus
            subax.append(
                add_subplot_axes(
                    fig,
                    ax[i],
                    [
                        plot_data_buses.loc[bus]["x"],
                        plot_data_buses.loc[bus]["y"],
                        0.025,
                        0.05,
                    ],
                )
            )
            subax[j].bar(
                x=[0.5],
                width=0.5,
                alpha=0.95,
                height=gen_curtail[figure].groupby("bus").sum().loc[bus]
                / max_bus_curtail,
            )
            # subax[j].bar(x=[0],width=0.5,color="white", alpha=0.95, height=gen_curtail[figure][gen_curtail[figure].index.get_level_values("carrier").str.contains("wind")].groupby("bus").sum().loc[bus]/max_wind_curtail)
            subax[j].set_ylim([0, 1])
        for line in plot_data_lines.index:
            # plots the lines. The width of each line is related to its capacity in relation to the max capacity
            ax[i].plot(
                [plot_data_lines.loc[line]["x0"], plot_data_lines.loc[line]["x1"]],
                [plot_data_lines.loc[line]["y0"], plot_data_lines.loc[line]["y1"]],
                color="black",
                linewidth=0.5
                + plot_data_lines.loc[line][f"mean_p_{figure}"] / divider * 3,
            )
            x, y, dx, dy = get_arrow_parameters(plot_data_lines, line, figure)
            ax[i].arrow(x, y, dx, dy, color="black", width=0.0, head_width=0.15)
            # ax[i].annotate(line, (x,y))

    fig.savefig(snakemake.output[0], bbox_inches="tight")
