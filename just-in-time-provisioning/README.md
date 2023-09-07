## Just in time provisioning(JITP)

### Introduction
In this section you will execute every step to configure AWS IoT Core for JITP, and run a simulation fleet using JITP. Note this is a strictly educational project, and the example and samples utilized here should not be implemented into projects without changes. For more information go to [Just in time provisioning documentation page](https://docs.aws.amazon.com/iot/latest/developerguide/jit-provisioning.html). 


Just in time provisioning has a dependency on using a private certificate authority(CA). The Private CA must be registered in the AWS IoT Core account and region where you wish to provision your devices for. In addition to that you must make sure the device attempting to connect to AWS IoT Core for the first time has a Unique device certificate, signed by the Private CA (or chain) which you registered in AWS IoT Core. 

The flow diagram below explains each action that happens in a JITP provisioning flow, note that some of those are not part of the flow itself, but actions that have to be done by a security administrator and manufacturing prior to the first connection. 

![JITP flow](/assets/jitp-flow.png)


### Pre-requisites 

 * AWS account 
 * AWS cloud9 or AWS CloudShell , with the relevant permissions to execute AWS IoT actions, or your preferred IDE with the relevant access.
 * AWS Command line interface (AWS CLI), installed and configured.
 * IAM role creation access (You will need to create IAM roles).

### Clone the repository 

Clone the repository and navigate to the just in time registration directory.
```
git clone https://github.com/aws-samples/aws-iot-core-device-provisioning-deep-dive.git
cd /aws-iot-core-device-provisioning/just-in-time-provisioning
pip3 install requeriments.txt
```
**This will be your work directory from this point**

### Understanding the provisioning template
Provisioning templates, are JSON documents used by the JITP service in order to customize how your IoT things will be provisioned and registered. Actions such as creating a thing, adding a thing to a group and attach a policy are examples of action executed accordingly to the template. Read the [provisioning templates](https://docs.aws.amazon.com/iot/latest/developerguide/provision-template.html) section on the documentation page to learn more. 

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

For this educational project you can just execute the commands below as is:

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

      openssl x509 -req -days 3650 -extfile rootCA_openssl.conf -extensions v3_ca -in rootCA.csr -signkey rootCA.key -out rootCA.pem
      ```
* **Fill the signing form**. 
   Feel free to use any value you like, but fill all fields, as the Certificate DN is a way to identify Certificates. An example below: 

   Country Name [ ]:**US**

   State [ ]:**CO**
   
   City [ ]:**Denver**
   
   Organization [ ]:**AnyCompany**
   
   Organization Unit [ ]:**All**
   
   Common Name [ ]:**IoT Devices Root CA**

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
      
       **Common Name (e.g. server FQDN or YOUR name) []: XXXXXXXREGISTRATION-CODEXXXXXXX**

         ```
         openssl x509 -req -in verificationCert.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out verificationCert.pem -days 500 -sha256
         ```

* **Register the CA certificate**
   This is the final step of the registration, there are a few modes in which a CA can be registered, to understand that better please read [Manage your CA certificates](https://docs.aws.amazon.com/iot/latest/developerguide/manage-your-CA-certs.html).
   In the example below we are registering for a single account, active and with auto-registration on. The auto-registration will invoke the provisioning template.

      ```
      aws iot register-ca-certificate --ca-certificate file://rootCA.pem --verification-cert file://verificationCert.pem --set-as-active --allow-auto-registration --registration-config templateName=jitp-provisioning-template
      ```

### Testing the provisioning template and deploying a simulation fleet 

For this next step you will be creating a Simulation fleet using Docker containers that simulate an IoT client device, using the [AWS IoT V2 SDK for Python](https://github.com/aws/aws-iot-device-sdk-python-v2).

   **Important** This simulation is using a simple x509 certificate and not a "chain certificate", in this use case make sure no other Private CA with the same subject name is present in IoT Core.

   The Diagram below describes what you are about to do.
   * The simulation.py will build a container Image based on the present Dockerfile.
   * The simulation will use the provided arguments (endpoint and FleetSize) to create docker containers.
   *  In the background the Signing_service.py will start.
   *  As the containers start, they will self generate unique Certificate Keys, and request the signing_service.py for a CA signature. **Note:** This is an educational example of how certificates can be signed on a secure and completely isolated network, do not replicate this method without proper understanding of manufacturing with x509 certificates. 
   *  With a signed certificate each container will connect to AWS IoT Core and start the JITP flow, they will then successfully connect and publish messages, on the AnyCompany/serialNumber/telemetry

![deep-dive-jitp.drawio](/assets/deep-dive-jitp.jpg)

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

### Next steps
I recommend you explore calls with [AWS IoT Device management - fleet indexing](https://docs.aws.amazon.com/iot/latest/developerguide/iot-indexing.html), using Fleet indexing will allow you to filter device by Groups, Hardware version etc. 

### Cleaning up
   * Delete all create things.
   * Delete all registered certificates. 
   * Delete the Provisioning template.
   * Delete the thing policy.
   * Terminate any EC2 / Cloud9 Instances that you created for the walkthrough.
  