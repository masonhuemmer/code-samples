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
required.add_argument( "--directory", default=os.environ.get('TF_DIRECTORY'), help="Terraform Directory")

# OPTIONAL ARGUMENTS
parser.add_argument( "-a", "--auto-approve", help="override confirmations and soft-mandatory policies during workspace run", action="store_true")
parser.add_argument( "-d", "--destroy", help="destroy or tear down infrastructure", action="store_true")

# LOGGING LEVELS - https://docs.python.org/3/library/logging.html#logging-levels
parser.add_argument( "-log", "--log", nargs="?", const="INFO", default="WARNING", help="set logging level for program")

args = parser.parse_args()

# ASSIGN ARGUMENTS TO VARIABLES
organization = args.organization
workspace = args.workspace
version = args.version
token = args.token
directory = args.directory
console_log_level = args.log

# OPTIONAL ARGUMENTS
override = args.auto_approve if args.auto_approve else False
destroy = args.destroy if args.destroy else False

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
logger.info("Terraform Version: {}".format(version))
logger.info("Workspace Name: {}".format(workspace))
logger.info("Terraform Directory: {}".format(directory))
logger.info("API Token: {}".format(token))

# -------------------------------------------------------------------------------
# Terraform Cloud API Program - Load And Run Workspace
# -------------------------------------------------------------------------------
if __name__ == '__main__':
    try:

        # CREATE CLASS INSTANCE
        ws = Workspace(organization,workspace,version,token,logger)
        logger.debug("Instance of Class Created")
        
        # FIND WORKSPACE
        found = ws.show_workspace()
        if not found:

            # RETRIEVE JSON TEMPLATE
            with open('templates/workspace.json','r') as data:
                payload = json.load(data)
                logger.debug("Workspace Payload: {}".format(payload))

            # UPDATE TEMPLATE WITH WORKSPACE ID
            payload["data"]["attributes"]["name"] = ws.name

            # CREATE WORKSPACE
            created = ws.create_workspace(payload)
            if created:
                logger.debug("Workspace created")
        else:
            logger.debug("Workspace Found")

        # SET WORKSPACE ID
        logger.info("Workspace ID: {}".format(ws.id))

        # RETRIEVE JSON TEMPLATE
        with open('templates/configuration.json','r') as data:
            payload = json.load(data)
            logger.debug("Configuration Version Payload: {}".format(payload))

        # CREATE CONFIGURATION VERSION
        created = ws.create_config_version(payload)

        # SET CONFIGURATION VERSION ID AND STATUS
        logger.info("Configuration Version ID: {}".format(ws.config_version_id))
        logger.debug("Configuration Version Created")

        # CREATE TARBALL
        tarball_directory = "config-{}.tar.gz".format((datetime.datetime.now().isoformat()))
        logger.debug("Tarball Directory: {}".format(tarball_directory))

        payload = ws.create_tarball(tarball_directory, directory)
        logger.debug("Tarball of Terraform Scripts Created")

        # UPLOAD TARBALL TO WORKSPACE
        uploaded = ws.upload_config_files(payload)
        if uploaded:
            logger.debug("Upload Request Completed")
        
        # PRPEARE FOR WHILE LOOP
        sleep_duration = 5
        done = False

        # CHECK CONFIGURATION VERSION STATUS
        logger.debug("Check Configuration Version Status")

        while not done:

            # RETRIEVE CONFIG VERSION
            response = ws.show_config_version()

            # SET CONFIG VERSION STATUS
            config_version_status = response["data"]["attributes"]["status"]

            # ROUTE ON STATUS
            if config_version_status == "uploaded":
                logger.info("Configuration Version Status: {}".format(config_version_status))
                done = True
            elif config_version_status == "errored":
                raise Exception("Configuration Version Upload Errored. Unable to proceed.")
            else:
                logger.debug("Waiting {} Seconds Before Next Loop".format(sleep_duration))
                time.sleep(sleep_duration)
        
        # PREPARE FOR VARIABLES
        sleep_duration = 2
        insert_variable = False

        # RETRIEVE EXISTING VARIABLES
        existing_variables = ws.list_variables()
        logger.debug("Retrieve Existing Variables in Workspace")

        # RETRIEVE VARIABLES JSON PAYLOAD TO ADD / UPDATE
        with open('{}/variables.json'.format(directory),'r') as data:
            payload = json.load(data)

        # INSERT / UPDATE WORKSPACE VARIABLES
        for element in payload:

            # SET TO TRUE, UNLESS FOUND IN TERRAFORM
            insert_variable = True

            for variable in existing_variables["data"]:
                if element["data"]["attributes"]["key"] == variable["attributes"]["key"]:
                    
                    # DELETE ELEMENT TO COMPARE
                    del variable["attributes"]["created-at"]
                    
                    # IF ELEMENTS DO NOT MATCH, UPDATE VARIABLES
                    if element["data"]["attributes"] != variable["attributes"]:
                        
                        # IF VARIABLE IS SENSITIVE, DELETE AND RE-ADD
                        if variable["attributes"]["sensitive"]:
                            
                            logger.info("Workspace Variable '{}' Is Sensative. Requires Delete and Re-Add Variable".format(element["data"]["attributes"]["key"]))

                            # DELETE VARIABLE
                            ws.delete_variable(variable["id"])
                            logger.info("Workspace Variable '{}' Has Been Deleted".format(element["data"]["attributes"]["key"]))
                            insert_variable = True

                        else:
                            # UPDATE VARIABLE
                            ws.update_variable(variable["id"],element)
                            
                            # LOG OUTCOME
                            logger.info("Workspace Variable '{0}' Has Been Updated".format(element["data"]["attributes"]["key"]))
                            logger.debug("{0}: {1}".format(element["data"]["attributes"]["key"], element["data"]["attributes"]["value"]))

                    else:
                        # NO UPDATE REQUIRED
                        insert_variable = False
                        logger.info("Workspace Variable '{}' Match Found. No Update Required".format(element["data"]["attributes"]["key"]))

            # INSERT VARIABLE
            if insert_variable:

                # INSERT VARIABLE
                ws.create_variable(element)

                # LOG OUTCOME
                logger.info("Workspace Variable '{0}' Has Been Added".format(element["data"]["attributes"]["key"]))
                logger.debug("{0}: {1}".format(element["data"]["attributes"]["key"], element["data"]["attributes"]["value"]))
            
            # WAIT BEFORE NEXT LOOP
            logger.debug("Waiting {} Seconds Before Next Loop".format(sleep_duration))
            time.sleep(sleep_duration)
        

        # RETRIEVE JSON TEMPLATE
        with open('templates/run.json','r') as data:
            payload = json.load(data)
            logger.debug("Run Payload: {}".format(payload))

        # UPDATE TEMPLATE WITH WORKSPACE ID
        payload["data"]["relationships"]["workspace"]["data"]["id"] = ws.id

        # UPDATE TEMPLATE WITH DESTROY
        if destroy:
            payload["data"]["attributes"]["is-destroy"] = True
            payload["data"]["attributes"]["message"] = "Queued to destroy infrastructure via the Terraform Cloud API"

        # CREATE WORKSPACE RUN
        response = ws.create_run(payload)
        logger.debug("Workspace Run Created")

        # SET RUN ID
        run = response["data"]["id"]
        logger.info("Run ID: {}".format(run))
        
        # PREPARE FOR WHILE LOOP
        done = False
        post_status = False
        save_plan = False
        apply = False
        sleep_duration = 5

        # CHECK RUN STATUS UNTIL UPDATE
        while not done:
            
            # RETRIEVE CURRENT RUN 
            response = ws.get_run(run)

            # SET RUN STATUS AND IS_CONFIRMABLE
            run_status = response["data"]["attributes"]["status"]
            logger.info("Run Status: {}".format(run_status))

            is_confirmable = response["data"]["attributes"]["actions"]["is-confirmable"]
            logger.debug("IS_CONFIRMABLE: {}".format(is_confirmable))

            # ROUTE BASED ON STATUS
            if run_status == "planned" and is_confirmable == True and override == False:
                save_plan, done = True, True
                logger.debug("Ready to review plan")
            elif run_status == "planned" and is_confirmable == True and override == True:
                apply, done = True, True
                logger.debug("Ready to Apply Run")
            elif run_status == "cost_estimated" and is_confirmable == True and override == False:
                save_plan, done = True, True
                logger.debug("Ready to review plan")
            elif run_status == "cost_estimated" and is_confirmable == True and override == True:
                apply, done = True, True
                logger.debug("Ready to Apply Run")                     
            elif run_status == "planned_and_finished":
                logger.debug("No changes. Infrastructure is up-to-date.")
                done = True
            elif run_status == "errored":
                logger.error("Error with plan. Unable to continue.")
                save_plan, done = True, True
            else:
                logger.debug("Wait {} Seconds Before Next Loop".format(sleep_duration)) 
                time.sleep(sleep_duration)
  
        if save_plan:

            # UNCOMMENT FOR AZURE DEVOPS PIPELINES
            print("##vso[task.setvariable variable=RUN_ID;]'{}'".format(run))

            # PREPARE FOR SAVING PLAN
            log_directory = "/tmp/plan-{}.log".format(datetime.datetime.now().isoformat())

            # RETRIEVE CURRENT PLAN
            response = ws.get_run(run, query="?include=plan")
            
            # SET PLAN LOG URL
            plan_log_url = response["included"][0]["attributes"]["log-read-url"]

            # DOWNLOAD PLAN AND STORE IN LOCAL FILE
            ws.get_log(plan_log_url,log_directory)

            # RETRIEVE PLAN AND ASSIGN TO VARIABLE
            with open(log_directory,'r') as data: 
                log_output = data.read()
            
            # PRINT PLAN TO STDOUT
            print(log_output)

        # RUN READY FOR APPLY
        if apply:

            # RETRIEVE CURRENT PLAN
            response = ws.get_run(run, query="?include=apply")

            # SET APPLY ID
            apply_id = response["included"][0]["id"]
            logger.info("Apply ID: {}".format(apply_id))

            # RETRIEVE JSON TEMPLATE
            with open('templates/apply.json','r') as data:
                payload = json.load(data)
            
            # APPLY TO WORKSPACE RUN
            response = ws.apply_run(run, payload)
            logger.debug("Completed Apply on Run")

            # PREPARE FOR WHILE LOOP
            done = False

            while not done:

                #RETRIEVE CURRENT STATUS
                response = ws.show_apply(apply_id)

                # SET APPLY STATUS
                apply_status = response["data"]["attributes"]["status"]
                logger.info("Apply Status: {}".format(apply_status))

                # ROUTE BASED ON STATUS
                if apply_status == "finished":
                    logger.debug("Apply Finished")
                    done = True
                elif apply_status == "errored":
                    logger.error("Error with plan. Exit Program.")
                    done = True
                time.sleep(sleep_duration)

    except SystemExit as err:
        logger.exception('main failed with exception')
        logger.error(str(err))