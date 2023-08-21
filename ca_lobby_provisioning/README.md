## Just in time provisioning and Lobby account for external accounts

In this section we will execute every step to configure AWS IoT core and a simulation fleet to use JITP. Note this is a strictly educational project, and the example and samples utilized here should not be implemented into projects without changes. 
For more information on Just in time provisioning please refer to this documentation page - https://docs.aws.amazon.com/iot/latest/developerguide/jit-provisioning.html
 
A workshop containing the concepts a example code used in this guide is also available at - https://catalog.us-east-1.prod.workshops.aws/workshops/7c2b04e7-8051-4c71-bc8b-6d2d7ce32727/en-US/provisioning-options/just-in-time-provisioning

Guidance is also available at - https://aws.amazon.com/blogs/iot/setting-up-just-in-time-provisioning-with-aws-iot-core/ 

### Pre-requisites 
 
 * AWS account 
 * AWS cloud9 instance with the relevant permission to execute AWS IoT actions
 * IAM role creation access


 ### Creating the JITP IAM role 
* Go to Identity and Access Management (IAM)
    
    - Roles -> Create a new role 
    - Select use cases, and under the drop down menu select *IoT*
    - Next 
    - Keep policies as default, next
    - Give it a name and keep the rest as default 
    - Create
    - Navigate back, copy and save the role ARN. 

 ### Building a simulation Public key infrastructure(PKI)

    * - Go to AWS cloud9 -> Create environment -> give it a name 
        
        Use the following configurations -
        
        - Create a new EC2 instance for environment (direct access)
        - t3.small (2 GiB RAM + 2 vCPU)
        - AmazonLinux 2

        Next step and create

* Clone the repository for the simulation
    ```
    git clone PLACEHOLDER
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

    * Go to Identity and Access Management (IAM)
    
    - Roles -> Create a new role 
    - Select use cases, and under the drop down menu select *IoT*
    - Next 
    - Keep policies as default, next
    - Give it a name and keep the rest as default 
    - Create
    - Navigate back, **copy and save the role ARN.** 

    * Prepare the provisioning template for the simulation 

    - Open the provisioning-template.json , and replace the ARN field with the Role ARN you copied on the previous step.

    ```
    aws iot register-ca-certificate --ca-certificate file://rootCA.pem --verification-cert file://verificationCert.pem --set-as-active --allow-auto-registration --registration-config file://provisioning-template.json
    ```

### Testing the provisioning template by deploying one device. 

From the same directory execute the commands bellow. YOu will create a unique Certificate, then a CSR (complete the whole from thoroughly), **during the CSR step we must add a Serial number to the Common name field.** The serial number will be used during the whole process of provisioning and account re-provisioning. **The serial number we will use for this demonstration is : 1234567890** 

    ```
    openssl genrsa -out deviceCert.key 2048
    openssl req -new -key deviceCert.key -out deviceCert.csr -set_serial "0x`openssl rand -hex 8`"
    openssl x509 -req -in deviceCert.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out deviceCert.crt -days 365 -sha256
    cat deviceCert.crt rootCA.pem > deviceCertAndCACert.crt
    ```
* Now we get the endpoint for your AWS IoT core and run the simulation 

    ```
    aws iot describe-endpoint \
    --endpoint-type iot:Data-ATS
    ```

    Run the command below replacing the endpoint here indicated. You will run the command once and receive a connection denied. That will start the provisioning flow, wait 2 seconds and run the **same command again**, now you will see a connection accepted message, head to AWS IoT core, Things and inspect the newly created thing.

    ```
    mosquitto_pub --cafile root.cert --cert deviceCertAndCACert.crt --key deviceCert.key -h <REPLACE-FOR-ENDPOINT-HERE> -p 8883 -q 1 -t /client/ready/SerialNumber -I anyclientID --tls-version tlsv1.2 -m '1234567890' -d
    ```


### Reacting to the device provisioning Lifecycle

Once the device is fully provisioned, it will publish a beacon message to a reserved topic /client/ready, the message will contain the device serial number so a Lambda function can then trigger the ownership check. Note that in a production environment this topic should be restricted per device. 

* Create an IoT rule



