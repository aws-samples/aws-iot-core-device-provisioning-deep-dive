
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
import subprocess
import argparse
import time
import socket
import os

#Pass argument into variables usin arparse Lib
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", action="store", required=True, dest="endpoint", help="regional AWS IoT Core AT endpoint")
parser.add_argument("-n", "--fleetsize", action="store", required=True, dest="fleetsize", help="Numbers of device on the simulated fleet")

args = parser.parse_args()
endpoint = args.endpoint
number_of_devices = int(args.fleetsize)

#Define create logs directory function
def create_logs_directory():
    logs_directory = "logs"
    
    if not os.path.exists(logs_directory):
        try:
            os.mkdir(logs_directory)
            print(f"Directory '{logs_directory}' created.")
        except Exception as e:
            print(f"Error creating directory '{logs_directory}': {e}")
    else:
        print(f"Directory '{logs_directory}' already exists.")


#Function to determine Host Ip address (Your host machine must have connectivity)
def get_local_ip():
    try:
        # Create a socket connection to a remote server
        # This will retrieve the local IP address used for the connection
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # Connect to Google's DNS server
            local_ip = s.getsockname()[0]
            return local_ip
    except Exception as e:
        print(f"Error: {e}")
        return None
    
print(f"The endpoint is {endpoint}")
print(f"Deploying fleet of {number_of_devices} devices")

#Function to run python script in background
def run_script_in_background(script_path):
    try:
        process = subprocess.Popen(["python3", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        print(f"Script {script_path} started in the background with PID: {process.pid}")
        return process  # Return the process object
    except Exception as e:
        print(f"Error: {e}")

#Define function to create a docker image
def build_docker_image(image_name, dockerfile_path=".", log_file=None):
    try:
        # Open log file for writing if provided
        log_output = open(log_file, 'a') if log_file else subprocess.PIPE
        
        build_image_process = subprocess.Popen(
            ["docker", "build", "--tag", image_name, dockerfile_path],
            stdout=log_output,
            stderr=log_output
        )
        
        build_image_process.communicate()
        
        if log_file:
            log_output.close()  # Close the log file
        
        print(f"Building Docker image {image_name}")
    except Exception as e:
        print(f"Error building Docker image {image_name}: {e}")

#Define function to create a docker container
def create_docker_container(local_ip, endpoint, n, log_file_path):
    try:
        # Open log file for writing
        with open(log_file_path, "a") as log_file:
            create_container_process = subprocess.Popen(
                ["docker", "run", "-d", "--network", "host", "-e", f"HOST_IP={local_ip}", "-e", f"IOT_ENDPOINT={endpoint}", "--name", f"jitp-iot-client-{n}", "jitp-iot-client-img"],
                stdout=log_file,
                stderr=log_file
            )

            create_container_process.communicate()

            print(f"Creating device{n} - Check log file for details.")
    except Exception as e:
        print(f"Error creating container for device{n}: {e}")

#Main 

#Get script directory path
script_directory = os.path.dirname(os.path.abspath(__file__))

#Create logs directory
create_logs_directory()

#build Container Image
build_docker_image("jitp-iot-client-img", script_directory, "./logs/docker_build.log")

#Get local ip address
local_ip = get_local_ip()

#Run signing_service.py in background
run_signing_service = run_script_in_background("signing_service.py")

for n in range(1,number_of_devices+1):

    create_docker_container(local_ip, endpoint, n, "./logs/docker_run.log")
    #Wait for 5 seconds before starting the next device
    time.sleep(5)


#Kill the signing_service process   
run_signing_service.terminate()
