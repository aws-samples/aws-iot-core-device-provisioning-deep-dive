

#What does this code snippet do:code do: 

#dependecies

import subprocess
import tempfile
import os
import random
import uuid
from OpenSSL import crypto
from retrying import retry
import requests
from pathlib import Path

#Define working path 
working_path= Path(__file__).resolve().parent
certs_path = working_path /"certs" 



#Define function to generate Device certificate info and return it as a variable to be user by OpenSSL when request CSR. 
def device_cert_gen():
    try:
        #Select random string from list
        def select_random_string(string_list):
            if not string_list:
                return None
            return random.choice(string_list)

        #Generate UUID (Device serial number)
        Device_serial_number = uuid.uuid4()

        #Generate random OU
        OU_list = ["Dev", "Prod", ""]
        OU = select_random_string(OU_list)

        #Generate random version 
        VERSION_list = ["HW.1.0.0/SW.1.0.0", "HW.1.0.0/SW.1.0.2", "HW.1.0.0/SW.2.0.0", "HW.1.0.0"]
        VERSION = select_random_string(VERSION_list)

        #Build Commmon Name
        CN = f"AnyThing/{VERSION}/{Device_serial_number}"

        #Organization 
        O = "AnyCompany"

        print(f"Device CSR will be generated with the following DN - /O={O}/OU={OU}/CN={CN}")

        return [CN, O, OU, VERSION]
    
    except Exception as e:
        print(e)


#Define function to generate Device keys and certificate CSR. 
def generate_key_and_csr_with_dn(key_name, common_name, organization, organizational_unit,path):
    
    try:
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


#Define function to send CSR to server. 
# Define a retry decorator
@retry(stop_max_attempt_number=3, wait_fixed=1000)  # Retry 3 times with a fixed delay of 1 seconds
def send_csr_to_server(csr, server_url, certificate_file_path):
    try:
        headers = {'Content-Type': 'application/x-pem-file'}
        response = requests.post(server_url, data=csr.encode('utf-8'), headers=headers)

        if response.status_code == 200:
            print("CSR successfully sent to the server.")
            print("Server response:")
            print(response.text)

            # Save the response as a certificate file
            with open(certificate_file_path, "w") as cert_file:
                cert_file.write(response.text)
            
            print(f"Certificate saved to {certificate_file_path}")
        else:
            raise Exception(f"Error sending CSR to the server. Status code: {response.status_code}\nServer response: {response.text}")
    except Exception as e:
        print(e)




#TEST STUFF REMOVE LATER









#Main (single execution)

#Generate Distinguished Name for device certificate.
device_cert_dn = device_cert_gen()

#Generate Device Key and CSR with DN.
csr = generate_key_and_csr_with_dn("deviceCert", device_cert_dn[0], device_cert_dn[1], device_cert_dn[2],certs_path) 

#Request CSR to server.
host = "http://localhost:8080"
send_csr_to_server(csr, server_url=host, certificate_file_path=certs_path)