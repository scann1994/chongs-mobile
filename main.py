"""`main` is the top level module for your Flask application."""

# Mobile Byte Version 1
# 
# Copyright 1/2016 Jennifer Mankoff
#
# Licensed under GPL v3 (http://www.gnu.org/licenses/gpl.html)
#

# Imports
import os
import jinja2
import webapp2
import logging
import json
import urllib
import MySQLdb
import math
import pygal

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# Define your production Cloud SQL instance information.
_INSTANCE_NAME = 'chongs-mobile:chongs-mobile-date'
_DB_NAME = 'data' # or whatever name you choose
_USER = 'root'


# the table where activities are logged
_ACTIVITY = 'locations'
# the table where locations are logged
_LOCATIONS = 'locations'
# the distance that determins new locations
_EPSILON = 1

if (os.getenv('SERVER_SOFTWARE') and
    os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    _DB = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME,
                          db=_DB_NAME,
                          user=_USER,
                          passwd='1234',
                          charset='utf8')
else:
    _DB = MySQLdb.connect(host='127.0.0.1',
                          port=3306,
                          db=_DB_NAME,
                          user=_USER,
                          passwd='1234',
                          charset='utf8')

    # Alternatively, connect to a Google Cloud SQL instance using:
    # _DB = MySQLdb.connect(host='ip-address-of-google-cloud-sql-instance', port=3306, user=_USER, charset='utf8')

# Import the Flask Framework
from flask import Flask, request
from flask import render_template
app = Flask(__name__)

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

@app.route('/')
def index():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    cursor = _DB.cursor()
    cursor.execute('SHOW TABLES')
    
    if (os.getenv('SERVER_SOFTWARE') and
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
        db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME,
                             db=_DB_NAME, user=_USER, passwd='1234', charset='utf8')
        cursor = db.cursor()
        
        logging.info("making queries")
        
        # some sample queries that will write examples of the sort of
        # data we have collected to the log so you can get a sense of things
        make_and_print_query(cursor, 'SHOW TABLES', 'Show the names of all tables')
        make_and_print_query(cursor, "SELECT * FROM plugin_google_activity_recognition WHERE LIMIT 10 ", 'Example contents of plugin_google_activity_recognition')
        make_and_print_query(cursor, "SELECT * FROM locations  LIMIT 10", 'Example contents of locations')
        
        
        # this query collects information about the number
        # of log enteries for each day. 
        day = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')"
        query = "SELECT {0} as day_with_data, count(*) as records FROM {1} GROUP by day_with_data".format(day, _LOCATIONS)
        
        rows = make_query(cursor, query)
        queries = [{"query": query, "results": rows}]
        
        # this query lets us collect information about 
        # locations that are visited so we can bin them. 
        query = "SELECT double_latitude, double_longitude FROM {0} ".format(_LOCATIONS)
        locations = make_query(cursor, query)
        #locations = make_and_print_query(cursor, query, "locatons")
        bins = bin_locations(locations, _EPSILON)
        for location in bins:
            queries = queries + [{"query": query, "results": bins}]
            
        # now get locations organized by day and hour 
        time_of_day = "FROM_UNIXTIME(timestamp/1000,'%H')"
        day = "FROM_UNIXTIME(timestamp/1000,'%Y-%m-%d')"
        query = "SELECT {0} as day, {1} as time_of_day, double_latitude, double_longitude FROM {2} GROUP BY day, time_of_day".format(day, time_of_day, _LOCATIONS)
        locations = make_query(cursor, query)
        
        # and get physical activity per day and hour
        # activity name and duration in seconds
        day_and_time_of_day = "FROM_UNIXTIME(timestamp/100, '%Y-%m-%d %H')"
        query = "SELECT {0} as day, {1} as time_of_day, activity_name FROM {2} GROUP BY day, activity_name, {3}".format(day, time_of_day, _ACTIVITY, day_and_time_of_day)
            
        activities = make_query(cursor, query)
            
        # now we want to associate activities with locations. This will update the
        # bins list with activities.
        group_activities_by_location(bins, locations, activities, _EPSILON)
            
    else:
        queries = [{"query": 'Need to connect from Google Appspot', "results": []}]

    logging.info(queries)
    
    context = {"queries": queries}
    
    return template.render(context)

@app.route("/bat.svg")
def mysvg():
		
		gauge = pygal.SolidGauge(half_pie=True, inner_radius=0.70,
   								 style=pygal.style.styles['default'](value_font_size=10))
		gauge.title = 'Battery Level Charged For Each Day of a Week'
		percent_formatter = lambda x: '{:.10g}%'.format(x)
		gauge.value_formatter = percent_formatter

		gauge.add('Monday', [
        	{'value': 42, 'max_value': 100},
        	{'value': 30, 'max_value': 100}])
		gauge.add('Tuesday', [
        	{'value': 16, 'max_value': 100},
        	{'value': 59, 'max_value': 100}])
		gauge.add('Wednesday', [
        	{'value': 54, 'max_value': 100}])
		gauge.add('Thursday', [
        	{'value': 34, 'max_value': 100},
        	{'value': 60, 'max_value': 100}])
		gauge.add('Friday', [
        	{'value': 60, 'max_value': 100}])
		gauge.add('Saturday', [
        	{'value': 75, 'max_value': 100}])
		gauge.add('Sunday', [
        	{'value': 3, 'max_value': 100},
        	{'value': 4, 'max_value': 100},
        	{'value': 86, 'max_value': 100}])
		
		return gauge.render_response()


@app.route("/bathr.svg")
def bathr():
		
		gauge2 = pygal.SolidGauge(half_pie=True, inner_radius=0.70,
    							style=pygal.style.styles['default'](value_font_size=10))
		gauge2.title = 'Battery Charging Time For Each Day of a Week'
		hour_formatter = lambda x: '{:.10g}hr'.format(x)
		gauge2.value_formatter = hour_formatter

		gauge2.add('Monday', [
		        {'value': 1.9, 'max_value': 24}])
		gauge2.add('Tuesday', [
		        {'value': 7.8, 'max_value': 24}])
		gauge2.add('Wednesday', [
		        {'value': 8.6, 'max_value': 24}])
		gauge2.add('Thursday', [
		        {'value': 2.4, 'max_value': 24}])
		gauge2.add('Friday', [
		        {'value': 8.0, 'max_value': 24}])
		gauge2.add('Saturday', [
		        {'value': 11.2, 'max_value': 24}])
		gauge2.add('Sunday', [
		        {'value': 8.5, 'max_value': 24}])
		
		return gauge2.render_response()


@app.route('/batscr.svg')
def batscr():
	batscr = pygal.Bar()
	batscr.title = 'Hourly Average Battery Level and Screen Status(Locked/Unlocked) of 2/6/2017'
	batscr.x_labels = map(str, range(0, 24))
	batscr.add('Average Battery', [52.93684210526316,
	 52.517241379310342,
	 47.995670995670999,
	 50.696606786427147,
	 51.205944798301488,
	 59.546875,
	 77.633528265107216,
	 84.459459459459453,
	 86.114754098360649,
	 85.387811634349035,
	 85.083798882681563,
	 84.726256983240219,
	 84.377094972067042,
	 83.079452054794515,
	 80.891705069124427,
	 75.320276497695858,
	 72.471783295711063,
	 69.613483146067409,
	 65.317567567567565,
	 60.916473317865432,
	 60.519348268839103,
	 61.88247863247863,
	 59.578616352201259,
	 56.74285714285714])
	batscr.add('Locked Screen %',  [54.6875,
	 52.173913043478258,
	 50.0,
	 50.0,
	 51.428571428571423,
	 51.282051282051277,
	 50.0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 45.0,
	 47.058823529411761,
	 52.173913043478258,
	 52.380952380952387,
	 50.0,
	 43.75,
	 54.054054054054056,
	 50.0,
	 48.387096774193552,
	 47.368421052631575,
	 55.102040816326522])
	batscr.add('Unlocked Screen %', [45.3125,
	 47.826086956521742,
	 50.0,
	 50.0,
	 48.571428571428569,
	 48.717948717948715,
	 50.0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 55.000000000000007,
	 52.941176470588239,
	 47.826086956521742,
	 47.619047619047613,
	 50.0,
	 56.25,
	 45.945945945945951,
	 50.0,
	 51.612903225806448,
	 52.631578947368418,
	 44.897959183673471])
	return batscr.render_response()

@app.route('/batscr1.svg')
def batscr1():
	batscr1 = pygal.Bar()
	batscr1.title = 'Hourly Average Battery Level and Screen Status of 2/7/2017 (Tue)'
	batscr1.x_labels = map(str, range(0, 24))
	batscr1.add('Average Battery', [52.93684210526316,
	 52.517241379310342,
	 47.995670995670999,
	 50.696606786427147,
	 51.205944798301488,
	 59.546875,
	 77.633528265107216,
	 84.459459459459453,
	 86.114754098360649,
	 85.387811634349035,
	 85.083798882681563,
	 84.726256983240219,
	 84.377094972067042,
	 83.079452054794515,
	 80.891705069124427,
	 75.320276497695858,
	 72.471783295711063,
	 69.613483146067409,
	 65.317567567567565,
	 60.916473317865432,
	 60.519348268839103,
	 61.88247863247863,
	 59.578616352201259,
	 56.74285714285714])
	batscr1.add('Off Screen %', [54.6875,
	 52.173913043478258,
	 50.0,
	 50.0,
	 51.428571428571423,
	 51.282051282051277,
	 50.0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 45.0,
	 47.058823529411761,
	 52.173913043478258,
	 52.380952380952387,
	 50.0,
	 43.75,
	 54.054054054054056,
	 50.0,
	 48.387096774193552,
	 47.368421052631575,
	 55.102040816326522])
	batscr1.add('On Screen %', [45.3125,
	 47.826086956521742,
	 50.0,
	 50.0,
	 48.571428571428569,
	 48.717948717948715,
	 50.0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 0,
	 55.000000000000007,
	 52.941176470588239,
	 47.826086956521742,
	 47.619047619047613,
	 50.0,
	 56.25,
	 45.945945945945951,
	 50.0,
	 51.612903225806448,
	 52.631578947368418,
	 44.897959183673471])
	return batscr1.render_response()


@app.route('/graphing')
def pygalexample():
	try:
		logging.info('called!')
		template = JINJA_ENVIRONMENT.get_template('templates/graphing.html')
		return template.render()
		#return graph.render_response()
	except Exception, e:
		return(str(e))
		

    
@app.route('/about')
def about():
    template = JINJA_ENVIRONMENT.get_template('templates/about.html')
    return template.render()

@app.route('/analysis')
def analysis():
    template = JINJA_ENVIRONMENT.get_template('templates/analysis.html')
    return template.render()

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404

@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500

# Takes the database link and the query as input
def make_query(cursor, query):
    # this is for debugging -- comment it out for speed
    # once everything is working

    try:
        # try to run the query
        cursor.execute(query)
        # and return the results
        return cursor.fetchall()
    
    except Exception:
        # if the query failed, log that fact
        logging.info("query making failed")
        logging.info(query)

        # finally, return an empty list of rows 
        return []

# helper function to make a query and print lots of 
# information about it. 
def make_and_print_query(cursor, query, description):
    logging.info(description)
    logging.info(query)
    
    rows = make_query(cursor, query)
        
def bin_locations(locations, epsilon):
    # always add the first location to the bin
    bins = {1: [locations[0][0], locations[0][1]]}
    # this gives us the current maximum key used in our dictionary
    num_places = 1
    
    # now loop through all the locations 
    for location in locations:
        lat = location[0]
        lon = location[1]
        # assume that our current location is new for now (hasn't been found yet)
        place_found = False
        # loop through the bins 
        for place in bins.values():
            # check whether the distance is smaller than epsilon
            if distance_on_unit_sphere(lat, lon, place[0], place[1]) < epsilon:
                #(lat, lon) is near  (place[0], place[1]), so we can stop looping
                place_found = True
                    
        # we weren't near any of the places already in bins
        if place_found is False:
            logging.info("new place: {0}, {1}".format(lat, lon))
            # increment the number of places found and create a new entry in the 
            # dictionary for this place. Store the lat lon for comparison in the 
            # next round of the loop
            num_places = num_places + 1
            bins[num_places] = [lat, lon]

    return bins.values()
            
def find_bin(bins, lat, lon, epsilon):
    for i in range(len(bins)):
        blat = bins[i][0]
        blon = bins[i][1]
        if distance_on_unit_sphere(lat, lon, blat, blon) < epsilon:
            return i
    bins.append([lat, lon])
    return len(bins)-1

def group_activities_by_location(bins, locations, activities, epsilon):
    searchable_locations = {}
    for location in locations:
        # day, hour
        key = (location[0], location[1])
        if key in searchable_locations:
            # lat,   lon 
            searchable_locations[key] = locations[key] + [(location[2], location[3])]
        else:
            searchable_locations[key] = [(location[2], location[3])]
    
    # a place to store activities for which we couldn't find a location
    # (indicates an error in either our data or algorithm)
    no_loc = []
    for activity in activities:
        # collect the information we will need 
        aday = activity[0] # day
        ahour = activity[1] # hour
        aname = activity[2] # name
        logging.info(aday + aname)
        try: 
            possible_locations = searchable_locations[(aday, ahour)]
            # loop through the locations
            for location in possible_locations:
                logging.info(" about to find bin")
                bin = find_bin(bins, location[0], location[1], epsilon)
                # and add the information to it
                bins[bin] = bins[bin] + [aname]
        except KeyError:
            no_loc.append([aname])

    # add no_loc to the bins
    bins.append(no_loc)
    # this function is taken verbatim from http://www.johndcook.com/python_longitude_latitude.html

def distance_on_unit_sphere(lat1, long1, lat2, long2):

    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
    
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
    
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
    
    # Compute spherical distance from spherical coordinates.
    
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
        
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    # sometimes small errors add up, and acos will fail if cos > 1
    if cos>1: cos = 1
    arc = math.acos( cos )
    
    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc
