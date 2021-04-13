import logging, logging.config, requests, argparse, json, sys, os
from helper import AzureDevOps, _ExcludeErrorsFilter, _RedactingFilter
from urllib.parse import urlparse

# -------------------------------------------------------------------------------
# Parse Arguments
# -------------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='Terraform Cloud API Program')
required = parser.add_argument_group("required arguments")

# REQUIRED ARGUMENTS
required.add_argument( "--organization", help="Azure DevOps Organization", required=True)
required.add_argument( "--project", help="Azure DevOps Team Project", required=True)
required.add_argument( "--vargroup", help="Azure DevOps VarGroup to set Sprint and Version", required=True)
required.add_argument( "--token", help="Azure DevOps API Token", required=True)

# LOGGING LEVELS - https://docs.python.org/3/library/logging.html#logging-levels
parser.add_argument( "-log", "--log", nargs="?", const="INFO", default="WARNING", help="set logging level for program")

args = parser.parse_args()

# ASSIGN ARGUMENTS TO VARIABLES
organization = args.organization
project = args.project
vargroup = args.vargroup
token = args.token
console_log_level = args.log

# -------------------------------------------------------------------------------
# Configure Logger
# -------------------------------------------------------------------------------
config = {
    'version': 1,
    'filters': {
        'exclude_errors': {
            '()': _ExcludeErrorsFilter
        },
        'redact_data':  {
            '()': _RedactingFilter,
            'patterns': {
                '{}'.format(token)
            }
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
            'level': '{}'.format(console_log_level),
            'formatter': 'main_formatter',
            'filters': [ 'exclude_errors', 'redact_data' ],
            'stream': sys.stdout
        },
        "log_file": {
            # Sends all log message to file
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": 'main_formatter',
            "filters": ['redact_data'],
            "maxBytes": 10485760,
            "mode": "a",
            "filename": "/tmp/load_and_run_workspace.log".format(),
            "encoding": "utf-8"
      }
    },
    'root': {
        # In general, this should be kept at 'NOTSET'.
        # Otherwise it would interfere with the log levels set for each handler.
        'level': 'NOTSET',
        'handlers': ['console_stderr', 'console_stdout', 'log_file']
    },
}

logging.config.dictConfig(config)
logger = logging.getLogger('main')

# -------------------------------------------------------------------------------
# Log Global Variables
# -------------------------------------------------------------------------------
logger.info("Organization: {}".format(organization))
logger.info("Project: {}".format(project))
logger.info("Variable Group: {}".format(vargroup))
logger.debug("API Token: {}".format(token))

# -------------------------------------------------------------------------------
# Run MAIN
# -------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        # CREATE CLASS INSTANCE
        ado = AzureDevOps(organization,project,token,logger)
        logger.debug("Instance of Class Created")

        # FIND VARGROUP
        response = ado.get_variable_groups(query="?groupname={}&api-version=6.0-preview.2".format(vargroup))
        for payload in response["value"]:
            
            # SET VARGROUP ID
            vargroup_id = payload["id"]
            logger.info("Variable Group ID: {}".format(vargroup_id))

            # SET VERSION IN JSON OBJECT
            version = int(payload["variables"]["version"]["value"])
            logger.debug("Previous Version: {}".format(version))
            version += 1
            logger.info("Version: {}".format(version))
            payload["variables"]["version"]["value"] = str(version)

            # UPDATE VARIABLE GROUP
            response = ado.update_variable_group(vargroup_id, payload)
            logger.debug("Variable Group Updated.")
    
    except SystemExit as err:
        logger.exception('main failed with exception')
        logger.error(str(err))