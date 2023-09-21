## Just in time registration(JITR)

### Introduction
In this section you will execute every step to configure AWS IoT Core for JITR, and run a simulation fleet using JITR. Note this is an educational project, and the example and samples utilized here should not be implemented into projects without changes. For more information go to [Just in time registration documentation page](https://docs.aws.amazon.com/iot/latest/developerguide/auto-register-device-cert.html). 

Just in time registration has a dependency on using a private certificate authority(CA). The Private CA must be registered in the AWS IoT Core account and region where you wish to provision your devices for. In addition to that you must make sure the device attempting to connect to AWS IoT Core for the first time has a Unique device certificate, signed by the Private CA (or chain) which you registered in AWS IoT Core. 

The flow diagram below explains each action that happens in a JITR provisioning flow, note that some of those are not part of the flow itself, but actions that have to be done by a security administrator and manufacturing prior to the first connection. 

**JITP vs JITR**
Before diving deeper on JITR, it is important that you familiarize yourself with Just-In-Time-Provisionig.
The JITR flow relies on an AWS Lambda function to complete the flow and provision AWS IoT resources. Because a Lambda function is used in this method, JITR is a much more flexible provisioning method than [JITP](https://github.com/aws-samples/aws-iot-core-device-provisioning-deep-dive/tree/main/just-in-time-provisioning). However, JITP is a much streamlined provisioning method which does not require an External lambda function to be designed, and it should be used if it meets your application requirement. 
A common use case to use JITR instead of JITP, is when you may want to enrich or check your device provisioning flow against another data source before the certificate is activated, e.g. Database table.  

### JITR provisioning flow
Below is the flow diagram which the JITR methods uses. Notice that in this flow relies on a registered certificate authority and a Unique device/client certificate that is signed by it. In this example you will also can make use of other AWS service or even external APIs for extra validation, we will be exemplifying with DynamoDB. 

![JITR flow](/assets/jitr-flow.png)

### Pre-requisites 

 * AWS account 
 * AWS cloud9 or AWS CloudShell , with the relevant permissions to execute AWS IoT actions, or your preferred IDE with the relevant access.
 * AWS Command line interface (AWS CLI), installed and configured.
 * IAM role creation permissions (You will need to create IAM roles).
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
In the example Lambda function used in this simulation, we will make use of a [Python Crypto library](https://pypi.org/project/pycrypto/) to extract the Certificate Serial Number and Distinguished name information from the provided client certificate. In order properly deploy this Lambda function with its dependencies, you can use the [AWS ToolKit for VS code](https://aws.amazon.com/visualstudio/) or [AWS Cloud9](https://aws.amazon.com/cloud9/) which already come with toolkit integrated. Optionally you can also work with [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html). **In this example I will be using an AWS Lambda Layer and the example files in this repository.**
In the directory **/jitr-lambda-example** you can find the **lambda_function.py** which was designed with Python **boto3** and **pyOpenSSL** libraries. You will also find the necessary resources to create the custom Lambda Layer.

Before deploying the lambda function, we must create a Lambda execution role. [Read about how to scope AWS Lambda execution roles](https://docs.aws.amazon.com/lambda/latest/operatorguide/least-privilege.html#). For this particular role, we need to execute action in AWS IoT Core, AWS CloudWatch and AWS DynamoDB. In a production environment you must scope your role permission down to the least needed privileges, which will be reflected by the actions executed in your Lambda function. For this particular example, you will find a policy **/jitr-lambda-function/lambda-execution-role-policy.json** that has been designed with the least privileges for the example **lambda_function.py**. Keep in mind that if you decide to customize the example for testing, you must make sure the policy meets your requeriments.

Run the following commands to create the Lambda execution role:

```
```


### Creating a DynamoDb Table for provisioning authorization


```
aws dynamodb
```

service in order to customize how your IoT things will be provisioned and registered. Actions such as creating a thing, adding a thing to a group and attach a policy are examples of action executed accordingly to the template. Read the [provisioning templates](https://docs.aws.amazon.com/iot/latest/developerguide/provision-template.html) section on the documentation page to learn more. 

For this test you will start with the example below. The provisioning template is the start point when developing for JITP, what you define in the template will influence how your authorization and cloud infrastructure needs to be setup. In this example the **Parameters** are being extracted from the device certificate itself. When you sign a device certificate you can add fields such as CommonName, Company, country etc. Those parameters will be used to register you IoT thing, AWS IoT defines the following:

AWS::IoT::Certificate::Country

AWS::IoT::Certificate::Organization

AWS::IoT::Certificate::OrganizationalUnit

AWS::IoT::Certificate::DistinguishedNameQualifier

AWS::IoT::Certificate::StateName

AWS::IoT::Certificate::CommonName

AWS::IoT::Certificate::SerialNumber (Given to the certificate by the CA, this is good candidate for the IoT:ThingName or Thing.Attribute)

AWS::IoT::Certificate::Id (**AWS managed**)

**Very important!** When defining a parameter, a "Default" value can be provided in case the certificate does not contain information on the defined field. If you do not use a default value, the defined field which does not receive a value from the certificate will force the registration job to fail, the certificate is deemed unsafe. 

In the **Resources** segment we define how and where the parameters are used. Finally, you define the certificate to be registered and the policy which will be attached to it. 
Provisioning templates can solve many cases, be sure to explore the documentation page for more examples. 

```json
{
  "Parameters": {
    "AWS::IoT::Certificate::Id": {
      "Type": "String"
    },
    "AWS::IoT::Certificate::CommonName": {
      "Type": "String"
    },
    "AWS::IoT::Certificate::SerialNumber": {
      "Type": "String"
    },
    "AWS::IoT::Certificate::DistinguishedNameQualifier": {
      "Type": "String"
    },
    "AWS::IoT::Certificate::OrganizationalUnit": {
      "Type": "String",
      "Default": "unclaimed"
    },
    "AWS::IoT::Certificate::Organization": {
      "Type": "String"
    }
  },
  "Resources": {
    "thing": {
      "Type": "AWS::IoT::Thing",
      "Properties": {
        "ThingName": {
          "Ref": "AWS::IoT::Certificate::SerialNumber"
        },
        "AttributePayload": {
          "hardwareVersion": {
            "Ref": "AWS::IoT::Certificate::CommonName"
          },
          "serialNumber": {
            "Ref": "AWS::IoT::Certificate::SerialNumber"
          },
          "provisioning": "JITP",
          "softwareVersion": "SW-100",
          "CA": "IoT-Device-RootCA"
        },
        "ThingTypeName": {
          "Ref": "AWS::IoT::Certificate::DistinguishedNameQualifier"
        },
        "ThingGroups": [
          {
            "Ref": "AWS::IoT::Certificate::OrganizationalUnit"
          }
        ],
        "BillingGroup": {
          "Ref": "AWS::IoT::Certificate::Organization"
        }
      },
      "OverrideSettings": {
        "AttributePayload": "REPLACE",
        "ThingTypeName": "REPLACE",
        "ThingGroups": "REPLACE"
      }
    },
    "certificate": {
      "Type": "AWS::IoT::Certificate",
      "Properties": {
        "CertificateId": {
          "Ref": "AWS::IoT::Certificate::Id"
        },
        "Status": "ACTIVE"
      }
    },
    "policy": {
      "Type": "AWS::IoT::Policy",
      "Properties": {
        "PolicyName": "AnyTypeThing-policy"
      }
    }
  }
}
```
The provisioning template above has already been created and added to the directory, **jitp-provisiong-template.json**. Feel free to make changes, but be aware the next steps will work with the Provisioning template. 

### Creating types, groups and billing groups. 
You may have noticed that the provisioning template tries to add Things to Types and Groups, you will create a few you can work with. If those groups and types are not already pre created the template will fail.

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
### Defining the IoT policy for provisioned devices
There are many strategies to accomplish best practices when creating IoT policies to be use by fleets of devices. Similar to an IAM policy, IoT policies also support policy variables, and that very efficient way to scale securely. 
In the demonstration policy below you will scope a policy with the least privileges for this educational project. 

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

 ### Creating the JITP provisioning role
 This role is assumed by the AWS IoT Core task running your provisioning template. The minimum trust and permissions for the role will vary depending on your provisioning template, example if your provisioning does not include adding thing to a Billing group, you don't need the **"iot:AddThingToBillingGroup"** action. To facilitate the scoping of a correct policy, AWS provides a managed [policy for Thing Registration](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSIoTThingsRegistration.html), we recommend you start from that one and trim it to the least needed privileges for your provisioning method. 

For this example project you can just execute the commands below as is:

    ```
    aws iam create-role \
        --role-name iot-core-provisioning-role \
        --assume-role-policy-document file://aws_iot_trust_policy.json \
        --description "Role for IoT Core Provisioning"    
    ```
    **Important**, save the role **ARN**, you will use on the next section.
    ```
    aws iam attach-role-policy \
        --role-name iot-core-provisioning-role \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSIoTThingsRegistration
    ```

### Creating the provisioning template.
Now that you have all resource in place and understand the template, you can execute the command below to create the template. 
   **Note**: If you did not save the Role ARN, got to IAM -> Roles, search for iot-core-provisionign-role, select and copy the ARN.

     
    ```
    aws iot create-provisioning-template \
        --template-name jitp-provisioning-template \
        --enabled \
        --type JITP \
        --provisioning-role-arn arn:aws:iam::<YOUR-ACCOUNT-ID>:role/iot-core-provisioning-role \
        --template-body file://jitp_provisioning_template.json 
    ```

 Any update to the provisioning template can be done using [update-provisioning-template](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/iot/update-provisioning-template.html) or [create-provisioning-template](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/iot/create-provisioning-template-version.html), in case you like to keep track of versions.

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
   *  In the background the Signing_service.py will start.
   *  As the containers start, they will self generate unique Certificate Keys, and request the signing_service.py for a CA signature. **Note:** This is an educational example of how certificates can be signed on a secure and completely isolated network, do not replicate this method without proper understanding of manufacturing with x509 certificates. 
   *  With a signed certificate each container will connect to AWS IoT Core and start the JITP flow, they will then successfully connect and publish messages, on the AnyCompany/serialNumber/telemetry

![deep-dive-jitr.drawio](/assets/deep-dive-jitp.png)

   Simply start the simulation with ENDPOINT and desire Fleet size (Max 20 device change at your own risk!). 

   ```
   Python3 simulation.py -e <YOUR-IOT-CORE-ATS_ENDPOINT> -n <NUMBER-OF-DEVICES>
   ```

### Troubleshooting 
   * Use the log files. 
      At the time you run the simulation a **/logs** directory will be created with 3 distinct log files, docker_compose.log. Inside the containers Log files are also available, in /opt/iot_client/logs and /opt/cert_signing_service/logs Use those files as references when asking questions on the discussions section.
   * Use docker log command to dig deeper into the specific container failure.  
   * Make use of AWS Cloudwatch by turning on logs in AWS IoT Core. Go to AWS IoT Core -> Settings -> Logs -> Manage logs, Create a log role and for the Log level use Debug. 
   * All provisioning action are tracked by AWS Cloudtrail, if any error with the provisioning template occur, you be able to identify it by looking for the iot-provisioning identification on the event.  
   * Docker compose command fails: Try pip3 install --upgrade docker-compose and pip3 install --upgrade docker

### Next steps
I recommend you explore calls with [AWS IoT Device management - fleet indexing](https://docs.aws.amazon.com/iot/latest/developerguide/iot-indexing.html), using Fleet indexing will allow you to filter device by Groups, Hardware version etc. 

### Cleaning up
   * Delete all create things.
   * Delete all registered certificates. 
   * Delete the Provisioning template.
   * Delete the thing policy.
   * Terminate any EC2 / Cloud9 Instances that you created for the walkthrough.
  





































































### Pre-requisites 
 
 * AWS account 
 * AWS cloud9 instance with the relevant permission to execute AWS IoT actions
 * IAM role creation access

 ### Building a simulation Public key infrastructure(PKI)
* Go to AWS Cloud9

    1 - Go to AWS cloud9 -> Create environment -> give it a name 
        
        Use the following configurations -
        
        - Create a new EC2 instance for environment (direct access)
        - t3.small (2 GiB RAM + 2 vCPU)
        - AmazonLinux 2

        Next step and create

* Clone the repository for the simulation
    ```
    git clone PLACEHOLDER
    cd /repo/JITR
    ```
        
* Create a simulation PKI by running the following OpenSSL commands:

    ```    
    openssl genrsa -out rootCA.key 2048
    ```
    ```
    openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 1024 -out rootCA.pem
    ```
    Fill the signing form. All fields are optional, but the common name, in this case lets use rootCA. 
    
* Registering Certificate with AWS IoT Core
    
    Execute the following commands

    ```
    aws iot get-registration-code
    ```
    Save this code for the next step
    ```
    openssl genrsa -out verificationCert.key 2048

    openssl req -new -key verificationCert.key -out verificationCert.csr 
    ```

    Now we need to set the Common Name field of the certificate with the registration code:

    Country Name (2 letter code) [AU]:

    State or Province Name (full name) []:

    Locality Name (for example, city) []:

    Organization Name (for example, company) []:

    Organizational Unit Name (for example, section) []:

    Common Name (e.g. server FQDN or YOUR name) []: XXXXXXXREGISTRATION-CODEXXXXXXX

    Email Address []:

    We use the CSR to create a private key verification certificate. The verificationCert.pem file we get from this step will be used when we register the CA certificate.

    ```
    openssl x509 -req -in verificationCert.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out verificationCert.pem -days 500 -sha256
    ```

* Register a CA certificate

    ```
    aws iot register-ca-certificate --ca-certificate file://rootCA.pem --verification-cert file://verificationCert.pem --set-as-active --allow-auto-registration 
    ```

### Create the JITR lambda function 

* Create the lambda role 
    - Go to IAM 
    - Create a role with the following permissions 
      ```
                {  
        "Version":"2012-10-17",
        "Statement":[  
            {  
                "Effect":"Allow",
                "Action":[  
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource":"arn:aws:logs:*:*:*"
            },
            {  
                "Effect":"Allow",
                "Action":[  
                    "iot:UpdateCertificate",
                    "iot:CreatePolicy",
                    "iot:AttachPrincipalPolicy"
                ],
                "Resource":"*"
            }
        ]
        }
- Save the ROLE ARN.


   ```
    aws lambda create-function \
        --region <YOUR-REGION_HERE> \
        --function-name jitr \
        --zip-file fileb://./jitr-lambda.zip \
        --role <LAMBDA-ROLE-ARN-HERE> \
        --handler lambda_function.lambda_handler \
        --runtime python3.7 \
        --timeout 30 \
        --memory-size 256
    ```

### Create the JITR rule action 

```
aws iot create-topic-rule --rule-name JITRRule \
  --topic-rule-payload "{
        \"sql\": \"SELECT * FROM '\$aws/events/certificates/registered/#' WHERE certificateStatus = \\\"PENDING_ACTIVATION\\\"\",
        \"description\": \"Rule for JITR\",
        \"actions\": [
            {
                \"lambda\": {
                    \"functionArn\": \"<YOUR-LAMBDA-ARN-HERE>\"
                }
            }
        ]
     }"
```

### Testing the Registration flow

For this next step we will be creating a Simulation fleet using Docker containers to simulate a IoT thing.

* Run the following commands to create a Docker image. Note that in this Simulation example the Root Ca key will be part of the Container image, which should never be applied in a production environments.!!!Important to notice this is a strictly for demonstration purpose example, CA keys should never be store in device images!!!


    ```
    mv rootCA.key ./iotdevice/rootCA.key
    mv rootCA.pem ./iotdevice/rootCA.pem
    docker build --tag golden-image-jitr .
    ```
* Now we get the endpoint for your AWS IoT core and run the simulation 

    ```
    aws iot describe-endpoint \
    --endpoint-type iot:Data-ATS
    ```
    Use it to run the next command. Also feel free to simulate as many devices as you like by change the number 20 to anything else. (Keep in mind too many containers will crash your Instance if not properly sized)

    ```
    python3 simulate_fleet.py -e <YOUR-ENDPOINT-HERE> -n 20
    ```
Check your AWS IoT Core - Under things, you should see the device populating the registry list with random UUIDs





