import geopandas as gpd
import pandas as pd
import numpy as np

# --- Load ---
wq_shapefile = "/home/rpb/majiconsult/amazon/QGIS/Water_quality/ana_cobrape_merged_waterquality_withclasses.shp"
wq_df = gpd.read_file(wq_shapefile)

# --- Original column sets you provided ---
station_metadata = ['codigo', 'pais', 'x', 'y', 'sub_bacia', 'class_merg']
water_quality_parameters = ['condu_elet', 'dbo', 'dqo', 'fosforotot', 'nitrato', 'od', 'solid_susp', 'turbidez', 'ph']
water_quality_classes = ['class_bod', 'class_do', 'class_TP', 'class_turb']

# --- Optional: ensure lon/lat (EPSG:4326) for maps ---
if wq_df.crs is not None:
    try:
        if wq_df.crs.to_epsg() != 4326:
            wq_df = wq_df.to_crs(4326)
    except Exception:
        pass

# Derive x/y from geometry if needed
if 'x' not in wq_df.columns or wq_df['x'].isna().all():
    wq_df['x'] = wq_df.geometry.x
if 'y' not in wq_df.columns or wq_df['y'].isna().all():
    wq_df['y'] = wq_df.geometry.y

# --- Map parameters that have a class column ---
param_to_class = {
    'dbo': 'class_bod',
    'od': 'class_do',
    'fosforotot': 'class_TP',
    'turbidez': 'class_turb',
}

# --- Safety check for expected columns ---
needed_cols = list({*station_metadata, *water_quality_parameters, *param_to_class.values()})
missing = [c for c in needed_cols if c not in wq_df.columns]
if missing:
    raise KeyError(f"These expected columns are missing from the shapefile: {missing}")

# --- Melt to long: parameter + value ---
long_vals = wq_df[station_metadata + water_quality_parameters].melt(
    id_vars=station_metadata,
    var_name='parameter',
    value_name='value'
)

# --- Bring in classes for params that have them ---
class_pieces = []
for param, class_col in param_to_class.items():
    tmp = wq_df[station_metadata + [class_col]].copy()
    tmp['parameter'] = param
    tmp.rename(columns={class_col: 'class'}, inplace=True)
    class_pieces.append(tmp)

if class_pieces:
    classes_long = pd.concat(class_pieces, ignore_index=True)
    long_df = long_vals.merge(classes_long, on=station_metadata + ['parameter'], how='left')
else:
    long_df = long_vals
    long_df['class'] = pd.NA

# --- Convert parameter codes (PT) -> English names, and add units ---
param_en_map = {
    'condu_elet': 'Electrical conductivity',
    'dbo': 'Biochemical oxygen demand (BOD)',
    'dqo': 'Chemical oxygen demand (COD)',
    'fosforotot': 'Total phosphorus',
    'nitrato': 'Nitrate',
    'od': 'Dissolved oxygen (DO)',
    'solid_susp': 'Suspended solids',
    'turbidez': 'Turbidity',
    'ph': 'pH',
}
unit_map = {
    'Electrical conductivity': 'µS/cm',
    'Biochemical oxygen demand (BOD)': 'mg/L',
    'Chemical oxygen demand (COD)': 'mg/L',
    'Total phosphorus': 'mg/L',
    'Nitrate': 'mg/L',
    'Dissolved oxygen (DO)': 'mg/L',
    'Suspended solids': 'mg/L',
    'Turbidity': 'NTU',
    'pH': 'unitless',
}

# translate parameter names
long_df['parameter'] = long_df['parameter'].map(param_en_map).fillna(long_df['parameter'])
# add units based on (English) parameter name
long_df['unit'] = long_df['parameter'].map(unit_map)

# --- Ensure numeric values where appropriate ---
long_df['value'] = pd.to_numeric(long_df['value'], errors='coerce')
long_df = long_df.dropna(subset=['value'])

# --- Rename station/metadata columns to English ---
rename_cols_en = {
    'codigo': 'station_id',
    'pais': 'country',
    'x': 'longitude',
    'y': 'latitude',
    'sub_bacia': 'sub_basin',
    'class_merg': 'overall_class',
}
long_df = long_df.rename(columns=rename_cols_en)

# -----------------------------
# filter values
# -----------------------------

valid_ranges = {
    'pH': (4, 10),
    'Dissolved oxygen (DO)': (0, 50),
    'Biochemical oxygen demand (BOD)': (0, 80),
    'Chemical oxygen demand (COD)': (0, 300),
    'Total phosphorus': (0, 5),
    'Nitrate': (0, 50),
    'Suspended solids': (0, 1000),
    'Turbidity': (0, 1000),
    'Electrical conductivity': (0, 5000),
}

def filter_realistic(df):
    mask = pd.Series(True, index=df.index)
    for param, (lo, hi) in valid_ranges.items():
        sel = df['parameter'] == param
        mask &= ~sel | df['value'].between(lo, hi)
    return df[mask]

long_df = filter_realistic(long_df)

# -----------------------------
# Add BIN COLUMNS (no extra table)
# -----------------------------
BINS = 10           # change as needed
BIN_METHOD = "width"  # "width" or "quantile"

def _bins_equal_width(g: pd.DataFrame) -> pd.DataFrame:
    v = g['value'].astype(float)
    vmin = v.min()
    vmax = v.max()
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        # one-value or invalid: put everything in a single bin 0
        return g.assign(
            bin_index=0,
            bin_start=vmin,
            bin_end=vmax,
            bin_sort=0,
            bin_label=(pd.Series([vmin]).round(3).astype(str) + '–' +
                       pd.Series([vmax]).round(3).astype(str)).iloc[0]
        )
    width = (vmax - vmin) / BINS
    idx = np.floor((v - vmin) / width).astype(int)
    idx = np.clip(idx, 0, BINS - 1)
    start = vmin + idx * width
    end = start + width
    label = start.round(3).astype(str) + '–' + end.round(3).astype(str)
    return g.assign(
        bin_index=idx.astype(int),
        bin_start=start,
        bin_end=end,
        bin_sort=idx.astype(int),
        bin_label=label
    )

def _bins_quantile(g: pd.DataFrame) -> pd.DataFrame:
    v = g['value'].astype(float).values
    v = v[np.isfinite(v)]
    if v.size == 0:
        return g.assign(bin_index=np.nan, bin_start=np.nan, bin_end=np.nan,
                        bin_sort=np.nan, bin_label=np.nan)
    # Quantile edges (unique to avoid zero-width bins)
    qs = np.linspace(0, 1, BINS + 1)
    edges = np.unique(np.quantile(v, qs))
    # If too few unique edges, fall back to equal-width
    if edges.size < 2:
        return _bins_equal_width(g)
    # Digitize with right-open bins
    idx = np.digitize(g['value'].astype(float), edges[1:-1], right=False)
    # Build starts/ends by index
    starts = pd.Series(edges[idx], index=g.index)
    ends = pd.Series(edges[np.minimum(idx + 1, edges.size - 1)], index=g.index)
    labels = starts.round(3).astype(str) + '–' + ends.round(3).astype(str)
    return g.assign(
        bin_index=idx.astype(int),
        bin_start=starts,
        bin_end=ends,
        bin_sort=idx.astype(int),
        bin_label=labels
    )

if BIN_METHOD == "quantile":
    long_df = long_df.groupby('parameter', group_keys=False).apply(_bins_quantile)
else:
    long_df = long_df.groupby('parameter', group_keys=False).apply(_bins_equal_width)

# -----------------------------
# Final column order (adds bins)
# -----------------------------
ordered_cols = [
    'station_id','country','longitude','latitude','sub_basin','overall_class',
    'parameter','unit','value',
    'bin_index','bin_start','bin_end','bin_label','bin_sort',
    'class'
]
existing = [c for c in ordered_cols if c in long_df.columns]
long_df = long_df[existing]

# Save (single table with bins)
out_csv = "/home/rpb/majiconsult/amazon/QGIS/Water_quality/water_quality_long_with_bins.csv"
long_df.to_csv(out_csv, index=False)
print(f"Saved with bins: {out_csv}")
print(long_df.head(10))
