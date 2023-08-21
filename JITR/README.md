## Just in time registration(JITR)

In this section we will execute every step to configure AWS IoT core and a simulation fleet to use JITR. Note this is a strictly educational project, and the example and samples utilized here should not be implemented into projects without changes. 
For more information on Just in time provisioning please refer to this documentation page - https://docs.aws.amazon.com/iot/latest/developerguide/jit-provisioning.html

A workshop containing the concepts a example code used in this guide is also available at - https://catalog.us-east-1.prod.workshops.aws/workshops/7c2b04e7-8051-4c71-bc8b-6d2d7ce32727/en-US/provisioning-options/just-in-time-registration
 
This guide is also available at - https://aws.amazon.com/blogs/iot/just-in-time-registration-of-device-certificates-on-aws-iot/ 

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





