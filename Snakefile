from os.path import normpath

LINERATING = ["slr", "dlr"]
YEARS = [2020, 2030]
CLUSTERS = ["all"]


configfile: "configs/config.yaml"


rule test:
    input:
        expand(
            "results/de{year}_{clusters}_nodes_{lr}.nc",
            year=YEARS,
            clusters=5,
            lr=LINERATING,
        ),


rule all:
    input:
        expand(
            "results/de{year}_{clusters}_nodes_{lr}.nc",
            year=YEARS,
            clusters=CLUSTERS,
            lr=LINERATING,
        ),


subworkflow pypsaeur2020:
    workdir:
        "pypsa-eur-2020"
    snakefile:
        "pypsa-eur-2020/Snakefile"
    configfile:
        "configs/config.2020.yaml"


subworkflow pypsaeur2030:
    workdir:
        "pypsa-eur-2030"
    snakefile:
        "pypsa-eur-2030/Snakefile"
    configfile:
        "configs/config.2030.yaml"


def from_subworkflow(wildcards):
    if wilcards.year == 2020:
        return pypsaeur2020("networks/elec_s_{wildcards.clusters}_ec_lv1.0_Co2L.nc")
    elif wilcards.year == 2030:
        return pypsaeur2030("networks/elec_s_{wildcards.clusters}_ec_lv1.0_Co2L.nc")


rule prepare_networks:
    input:
        network=from_subworkflow,
    output:
        network_dlr="networks/de{year}_{clusters}_nodes_dlr.nc",
        network_slr="networks/de{year}_{clusters}_nodes_slr.nc",
    script:
        "scripts/prepare_networks.py"


rule solve_network:
    input:
        "networks/de{year}_{clusters}_nodes_{lr}.nc",
    output:
        "results/de{year}_{clusters}_nodes_{lr}.nc",
    log:
        solver="logs/solve_network/de{year}_{clusters}_nodes_{lr}_solver.log",
        python="logs/solve_network/de{year}_{clusters}_nodes_{lr}_python.log",
        memory="logs/solve_network/de{year}_{clusters}_nodes_{lr}_memory.log",
    benchmark:
        "benchmarks/solve_network/de{year}_{clusters}_nodes_{lr}"
    threads: 4
    shadow:
        "shallow"
    script:
        pypsaeur("scripts/solve_network.py")


def both_rating_types(wildcards):
    return expand(
        "results/de{year}_{clusters}_nodes_{lr}.nc",
        year=w.year,
        clusters=w.clusters,
        lr=LINERATING,
    )


rule plot_flow_wind_expansion:
    input:
        both_rating_types,
    output:
        "figures/de{year}_{clusters}_nodes_{lr}/flow_wind_expansion.{ext}",
    script:
        "scripts/plot_flow_wind_expansion.py"


rule plot_curtailment:
    input:
        both_rating_types,
    output:
        "figures/de{year}_{clusters}_nodes_{lr}/curtailment.{ext}",
    script:
        "scripts/plot_curtailment.py"


rule plot_congestion:
    input:
        both_rating_types,
    output:
        "figures/de{year}_{clusters}_nodes_{lr}/congestion.{ext}",
    script:
        "scripts/plot_congestion.py"


rule test_voltage_angles:
    input:
        "results/de{year}_{clusters}_nodes_{lr}.nc",
    script:
        "scripts/test_voltage_angles.py"


# ==================================================================================
# Additional plots and analysis without pypsa-eur
# ==================================================================================


rule plot_parameter_space:
    output:
        "figures/parameter-space.pdf",
    script:
        "scripts/parameter-space.py"
