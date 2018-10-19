
import pandas as pd
import folium as flm
import json


EMBED_HTML = False

style_function = lambda feature: {
        'fillColor': 'transparent',
        'color': 'black',
        'weight': 2,
        'dashArray': '5, 5'
    }


# Create map
mapMT = flm.Map(location=[47.2, -110], max_zoom=12, control_scale=False, tiles='Stamen Terrain')

# Montana Counties outline
counties_fn = r'../data/countiesMT_4326.geojson'
with open(counties_fn) as f:
    dat = json.load(f)

for feat in (dat['features']):
    name = feat['properties']['NAME']
    gj = flm.GeoJson(data=feat, overlay=True, style_function=style_function, name=name)
    gj.add_to(mapMT)

# Add streamflow stuff
pntsStream = r'../data/streamflow/MT_active_gages.geojson'


with open(pntsStream) as f:
    stmGauges = json.load(f)

snotel_cluster = flm.MarkerCluster().add_to(mapMT)

for feats in (stmGauges['features']):
    lon, lat = feats['geometry']['coordinates']
    id = feats['properties']['STAID']
    icon = flm.Icon(icon='ok')

    try:
        with open('../graphs/'+id+'.html', 'r') as f:
            if (EMBED_HTML):
                html = f.read()
            else:
                html = 'graphs/'+id+'.html'
    except IOError:
        continue

    iframe = flm.IFrame(html=html, width=800, height=600, embed=False)
    pop = flm.Popup(iframe, max_width=2500)
    mark = flm.Marker([lat, lon], icon=icon, popup=pop)
    mark.add_to(snotel_cluster)


#Retrieve geojson
# https://waterservices.usgs.gov/nwis/dv/?format=json,1.1&sites=06090800&startDT=2005-01-01
#flm.LayerControl().add_to(mapMT)

mapMT.fit_bounds(mapMT.get_bounds())
mapMT.save('../streamflowMap.html')
