from argparse import ArgumentParser
from libs.zapi import zapi
import sys, logging, json, time, re

parser = ArgumentParser()
parser.add_argument('--auth_token', \
                    help="API access authentication token or bearer token", \
                    required=True)
parser.add_argument('--edge_app', \
                    help="input edge app name in Zededa orchestrator Marketplace", \
                    required=True)
parser.add_argument('--data_store',\
                    help="datastore name",\
                    required=True)
parser.add_argument('--container_image',\
                    help="container image", \
                    required=True)

options = parser.parse_args()
zsession = None
name=sys.argv[0].strip('.py')
log = logging.getLogger(name)
log.setLevel(logging.INFO)
handler=logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

def datastore_id(datastore_name):
    ext_url = "/api/v1/datastores/name/{}".format(datastore_name)
    result, response = zsession.get_request(ext_url)
    if result == 0:
        id = response['id']
    else:
        id = None
    return id

def uplink_image(image_id):

    ext_url = "/api/v1/apps/images/id/{}".format(image_id)
    status, response = zsession.get_request(ext_url)
    payload = dict(response)
    ext_url = "/api/v1/apps/images/id/{}/uplink".format(image_id)
    status, response = zsession.put_request(ext_url, payload)
    return status, response

def create_container_image(name, datastore, path):
    """
    method to create newly build container image in zededa orchestration platform
    """
    ext_url = "/api/v1/apps/images"
    payload = {
        "originType": "ORIGIN_LOCAL",
        "imageType": "IMAGE_TYPE_APPLICATION",
        "datastoreIdList": [],
        "imageFormat": "CONTAINER",
        "imageArch": "AMD64",
        "projectAccessList": [],
        "imageSizeBytes": 0
    }
    payload['name'] = name
    payload['title'] = name
    payload['datastoreIdList'].append(datastore)
    payload['imageRelUrl'] = path
    status, response = zsession.post_request(ext_url, payload)
    if status != 0:
        log.info("Post rewust to create {} image failed {}".\
                 format(name, response))
        return 1, None
    return 0, response['objectId']

def get_edge_app_by_name(edge_app):
    ext_url = "/api/v1/apps/name/{}".format(edge_app)
    status, response = zsession.get_request(ext_url)
    if status != 0:
        log.info("failed to get {} parameters from zededa orchestrator".\
                 format(edge_app))
        return None
    
    return dict(response) 

def get_image_by_name(image_name):
    ext_url = "/api/v1/images/name/{}".format(image_name)
    status, response = zsession.get_request(ext_url)
    if status != 0:
        log.info("failed to get id of the image")
        return None
    return response[id]

def update_edge_app(image_name, image_id, edge_app):
    
    payload=get_edge_app_by_name(edge_app)
    id = payload['id']
    if 'images' in payload.get('manifestJSON', {}):
        for image_info in payload['manifestJSON']['images']:
            if image_info.get('imageformat') == "CONTAINER":
                image_info['imagename'] = image_name
                image_info['imageid'] = image_id
    ext_url = "/api/v1/apps/id/{}".format(id)
    status, response = zsession.put_request(ext_url, payload)
    if status != 0:
        log.info("application updated failed")
        return None
    return 0


def main():

    global zsession
    url = "https://zedcontrol.gmwtus.zededa.net"
    zsession = zapi(url, options.auth_token, log)

    ### get datastore ID ###
    id = datastore_id(options.data_store)

    ###Create edge application image ###
    image_name = re.sub(r':', r'_', options.container_image)
    status, image_id = create_container_image(image_name, id, options.container_image)
    if status == 1:
        log.info("Image createing failed")
        sys.exit(1)

    ### uplink image ###
    status, response = uplink_image(image_id)
    ###Update edge application ###
    payload = update_edge_app(image_name, image_id, options.edge_app)

if __name__ == '__main__':
    main()
   





