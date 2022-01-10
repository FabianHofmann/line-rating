'''
Only preliminary code for plotting the line data. Not working yet with the snakemake workflow.
Path to results with line rating and without line rating has to specified.
TODO: Find a way how to automate the workflow. So far only idea using wildcards instead of config.
'''

import pypsa
import matplotlib.pyplot as plt
plt.style.use("bmh")
import pandas as pd
import numpy as np
import cartopy
import cartopy.crs as ccrs
import cartopy.mpl.geoaxes
import cartopy.feature as cfeature


def add_subplot_axes(fig, ax,rect):#,axisbg='w'):
    box = ax.get_position(original=False)
    width = box.width
    height = box.height
    axis_to_data = ax.transAxes + ax.transData.inverted()
    data_to_axis = axis_to_data.inverted()
    inax_position  = data_to_axis.transform(rect[0:2])
    fig_to_ax = fig.transFigure + ax.transAxes.inverted()
    ax_to_fig = fig_to_ax.inverted()
    infig_position = ax_to_fig.transform(inax_position)    
    x = infig_position[0]
    y = infig_position[1]
    width *= rect[2]
    height *= rect[3] 
    subax = fig.add_axes([x,y,width,height]) #,axisbg=axisbg)
    x_labelsize = subax.get_xticklabels()[0].get_size()
    y_labelsize = subax.get_yticklabels()[0].get_size()
    x_labelsize *= rect[2]**0.5
    y_labelsize *= rect[3]**0.5
    subax.xaxis.set_tick_params(labelsize=x_labelsize)
    subax.yaxis.set_tick_params(labelsize=y_labelsize)
    subax.axis('off')
    return subax

def get_arrow_parameters(plot_data_lines, line, figure):
    x0=plot_data_lines.loc[line]["x0"]
    x1=plot_data_lines.loc[line]["x1"]
    y0=plot_data_lines.loc[line]["y0"]
    y1=plot_data_lines.loc[line]["y1"]

    x=(x0+x1)/2
    y=(y0+y1)/2
    dx=(x1-x0)/100
    if plot_data_lines.loc[line][f"flow_direction_{figure}"]>0:
        dy=(y1-y0)/(x1-x0)*dx
    elif plot_data_lines.loc[line][f"flow_direction_{figure}"]<0:
        dy=-(y1-y0)/(x1-x0)*dx
        dx=-dx
    else:
        dx=0
        dy=0
    return x,y,dx,dy




if "snakemake" not in globals():
    from _helpers import mock_snakemake

    snakemake = mock_snakemake("plot_flow_expansion")

    n={"w_lr":pypsa.Network("elec_s_40_ec_lv1.0_Co2L-4H_ll_lr.nc"), "w/o_lr":pypsa.Network("elec_s_40_ec_lv1.0_Co2L-4H_ll_no_lr.nc")}

    ####

    def sign(x):
        return np.sign(x)

    plot_data_buses=n["w/o_lr"].buses[n["w/o_lr"].buses.carrier=='AC'].loc[:,['x', 'y']]

    plot_data_lines=pd.DataFrame(index=n["w/o_lr"].lines.index, columns=['x0','x1','y0','y1'])
    for line in n["w/o_lr"].lines.index:
        bus0=n["w/o_lr"].lines.loc[line]['bus0']
        bus1=n["w/o_lr"].lines.loc[line]['bus1']
        plot_data_lines.loc[line]['x0']=n["w/o_lr"].buses.loc[bus0]['x']
        plot_data_lines.loc[line]['x1']=n["w/o_lr"].buses.loc[bus1]['x']
        plot_data_lines.loc[line]['y0']=n["w/o_lr"].buses.loc[bus0]['y']
        plot_data_lines.loc[line]['y1']=n["w/o_lr"].buses.loc[bus1]['y']

    ####
    plot_data_lines["mean_p_w/o_lr"]=np.abs(n["w/o_lr"].lines_t["p0"].mean(axis=0))
    plot_data_lines["mean_p_w_lr"]=np.abs(n["w_lr"].lines_t["p0"].mean(axis=0))
    plot_data_lines["flow_direction_w/o_lr"]=n["w/o_lr"].lines_t["p0"].mean(axis=0).transform(sign)
    plot_data_lines["flow_direction_w_lr"]=n["w_lr"].lines_t["p0"].mean(axis=0).transform(sign)


    ####
    results=["w/o_lr","w_lr"]
    gen_expansion={}
    for result in results:
        gen_expansion.update({result:n[result].generators.groupby(["bus", "carrier"]).sum()["p_nom_opt"]-n[result].generators.groupby(["bus", "carrier"]).sum()["p_nom"]})
  
    ###

    figures=["w/o_lr", "w_lr"]
    #used to scale all wind extension at buses with the max_wind_expansion
    max_wind_expansion=np.max([gen_expansion[result][np.core.defchararray.find(gen_expansion[result].index.get_level_values(1).values.astype(str),"wind")!=-1].groupby("bus").sum().max() for result in results])

    fig=plt.figure(figsize=(20,15))
    ax=[]
    divider=np.max([plot_data_lines[f"mean_p_{figure}"].max() for figure in figures])
    for i, figure in enumerate(figures):
        ax.append(plt.subplot(1,len(figures), i+1, projection=ccrs.PlateCarree()))
        ax[i].set_extent([4, 16, 47, 56], ccrs.PlateCarree())
        ax[i].coastlines(resolution='10m')
        ax[i].add_feature(cartopy.feature.OCEAN, color='steelblue')
        ax[i].add_feature(cartopy.feature.LAND, edgecolor='black', color="burlywood")
        ax[i].add_feature(cartopy.feature.BORDERS)
        ax[i].scatter(x=plot_data_buses['x'], y=plot_data_buses['y'], color='black')
        ax[i].set_title(figure)
        subax=[]
        for j, bus in enumerate(plot_data_buses.index):
            #Plots the wind expansion data at each bus
            subax.append(add_subplot_axes(fig, ax[i], [plot_data_buses.loc[bus]["x"], plot_data_buses.loc[bus]["y"], 0.025, 0.05]))
            subax[j].bar(x=[0],width=0.3, alpha=0.95, height=gen_expansion[figure][np.core.defchararray.find(gen_expansion[figure].index.get_level_values(1).values.astype(str),"wind")!=-1].loc[bus].sum())
            subax[j].set_ylim([0, max_wind_expansion])
        for line in plot_data_lines.index:
            #plots the lines. The width of each line is related to its capacity in relation to the max capacity
            ax[i].plot([plot_data_lines.loc[line]["x0"],plot_data_lines.loc[line]["x1"]], [plot_data_lines.loc[line]["y0"],plot_data_lines.loc[line]["y1"]], color="black" , linewidth=0.5+plot_data_lines.loc[line][f"mean_p_{figure}"]/divider*3)
            x,y,dx,dy=get_arrow_parameters(plot_data_lines, line, figure)
            ax[i].arrow(x,y,dx,dy, color="black", width=0.0, head_width=0.15)
            #ax[i].annotate(line, (x,y))
