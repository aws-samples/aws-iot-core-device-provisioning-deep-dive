## Fleet Provisioning by claim 



# under construction do not use it


In this section we will execute every step to configure AWS IoT core for fleet provisioning by claim. We will also simulate a fleet by using docker containers. Note this is a strictly educational project, and the example and samples utilized here should not be implemented into projects without changes. 
For more information on Fleet Provisioning please refer to this documentation page - https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html

A workshop containing the concepts a example code used in this guide is also available at - https://catalog.us-east-1.prod.workshops.aws/workshops/7c2b04e7-8051-4c71-bc8b-6d2d7ce32727/en-US/provisioning-options/fleet-provisioning
 
Guidance on best practice is also available at - https://aws.amazon.com/blogs/iot/how-to-automate-onboarding-of-iot-devices-to-aws-iot-core-at-scale-with-fleet-provisioning/


### Pre-requisites 
 
 * AWS account 
 * AWS cloud9 instance with the relevant permission to execute AWS IoT actions
 * IAM role creation access

 ### Creating the Fleet Provisioning IAM role 
* Go to Identity and Access Management (IAM)
    
    - Roles -> Create a new role 
    - Select use cases, and under the drop down menu search for AWS IoT and select *IoT*
    - Next 
    - Keep policies as default, next
    - Give it a name and keep the rest as default 
    - Create
    - Navigate back, copy and save the role ARN. 

 ### Building a simulation environment 
* Go to AWS Cloud9

    1 - Go to AWS cloud9 -> Create environment -> give it a name 
        
        Use the following configurations -
        
        - Create a new EC2 instance for environment (direct access)
        - t3.small (2 GiB RAM + 2 vCPU)
        - AmazonLinux 2

        Next step and create

* Clone the repository for the simulation and change into the directory 
    ```
    git clone PLACEHOLDER
    cd fleet_provisioning_by_claim
    ```

* Create a provisioning template with AWS IoT core 

    ```
    aws iot create-provisioning-template \
     --template-name FleetProvisioningTemplate \
     --provisioning-role-arn <THE PROVISIONING ROLE ARN HERE> \
     --template-body file://./fleet-provisioning-template.json \
     --enabled
    ```
        
* Create a claim certificate:

    ```    
    THING_NAME=provision-claim
    aws iot create-keys-and-certificate --set-as-active \
    --public-key-outfile $THING_NAME.public.key \
    --private-key-outfile $THING_NAME.private.key \
    --certificate-pem-outfile $THING_NAME.certificate.pem > provisioning-claim-result.json
    ```
    Now we save the ID to a variable for the next step.
    ```
    CERTIFICATE_ARN=$(jq -r ".certificateArn" provisioning-claim-result.json)
    ```
    **Note that Claim certificate are just AWS generate x.509 certificate, what makes it into a secure claim certificate is the action of restricting it with the correct policy which we will do in the next step.** 
  
* Attach Claim policy to claim certificate
    
    **Before executing the next command be sure to edit the fleet-provisioning-policy.json document with your region and AWS account ID.**
    ```
    aws iot create-policy --policy-name fleet-provisioning_Policy \
    --policy-document file://./fleet-provisioning-policy.json
    ```
    
    Then attach the policy to the claim cert 
    ```
    aws iot attach-policy --policy-name fleet-provisioning_Policy \
    --target $CERTIFICATE_ARN
    ```

### Testing the Fleet provisioning template and deploying a fleet 

For this next step we will be creating a Simulation fleet using Docker containers to simulate a IoT thing.

* Run the following commands to create a Docker image. 

    ```
    mv provision-claim.certificate.pem ./iotdevice/provision-claim.certificate.pem
    mv provision-claim.private.key ./iotdevice/provision-claim.private.key
    docker build --tag golden-image-fpc .
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

### Provisioning hook 

When using Fleet provisioning by Claim a provisioning hook lambda action is **Mandatory**. While you can create Fleet provisioning template and test you development environment without it, before going into production you must consider how you will check and validate your IoT device ownership. Common use cases use Serial number for instance, one of the parameters passed in the provisioning template is a unique Serial number of your device which can be then whitelisted by a Dynamo DB table.
In this example we will use the preset value '123456' in the lambda function itself. First we will add the Provisioning hook function to the Provisioning template. Then we will see how devices created by the Docker image are fully provisioned. After that we will modify the docker image with a diferent Serial number and see how the device is not provisioned but also the Lambda function send the ERROR log to AWS Cloudwatch. 

* Create the Provisioning Hook lambda function

    1 - Go to AWS Lambda-> Create Function
        
        - Select Author from scratch
        - Name it FleetProvisioningHook 
        - For Runtime Select Python 3.7
        - Keep everything else as default and Create function

        - In the lambda Code Source editor, replace the contents with the contents from the Provisioning_hook.py file
        - Deploy
        
* Add the Function to the provisioning template
        
        1 - Go to AWS IoT Core --> Connect many devices --> Provisioning templates
        
        - Find the template we create in this guide, name FleetProvisioningTemplate
        - Click on the template name and Edit details
        - Under POre provisioning Actions, select the Lambda function you just create, FleetProvisioningHook
        - Update template

* Testing Fleet provisioning with Provisioning Hook

    First I recommend you clean your Docker Daemon and IoT core account so you can better follow the changes

    Go to the AWS IoT Core console -> Things, Slect all things create on this guide, and delete them.

    Run the commands below to clean your Docker Daemon

    ```
    docker stop $(docker ps -aq)
    docker rm $(docker ps -aq)
    ```  

    Run the command below to create a Single device 

    ```
    python3 simulate_fleet.py -e <YOUR-ENDPOINT-HERE> -n 1
    ```
    Check your AWS IoT Core things list, you should see a new device which was create with the provisioning hook in place.

* Testing Fleet provisioning with Provisioning Hook with a bad serial number

    In this last step we will alter the Serial number allowed in the Lambda function. 

    Navigate back to AWS Lambda in the AWS console. Click on the lambda function you create, ProvisioningHook. In the source code editor find the line **SERIAL_STARTSWITH = "123456"**, then change the number sequence to anything diferent than 123456. Now, Deploy.

    Try provisioning a new IoT thing by running the command below

    ```
    python3 simulate_fleet.py -e <YOUR-ENDPOINT-HERE> -n 2
    ```

    The IoT Thing should no be created. And if you navigate to AWS CloudWatch --> Logs --> Log groups, under the Lmabda function name you will find an Error returned from Lambda "Serial_number 123455 verification failed - does not start with 123456".

