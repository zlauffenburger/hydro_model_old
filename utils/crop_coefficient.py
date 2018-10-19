from __future__ import division
import pandas as pd
from dateutil import parser
import math
from scipy.interpolate import interp1d
import pkg_resources

DATA_PATH = pkg_resources.resource_filename('utils', '/')


def retrieve_crop_coefficient(current_date, start_date, cover_date, end_date,
                              crop_id, kc_table="crop_coefficients.txt"):
    """Returns crop coefficient for current_date interpolated from agMet lookup table. Dates are strings
    with m/d/YYYY format if they are ambiguous (e.g. 06/03/12 is June, 3 2012)

    Parameters
    ==========

    :param current_date: Date for crop coefficient, m/d/YYYY string if dates are ambiguous
    :param start_date: Crop planting date, m/d/YYYY string if dates are ambiguous
    :param cover_date: Date at which crop is fully matured and has reached maximum coverage
    :param end_date: Date at which crop ends, either harvested or dead
    :param crop_id: Integer with crop id from AgMet crop coefficient lookup table
    :param kc_table: Optional. Text lookup with crop coefficient curves. See default table for format.

    Returns
    =======
    :returns: float, crop coefficient of crop_id for corresponding current_date

    """

    df_kc = pd.read_table(DATA_PATH + '/' + kc_table, index_col="crop_id")
    current_date = parser.parse(current_date)
    start_date = parser.parse(start_date)
    cover_date = parser.parse(cover_date)
    end_date = parser.parse(end_date)
    crop_id = int(crop_id)

    if (current_date > start_date) & (current_date < cover_date):
        frac_growing_season = (current_date - start_date).days / (cover_date - start_date).days * 100
        f = interp1d(range(0, 110, 10), df_kc.loc[crop_id][:11])
    elif (current_date >= cover_date) & (current_date <= end_date):
        frac_growing_season = (current_date - cover_date).days / (end_date - cover_date).days * 100
        f = interp1d(range(0, 110, 10), df_kc.loc[crop_id][10:-2])
    else:
        return 0.0

    return f(frac_growing_season)
