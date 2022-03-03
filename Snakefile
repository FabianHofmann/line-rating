from os.path import normpath


configfile: "configs/config.yaml"


rule all:
    input:
        expand(
            "results/de{year}_{clusters}_nodes_{opts}_{rating}.nc",
            **config["scenario"]
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


def network_from_subworkflow(wildcards):
    if wildcards.year == "2020":
        return pypsaeur2020("networks/elec_s_{clusters}_ec_lv1.0_{opts}.nc")
    elif wildcards.year == "2030":
        return pypsaeur2030("networks/elec_s_{clusters}_ec_lv1.0_{opts}.nc")
    else:
        raise ValueError("Wildcard 'year' must be 2020 or 2030.")


rule prepare_networks:
    input:
        network=network_from_subworkflow,
    output:
        network_dlr="networks/de{year}_{clusters}_nodes_{opts}_dlr.nc",
        network_slr="networks/de{year}_{clusters}_nodes_{opts}_slr.nc",
    script:
        "scripts/prepare_networks.py"


rule solve_network:
    input:
        "networks/de{year}_{clusters}_nodes_{opts}_{rating}.nc",
    output:
        "results/de{year}_{clusters}_nodes_{opts}_{rating}.nc",
    log:
        solver="logs/solve_network/de{year}_{clusters}_nodes_{opts}_{rating}_solver.log",
        python="logs/solve_network/de{year}_{clusters}_nodes_{opts}_{rating}_python.log",
        memory="logs/solve_network/de{year}_{clusters}_nodes_{opts}_{rating}_memory.log",
    benchmark:
        "benchmarks/solve_network/de{year}_{clusters}_nodes_{opts}_{rating}"
    threads: 4
    shadow:
        "shallow"
    script:
        pypsaeur2020("scripts/solve_network.py")


def both_rating_types(wildcards):
    return expand(
        "results/de{year}_{clusters}_nodes_{opts}_{rating}.nc",
        year=w.year,
        clusters=w.clusters,
        lr=LINERATING,
    )


rule plot_flow_wind_expansion:
    input:
        both_rating_types,
    output:
        "figures/de{year}_{clusters}_nodes_{opts}_{rating}/flow_wind_expansion.{ext}",
    script:
        "scripts/plot_flow_wind_expansion.py"


rule plot_curtailment:
    input:
        both_rating_types,
    output:
        "figures/de{year}_{clusters}_nodes_{opts}_{rating}/curtailment.{ext}",
    script:
        "scripts/plot_curtailment.py"


rule plot_congestion:
    input:
        both_rating_types,
    output:
        "figures/de{year}_{clusters}_nodes_{opts}_{rating}/congestion.{ext}",
    script:
        "scripts/plot_congestion.py"


rule test_voltage_angles:
    input:
        "results/de{year}_{clusters}_nodes_{opts}_{rating}.nc",
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
