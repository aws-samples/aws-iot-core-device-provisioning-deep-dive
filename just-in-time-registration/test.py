import json
import uuid

def generate_serial_numbers_file(file_path, num_serial_numbers):
    serial_numbers = [uuid.uuid4().int for _ in range(num_serial_numbers)]

    data = {"serial_numbers": serial_numbers}

    try:
        with open(file_path, "w") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Serial numbers file generated at {file_path}")
    except Exception as e:
        print(f"Error generating serial numbers file: {e}")

# Usage example:
file_path = "serial_numbers.json"
num_serial_numbers = 10  # Set the number of serial numbers you want to generate
generate_serial_numbers_file(file_path, num_serial_numbers)