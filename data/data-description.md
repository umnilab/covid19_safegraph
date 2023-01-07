**City/Regional Data Description**

# Regions

We have processed the data from different sources and segregated by county. City/metropolitan areas have been conveniently defined as collections of counties so that their data can be quickly aggregated from the counties data files.

The 10 city regions have been defined in ~/Data/regions\_meta.json where each region has the following information:

| Field | Description |
| --- | --- |
| name | Full name of the region, used to define the region&#39;s data directory. |
| counties | List of constituent counties mapped with a 2-tuple of its state and county FIPS codes. For example, NY: Bronx: [36, 5] means that Bronx County, NY has the FIPS code 5, with the FIPS of the state of NY being 5. |
| events | List of relevant COVID-19-related events in the region, along with their dates. This information is gathered from different sources provided on the Wikipedia pages of the different regions, generally with the title template &#39;COVID-19 pandemic in \&lt;region\&gt;&#39;. |
| income\_bins | Arbitrarily created median household income buckets for some cities to group the CBGs into different income classes; they are different for different cities because of the difference in their purchasing powers and standards of living. |

## Shapefile

The shapefile of the region is created by simply filtering the counties of the region in the state&#39;s shapefile that is available for [download](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2019&amp;layergroup=Block+Groups) from census.gov. Each row in the attributes table is a CBG with other columns just components of its CBG FIPS code.

# Schema

The data tables are stored as binary files (.pickle) that are easy to load in Python than .csv or .txt formats. The pickle library uses [protocol 5](https://www.python.org/dev/peps/pep-0574/) to store these files which require Python \&gt;3.8x.

## Places

Table containing information of places of interest (POI). See the [original table schema](https://docs.safegraph.com/v4.0/docs#section-core-places).

| Field | DType | Description |
| --- | --- | --- |
| poi\_id | int32 | Unique integer ID of a POI. This is mapped to the original safegraph\_place\_id column. This ID was shrunken to a 32-bit integer from a 35-character string to save some space. The mapping between the original and current IDs is given in ~/Data/poi\_ids.pickle. |
| naics | int32 | 6-digit NAICS code for the classification of the business category. The description of these categories is provided in ~/Data/ 2017\_NAICS\_descriptions.csv. |
| lat, lon | float32 | Latitude and longitude of the centroid of the POI. |
| zip\_code | int32 | ZIP code. |
| poi\_cbg | int64 | FIPS code of the census block group (CBG) of the POI. See the [description](https://www.safegraph.com/blog/beginners-guide-to-census). |
| is\_synthetic | bool | From the SafeGraph [website](https://docs.safegraph.com/v4.0/docs/places-schema#section-geometry), &quot;If true then this is not a precise POI footprint polygon, but instead is an inferred polygon from an accurate centroid, category-based radius, and heuristics like avoiding overlap with roads.&quot; |
| includes\_parking\_lot | object | Whether the POI polygon includes a parking lot. |
| area\_sqft | int64 | Plan area (sq. ft.) of the POI (of the POI&#39;s polygon in the geojson database) |

## Census

This includes the data of selected census features, taken from the American Community Survey (ACS) 2017 data available on [census.gov](https://data.census.gov/cedsci/), for each census block group (CBG) contained in the city&#39;s limits. Note that only a few census fields have been recorded in this dataset. Here is their description:

| Field name in the ACS tables | Field name in the existing census table | Description |
| --- | --- | --- |
| B00001e1 | total\_pop | total population |
| B01001e26 | sex\_f | total female population(?) |
| B01001e2 | sex\_m | total male population(?) |
| B01002e1 | med\_age | overall median age |
| B02001e2 | race\_white | total white population |
| B02001e3 | race\_black | &quot;&quot; black &quot;&quot; |
| B02001e5 | race\_asian | &quot;&quot; Asian &quot;&quot; |
| B08008e1 | tot\_workers | total estimate of workers (aged \&gt;16) |
| B08303e1 | commute\_time | avg commute time of non-WFH workers (aged\&gt;16) |
| B08301e3 | cm\_car\_alone | no. of people who commute by driving alone to work |
| B08301e4 | cm\_pool | &quot;&quot; carpool (total) |
| B08301e18 | cm\_bike | &quot;&quot; commute by bicycle |
| B08301e13 | cm\_subway | &quot;&quot; train/rail transit |
| B08301e11 | cm\_bus | &quot;&quot; bus rapid transit |
| B08301e16 | cm\_taxi | &quot;&quot; taxicab |
| B08301e19 | cm\_walk | &quot;&quot; walk to work |
| B08301e21 | cm\_wfh | &quot;&quot; work from home |
| B15003e1 | pop\_age\_over25 | total population aged \&gt;= 25 |
| B15011e1 | tot\_bachelors | total people having bachelor&#39;s degree or more |
| B16004e2 | pop\_under17 | population aged \&lt;= 17 |
| B16004e24 | pop\_18\_64 | &quot;&quot; aged 18-64 |
| B16004e46 | pop\_over65 | &quot;&quot; aged \&gt;= 65 |
| B17017e1 | hh\_poor | no. of households below poverty level |
| B17017e31 | hh\_nonpoor | no. of households above poverty level |
| B19001e1 | tot\_hh | total no. of households |
| B19313e1 | tot\_income | aggregate income of the households in the CBG |
| B19301e1 | avg\_income | per capita income of the households in the CBG |
| B19025e1 | tot\_hh\_income | aggregate household income |
| B19013e1 | med\_hh\_income | overall median household income |
| B24080e1 | tot\_employed | total employed people (age\&gt;16) |

## Patterns

The [weekly patterns data](https://docs.safegraph.com/v4.0/docs/weekly-patterns) have been collected for the weeks of 30 Dec 2019 (i.e., starting from 30 Dec 2019) through 22 June 2020 (i.e., ending on 28 June 2020). Each row of the patterns table represents the data of a unique combination of POI and week. In SafeGraph&#39;s data, the first day of the week is a Monday.

| Field | DType | Description |
| --- | --- | --- |
| index | int64 | Row ID of the original patterns table, used for joining tables, esp. the homes table. |
| raw\_visit\_counts | int16 | Total no. of visits at this POI in this week. |
| raw\_visitor\_counts | int16 | Total no. of visitors (who may each visit multiple times). |
| visits\_daily | array(int16) | Total daily visits at this POI in this week. They should add up to raw\_visit\_counts. |
| visits\_hourly | array(int16) | 168-size vector showing no. of hourly visits. They should add up to raw\_visit\_counts. |
| cbg | int64 | FIPS code of the CBG where this POI belongs. |
| dist\_home | float32 | Median distance (meters) from homes of the visitors. |
| median\_dwell | float32 | Median dwell time (minutes) of the visitors at the POI. |
| dwell\_bins | array(int16) | 5-size vector denoting the no. of visits within 5 dwell time buckets: [0-5, 5-20, 20-60, 60-240, \&gt;240] min. They should add up to raw\_visit\_counts. |
| poi\_id | int64 | POI ID as mapped in ~/Data/poi\_ids.pickle. |
| date | int32 | Starting date of the week, given in the format yymmdd and stored as integer to save space. |
| state, cnty | int8, int16 | FIPS codes of the state and county; quite redundant (as this info is present in cbg) but stored nonetheless. |

## Patterns OD

This is an extension of the patterns table, derived from a particular column visitor\_home\_cbgs because of its special structure and large size. It can be thought of as an origin-destination (OD) table showing the number of visitors who visit a particular POI from their home CBG in a given week.

| Field | DType | Description |
| --- | --- | --- |
| pat\_row\_id | int32 | Row ID of the patterns table that this POI corresponds to; it should have been substituted by poi\_id but this works as well in joining it with the patterns table. The patterns table contains the cbg of the POI, which is the destination in this case. |
| home\_cbg | int64 | CBG of the home of visitors, thought of as the origin in the OD table. |
| visitors | int16 | Total no. of visitors (not visits). |
| date | int32 | Total daily visits at this POI in this week. They should add up to raw\_visit\_counts. |

## Social Distancing

This daily data shows the aggregate-level social distancing metrics, mostly the number of devices in several cases. Here, each row is a CBG and the metrics are aggregated at the CBG level. Here is SafeGraph&#39;s [documentation](https://docs.safegraph.com/v4.0/docs/social-distancing-metrics) about it.

| Field | DType | Description |
| --- | --- | --- |
| orig\_cbg | int64 | CBG code of the origin. |
| nDev\_total | int16 | Total no. of devices recorded in this day that have home in this CBG. |
| med\_dist | int32 | Daily median distance (meters) traveled by nDev\_total. |
| nDev\_home | int16 | No. of devices recorded completely at home all day. |
| med\_time\_home | int16 | Median dwell time (minutes) at home for all devices in nDev\_total. |
| nDev\_home\_hourly | array(int16) | Hourly count of devices at home. |
| nDev\_part\_time | int16 | No. of devices recorded spending 3-6 hours at one non-home location. |
| nDev\_full\_time | int16 | &quot;&quot; \&gt;6 hours &quot;&quot; |
| nDev\_delivery | int16 | No. of devices that stopped for \&lt;20 minutes at \&gt;3 non-home locations. |
| med\_time\_outside | int16 | Median dwell time (minutes) outside home for all devices in nDev\_total. |
| nDev\_candidate | int16 | No. of devices whose home is in this CBG regardless of mobile phone activity. |
| med\_perc\_time\_home | int8 | Median % time spend at home. |
| dist\_\<bin\> | int16 | No. of devices to have traveled a distance lying in the given bin. Bin boundaries are [0, 1, 2, 8, 16, 50] km. |
| time\_dist\_\<bin\> | int16 | Median dwell time of devices having traveled a distance in the given bucket/bin. Bins are same as above. |
| time\_\<bin\> | int16 | No. of devices that dwelled at home for the given time bucket. Bin boundaries are [0, 1, 6, 9, 18] hours. |
| %time\_\<bin\> | int16 | No. of devices spending a percentage of all day at home lying in the given bin. Bin boundaries are [0, 25, 75, 100] %. Interestingly, it also has a bin for \&gt;100%. |
| date | int32 | Date in the integer format yymmdd. |
| state, cnty | int8, int16 | FIPS codes of the state and county; quite redundant (as this info is present in cbg) but stored nonetheless. |
| row\_id | float64 | Row number of this table used for connecting to the social\_od table. |

## Social OD

Similar to patterns\_od, this table is an extension of the social distancing table, particularly of its column destination\_cbgs. It shows the no. of devices traveling from their home CBG to another CBG in the given day.

| Field | DType | Description |
| --- | --- | --- |
| social\_dist\_row\_id | int32 | Row ID of the social distancing table that this home CBG corresponds to; it should have been substituted by social&#39;s cbg column, but this works as well in joining it with the social distancing table. |
| dest\_cbg | int64 | CBG code of the destination. |
| nDevices | int16 | No. of devices traveling for \&gt;1 minute from home CBG to dest\_cbg. |
| date | int32 | Date in the integer format yymmdd. |
| state, cnty | int8, int16 | Redundant |