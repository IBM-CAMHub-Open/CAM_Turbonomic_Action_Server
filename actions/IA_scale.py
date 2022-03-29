#!/usr/bin/python3
# =================================================================
# Copyright 2022 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =================================================================
from configparser import ConfigParser
import json
import logging
import os
import requests
import sys
import time
from urllib3.exceptions import InsecureRequestWarning

IN_PROGRESS = 'In Progress'
ACTIVE = 'Active'

#####################################################################
# Set up logger                                                     #
#####################################################################
LOG_FILE = os.path.join(os.path.dirname(__file__), "IA_scale.log")
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)
logger.info('Action script is running...')

#####################################################################
# Read information from the setting file                            #
#####################################################################
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.ini")
if os.path.exists(SETTINGS_FILE) == False:
    logger.error('Settings file %s does not exist', SETTINGS_FILE)
    sys.exit(1)

parser = ConfigParser()
parser.read(SETTINGS_FILE)
auth_url = parser.get('cam', 'auth_url')
cam_url = parser.get('cam', 'cam_url')
user = parser.get('cam', 'user')
password = parser.get('cam', 'password')
update_service_timeout = int(parser.get('timeouts','update_service'))

def get_access_token():
    '''
    Returns an access token.
    '''
    access_token = None
    auth_header_value = None
    form_data = {'grant_type':'password','username':user, 'password':password,'scope':'openid'}
    response = requests.post(auth_url + '/v1/auth/identitytoken', verify=False, data=form_data)
    if response.status_code == 200:
        access_token = response.json()['access_token']
    else:
        logger.error('Error %d authenticating user %s', response.status_code, user)

    return access_token


def get_tenant_id(access_token):
    '''
    Returns the tenant ID.
    
    Parameters:
        access_token: A valid access token
    Returns:
        The tenant ID
    '''
    tenant_id = None
    if access_token is not None:
        headers = {'Authorization': 'Bearer ' + access_token}
        response = requests.get(cam_url + '/cam/tenant/api/v1/tenants/getTenantOnPrem', verify=False, headers=headers)
        if response.status_code == 200:
            tenant_id = response.json()['id']
        else:
            logger.error('Error %d getting tenant information', response.status_code)

    return tenant_id

def update_service_instance(access_token, tenant_id, service_instance_id, instance_type_parameter, new_instance_type):
    '''
    Update an existing CAM service instance with the new instance type.
    
    Parameters:
        access_token           : A valid access token
        tenant_id              : The tenant ID
        service_instance_id    : The ID of the service instance to update
        instance_type_parameter: The CAM service input parameter that sets the instance type
        new_instance_type      : The new instance type for the update
    Returns:
        The HTTP status code from the update request
    '''
    body = {'update_details': {'instance_parameters': {instance_type_parameter: new_instance_type}}}
    headers = {'Authorization': 'Bearer ' + access_token}
    response = requests.post(cam_url + '/cam/composer/api/v1/ServiceInstances/'+service_instance_id+'/update?tenantId='+tenant_id+'&ace_orgGuid=all', verify=False, headers=headers, json=body)
    if response.status_code != 200:
        logger.error('Error %d updating CAM service instance with ID %s', response.status_code, service_instance_id)
        logger.error(response.text)

    return response.status_code

def get_service_instance_details(access_token, tenant_id, service_instance_id):
    '''
    Return details about a service instance.
    
    Parameters:
        access_token       : A valid access token
        tenant_id          : The tenant ID
        service_instance_id: The ID of the service instance to update
    Returns:
        Service instance details
    '''
    service_instance_details = None

    if access_token is not None and tenant_id is not None:
        headers = {'Authorization': 'Bearer ' + access_token}
        response = requests.get(cam_url + '/cam/composer/api/v1/ServiceInstances/'+service_instance_id+'?tenantId='+tenant_id+'&ace_orgGuid=all', verify=False, headers=headers)
        if response.status_code == 200:
            service_instance_details = response.json()
        else:
            logger.error('Error %d getting details for CAM service instance with ID %s', response.status_code, service_instance_id)
            logger.error(response.text)

    return service_instance_details

def get_service_instance_status(access_token, tenant_id, service_instance_id):
    '''
    Return the service instance status.
    
    Parameters:
        access_token       : A valid access token
        tenant_id          : The tenant ID
        service_instance_id: The ID of the service instance to update
    Returns:
        Service instance status
    '''
    service_instance_status = None
    service_instance_details = get_service_instance_details(access_token, tenant_id, service_instance_id)
    if service_instance_details is not None:
        service_instance_status = service_instance_details['Status']

    return service_instance_status

def main(argv=sys.argv):

    #######################################
    # Only process SCALE actions          #
    #######################################
    input = json.load(sys.stdin)
    action_type = input['actionType']
    if action_type != 'SCALE':
        logger.error('Action type %s is not supported', action_type)
        return(1)

    # Get the SCALE action item from the list of action items
    scale_action = None
    action_items = input['actionItem']
    for action_item in action_items:
        if  action_item['actionType'] == 'SCALE':
            scale_action = action_item
            break

    if scale_action is None:
        logger.error('Did not find a SCALE action item')
        return(1)

    # Only scale virtual machines
    target_se = scale_action.get('targetSE', {}).get('entityType')
    if target_se != 'VIRTUAL_MACHINE':
        logger.error('Scaling ' + target_se + ' is not supported')
        return(1)

    # Get the CAM service instance information from virtual machine tags
    instance_type_parameter = None
    service_instance_id = None
    service_instance_name = None
    for entity_property in scale_action['targetSE']['entityProperties']:

        if entity_property['namespace'] == 'VCTAGS' and entity_property['name'] == 'service_identifier':
            service_instance_id = entity_property['value']

        if entity_property['namespace'] == 'VCTAGS' and entity_property['name'] == 'service_name':
            service_instance_name = entity_property['value']

        if entity_property['namespace'] == 'VCTAGS' and entity_property['name'] == 'turbonomic_instance_type':
            instance_type_parameter = entity_property['value']

        if instance_type_parameter is not None and service_instance_id is not None and service_instance_name is not None:
            break

    if service_instance_id is None:
        logger.error('Did not find the CAM service instance ID')
        return(1)

    # If not explicitly set by a tag, use 'instance_type' as the CAM service
    # input parameter for setting the virtual machine instance type
    if instance_type_parameter is None:
        instance_type_parameter = "instance_type"

    # Get the new instance type from the SCALE action item
    new_instance_type = scale_action['newSE']['id'].split('::')[2]

    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    access_token = get_access_token()
    if access_token is None:
        return(1)

    tenant_id = get_tenant_id(access_token)
    if tenant_id is None:
        return(1)

    exit_status = 0
    logger.info('Update CAM service instance %s with id %s with new instance type %s', service_instance_name,service_instance_id, new_instance_type)
    status_code = update_service_instance(access_token, tenant_id, service_instance_id, instance_type_parameter, new_instance_type)
    if status_code == 200:
        service_instance_status = get_service_instance_status(access_token, tenant_id, service_instance_id)

        # Wait for the CAM service instance update to finish
        time.sleep(30)
        time_waited = 30
        while service_instance_status == IN_PROGRESS and time_waited <= update_service_timeout:
            logger.info('CAM service instance update in progress...')
            time.sleep(10)
            time_waited += 10
            service_instance_status = get_service_instance_status(access_token, tenant_id, service_instance_id)

        if service_instance_status == IN_PROGRESS:
            logger.info('Waited %d seconds for the CAM service instance to update, but it is still in progress', timeout)
        elif service_instance_status == ACTIVE:
            logger.info('CAM service instance %s with ID %s was updated successfully', service_instance_name, service_instance_id)
        else:
            logger.info('CAM service instance %s with ID %s was not updated successfully', service_instance_name, service_instance_id)
            exit_status = 1
    else:
        exit_status = 1

    return(exit_status)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
