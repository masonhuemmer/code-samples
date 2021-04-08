import logging, logging.config, requests, argparse, tarfile, datetime, time, json, sys, os
from helper import Workspace, _ExcludeErrorsFilter, _RedactingFilter

# -------------------------------------------------------------------------------
# Parse Arguments
# -------------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='Terraform Cloud API Program')
required = parser.add_argument_group("required arguments")

# REQUIRED ARGUMENTS
required.add_argument( "--organization", default=os.environ.get('TF_ORGANIZATION'), help="Terraform Cloud Organization")
required.add_argument( "--workspace", default=os.environ.get('TF_WORKSPACE'), help="Terraform Workspace")
required.add_argument( "--version", default=os.environ.get('TF_VERSION'), help="Terraform Version")
required.add_argument( "--token", default=os.environ.get('TF_TOKEN'), help="Terraform API Token")
required.add_argument( "--run", default=os.environ.get('TF_RUNID'), help="Terraform Run ID")

# LOGGING LEVELS - https://docs.python.org/3/library/logging.html#logging-levels
parser.add_argument( "-log", "--log", nargs="?", const="INFO", default="WARNING", help="set logging level for program")

args = parser.parse_args()

# ASSIGN ARGUMENTS TO VARIABLES
organization = args.organization
workspace = args.workspace
version = args.version
token = args.token
run = args.run
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
                token
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
            'level': 'INFO',
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
logger.info("Terraform Version: {}".format(version))
logger.info("Workspace Name: {}".format(workspace))
logger.debug("API Token: {}".format(token))
logger.debug("Run ID: {}".format(run))

# -------------------------------------------------------------------------------
# Terraform Cloud API Program - Load And Run Workspace
# -------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        # CREATE CLASS INSTANCE
        ws = Workspace(organization,workspace,version,token,logger)
        logger.debug("Instance of Class Created")

        # PREPARE FOR APPLY
        apply, done = False, False
        sleep_duration = 5

        # FIND WORKSPACE RUN
        response = ws.get_run(run, query="?include=apply")

        # IF WORKSPACE RUN EXISTS
        if response:

            run_status = response["data"]["attributes"]["status"]
            logger.info("Run Status: {}".format(run_status))

            is_confirmable = response["data"]["attributes"]["actions"]["is-confirmable"]
            logger.debug("IS_CONFIRMABLE: {}".format(is_confirmable))

            if run_status == "planned" and is_confirmable == True:
                apply = True
                logger.debug("Ready to Apply Run")

        if apply:

            # SET APPLY ID
            apply_id = response["included"][0]["id"]
            logger.info("Apply ID: {}".format(apply_id))

            # RETRIEVE JSON TEMPLATE
            with open('templates/apply.json','r') as data:
                payload = json.load(data)
            
            # APPLY TO WORKSPACE RUN
            response = ws.apply_run(run, payload)
            logger.debug("Completed Apply on Run")
            
            while not done:

                #RETRIEVE CURRENT STATUS
                response = ws.show_apply(apply_id)

                # SET APPLY STATUS
                apply_status = response["data"]["attributes"]["status"]
                logger.info("Apply Status: {}".format(apply_status))

                # ROUTE BASED ON STATUS
                if apply_status == "finished":
                    logger.debug("Apply Finished")

                    # PREPARE FOR SAVING PLAN
                    log_directory = "/tmp/apply-{}.log".format(datetime.datetime.now().isoformat())
                    apply_log_url = response["data"]["attributes"]["log-read-url"]
                    
                    # DOWNLOAD PLAN AND STORE IN LOCAL FILE
                    ws.get_log(apply_log_url,log_directory)

                    # RETRIEVE PLAN AND ASSIGN TO VARIABLE
                    with open(log_directory,'r') as data: 
                        log_output = data.read()
                        
                    # PRINT PLAN TO STDOUT
                    print(log_output)

                    # END WHILE LOOP
                    done = True

    except SystemExit as err:
        logger.exception('main failed with exception')
        logger.error(str(err))