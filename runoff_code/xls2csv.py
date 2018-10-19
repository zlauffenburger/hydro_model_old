import numpy as np
import pandas as pd
import glob

list_fn = glob.glob(r'data/[!~]*.xlsx')

dfYields = pd.DataFrame()
lst_ylds=[]
# For each file crop
print list_fn
for fn in list_fn:
    crop = fn.split('_')[0].split('/')[1]
    print crop
    xlsdf = pd.read_excel(fn, sheetname=None, index_col=None, header=None, skiprows=2,
                          parse_cols=2, names=['County', 'Prod', 'Std'])

    yr, ylds = xlsdf.keys(), xlsdf.values()
    print type(ylds)
    for i in range(len(yr)):
        ylds[i]['Year'] = yr[i]
        ylds[i]['Crop'] = crop

    dfYields = dfYields.append(ylds)





print set(dfYields['Crop'])
dfYields = pd.pivot_table(dfYields, index=['County', 'Crop'], columns='Year', values='Prod')

dfYields.to_csv(r'data/yield_data.csv')