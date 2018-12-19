import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

usgs_streamflow = pd.read_csv('/home/geoscigrad/workspace/hydro_model/data/USGS_streamflow_2012-08-30_2013-08-31.csv')
model_streamflow = pd.read_csv('/home/geoscigrad/workspace/hydro_model/data/Model_streamflows.csv')
usgs_streamflow.set_index('date', inplace=True)
model_streamflow.set_index('date', inplace=True)


usgs_streamflow.to_csv('/home/geoscigrad/workspace/hydro_model/data/dfUSGS_streamflow_2012-08-30_2013-08-31.csv')
model_streamflow.to_csv('/home/geoscigrad/workspace/hydro_model/data/dfModel_streamflows.csv')

usgs_streamflow.from_csv('/home/geoscigrad/workspace/hydro_model/data/dfUSGS_streamflow_2012-08-30_2013-08-31.csv', index_col=0)
model_streamflow.from_csv('/home/geoscigrad/workspace/hydro_model/data/dfModel_streamflows.csv', index_col=0)
#


model_streamflow['13'].plot()
usgs_streamflow['13'].plot()
plt.xlabel('Date')
plt.ylabel('Discharge (m3/yr)')
plt.title('Streamflow Calibration\nNode 13')
plt.legend()
plt.show()


#print model_streamflow