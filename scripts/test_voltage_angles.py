import os
import numpy as np
import pypsa
import pandas as pd

def normed(s): return s/s.sum()

def test_voltage_angles():

    #import optimized network
    network = pypsa.Network(snakemake.input[0])
    #number of snapshots
    n=100
    network.set_snapshots(network.snapshots[:n])

    # calculate voltage angles
    v_ang=network.buses_t.v_ang
    v_ang_diff=v_ang[network.lines.bus0].values-v_ang[network.lines.bus1].values
    v_ang_diff = pd.DataFrame(v_ang_diff, index=v_ang.index, columns= network.lines.index)

    #For the PF, set the P to the optimised P
    network.generators_t.p_set = network.generators_t.p
    network.stores_t.p_set = network.stores_t.p

    #set all buses to PV, since we don't know what Q set points are
    network.generators.control = "PV"

    #neglect storage buses
    #storage_filter=network.buses.index[network.buses.carrier != "AC"]
    #network.buses.drop(storage_filter, axis=0, inplace=True)

    #Need some PQ buses so that Jacobian doesn't break
    f = network.generators[network.generators.bus==network.generators.bus.iloc[0]]
    network.generators.loc[f.index,"control"] = "PQ"

    # by dispatch
    network.pf(distribute_slack=True, slack_weights='p_set')

    # by capacity
    #network.pf(distribute_slack=True, slack_weights='p_nom')

    np.testing.assert_array_almost_equal(
        network.generators_t.p_set.apply(normed, axis=1),
        (network.generators_t.p - network.generators_t.p_set).apply(normed, axis=1)
    )



if __name__ == "__main__":

    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "test_voltage_angles",
            network="elec",
            simpl="",
            clusters="40",
            ll="v1.0",
            opts="Co2L-4H",
        )

    test_voltage_angles()