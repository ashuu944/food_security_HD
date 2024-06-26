#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  1 00:02:35 2024

@author: syed
"""


"""
Installation libraries required

pip install numpy
pip install pandas
pip install matplotlib
pip install seaborn
pip install xlrd
pip install openpyxl
"""


"""
Importing necessary libraries
"""
from logger import log
from logger import Logs
import calendar
import pandas as pd
import numpy as np
import os
import re
import configuration as conf
from osgeo import gdal
from sklearn.model_selection import train_test_split



def get_month_number(month):
    month = month.capitalize()  
    if month in list(calendar.month_abbr): 
        return list(calendar.month_abbr).index(month)
    if month in list(calendar.month_name):
        return list(calendar.month_name).index(month)

def get_time_range(time_window):
  time_window_ret =[]
  if time_window['applied_year'] == 'same':
    start_c, end_c = get_month_number(time_window['start']), get_month_number(time_window['end'])
    time_window_ret.append(list(range(start_c, end_c+1)))
    time_window_ret.append(list(range(start_c, end_c+1)))
    return time_window_ret
  if time_window['applied_year'] == 'previous':
    start_c, end_c = get_month_number(time_window['start']), get_month_number('December')
    start_p, end_p = get_month_number('January'), get_month_number(time_window['end'])
    time_window_ret.append(list(range(start_p, end_p+1)))
    time_window_ret.append(list(range(start_c, end_c+1)))
    return time_window_ret

# Function to rename columns
def rename_columns(country, df, year, column_name, is_current):
    renamed_columns = {}
    for col in df.columns:
        if col not in conf.SPATIAL_GRANULARITY[country]:
            match_term = re.search(re.escape(column_name) + r'_*(\d+)', col) 
            
            if match_term:
              month = int(match_term.group(1))
              renamed_columns[col] = f'{column_name}_{month}(t-{1 if is_current else 0})'
    return df.rename(columns=renamed_columns)


# ======================================================================================#
# Variables transformation for Tanzania/Rawanda for year t-0, t-1 from May-November     #
# ======================================================================================#
def rename_timeseries_variables(country, df, years, column_name):
    merged_df = pd.DataFrame()
    for year in years:
        year_t_minus_1, year_t = year-1, year
       
    
    
        # Filter columns using regex
        cols_to_keep = conf.SPATIAL_TEMPORAL_GRANULARITY[country] + [col for col in df.columns if re.match(re.escape(column_name) + r'_*(\d+)$', col)] # We have to change it as to which months for time-series
        df_filtered = df[cols_to_keep]
        
        # Split the data into year_t_minus_1 and year_t
        df_t_minus_1 = df_filtered[df_filtered[conf.TEMPORAL_GRANULARITY[country]] == year_t_minus_1].drop(columns=[conf.TEMPORAL_GRANULARITY[country]])
        df_t = df_filtered[df_filtered[conf.TEMPORAL_GRANULARITY[country]] == year_t].drop(columns=[conf.TEMPORAL_GRANULARITY[country]])
        
        
        # Rename columns
        df_t_minus_1_renamed = rename_columns(country, df_t_minus_1, year_t_minus_1, column_name, False)
        df_t_renamed = rename_columns(country, df_t, year_t, column_name, True)
       
        # Merge the two DataFrames on 'province' and 'district'
        
        merged_pair_df = pd.merge(df_t_renamed, df_t_minus_1_renamed, on=conf.SPATIAL_GRANULARITY[country])
        # Add the year column back
       
        merged_pair_df.insert(loc=0, column=conf.TEMPORAL_GRANULARITY[country], value=year_t)
        # Append the merged result to the main DataFrame
        merged_df = pd.concat([merged_df, merged_pair_df], ignore_index=True)
    return merged_df

# =============================================================================#
# Data (variables) loading method: Load data (variables) from Excel files      #
# =============================================================================#
def read_add_variables(data_rep, country, var_type, criteria):

    for D in var_type:
        log(country, f"Reading Variable {D}...")
        if not os.path.exists(os.path.join(conf.DATA_DIRECTORY , country, conf.VAR_DIRECTORY , "data_" + D + ".xlsx")):
            log(country, "*****File doesn't exists: "+ os.path.join(conf.DATA_DIRECTORY , country, conf.VAR_DIRECTORY , "data_" + D + ".xlsx"), Logs.WARNING)
        else:    
            data_temp = pd.read_excel(
               os.path.join(conf.DATA_DIRECTORY , country, conf.VAR_DIRECTORY , "data_" + D + ".xlsx")
            )# Impoort variables
            #log(country, f"Path of Reading variable {D} with columns: "+ str(list(data_temp.columns)), Logs.INFO)
            if country != conf.countries['burkina_faso'] and var_type == conf.vars_timeseries:
                #print('variables check:', data_rep[conf.TEMPORAL_GRANULARITY[country]].unique(), D)
                data_temp = rename_timeseries_variables(country, data_temp, data_rep[conf.TEMPORAL_GRANULARITY[country]].unique(), D)
            data_rep = pd.merge(data_rep, data_temp, how="left", on=criteria)
    log(country, "criteria of Merging:"+ str(criteria))    
    return data_rep

# =======================================================================================#
# format time series variables and its renaming for Rawanda and Tanzania                 #
# =======================================================================================#
def filter_variables_(country, data_aggr, var_type):
    time_window = get_time_range(conf.time_window[country])
    cols_to_keep = []
    for i in [0,1]:  # année t-1 et t
        log(country, "Time window: "+ str(time_window[i]))
        for j in time_window[i-1]:  # 
            for D in var_type:
               pattern = r"{0}.*{1}\(t-{2}".format(D, j, i)
               # Filter columns using the regex and compute max across these columns
               filtered_df = data_aggr.filter(regex=pattern)
               new_columns = "{0}{1}t-{2}".format(D, j, i)

               # Compute max across the filtered columns
               data_aggr[new_columns] = filtered_df.max(axis=1)
               cols_to_keep.append(new_columns)
    data_aggr = data_aggr[cols_to_keep]
    return data_aggr

# =======================================================================================#
# Standardization/Formating Method: Extract,format time series variables and its renaming#
# =======================================================================================#
def filter_variables(country, data_aggr, var_type):
    if country != conf.countries['burkina_faso']:
        return filter_variables_(country, data_aggr, var_type)
    time_window = get_time_range(conf.time_window[country])
    cols_to_keep = []
    for i in [0,1]:  # année t-1 et t
       log(country, "Time window: "+ str(time_window[i]))
       for j in time_window[i-1]:  # 
           for D in var_type:
               if os.path.exists(os.path.join(conf.DATA_DIRECTORY , country, conf.VAR_DIRECTORY , "data_" + D + ".xlsx")):
                    if D == 'maize':
                        pattern = r"{1}{0}-.*\(.*t-{2}".format(D, j, i)
                    elif D == "tmin" or D == "tmax":
                        t_var = D.replace("t", "t_")
                        pattern = r"{0}.*{1}\(t-{2}".format(t_var, j, i)
                    else:
                        pattern = r"{0}.*{1}\(.*t-{2}".format(D, j, i)
                    
                    filtered_df = data_aggr.filter(regex=pattern)
                    new_columns = "{0}{1}t-{2}".format(D, j, i)
                    data_aggr[new_columns] = filtered_df.max(axis=1)
                    cols_to_keep.append(new_columns)
    
    data_aggr = data_aggr[cols_to_keep]
    return data_aggr

                   
              
    


# ====================================================================================================#
# Normalization Method: Normalization of variables using mean and standard deviation: (X-X.mean)/X.std#
# ====================================================================================================#


def normalize(country, data, var_type):
    log(country, f"{var_type} variables to Normalize:"+ str(list(data.columns)))
    for v in var_type:
        data.loc[:, data.columns.str.startswith(v)] = (
            data.loc[:, data.columns.str.startswith(v)]
            - data.loc[:, data.columns.str.startswith(v)].stack().mean()
        ) / data.loc[:, data.columns.str.startswith(v)].stack().std()
    return data


# ==========================================================================================#
# Return output (Y) Numpy Array                                                             #
# ==========================================================================================#
def output_Y(data_aggregate, output):
    data_Y = []
    for i in range(len(data_aggregate)):
        data_Y.append([data_aggregate[output][i]])
    data_Y = np.array(data_Y)
    return data_Y

# ==========================================================================================#
# Function to extract the year from the date string                                         #
# ==========================================================================================#

def transform_year(date_str):
    # Split the date string by either '/' or '-' and return the first part (year)
    if isinstance(date_str, str):
        return int(date_str.split('/')[0].split('-')[0])
    return int(date_str)


# ==========================================================================================#
# Export the preprocessed variables                                                         #
# ==========================================================================================#
def export(country, data_timeseries, data_conjunctural_structural, data_rep_columns):
    log(country, f"Saving of {country} time-series variables at: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.PREPROCESS_FILES["timeseries"]),Logs.INFO)
    data_timeseries.to_excel(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.PREPROCESS_FILES["timeseries"]))
    log(country, f"Saving of {country} conjunctural/structural variables at: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.PREPROCESS_FILES["conjunctural_structural"]),Logs.INFO)
    data_conjunctural_structural.to_excel(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.PREPROCESS_FILES["conjunctural_structural"]))
    
    # data_all = pd.merge(
    #     data_timeseries, data_conjunctural_structural, how="left", on=data_rep_columns
    # )
    # data_all.to_excel(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.PREPROCESS_FILES["all"]))
    # log(country, f"Saving of {country} all variables at: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.PREPROCESS_FILES["all"]),Logs.INFO)
    
    return


# ==========================================================================================#
# Create directories for features in case if doesn't exists                                 #
# ==========================================================================================#
def create_directories(r_split, country):
    os.makedirs(
        os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_" + conf.OUTPUT_VARIABLES[country][0]), exist_ok=True
    )
    os.makedirs(
        os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY , "features_" + conf.OUTPUT_VARIABLES[country][1]), exist_ok=True
    )


# ==========================================================================================#
# Main Preprocessing Method: Data processing for processing of numerical and spatial data   #
# ==========================================================================================#


def preprocess(rep, r_split, country):

    pd.set_option("display.max_columns", None)
    log(country, f"Preprocessing of {country} data started ...", Logs.INFO)
    log(country, "Path of Ground Truth file: " + os.path.join(
        conf.DATA_DIRECTORY, country, conf.RESPONSE_FILE[country]), Logs.INFO)
    data_response_src = pd.read_excel(os.path.join(
        conf.DATA_DIRECTORY, country, conf.RESPONSE_FILE[country]))  # Read Survey Data
    data_response_src[conf.TEMPORAL_GRANULARITY[country]] = data_response_src[conf.TEMPORAL_GRANULARITY[country]].apply(transform_year) # Transform year
    
    data_rep_columns = list(
        data_response_src.columns
    )  # Get the name of Response columns
    #log(country, "Column Names: " + str(list(data_rep_columns)), Logs.INFO)
    
    data_response_src.loc[:, conf.ID_REGIONS[country]] = pd.factorize(data_response_src[conf.FINE_SP_GRANULARITY[country]])[0] + 1 if conf.ID_REGIONS[country] not in data_rep_columns else data_response_src[conf.ID_REGIONS[country]]
    
    data_rep_columns = list(
        data_response_src.columns
    ) 
    log(country, f'Columns of Ground Truth Data:'+ str(data_rep_columns))
    data_rep = data_response_src  # Keeping the original response data as it is...
    
    
    
    # =============================================================================#
    #     Preprocessing of Time-series variables data                              #
    # =============================================================================#
    
    data_aggregation_timeseries = read_add_variables(
        data_rep, country, conf.vars_timeseries, conf.SPATIAL_TEMPORAL_GRANULARITY[country]
    )  
 
    
    #data_aggregation_timeseries.to_excel(os.path.join(conf.PREPROCESS_DATA_DIR, country, "timeseries.xlsx"))
    data_aggregation_timeseries.dropna(
        subset=conf.OUTPUT_VARIABLES[country], how="all", inplace=True
    )  # Remove rows with response variable Nan
    # read time-series variables
    #data_aggregation_timeseries = data_aggregation_timeseries.drop(columns=data_rep_columns)
    
    data_aggregation_timeseries = filter_variables(country, 
        data_aggregation_timeseries, conf.vars_timeseries
    )  # Standardization of variables and column names
   
   
    
    data_aggregation_timeseries = normalize(country, 
        data_aggregation_timeseries, conf.vars_timeseries
    )  # Normalize variables by mean/STD
    
    
    data_X_timeseries = np.array(
        data_aggregation_timeseries.loc[
            :, ~data_aggregation_timeseries.columns.isin(data_rep_columns)
        ]
    )  # Store the data of time-series variables in NUMPY Array
    log(country, f"Time-series variables Numpy array with shape {data_X_timeseries.shape}:"+ str(data_X_timeseries.shape), Logs.INFO)
    
    # =============================================================================#
    #     Preprocessing of Conjuntural variables data                              #
    #     TODO: Need to restructure the code for world bank                        #
    # =============================================================================#

    data_aggregation = data_response_src
    data_temp = pd.read_excel(
        os.path.join(conf.DATA_DIRECTORY, country, conf.VAR_DIRECTORY , "data_world_bank.xlsx")
    )  # Conjunctural variable handle explicitly
    data_aggregation = pd.merge(
        data_aggregation, data_temp, how="left", on=[conf.TEMPORAL_GRANULARITY[country]]
    ) 
    # read conjunctural variables
    
    data_aggregation = read_add_variables(
        data_aggregation, country, 
        [i for i in conf.vars_conjuctral if i != "world_bank"],
        conf.SPATIAL_TEMPORAL_GRANULARITY[country],
    )
    
    
    # =============================================================================#
    #     Preprocessing of Structural variables data                               #
    # =============================================================================#
    data_aggregation = read_add_variables(
        data_aggregation, country, 
        conf.vars_structural,
        [i for i in conf.SPATIAL_GRANULARITY[country]],
    )
    #data_aggregation = data_aggregation.fillna(0) # For missing waterways in Rawanda
    
    column_to_normalize = list(set(data_aggregation.columns) - set(data_rep_columns))
    for v in column_to_normalize:
        data_aggregation[v] = (data_aggregation[v] - data_aggregation[v].mean())/data_aggregation[v].std()
    
    log(country, f"Columns shape {len(column_to_normalize)}:"+ str(column_to_normalize))
    
    data_X_CS = np.array(
        data_aggregation.loc[
            :, column_to_normalize
        ]
    )  # Store the data of structural variables in NUMPY Array
    # print(data_aggregation_structural)
    # =============================================================================#
    #     Storing Commune information per year for CNN Processing                  #
    # =============================================================================#
    dataInfo = []
    for i in range(len(data_aggregation)):
        dataInfo.append(
            [
                data_aggregation[conf.TEMPORAL_GRANULARITY[country]][i],
                data_aggregation[conf.ID_REGIONS[country]][i],
            ]
        )
    #log(country, "data Info:"+ str(dataInfo))
    
    
    dataInfo = np.array(dataInfo)

    # =============================================================================#
    #     Storing output information (Y) in numpy array = ['sca','sda']            #
    # =============================================================================#
    data_Y_SCA = output_Y(
        data_aggregation, conf.OUTPUT_VARIABLES[country][0]
    )  # Return output variable (SCA) Numpy Array
    data_Y_SDA = output_Y(
        data_aggregation, conf.OUTPUT_VARIABLES[country][1]
    )  # Return output variable (SDA) Numpy Array
    
    # =================================================================================================#
    # Combine Conjunctural and Structural Variables                                                                     #
    # =================================================================================================#
   
    data_X_CS = np.array(
        data_aggregation.loc[:, ~data_aggregation.columns.isin(data_rep_columns)]
    )  # Store the data of Conjunctural+structural variables in NUMPY Array

    # =================================================================================================#
    # EXPORT : Export the variables data                                                               #
    # =================================================================================================#
    create_directories(r_split, country)
    export(country,
        data_aggregation_timeseries,
        data_aggregation,
        data_rep_columns,
    )
   
    # =================================================================================================#
    # Weight storage (W) (for each observation: W = root(number of households)/root(total households)) #
    # =================================================================================================#

    data_aggregation["count"] = (
        np.sqrt(data_aggregation["count"]) / np.sqrt(data_aggregation["count"]).sum()
    )
    
    data_W = []  # Weight Array
    for i in range(len(data_aggregation)):
        data_W.append([data_aggregation["count"][i]])
    data_W = np.array(data_W)

    # =================================================================================================#
    # Train/Test data split                                                                            #
    # =================================================================================================#

    (
        X_train_timeseries,
        X_test_timeseries,
        X_train_CS,
        X_test_CS,
        y_train_SCA,
        y_test_SCA,
        y_train_SDA,
        y_test_SDA,
        w_train,
        w_test,
        info_train,
        info_test,
    ) = train_test_split(
        data_X_timeseries,
        data_X_CS,
        data_Y_SCA,
        data_Y_SDA,
        data_W,
        dataInfo,
        test_size=0.15,
        random_state=r_split,
    )

    log(country, "Years list: "+ str(list(data_response_src[conf.TEMPORAL_GRANULARITY[country]].unique())))
    # =============================================================================#
    #     Preprocessing of Spatial Data                                            #
    # =============================================================================#

    raster_com = gdal.Open(os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["epa"]))
    log(country, "Loaded Rasters: "+os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["epa"]), Logs.INFO)
    log(country, "Years list: "+ str(list(data_response_src[conf.TEMPORAL_GRANULARITY[country]].unique())))
    
    crop = gdal.Open(os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["crop"]))  # import crop Data
    log(country, "Loaded Rasters: "+os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["crop"]), Logs.INFO)
    forest = gdal.Open(os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["forest"]))  # import forest data
    log(country, "Loaded Rasters: "+os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["forest"]), Logs.INFO)
    zones = gdal.Open(os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["zones"]))  # import constructed zones data
    log(country, "Loaded Rasters: "+os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, conf.SPATIAL_TIF_VARS["zones"]), Logs.INFO)
    
    # =============================================================================#
    #     Numpy Arrays of Tif Files: epa, crop, forest and zones                   #
    # =============================================================================#

    raster_com = np.array(raster_com.ReadAsArray())
    crop = np.array(crop.ReadAsArray())
    forest = np.array(forest.ReadAsArray())
    zones = np.array(zones.ReadAsArray())

    dictrep = dict()  # dictionary of answers for each year
    dictpop = dict()  # dictionary of population for each year

    # ================================================================================================================#
    #     Importing Rasters for response and population for each year                                                 #
    #     **TODO: Reduce the redundant data folders e.g. (sca_100m, sda_sda100m)-> should be one folder               #
    # =============================================================================================================== #
    
    years= list(data_response_src[conf.TEMPORAL_GRANULARITY[country]].unique())
    # import des rasters réponse et population de chaque année
    for annee in years:  # import des rasters réponse et population
        dictrep[annee] = gdal.Open(os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, 
            rep+"_"
            + conf.PIXEL
            + "/epa_"
            + rep
            + "_"
            + str(annee)
            + ".tif"
        ))
        log(country, "Loaded Rasters: "+os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, 
            rep+"_"
            + conf.PIXEL
            + "/epa_"
            + rep
            + "_"
            + str(annee)
            + ".tif"), Logs.INFO)
    
        dictpop[annee] = gdal.Open(os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, 
             "population_"
            + conf.PIXEL
            + "/population_"
            + str(annee)
            + ".tif"
        ))
        log(country, "Loaded Rasters: "+os.path.join(conf.DATA_DIRECTORY, country, conf.SPATIAL_DIRECTORY, 
             "population_"
            + conf.PIXEL
            + "/population_"
            + str(annee)
            + ".tif"
        ), Logs.INFO)
        # Conversion into Numpy Array per year
        dictrep[annee] = np.array(dictrep[annee].ReadAsArray())
        dictpop[annee] = np.array(dictpop[annee].ReadAsArray())

        # Replacement of Zero-value pixel to NAN value
        dictrep[annee][dictrep[annee] <= 0] = np.nan
        dictpop[annee][dictpop[annee] <= 0] = np.nan

        # Normalization of pixelated poulation (X-mean/std)
        dictpop[annee] = dictpop[annee] - np.nanmean(dictpop[annee]) / np.nanstd(
            dictpop[annee]
        )

    # ================================================================================================================#
    #     Listing the variables for CNN                                                                               #
    # =============================================================================================================== #

    info_pix_cnn = (
        []
    )  # data on the pairs (municipality, year) associated with each pixel
    dataX_CNN = []  # list of population pixel patches
    dataY_CNN = []  # list of response pixels
    length = 10  # length of patches
    step = 30  # distance between 2 selected pixels

    # ================================================================================================================#
    #     Filling the variables declared for CNN                                                                      #
    # =============================================================================================================== #
    for annee in years:  # pour chaque année
        for i in range(
            int(length / 2), dictrep[annee].shape[0] - int(length / 2), step
        ):  # pixels are scanned horizontally in steps of 30 with a margin = int(length/2)
            for j in range(
                int(length / 2), dictrep[annee].shape[1] - int(length / 2), step
            ):  # pixels are scanned vertically in steps of 30 with a margin = int(length/2)
                """
                conditions for integrating a response pixel + a population patch + 3 oqp_sol patches into the CNN dataset:
                - the response pixel must not be Nan
                - none of the pixels in the associated population patch must be Nan
                - all the pixels in the associated population patch must belong to the same municipality as the response pixel
                """
                if not (
                    (np.isnan(dictrep[annee][i, j]))
                    | (
                        np.isnan(
                            dictpop[annee][
                                i - int(length / 2) : i + int(length / 2),
                                j - int(length / 2) : j + int(length / 2),
                            ]
                        ).any()
                    )
                    | (
                        raster_com[
                            i - int(length / 2) : i + int(length / 2),
                            j - int(length / 2) : j + int(length / 2),
                        ]
                        != raster_com[i, j]
                    ).any()
                ):

                    info_pix_cnn.append([annee, raster_com[i, j], len(info_pix_cnn)])
                    dataX_CNN.append(
                        [
                            dictpop[annee][
                                i - int(length / 2) : i + int(length / 2),
                                j - int(length / 2) : j + int(length / 2),
                            ],
                            crop[
                                i - int(length / 2) : i + int(length / 2),
                                j - int(length / 2) : j + int(length / 2),
                            ],
                            forest[
                                i - int(length / 2) : i + int(length / 2),
                                j - int(length / 2) : j + int(length / 2),
                            ],
                            zones[
                                i - int(length / 2) : i + int(length / 2),
                                j - int(length / 2) : j + int(length / 2),
                            ],
                        ]
                    )
                    dataY_CNN.append([dictrep[annee][i, j]])

    # ================================================================================================================#
    #     Conversion of CNN spatial variables into Numpy array                                                        #
    # =============================================================================================================== #

    dataX_CNN = np.array(dataX_CNN)
    dataY_CNN = np.array(dataY_CNN)
    info_pix_cnn = np.array(info_pix_cnn, dtype=int)

    # ================================================================================================================#
    #  transformation of info data into a dataframe for merging pixel info and info (municipality, year) train / test #
    # =============================================================================================================== #

    RASTER_GRANULARITY = "CODE_COM"
    #RASTER_GRANULARITY = "DISTRICT_ID"

    info_pix_cnn = pd.DataFrame(info_pix_cnn, columns=[conf.TEMPORAL_GRANULARITY[country], RASTER_GRANULARITY, "line"]) # CODE_COM RASTER_GRANULARITY, "line"]
    info_train = pd.DataFrame(info_train, columns=[conf.TEMPORAL_GRANULARITY[country], RASTER_GRANULARITY])
    info_test = pd.DataFrame(info_test, columns=[conf.TEMPORAL_GRANULARITY[country], RASTER_GRANULARITY])
    info_pix_cnn.to_excel(os.path.join(conf.PREPROCESS_DATA_DIR, country,'info_pix_cnn.xlsx'))
    info_train.to_excel(os.path.join(conf.PREPROCESS_DATA_DIR, country,'info_train.xlsx'))
    info_test.to_excel(os.path.join(conf.PREPROCESS_DATA_DIR, country,'info_test.xlsx'))
    
    # ================================================================================================================#
    #  Merge pixel info and info (town, year) train and test                                                          #
    # =============================================================================================================== #

    info_pix_cnn_train = pd.merge(
        info_pix_cnn, info_train, how="inner", on=[conf.TEMPORAL_GRANULARITY[country], RASTER_GRANULARITY]
    )
    info_pix_cnn_test = pd.merge(
        info_pix_cnn, info_test, how="inner", on=[conf.TEMPORAL_GRANULARITY[country], RASTER_GRANULARITY]
    )

    # ================================================================================================================#
    #  Conversion into Numpy array                                                                                    #
    # =============================================================================================================== #

    info_pix_cnn_train = np.array(info_pix_cnn_train)
    info_pix_cnn_test = np.array(info_pix_cnn_test)

    # ================================================================================================================#
    #  Train/Test split                                                                                               #
    # =============================================================================================================== #

    X_pix_train_cnn = dataX_CNN[info_pix_cnn_train[:, 2]]
    X_pix_test_cnn = dataX_CNN[info_pix_cnn_test[:, 2]]
    y_pix_train_cnn = dataY_CNN[info_pix_cnn_train[:, 2]]
    y_pix_test_cnn = dataY_CNN[info_pix_cnn_test[:, 2]]

    # no more need for information on pixel locations, they're removed
    info_pix_cnn_train = np.delete(info_pix_cnn_train, 2, 1)
    info_pix_cnn_test = np.delete(info_pix_cnn_test, 2, 1)

    log(country, "X-Train Shape: "+  str(X_pix_train_cnn.shape), Logs.INFO)
    log(country, "X-Test Shape: "+   str(X_pix_test_cnn.shape), Logs.INFO)

    # save cnn elements
    # np.save(conf.PREPROCESS_DATA_DIR+ conf.FEATURES_DIRECTORY + "features_" + str(r_split) + "/cnn_info_pix_train.npy", info_pix_cnn_train)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_info_pix_train.npy"), info_pix_cnn_train)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_info_pix_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_info_pix_test.npy"), info_pix_cnn_test)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_info_pix_test.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_x_pix_train.npy"), X_pix_train_cnn)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_x_pix_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_x_pix_test.npy"), X_pix_test_cnn)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_x_pix_test.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_y_pix_train.npy"), y_pix_train_cnn)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_y_pix_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_y_pix_test.npy"), y_pix_test_cnn)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cnn_y_pix_test.npy"), Logs.INFO)

    #loaded_train = np.load(conf.FEATURES_DIRECTORY + "cnn_x_pix_train.npy")
    #print("X-Train Load", type(loaded_train), loaded_train.shape)

    # save explicative variables X
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "timeseries_x_train.npy"), X_train_timeseries)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "timeseries_x_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "timeseries_x_test.npy"), X_test_timeseries)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "timeseries_x_test.npy"), Logs.INFO)
    
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cs_x_train.npy"), X_train_CS)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cs_x_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cs_x_test.npy"), X_test_CS)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "cs_x_test.npy"), Logs.INFO)
    
    # save response Y (SCA)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][0],"y_train.npy"), y_train_SCA)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][0],"y_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][0],"y_test.npy"), y_test_SCA)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][0],"y_train.npy"), Logs.INFO)
    
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][1],"y_train.npy"), y_train_SDA)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][1],"y_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][1],"y_test.npy"), y_test_SDA)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "features_"+ conf.OUTPUT_VARIABLES[country][1],"y_test.npy"), Logs.INFO)
   
    # save weights W
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY + "w_train.npy"), w_train)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "w_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY + "w_test.npy"), w_test)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "w_test.npy"), Logs.INFO)
    # save infos (commune, année) des données train et test
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY + "info_train.npy"), info_train)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "info_train.npy"), Logs.INFO)
    np.save(os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY + "info_test.npy"), info_test)
    log(country, "Saving Rasters: "+ os.path.join(conf.PREPROCESS_DATA_DIR, country, conf.FEATURES_DIRECTORY, "info_test.npy"), Logs.INFO)
    log(country, 'Variables and features saved in folder "features" ', Logs.INFO)
    log(country, "End preprocessings", Logs.INFO)
