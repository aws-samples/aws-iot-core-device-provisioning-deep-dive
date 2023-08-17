'''
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
This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
opensource-codeofconduct@amazon.com with any additional questions or comments.
'''
 
#This python script runs at the docker container lauch, it generates a unique deviceCertificate Key.
#The deviceCertificate Key is used to sign the CSR wiht Certificate DN randomized.
#The Common Name, company and organization are also used to set ENV VARIABLES.
#on host port 8080. The server then returns the signed certificate on response. 
#The certificat eis saved locally in the /certs diretory to be used later on the MQTT connection.
#If sucesfull this script will also launch the iot_client_simulation.py script.

#dependecies
import subprocess
import random
import uuid
from OpenSSL import crypto
from retrying import retry
import requests
from pathlib import Path
import os

#Define working path 
working_path= Path(__file__).resolve().parent
certs_path = working_path /"certs" 

# Define function to set environment variables using the device certificate information.
def set_environment_variables(CN, O, OU):
    try:
        os.environ["DEVICE_CN"] = CN
        os.environ["DEVICE_O"] = O
        os.environ["DEVICE_OU"] = OU
    except Exception as e:
        print(e)

#Define function to get IP address of host from environment variable
def get_ip_address():
    try:
        #Get IP address of host
        ip_address = os.environ["HOST_IP"]
        return ip_address
    except Exception as e:
        print(e)

#Define function to run python script in background
def run_script_in_background(script_path):
    try:
        process = subprocess.Popen(["python3", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True)

        # Continuously read and print the output of the subprocess
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())

        # Wait for the subprocess to complete
        process.wait()

        print(f"Script {script_path} finished with return code: {process.returncode}")
    except Exception as e:
        print(f"Error: {e}")


#Define function to generate Device certificate info and return it as a variable to be user by OpenSSL when request CSR. 
def device_cert_gen():
    try:
        #Select random string from list
        def select_random_string(string_list):
            if not string_list:
                return None
            return random.choice(string_list)

        #Generate UUID (Device serial number)
        Device_serial_number = str(uuid.uuid4()).replace('-', '')

        #Generate random OU
        OU_list = ["Dev", "Prod", ""]
        OU = select_random_string(OU_list)

        #Generate random version 
        VERSION_list = ["HW100", "HW103", "HW200", "HW204"]
        VERSION = select_random_string(VERSION_list)

        #Build Commmon Name
        CN = f"AnyType-{VERSION}-{Device_serial_number}"

        #Organization 
        O = "AnyCompany"

        # Set environment variables using the device certificate information
        set_environment_variables(CN, O, OU)

        print(f"Device CSR will be generated with the following DN - /O={O}/OU={OU}/CN={CN}")

        return [CN, O, OU, VERSION]
    
    except Exception as e:
        print(e)


    
#Define function to generate Device keys and certificate CSR. 
def generate_key_and_csr_with_dn(key_name, common_name, organization, organizational_unit,path):
    
    try:
        # Check if deviceCert.csr is already present
        csr_file_path = os.path.join(path, "deviceCert.csr")
        if os.path.exists(csr_file_path):
            print("CSR file already present, skipping CSR generation.")
            return None  # Return None if CSR file is already present

        # Generate a private key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)

        #adding excpetion for organizational unit Example
        if organizational_unit == "":
            # Generate a certificate signing request (CSR) without OU
            req = crypto.X509Req()
            req.get_subject().CN = common_name
            req.get_subject().O = organization
            req.get_subject().serialNumber 
            req.set_pubkey(key)
            req.sign(key, "sha256")
        else:
            # Generate a certificate signing request (CSR) with OU
            req = crypto.X509Req()
            req.get_subject().CN = common_name
            req.get_subject().O = organization
            req.get_subject().OU = organizational_unit
            req.get_subject().serialNumber 
            req.set_pubkey(key)
            req.sign(key, "sha256")

        # Save the private key in file
        with open(f"{path}/{key_name}.key", "wb") as key_file:
            key_file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        #return CSR as variable to be used on HTTP request.
        # Convert the CSR to a PEM-formatted string
        #Also ves the CSR in a file
        with open(f"{path}/{key_name}.csr", "wb") as csr_file:
            csr_file.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))
        csr_pem = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req).decode('utf-8')

        #print results
        print(f"Private key saved to {path}/{key_name}.key")
        print(f"CSR saved to {path}/{key_name}.csr")
        csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_pem)
        print(f"CSR_Details:{csr.get_subject()}")

        return csr_pem
    
    except Exception as e: 
        print(e)


#Define function to send CSR to server, and get a signed certificate back. 
# It also will start the MQTT connection and test script
# Define a retry decorator
@retry(stop_max_attempt_number=3, wait_fixed=3000)  # Retry 3 times with a fixed delay of 3 seconds
def send_csr_to_server(csr, server_url, certificate_file_path):
    try:
        # Check if deviceCert.crt is already present
        crt_file_path = os.path.join(certificate_file_path, "deviceCert.crt")
        if os.path.exists(crt_file_path):
            print("Certificate file already present, skipping CSR submission and MQTT connection.")
            return  # Return without executing further if certificate file is present
        
        #Submit CSR to server
        headers = {'Content-Type': 'application/x-pem-file'}
        response = requests.post(server_url, data=csr.encode('utf-8'), headers=headers)

        if response.status_code == 200:
            print("CSR successfully sent to the server.")
            print("Server response:")
            print(response.text)

            # Save the response as a certificate file
            with open(f"{certs_path}/deviceCert.crt", "w") as cert_file:
                cert_file.write(response.text)
            
            print(f"Certificate saved to {certificate_file_path}")
        
            #Start MQTT connection and test script
            run_script_in_background(working_path / "iot_client_simulation.py")
                                     
        else:
            raise Exception(f"Error sending CSR to the server. Status code: {response.status_code}\nServer response: {response.text}")
    except Exception as e:
        print(e)

#Main (single execution)

#Generate Distinguished Name for device certificate.
device_cert_dn = device_cert_gen()

#Generate Device Key and CSR with DN.
csr = generate_key_and_csr_with_dn("deviceCert", device_cert_dn[0], device_cert_dn[1], device_cert_dn[2],certs_path) 

#Request CSR to server.
host_ip = get_ip_address()
host = f"http://{host_ip}:8080"
send_csr_to_server(csr, server_url=host, certificate_file_path=certs_path)