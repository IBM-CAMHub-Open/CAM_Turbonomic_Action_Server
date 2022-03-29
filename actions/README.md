# Python Script to Update a CAM Service Instance
This python script reads standard input, parses out the new instance type, and updates a CAM service instance with this new instance type.

**Notes**
- Standard input is the JSON block created by the running of a Turbonomic virtual machine scale action.
- The CAM service must have a service level parameter named **instance_type**. This python script passes the new instance type found in the JSON block as the value for this parameter when it updates the CAM service instance.
- **settings.ini** must be updated with the connection information for your CAM installation.
