#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  8 09:33:20 2022.

@author: fabian
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from atlite.convert import convert_line_rating

# Use basic quantities fromt the IEEE test case in atlite/test/test_dynamic_line_rating


def current_capacity(**update):
    ds = {
        "temperature": 313,
        "wnd100m": 0.61,
        "height": 0,
        "wnd_azimuth": 0,
        "influx_direct": 1027,
        "solar_position: altitude": np.pi / 2,
        "solar_position: azimuth": np.pi,
    }

    ds.update(**update)

    psi = 90  # line azimuth
    D = 0.02814  # line diameter
    Ts = 273 + 100  # max allowed line surface temp
    epsilon = 0.8  # emissivity
    alpha = 0.8  # absorptivity

    R = 9.39e-5  # resistance at 100°C in Ohm/m

    return convert_line_rating(ds, psi, R, D, Ts, epsilon, alpha)


windspeeds = [1, 9]

# first translating, then averaging
case1 = sum(current_capacity(wnd100m=w) for w in windspeeds) / len(windspeeds)

# first averaging, then translating
case2 = current_capacity(wnd100m=sum(windspeeds) / len(windspeeds))

windspeedstring = ", ".join(f"{w}m/s" for w in windspeeds)
print(
    f"Using windspeed {windspeedstring}: \n"
    f"First converting then averaging gives {case1}. \n"
    f"First averaging, then converting gives {case2}."
)


# %%  Try to derive a correction factor
# Assume a constant variability around the base wind speed


def correction_factor(windspeeds):
    case1 = sum(current_capacity(wnd100m=w) for w in windspeeds) / len(windspeeds)
    case2 = current_capacity(wnd100m=sum(windspeeds) / len(windspeeds))
    return case1 / case2


def variable_wind(base, variability, length=50):
    speed = np.full(length, base)
    fluctuation = (np.random.rand(length) - 0.5) * base * variability
    return np.clip(speed + fluctuation, 0, np.inf)


B = np.arange(30)
V = np.arange(0, 1, 0.1)
combinations = np.array(np.meshgrid(B, V)).T.reshape(-1, 2)
factors = pd.DataFrame(combinations, columns=["Base", "Variability"])
factors["Correction Factor"] = factors.apply(correction_factor, axis=1)

sns.set_style("white")
fig, ax = plt.subplots(1, 1, figsize=(10, 5))
sns.lineplot(data=factors, y="Correction Factor", x="Variability", hue="Base", ax=ax)
ax.legend(bbox_to_anchor=(1, 1), loc="upper left", title="Base [m/s]")
fig.tight_layout()
fig.savefig("../figures/wind_speed_correctionfactor.pdf")
