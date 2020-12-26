#%% IMPORTS
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import geopandas as gp

mpl.rcParams.update({
    'axes.titlesize': 16,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 13,
    'legend.title_fontsize': 15,
})

#%% INPUTS

# root directory of the data & code
DATA_DIR = '/Volumes/Seagate_RV/Research_Data/SG_Covid19'
CODE_DIR = '/Volumes/data/OneDrive - purdue.edu/Purdue/Research/COVID19_Business/code'

# relevant files/folders, all located inside the root `DATA_DIR`
IO = {k: DATA_DIR + '/' + v for k, v in {
    # base directory of the county data (contains folder for each state)
    'cnty_root': 'county_wise',
    # directory containing data of regions (cities)
    'city_root': 'city_wise',
    # info of regions (cities): their counties and COVID-related events
    'city_info': 'city_wise/cities_meta.json',
    # NAICS codes
    'naics': 'places/2017_NAICS_descriptions.csv',
    # POI Ids
    'pois': 'places/all_pois.csv',
    # shapfefile of the zip areas along with counties
    'zips_shp': 'geometry/us_zcta_2018/cb_2018_us_zcta510_500k.shp',
    # mapping between zip & CBG codes
    'zip2tract': 'geometry/zcta_tract_rel_10.csv',
    # location of shapefiles of states, indexed by state fips code
    'state_shp': 'geometry/states_shapefile_cbg/tl_2019_{0:02}_bg/tl_2019_{0:02}_bg.shp',
    # NYC cases data by zip code (static for one day; earliest date May 18)
    'nyc_cases': 'health_cases/nyc/data-by-modzcta.csv',
    # NYC cases data by zip code daily (up to May 18)
    # from https://github.com/thecityny/covid-19-nyc-data/
    'nyc_cases_old': 'health_cases/nyc/thecityny.csv',
    # NYC cases data by zip code (static for one day; beginning May 18)
    'nyc_cases_new': 'health_cases/nyc/nyc_zip_data_daily.csv',
    # Chicago cases by zip code
    'chi_cases': 'health_cases/cases-zip-chicago.csv',
    # Illinois cases by zip code
    'il_cases': 'health_cases/cases-zip-illinois.csv'
}.items()}

# periods of interest
# these are the dates for which data had been prepared
# & file names bear these dates
# weeks (for patterns data)
WEEKS = pd.date_range('2019-12-30', '2020-06-23', freq='W-MON')

# dates (for social distancing data)
DATES = pd.date_range('2020-01-01', '2020-06-30')

# the baseline to be used to compare the ratio of POI mobility metrics
# like RPS and PET to get the idea of how these metrics changed over time
# instead of their absolute values
BASELINE = '2020-02-01'

# details of the 5 dwell-time buckets
DWELL_BINS = {
    'names': ['0-5', '5-20', '20-60', '60-240', '>240'], # bucket names
    'avg': [2.5, 12.5, 40, 150, 240], # values of representative points
    'min': [0, 5, 20, 60, 240], # lower bound points
    'exp_hour': [2.5, 12.5, 40, 60] # values for calculation of hourly exposure
}

# no. of income quantiles for analysis
INC_NBINS = 5

# demographics considered for social vulnerability
VUL_VARS = ['frac_'+x for x in
            ['poor', 'low_edu', 'old', 'female', 'black', 'transit']]

# consistent colors & colormaps for analysis
COLORS = {
    'vul': 'tomato', # for vulnerable neighborhoods
    'nonvul': 'limegreen', # for non-vulnerable neighborhoods
    # the automatic colormap does not yield clearly distinguishable colors
    # so this is to explicitly provide readable colors
    'income_classes5': ['tomato', 'goldenrod', 'yellowgreen',
                        'limegreen', 'mediumseagreen'],
    'income_classes6': ['tomato', 'orange', 'goldenrod', 'yellowgreen',
                        'limegreen', 'mediumseagreen'],
}
CMAPS = {
    'cities': 'husl', # for cities
    'industries': 'husl', # for industries (NAICS)
    'income_classes': 'summer_r', # for income groups
    'dwell_bins': 'plasma_r', # the 4 or 5 dwell-time buckets
}

# NAICS codes of important industries to be analyzed in the study
IMP_NAICS = (
    pd.DataFrame.from_dict({
        # key = NAICs code, value = [category name, official NAICS name]
        445110: ['Supermarkets',        'Supermarkets and Other Grocery (except Convenience) Stores'],
        447110: ['Gas stations',        'Gasoline Stations with Convenience Stores'],
        531120: ['Malls',               'Lessors of Nonresidential Buildings (except Miniwarehouses)'],
        611110: ['Schools',             'Elementary and Secondary Schools'],
        622110: ['Hospitals',           'General Medical and Surgical Hospitals'],
        624410: ['Daycare centers',     'Child Day Care Services'],
        # 712190: ['Nature parks',        'Nature Parks and Other Similar Institutions'],
        713940: ['Fitness centers',     'Fitness and Recreational Sports Centers'],
        721110: ['Hotels/Motels',       'Hotels (except Casino Hotels) and Motels'],
        722410: ['Bars/Pubs',           'Drinking Places (Alcoholic Beverages)'],
        722511: ['Full Restaurants',    'Full-Service Restaurants'],
        722513: ['Fast food/Takeout',   'Limited-Service Restaurants'],
        722515: ['Coffee/Snack places', 'Snack and Nonalcoholic Beverage Bars'],
    }, orient='index')
    .rename(columns={0: 'category', 1: 'description'})
    .rename_axis('naics')
    .sort_values('category')
    .assign(color = lambda x: sns.color_palette(
        CMAPS['industries'], x.shape[0]).as_hex())
)

#%% CITY CLASS ----------------------------------------------------------------

class City:
    """
    City class that contains all of the data about a city. Natively, it only
    contains info about the input data (that comes from the input JSON file),
    but it is used to organize all the heavy data for each city.
    """
    def __init__(self, key, dict_):
        self.key = key  # key in the cities dictionary
        self.name_ = dict_['name']
        self.name = self.name_.replace('_', ' ').title()
        self.dir = IO['city_root'] + '/' + self.name_
        self.counties = dict_['counties']
        self.events = dict_['events']

    def __repr__(self):
        return f'<City:{self.name}>'


def load_pois(city):
    """
    Static information of the city's POIs.
    """
    return (pd.read_pickle(city.dir + '/places.pickle')
            .rename(columns={'zip_code': 'zip', 'poi_cbg': 'cbg'})
            .assign(cnty = lambda x: x['cbg'] // 10000000)
            .set_index('poi_id'))

def load_shp_cbg(city):
    """
    Shapefile containing info of census block groups (CBGS).
    """
    return (gp.read_file(f'{city.dir}/shapefile/{city.name_}_CBG.shp')
            .rename(columns=lambda x: x.lower())
            .astype({'geoid': np.int64})
            .query('aland > 0'))

def load_shp_cnty(city):
    """
    Shapefile containing the county borders & info.
    """
    return gp.read_file(f'{city.dir}/shapefile/{city.name_}_cnty.shp')

def load_acs(city):
    """
    Relevant attributes of the census data, converted for better use.
    """
    x = pd.read_pickle(city.dir + '/census.pickle').set_index('cbg')
    x['tot_pop'] = x['sex_f']+x['sex_m']
    x['avg_hh_income'] = x['tot_hh_income']/x['tot_hh']
    x['frac_poor'] = x['hh_poor']/(x['hh_poor'] + x['hh_nonpoor'])
    x['frac_low_edu'] = 1 - x['tot_bachelors']/x['pop_age_over25']
    x['frac_old'] = x['pop_over65']/x['tot_pop']
    x['frac_black'] = x['race_black']/x['tot_pop']
    x['frac_female'] = x['sex_f']/x['tot_pop']
    x['frac_transit'] = ((x['cm_bus']+x['cm_subway']) /
                         x.loc[:, x.columns.str.startswith('cm_')].sum(1))
    x = x[['tot_pop', 'tot_hh', 'tot_workers', 'tot_income', 'avg_income',
            'tot_hh_income', 'avg_hh_income', 'med_hh_income'] +
          [y for y in x.columns if y.startswith('frac_')]]
    return x

def load_rt(city):
    """
    Rt and cases data at the county level.
    """
    return (pd.read_csv(city.dir + '/rt.csv')
            .assign(cnty = lambda x: x['state'] * 1000 + x['cnty'],
                    date = lambda x: str2date(x['date']))
            .drop(columns=['state']))

def load_pat(city, pat_vars=['vis_daily', 'vis_hourly', 'dwells']):
    """
    Load the weekly POI patterns data and pop the heavy columns of
    daily visits, hourly visits, and weekly visits by dwell time buckets.
    @param city: target city object
    @param pat_vars: list of additional variables that are to be processed &
    returned - these include matrix-type heavy columns like daily & hourly
    visits
    """
    pat = (pd.read_pickle(city.dir + '/patterns_' +
                          dateRange2str(WEEKS) + '.pickle')
           .astype({'state': int, 'cnty': int})
           .assign(cnty=lambda x: x['state'] * 1000 + x['cnty'])
           .drop(columns=['state', 'dist_home'])
           .rename({'date': 'week', 'index': 'row_id',
                    'raw_visit_counts': 'visits', 'cbg': 'poi_cbg',
                    'raw_visitor_counts': 'visitors',
                    'median_dwell': 'med_dwell'}, axis=1)
           .query('week > 200000')
           .astype({'cnty': np.int32, 'row_id': np.int32}))
    # also add POI info
    if not hasattr(city, 'pois'):
        city.pois = load_pois(city)
    pat = (pat.merge(city.pois[['naics', 'zip']], on='poi_id')
           .astype({'naics': np.int32, 'poi_id': np.int32}))

    # prepare the output (result) dictionary
    res = {'pat': pat}
    # separate the heavy columns and convert them to matrices
    daily = pat.pop('visits_daily').values
    if 'vis_daily' in pat_vars:
        res['vis_daily'] = pd.DataFrame(np.stack(daily))
    hourly = pat.pop('visits_hourly').values
    if 'vis_hourly' in pat_vars:
        res['vis_hourly'] = pd.DataFrame(np.stack(hourly))
    dwells = pat.pop('dwell_bins').values
    if 'dwells' in pat_vars:
        res['dwells'] = pd.DataFrame(np.stack(dwells),
                                     columns=DWELL_BINS['names'])
    return res

def load_pat_od(city):
    """
    Weekly POI patterns OD table mapping visitors from home CBG to POI row
    index for a given week (in the `pat` table).
    """
    return (pd.read_pickle(city.dir + '/patterns_od_{}.pickle'
                           .format(dateRange2str(WEEKS)))
            .drop(columns=['state', 'cnty'])
            .query('date > 200000')
            .rename(columns={'pat_row_id': 'row_id', 'date': 'week',
                             'home_cbg': 'cbg'})
            .astype({'row_id': np.int32}))

def load_od_zip(city):
    """
    Weekly POI patterns OD table aggregated by zip code of home CBG.
    """
    if hasattr(city, 'pat_od'):
        pat_od = city.pat_od
    else:
        pat_od = load_pat_od(city)
    return (pat_od
            .assign(zip = lambda x: map_cbg_zip(x['cbg'], how='left'
                                                )['zip'].values)
            .groupby(['row_id', 'week', 'zip'])
            ['visitors'].sum()
            .reset_index()
            .astype(np.int32))

def load_social_dist(city):
    """
    Daily home CBG social distancing metrics (time & % time spent home).
    """
    try:
        df = (pd.read_pickle(city.dir + '/model_data_daily.pickle')
              [['nDevices', 'med_time_home', 'prop_at_home']]
              .reset_index()
              .rename(columns={'nDevices': 'tot_dev',
                               'med_time_home': 'time_home'}))
        df['dev_home'] = df['prop_at_home']*df['tot_dev']
        df = df.drop(columns=['prop_at_home'])
    except FileNotFoundError:
        df = pd.read_pickle(city.dir + '/social_dist_{}.pickle'
                            .format(dateRange2str(DATES)))
        df = (df[['date', 'orig_cbg', 'nDev_total', 'nDev_home', 'med_time_home']]
              .rename(columns={'orig_cbg': 'cbg', 'nDev_total': 'tot_dev',
                               'nDev_home': 'dev_home',
                               'med_time_home': 'time_home'}))
        df['date'] = int2date(df['date'])
    df['time_home'] = df['time_home']/60
    df = (df.set_index(['cbg', 'date'])
          [['tot_dev', 'dev_home', 'time_home']].dropna()
          .astype({'dev_home': np.uint16}))
    return df

def load_exposure(city, exp_vars=['cei']):
    """
    POI-weekly table containing exposure metrics.
    """
    return (pd.read_pickle(city.dir + '/exposure.pickle')
            .reset_index()
            .assign(date = lambda x: date2int(x['date']))
            .query('date > 200000')
            [['date', 'poi_id', 'visits'] + exp_vars]
            .rename(columns={'visits': 'exp_visits'})
            .astype({**{'date': np.int32, 'poi_id': np.int32},
                     **{x: np.float32 for x in exp_vars}})
            .set_index(['date', 'poi_id']))

# load the data of each city
def load_city_data(city, exclude=['od_zip'],
                   pat_vars=[], exp_vars=['cei']):
    """
    Load the pickled data of the given city, excluding some tables if
    explicitly provided.
    @param city: target city object
    @param exp_vars: list of exposure metrics - should be one of ['cei',
    'pet', 'rps']
    @param exclude: list of attributes that are not to be processed & stored
    @param pat_vars: matrix-type, heavy columns in the weekly POI
    patterns table that need additional effort to process
    """
    # CBG shapefile
    if not 'shp_cbg' in exclude:
        city.shp_cbg = load_shp_cbg(city)
    # county shapefile
    if not 'shp_cnty' in exclude:
        city.shp_cnty = load_shp_cnty(city)
    # POI info
    if not 'pois' in exclude:
        city.pois = load_pois(city)
    # Rt & cases data
    if not 'rt' in exclude:
        city.rt = load_rt(city)
    # relevant census properties of CBGs and format it
    if not 'acs' in exclude:
        city.acs = load_acs(city)
    # weekly patterns data but do not include daily and hourly visits
    if not 'pat' in exclude:
        pat_dict = load_pat(city, pat_vars)
        for name, value in pat_dict.items():
            setattr(city, name, value)
    # read patterns OD matrix & aggregate the home CBGs into home zips
    # since all further analysis will be done at home zip level
    if not 'od_zip' in exclude:
        city.od_zip = load_od_zip(city)
    # social distancing metrics
    if not 'sd' in exclude:
        city.sd = load_social_dist(city)
    # daily exposure data
    if not 'exp' in exclude:
        city.exp = load_exposure(city, exp_vars)


#%% HELPER FUNCTIONS ----------------------------------------------------------

def peek(df, memory=True, top=3):
    """
    Get a quick overview of a pandas dataframe. Similar to `head()`
    but provides more information.
    """
    info = 'Shape: ' + str(df.shape)
    if memory:
        memory_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)
        info += f', Memory: {memory_mb:.3f} MB'
    print(info)
    return df.head(top)

def wtd_avg(df, val, wt):
    """
    Weighted average of two columns of a pandas dataframe.
    """
    return np.average(df[val], weights=df[wt])

def weekly_avg(series):
    """
    Get running weekly average of a daily time pandas series.
    """
    index = series.index - series.index.weekday * np.timedelta64(1, 'D')
    weeks = (pd.Series(series.values, index=index)
             .rename(series.name)
             .rename_axis('week'))
    week_avg = weeks.groupby('week').mean()
    return week_avg

def roll_avg(series, win=7, fwd_shift=True):
    """
    Shorthand for rolling mean with a window size, optionally forward shifted
    so that NaN are not generated in the beginning of the series but at end.
    """
    res = series.rolling(win).mean()
    if fwd_shift:
        res = res.shift(-win)
    return res

def str2date(date_str, fmt='%Y-%m-%d'):
    """
    Shorthand for converting a string to pandas date.
    """
    return pd.to_datetime(date_str, format=fmt)

def int2date(date_int, fmt='%y%m%d'):
    """
    Shorthand for converting an integer to pandas date.
    """
    if isinstance(date_int, int):
        return pd.to_datetime(str(date_int), format=fmt)
    if isinstance(date_int, pd.Series):
        return pd.to_datetime(date_int.astype(str), format=fmt)

def date2int(dates, fmt='%y%m%d'):
    """
    Convert date back to integer.
    """
    if fmt == '%y%m%d':
        return (dates.dt.year-2000)*10000 + dates.dt.month*100 + dates.dt.day
    else:
        return dates.strftime(fmt).astype(int)
    
def strdate2int(date_str):
    """
    Shorthand for converting a single '%Y-%m-%d' date string to '%y%m%d' int
    """
    return int(date_str[2:].replace('-', ''))

def dateRange2str(x):
    """
    Get the first & last dates and concatenate as string.
    """
    return x[0].strftime('%Y-%m-%d') + '_' + x[-1].strftime('%Y-%m-%d')

def get_week(dates, starts='monday'):
    """
    Get the date of the first weekday of a given daily datetime series.
    """
    if starts == 'monday':
        return dates - dates.dt.weekday * np.timedelta64(1, 'D')
    elif starts == 'sunday':
        return dates - dates.dt.weekday * np.timedelta64(2, 'D')

def range_norm(series):
    """
    Range normalize a series.
    """
    return (series - series.min()) / (series.max() - series.min())

def rationalize_baseline(series, baseline=BASELINE):
    """
    Divide a time series by its mean before a given date.
    """
    return series / series[series.index < str2date(baseline)].mean()

def remove_outliers(series, thresh=0.975):
    """
    Remove outliers above an upper bound quantile.
    """
    return series[series <= series.quantile(thresh)]

def plot_event(events, ax=None, show_labels=True, va='top',
               linecolor='silver', linestyle='-', labelcolor='black'):
    """
    Draw a vertical line on a time series plot for a given list of events.
    """
    fig = plt.gcf()
    if ax is None:
        ax = plt.gca()
    ylim = ax.get_ylim()
    ypos = ''
    if va == 'top':
        ypos = ylim[1] - 0.01 * (ylim[1] - ylim[0])
    elif va == 'bottom':
        ypos = ylim[0] + 0.01 * (ylim[1] - ylim[0])
    for name, date_str in events.items():
        date = pd.to_datetime(date_str)
        ax.axvline(date, color=linecolor, linestyle=linestyle)
        if show_labels:
            ax.text(date + pd.Timedelta(days=1), ypos, f'{name} [{date_str[5:]}]',
                    color=labelcolor, va=va, rotation=90)
    return fig


#%% LOAD & PROCESS COMMON DATASETS --------------------------------------------

def load_cities(exclude=['nym']):
    """
    Create the city objects for all cities without loading their heavy data.
    @param exclude: list of city keys which have to be excluded
    """
    cities = {}
    with open(IO['city_info'], 'r') as f:
        city_dict = json.load(f)
        for k in sorted(city_dict):
            # exclude New York metro city object (obsolete region)
            if not k in exclude:
                c = City(k, city_dict[k])
                cities[k] = c
    return cities

# noinspection PyRedeclaration
def load_all_pois():
    """
    Load the big table containing the relevant information about all of the
    POIs in the SafeGraph dataset, along with the artificially created POI IDs.
    """
    return (pd.read_csv(IO['pois'])
            [['poi_id', 'location_name', 'street_address', 'city',
              'postal_code', 'latitude', 'longitude', 'parent_poi_id']]
            .rename(columns={'postal_code': 'zip'})
            .astype({'poi_id': np.int32, 'zip': np.int32}))

def load_all_zips():
    """
    Load the mapping between ZIP codes and census tract codes for the U.S.
    """
    return (pd.read_csv(IO['zip2tract'])
            .rename(columns=lambda x: x.lower())
            .rename(columns={'zcta5': 'zip'})
            [['zip', 'state', 'county', 'geoid', 'zpop', 'zarealand']]
            .astype({'zip': np.int32, 'zpop': np.int32}))

def load_all_naics():
    """
    Load the table that contains all the NAICS codes along with their
    industry names & description.
    """
    return (pd.read_csv(IO['naics'], encoding='latin')
            .pipe(lambda x: x[x['code'].apply(lambda y: y.isnumeric())])
            .astype({'code': np.int32})
            .rename(columns={'code': 'naics', 'title': 'naics_title'})
            [['naics', 'naics_title']])

def map_cbg_zip(cbgs, zips=None, how='inner'):
    """
    Given a series of CBG ids, get their corresponding zip codes.
    """
    # load the ZIP to tract mapping if not already given
    if zips is None:
        zips = load_all_zips()
    # get the mapping between CBG & tracts
    cbg2tract = pd.DataFrame(cbgs).assign(tract = lambda x: x['cbg']//10)
    # get the mapping between zip codes & tracts, removing duplicate
    # assignment of tract to zip
    zip2tract = (zips[['zip', 'geoid']]
                 .rename(columns={'geoid': 'tract'})
                 .drop_duplicates(subset=['tract']))
    # join them
    res = pd.merge(cbg2tract, zip2tract, on='tract', how=how).drop(columns=['tract'])
    return res

def get_inc_classes(incomes, bins=[], quantile=INC_NBINS):
    """
    Divide the given series of income into classes by either a given quantile
    or explicitly provided bins.
    """
    incomes = pd.Series(incomes, name='income_bin')
    if quantile is not None:
        return pd.qcut(incomes, quantile)
    elif len(bins) != 0:
        return pd.cut(incomes, bins)
    else:
        return None


#%% MAIN ----------------------------------------------------------------------
if __name__ == '__main__':
    cities = load_cities()
    chi = cities['chi']
    load_city_data(chi)