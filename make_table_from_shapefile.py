import geopandas as gpd
# input
file_path = "/home/rpb/majiconsult/amazon/QGIS/Boundaries/amazon_nexus_catchments_ORA_EPSG4326_withbasinID.shp"
# output
out_path = file_path[:-4] + '_table.csv'

# map basins to catchments
map_basins = True
# basin_file
basin_path = "/home/rpb/majiconsult/amazon/QGIS/Boundaries/OTCA_plus_main_basins/OTCA_plus_MainBasins_v2_fixed.shp"

# open shapefile
shapefile_df = gpd.read_file(file_path)


# Map basins into shapefile
if map_basins:
    # open shapefile
    basin_df = gpd.read_file(basin_path)
    # Compute centroids of each catchment in shapefile_df
    shapefile_df['centroid'] = shapefile_df.geometry.centroid
    # Convert centroids into a new GeoDataFrame
    centroids_gdf = gpd.GeoDataFrame(shapefile_df.drop(columns='geometry'),
                                     geometry=shapefile_df['centroid'],
                                     crs=shapefile_df.crs)
    # Perform spatial join: find which basin each centroid falls into
    joined = gpd.sjoin(centroids_gdf, basin_df[['ID', 'geometry']], how='left', predicate='within')
    # Map the 'ID' from basin_df back to the original shapefile_df
    shapefile_df['basin_ID'] = joined['ID']
    # fill surrounding basins with the AMZ_OTCA basin
    shapefile_df['basin_ID'] = shapefile_df['basin_ID'].fillna('AMZ_OTCA')
    # Drop the temporary centroid column if desired
    shapefile_df = shapefile_df.drop(columns='centroid')
    # save shapefile
    shapefile_df.to_file(file_path)


# export
shapefile_df.drop('geometry',axis=1).to_csv(out_path, index=False)