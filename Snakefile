from os.path import normpath
import seaborn as sns
import matplotlib.pyplot as plt

# sns.set_style('white', )
plt.rc("text", usetex=True)
plt.rc("font", family="sans-serif")


configfile: "configs/config.yaml"


rule all:
    input:
        expand(
            "figures/de{year}_{clusters}_nodes_{opts}/{map}_map.pdf",
            **config["scenario"],
            map=["operation", "capacity"]
        ),


rule test:
    input:
        expand("results/de{year}_{clusters}_nodes_{opts}_{rating}.nc", **config["test"]),


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


def shapes_from_subworkflow(wildcards):
    if wildcards.year == "2020":
        return pypsaeur2020("resources/regions_{shore}_elec_s_{clusters}.geojson")
    elif wildcards.year == "2030":
        return pypsaeur2030("resources/regions_{shore}_elec_s_{clusters}.geojson")
    else:
        raise ValueError("Wildcard 'year' must be 2020 or 2030.")


rule get_shapes:
    input:
        shapes=shapes_from_subworkflow,
    output:
        "resources/regions_{shore}_de{year}_{clusters}_nodes.geojson",
    shell:
        "cp {input} {output}"


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


rule plot_maps:
    input:
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
        shapes="resources/regions_onshore_de{year}_{clusters}_nodes.geojson",
    output:
        capacity="figures/de{year}_{clusters}_nodes_{opts}/capacity_map.{ext}",
        operation="figures/de{year}_{clusters}_nodes_{opts}/operation_map.{ext}",
        curtailment="figures/de{year}_{clusters}_nodes_{opts}/curtailment_map.{ext}"
    script:
        "scripts/plot_maps.py"


rule plot_grid_stats:
    input:
        network_slr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
    output:
        potential_correlation="figures/de{year}_{clusters}_nodes_{opts}/potential_correlation.{ext}",
    script:
        "scripts/plot_grid_stats.py"


rule plot_flow_wind_expansion:
    input:
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
    output:
        figure="figures/de{year}_{clusters}_nodes_{opts}/flow_wind_expansion.{ext}",
    script:
        "scripts/plot_flow_wind_expansion.py"


rule plot_curtailment:
    input:
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
    output:
        figure="figures/de{year}_{clusters}_nodes_{opts}/curtailment.{ext}",
    script:
        "scripts/plot_curtailment.py"


rule plot_congestion:
    input:
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
    output:
        figure="figures/de{year}_{clusters}_nodes_{opts}/congestion.{ext}",
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
