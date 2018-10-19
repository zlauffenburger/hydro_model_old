from bokeh.plotting import figure, show
from bokeh.palettes import Spectral11
from bokeh.resources import CDN
from bokeh.embed import file_html
import numpy as np

from folium import IFrame

# def plot(data, **kwargs):
#     chart = altair.Chart(data,  **kwargs)
#     chart.mark_line().encode(
#         color='Crop',
#         x='Year',
#         y='Production',
#     )
#     return chart


# def plot(data, title, **kwargs):
#     chart = vincent.Line(data, iter_idx='index', **kwargs)
#     chart.axis_titles(x='Year', y='Production (1000 Tons)')
#     chart.scales[0].type = 'ordinal'
#     chart.title=title
#     chart.legend(title='Crop' + title)
#     return chart





def bokeh_html(series, title, width=600, height=300):

    p = figure(
               title=title,
               width=width, height=height,
               toolbar_location="above",
               x_axis_label="Year",
               y_axis_label="Production (tonsx1000)",
               )
    for i in range(len(series.columns)):
        p.line(series.index.values, series.ix[:, i],
               legend=series.columns[i],
               line_width=2, color=Spectral11[i])
        p.legend.background_fill_alpha = 0.2
        #p.legend.orientation = "horizontal"


    html = file_html(p, CDN, title)
    iframe = IFrame(html, width=width + 40, height=height + 80)

    return iframe

