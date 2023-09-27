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


#This code starts a web server that receives a CSR from secure network and returns a signed certificate.
#The Web server makes use of OpenSSL to sign the CSR, using the root CA certificate. Then returns the signed
#to requester. There are no authenticaiton mechanisms implemented, this is a simulation of an isolated network.

#Dependencies
import http.server
import socketserver
from OpenSSL import crypto
from pathlib import Path
import logging
import json


# Define working path
working_path = Path(__file__).resolve().parent

# Set up logging
logs_folder = working_path / "logs"
logs_folder.mkdir(parents=True, exist_ok=True)
log_file_path = logs_folder / 'server.log'  # Full path to the log file
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

#Define function to load serialNumbers from file into memory
def load_serial_numbers_from_file(file_path):
    try:
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
            logging.info(f"Loaded serial numbers from file: {file_path}")
            return data
    except Exception as e:
        # Handle any exceptions, e.g., file not found or JSON parsing error
        print(f"Error loading serial numbers: {e}")
        logging.error(f"Error loading serial numbers: {e}")
        return {}
# Define a global variable to keep track of the used serial numbers
used_serial_numbers = set()

# Usage example:
file_path = "serial_numbers.json"
serial_numbers_data = load_serial_numbers_from_file(file_path)
print(serial_numbers_data)


# Describe class to handle CSR requests
# Describe class to handle CSR requests
class CSRHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        csr_data = self.rfile.read(content_length).decode('utf-8')

        signed_cert = self.sign_csr(csr_data)

        self.send_response(200)
        self.send_header('Content-Type', 'application/x-pem-file')
        self.end_headers()
        self.wfile.write(signed_cert.encode('utf-8'))

    def sign_csr(self, csr_data):
        try:
            # Load CA private key and certificate
            ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(f"{working_path}/certs/rootCA.key").read())
            ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(f"{working_path}/certs/rootCA.pem").read())

            # Load and parse the incoming CSR
            csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_data)
            csr_subject = csr.get_subject()

            # Get the next available serial number from the list
            serial_numbers_data = load_serial_numbers_from_file(f"{working_path}/serial_numbers.json")
            serial_numbers = serial_numbers_data.get("serial_numbers", [])

            serial_number = None
            while serial_numbers:
                potential_serial = serial_numbers[0]
                if potential_serial not in used_serial_numbers:
                    serial_number = potential_serial
                    used_serial_numbers.add(serial_number)
                    break
                else:
                    serial_numbers.pop(0)

            if serial_number is None:
                raise Exception("No more serial numbers available.")

            # Create a new certificate
            signed_cert = crypto.X509()
            signed_cert.set_subject(csr_subject)
            signed_cert.set_pubkey(csr.get_pubkey())
            signed_cert.set_serial_number(serial_number)
            signed_cert.gmtime_adj_notBefore(0)
            signed_cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 1 year validity
            signed_cert.set_issuer(ca_cert.get_subject())
            signed_cert.sign(ca_key, "sha256")

            # Log the certificate signing operation
            logging.info(f"Certificate for {csr_subject} signed by {ca_cert.get_subject()} with serial number {serial_number}")

            # Return the signed certificate
            return crypto.dump_certificate(crypto.FILETYPE_PEM, signed_cert).decode('utf-8')

        except Exception as e:
            logging.error(f"Error signing CSR: {e}")
            return ""

# Set up the HTTP server
handler = CSRHandler
httpd = socketserver.TCPServer(('0.0.0.0', 8080), handler)

logging.info("Server started at http://0.0.0.0:8080")
httpd.serve_forever()