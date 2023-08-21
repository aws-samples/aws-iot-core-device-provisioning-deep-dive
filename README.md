# AWS IoT Device provisioning deep dive series
 
### Disclaimer
This repository is intended to educate IoT developers and Solutions architect on the different ways IoT devices can be provisioned for AWS IoT Core. This is an educational project, and the code samples and libraries should not be applied to a production environment without the appropriate development.

### Introduction
Developing and manufacturing IoT device at scale comes with a multitude of challenges, being one of them, provision the devices with the necessary authentication elements. In AWS IoT Core authentication is handled by customers, following our shared [responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/). In order to help customers to accomplish provisioning in the most efficient and secure way for their use case, AWS IoT Core supports a number of provisioning methods using [X.509 certificates](https://docs.aws.amazon.com/iot/latest/developerguide/x509-client-certs.html), those are:

* Just in time provisioning(JITP)
* Just in time registration(JITR)
* Multi-account registration 
* Fleet provisioning - by trusted user
* Fleet provisioning - by claim
* Bulk registration
* Single thing provisioning 

Each one of those methods will be suitable to a specific use case, which is usually influenced by the device manufacturing supply chain. In the [Device manufacturing and Provisioning with x.509 Certificates in AWS IoT Core](https://docs.aws.amazon.com/whitepapers/latest/device-manufacturing-provisioning/device-provisioning-during-development.html) white paper, you can learn more about how supply chains can influence you device provisioning strategy. 

### How to use this repository
You will find a sub folder for each provisioning method mentioned above. In the sub folder you will find another README for each segment, which will guide you through the steps of configuring a testing. 







 TODO
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)







## My Project

TODO: Fill this README out!

Be sure to:

* Change the title in this README
* Edit your repository description on GitHub

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.