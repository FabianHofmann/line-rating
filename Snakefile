# configfile: "config.yaml"

wildcard_constraints:
    simpl="[a-zA-Z0-9]*|all",
    clusters="[0-9]+m?|all",
    ll="(v|c)([0-9\.]+|opt|all)|all",
    opts="[-+a-zA-Z0-9\.]*"

import matplotlib.pyplot as plt
from os.path import normpath, exists
# plt.rc('figure', dpi=300)

configfile: "pypsa-eur/config.yaml"
figures = ["flow_wind_expansion_s{simpl}_{clusters}_ec_l{ll}_{opts}.png"]#["parameter-space"]

rule all:
    input:
        expand('figures/{figure}.pdf', figure=figures),


rule plot_parameter_space:
    output: "figures/parameter-space.pdf"
    script: "scripts/parameter-space.py"

subworkflow pypsaeur:
    workdir: "pypsa-eur"
    snakefile: "pypsa-eur/Snakefile"

rule solve_network_nolr:
    input: "networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr.nc"
    output: "results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr.nc"
    log:
        solver=pypsaeur(normpath("logs/solve_network/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr_solver.log")),
        python=pypsaeur("logs/solve_network/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr_python.log"),
        memory=pypsaeur("logs/solve_network/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr_memory.log")
    benchmark: pypsaeur("benchmarks/solve_network/elec_s{simpl}_{clusters}_ec_l{ll}_nolr_{opts}")
    threads: 4
    shadow: "shallow"
    script: pypsaeur("scripts/solve_network.py")

rule solve_operations_network_lr:
    input:
        unprepared="networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_lr_unprepared.nc",
        optimized="results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr.nc"
    output: "results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_lr_op.nc"
    log:
        solver=pypsaeur(normpath("logs/solve_operations_network/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_op_solver.log")),
        python=pypsaeur("logs/solve_operations_network/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_op_python.log"),
        memory=pypsaeur("logs/solve_operations_network/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_op_memory.log")
    benchmark: pypsaeur("benchmarks/solve_operations_network/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}")
    threads: 4
    resources: mem=(lambda w: 5000 + 372 * int(w.clusters))
    shadow: "shallow"
    script: pypsaeur("scripts/solve_operations_network.py")

rule modify_network:
    input: 
        prepared=pypsaeur("networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}.nc"),
        unprepared=pypsaeur("networks/elec_s{simpl}_{clusters}_ec.nc")
    output: 
        prepared="networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr.nc",
        unprepared="networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_lr_unprepared.nc"
    script: "scripts/modify_network.py"

rule copy_network_results:
    input: pypsaeur("results/networks/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}.nc")
    output: "results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_lr.nc"
    shell: "cp {input} {output}"

rule plot_flow_wind_expansion:
    input: 
        nolr="results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr.nc",
        lr="results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_lr.nc"
    output: "figures/flow_wind_expansion_s{simpl}_{clusters}_ec_l{ll}_{opts}.png"
    script: "scripts/plot_flow_wind_expansion.py"

rule plot_curtailment:
    input: 
        nolr= "results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_nolr.nc",
        lr= "results/elec_s{simpl}_{clusters}_ec_l{ll}_{opts}_lr_op.nc"
    output: "figures/curtailment_s{simpl}_{clusters}_ec_l{ll}_{opts}.png"
    script: "scripts/plot_curtailment.py"


