import json
import os
from sqlite3 import Timestamp
import subprocess 
import time

#copy uuid from Env var

DOCKER_ID = os.environ['DOCKER_ID']
ENDPOINT = os.environ['ENDPOINT']
print(f"The DOCKER_ID is {DOCKER_ID}")
topic = f"device/{DOCKER_ID}"
print(f"{topic}")
print(f"publishing to {ENDPOINT}")
# Publish to the same topic in a loop forever
loopcount = 0
while True:

    #build simulation message 
    simulation_message = { 
                      "message": {"sequence": loopcount,
                                  "Device_ID": DOCKER_ID}
                        }
                            
    payload = json.dumps(simulation_message)
    
    print(simulation_message)

    cmd = f"mosquitto_pub --cafile root.cert --cert deviceCertAndCACert.crt --key deviceCert.key -h {ENDPOINT} -p 8883 -q 1 -t {topic} -I anyclientID --tls-version tlsv1.2 -m '{payload}' -d"
    print (cmd)
    pub = subprocess.getoutput(cmd)
    print (pub)
    
    
    loopcount = loopcount+1
    time.sleep(5)