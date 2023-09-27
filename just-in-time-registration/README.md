## Just in time registration(JITR)

### Introduction
In this section you will execute every step to configure AWS IoT Core for JITR, and run a simulation fleet using JITR. Note this is an educational project, and the example and samples utilized here should not be implemented into projects without changes. For more information go to [Just in time registration documentation page](https://docs.aws.amazon.com/iot/latest/developerguide/auto-register-device-cert.html). 

Just in time registration has a dependency on using a private certificate authority(CA). The Private CA must be registered in the AWS IoT Core account and region where you wish to provision your devices for. In addition to that you must make sure the device attempting to connect to AWS IoT Core for the first time has a Unique device certificate, signed by the Private CA (or chain) which you registered in AWS IoT Core. 

The flow diagram below explains each action that happens in a JITR provisioning flow, note that some of those are not part of the flow itself, but actions that have to be done by a security administrator and manufacturing prior to the first connection. 

**JITP vs JITR**
Before diving deeper on JITR, it is important that you also familiarize yourself with Just-In-Time-Provisionig.
The JITR flow relies on an AWS Lambda function to provision AWS IoT resources. Because a Lambda function is used in this method, JITR is a much more flexible provisioning method than [JITP](https://github.com/aws-samples/aws-iot-core-device-provisioning-deep-dive/tree/main/just-in-time-provisioning). However, JITP is a much streamlined provisioning method which does not require an External lambda function to be designed, and it should be used if it meets your application requirements. 
A common use case to use JITR instead of JITP, is when you may want to enrich or check your device provisioning flow against another data source before the certificate is activated, e.g. Database table.  

### JITR provisioning flow
Below is the flow diagram which the JITR methods uses. Notice that in this flow relies on a registered certificate authority and a Unique device/client certificate that is signed by it. In this example you will also can make use of other AWS service or even external APIs for extra validation, we will be exemplifying with DynamoDB. 

![JITR flow](/assets/jitr-flow.png)

### Pre-requisites 

 * AWS account 
 * AWS cloud9 or AWS CloudShell, with the relevant permissions to execute AWS IoT actions, or your preferred IDE with the relevant access.
 * AWS Command line interface (AWS CLI), installed and configured.
 * IAM role creation permissions (You will need to create IAM roles).
 * Secret key for boto3 commands
 * Install Docker compose on your environment

### Clone the repository 

Clone the repository and navigate to the just in time registration directory.
```
git clone https://github.com/aws-samples/aws-iot-core-device-provisioning-deep-dive.git
cd aws-iot-core-device-provisioning-deep-dive/just-in-time-registration
```
**This will be your work directory from this point**

### Understanding the Just in time registration AWS Lambda function.
During the provisioning flow the Lambda function will be invoked by an [AWS IoT Core rule](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rules.html). The invocation will pass information about the registration event which is published to a reserved topic, **$aws/events/certificates/registered/caCertificateId**, where the caCertificateId is the CA that issued the client certificate. The message published to this topic has the following structure: 

```json
{
        "certificateId": "certificateId",
        "caCertificateId": "caCertificateId",
        "timestamp": timestamp,
        "certificateStatus": "PENDING_ACTIVATION",
        "awsAccountId": "awsAccountId",
        "certificateRegistrationTimestamp": "certificateRegistrationTimestamp"
}
```
This message is published to the reserved topic Certificate anytime an unregistered certificate signed by a Certificate Authority registered in AWS IoT Core attempts to connect. The certificates will be auto registered (if "auto-registration" on) and will remain on a **pending_activation** status until the provisioning flow is completed. In the case of JITR it will be completed by a Lambda function that can perform actions on AWS IoT Core.

###Designing an AWS IoT Core JITR Lambda Function.
When designing a Lambda function for JITR you must follow the same [best practices of designing any Lambda function](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html). Since JITR leverages a Private Certificate Authority, and uniquely generate and signed client certificate, it is a common practice to leverage the information in the client certificate during the creation of AWS IoT Resources, by extracting a serial number from the certificate and assigning it to an attribute on the AWS IoT Core registry for example. 

### Designing the JITR Lambda function
In the example Lambda function used in this simulation, you will make use of a [Python Crypto library](https://pypi.org/project/pycrypto/) to extract the Certificate Serial Number and Distinguished name information from the provided client certificate. In order properly deploy this Lambda function with its dependencies, you can use the [AWS ToolKit for VS code](https://aws.amazon.com/visualstudio/) or [AWS Cloud9](https://aws.amazon.com/cloud9/) which already come with toolkit integrated. Optionally you can also work with [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html). **In this example I will be using an AWS Lambda Layer.**

In the directory **/jitr-lambda-example** you can find the **lambda_function.py** which was designed with Python **boto3** and **pyOpenSSL** libraries. You will also find the necessary resources to create the custom Lambda Layer.

Before deploying the lambda function, we must create a Lambda execution role. [Read about how to scope AWS Lambda execution roles](https://docs.aws.amazon.com/lambda/latest/operatorguide/least-privilege.html#). For this particular role, we need to execute actions in AWS IoT Core, AWS CloudWatch and AWS DynamoDB. In a production environment you must scope your role permission down to the least needed privileges, which will be reflected by the actions executed in your Lambda function. For this particular example, you will find a policy **/jitr-lambda-function/lambda-execution-role-policy.json** that has been designed with the least privileges for the example **lambda_function.py**. Keep in mind that if you decide to customize the example for testing, you must make sure the policy meets your requirements.

**Please modify where you see < >.**

**Creating execution role**
Run the following commands to create the Lambda execution role, **save the role ARN**:
```
aws iam create-role \
  --role-name jitr-example-lambda-role \
  --assume-role-policy-document file://aws_lambda_trust_policy.json 
```
Now create a Policy for the role and attach to it:
```
aws iam create-policy \
  --policy-name jitr-example-lambda-role-policy \
  --policy-document file://jitr_example_lambda_role_policy.json
```
Copy the policy ARN from response and use on the next command:
```
aws iam attach-role-policy \
  --policy-arn arn:aws:iam::<ACCOUNT ID>:policy/jitr-example-policy \
  --role-name jitr-example-lambda-role
  ```
**Creating custom Lambda Layer**
Run the following command to create the necessary custom lambda layer, **Save the Layer VERSION ARN**:
```
aws lambda publish-layer-version \
  --layer-name jitr_example_lambda_layer \
  --compatible-runtimes "python3.7" \
  --zip-file fileb://jitr_example_lambda_layer.zip
```
**Creating the jitr-example-lambda-function**
Now create the lambda-function:
```
zip lambda_function.py.zip lambda_function.py

aws lambda create-function \
  --function-name jitr-example-lambda \
  --role arn:aws:iam::<ACCOUNT ID>:role/jitr-example-lambda-role \
  --zip-file fileb://lambda_function.py.zip \
  --runtime python3.7 \
  --handler lambda_function.lambda_handler \
  --layers arn:aws:lambda:<REGION>:<ACCOUNT ID>:layer:jitr_example_lambda_layer:1 \
  --timeout 60
```

### Defining the IoT policy for provisioned devices
There are many strategies to accomplish best practices when creating IoT policies to be use by fleets of devices. Similar to an IAM policy, IoT policies also support policy variables, and that very efficient way to scale securely. 
In the demonstration policy below you will scope a policy with the least privileges for this project. 

```json
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
		"Resource": "arn:aws:iot:<YOUR-REGION>:<ACCOUNT-ID>:client/${iot:Connection.Thing.ThingName}"
	  },
	  {
		"Effect": "Allow",
		"Action": "iot:Publish",
		"Resource": "arn:aws:iot:<YOUR-REGION>:<ACCOUNT-ID>:topic/AnyCompany/${iot:Connection.Thing.ThingName}/telemetry"
	  },
	  {
		"Effect": "Allow",
		"Action": "iot:Subscribe",
		"Resource": "arn:aws:iot:<YOUR-REGION>:<ACCOUNT-ID>:topicfilter/AnyCompany/${iot:Connection.Thing.ThingName}/telemetry"
	  },
	  {
		"Effect": "Allow",
		"Action": "iot:Receive",
		"Resource": "arn:aws:iot:<YOUR-REGION>:<ACCOUNT-ID>:topic/AnyCompany/${iot:Connection.Thing.ThingName}/telemetry"
	  }
	]
  }
```
The **AnyTypeThing_policy_document.json** has already been created in this directory, Please modify where you see < >.

Then run the command below: 
```
aws iot create-policy --policy-name AnyTypeThing-policy --policy-document file://any_type_thing_policy.json
```
### Creating types, groups and billing groups. 
You also need to create resources in which thing will be provisioned. In this example the lambda function doe snot create Types or Groups, it only allocates things to it, so you must either pre create them or re-configure the function to do so. 

Run the commands below:

For the thing type.
```
aws iot create-thing-type --thing-type-name AnyType
```

For the Groups, create a Parent group.
```
aws iot create-thing-group --thing-group-name AnyCompany
```

Then create three groups and add them as child groups of AnyCompany.
```
aws iot create-thing-group --thing-group-name Dev --parent-group-name AnyCompany
aws iot create-thing-group --thing-group-name Prod --parent-group-name AnyCompany
aws iot create-thing-group --thing-group-name unclaimed --parent-group-name AnyCompany
```
Finally, create the billing group.
```
aws iot create-billing-group --billing-group-name AnyCompany
```
### Creating the IoT Rule for JITR
The last resource that must be in place before your Private CA and the simulation is an [AWS IoT rule](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rules.html). The Rule subscription will listen to the **$aws/events/certificates/registered/caCertificateId** topic, and trigger the JITR example lambda function anytime a new registration is published. 
To create the AWS IoT Rule inspect the **jitr_iot_rule.json**, replace where you see < REGION >:< ACCOUNT ID > and run the command below:

```
aws iot create-topic-rule \
  --rule-name jitr_iot_rule \
  --topic-rule-payload file://jitr_iot_rule.json
```

### Registering a Private CA 
 Next is registering the Private CA authority which will be used to invoke a registration by the template. OpenSSL is required for the following steps, make sure you have installed and configured. **Note**: all the OpenSSL commands used in this project are for educational purposes only, make sure you understand your use case, and have done the necessary work to select the correct signing algorithm. 

* **Create a certificate to be used as Private CA** 
   Run the following OpenSSL commands, note that you will be using the **rootCA_openssl.conf** which makes sure your CA is adhering to the minimal requirements. 

      ```    
      openssl genrsa -out rootCA.key 2048

      openssl req -new -sha256 -key rootCA.key -nodes -out rootCA.csr -config rootCA_openssl.conf
      ```
* **Fill the signing form**. 
   Feel free to use any value you like, but fill all fields, as the Certificate DN is a way to identify Certificates. An example below: 

   Country Name [ ]:**US**

   State [ ]:**CO**
   
   City [ ]:**Denver**
   
   Organization [ ]:**AnyCompany**
   
   Organization Unit [ ]:**All**
   
   Common Name [ ]:**JITR-IoT-Devices-Root-CA**


* **Now sign the Certificate with the key**
      ```
      openssl x509 -req -days 3650 -extfile rootCA_openssl.conf -extensions v3_ca -in rootCA.csr -signkey rootCA.key -out rootCA.pem
      ```

* **Create verification code certificate**.
   The verificationCert.pem file we get from this step will be used when we register the CA certificate. This is necessary step which protects the registration, the service or user registering must be able to acquire a verification code. 
   Execute the following commands:

    ```
    aws iot get-registration-code
    ```
    **Save this code for the next step**
       
    ```
    openssl genrsa -out verificationCert.key 2048

    openssl req -new -key verificationCert.key -out verificationCert.csr 
    ```

    **Using the registration code, now you need to set the Common Name field of the certificate with the registration code:**
      
    **Common Name (e.g. server FQDN or YOUR name) []: < REGISTRATION-CODE>**

* **Now sign the Certificate with the key**
    ```
    openssl x509 -req -in verificationCert.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out verificationCert.pem -days 500 -sha256
    ```

* **Register the CA certificate**
   This is the final step of the registration, there are a few modes in which a CA can be registered, to understand that better please read [Manage your CA certificates](https://docs.aws.amazon.com/iot/latest/developerguide/manage-your-CA-certs.html).
   In the example below we are registering for a single account, active and with auto-registration on. The auto-registration will register a certificate on PENDING_ACTIVATIOn state and publish the event to the **$aws/events/certificates/registered/caCertificateId** topic.

      ```
      aws iot register-ca-certificate --ca-certificate file://rootCA.pem --verification-cert file://verificationCert.pem --set-as-active --allow-auto-registration 
      ```
    If you navigate to **AWS IoT Core -> Security -> CA certificates** you will see that your CA has been registered as the example below.

    ![registered-ca](/assets/registered-ca.png)

### Testing the provisioning template and deploying a simulation fleet 

For this next step you will be creating a Simulation fleet using Docker containers that simulate an IoT client device, using the [AWS IoT V2 SDK for Python](https://github.com/aws/aws-iot-device-sdk-python-v2).

   **Important** This simulation is using a simple x509 certificate and not a "chain certificate", in this use case make sure no other Private CA with the same subject name is present in IoT Core.

   The Diagram below describes what you are about to do.
   * The simulation.py will build a container Image based on the present Dockerfile.
   * The simulation will use the provided arguments (endpoint and FleetSize) to create docker containers.
   *  In the background the Signing_service.py will start (A dynamo DB table with the serialNumbers will be provisioned for the authorization task, The Signing certificate will sign the Device/Client certificates with the serial numbers that will be recorded to the DynamoDB table).**DynamoDb Table for provisioning authorization**. There a many ways in which provisioning can be authorized within a lambda function, you must understand your requirements in order to define that. For this project we will be using an AWS DynamoDB Table that simply stores the Ownership and serial number of devices. When you start the **simulation.py** file below, it will attempt to create a table in DynamoDB, make sure the environment which this simulation is running for has the permissions to do so, the script will request an access key. 
   *  As the containers start, they will self generate unique Certificate Keys, and request the signing_service.py for a CA signature. **Note:** This is an example of how certificates can be signed on a secure and completely isolated network, do not replicate this method without proper understanding of manufacturing with x509 certificates. 
   *  With a signed certificate each container will connect to AWS IoT Core and start the JITP flow, they will then successfully connect and publish messages, on the AnyCompany/serialNumber/telemetry

![deep-dive-jitr.drawio](/assets/deep-dive-jitr.png)

   Simply start the simulation with ENDPOINT and desire Fleet size (Max 20 device change at your own risk!). 

   ```
   Python3 simulation.py -e <YOUR-IOT-CORE-ATS_ENDPOINT> -n <NUMBER-OF-DEVICES> --aws_access_key_id <ACCESS-KEY-ID> --aws_secret_access_key <SECRET-KEY> --region_name <REGION>
   ```

### Troubleshooting 
   * Use the log files. 
      At the time you run the simulation a **/logs** directory will be created with 3 distinct log files, docker_compose.log. Inside the containers Log files are also available, in /opt/iot_client/logs and /opt/cert_signing_service/logs Use those files as references when asking questions on the discussions section.
   * Use docker log command to dig deeper into the specific container failure.  
   * Make use of AWS Cloudwatch by turning on logs in AWS IoT Core. Go to AWS IoT Core -> Settings -> Logs -> Manage logs, Create a log role and for the Log level use Debug. 
   * All provisioning action are tracked by AWS Cloudtral and CLoudWatch, if any error with the provisioning Lambda occur, you be able to identify it by looking for IoT Actions in CloudTrail, and the Lambda logstream in CloudWatch. 
   * Docker compose command fails: Try pip3 install --upgrade docker-compose and pip3 install --upgrade docker

### Next steps
I recommend you explore calls with [AWS IoT Device management - fleet indexing](https://docs.aws.amazon.com/iot/latest/developerguide/iot-indexing.html), using Fleet indexing will allow you to filter device by Groups, Hardware version etc. 

### Cleaning up
   * Delete all create things.
   * Delete all registered certificates. 
   * Delete the Lambda function.
   * Delete the Lambda Layer.
   * Delete the thing policy.
   * Delete the DynamoDB table
   * Terminate any EC2 / Cloud9 Instances that you created for the walkthrough.
  




