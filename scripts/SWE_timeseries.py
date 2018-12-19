import pandas as pd
import matplotlib.pyplot as plt

nrcs_swe = pd.read_csv('/home/geoscigrad/workspace/output_processing/snotel_swe.csv')
model_swe = pd.read_csv('/home/geoscigrad/workspace/output_processing/dfFinal_90runs.csv')
nrcs_swe.set_index('date', inplace=True)
model_swe.set_index('date', inplace=True)

model_swe['1008'].plot()
nrcs_swe['1008'].plot()
plt.xlabel('Date')
plt.ylabel('SWE (mm)')
plt.title('SWE Calibration\nSNOTEL Station 1008')
plt.legend(['Simulated', 'NRCS'])
plt.show()

model_swe['1009'].plot()
nrcs_swe['1009'].plot()
plt.xlabel('Date')
plt.ylabel('SWE (mm)')
plt.title('SWE Calibration\nSNOTEL Station 1009')
plt.legend(['Simulated', 'NRCS'])
plt.show()