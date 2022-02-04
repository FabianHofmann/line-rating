'''
This script changes the network file such that the parameters of the dynamic line rating are deleted. 
Afterwards the solve_network script can be rerun to obtain a solution with the same grid without line raitng.
'''

import pandas as pd
import pypsa

if __name__ == "__main__":

    #prepared
    n = pypsa.Network(snakemake.input.prepared)
    n.lines_t.s_max_pu.drop(n.lines_t.s_max_pu.columns, axis=1, inplace=True)
    n.export_to_netcdf(snakemake.output.prepared)
    
    #unprepared_lr
    n = pypsa.Network(snakemake.input.unprepared)
    #n.lines_t.s_max_pu.drop(n.lines_t.s_max_pu.columns, axis=1, inplace=True)
    n.export_to_netcdf(snakemake.output.unprepared_lr)

    #unprepared_lr
    n = pypsa.Network(snakemake.input.unprepared)
    n.lines_t.s_max_pu.drop(n.lines_t.s_max_pu.columns, axis=1, inplace=True)
    n.export_to_netcdf(snakemake.output.unprepared_nolr)
