import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pypsa
import seaborn as sns
from matplotlib.legend_handler import HandlerPatch
from pypsa.plot import projected_area_factor

keys = {"network_dlr": "Dynamic Line Rating", "network_slr": "Static Line Rating"}

super_carrier = {
    "coal": "Fossil Carriers",
    "CCGT": "Fossil Carriers",
    "lignite": "Fossil Carriers",
    "geothermal": "Other Renewables",
    "biomass": "Other Renewables",
    "onwind": "Onshore Wind",
    "offwind": "Offshore Wind",
    "offwind": "Offshore Wind",
    "solar": "Solar",
    "nuclear": "Nuclear",
    "PHS": "Other Renewables",
    "hydro": "Other Renewables",
    "ror": "Other Renewables",
    "OCGT": "Fossil Carriers",
    "battery": "Battery Infrastructure",
    "battery discharger": "Battery Infrastructure",
    "battery charger": "Battery Infrastructure",
    "H2": "Hydrogen Infrastructure",
    "H2 fuel cell": "Hydrogen Infrastructure",
    "H2 electrolysis": "Hydrogen Infrastructure",
    "Load": "",
    "AC": "Transmission System",
    "DC": "Transmission System",
}

plt.style.use("seaborn-colorblind")
sns.set_context(
    "paper",
    rc={
        "font.size": 12,
        "font.family": "Times New Roman",
        "figure.titlesize": "normal",
        "legend.fontsize": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 12,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
    },
)


def add_load_shedding_color(n):
    """
    Needed until https://github.com/PyPSA/pypsa-eur/pull/320 is merged.
    """
    if "Load" in n.carriers.index:
        n.carriers.loc["load", "color"] = "purple"
        n.carriers.loc["load", "co2_emissions"] = 0
        n.carriers.loc["load", "nice_name"] = "Load shedding"
        n.remove("Carrier", "Load")
    return n


def modify_offwind_carrier(n):
    n.add("Carrier", "offwind", nice_name="Offshore Wind", color="#6895dd")
    n.mremove("Carrier", ["offwind-ac", "offwind-dc"])
    n.generators.loc[
        n.generators.carrier.str.startswith("offwind"), "carrier"
    ] = "offwind"
    return n


def add_carrier_nice_names(n):
    n.add("Carrier", "AC", nice_name="AC Transmission")
    n.add("Carrier", "DC", nice_name="DC Transmission")
    n.add("Carrier", "battery discharger", nice_name="Battery Discharging")
    n.add("Carrier", "battery charger", nice_name="Battery Charging")
    n.add("Carrier", "H2 fuel cell", nice_name="Hydrogen Fuel Cell")
    n.add("Carrier", "H2 electrolysis", nice_name="Hydrogen Electrolysis")
    return n


def add_carrier_groups(n):
    n.carriers["group"] = n.carriers.index.map(super_carrier)


def load_network(path):
    n = pypsa.Network(path)
    if "dlr1.0" in path:
        n.name = "Static Line Rating"
    elif "dlr" in path:
        n.name = "Dynamic Line Rating"
    else:
        raise ValueError("Cannot evaluate network name.")
    add_load_shedding_color(n)
    modify_offwind_carrier(n)
    add_carrier_nice_names(n)
    add_carrier_groups(n)
    n.carriers = n.carriers.sort_values(["co2_emissions", "group"])
    return n


def plot_shapes(ax, shapes, **kwargs):
    kwargs.setdefault("facecolor", "whitesmoke")
    kwargs.setdefault("edgecolor", "grey")
    shapes.plot(
        ax=ax, linewidth=0.1, transform=ccrs.PlateCarree(), aspect="equal", **kwargs
    )


class HandlerCircle(HandlerPatch):
    """
    Legend Handler used to create circles for legend entries.

    This handler resizes the circles in order to match the same
    dimensional scaling as in the applied axis.
    """

    def create_artists(
        self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans
    ):
        radius = orig_handle.get_radius()
        center = 5 - xdescent, 5 - ydescent
        p = plt.Circle(center, radius)
        self.update_prop(p, orig_handle, legend)
        p.set_transform(trans)
        return [p]


def add_carrier_legend(ax, carriers, size=1, scale=1, **kwargs):
    """
    Add a legend to the network plot.

    This legend will draw circles with the same dimensional scaling
    as in the network plot.

    Parameters
    ----------
    ax : AxesSubplot/GeoAxesSubplot
        Axis in which to draw the legend.
    carriers : pandas.DataFrame
        Dataframe determining the legend entries.
        The column `color` is required.
        If the column `nice_name` exists, its entries will  be
        used as labels. If not, the index will be used as labels.
        If the column `size` is existent, its entries will
        determine the circle sizes. If not the `size` argument
        will be used.
    size: float
        Size of the legend circles. Will be supersed by the `size`
        column of `carriers` if existent.
    scale : float
        Factor used to scale the original bus sizes in the network plot.
    **kwargs :
        Keyword aguments passed to `ax.legend`.

    Returns
    -------
    legend:
        Initialized Legend.

    Example
    -------

    >>> import pandas as pd
    >>> import pypsa
    >>> from cartopy import crs as ccrs
    >>> import matplotlib.pyplot as plt

    >>> n = pypsa.examples.ac_dc_meshed()
    >>> n.carriers.color = ["red", "blue", "yellow"]
    >>> fig, ax = plt.subplots(
    ...     figsize=(10, 10), subplot_kw={"projection": ccrs.PlateCarree()}
    ... )
    >>> bus_sizes = n.generators.groupby(["bus", "carrier"]).p_nom.sum()
    >>> bus_scale = 1e-6
    >>> n.plot(bus_sizes=bus_sizes * bus_scale, ax=ax)

    >>> pypsa.plot.add_legend(ax, n.carriers, size=10000, scale=bus_scale)
    >>> # add reference circle
    >>> biggest_size = n.generators.groupby("bus").p_nom.sum().max()
    >>> circ = pd.Series(["white", "k"], index=["color", "edgecolor"])
    >>> circ = circ.to_frame(f"Biggest circle = {biggest_size} MW").T
    >>> pypsa.plot.add_legend(ax, circ, size=biggest_size, scale=bus_scale, loc=2)
    """

    size = carriers.get("size", size)
    radius = (size * scale) ** 0.5
    empty_ser = pd.Series(index=carriers.index, dtype=object)
    nice_names = carriers.get("nice_name", empty_ser)
    circles = carriers.rename(columns={"color": "facecolor"})
    circles = circles[
        list(set(plt.Circle.properties(plt.Circle((0, 0)))) & set(circles))
    ]

    # Scale the legend circles according to the circles drawn in the figure.
    # Note: the factor 56 is derived emprically!
    fig = ax.get_figure()
    unit = np.diff(ax.transData.transform([(0, 0), (1, 1)]), axis=0)[0][1]
    area_factor = projected_area_factor(ax)
    figscale = unit * (56 / fig.dpi) * area_factor

    rows = circles.iterrows()
    handles = [plt.Circle((0, 0), radius * figscale, **row[1].dropna()) for row in rows]

    notnull = (nice_names != "") & nice_names.notnull()
    labels = list(nice_names.where(notnull, carriers.index))

    handler_map = {plt.Circle: HandlerCircle()}

    legend = fig.legend(handles, labels, handler_map=handler_map, **kwargs)
    fig.add_artist(legend)
    return legend


def get_line_utilization(networks):
    """
    Helper function to normalize the utilization of each transmission line and
    make them comparable for DLR and SLR.

    Utilization is the power flow in each line divided by the maximal
    possible power flow at each timestep.
    """
    line_util = dict()
    line_util_temp = dict()
    for n in networks:
        if "Static" in n.name:
            line_util_temp.update(
                {
                    n.name: np.abs(n.lines_t.p0).divide(
                        n.lines.s_nom_opt * n.lines.s_max_pu, axis=1
                    )
                }
            )
        elif "Dynamic" in n.name:
            line_util_temp.update(
                {
                    n.name: np.abs((n.lines_t.p0 / n.lines_t.s_max_pu)).divide(
                        n.lines.s_nom_opt, axis=1
                    )
                }
            )

    line_util_min = np.min(
        [line_util_temp[n.name].mean(axis=0).min() for n in networks]
    )
    line_util_max = np.max(
        [line_util_temp[n.name].mean(axis=0).max() for n in networks]
    )

    for n in networks:
        line_util.update(
            {
                n.name
                + "_mean_nom": line_util_temp[n.name]
                .mean(axis=0)
                .apply(lambda x: (x - line_util_min) / (line_util_max - line_util_min))
            }
        )

    return line_util


def get_line_congestion(networks):
    """
    Helper function to get the congestion value for a set of and make them
    comparable for DLR and SLR.

    Utilization is the power flow in each line divided by the maximal
    possible power flow at each timestep.
    """
    comps = ["Line", "Link"]
    congestion = dict()
    for n in networks:
        f = pd.concat(
            {
                c: ((n.pnl(c).mu_lower.abs() + n.pnl(c).mu_lower.abs()) != 0).sum()
                for c in comps
            }
        )
        f = f.where(n.branches().carrier.isin(["AC", "DC"]).reindex_like(f), 0)
        congestion.update({n.name: f})
    return congestion
