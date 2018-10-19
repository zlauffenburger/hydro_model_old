import numpy as np
import econengine as econ
import utils
from utils.crop_coefficient import retrieve_crop_coefficient
from dateutil import parser
import datetime
import rasterio as rio
from rasterio.features import rasterize
import logging
import json


__all__ = ['HydroEconCoupling', 'StrawFarmCoupling']


class StrawFarmCoupling(object):
    @staticmethod
    def retrieve_supplemental_irrigation_map(*args):
        return np.array([0])

    @staticmethod
    def retrieve_water_diversion_per_node(*args):
        return np.zeros((2,1)), np.zeros((2,1))


class HydroEconCoupling(object):
    """Couples the hydrologic and economic models"""

    def __init__(self, routing_obj, water_users_lst, precip_arr, transform):

        self.nodes = routing_obj
        self.water_users = water_users_lst

        self.farms_table = self._build_water_user_matrix()
        self.farm_idx = np.where(self.farms_table[:, 1:])

        # self.array_supplemental_irrigation = np.zeros_like(precip_arr)

        self.water_user_mask = np.zeros_like(precip_arr)

        self.transform = transform

    @staticmethod
    def apply_to_all_members(sequence, attrib, *args, **kwargs):
        """Returns a list with the results of applying attrib to a sequence of objects. Parameter attrib is
        a string with the method name and can be an attribute obj.attrib or a method obj.attrib(*args, **kwargs)"""

        lst = []
        for obj in sequence:
            try:
                lst.append(getattr(obj, attrib)(*args, **kwargs))
            except TypeError:
                lst.append(getattr(obj, attrib))

        return lst

    def setup_farmer_user(self, water_user_shapes, id_field, **kwargs):
        # type: (str, str) -> self
        """Sets the spatial location of farm water users.
        It takes a shape or geojson polygon file with an id field to provide geographical context to water users.

        Parameters
        ==========

        :param water_user_shapes: shape or geojson filename
        :param id_field: name of field in 'water_user_sapes' with farm integer farm IDs

        Returns
        =======
        :returns: HydroEconCoupling object
        """
        self.water_user_mask = self._rasterize_water_user_polygons(water_user_shapes, id_field, **kwargs)

        return self

    def _build_water_user_matrix(self):
        """ Loop through nodes in the network, find farms diverting from it and construct matrix of
         farms associated to each node."""
        nodes = []

        for ids in self.nodes.conn.index:
            li = [ids]
            for farm in self.water_users:
                if farm.get('source_id') == ids:
                    li.append(econ.Farm(**farm))
                else:
                    li.append(0)
            nodes.append(li)
        arr_nodes = np.array(nodes)

        return arr_nodes

    def simulate_all_users(self, lst_scenarios):
        # type: (list) -> FarmCoupling

        for obs in lst_scenarios:
            for farm in self.farms_table[:, 1:][self.farm_idx]:
                if obs.get("farm_id") == farm.source_id:
                    farm.simulate(**obs)

        return FarmCoupling(self.water_users, self.farms_table, self.farm_idx, self.water_user_mask)

    def _rasterize_water_user_polygons(self, fn_water_user_shapes, property_field_name, **kwargs):
        """
        returns a 2D array with rows and cols shape like precipitation inputs
        and vector features pointed by `fn_water_user_shapes` burned in. Burn-in values are these provided by
        `property_field_name`. The function also updates self.array_supplemental_irrigation with the returned array.
        """
        fill = kwargs.get('fill_value', 0)
        shapes = utils.VectorParameterIO(fn_water_user_shapes).read_features()

        try:
            feats = ((g['geometry'], g['properties'][property_field_name]) for g in shapes)
        except KeyError, e:
            print "field name %s does not exist in water user polygon file" %str(property_field_name)
            print e
            exit(-1)


        t = self.water_user_mask = \
            rasterize(feats,
                      self.water_user_mask.shape,
                      fill=fill,
                      transform=self.transform)

        return t


class FarmCoupling(object):

    def __init__(self, water_users_lst, farm_table, farm_idx, water_user_mask):

        self.water_users = water_users_lst
        self.farms_table = farm_table
        self.farm_idx = farm_idx
        self.water_user_mask = water_user_mask

        self.applied_water_factor = np.zeros_like(self.farms_table)

        self.array_supplemental_irrigation = np.zeros_like(self.water_user_mask)

        self._calculate_applied_water_factor()

    def retrieve_water_diversion_per_node(self, date):
        """Returns a vector and a matrix of length ``num_nodes`` and ``num_nodes x num_water_users`` with
         total water diverted from each node and water diverted from each node and user,
         respectively.

         Parameters
         ==========
         :param date: date for which the diversions are required are required

         """

        # obtain vector of crop coefficients
        vect_retrieve_kcs = np.vectorize(retrieve_crop_coefficient, excluded=['current_date'])

        # Obtains water simulated per crop
        s = HydroEconCoupling.apply_to_all_members(self.farms_table[:, 1:][self.farm_idx], "crop_start_date")
        c = HydroEconCoupling.apply_to_all_members(self.farms_table[:, 1:][self.farm_idx], "crop_cover_date")
        e = HydroEconCoupling.apply_to_all_members(self.farms_table[:, 1:][self.farm_idx], "crop_end_date")
        cropid = HydroEconCoupling.apply_to_all_members(self.farms_table[:, 1:][self.farm_idx], "crop_id")

        current_kcs = vect_retrieve_kcs(date, s, c, e, cropid)

        # Obtain water simulated per crop
        Xw = np.vstack(
            HydroEconCoupling.apply_to_all_members(
                self.farms_table[:, 1:][self.farm_idx], "watersim"
            )
        )

        # Obtain applied water factor
        f = np.vstack(self.applied_water_factor[:, 1:][self.farm_idx])

        # Calculated water diverted for each crop and farm

        # diversions per per farm, crop and node
        d = Xw * np.divide(current_kcs, f, where=f != 0)
        D = self.farms_table.copy()
        D[:, 1:][self.farm_idx] = tuple(d)

        # Total diversions per node
        # First sum all water diverted per crop in each farm
        dtot = [fm.sum() for fm in d]
        Dtot = self.farms_table.copy()
        Dtot[:, 1:][self.farm_idx] = dtot
        Dtot = np.vstack((Dtot[:, 0], Dtot[:, 1:].sum(axis=1)))

        return Dtot, D

    def retrieve_supplemental_irrigation_map(self, array_land_use, irr_ag_ids, water_diversion_table):
        """Returns an array with the supplemental irrigation rate on pixels in array ``array_land_use`` with
        id ``irr_ag_ids`` resulting from spreading evenly in space water diverted by water users as provided in
        ``water_diversion_table``"""

        if isinstance(array_land_use, np.ndarray):
            lu = array_land_use
        elif isinstance(array_land_use, basestring):
            lu = utils.RasterParameterIO(array_land_use).array

        else:
            raise TypeError('Incorrect type for argument array_land_use')

        if lu.shape != self.water_user_mask.shape:
            raise ValueError("Land user rasters do not line up with shapes: " +
                             str(lu.shape) + str(self.water_user_mask.shape))

        for i, farm in enumerate(self.water_users):
            farm_id = farm.get('id')
            m = np.count_nonzero(np.isin(lu, irr_ag_ids) & (self.water_user_mask == farm_id))
            applied_water = np.apply_along_axis(np.sum, 0, water_diversion_table[:, i + 1]).sum()
            if m == 0:
                logging.warning("WARNING: water user with id %i is irrigating but water user mask does not contain"
                      " irrigated pixels" %farm_id)

            self.array_supplemental_irrigation = np.where(np.isin(lu, irr_ag_ids) &
                                                                 (self.water_user_mask == farm_id),
                                                          applied_water / m,
                                                          self.array_supplemental_irrigation)

        return self.array_supplemental_irrigation

    def _calculate_applied_water_factor(self):
        """Sets member variable ``applied_water_factor``, a masked matrix of arrays with the water diversion
        adjustment factors per crop and farm.

         The factor takes into account the irrigation efficient as well as the length of the crop period
          expressed as the accumulation of crop coefficients. The factor is defined as follows:

          ::

          f:= Sum_t(Kc_t) * Ieff

        The actual daily water diverted (D) to supply water for each crop can then be calculated as:

         ::

         D = Wtot_t * Kc_t / f

        Factor f and the subsequent calculation of D is calculated per crop. Thus, th function yields a
        vector per farm, with one f per crop.


        """

        Kcs = np.vectorize(retrieve_crop_coefficient)

        lst_kc = []
        for i, farm in enumerate(self.farms_table[:, 1:][self.farm_idx]):
            try:
                dates = zip(farm.crop_start_date,
                            farm.crop_cover_date,
                            farm.crop_end_date,
                            farm.crop_id,
                            farm.irr_eff,
                            farm.irr)
            except TypeError, e:
                print "Water User %s does not have information on crop planting dates. Did you forget to " \
                      "simulate a scenario?" %farm.name
                exit(-1)

            lst = []
            for s, c, e, cropid, i_eff, i_mask, in dates:

                date_array = [(parser.parse(s) + datetime.timedelta(days=x)).strftime("%m/%d/%Y")
                              for x in range(0, (parser.parse(e) - parser.parse(s)).days + 1)]
                lst.append(
                      Kcs(date_array, s, c, e, cropid).sum() * i_eff * i_mask
                )
            lst_kc.append(np.array(lst))

        self.applied_water_factor[:, 1:][self.farm_idx] = lst_kc

    def save_farm_list_json(self, fname):
        """Saves dictionary of farms to disk with name fname."""

        res = [farm.write_farm_dict() for farm in self.farms_table[:, 1:][self.farm_idx]]
        d = {"farms": res}

        with open(fname, 'w') as json_out:
            json.dump(d, json_out)




