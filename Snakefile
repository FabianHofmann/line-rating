from os.path import normpath
import seaborn as sns
import matplotlib.pyplot as plt

# sns.set_style('white', )


configfile: "configs/config.yaml"


rule create_figures:
    input:
        expand(
            "figures/de{year}_{clusters}_nodes_{opts}/{figure}.pdf",
            **config["scenario_2020"]
        ),
        expand(
            "figures/de{year}_{clusters}_nodes_{opts}/{figure}.pdf",
            **config["scenario_2030"]
        ),


rule create_figures_test:
    input:
        expand(
            "figures/de{year}_{clusters}_nodes_{opts}/{figure}.pdf",
            **config["test"],
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


def memory(w):
    factor = 3.0
    for o in w.opts.split("-"):
        m = re.match(r"^(\d+)h$", o, re.IGNORECASE)
        if m is not None:
            factor /= int(m.group(1))
            break
    for o in w.opts.split("-"):
        m = re.match(r"^(\d+)seg$", o, re.IGNORECASE)
        if m is not None:
            factor *= int(m.group(1)) / 8760
            break
    if w.clusters.endswith("m"):
        return int(factor * (18000 + 180 * int(w.clusters[:-1])))
    elif w.clusters == "all":
        return int(factor * (18000 + 180 * 4000))
    else:
        return int(factor * (10000 + 195 * int(w.clusters)))


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
    resources:
        mem_mb=memory,
        walltime="20:00:00",
    shadow:
        "shallow"
    script:
        pypsaeur2020("scripts/solve_network.py")


rule plot_maps:
    input:
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        shapes="resources/regions_onshore_de{year}_{clusters}_nodes.geojson",
    output:
        capacity="figures/de{year}_{clusters}_nodes_{opts}/capacity_map.{ext}",
        operation="figures/de{year}_{clusters}_nodes_{opts}/operation_map.{ext}",
        curtailment="figures/de{year}_{clusters}_nodes_{opts}/curtailment_map.{ext}",
        utilization="figures/de{year}_{clusters}_nodes_{opts}/utilization_map.{ext}",
        congestion="figures/de{year}_{clusters}_nodes_{opts}/congestion_map.{ext}",
    script:
        "scripts/plot_maps.py"


rule plot_bars:
    input:
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        curtailment_data="data/curtailment_carrier.csv",
    output:
        operation="figures/de{year}_{clusters}_nodes_{opts}/operation_bar.{ext}",
        capacity="figures/de{year}_{clusters}_nodes_{opts}/capacity_bar.{ext}",
        curtailment="figures/de{year}_{clusters}_nodes_{opts}/curtailment_bar.{ext}",
        relative_curtailment="figures/de{year}_{clusters}_nodes_{opts}/relative_curtailment_bar.{ext}",
        historical_curtailment="figures/de{year}_{clusters}_nodes_{opts}/historical_curtailment_bar.{ext}",
        cost="figures/de{year}_{clusters}_nodes_{opts}/cost_bar.{ext}",
    script:
        "scripts/plot_bars.py"


rule plot_grid_stats:
    input:
        network_slr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
    output:
        potential_correlation="figures/de{year}_{clusters}_nodes_{opts}/potential_correlation.{ext}",
        congestion_correlation="figures/de{year}_{clusters}_nodes_{opts}/congestion_correlation.{ext}",
        line_capacity_overlay="figures/de{year}_{clusters}_nodes_{opts}/line_capacity_overlay.{ext}",
        congestion_duration_curve="figures/de{year}_{clusters}_nodes_{opts}/congestion_duration_curve.{ext}",
    script:
        "scripts/plot_grid_stats.py"


# rule plot_analysis:
#     input:
#         network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr.nc",
#         network_slr="results/de{year}_{clusters}_nodes_{opts}_slr.nc",
#     output:
#         congestion_correlation="figures/de{year}_{clusters}_nodes_{opts}/congestion_correlation.{ext}",
#         congestion_wind_correlation="figures/de{year}_{clusters}_nodes_{opts}/congestion_wind_correlation.{ext}",
#     script:
#         "scripts/plot_analysis.py"


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
        figure="figures/parameter-space-{kind}.pdf",
    script:
        "scripts/parameter-space.py"
