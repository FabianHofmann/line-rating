import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.legend_handler import HandlerPatch
from pypsa.plot import projected_area_factor

keys = {"network_dlr": "Dynamic Line Rating", "network_slr": "Static Line Rating"}


def add_load_shedding_color(n):
    if "Load" in n.carriers.index:
        n.carriers.loc["load", "color"] = "indianred"
        n.carriers.loc["load", "nice_name"] = "Load shedding"
        n.remove("Carrier", "Load")
    return n


def plot_shapes(ax, shapes):
    shapes.plot(
        ax=ax,
        linewidth=0.2,
        transform=ccrs.PlateCarree(),
        aspect="equal",
        facecolor="whitesmoke",
        edgecolor="grey",
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

    legend = ax.legend(handles, labels, handler_map=handler_map, **kwargs)
    ax.add_artist(legend)
    return legend
