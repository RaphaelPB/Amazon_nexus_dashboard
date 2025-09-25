"""
makes a table out of the water quality shapefile
"""

import geopandas as gpd

wq_shapefile_path = '/home/rpb/majiconsult/amazon/QGIS/Water_quality/catchments_withclasses.shp'
wq_export_path = '/home/rpb/majiconsult/amazon/QGIS/Water_quality/water_quality_by_catchment.csv'

wq_df = gpd.read_file(wq_shapefile_path)

# keep relevant columns
wq_df = wq_df[['ncatch','wq_class', 'wq_nvals', 'wq_class_p']]

# make projected or not column
wq_df['data source'] = 'measurement'
wq_df.loc[wq_df['wq_class'].isnull() & ~ wq_df['wq_class_p'].isnull(), 'data source'] = 'projected'

# rename fields
wq_df = wq_df.rename(columns={'ncatch':'catchment', 'wq_class':'measured water quality class','wq_class_p': 'water quality class' })

# export to csv
wq_df.to_csv(wq_export_path, index=False)