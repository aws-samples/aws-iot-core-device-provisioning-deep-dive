



import http.server
import socketserver
from OpenSSL import crypto
from pathlib import Path

#Define working path 
working_path= Path(__file__).resolve().parent


#Describe class to handle CSR requests
#Create a server session that receives a CSR from secure network, signs with CA and return certificate.
class CSRHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        csr_data = self.rfile.read(content_length).decode('utf-8')

        signed_cert = self.sign_csr(csr_data)

        self.send_response(200)
        self.send_header('Content-Type', 'application/x-pem-file')
        self.end_headers()
        self.wfile.write(signed_cert.encode('utf-8'))

    def sign_csr(self, csr_data, working_path):
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
        signed_cert.set_serial_number(1)
        signed_cert.gmtime_adj_notBefore(0)
        signed_cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 1 year validity
        signed_cert.set_issuer(ca_cert.get_subject())
        signed_cert.sign(ca_key, "sha256")

        return crypto.dump_certificate(crypto.FILETYPE_PEM, signed_cert).decode('utf-8')

# Set up the HTTP server
handler = CSRHandler
httpd = socketserver.TCPServer(('localhost', 8080), handler)

print("Server started at http://localhost:8080")
httpd.serve_forever()