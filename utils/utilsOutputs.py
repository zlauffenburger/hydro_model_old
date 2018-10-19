from __future__ import division
import numpy as np
import pandas as pd
import datetime
from dateutil.parser import parse
import json


class WriteOutputTimeSeries(object):

    """
    Handles model time series outputs
    """

    def __init__(self,  conn_matrix, init_date, dt=1):
        """ Initializes object with connectivity matrix, the initial date and the size
        of the simulation time step (defaults to 1 day)

        :param conn_matrix: connectivity matrix of stream network, pandas dataframe
        :param init_date: date of first time step, string
        :param dt: time step size, days
        """

        self.conn_matrix = conn_matrix
        self.init_date = parse(init_date)
        self.dt = datetime.timedelta(days=dt)

    def write_json(self, data):
        """
        Writes list of model outputs at each node as a JSON file with the following format:

        {
            "nodes": [
            {
            "id": 1,
            "dates": [
                {
                "date: "10/01/2009",
                "flow": 245.3
                },
                {
                "date: "10/02/2009",
                "flow": 245.3
                },
                ]
            },
            {
            "id": 2,
            "dates": [
                {
                "date: "10/01/2009",
                "flow": 245.3
                },
                {
                "date: "10/02/2009",
                "flow": 245.3
                },
                ]
            },

            ]
        }

        The function returns a json dictionary and saves it to
        :param data: list of lists of numpy array with flows
        :return: json dictionary in the format described above
        """
        lst_nodes = []
        data = np.array(data).T
        for row, nodeid in enumerate(self.conn_matrix.index.values):
            node = {"id": nodeid}
            node["dates"] = \
                [{"date": (self.init_date + ts * self.dt).strftime("%Y/%m/%d"),
                  "flow": d} for ts, d in enumerate(data[row])]

            lst_nodes.append(node)

        dict_nodes = {"nodes": lst_nodes}

        with open(r'streamflows.json', 'w') as buff:
            json.dump(dict_nodes, buff, indent=4)

        return dict_nodes





