## Bulk registration - from CSR 

### Introduction
In this section you will execute every step to configure AWS IoT Core for a bulk registration job. Bulk registration flow allows provisioning of devices by the use of the [Bulk-registration-API](https://docs.aws.amazon.com/iot/latest/developerguide/bulk-provisioning.html), This option allows you to specify a list of single-thing provisioning template values that are stored in a file in an S3 bucket. This approach works well if you have a large number of known devices whose desired characteristics you can assemble into a list. In this walkthrough you will learn how to create the necessary resources in AWS and run simulation to test your configurations. 

**In this example you will learn the CSR method.** In this methodology you supply the registration task with a Certificate signing request, which is then signed by the [Amazon trust service](https://www.amazontrust.com/repository/), an Amazon privately managed Certificate Authority(CA).

### Limitations
Bulk registration has 2 mains dependencies, a [Provisioning template](https://docs.aws.amazon.com/iot/latest/developerguide/provision-template.html#bulk-template-example) and a Parameters list file, which the API uses to replace the parameter fields in the template.

Bulk registration is an ideal mechanism for use cases such as migration of known devices into AWS IoT Core. That is due to the dependencies and the methodology of which certificates are associated to things. Unlikely other provisioning methods in AWS IoT Core, bulk registration will not be interacting with a IoT device directly, but only provisioning the necessary resources of which a device needs in place to connect, on top of that a mechanism to deliver the Certificates and Keys to the devices must be designed accordingly. Understanding that, make sure you select the correct Certificate assertion mechanism for your provisioning template. Here are the options:
  * Certificate signing request - In this option, you parameters file will provide the template with a certificate signing request which was generated from a Unique private Key

### Bulk registration flow
In the flow below you can understand the process of which you will be learning in this repository. The flow indicates the use of a CSR, which means in a real use case, the Device manufacturing team would have to provide the administrator with a list of CSRs generated from Private key in the devices. That list would be used to run the bulk provisioning registration task along with a file containing the parameters to define the IoT Things. Remember that bulk registration is a feature meant for manual registration, tasks such as migration use cases or cross region transferences. Use cases for bulk registration may vary, but it is not a recommended method if your use case requires AWS IoT core to interact with your device directly during the provisioning. 

![bulk registration flow](/assets/bulk-registration-flow.png)

### Pre-requisites 

 * AWS account 
 * AWS cloud9 or AWS CloudShell, with the relevant permissions to execute AWS IoT actions, or your preferred IDE with the relevant access.
 * AWS Command line interface (AWS CLI), installed and configured (version 2.13 or later).
 * IAM role creation permissions (You will need to create IAM roles).

### Clone the repository 

Clone the repository and navigate to the just in time registration directory.
```
git clone https://github.com/aws-samples/bulk-registration-using-csr
cd aws-iot-core-device-provisioning-deep-dive/bulk-registration-using-csr
```
**This will be your work directory from this point**

### Understanding the provisioning template
Provisioning templates, are JSON documents used by the JITP service in order to customize how your IoT things will be provisioned and registered. Actions such as creating a thing, adding a thing to a group and attach a policy are examples of action executed accordingly to the template. Read the [provisioning templates](https://docs.aws.amazon.com/iot/latest/developerguide/provision-template.html) section on the documentation page to learn more. 

![template mapping](/assets/bulk-registration-template-mapping.png)

For this test you will start with the example below. The provisioning template is the start point when developing for Bulk-registration, what you define in the template will influence how your authorization and cloud infrastructure needs to be setup. In this example the **Parameters** are being extracted from the file which will be placed in an Amazon S3 bucket. The basic skeleton of the parameter file can be found on the [bulk-registration documentation page](https://docs.aws.amazon.com/iot/latest/developerguide/bulk-provisioning.html). In this project we will use the following structure. 
```json
{"ThingName": "ThingTypeD_eea9ae4efd1b4e41b9cc3b33dba1aa39", "businessUnitMaker": "AnyCompany", "SerialNumber": "eea9ae4efd1b4e41b9cc3b33dba1aa39", "ThingTypeName": "ThingTypeD", "ThingGroup": "", "countryOrigin": "US", "licenseType": "basic", "hardwareVersion": "100", "softwareVersion": "100", "CSR": "-----BEGIN CERTIFICATE REQUEST-----\n<CONTENT>\n-----END CERTIFICATE REQUEST-----\n"}
```
Each line of the file in the S3 bucket must provide the information which the template uses for each IoT Thing registration (One Thing per line). 

In the **Resources** segment we define how and where the parameters are used. Finally, you define the certificate to be registered and the policy which will be attached to it, note that in this examople we specify **CSR**. 
Provisioning templates can solve many cases, be sure to explore the documentation page for more examples. 

**Very important!** When defining a parameter, a "Default" value can be provided in case the certificate does not contain information on the defined field. If you do not use a default value, the defined field which does not receive a value f will force the registration job to fail, and the operation is deemed unsafe. 

For more information on how to build Provisioning templates consult the documentation for [Provisioning templates](https://docs.aws.amazon.com/iot/latest/developerguide/provision-template.html).

```json
{
  "Parameters" : {
      "ThingName" : {
          "Type" : "String"
      },
      "SerialNumber" : {
          "Type" : "String"
      },
      "countryOrigin" : {
          "Type" : "String",
          "Default" : "US"
      },
      "ThingGroup" : {
        "Type" : "String",
        "Default" : "unclaimed"
      },
      "ThingTypeName" : {
        "Type" : "String"
      },
      "licenseType" : {
        "Type" : "String"
      },
      "businessUnitMaker" : {
        "Type" : "String"
      },
      "hardwareVersion" : {
        "Type" : "String"
      },
      "softwareVersion" : {
        "Type" : "String"
      },
        "CSR" : {
        "Type" : "String"    
        }
  },
  "Resources" : {
      "thing" : {
          "Type" : "AWS::IoT::Thing",
          "Properties" : {
              "ThingName" : {"Ref" : "ThingName"},
              "AttributePayload" : { 
              "hardwareVersion" : {"Ref": "hardwareVersion"},
              "softwareVersion" : {"Ref": "hardwareVersion"}, 
              "serialNumber" :  {"Ref" : "SerialNumber"},
              "countryOrigin": {"Ref": "countryOrigin"},
              "businessUnitMaker": {"Ref": "businessUnitMaker"},
              "licenseType": {"Ref": "licenseType"},
              "provisioning": "bulkRegistration"
            }, 
              "ThingTypeName" : {"Ref": "ThingTypeName"},
              "ThingGroups" : [{"Ref": "ThingGroup"}],
              "BillingGroup" : {"Ref": "businessUnitMaker"}
          }
      },
      "certificate" : {
          "Type" : "AWS::IoT::Certificate",
          "Properties" : {
              "CertificateSigningRequest": {"Ref" : "CSR"},
              "Status" : "ACTIVE"      
          }
      },
      "policy" : {
          "Type" : "AWS::IoT::Policy",
          "Properties" : {
              "PolicyName" :"AnyTypeThing-policy" 
          }
      }
  }
}

```
The template above, has already being saved on this directory as **bulk_registration_provisioning_template.json**

### Prepare your infrastructure. 
You may have noticed that the provisioning template tries to add Things to Types and Groups, you must create those resources in your AWS IoT environment prior to the registration task, or it will fail. Another important step is to create an IAM ServiceRole scoped down for the registration task, which is also created, on the bootstrapping process below. A **bootstrap.sh** file has already been created, just execute the commands below, and you will have all the resources in place.**Note:** make sure you have the appropriate permissions to run the bootstrap.sh file as it makes AWS CLI calls to AWS services in your behalf. 

The AWS IoT Thing, groups and types which the bootstrap file and simulation below creates will use any of the possible variants on the image below:

![IoT Core resources](/assets/bulk-registration-simulation.png)

Run the commands below:
```
chmod +x bootstrap.sh
./bootstrap.sh 
```
### Simulating a Bulk-registration task
Below you can have a look at the simulation diagram:
  1- The Simulation.py script will create a set of x509 keys and certificates signing requests from the keys. THe keys and CSRs will be stored on CSR_store.json and Key_store.json if you wish to further this simulation and simulate devices connecting to AWS IoT Core.**Important**, keeping Private keys on a JSON file is not a best practices, we are using this method with an educational purpose, please consult the main page on this repository where you can learn more about manufacturing with x509 certificates. 
  2- Simulation.py will use the CSR list to create the parameters.
  3- Generates parameters.json and store it to a S3 bucket (bucket has been created during bootstrap, bulkregistrationtasks< accountID >).
  4- Calls the Bulk -registration api - aws iot start-registration-task.
  5- Your things will be registered in AWS IoT Core, you can now inspect the registration task and download the result logs containing the Signed- certs

![simulation flow](/assets/bulk-registration-simulation-flow.png)

Run the command below and indicate how many devices you would like to register.After the python script is done it will automatically call the [Start-thing-registration call](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/iot/start-thing-registration-task.html).

   ```
   Python3 simulation.py -n <NUMBER-OF-DEVICES>
   ```

Now go to **AWS IoT Core**->**Connect many devices**->**Bulk registration**.
In this console menu you can see all registration tasks and their current status, similar to the picture below. After the registration task shows status **Completed**, you can click and select it, then click on the top right **Actions**. You can now download the Success Logs, this log file will contain all certificates that have been signed for your devices on the same order they have been received on the parameter.json file. In case you have a Failure in the task, a failure log will also be available you can use that for troubleshooting. 

![registration task](/assets/registration-task.png)

Optionally you can use the [Describe thing registration API call](https://awscli.amazonaws.com/v2/documenthttps://awscli.amazonaws.com/v2/documentation/api/latest/reference/iot/list-thing-registration-task-reports.htmlation/api/latest/reference/iot/describe-thing-registration-task.html), and the [registration report](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/iot/list-thing-registration-task-reports.html) call to retrieve the log file.

### Troubleshooting 
   * Use the log files. 
      The simulation will create a file name simulation.log and the bootstrap operation will create file name boostrap.log, use those when reporting issues.   
   * Make use of AWS Cloudwatch by turning on logs in AWS IoT Core. Go to AWS IoT Core -> Settings -> Logs -> Manage logs, Create a log role and for the Log level use Debug. 
   * All provisioning action are tracked by AWS Cloudtrail, if any error with the provisioning template occur, you be able to identify it by looking for the iot-provisioning identification on the event.  
   
### Next steps
Explore calls with [AWS IoT Device management - fleet indexing](https://docs.aws.amazon.com/iot/latest/developerguide/iot-indexing.html), using Fleet indexing will allow you to filter device by Groups, Hardware version etc. 

### Cleaning up
   * Delete all create things.
   * Delete all registered certificates. 
   * Delete the Provisioning template.
   * Delete the thing policy.
   * Delete the thing types and thing groups
   * Terminate any EC2 / Cloud9 Instances that you created for the walkthrough.