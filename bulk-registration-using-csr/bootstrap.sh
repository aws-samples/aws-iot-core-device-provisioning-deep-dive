#!/bin/bash

# Log file
log_file="bootstrap.log"

# Create log file if it doesn't exist
touch "$log_file"

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
export AWS_ACCOUNT_ID="$aws_account"
export AWS_DEFAULT_REGION="$aws_region"

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
aws iot create-billing-group --billing-group-name AnyCompany && print_success "AnyCompany created" || print_error_and_exit "Failed to create AnyCompany"

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

echo "$policy_content" > any_type_thing_policy.json && print_success "any_type_thing_policy.json created" || print_error_and_exit "Failed to create any_type_thing_policy.json"

#Create policy for all things to be provisioned
aws iot create-policy \
    --policy-name AnyTypeThing-policy \
    --policy-document file://any_type_thing_policy.json

# Creating the bulk registration task role
#This role is assumed by the AWS IoT Core task running your provisioning template. 
#The minimum trust and permissions for the role will vary depending on your provisioning template, 
#example if your provisioning does not include adding thing to a Billing group, you don't need the **"iot:AddThingToBillingGroup"** action. 
#To facilitate the scoping of a correct policy, AWS provides a managed [policy for Thing Registration](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSIoTThingsRegistration.html), 
#we recommend you start from that one and trim it to the least needed privileges for your provisioning method. 

#For this example project you can just execute the commands below as is:

aws iam create-role \
    --role-name iot-core-provisioning-role \
    --assume-role-policy-document file://aws_iot_trust_policy.json \
    --description "Role for IoT Core Provisioning" && print_success "IoT Core Provisioning Role created" || print_error_and_exit "Failed to create IoT Core Provisioning Role"

aws iam attach-role-policy \
    --role-name iot-core-provisioning-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSIoTThingsRegistration && print_success "Policy attached to IoT Core Provisioning Role" || print_error_and_exit "Failed to attach policy to IoT Core Provisioning Role"