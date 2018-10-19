from runoff_code import retrieveHydroData as rhd
import json
import os
import glob
import pandas as pd

"""
retrieveHydroData class, downloadStreamflowFromGeoJsonand json2dataframe functions taken from Marco Maneta with 
minimal changes.
"""


def downloadStreamflowFromGeoJson(fnPointFeatures, target_dir, startDT, endDT):
    """
    Downloads streamflows from usgs json server using station codes contained in a geoJson point layer.

    :param fnPointFeatures:
    :param target_dir:
    :param startDT:
    :return: None
    """
    with open(fnPointFeatures) as f:
        stmGauges = json.load(f)

    fetcher = rhd.retrieve_streamflows()
    for feats in (stmGauges['features']):
        print "Downloading station " + feats['properties']['STANAME']
        stid = feats['properties']['STAID']
        data = fetcher.retrieveQ(stid, startDT=startDT, endDT=endDT)

        filename = os.path.join(target_dir, stid + '.json')

        with open(filename, 'w') as f1:
            json.dump(data.json(), f1)


def json2dataframe(data):
    """
    Parses a usgs streamflow json object and returns a pandas data frame

    :param usgs_jsondata:
    :return: pandas dataframe, site id
    """
    # Load and parse the available streamflow data
    siteId = data['value']['timeSeries'][0]['sourceInfo']['siteCode'][0]['value']
    df = pd.DataFrame(data['value']['timeSeries'][0]['values'][0]['value'])
    df = df.set_index(df['dateTime'], drop=True)
    df['value'] = df['value'].astype('float32')
    df.index = pd.to_datetime(df.index)
    last_available_date = df.index[-1].strftime("%Y-%m-%d")
    return df, siteId, last_available_date


def format_streamflows(data_dir):
    """
    Creates a pandas dataframe from all streamflow json files

    :param data_dir: path to directory with streamflow JSON files
    :return: pandas dataframe of all streamflow data from all MT gages.
    """

    search_expr = data_dir + "/*.json"

    df = pd.DataFrame()

    for json_file in glob.glob(search_expr):

        with open(json_file, 'r') as fn:
            data = json.load(fn)

        try:
            data = json2dataframe(data)

            new_df = data[0]
            new_df = new_df.drop(columns=['dateTime', 'qualifiers'])
            new_df = new_df.rename(columns={'value': data[1]})
            df = pd.concat([df, new_df], axis=1)

        except IndexError, e:
            print 'Error:', e
            continue

    return df


def aggregateFunctions(fnPointFeatures, start_date, end_date, out_dir):
    """
    Retrieves streamflow data data from usgs and then formats it into a pandas df that matches model output.

    :param fnPointFeatures: path to MT_active_gages.geojson on local machine
    :param start_date: start date to pull data from
    :param end_date: last date to pull data from
    :param out_dir: directory where you want jsons and pandas saved to
    :return: None
    """

    downloadStreamflowFromGeoJson(fnPointFeatures=fnPointFeatures, target_dir=out_dir,
                                  startDT=start_date, endDT=end_date)

    dat = format_streamflows(out_dir)
    fname = out_dir + '/pd_streamflow.csv'

    dat.to_csv(fname)


# example to run code:
# aggregateFunctions('../data/MT_active_gages.geojson', '2016-08-31', '2017-09-01', '../data/streamflow')
