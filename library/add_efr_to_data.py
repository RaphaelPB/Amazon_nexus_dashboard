"""
This code adds relevant efr data to powerBI data
"""

import pandas as pd
import numpy as np

# EFR data
efr_data_path = '/home/rpb/majiconsult/amazonII/env_flows/compiled_efr.csv'

# water consumption
waterbalance_data_path = '/home/rpb/majiconsult/amazonII/env_flows/water_available_and_consumption_by_source_catchment_time_step.csv'
waterbalance_output_path = '/home/rpb/majiconsult/amazonII/env_flows/water_available_and_consumption_by_source_catchment_time_step_with_EFR.csv'

# load data
# EFR
efr_df = pd.read_csv(efr_data_path)
efr_df['EFR (Mm3/month)']=efr_df['EFR (m3/s)']*3600*24*365/12/10**6
efr_df['catchment'] = 'c'+ efr_df['Catchment'].astype(str)
# water balance
wb_df = pd.read_csv(waterbalance_data_path)
wb_df['outflow (Mm3/month)'] = wb_df['water available (Mm3/month)'] - wb_df['total water consumption (Mm3/month)']

# Merge EFR and water balance
# Month name to match the EFR table (January, February, ...)
wb_df["Month"] = pd.to_datetime(wb_df["time step"]).dt.month_name()
wb_merged = wb_df.merge(efr_df,on=["catchment", "Month"],how="left")
# drop useless columns
wb_merged = wb_merged.drop(columns=['EFR (m3/s)', 'Month', 'Catchment'])

# look if EFR constrain is satisfied
wb_merged['EFR_violation'] = (wb_merged['EFR (Mm3/month)'] > wb_merged['water available (Mm3/month)']).astype(int)

# water consumption ratio including EFR
wb_merged['water consumption ratio including EFR (%)'] = ((wb_merged['total water consumption (Mm3/month)'] + wb_merged['EFR (Mm3/month)'])
                                                          /wb_merged['water available (Mm3/month)'])*100
# net water consumption ratio max(0, water available - EFR)
wb_merged['net water available (Mm3/month)'] = wb_merged['water available (Mm3/month)'] - wb_merged['EFR (Mm3/month)']
wb_merged.loc[wb_merged['net water available (Mm3/month)']<0,'net water available (Mm3/month)'] = 0
wb_merged['net water consumption ratio (%)'] = (wb_merged['total water consumption (Mm3/month)']
                                                          /wb_merged['net water available (Mm3/month)'])*100
wb_merged.replace([np.inf, -np.inf], np.nan, inplace=True)
# export data again
wb_merged['EFR (Mm3/month)'] = wb_merged['EFR (Mm3/month)'].round(3)
wb_df['outflow (Mm3/month)'] = wb_df['outflow (Mm3/month)'].round(3)
wb_merged['net water available (Mm3/month)'] = wb_merged['net water available (Mm3/month)'].round(3)
wb_merged['net water consumption ratio (%)'] = wb_merged['net water consumption ratio (%)'].round(2)
wb_merged['water consumption ratio including EFR (%)'] = wb_merged['water consumption ratio including EFR (%)'].round(2)

wb_merged.to_csv(waterbalance_output_path, index=False)
print('end')