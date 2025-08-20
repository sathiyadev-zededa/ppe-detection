import requests
from requests import Session
from requests.exceptions import ConnectionError
import json, uuid

class zapi(object):
    def __init__(self, base_url=None, \
             auth_token=None, log=None):

        self.session = Session()
        self.base_url = base_url
        self.auth_token = auth_token
        self.log = log
        self.header = {
            'content-type': 'application/json',
            'Authorization': "bearer {}".format(self.auth_token)   
        }
    
    def get_request(self, url_extention, params=None):

        url = self.base_url + url_extention
        self.log.info("GET request to API {}".format(url))
        try:
            if params == None:
                response = self.session.get(url, headers=self.header)
            else:
                response = self.session.get(url, headers=self.header, params=params)

            if response.status_code != 200:
                self.log.info("GET to url {} failed with response status code {} text output {}".\
                              format(url, response.status_code, response.text))
                return 1, response.text
            json_response = response.json()
        except ConnectionError as e:
           self.log.info("Connection error during GET url {} error{}".format(url, e))
           return 1, str(e)
        except Exception as e:
            self.log.info("Exception during GET url {} error {}".format(url, e))
            return 1, str(e)
        return 0, json_response
    
    def put_request(self, url_extention, payload=None):

        url = self.base_url + url_extention
        self.log.info("PUT request to API {}".format(url))
        try:
            if payload == None:
                response = self.session.put(url, headers=self.header)
            else:
                response = self.session.put(url, headers=self.header, data=json.dumps(payload))
            
            if response.status_code not in [200,202]:
                self.log.info("PUT to url {} failed with response status code {} text  output {}".\
                              format(url, response.status_code, response.text))
                return 1, response.text
            json_response = response.json()
        except ConnectionError as e:
            self.log.info("Connection error when executing PUT url {} error {}".format(url, e))
            return 1, str(e)
        except Exception as e:
            self.log.info("Exception during PUT url {] error {}".format(url, e))
            return 1, str(e)
        return 0, json_response

    def post_request(self, url_extention, payload):

        url = self.base_url + url_extention
        self.log.info("POST request to API {}".format(url))
        try:
            response = self.session.post(url, headers=self.header, data=json.dumps(payload))
            json_response = response.json()
        except ConnectionError as e:
            self.log.info("Connection Error when executing POST {} error {}".format(url, e))
            return 1, str(e)
        except Exception as e:
            self.log.info("Exception when executing POST url {} error {}".format(url, e))
            return 1, str(e)
        return 0, json_response

    def delete_request(self, url_extention):

        url = self.base_url + url_extention
        self.log.info("DELTE request to  API {}".format(url))
        try:
            response = self.session.delete(url, headers=self.header)
            json_response = response.json()
        except ConnectionError as e:
            self.log.info("Connection error when executing PUT url {} error {}".format(url, e))
            return 1, str(e)
        except Exception as e:
            self.log.info("Exception when executing DELETE request url {} error {}".format(url, e))
            return 1, str(e)
        return 0, json_response