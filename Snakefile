from os.path import normpath
import seaborn as sns
import matplotlib.pyplot as plt


wildcard_constraints:
    rating="[0-9\.]+|",


configfile: "configs/config.yaml"
configfile: "configs/config.cluster.yaml"


rule create_figures:
    input:
        expand(
            "figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/{figure}.pdf",
            **config["scenario_2020"]
        ),
        expand(
            "figures/de{year}_{clusters}_nodes_{opts}/{figure}.pdf",
            **config["scenario_2030"]
        ),
        "figures/parameter-space-reduced.pdf",


rule create_figures_test:
    input:
        expand(
            "figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/{figure}.pdf",
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
        network="networks/de{year}_{clusters}_nodes_{opts}_dlr{rating}.nc",
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
        "networks/de{year}_{clusters}_nodes_{opts}_dlr{rating}.nc",
    output:
        "results/de{year}_{clusters}_nodes_{opts}_dlr{rating}.nc",
    log:
        solver="logs/solve_network/de{year}_{clusters}_nodes_{opts}_dlr{rating}_solver.log",
        python="logs/solve_network/de{year}_{clusters}_nodes_{opts}_dlr{rating}_python.log",
        memory="logs/solve_network/de{year}_{clusters}_nodes_{opts}_dlr{rating}_memory.log",
    benchmark:
        "benchmarks/solve_network/de{year}_{clusters}_nodes_{opts}_dlr{rating}"
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
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr{rating}.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr1.0.nc",
        shapes="resources/regions_onshore_de{year}_{clusters}_nodes.geojson",
    output:
        capacity="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/capacity_map.{ext}",
        operation="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/operation_map.{ext}",
        utilization="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/utilization_map.{ext}",
        congestion="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/congestion_map.{ext}",
    script:
        "scripts/plot_maps.py"


rule plot_bars:
    input:
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr{rating}.nc",
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr1.0.nc",
        curtailment_data="data/curtailment_carrier.csv",
    output:
        operation="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/operation_bar.{ext}",
        capacity="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/capacity_bar.{ext}",
        curtailment="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/curtailment_bar.{ext}",
        relative_curtailment="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/relative_curtailment_bar.{ext}",
        historical_curtailment="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/historical_curtailment_bar.{ext}",
        cost="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/cost_bar.{ext}",
    script:
        "scripts/plot_bars.py"


rule plot_grid_stats:
    input:
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr1.0.nc",
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr{rating}.nc",
    output:
        potential_correlation="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/potential_correlation.{ext}",
        congestion_correlation="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/congestion_correlation.{ext}",
        line_capacity_overlay="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/line_capacity_overlay.{ext}",
        congestion_duration_curve="figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/congestion_duration_curve.{ext}",
    script:
        "scripts/plot_grid_stats.py"


rule run_power_flow:
    input:
        network_slr="results/de{year}_{clusters}_nodes_{opts}_dlr1.0.nc",
        network_dlr="results/de{year}_{clusters}_nodes_{opts}_dlr{rating}.nc",
    output:
        "figures/de{year}_{clusters}_nodes_{opts}_dlr{rating}/converged_power_flow_calculation.{ext}",
    script:
        "scripts/run_power_flow.py"


# ==================================================================================
# Additional plots and analysis without pypsa-eur
# ==================================================================================


rule plot_parameter_space:
    output:
        figure="figures/parameter-space-{kind}.pdf",
    script:
        "scripts/parameter-space.py"


# ---------------------------------------------------------------------------- #
#                     Additional function to run on cluster                    #
# ---------------------------------------------------------------------------- #


rule sync:
    params:
        cluster=config["cluster"],
    shell:
        """
        rsync -uvarh --no-g --exclude-from=.syncignore-send . {params.cluster}
        rsync -uvarh --no-g --exclude-from=.syncignore-receive {params.cluster} .
        """
