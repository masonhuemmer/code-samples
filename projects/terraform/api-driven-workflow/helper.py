import requests, logging, tarfile, json, os

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

class Workspace:
    def __init__(self, org, name, version, token, logger):
        self.org = org
        self.name = name
        self.version = version
        self.token = token
        self.logger = logger
        self.id = ""
        self.config_version_id = ""
        self.upload_url = ""

    # -------------------------------------------------------------------------------
    # API Reference Doc - Workspaces
    # https://www.terraform.io/docs/cloud/api/workspaces.html
    # -------------------------------------------------------------------------------
    def create_workspace(self, payload: list):

        url = "https://app.terraform.io/api/v2/organizations/{0}/workspaces".format(self.org)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }
        payload = json.dumps(payload)

        try:
            response = requests.post(url,data=payload,headers=header)
            response.raise_for_status()
            self.id = response.json()["data"]["id"]
        except requests.exceptions.HTTPError as errh:
            if errh.response.status_code == 422:
                return False
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def update_workspace(self, payload: list):

        url = "https://app.terraform.io/api/v2/organizations/{0}/workspaces/{1}".format(self.org,self.name)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }
        payload = json.dumps(payload)

        try:
            response = requests.patch(url,data=payload,headers=header)
            response.raise_for_status()
            self.id = response.json()["data"]["id"]
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json() 

    def show_workspace(self):                 

        url = "https://app.terraform.io/api/v2/organizations/{0}/workspaces/{1}".format(self.org,self.name)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try: 
            response = requests.get(url,headers=header)
            response.raise_for_status()
            self.id = response.json()["data"]["id"]
        except requests.exceptions.HTTPError as errh:
            if errh.response.status_code == 404:
                return False
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def list_workspaces(self):                 

        url = "https://app.terraform.io/api/v2/organizations/{0}/workspaces".format(self.org)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try: 
            response = requests.get(url,headers=header)
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            if errh.response.status_code == 404:
                return False
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    # -------------------------------------------------------------------------------
    # API Reference Doc - Configuration Versions
    # https://www.terraform.io/docs/cloud/api/configuration-versions.html
    # -------------------------------------------------------------------------------
    def list_config_version(self, query=""):
        
        url = "https://app.terraform.io/api/v2/workspaces/{0}/configuration-versions{1}".format(self.id,query)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try:
            response = requests.get(url,headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def show_config_version(self):
        
        url = "https://app.terraform.io/api/v2/configuration-versions/{0}".format(self.config_version_id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try:
            response = requests.get(url,headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def create_config_version(self, payload: list):

        url = "https://app.terraform.io/api/v2/workspaces/{0}/configuration-versions".format(self.id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }
        payload = json.dumps(payload)

        try:
            response = requests.post(url,data=payload,headers=header)
            response.raise_for_status()
            self.config_version_id = response.json()["data"]["id"]
            self.upload_url = response.json()["data"]["attributes"]["upload-url"]
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def upload_config_files(self, payload):
        
        success = False

        url = self.upload_url
        header = {
            "content-type": "application/octet-stream", 
        }

        try:
            response = requests.put(url,data=payload,headers=header)
            response.raise_for_status()
            success = True
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return success

    def create_tarball(self, tarball, source_directory):

        with tarfile.open(tarball, "x:gz") as tar:
            tar.add(source_directory, arcname=".")

        with open(tarball,"rb") as data_bytes:
            payload = data_bytes.read()
            return payload

    # -------------------------------------------------------------------------------
    # API Reference Doc - Workspace Variables 
    # https://www.terraform.io/docs/cloud/api/workspace-variables.html
    # -------------------------------------------------------------------------------
    def create_variable(self, payload: list):

        url = "https://app.terraform.io/api/v2/workspaces/{0}/vars".format(self.id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }
        payload = json.dumps(payload)

        try:
            response = requests.post(url,data=payload,headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()["data"]["id"] 

    def list_variables(self):
        
        url = "https://app.terraform.io/api/v2/workspaces/{0}/vars".format(self.id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try:
            response = requests.get(url,headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def update_variable(self, variable_id, payload: list):
        success = False

        url = "https://app.terraform.io/api/v2/workspaces/{0}/vars/{1}".format(self.id, variable_id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }
        payload = json.dumps(payload)

        try:
            response = requests.patch(url,data=payload,headers=header)
            response.raise_for_status()
            success = True
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return success

    def delete_variable(self, variable_id):
        success = False

        url = "https://app.terraform.io/api/v2/workspaces/{0}/vars/{1}".format(self.id, variable_id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try:
            response = requests.delete(url,headers=header)
            response.raise_for_status()
            success = True
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return success

    # -------------------------------------------------------------------------------
    # API Reference Doc - Runs
    # https://www.terraform.io/docs/cloud/api/run.html
    # -------------------------------------------------------------------------------
    def create_run(self, payload: list):
        
        url = "https://app.terraform.io/api/v2/runs"
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }
        payload = json.dumps(payload)

        try:
            response = requests.post(url,data=payload, headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def get_run(self, run_id, query=""):

        url = "https://app.terraform.io/api/v2/runs/{0}{1}".format(run_id,query)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try:
            response = requests.get(url, headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def get_log(self,log_url, source_directory):

        url = log_url

        try:
            log_file = requests.get(url)
            open(source_directory,'wb').write(log_file.content)
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

    def apply_run(self, run_id, payload: list):
        
        url = "https://app.terraform.io/api/v2/runs/{0}/actions/apply".format(run_id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }
        payload = json.dumps(payload)

        try:
            response = requests.post(url,data=payload, headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()

    def show_apply(self, apply_id):

        url = "https://app.terraform.io/api/v2/applies/{0}".format(apply_id)
        header = {
            "content-type": "application/vnd.api+json", 
            "Authorization": "Bearer {0}".format(self.token) 
        }

        try:
            response = requests.get(url, headers=header)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("{0}".format(err))

        return response.json()