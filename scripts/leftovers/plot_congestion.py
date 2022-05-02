"""
Only preliminary code for plotting the line data.

Not working yet with the snakemake workflow.
Path to results with line rating and without line rating has to specified.
TODO: Find a way how to automate the workflow. So far only idea using wildcards instead of config.
"""

import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.mpl.geoaxes
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pypsa
from matplotlib import cm

plt.style.use("bmh")


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
            "plot_congestion",
            year="2020",
            clusters="5",
            opts="Co2L-4H",
            ext="png",
        )

    n = {
        "lr": pypsa.Network(snakemake.input.network_slr),
        "nolr": pypsa.Network(snakemake.input.network_dlr),
    }

    ### heper functions

    def sign(x):
        return np.sign(x)

    def normalize(x):
        return (x - x.min()) / (x.max() - x.min())

    ### Line and Bus Location Data

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

    ### utilization
    line_util = dict()
    for key in n.keys():
        if key == "nolr":
            line_util.update(
                {
                    key: np.abs(n[key].lines_t.p0).divide(
                        n[key].lines.s_nom_opt * n[key].lines.s_max_pu, axis=1
                    )
                }
            )
        elif key == "lr":
            line_util.update(
                {
                    key: np.abs((n[key].lines_t.p0 / n[key].lines_t.s_max_pu)).divide(
                        n[key].lines.s_nom_opt, axis=1
                    )
                }
            )
        line_util.update({key + "_mean": line_util[key].mean(axis=0)})
        # line_util.update({key+"_mean_nom":normalize(line_util[key].mean(axis=0))})

    # other approach to make both flows comparable
    line_util_min = np.min([line_util[key].mean(axis=0).min() for key in n.keys()])
    line_util_max = np.max([line_util[key].mean(axis=0).max() for key in n.keys()])
    for key in n.keys():
        line_util.update(
            {
                key
                + "_mean_nom": line_util[key]
                .mean(axis=0)
                .apply(lambda x: (x - line_util_min) / (line_util_max - line_util_min))
            }
        )

    ### Plots
    figures_name = {"nolr": "Static line rating", "lr": "Dynamic line rating"}
    figures = ["nolr", "lr"]
    # used to scale all wind extension at buses with the max_wind_expansion

    fig, ax = plt.subplots(
        1, 2, figsize=(25, 10), subplot_kw={"projection": ccrs.PlateCarree()}
    )
    fig.suptitle(
        "Congestion comparison between power system with static and dynamic line rating",
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
        # for j, bus in enumerate(plot_data_buses.index):
        #     #Plots the wind expansion data at each bus
        #     subax.append(add_subplot_axes(fig, ax[i], [plot_data_buses.loc[bus]["x"], plot_data_buses.loc[bus]["y"], 0.025, 0.05]))
        #     subax[j].bar(x=[0.5],width=0.5, alpha=0.95, height=gen_curtail[figure].groupby("bus").sum().loc[bus]/max_bus_curtail)
        #     subax[j].set_ylim([0, 1])
        for line in plot_data_lines.index:
            # plots the lines. The width of each line is related to its capacity in relation to the max capacity
            ax[i].plot(
                [plot_data_lines.loc[line]["x0"], plot_data_lines.loc[line]["x1"]],
                [plot_data_lines.loc[line]["y0"], plot_data_lines.loc[line]["y1"]],
                color=cm.YlOrBr(line_util[f"{figure}_mean_nom"][line]),
                linewidth=0.5 + line_util[f"{figure}_mean_nom"][line] * 2,
            )
            x, y, dx, dy = get_arrow_parameters(plot_data_lines, line, figure)
            ax[i].arrow(x, y, dx, dy, color="black", width=0.0, head_width=0.15)
            # ax[i].annotate(line, (x,y))

    fig.savefig(snakemake.output.figure, bbox_inches="tight")
