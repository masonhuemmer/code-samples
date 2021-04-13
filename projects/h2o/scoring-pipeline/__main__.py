#!/usr/bin/env python3
# -------------------------------------------------------------------------------
# Name: __main__.py
# Purpose: Housing Model Api
# Version: 2.0
# Date: Jun 18, 2020
# Author: Mason Huemmer
# -------------------------------------------------------------------------------

# -------------------------------------------------------------------------------
# Library Imports
# -------------------------------------------------------------------------------
from flask import Flask
from flask_restx import Api, Resource, fields
from influxdb import InfluxDBClient
from app import helper
import logging.config
import argparse
import logging
import time
import json
import sys
import os

# -------------------------------------------------------------------------------
# Environment Variables
# -------------------------------------------------------------------------------
# host          = os.environ['INFLUXDB_HOST']
# port          = os.environ['INFLUXDB_PORT']
# database      = os.environ['INFLUXDB_DATABASE']
# username      = os.environ['INFLUXDB_USERNAME']
# password      = os.environ['INFLUXDB_PASSWORD']
# driverless_ai = os.environ['DRIVERLESS_AI_LICENSE_KEY']

# -------------------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------------------
class _ExcludeErrorsFilter(logging.Filter):
    def filter(self, record):
        """Filters out log messages with log level ERROR (numeric value: 40) or higher."""
        return record.levelno < 40

config = {
    'version': 1,
    'filters': {
        'exclude_errors': {
            '()': _ExcludeErrorsFilter
        }
    },
    'formatters': {
        # Modify log message format here or replace with your custom formatter class
        'main_formatter': {
            'format': '(%(process)d) %(asctime)s %(name)s (line %(lineno)s) | %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console_stderr': {
            # Sends log messages with log level ERROR or higher to stderr
            'class': 'logging.StreamHandler',
            'level': 'ERROR',
            'formatter': 'main_formatter',
            'stream': sys.stderr
        },
        'console_stdout': {
            # Sends log messages with log level lower than ERROR to stdout
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'main_formatter',
            'filters': [ 'exclude_errors' ],
            'stream': sys.stdout
        }
    },
    'root': {
        # In general, this should be kept at 'NOTSET'.
        # Otherwise it would interfere with the log levels set for each handler.
        'level': 'NOTSET',
        'handlers': ['console_stderr', 'console_stdout']
    },
}

logging.config.dictConfig(config)
logger = logging.getLogger('main')

# -------------------------------------------------------------------------------
# Initialize Flask
# -------------------------------------------------------------------------------
app = Flask("Housing Model")
api = Api(app)

# -------------------------------------------------------------------------------
# API Methods
# - GET:  Ping
# - POST: Score 
# -------------------------------------------------------------------------------

# -------------------------------------------------------------------------------
# GET Method: Ping 
# -------------------------------------------------------------------------------
@api.route('/ping', methods=['GET'])
class Ping(Resource):
    def get(self):
        ping = {"status":"Connection Successful"}
        return json.dumps(ping)

# -------------------------------------------------------------------------------
# Model Input / Output for API Decorators
# -------------------------------------------------------------------------------
model_input = api.model(
    'housing_model_input', 
    {
        'BOROUGH' : fields.Integer,
        'NEIGHBORHOOD' : fields.String(),
        'BUILDING_CLASS_CATEGORY': fields.String(),
        'COMMERCIAL_UNITS': fields.Integer,
        'TOTAL_UNITS': fields.Integer,
        'LAND_SQUARE_FEET': fields.Integer,
        'GROSS_SQUARE_FEET': fields.Integer,
        'YEAR_BUILT': fields.Integer,
        'BUILDING_CLASS_AT_TIME_OF_SALE': fields.String()
    }
)

model_output = api.model (
    'housing_model_output',
    {
        "SALE PRICE" : fields.List(fields.Float)
    }
)

# -------------------------------------------------------------------------------
# POST Method: Score
# -------------------------------------------------------------------------------
@api.route('/score')
class Model(Resource):
    @api.expect(model_input)
    @api.marshal_with(model_output)
    def post(self):

        # -------------------------------------------------------------------------------
        # Initialize Variables
        # -------------------------------------------------------------------------------
        influx_measurement = 'sale_prices'

        # -------------------------------------------------------------------------------
        # Connect to InfluxDB
        # -------------------------------------------------------------------------------
        client = InfluxDBClient(host=host, port=port, username=username, password=password)
        client.create_database(database)

        # -------------------------------------------------------------------------------
        # RETURN MOJO Scores
        # -------------------------------------------------------------------------------
        scores = helper.model_run(api.payload, logger)

        # -------------------------------------------------------------------------------
        # Return Scores Payload
        # -------------------------------------------------------------------------------
        data = helper.create_scores_payload(influx_measurement, scores, api.payload)
     
        # -------------------------------------------------------------------------------
        # Write to InfluxDB
        # -------------------------------------------------------------------------------
        client.write_points(data, database=database, time_precision='ms', protocol='json')        

        # -------------------------------------------------------------------------------
        # Return Scores to Flask API
        # -------------------------------------------------------------------------------
        return scores

# -------------------------------------------------------------------------------
# Console Entry Point
# -------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        app.run(host="0.0.0.0", port=8080)
    except SystemExit as e:
        logger.exception('main failed with exception')
        logger.error(str(e))