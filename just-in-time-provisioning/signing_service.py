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
import uuid

# Define working path
working_path = Path(__file__).resolve().parent


# Set up logging
logging.basicConfig(
    filename='./logs/server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
            ca_key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(f"{working_path}/rootCA.key").read())
            ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(f"{working_path}/rootCA.pem").read())

            # Load and parse the incoming CSR
            csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_data)
            csr_subject = csr.get_subject()

            # Create a new certificate
            signed_cert = crypto.X509()
            signed_cert.set_subject(csr_subject)
            signed_cert.set_pubkey(csr.get_pubkey())
            signed_cert.set_serial_number(uuid.uuid4().int)  # Generate a UUID-based serial number)
            signed_cert.gmtime_adj_notBefore(0)
            signed_cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 1 year validity
            signed_cert.set_issuer(ca_cert.get_subject())
            signed_cert.sign(ca_key, "sha256")

            # Log the certificate signing operation
            logging.info(f"Certificate for {csr_subject} signed by {ca_cert.get_subject()}")

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