
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


#Dependencies 
import random
import uuid
from OpenSSL import crypto
import json
import logging
import argparse
import subprocess
import os

#Pass argument into variables usin arparse Lib
try:
    # Pass arguments into variables using argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--fleetsize", action="store", required=True, dest="fleetsize", help="Numbers of devices on the simulated fleet")
    
    args = parser.parse_args() 
    number_of_devices = int(args.fleetsize)
    
    print("Number of Devices:", number_of_devices)
    
except argparse.MissingArgumentError as e:
    print("Error:", e)
    print("Please provide the required arguments.")
except ValueError as e:
    print("Error:", e)
    print("Invalid value provided for fleetsize. Please provide a valid integer.")
except Exception as e:
    print("An error occurred:", e)

# Set up logging
logging.basicConfig(filename='simulation.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


#Define fixed values from this simulation.
#The list below can be changed as needed, keep in mind this resources are expected to be present 
# in AWS IoT Core at the moment of the registration task
ThingTypeName_list = ["ThingTypeA","ThingTypeB","ThingTypeC","ThingTypeD"]
ThingGroups_list = ["CustomerA","CustomerB","CustomerC",""] #Intentionally left "" for unclaimed use case
countryOrigin_list = ["US","UK","IN","CH"]
licenseType_list = ["premium","basic"]

#Define function to create simulation keys and CSRs 
def generate_key_and_csr(serialNumber):
    try:
        # Create a key pair
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        # Generate a CSR
        req = crypto.X509Req()
        subj = req.get_subject()
        subj.O = "AnyCompany"  # Organization
        subj.CN = f"{serialNumber}"  # Common NameserialNumber  # Common Name serial number of device

        # Attach the public key to the CSR
        req.set_pubkey(key)

        # Sign the CSR with the private key
        req.sign(key, 'sha256')

        # Get the private key and CSR in PEM format
        private_key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode('utf-8')
        csr_pem = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req).decode('utf-8')

        # Append private key to file with serial number identification
        with open('keyStore.json', 'a') as key_file:
            key_data = {'device_serialNumber': serialNumber, 'private_key': private_key_pem}
            json.dump(key_data, key_file, indent=2)
            key_file.write('\n')  # Add a newline for separation

        # Append CSR to file with serial number identification
        with open('CSRStore.json', 'a') as csr_file:
            csr_data = {'device_serialNumber': serialNumber, 'csr': csr_pem}
            json.dump(csr_data, csr_file, indent=2)
            csr_file.write('\n')  # Add a newline for separation

        # Log success
        print("INFO - Successfully generated key and CSR for serial number: {}".format(serialNumber))
        logging.info("Successfully generated key and CSR for serial number: {}".format(serialNumber))
        # Return the CSR as a string
        return csr_pem
    except Exception as e:
        # Log error with more details
        print(f"ERROR - Error generating key and CSR for serial number {serialNumber}: {str(e)}")
        logging.error(f"Error generating key and CSR for serial number {serialNumber}: {str(e)}", exc_info=True)
        return None

# Define function to generate random values and build the parameters.json file.
def pick_random_string(lst):
    try:
        return random.choice(lst)
    except Exception as e:
        logging.error(f"Error picking random string: {e}")
        return None

#Define function which builds the parameters.json file content
def build_parameters_and_save(ThingTypeName_list, ThingGroups_name, countryOrigin, licenseType):
    try:
        # Define random values for the parameters.
        ThingTypeName = pick_random_string(ThingTypeName_list)
        ThingGroups = pick_random_string(ThingGroups_name)
        country_origin = pick_random_string(countryOrigin)  # Renamed variable to avoid conflict
        license_type = pick_random_string(licenseType)  # Renamed variable to avoid conflict

        # Generate THING Serial number
        serial_number = str(uuid.uuid4()).replace("-", "") 
        print(f"Serial Number: {serial_number}")

        # Build Thing Name
        thing_name = f"{ThingTypeName}_{serial_number}"
        print(f"Thing Name: {thing_name}")

        # Create Key and CSR
        csr = generate_key_and_csr(serial_number)

        # Build Object
        parameters = {
            "ThingName": thing_name,
            "businessUnitMaker": "AnyCompany",
            "SerialNumber": serial_number,
            "ThingTypeName": ThingTypeName,
            "ThingGroup": ThingGroups,
            "countryOrigin": country_origin,
            "licenseType": license_type,
            "hardwareVersion": "100",
            "softwareVersion": "100",
            "CSR": csr
        }

        # Save parameters to file with a newline
        with open('parameters.json', 'a') as parameters_file:
            parameters_file.write(json.dumps(parameters, indent=None))
            parameters_file.write('\n')
        print(f"INFO - Parameters saved to file: {parameters}")
        logging.info(f"Parameters saved to file: {parameters}")
        return parameters
    except Exception as e:
        print(f"ERROR - Error building parameters and saving to file: {e}")
        logging.error(f"Error building parameters and saving to file: {e}")
        return None
        
#Define function to retrieve values generate during the bootstrap.sh file execution
def get_simulation_variables():
    json_file = "simulation_variables.json"

    try:
        with open(json_file, "r") as file:
            data = json.load(file)
            print(f"INFO - Retrieved simulation variables from file: {json_file}")
            logging.info(f"Retrieved simulation variables from file: {json_file}")
            return data
        
    except FileNotFoundError:
        print(f"Error: {json_file} not found.")
        logging.error(f"Error: {json_file} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Unable to parse {json_file}.")
        logging.error(f"Error: Unable to parse {json_file}.")
        return None


#Defines function to CP to a S3 bucket
def put_object_to_s3_bucket(bucket_name, source_file):
    try:
        subprocess.run(["aws", "s3", "cp", source_file, f"s3://{bucket_name}/"])
        print(f"INFO - {source_file} copied to S3 bucket: {bucket_name}")
        logging.info(f"{source_file} copied to S3 bucket: {bucket_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        logging.error(f"Error: {e}")
        

#Define start registration task function
def start_thing_registration_task(template_body, input_file_bucket, input_file_key, role_arn):
    try:
        command = [
            "aws iot start-thing-registration-task",
            "--template-body", template_body,
            "--input-file-bucket", input_file_bucket,
            "--input-file-key", input_file_key,
            "--role-arn", role_arn
        ]

        subprocess.run(command, check=True)
        print("Thing registration task started successfully.")
        logging.info("Thing registration task started successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        logging.error(f"Error: {e}")
        # Handle the error as needed


# Main function to run the simulation based on argument input 
# Change this to the desired number of device to be registered
for _ in range(number_of_devices):
    run_result = build_parameters_and_save(ThingTypeName_list, ThingGroups_list, countryOrigin_list, licenseType_list)
    # Optionally, you can use the 'run_result' for further processing or checks

#retrieve simulation variables from bootstrap.sh execution
simulation_variables = get_simulation_variables()
print (f"Bucket name is{simulation_variables['BUCKET_NAME']}")
print (f"Provisioning role ARN is{simulation_variables['PROVISIONING_ROLE_ARN']}")

# Copy parameters.json to S3 bucket
send_to_s3 = put_object_to_s3_bucket(simulation_variables["BUCKET_NAME"], "parameters.json")

#Run bulk registration task in AWS IoT Core
start_bulk_registration = start_thing_registration_task("bulk_registration_template.json", simulation_variables["BUCKET_NAME"], "parameters.json", simulation_variables["PROVISIONING_ROLE_ARN"])
    
#end