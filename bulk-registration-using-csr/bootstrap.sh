#!/bin/bash

# Log file
log_file="bootstrap.log"

# Create log file if it doesn't exist
[ ! -f "$log_file" ] && touch "$log_file"

# Function to print success message and log
print_success() {
    local message="$1"
    echo "Success: $message"
    echo "$(date) - Success: $message" >> "$log_file"
}

# Function to print error message, log, and exit
print_error_and_exit() {
    local message="$1"
    echo "Error: $message"
    echo "$(date) - Error: $message" >> "$log_file"
    exit 1
}

# Prompt for AWS account
read -p "Enter your AWS account ID: " aws_account
if [[ -z "$aws_account" ]]; then
    print_error_and_exit "AWS account ID is required."
fi

# Prompt for AWS region
read -p "Enter the AWS region: " aws_region
if [[ -z "$aws_region" ]]; then
    print_error_and_exit "AWS region is required."
fi

# Set AWS account and region
AWS_ACCOUNT_ID="$aws_account"
AWS_DEFAULT_REGION="$aws_region"

#Create variable for bucket name
BUCKET_NAME=iotcorebulkregistrationtaskbucket${AWS_ACCOUNT_ID}

#Create the Amazon S3 bucket for the bulk registration task
#US EAST 1 is my default location, change as needed 
aws s3api create-bucket \
	--bucket "$BUCKET_NAME" \
	--region us-east-1 \
	--acl private && print_success "S3 bucket created successfully - us-east-1" || print_error_and_exit "Failed to create S3 bucket - (Hint check your Global S3 region)"

# Create Thing Types
aws iot create-thing-type --thing-type-name ThingTypeA && print_success "ThingTypeA created" || print_error_and_exit "Failed to create ThingTypeA"
aws iot create-thing-type --thing-type-name ThingTypeB && print_success "ThingTypeB created" || print_error_and_exit "Failed to create ThingTypeB"
aws iot create-thing-type --thing-type-name ThingTypeC && print_success "ThingTypeC created" || print_error_and_exit "Failed to create ThingTypeC"
aws iot create-thing-type --thing-type-name ThingTypeD && print_success "ThingTypeD created" || print_error_and_exit "Failed to create ThingTypeD"

# Create Thing Groups
aws iot create-thing-group --thing-group-name CustomerA && print_success "CustomerA created" || print_error_and_exit "Failed to create CustomerA"
aws iot create-thing-group --thing-group-name CustomerB && print_success "CustomerB created" || print_error_and_exit "Failed to create CustomerB"
aws iot create-thing-group --thing-group-name CustomerC && print_success "CustomerC created" || print_error_and_exit "Failed to create CustomerC"
aws iot create-thing-group --thing-group-name unclaimed && print_success "Unclaimed created" || print_error_and_exit "Failed to create Unclaimed"

# Create Billing Group
aws iot create-billing-group --billing-group-name AnyCompany && print_success "Billing group AnyCompany created" || print_error_and_exit "Failed to create AnyCompany"

#Create anything policy for all things to be provisioned (in this simulation no thing will connect AWS IoT core, however the policy create here follows the best practices)
# Create JSON document any_type_thing_policy.json
policy_content=$(cat <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Condition": {
				"Bool": {
					"iot:Connection.Thing.IsAttached": "true"
				}
			},
			"Effect": "Allow",
			"Action": "iot:Connect",
			"Resource": "arn:aws:iot:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:client/\${iot:Connection.Thing.ThingName}"
		},
		{
			"Effect": "Allow",
			"Action": "iot:Publish",
			"Resource": "arn:aws:iot:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:topic/AnyCompany/\${iot:Connection.Thing.ThingName}/telemetry"
		},
		{
			"Effect": "Allow",
			"Action": "iot:Subscribe",
			"Resource": "arn:aws:iot:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:topicfilter/AnyCompany/\${iot:Connection.Thing.ThingName}/telemetry"
		},
		{
			"Effect": "Allow",
			"Action": "iot:Receive",
			"Resource": "arn:aws:iot:${AWS_DEFAULT_REGION}:${AWS_ACCOUNT_ID}:topic/AnyCompany/\${iot:Connection.Thing.ThingName}/telemetry"
		}
	]
}
EOF
)

# Check if any_type_thing_policy.json exists
if [ -f "any_type_thing_policy.json" ]; then
    read -p "any_type_thing_policy.json already exists. Do you want to overwrite it? (y/n): " overwrite_confirmation
    if [ "$overwrite_confirmation" != "y" ]; then
        echo "Aborting to prevent overwriting."
        exit 1
    fi
fi

echo "$policy_content" > any_type_thing_policy.json && print_success "any_type_thing_policy.json created" || print_error_and_exit "Failed to create any_type_thing_policy.json"

# Create policy for all things to be provisioned
aws iot create-policy \
    --policy-name AnyTypeThing-policy \
    --policy-document file://any_type_thing_policy.json

# Check the exit status of the last command
if [ $? -eq 0 ]; then
    print_success "Policy 'AnyTypeThing-policy' created successfully."
else
    print_warning "Failed to create policy 'AnyTypeThing-policy'. Continuing script execution."
fi



# Creating the bulk registration task role
#This role is assumed by the AWS IoT Core task running your provisioning template. 
#The minimum trust and permissions for the role will vary depending on your provisioning template, 
#example if your provisioning does not include adding thing to a Billing group, you don't need the **"iot:AddThingToBillingGroup"** action. 
#To facilitate the scoping of a correct policy, AWS provides a managed [policy for Thing Registration](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSIoTThingsRegistration.html), 
#we recommend you start from that one and trim it to the least needed privileges for your provisioning method. 

#For this example project you can just execute the commands below as is:
# Creating the bulk registration task role
# Execute the command to create the role and capture the role ARN
role_arn=$(aws iam create-role \
    --role-name iot-core-provisioning-role \
    --assume-role-policy-document file://aws_iot_trust_policy.json \
    --description "Role for IoT Core Provisioning" \
    --query 'Role.Arn' \
    --output text 2>&1)

# Check if the role creation was successful
if [ $? -eq 0 ]; then
    print_success "IoT Core Provisioning Role created. Role ARN: $role_arn"
else
    print_error_and_exit "Failed to create IoT Core Provisioning Role. Error: $role_arn"
fi

# Finally, we need to attach a permission to the role which allows access to the S3 bucket
# Create inline policy to allow full access to the S3 buckets
aws iam put-role-policy \
    --role-name iot-core-provisioning-role \
    --policy-name S3BucketAccessPolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": "arn:aws:s3:::'"${BUCKET_NAME}"'/*"
            }
        ]
    }'

if [ $? -eq 0 ]; then
    print_success "Inline policy 'S3FullAccessPolicy' added to allow full access to S3 bucket ${BUCKET_NAME}."
else
    print_error_and_exit "Failed to add inline policy for S3 full access."
fi

# Set the role ARN variable
PROVISIONING_ROLE_ARN="$role_arn"

# Attach the policy to the role, this policy is for IoT registration things
aws iam attach-role-policy \
    --role-name iot-core-provisioning-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSIoTThingsRegistration && print_success "Policy attached to IoT Core Provisioning Role" || print_error_and_exit "Failed to attach policy to IoT Core Provisioning Role"

# Function to save simulation variables to JSON file
save_simulation_variables() {
    local json_file="simulation_variables.json"
    local json_content="{\"PROVISIONING_ROLE_ARN\":\"$PROVISIONING_ROLE_ARN\",\"BUCKET_NAME\":\"$BUCKET_NAME\"}"

    echo "$json_content" > "$json_file"

    if [ $? -eq 0 ]; then
        print_success "Simulation variables saved to $json_file"
    else
        print_error_and_exit "Failed to save simulation variables to $json_file"
    fi
}

# Check if the JSON file exists, create it if not
if [ ! -f "simulation_variables.json" ]; then
    touch "simulation_variables.json"
fi

# Save simulation variables to JSON file
save_simulation_variables


print_success "Bootstrap complete. Check bootstrap.log for more details"
#END