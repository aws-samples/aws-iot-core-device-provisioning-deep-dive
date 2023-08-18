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

#Simulation of an MQTT client using AWS IoT Device SDK for Python V2 PUBSUB sample.
#This script simulates a client that connects to an AWS IoT Core endpoint.
#Initiates a provisioning flow, and publishes random data to a topic.
#Runs process on background and restarts it if it fails.

# Dependencies
import subprocess
import time
import os

def run_command_with_logging(command, log_file_path):
    while True:
        try:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)  # Create the logs directory if it doesn't exist
            
            with open(log_file_path, 'a') as log_file:
                subprocess.run(command, check=True, stdout=log_file, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            with open(log_file_path, 'a') as log_file:
                log_file.write(f"Command failed with exit code: {e.returncode}\n")
                log_file.write("Restarting in 5 seconds...\n")
            time.sleep(5)

def run_command():
    endpoint = os.environ.get("IOT_ENDPOINT")
    client_id = os.environ.get("SERIAL_NUMBER")
    organization = os.environ.get("ORGANIZATION")
    topic = f"/{organization}/{client_id}/telemetry"

    if not endpoint or not client_id or not topic:
        print("Missing environment variables. Please set IOT_ENDPOINT, SERIAL_NUMBER, or ORGANIZATION")
        return
    
    print(f"Building MQTT client for {endpoint} with client id {client_id} and topic {topic}")
    
    # AWS IoT Core PUBSUB sample command
    command = [
        "python3", "/opt/iot_client/aws-iot-device-sdk-python-v2/samples/pubsub.py",
        "--endpoint", endpoint,
        "--cert", "/opt/iot_client/certs/deviceCert.crt",
        "--key", "/opt/iot_client/certs/deviceCert.key",
        "--client_id", client_id,
        "--topic", topic,
        "--message", '{"msg":"test"}',
        "--count", "0"
    ]

    # Log file path
    log_file_path = "/opt/iot_client/logs/mqtt_client.log"
    
    # Run process in the background with logging
    run_command_with_logging(command, log_file_path)

if __name__ == "__main__":
    run_command()