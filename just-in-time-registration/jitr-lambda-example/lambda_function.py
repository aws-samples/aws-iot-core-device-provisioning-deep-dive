# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Code of Conduct
# This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
# For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
# opensource-codeofconduct@amazon.com with any additional questions or comments.

#This code is based on previous work from https://github.com/aws-samples/aws-iot-device-management-workshop
#This code has no retry strategy implemented.
#This code will not handle error for missing rerources such as ThingType, Things or ThingGroups



#Dependencies
import boto3 #AWS CLI SDk for Python
import logging
import json 
import os
from OpenSSL import crypto #Crypto library to extract info from certificate
from cryptography import x509 #x509 library to extract serial number from certificate
from cryptography.hazmat.backends import default_backend #x509 library to extract serial number from certificate

#Configure logging
Logger = logging.getLogger(__name__)
Logger.setLevel(logging.INFO)

ERROR = []

#Define 2 functions to extract certificate info from certificate
def extract_serial_number(cert_pem):
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        serial_number = cert.serial_number

        return serial_number
    except Exception as e:
        Logger.error(f"Error extracting serial number: {str(e)}")
        return None

def get_certificate_info(response):
    try:
        cert_pem = response['certificateDescription']['certificatePem']
        cert_arn = response['certificateDescription']['certificateArn']
        Logger.info(cert_pem)

        # Extract serial number from certificate
        serial_number = extract_serial_number(cert_pem)
        Logger.info(f"serialNumber: {serial_number}")

        # Extract additional certificate attributes
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        subject = cert.subject
        

        # Extract DN Qualifier and other attributes
        dn_qualifier = None
        common_name = None
        organizational_unit = None
        organization = None

        for attribute in subject:
            if attribute.oid == x509.NameOID.DN_QUALIFIER:
                dn_qualifier = attribute.value
            elif attribute.oid == x509.NameOID.COMMON_NAME:
                common_name = attribute.value
            elif attribute.oid == x509.NameOID.ORGANIZATIONAL_UNIT_NAME:
                organizational_unit = attribute.value
            elif attribute.oid == x509.NameOID.ORGANIZATION_NAME:
                organization = attribute.value
        Logger.info(f"Certificate ARN: {cert_arn}")
        Logger.info(f'dnQ:{dn_qualifier},CN:{common_name},OU:{organizational_unit},O:{organization}')
        return {
            'serial_number': serial_number,
            'distinguished_name_qualifier': dn_qualifier,
            'common_name': common_name,
            'organizational_unit': organizational_unit,
            'organization': organization,
            'certificate_arn': cert_arn
        }
    except Exception as e:
        Logger.error(e)

#Define function to create thing in AWS IoT, with thingType and Attributes
def aws_iot_create_thing(iot_client, thingName, thingTypeName=None, attributes=None, merge=False, billingGroupName=None):
    try:
        # Define the parameters
        params = {
            'thingName': thingName,
            'attributePayload': {
                'attributes': attributes,
                'merge': merge
            }
        }
        
        # Add thingTypeName if provided
        if thingTypeName:
            params['thingTypeName'] = thingTypeName
        
        # Create the thing with optional billingGroupName
        if billingGroupName:
            params['billingGroupName'] = billingGroupName
        
        # Create the thing
        response = iot_client.create_thing(**params)
        Logger.info(params)
        # Log the response
        Logger.info(response)
    except Exception as e:
        Logger.error(e)
        ERROR.append(e)

#Define function to add thing to thing group in AWS IoT
def aws_iot_add_thing_to_thinggroup(iot_client, thingGroupName, thingName):
    try:
        Logger.info(f"Adding {thingName} to {thingGroupName}")
        response = iot_client.add_thing_to_thing_group(thingGroupName=thingGroupName, thingName=thingName)
        Logger.info(response)
        #handles exception when thingGroup is not found, it adds it to unclaimed
    except iot_client.exceptions.ResourceNotFoundException:
        Logger.info(f"Thing group '{thingGroupName}' not found. Adding {thingName} to 'unclaimed' group.")
        try:
            response_unclaimed = iot_client.add_thing_to_thing_group(thingGroupName='unclaimed', thingName=thingName)
            Logger.info(response_unclaimed)
        except Exception as e:
            Logger.error(e)
            ERROR.append(e)
    except Exception as e:
        Logger.error(e)
        ERROR.append(e)

#Define function to attach policy to principal in AWS IoT
def aws_iot_attach_policy(iot_client,policyName,principal):    
    try:
        Logger.info(f"Attaching {policyName} to {principal}")
        response = iot_client.attach_policy(policyName=policyName,target=principal)    
        Logger.info(response)
    except Exception as e:
        Logger.error(e)
        ERROR.append(e)

#Define function to describe certificate in AWS IoT
def aws_iot_describe_certificate(iot_client,certificateId):
    try:
        response = iot_client.describe_certificate(certificateId=certificateId)
        Logger.info(response)
        return response
    except Exception as e:
        Logger.error(e)
        ERROR.append(e)

#Define function to activate certificate in AWS IoT
def aws_iot_activate_certificate(iot_client,certificateId):
    try:
        response = iot_client.update_certificate(certificateId=certificateId,newStatus='ACTIVE')
        Logger.info(response)
    except Exception as e:
        Logger.error(e)
        ERROR.append(e)

#Define function to attach certificate to thing in AWS IoT
def aws_iot_attach_certificate(iot_client,certificateARN,thingName):
    try:
        response = iot_client.attach_thing_principal(thingName=thingName,principal=certificateARN)  
        Logger.info(response)
    except Exception as e:
        Logger.error(e)
        ERROR.append(e)

#Define function to check DynamoDB table for allowed serial number
def check_serial_number(dynamodb, table_name, serial_number_int):
    try:
        #Convert serial number to string
        serial_number = str(serial_number_int)
        # Define the primary key for the query
        key_condition_expression = 'serialNumber = :serial_number'
        expression_attribute_values = {':serial_number': {'S': serial_number}}

        # Query the DynamoDB table
        response = dynamodb.query(
            TableName=table_name,
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

        # Extract and return the query results
        items = response.get('Items', [])
        
        if items:
            # If the serial number is found, construct the dictionary
            item = items[0]  # Assuming there's only one matching item
            result_dict = {
                'allowProvisioning': True,
                'serialNumber': item.get('serialNumber', {}).get('S', 'none'),
                'Ownership': item.get('Ownership', {}).get('S', 'none')
            }
        else:
            # If the serial number is not found, return the not found dictionary
            result_dict = {
                'allowProvisioning': False,
                'serialNumber': 'none',
                'Ownership': 'none'
            }
        Logger.info(result_dict)    
        return result_dict
    except Exception as e:
        Logger.error(f"An error occurred: {str(e)}")


#MAIN

#Define Lambda function handler


event = {
  "certificateId": "8f17408ba4f89fd08010d96e09b5e5f033ab0372d3470821d89c98c5e336834c",
  "caCertificateId": "dbe57b77e32c89ec2e5fec27cd444c1856da1d39fa664400844e5c4459b30ca6",
  "timestamp": 1695074220131,
  "certificateStatus": "PENDING_ACTIVATION",
  "awsAccountId": "404125507795",
  "certificateRegistrationTimestamp": None,
  "sourceIp": "67.161.193.248"
}


def lambda_handler(event, context):
    Logger.info("event: {}".format(event))
    Logger.info(json.dumps(event, indent=4))

    region = os.environ["AWS_REGION"]
    Logger.info("region: {}".format(region))

    #REMOVE LATER
    table_name = 'AnyCompany_serilaNumber'
    policyName = 'ALLOW_ALL_TEST_ONLY'
    

    try:
        #Get certificate info from event
        ca_certificate_id = event['caCertificateId']
        certificate_id = event['certificateId']
        certificate_status = event['certificateStatus']

        Logger.info("ca_certificate_id: " + ca_certificate_id)
        Logger.info("certificate_id: " + certificate_id)
        Logger.info("certificate_status: " + certificate_status)

        #Initialize AWS IoT client
        iot_client = boto3.client('iot')
        #Initialize DynamoDB client
        dynamodb_client = boto3.client('dynamodb')

        #Extract certificate info from certificate
        certificate_info = get_certificate_info(aws_iot_describe_certificate(iot_client,certificate_id))

        #Check DynamoDB table for allowed serial number
        allow_provisioning= check_serial_number(dynamodb_client, table_name, certificate_info['serial_number'])
        if allow_provisioning['allowProvisioning']:
            #Activate certificate in AWS IoT
            aws_iot_activate_certificate(iot_client,certificate_id)
            # Dumps attributes to a dictionary
            thing_attributes = {
                "CA": "IoT-Device-Root-CA",
                "hardwareVersion": certificate_info['common_name'],
                "provisioning": "JITR",
                "serialNumber": str(certificate_info['serial_number']),  # Convert to string
                "softwareVersion": "1.0.0"
            }
            # Create thing in AWS IoT
            aws_iot_create_thing(
                iot_client,
                thingName=str(certificate_info['serial_number']),  # Convert to string
                thingTypeName=certificate_info['distinguished_name_qualifier'],
                attributes=thing_attributes,  # Pass as a dictionary
                merge=False,
                billingGroupName=certificate_info['organization']
            )
            #Add thing to thing group in AWS IoT
            aws_iot_add_thing_to_thinggroup(iot_client,thingGroupName=str(certificate_info['organizational_unit']),
                                            thingName=str(certificate_info['serial_number']))
            #Attach certificate to thing in AWS IoT
            aws_iot_attach_certificate(iot_client,certificateARN=str(certificate_info['certificate_arn']),
                                       thingName=str(certificate_info['serial_number']))
            #Attach policy to principal in AWS IoT
            aws_iot_attach_policy(iot_client,policyName=policyName,
                                  principal=certificate_info['certificate_arn'])
        else:
            Logger.info("Serial Number not found in database, provisioning failed")
            Logger.warn("Serial Number not found in database, provisioning failed, this could indicate a security breach")
            return {"status": "warning", "message": "Serial Number not found in database, provisioning failed, this could indicate a security breach"}
            
    except Exception as e:
        Logger.error(e)
        return {"status": "error", "message": '{}'.format(e)}

    if ERROR:
        return {"status": "error", "message": '{}'.format(ERROR)}

    return {"status": "success"}
            
print('run')
invoke=lambda_handler(event,"test")
print(invoke)