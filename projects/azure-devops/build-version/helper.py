import requests, logging, json, os

class _ExcludeErrorsFilter(logging.Filter):
    def filter(self, record):
        """Filters out log messages with log level ERROR (numeric value: 40) or higher."""
        return record.levelno < 40

class _RedactingFilter(logging.Filter):
    def __init__(self, patterns):
        self._patterns = patterns

    def filter(self, record):
        record.msg = self.redact(record.msg)
        if isinstance(record.args, dict):
            for k in record.args.keys():
                record.args[k] = self.redact(record.args[k])
        else:
            record.args = tuple(self.redact(arg) for arg in record.args)
        return True

    def redact(self, msg):
        msg = str(msg)
        for pattern in self._patterns:
               msg = msg.replace(pattern, "***")
        return msg

class AzureDevOps:
    def __init__(self, org, project, token, logger):
        self.org = org
        self.project = project
        self.token = ('','{0}'.format(token))
        self.logger = logger

    # -------------------------------------------------------------------------------
    # API Reference Doc - Workspaces
    # https://www.terraform.io/docs/cloud/api/workspaces.html
    # -------------------------------------------------------------------------------
    def get_variable_groups(self,query=""):

        url = "{0}{1}/_apis/distributedtask/variablegroups{2}".format(self.org,self.project,query)
        header = {  "content-type": "application/json" }

        try:
            response = requests.get(url,headers=header, auth=self.token)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def get_variable_group(self,vargroup_id):

        url = "{0}{1}/_apis/distributedtask/variablegroups/{2}?api-version=6.0-preview.2".format(self.org,self.project,vargroup_id)
        header = {  "content-type": "application/json" }

        try:
            response = requests.get(url,headers=header, auth=self.token)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def update_variable_group(self, vargroup_id, payload):

        url = "{0}{1}/_apis/distributedtask/variablegroups/{2}?api-version=5.1-preview.1".format(self.org, self.project, vargroup_id)
        header = {  "content-type": "application/json" }
        payload = json.dumps(payload)
    
        try:
            response = requests.put(url,headers=header,data=payload,auth=self.token)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()