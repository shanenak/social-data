import base64
import pandas as pd
from six import BytesIO
import geopandas as gpd


def to_excel(df: pd.DataFrame):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1')
    writer.save()
    processed_data = output.getvalue()
    return processed_data


def get_table_download_link(df: pd.DataFrame, file_name: str, text: str) -> str:
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    val = to_excel(df)
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{file_name}.xlsx">{text}</a>'


def output_table(df: pd.DataFrame, path: str):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.to_excel(path)


def make_geojson(geo_df: pd.DataFrame, features: list) -> dict:
    geojson = {"type": "FeatureCollection", "features": []}
    if 'Census Tract' in geo_df.columns:
        for i, row in geo_df.iterrows():
            feature = row['coordinates']['features'][0]
            props = {"name": str(row['Census Tract'])}
            [props.update({f: row[f]}) for f in features]
            feature["properties"] = props
            del feature["id"]
            del feature["bbox"]
            feature["geometry"]["coordinates"] = [feature["geometry"]["coordinates"]]
            geojson["features"].append(feature)
    elif 'Census Tract' not in geo_df.columns:
        for i, row in geo_df.iterrows():
            feature = row['coordinates']['features'][0]
            props = {"name": row['County Name']}
            [props.update({f: row[f]}) for f in features]
            feature["properties"] = props
            del feature["id"]
            del feature["bbox"]
            feature["geometry"]["coordinates"] = [feature["geometry"]["coordinates"]]
            geojson["features"].append(feature)
    return geojson


def convert_coordinates(row) -> list:
    for f in row['coordinates']['features']:
        new_coords = []
        if f['geometry']['type'] == 'MultiPolygon':
            f['geometry']['type'] = 'Polygon'
            combined = []
            for i in range(len(f['geometry']['coordinates'])):
                combined.extend(list(f['geometry']['coordinates'][i]))
            f['geometry']['coordinates'] = combined
        coords = f['geometry']['coordinates']
        for coord in coords:
            for point in coord:
                new_coords.append([round(point[0], 6), round(point[1], 6)])
        f['geometry']['coordinates'] = new_coords
    return row['coordinates']


def convert_geom(geo_df: pd.DataFrame, data_df: pd.DataFrame, map_features: list) -> dict:
    if 'Census Tract' not in data_df:
        data_df = data_df[['county_id'] + map_features]
        data_df=data_df.round(3)
        cols_to_use = list(data_df.columns.difference(geo_df.columns))
        cols_to_use.append('county_id')
        geo_df = geo_df.merge(data_df[cols_to_use], on='county_id', how="outer")
    else:
        data_df = data_df[['Census Tract'] + map_features]
        data_df=data_df.round(3)

        geo_df = geo_df.merge(data_df, on='Census Tract')

    # geo_df.fillna(0,inplace=True)

    geo_df['geom'] = geo_df.apply(lambda row: row['geom'].buffer(0), axis=1)
    geo_df['coordinates'] = geo_df.apply(lambda row: gpd.GeoSeries(row['geom']).__geo_interface__, axis=1)
    geo_df['coordinates'] = geo_df.apply(lambda row: convert_coordinates(row), axis=1)
    geojson = make_geojson(geo_df, map_features)
    return geojson
