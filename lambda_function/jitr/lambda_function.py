#required libraries
import boto3
import json
import logging
import os
from boto3.dynamodb.conditions import Key, Attr
import sys

from OpenSSL import crypto

# configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ERRORS = []


def get_thing_name(c_iot, certificate_id, response):
    try:
        cert_pem = response['certificateDescription']['certificatePem']
        logger.info('cert_pem: {}'.format(cert_pem))

        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)

        subject = cert.get_subject()
        cn = subject.CN
        logger.info('subject: {} cn: {}'.format(subject, cn))
        return cn
    except Exception as e:
        logger.warn('unable to get CN from certificate_id: {}: {}, using certificate_id as thing name'.format(certificate_id, e))
        return certificate_id


def thing_exists(c_iot, thing_name):
    try:
        response = c_iot.describe_thing(thingName=thing_name)
        print('response: {}'.format(response))
        return True
    except Exception as e:
        logger.warn('describe thing: {}'.format(e))
        return False


def create_thing(c_iot, thing_name):
    global ERRORS
    try:
        if not thing_exists(c_iot, thing_name):
            response = c_iot.create_thing(thingName=thing_name)
            logger.info("create_thing: response: {}".format(response))
        else:
            logger.info("thing exists already: {}".format(thing_name))
    except Exception as e:
        logger.error("create_thing: {}".format(e))
        ERRORS.append("create_thing: {}".format(e))


def policy_exists(c_iot, policy_name):
    try:
        response = c_iot.get_policy(policyName=policy_name)
        print('response: {}'.format(response))
        return True
    except Exception as e:
        logger.warn('get policy: {}'.format(e))
        return False


def create_iot_policy(c_iot, policy_name):
    global ERRORS
    policy_document = {
        "Version":"2012-10-17",
        "Statement":[
            {
                "Effect": "Allow",
                "Action":"*",
                "Resource":"*"
            },
        ]
    }

    try:
        if not policy_exists(c_iot, policy_name):
            response = c_iot.create_policy(
                policyName=policy_name,
                policyDocument=json.dumps(policy_document)
            )
            logger.info("create_iot_policy: response: {}".format(response))
        else:
            logger.info("policy exists already: {}".format(policy_name))
    except Exception as e:
        logger.error("create_iot_policy: {}".format(e))
        ERRORS.append("create_iot_policy: {}".format(e))


def activate_certificate(c_iot, certificate_id):
    global ERRORS
    try:
        response = c_iot.update_certificate(certificateId=certificate_id, newStatus='ACTIVE')
        logger.info("activate_cert: response: {}".format(response))
    except Exception as e:
        logger.error("activate_certificate: {}".format(e))
        ERRORS.append("activate_certificate: {}".format(e))


def attach_policy(c_iot, thing_name, policy_name, response):
    global ERRORS
    try:
        certificate_arn = response['certificateDescription']['certificateArn']
        logger.info("certificate_arn: {}".format(certificate_arn))

        response = c_iot.attach_thing_principal(thingName=thing_name, principal=certificate_arn)
        logger.info("attach_thing_principal: response: {}".format(response))

        response = c_iot.attach_policy(policyName=policy_name, target=certificate_arn)
        logger.info("attach_policy: response: {}".format(response))
    except Exception as e:
        logger.error("attach_policy: {}".format(e))
        ERRORS.append("attach_policy: {}".format(e))

def get_item_dynamoDB(c_dynamodb, SerialNumber)
    global ERRORS
    try:
        

        


def lambda_handler(event, context):
    logger.info("event: {}".format(event))
    logger.info(json.dumps(event, indent=4))

    region = os.environ["AWS_REGION"]
    logger.info("region: {}".format(region))

    try:
        ca_certificate_id = event['caCertificateId']
        certificate_id = event['certificateId']
        certificate_status = event['certificateStatus']

        logger.info("ca_certificate_id: " + ca_certificate_id)
        logger.info("certificate_id: " + certificate_id)
        logger.info("certificate_status: " + certificate_status)

        c_iot = boto3.client('iot')
        c_dynamodb = boto3.client('dynamodb')

        res_desc_cert = c_iot.describe_certificate(certificateId=certificate_id)
        logger.info('res_desc_cert: {}'.format(res_desc_cert))

        thing_name = get_thing_name(c_iot, certificate_id, res_desc_cert)
        create_thing(c_iot, thing_name)
        #create_iot_policy(c_iot, '{}-policy'.format(thing_name))
        create_iot_policy(c_iot, 'jitr_Policy')
        activate_certificate(c_iot, certificate_id)
        attach_policy(c_iot, thing_name, 'jitr_Policy', res_desc_cert)
    except Exception as e:
        logger.error('describe_certificate: {}'.format(e))
        return {"status": "error", "message": '{}'.format(e)}

    if ERRORS:
        return {"status": "error", "message": '{}'.format(ERRORS)}

    return {"status": "success"}
