# configfile: "config.yaml"

import matplotlib.pyplot as plt
# plt.rc('figure', dpi=300)


figures = ["parameter-space"]

rule all:
    input:
        expand('figures/{figure}.pdf', figure=figures),


rule plot_parameter_space:
    output: "figures/parameter-space.pdf"
    script: "scripts/parameter-space.py"


subworkflow pypsaeur:
    workdir: "pypsa-eur"
    snakefile: "pypsa-eur/Snakefile"
    configfile: "config.de.yaml"

