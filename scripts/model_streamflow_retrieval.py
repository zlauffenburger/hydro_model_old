import json
import pandas as pd

with open("/home/geoscigrad/workspace/dawuaphydroengine/docs/example/streamflows.json") as f:
    flows = json.load(f)
    dfModel_streamflows = pd.DataFrame()
    nodes = flows['nodes']

    for node in nodes:
        id = node['id']
        date_list = node['dates']
        flows = pd.DataFrame(date_list, columns=['date', 'flow'])
        flows = flows.rename(columns={'flow': id})
        flows = flows.set_index(['date'])
        flows.index = pd.to_datetime(flows.index)

        dfModel_streamflows = pd.concat([dfModel_streamflows, flows], axis=1)

dfModel_streamflows.to_csv("/home/geoscigrad/workspace/hydro_model/dfModel_streamflows.csv")
