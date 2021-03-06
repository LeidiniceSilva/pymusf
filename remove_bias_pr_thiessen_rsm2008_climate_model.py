# -*- coding: utf-8 -*-

"""
This script remove daily mean precipitation bias from RSM2008
model. This script focus on operational period and creates files in
the same pr_thiessen pattern.
"""
    
import os
import glob
import argparse
import bisect
import calendar
import numpy as np
import numpy.ma as ma
import scipy.stats as ss

from netCDF4 import Dataset
from collections import Counter
from dateutil.relativedelta import *
from datetime import datetime, date
from hidropy.utils.write_thiessen import write_thiessen
from PyFuncemeClimateTools import ClimateStats as cs
from PyFuncemeClimateTools.Thiessen import thiessen
from hidropy.utils.hidropy_utils import date2index, basin_dict
from hidropy.utils.basins_remove_bias_pr_rsm2008_all_methods_daily import dict_remove_bias
 
from os.path import expanduser

HIDROPY_DIR = os.environ['HIDROPY_DIR']
    
__author__ = 'Leidinice Silva'
__email__  = 'leidinice.silva@funceme.br'
__date__   = '11/08/2017'
__description__='This script remove daily mean precipitation bias from RSM2008' \
                ' model. This script focus on operational' \
                ' period and creates files in the same pr_thiessen pattern.'


def arguments():
    global args

    parser = argparse.ArgumentParser(description=__description__,
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--month_target', default='', 
                        help='Insert initial forecast month.')
    parser.add_argument('--year_target', default='', 
                        help='Insert initial forecast year.')
    parser.add_argument('--local_dir', default='/io',
                        help='Path to data directory.')
    parser.add_argument('--model_name', choices=['rsm2008'],
                        type=str, nargs='?', help='Model options.')
    parser.add_argument('--basin', help='Name of input basin.', default='')
    parser.add_argument('--macro', action='store_true',
                        help='Compute Thiessen for all macro-basins.')
    parser.add_argument('--micro', action='store_true',
                        help='Compute Thiessen for all micro-basins of '
                             'input basin.')
    parser.add_argument('--all_basins', action='store_true',
                        help='True to compute Thiessen for all macro-basins'
                             ' and micro-basins.')

    args = parser.parse_args()

    return args


def define_initial_parameters(modelname):
    """ Define target data and models list.

    :param: modelname: str
    :return: target_date: datatime
    :return: model name list: list
    """

    # List Models
    if modelname == 'rsm2008':
        list_model = ['rsm2008']
    else:
        list_model = [modelname]

    if not month:
        target_date = datetime(date.today().year, date.today().month, 01) 
    else:
        target_date = datetime(int(year), int(month),  01)

    return target_date, list_model     
 
   
def define_dates(target_date):
    """ Define date start run, and dates that the forecast starts and ends.

    :param: target_date: datatime
    :return: start_rundate: str
    :return: start_fcstdate: str
    :return: end_fcstdate: str
    """
    
    str_mon = target_date.strftime("%b").lower()

    target_ifcstdate = target_date + relativedelta(months=1)
    target_mfcstdate = target_date + relativedelta(months=2)
    target_efcstdate = target_date + relativedelta(months=3)
    
    fcst_mon1 = target_ifcstdate.strftime("%m")
    fcst_mon2 = target_mfcstdate.strftime("%m")
    fcst_mon3 = target_efcstdate.strftime("%m")

    start_rundate  = '{0}{1:02d}01'.format(target_date.year, target_date.month)
    start_fcstdate = '{0}{1:02d}01'.format(target_ifcstdate.year, target_ifcstdate.month)
    end_fcstdate   = '{0}{1:02d}{2:02d}'.format(target_efcstdate.year, target_efcstdate.month,
		      calendar.monthrange(target_efcstdate.year, target_efcstdate.month)[1])
    
    return str_mon, fcst_mon1, fcst_mon2, fcst_mon3, start_rundate, start_fcstdate, end_fcstdate


def import_fcst_model_data(model_name, target_date, basin):
    """ Import fcst model data.

    :param: model_name: str (rsm2008)
    :param: target_date: datetime
    :param: basin: str
    :return: precipitation Thiessen time serie
    :return: flag that it refers to data control
    :rtype:list
    """

    str_mon, fcst_mon1, fcst_mon2, fcst_mon3, start_rundate, start_fcstdate, end_fcstdate = define_dates(target_date)

    firt_mon = calendar.monthrange(target_date.year, int(fcst_mon1))[1]
    seco_mon = calendar.monthrange(target_date.year, int(fcst_mon2))[1]
    thir_mon = calendar.monthrange(target_date.year, int(fcst_mon3))[1]
    
    basin_full_name = basin_dict(basin)[2]
    basin_name = basin_dict(basin)[1]
    
    dir_modelname   =  "{0}{1}/{2}/hind8110/{3}/{4}/{5}_thiessen/{6}/". \
		       format(HIDROPY_DIR, localdir, model_name, str_mon, time_freq,
		       var_name, basin_name)
		    
    file_modelname  = "{0}_{1}_{2}_hind8110_fcst_{3}_{4}_{5}_thiessen_{6}.nc". \
		       format(var_name, time_freq, model_name, start_rundate, start_fcstdate,
		       end_fcstdate, basin_full_name)	    
    try:
	input_data = Dataset(os.path.join(dir_modelname, file_modelname))
	var = input_data.variables[var_name][:]
	
	var1 = np.copy(var[0:firt_mon])
	var2 = np.copy(var[firt_mon:firt_mon+seco_mon])
	var3 = np.copy(var[firt_mon+seco_mon:firt_mon+seco_mon+thir_mon])
	input_data.close()
	flag = True
	
    except:
	print 'File: {0} is not available'.format(os.path.join(dir_modelname, file_modelname))
	var1 = []
	var2 = []
	var3 = []
	flag = False
    
    fcst1 = np.array(var1)
    fcst2 = np.array(var2)
    fcst3 = np.array(var3)

    return fcst1, fcst2, fcst3, firt_mon, seco_mon, thir_mon, flag


def import_hind_model_data(model_name, target_date, basin):
    """ Import fcst model data.

        :param: model_name: str ('RSM2008')
        :param: target_date: datetime
        :param: basin: str
        :return: precipitation Thiessen time serie
        :rtype: list
        """
    hind_clim1 = []
    hind_clim2 = []
    hind_clim3 = []

    ihind = 1981
    year_list = np.arange(ihind, 2010 + 1)
    
    for ii, y in enumerate(year_list):
	
	target_rundate = datetime(y, target_date.month, 01)
	str_mon, fcst_mon1, fcst_mon2, fcst_mon3, start_rundate, start_fcstdate, end_fcstdate = define_dates(target_rundate)
	
	firt_mon = calendar.monthrange(y, int(fcst_mon1))[1]
	seco_mon = calendar.monthrange(y, int(fcst_mon2))[1]
	thir_mon = calendar.monthrange(y, int(fcst_mon3))[1]

	basin_full_name = basin_dict(basin)[2]
        basin_name = basin_dict(basin)[1]

	dir_modelname   =  "{0}{1}/{2}/hind8110/{3}/{4}/{5}_thiessen/{6}/". \
		            format(HIDROPY_DIR, localdir, model_name, str_mon, time_freq,
			    var_name, basin_name)
			
	file_modelname  = "{0}_{1}_{2}_hind8110_fcst_{3}_{4}_{5}_thiessen_{6}.nc". \
			   format(var_name, time_freq, model_name, start_rundate, start_fcstdate,
			   end_fcstdate, basin)	
	try:
	    input_data = Dataset(os.path.join(dir_modelname, file_modelname))
	    hind = input_data.variables[var_name][:]
	       
	    hind_clim1.append(np.nansum(hind[0:firt_mon]))
	    hind_clim2.append(np.nansum(hind[firt_mon:firt_mon+seco_mon]))
	    hind_clim3.append(np.nansum(hind[firt_mon+seco_mon:firt_mon+seco_mon+thir_mon]))

	except:
	    print 'Hindcast File: {0} is not available'.format(os.path.join(dir_modelname, file_modelname))
	    hind_clim1 = np.nan
    	    hind_clim2 = np.nan
	    hind_clim3 = np.nan
    
    input_data.close()
    clim_model1 = np.squeeze(hind_clim1)
    clim_model2 = np.squeeze(hind_clim2)
    clim_model3 = np.squeeze(hind_clim3)
   
    return clim_model1, clim_model2, clim_model3


def import_hind_obs_data(model_name, target_date, basin):
    """ Import obs data.

    :param: model_name: str (rsm2008')
    :param: target_date: datetime
    :param: basin: str
    :return: precipitation Thiessen time serie
    """
    
    hind_obs1 = []
    hind_obs2 = []
    hind_obs3 = []

    for y in range(1981, 2010 + 1):
	
	target_rundate = datetime(y, target_date.month, 01)
	str_mon, fcst_mon1, fcst_mon2, fcst_mon3, start_rundate, start_fcstdate, end_fcstdate = define_dates(target_rundate)
	
	firt_mon = calendar.monthrange(y, int(fcst_mon1))[1]
	seco_mon = calendar.monthrange(y, int(fcst_mon2))[1]
	thir_mon = calendar.monthrange(y, int(fcst_mon3))[1]
	
	basin_full_name = basin_dict(basin)[2]
	basin_name = basin_dict(basin)[1]
	
	file_name = '{0}{1}/inmet_ana_chirps_merge/calibration/{2}/' \
		    '{3}_thiessen/{4}/{3}_{2}_{5}_obs_{6}_thiessen_{7}.nc' \
		    .format(HIDROPY_DIR, localdir, time_freq, var_name, basin_name, data_base,
		     hind_obs_period, basin_full_name)	      

	inc = Dataset(file_name)
	time_var = inc.variables['time']
	ifcstdate = datetime.strptime(start_fcstdate, "%Y%m%d")
	ffcstdate = datetime.strptime(end_fcstdate, "%Y%m%d")

	iidx = date2index(datetime(ifcstdate.year, ifcstdate.month, ifcstdate.day), time_var)
	fidx = date2index(datetime(ffcstdate.year, ffcstdate.month, ffcstdate.day), time_var)
	aux = inc.variables[var_name][iidx:fidx+1]

	hind_obs1.append(np.nansum(aux[0:firt_mon]))
	hind_obs2.append(np.nansum(aux[firt_mon:firt_mon+seco_mon]))
	hind_obs3.append(np.nansum(aux[firt_mon+seco_mon:firt_mon+seco_mon+thir_mon]))

    inc.close()
    clim_obs1 = np.squeeze(hind_obs1)
    clim_obs2 = np.squeeze(hind_obs2)
    clim_obs3 = np.squeeze(hind_obs3)

    return clim_obs1, clim_obs2, clim_obs3


def closest(fcst_target, clim_list):
    aux = []    
    for ii in range(0, clim_list.shape[0]):
        aux.append(abs(fcst_target-clim_list[ii]))
    min_value = np.min(aux)    
    idx_min = np.where(aux == min_value)[-1][-1]

    return idx_min


def eqmres_bias_correction(hind, obs, fcst):    
    """ Remove precipitaiton bias via Empirical Quantile Mapping
    (eQM).

    :param: hind: list
    :param: obs: list
    :param: fcst: list
    :return: precipitation
    """

    xs_hind = np.sort(hind)
    #ys_hind = np.arange(1, len(xs_hind)+1)/float(len(xs_hind))
    xs_obs = np.sort(obs)
    #ys_obs = np.arange(1, len(xs_obs)+1)/float(len(xs_obs))
    
    # corr = []
    # for xx in fcst:
        # idx_hind = closest(xx, xs_hind)
        # corr.append(xs_obs[idx_hind])
	
    idx_hind = closest(fcst, xs_hind)
    corr = xs_obs[idx_hind]
    
    return np.array(corr)


if __name__ == "__main__":

    arguments()
    global month, year, localdir, var_name, time_freq, data_base,  \
           hind_obs_period
	   
    # Target basin
    bname = args.basin
    macros = args.macro
    micros = args.micro
    allbasins = args.all_basins

    # Local directory,variable name and Model
    localdir = args.local_dir
    modelname = args.model_name
    
    hind_name = 'hind8110'
    var_name  = 'pr'
    time_freq = 'daily'
    data_base = 'inmet_ana_chirps_merge'
    hind_obs_period = '19610101_20141231'

    # Target period
    month = args.month_target
    year = args.year_target

    # Target basin
    if macros or micros or allbasins:
        basin_list = basin_dict(bname, macro=macros, micro=micros,
                                all_basins=allbasins)
    else:
        basin_list = [bname]
	
    target_date, list_model = define_initial_parameters(modelname)
    
    for modname in list_model:
        
        print " " 
        print "Run Remotion Bias for Model and Date: {0} - {1}/{2:02d}".format(modname.upper(),
                                        target_date.year, target_date.month)
        print " " 
         
        for basin in basin_list:
            
            print 'Processing Basin: {0}'.format(basin)

            basin_full_name = basin_dict(basin)[2]
            basin_name = basin_dict(basin)[1]
            
	    str_mon, fcst_mon1, fcst_mon2, fcst_mon3, start_rundate, start_fcstdate, end_fcstdate = define_dates(target_date)
                
            fcst1, fcst2, fcst3, firt_mon, seco_mon, thir_mon, flag = import_fcst_model_data(modname, target_date, basin)
	   
	    fcst_acc1 = np.array(np.nansum(fcst1))
	    fcst_acc2 = np.array(np.nansum(fcst2))
	    fcst_acc3 = np.array(np.nansum(fcst3))
	    
            if flag:
	    
                model1, model2, model3 = import_hind_model_data(modname, target_date, basin)
                obs1, obs2, obs3 = import_hind_obs_data(modname, target_date, basin)
		
                if  len(model1) != len(obs1):
                    print 'Error hind and obs climatology period1'

                if  len(model2) != len(obs2):
                    print 'Error hind and obs climatology period2'
		    
                if  len(model3) != len(obs3):
                    print 'Error hind and obs climatology period3'
		    
                # Removing Bias - Empirical Quantil Mapping Method
		idx_bestmethod = target_date.month - 1
                best_method = dict_remove_bias[basin][idx_bestmethod]
                                
                if best_method == 'eqm_des':
		    fcst_corr1 = eqmres_bias_correction(model1, obs1, fcst_acc1)
		    fcst_corr2 = eqmres_bias_correction(model2, obs2, fcst_acc2)
		    fcst_corr3 = eqmres_bias_correction(model3, obs3, fcst_acc3)
                else: 
                    fcst_corr = np.copy(fcst_agg)
		    fcst_corr1 = np.copy(fcst_acc1)
		    fcst_corr2 = np.copy(fcst_acc2)
		    fcst_corr3 = np.copy(fcst_acc3)
		
		corr1 = np.full((firt_mon), np.nan)
		corr_des1 = ((fcst1 / fcst_acc1) * fcst_corr1)
		
		corr2 = np.full((seco_mon), np.nan)
		corr_des2 = ((fcst2 / fcst_acc2) * fcst_corr2)

		corr3 = np.full((thir_mon), np.nan)
		corr_des3 = ((fcst3 / fcst_acc3) * fcst_corr3)
		
		fcst_eqmres_array  = np.array([corr_des1, corr_des2, corr_des3])
		fcst_eqmres  =  np.concatenate((fcst_eqmres_array), axis=0)

                path_out = "{0}{1}/{2}/hind8110/{3}/{4}/{5}_thiessen_cor/{6}/". \
			    format(HIDROPY_DIR, localdir, modname, str_mon, time_freq,
			    var_name, basin_name)

                if not os.path.exists(path_out):
		    os.makedirs(path_out)

                write_thiessen(fcst_eqmres, start_fcstdate, end_fcstdate, time_freq,
                        var_name, '{0}_{1}'.format(modname, hind_name), 'fcst', 
                        '{0}_cor_eqmdes'.format(basin), init_date=start_rundate,
			output_path=path_out)
            else:
		continue


