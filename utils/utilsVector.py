# -*- coding: utf-8 -*-
"""Classes to manipulate vector datasets used in daWUAP.

The ReadVector base class reads and writes fiona geometry objects. This class is inherited by
the other three classes in this module.

"""
from __future__ import division
#import numpy as np
import pandas as pd
#import shapefile as shp
import fiona
from shapely.geometry import mapping, shape


class ReadVector(object):

    """Base class to read vector datasets using Fiona.

    Reads and stores metadata from fiona objects, and facilitates the writing of vector files.


    """

    def __init__(self, fn_vector):
        """The constructors requires a path to a file such as 'data/map_spain.shp'.

        An internal call to the protected ``_read_fiona_object()`` method opens the file and
        populates the metadata variables.

        """
        self.fn_vector = fn_vector
        # Next three variables are updated after the call to _read_fiona_object()
        self.crs = None
        self.schema = None
        self.driver = None
        self._read_fiona_object()

    def _read_fiona_object(self):
        """Returns an iterator over records in the vector file"""
        # test it as fiona data source
        features_iter = None
        try:
            with fiona.open(self.fn_vector, 'r') as src:
                assert len(src) > 0
                self.crs = src.crs
                self.schema = src.schema.copy()
                self.driver = src.driver

            def fiona_generator(obj):
                with fiona.open(obj, 'r') as src2:
                    for feature in src2:
                        yield feature

            features_iter = fiona_generator(self.fn_vector)

        except (AssertionError, TypeError, IOError, OSError):
            print "fn_vector does not point to a fiona object, error "

        return features_iter

    def _write_fiona_object(self, fn, crs=None, driver=None, schema=None, params=None):
        """Writes a vector file using fn_vector as template.

        Returns nothing.


        :param fn: output file name
        :param crs:
        :param driver:
        :param schema:
        :param params: dictionary
        :type fn: str
        :type driver: str
        :type schema: str
        :type params: dict
        :return: None
        :rtype: None

        .. todo:: Solve problem writing projection info in shp and geojson. Also overwriting geojson files
        """
        if crs is None:
            crs = self.crs
        if driver is None:
            driver = self.driver
        if schema is None:
            schema = self.schema

        # TODO: solve problems writing projection information in shapefiles and geojson
        feature_iter = self._read_fiona_object()
        with fiona.open(fn, 'w', crs=crs, driver=driver, schema=schema) as sink:

            for i, feats in enumerate(feature_iter):
                geom = shape(feats['geometry'])
                if params is not None:
                    props = params[i]['properties']
                else:
                    props = feats['properties']
                sink.write({'properties': props, 'geometry': mapping(geom)})


class ParseNetwork(ReadVector):
    """Returns a dataframe.

    Class to parse the model stream network. It calculates the connectivity matrix
    during the initialization and makes it available as a class variable.
    This class has the following public methods:

    - get_parameter(param): returns a list with the value of this parameter for all river reaches
    """

    def __init__(self, fn_vector):
        super(ParseNetwork, self).__init__(fn_vector)
        self.conn_matrix = self._calc_connectivity_matrix()

    def _calc_connectivity_matrix(self):
        feature_iter = self._read_fiona_object()

        lst_node_connections = []

        for i, feats in enumerate(feature_iter):
            geom = shape(feats['geometry'])
            props = feats['properties']
            lst_node_connections.append((props["FROM_NODE"], props["TO_NODE"]))

        lstNodes = set(zip(*lst_node_connections)[0])
        df = pd.DataFrame(0, index=lstNodes, columns=lstNodes)
        # drop the connections that go out of the basin to node 0
        lst_node_connections = [i for i in lst_node_connections if i[1]>0]
        for link in lst_node_connections:
            df.loc[link] = 1

        return df

    def get_parameter(self, param):

        """
        Retrieves a list of values associated with the :param: parameter
        :param param: string with name of the parameter to retrieve
        :return: list of parameter values in the order they appear in the river network dictionary
        """
        feature_iter = self._read_fiona_object()

        lst_param = []

        for i, feats in enumerate(feature_iter):
            lst_param.append(
                feats['properties'][param]
            )
        return lst_param


class VectorParameterIO(ReadVector):
    """
    Class to provide model parameter fields adn values to network and basin vector datasets.
    It has the following public methods:

    """
    def __init__(self, fn_vector):
        """
        Initializes the object with a polygon (basin) or multiline (network) vector dataset
        :param fn_vector: fn of vector dataset
        """
        super(VectorParameterIO, self).__init__(fn_vector)

    def read_features(self):
        """
        return a generator of features in the dataset
        :return: fiona generator
        """
        return self._read_fiona_object()

    def write_dataset(self, fn, crs=None, driver=None, schema=None, params=None):
        """
        Writes a vector file using fn_vector as template
        :param fn: outfile name
        :param crs:
        :param driver:
        :param schema:
        :param params: dictionary
        :return: None
        """
        return self._write_fiona_object(fn, crs, driver, schema, params)


class ModelVectorDatasets(object):
    """
    Class to handle the the manipulation of all vector dataset in the model
    """
    def __init__(self, fn_network=None, fn_subsheds=None):

        self.network = None
        self.subsheds = None

        if fn_network is not None:
            self.network = VectorParameterIO(fn_network)
        if fn_subsheds is not None:
            self.subsheds = VectorParameterIO(fn_subsheds)

    def write_muskingum_parameters(self, outfn, params=None):
        # type: (str, list) -> None
        """
        Adds or updates the vector network file with the Muskingum-Cunge
        parameters. If params is not provided, the dataset is updated with default parameter
        values.

        :param outfn: filename for updated vector network
        :param params: list of parameter dictionaries with format [{'ARCID': ID, 'e': value, 'ks': value},{}]
        :return: None
        """
        # Check if network dataset is present
        if self.network is None:
            return

        schema = self.network.schema.copy()
        schema['properties']['e'] = 'float'
        schema['properties']['ks'] = 'float'

        lstDicts = []
        feature_iter = self.network.read_features()
        for i, feats in enumerate(feature_iter):
            arc_id = feats['properties']['ARCID']
            print("Processing reach feature id %i" % arc_id)
            try:
                val = (item for item in params if item['ARCID'] == arc_id).next()
            except:
                val = {}
            feats['properties']['e'] = val.get('e', 0.35)
            feats['properties']['ks'] = val.get('ks', 82400)
            lstDicts.append(feats)

        self.network.write_dataset(outfn, schema=schema, params=lstDicts)

    def write_hvb_parameters(self, outfn, params=None):
        # type: (str, list) -> None
        """
        Adds or updates the vector file of model subwatersheds with the hbv RR model parameters.
        If params is not provided, the dataset is updatd with default parameter values

        :param outfn: filename for updated vector network
        :param params: list of parameter dictionaries with format []
        :return: None
        """
        if self.subsheds is None:
            return

        schema = self.subsheds.schema.copy()
        schema['properties']['hbv_ck0'] = 'float'
        schema['properties']['hbv_ck1'] = 'float'
        schema['properties']['hbv_ck2'] = 'float'
        schema['properties']['hbv_hl1'] = 'float'
        schema['properties']['hbv_perc'] = 'float'
        schema['properties']['hbv_pbase'] = 'int'

        lstDicts = []
        feature_iter = self.subsheds.read_features()
        for i, feats in enumerate(feature_iter):
            arc_id = feats['properties']['GRIDCODE']
            print("Processing subwatershed feature id %i" %arc_id)
            try:
                val = (item for item in params if item['GRIDCODE'] == arc_id).next()
            except:
                val = {}

            feats['properties']['hbv_ck0'] = val.get('hbv_ck0', 10.)
            feats['properties']['hbv_ck1'] = val.get('hbv_ck1', 50.)
            feats['properties']['hbv_ck2'] = val.get('hbv_ck2', 10000)
            feats['properties']['hbv_hl1'] = val.get('hbv_hl1', 50)
            feats['properties']['hbv_perc'] = val.get('hbv_perc', 50)
            feats['properties']['hbv_pbase'] = val.get('hbv_pbase', 5)
            lstDicts.append(feats)

        self.subsheds.write_dataset(outfn, schema=schema, params=lstDicts)





# def add_muskingum_model_parameters_to_network(vectorNetwork, outshp=''):
#     """
#     Add default muskingum cunge parameters to streamflow network
#     :param vectorNetwork:
#     :param outshp:
#     :return:
#     """
#
#     def _read_features(inFile):
#         # test it as fiona data source
#         features_iter = None
#         try:
#             with fiona.open(inFile, 'r') as src:
#                 assert len(src) > 0
#
#             def fiona_generator(obj):
#                 with fiona.open(obj, 'r') as src:
#                     for feature in src:
#                         yield feature
#
#             features_iter = fiona_generator(inFile)
#
#         except (AssertionError, TypeError, IOError, OSError):
#             print "fn_vector does not point to a fiona object, error "
#
#         return features_iter
#
#     feature_iter = _read_features(vectorNetwork)
#     lst_node_connections = []
#
#     for i, feats in enumerate(feature_iter):
#         geom = shape(feats['geometry'])
#         props = feats['properties']
#         lst_node_connections.append((props["FROM_NODE"], props["TO_NODE"]))
#
#
# def add_rr_model_parameters_to_shapefile(shapefile, outshp=''):
#     """
#     Add default field and parameter values to shapefile. A bug in the pyShp library
#     handles incorrectly Date fields. If date fields are contained in the shapefile
#     the library needs to be patched including the follwing lines in shapefile.py:
#
#     from datetime import date
#     comment out line 525 and replace by:
#      value = date(y,m,d).strftime('%Y%m%d')
#     :param shapefile: Polygon (catchment) shapefile to which parameter fields will be added
#     :param outshp: optional, output shapefile filename. Overwrite original if empy
#     :return: None
#     """
#     r = shp.Reader(shapefile)
#     w = shp.Writer(r.shapeType)
#     w.autoBalance = 1
#
#     w.fields = list(r.fields)
#     #w.records.extend(r.records())
#     w._shapes.extend(r.shapes())
#
#     fldnames = [fld[0] for fld in w.fields]
#
#     if 'hbv_ck0' not in fldnames:
#         w.field('hbv_ck0', 'N', 10, 6)
#     if 'hbv_ck1' not in fldnames:
#         w.field('hbv_ck1', 'N', 10, 6)
#     if 'hbv_ck2' not in fldnames:
#         w.field('hbv_ck2', 'N', 10, 6)
#     if 'hbv_hl1' not in fldnames:
#         w.field('hbv_hl1', 'N', 10, 6)
#     if 'hbv_perc' not in fldnames:
#         w.field('hbv_perc', 'N', 10, 6)
#     if 'hbv_pbase' not in fldnames:
#         w.field('hbv_pbase', 'N', 10, 0)
#
#     counter = 1
#     for ca in r.records():
#         print "Appending parameter to record ", counter
#         ca.append(10.0)
#         ca.append(50.0)
#         ca.append(10000.0)
#         ca.append(50.0)
#         ca.append(50.0)
#         ca.append(5)
#         w.records.append(ca)
#         counter += 1
#
#     #w.records.append(('hbv_ck0', '1.0'))
#     if not outshp:
#         outshp=shapefile
#
#     w.save(outshp)
#     r = w = None
#
# #add_rr_model_parameters_to_shapefile('test_data/HUC8_NetworkLite.shp')

