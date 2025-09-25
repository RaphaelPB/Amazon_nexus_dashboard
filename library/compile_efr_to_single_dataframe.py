import pandas as pd
import glob
import os

# folder where your csv files are stored
folder = "/home/rpb/majiconsult/amazonII/env_flows/env_flows_from_silvia"

# list all csv files
files = glob.glob(os.path.join(folder, "Level_1_efr_*_hist.csv"))

all_data = []

for file in files:
    # extract catchment id from filename
    catchment_id = os.path.basename(file).split("_")[3]

    # read the csv
    df = pd.read_csv(file)

    # add catchment column
    df["Catchment"] = catchment_id

    # append to list
    all_data.append(df)

# concatenate everything
compiled = pd.concat(all_data, ignore_index=True)

# reorder columns
compiled = compiled[["Catchment", "Month", "EFR (m3/s)"]]

# save result
compiled.to_csv(os.path.join(folder, "compiled_efr.csv"), index=False)

print("✅ Compiled file saved as compiled_efr.csv")