
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
import os
import logging
import shutil
import sys


#Pass argument into variables usin arparse Lib
try:
    # Pass arguments into variables using argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", action="store", required=True, dest="endpoint", help="regional AWS IoT Core AT endpoint")
    parser.add_argument("-n", "--fleetsize", action="store", required=True, dest="fleetsize", help="Numbers of devices on the simulated fleet")
    
    args = parser.parse_args()
    endpoint = args.endpoint
    number_of_devices = int(args.fleetsize)

    # Continue with your script logic here
    print("Endpoint:", endpoint)
    print("Number of Devices:", number_of_devices)
    
except argparse.ArgumentError as e:
    print("Error:", e)
    print("Please provide the required arguments.")
except ValueError as e:
    print("Error:", e)
    print("Invalid value provided for fleetsize. Please provide a valid integer.")
except Exception as e:
    print("An error occurred:", e)

# Limitation: Check if fleet size exceeds the allowed limit (change this if you would like to go over 20, at your own risk!!!)
MAX_FLEET_SIZE = 20
if number_of_devices > MAX_FLEET_SIZE:
    raise Exception(f"Max FleetSize allowed is {MAX_FLEET_SIZE} devices")

#Define Logger
def logger(name):
    # Create the "logs" directory if it doesn't exist
    logs_directory = "logs"
    if not os.path.exists(logs_directory):
        os.mkdir(logs_directory)

    log_file_path = os.path.join(logs_directory, "simulation.log")

    # Create a logger instance
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set the logger's default level to DEBUG

    # Create a formatter
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Create a file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)  # Set the file handler's level to INFO
    file_handler.setFormatter(formatter)

    # Create a console handler (for printing log messages to the console)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Set the console handler's level to INFO
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

#Define fuction to move rootCA to diretory
def copy_file(source_file_path, destination_directory, stop_on_error=False):
    try:
        # Get the directory of the currently executing script
        script_directory = os.path.dirname(os.path.realpath(__file__))

        # Set the working directory to the script directory
        os.chdir(script_directory)
        print(f"Working directory is now '{script_directory}'.")
        logger.info(f"Working directory is now '{script_directory}'.")

        # Check if the source file exists
        if not os.path.exists(source_file_path):
            error_message = f"Source file '{source_file_path}' not found."
            print(error_message)
            logger.error(error_message)
            if stop_on_error:
                sys.exit(1)  # Stop the script with a non-zero exit code

        # Get the filename from the source path
        file_name = os.path.basename(source_file_path)

        # Construct the destination path in the specified directory
        destination_file_path = os.path.join(destination_directory, file_name)

        # Copy the file to the destination directory
        shutil.copy2(source_file_path, destination_directory)

        print(f"File '{file_name}' copied to '{destination_file_path}'.")
        logger.info(f"File '{file_name}' copied to '{destination_file_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")
        if stop_on_error:
            sys.exit(1)  # Stop the script with a non-zero exit code

#Define create ENV variables
def set_environment_variable(variable_name, value):
    try:
        os.environ[variable_name] = value
        print(f"Set environment variable {variable_name} to {value}")
        logger.info(f"Set environment variable {variable_name} to {value}")
    except Exception as e:
        print(f"Error setting environment variable: {e}")
        logger.error(f"Error setting environment variable: {e}")

#Define function to run docker-compose
def run_docker_compose(command):
    try:
        # Construct the Docker Compose command
        print("Docker compose building deployment....")
        cmd = ['docker', 'compose'] + command.split()

    
        # Open a log file for writing
        with open('docker_compose.log', 'w') as log_file:
            log_file.write(f"Docker Compose command: {' '.join(cmd)}\n")

            # Run the Docker Compose command and capture the output
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Read and log the stdout and stderr in real-time
            for line in process.stdout:
                log_file.write(line)
                logger.info(line.strip())

            for line in process.stderr:
                log_file.write(line)
                logger.info(line.strip())

            # Wait for the process to complete
            process.wait()

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Docker Compose command: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

#Main 
#Logger
logger = logger("simulation")

#Check if the endpoint is empty
print(f"The endpoint is {endpoint}")
print(f"Deploying fleet of {number_of_devices} devices")

#Create IOT_ENDPOINT Variable
set_environment_variable('IOT_ENDPOINT', endpoint)

#Copy rootCA.pem and rootCA.key to /cert_signing_service
copy_file('rootCA.pem', './cert_signing_service/certs', stop_on_error=True)
copy_file('rootCA.key', './cert_signing_service/certs', stop_on_error=True)

#run docker-compose
run_docker_compose(f"up -d --scale iot-client={number_of_devices}")
