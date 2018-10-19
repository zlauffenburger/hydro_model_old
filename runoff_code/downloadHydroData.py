#!/home/MARCO/anaconda2/bin/python
import retrieveHydroData as rhd
import json
import logging
import os
import glob
import pandas as pd
import datetime
from bokeh.plotting import figure, show, output_file, save
from bokeh.models import FuncTickFormatter, FixedTicker



def update(d, u):
    # Extends the list of values, does not check for duplicates.
    d['value']['timeSeries'][0]['values'][0]['value'].extend(u['value']['timeSeries'][0]['values'][0]['value'])
    return d


def downloadStreamflowFromGeoJson(fnPointFeatures, target_dir='.', startDT="1900-1-1"):
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
        data = fetcher.retrieveQ(stid, startDT=startDT)

        filename = os.path.join(target_dir, stid+'.json')

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


if __name__ == "__main__":

    # Uncomment this to download all available data for the stations in pntsStream into data/streamflow
    #pntsStream = r'data/streamflow/MT_active_gages.geojson'
    #downloadStreamflowFromGeoJson(pntsStream, 'data/streamflow/')
    #exit(0)

    # CONFIGURATION
    # Update streamflow datafiles from the internet

    os.chdir('/var/www/html/runoff_code')
    UPDATE_STREAMFLOW_DATA = True

    # JSon datafile path
    json_data = r'../data/streamflow/[!s]*'

    # output path for html plots
    html_plots = r'../graphs'

    
    #####################################################
    logging.basicConfig(filename='downloadHydroData.log', level=logging.DEBUG, format='%(asctime)s %(message)s')



    flist = glob.glob(json_data)
    #flist = ['../data/streamflow/06290000.json']

    # For each station in the folder
    for f in flist:
        try:
            with open(f, 'r') as fn:
                data = json.load(fn)

            # parse data, get site id and the last date on file
            df, siteId, last_datapoint = json2dataframe(data)


            if(UPDATE_STREAMFLOW_DATA):
                # Download new data and append it to current dataset
                if(not datetime.datetime.now().strftime("%Y-%m-%d")==last_datapoint):

                    print "Downloading data for station ", siteId
                    new_data = rhd.retrieve_streamflows().retrieveQ(siteId, last_datapoint)
                    print new_data
                    print "Updating data for ", siteId
                    data = update(data, new_data.json())
                    df, siteId, last_datapoint = json2dataframe(data)
                    #df.update(df2)
                    # also update the file
                    with open(f, 'w') as fn:
                        json.dump(data, fn)

            df = df.clip(lower=0)  # clip negative values at zero
            df = df.groupby(df.index).first()  # remove duplicates in the index
            df['value'] *= 0.0283168  # convert from f3/sec to cumecs
            print "Generating graph for site ", siteId
            dfbydoy = pd.pivot(df.index.dayofyear, df.index.year, df['value'])
            df['doy'] = df.index.dayofyear
            p = figure(title="Station id "+siteId, plot_width=700, plot_height=500)
            for i in range(len(dfbydoy.columns)):
                p.line(dfbydoy.index, dfbydoy.iloc[:, i], line_color='grey', line_width=1, alpha=0.25)

            this_year = datetime.datetime.now().year
            df2 = df[df.index.year == this_year]
            p.line(df2.index.dayofyear, df2['value'], line_color='red', line_width=2, legend='Current year')
            p.xaxis[0].ticker = FixedTicker(ticks=[1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])
            p.xaxis.formatter = FuncTickFormatter(code="""
                 var labels = {'1':'Jan',32:'Feb',60:'Mar',91:'Apr',121:'May',152:'Jun',182:'Jul',213:'Aug',244:'Sep',274:'Oct',305:'Nov',335:'Dec',366:'Jan'}
                 return labels[tick];
            """)

            p.xaxis.axis_label = 'Day of year'
            p.yaxis.axis_label = 'Streamflow, m3/s'

            out_path = os.path.join(html_plots, siteId)
            print out_path
            output_file(out_path+".html")
            save(p)
        except Exception as e:  # if somethin happens, skip the file
            print "error", e
            logging.exception("Error processing station {0} with message {1}".format(siteId, e))
            #print "skipping graph ", siteId
            continue



