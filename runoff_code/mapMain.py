
import pandas as pd
import folium as flm
import json
import jsonplotting


counties_fn = r'../data/countiesMT_4326.geojson'
rsdata_fn = r'../data/yield_data.csv'

df = pd.read_csv(rsdata_fn)
df['County'] = map(lambda x: x.upper(), df['County'])
with open(counties_fn) as f:
    dat = json.load(f)

dfPivoted = df.pivot_table(df, index=['County', 'Crop'])
dfPivoted/=1000000
#df = dfPivoted.xs('Alfalfa', level='Crop').reset_index()
dfstacked = dfPivoted.stack()

#df = df['2011']
#df.to_json('alfalfa.json')

style_function = lambda feature: {
        'fillColor': '#ffff00',

        'color': 'black',
        'weight': 2,
        'dashArray': '5, 5'
    }

mapMT = flm.Map(location=[47.2, -110], max_zoom=8, control_scale=False)

for feat in (dat['features']):
    name = feat['properties']['NAME']
    gj = flm.GeoJson(data=feat, overlay=True, style_function=style_function, name=name)

    dfrm = dfstacked.xs(name, level='County')
    dfrm = dfrm.unstack(level=0)
    plot = jsonplotting.bokeh_html(dfrm, name)
    pop = flm.Popup(plot, max_width=800)
    gj.add_child(pop)
    gj.add_to(mapMT)


mapMT.fit_bounds(mapMT.get_bounds())
mapMT.save('cropProduction.html')
