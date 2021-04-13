# -------------------------------------------------------------------------------
# Library Imports
# -------------------------------------------------------------------------------

import daimojo.model
import datatable
import pandas

# -------------------------------------------------------------------------------
# HELPER FUNCTIONS
# - model_run(payload)
# - convert_to_datatable(payload)
# - create_scores_payload(measurement, scores, payload)
# - validate_integer(category)
# -------------------------------------------------------------------------------
 
def model_run(payload, logger):

    logger.debug("Payload: {0}".format(payload))
    # -------------------------------------------------------------------------------
    # Pipeline.MOJO Directory // NOT IN PROJECT
    # -------------------------------------------------------------------------------
    mojo_directory = "./lib/pipeline.mojo"
    mojo = daimojo.model(mojo_directory)

    # -------------------------------------------------------------------------------
    # Return Datatable Dataframe using helper.py function
    # -------------------------------------------------------------------------------
    dt = convert_to_datatable(payload)
        
    # -------------------------------------------------------------------------------
    # Return Scores
    # -------------------------------------------------------------------------------
    scores = mojo.predict(dt)
    logger.debug("Payload Score: {0}".format(scores.to_dict()))
    return scores.to_dict()

def convert_to_datatable(payload):

    # -------------------------------------------------------------------------------
    # Convert API Payload to Pandas Dataframe
    # -------------------------------------------------------------------------------

    if(type(payload) == list):
        df = pandas.DataFrame(payload)
    else: 
        df = pandas.DataFrame(payload, index=[0])
    
    # -------------------------------------------------------------------------------
    # Convert Pandas Dataframe to Datatables Dataframe
    # -------------------------------------------------------------------------------

    dt = datatable.Frame(df)

    # -------------------------------------------------------------------------------
    # Return Datatable
    # -------------------------------------------------------------------------------

    return dt

def create_scores_payload(measurement, scores, payload):

    # -------------------------------------------------------------------------------
    # Initialize Array to Build Scores Payload
    # -------------------------------------------------------------------------------
    scores_payload = []

    # -------------------------------------------------------------------------------
    # Enumerate the Sale Prices in List
    # -------------------------------------------------------------------------------

    for count, price in enumerate(scores['SALE PRICE']):

        # -------------------------------------------------------------------------------
        # Simplify Payload 
        # -------------------------------------------------------------------------------

        if(type(payload) == list):
            data = payload[count]
        else:
            data = payload

        # -------------------------------------------------------------------------------
        # Validate Integers from Payload using helper.py function
        # -------------------------------------------------------------------------------

        land_square_feet = validate_integer(data['LAND SQUARE FEET'])
        gross_square_feet = validate_integer(data['GROSS SQUARE FEET'])

        # -------------------------------------------------------------------------------
        # Build Scores Payload
        # -------------------------------------------------------------------------------

        scores_payload.append(
            {
                "measurement": measurement,
                "fields": {
                    "BOROUGH": data['BOROUGH'], 
                    "NEIGHBORHOOD": data['NEIGHBORHOOD'],
                    "BUILDING CLASS CATEGORY": data['BUILDING CLASS CATEGORY'],
                    "COMMERCIAL UNITS": data['COMMERCIAL UNITS'],
                    "TOTAL UNITS": data['TOTAL UNITS'],
                    "LAND SQUARE FEET": land_square_feet,
                    "GROSS SQUARE FEET": gross_square_feet,
                    "YEAR BUILT": data['YEAR BUILT'],
                    "BUILDING CLASS AT TIME OF SALE": data['BUILDING CLASS AT TIME OF SALE'],
                    "SALE PRICE": price
                }
            }
        )

        # -------------------------------------------------------------------------------
        # Return Scores Payload
        # -------------------------------------------------------------------------------

        return scores_payload

def validate_integer(category):
    if category in ['-']:
        data = 0
    else: 
        data = category
    return int(data)
