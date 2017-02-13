# Imports
import os
import jinja2
import webapp2
import logging

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
    
from flask import Flask
app = Flask(__name__)
app.config['DEBUG'] = True

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.


@app.route('/')
def hello():
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    return template.render()

@app.route('/table')
def table():
    template = JINJA_ENVIRONMENT.get_template('templates/table.html')
    return template.render()

@app.route('/teamInfo')
def teamInfo():
    template = JINJA_ENVIRONMENT.get_template('templates/teamInfo.html')
    return template.render()


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404