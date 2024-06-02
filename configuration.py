#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 18 10:16:59 2024

@author: syed
"""

import os
import argparse, sys
# =============================================================================#
# Data Directories Structure                                                   #
# =============================================================================#



DATA_DIRECTORY = "data" # Main data directory
VAR_DIRECTORY =   "data_explicatives"  # Variables directory
SPATIAL_DIRECTORY = "spatial"  # Spatial data e.g. TIF files
PREPROCESS_DATA_DIR = "staging_data" #data_intermediate, data_pipeline
OUTPUT_DIR = "output" #data_intermediate, data_pipeline
PREPROCESS_FILES = {
    "timeseries":  "data_timeseries.xlsx",
    "conjunctural":  "data_conjunctural.xlsx",
    "structural":  "data_structural.xlsx",
    "all": "data_preprocessed.xlsx",
}

# =============================================================================#
# Datasets: Countries Data                                                     #
# =============================================================================#
countries = {"burkina_faso":"burkina_faso", "rawanda":"rawanda", "tanzania": "tanzania"}

# =============================================================================#
# Output: Prediction Variables                                                 #
# =============================================================================#

OUTPUT_VARIABLES = {"burkina_faso":["sca", "sda"], "rawanda": ["fcs", "hdds"], "tanzania": ["fcs", "hdds"]}

# =============================================================================#
# Survey Response File                                                         #
# =============================================================================#
RESPONSE_FILE = {"burkina_faso":"rep_epa_2009-2018.xlsx","rawanda":"rep_epa_2006-2021.xlsx",
                 "tanzania":"rep_epa_2010-2022.xlsx"}  # Name of the response file

# =============================================================================#
# Features Directory                                                           #
# =============================================================================#

FEATURES_DIRECTORY =  "features/"

# =============================================================================#
# Spatio-temporal Granularity                                                  #
# =============================================================================#

SPATIAL_TEMPORAL_GRANULARITY = {"burkina_faso":["REGION", "PROVINCE", "COMMUNE", "ANNEE"], 
                                "rawanda": [ "province", "district", "year"],
                                "tanzania": [ "region", "district", "year"]}

TEMPORAL_GRANULARITY = {"burkina_faso":"ANNEE", "rawanda":"year", "tanzania": "year"}

# =============================================================================#
# Variables Lists: Time Series, Conjuctural and structural variables           #
# =============================================================================#
vars_timeseries = [
    "rainfall",
    "maize",
    "smt",
    "tmax",
    "tmin",
]  # Features used in the code : ['rainfall', 'maize', 'smt', 'tmax', 'tmin', 'ndvi','grains']
vars_conjuctral = [
    "world_bank",
    "weather",
    "population",
    "ndvi",
]  # conjunctual variables = ['world_bank', 'meteo', 'pop', 'ndvi']
vars_structural = [
    "hospital_education",
    "voilence_events",
    "quality_soil",
    "elevation",
    "waterways",
]  # structural variables = ['hosp_educ', 'acled', 'quality_soil', 'elevation', 'waterways']

# =============================================================================#
# Spatial Data files                                                           #
# =============================================================================#
PIXEL = "100m"
SPATIAL_TIF_VARS = {
    "epa": "epa_" + PIXEL + "_com.tif",
    "crop": "crop_mean_" + PIXEL + ".tif",
    "forest": "forest_mean_" + PIXEL + ".tif",
    "zones": "built_mean_" + PIXEL + ".tif",
}

# =============================================================================#
# Temporal Range                                                               #
# =============================================================================#

TIME_RANGE = [2009, 2018]
