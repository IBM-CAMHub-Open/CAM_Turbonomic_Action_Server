# CAM-Turbonomic Integration Action Server
Copyright IBM Corp. 2022

This code is released under the Apache 2.0 License.

## Overview
These files are used to create a Turbonomic action server. This action server handles Turbonomic virtual machine scale actions for virtual machines deployed by a CAM service.

## Prerequisites
1. A Turbonomic instance.
2. A virtual machine to host the action server.
    - The virtual machine must be accessible using an SSH key.
    - The virtual machine must have Python 3 installed.
    - The following Python packages are required: logging, os, requests, sys and time. Use pip3 to install these packages.


## Setting up the action server
1. ssh into the virtual machine.
2. Clone this repository.
3. Set folder permissions: ```chmod -R 755 ./CAM_Turbonomic_Action_Server```
4. Edit file ./CAM_Turbonomic_Action_Server/actions/settings.ini 
5. Update the Cloud Automation Manager connection information: 
```
[cam]
auth_url=https://cp-console.apps.xxx.com
cam_url=https://cam.apps.xxx.com
cam user=my_user
cam pw=my_pw
```
**Note**: The cam_url can be found in the OpenShift Container Platform user interface under **Networking** > **Routes**. 


## Configure the action server in Turbonomic

1. Sign in to Turbonomic
2. In left navigation toolbar, click **SETTINGS**
3. In the **Turbonomic Settings** page click **Target Configuration**
4. Click the **NEW TARGET** button in upper right corner
5. For **Choose Target Category** click **Orchestrator**
6. For **Choose Target Type** click **Action Script**
7. For **ADD Action Script Target** enter:
    - **NAME OR ADDRESS** -  Enter the host name or IP address of the action server.
    - **SCRIPT PATH** - Enter the path of the **IA_scale.yaml** file. For example: /*clone_directory*/CAM_Turbonomic_Action_Server/manifests/IA_scale.yaml
    - **USER ID** - Enter the ID of a user that can ssh into the virtual machine. For example: root
    - **PRIVATE TOKEN** - Enter the users private key.
    - Click **ADD**. Validation runs. If all values are correct the resulting target  onfiguration will appear in the list with a green indicator.
