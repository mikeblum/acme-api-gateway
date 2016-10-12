#!/usr/bin/env python2

import logging
import os
from pprint import pprint
import sys
import time
from time import sleep

import tldextract
import dns.resolver

import boto3
import botocore
import route53

# logging.basicConfig(level=logging.DEBUG)
TTL = 60 # seconds
CERT_FILE = "cert.pem"
PRIVATE_KEY_FILE = "privkey.pem"
CHAIN_FILE = "chain.pem"
FULL_CHAIN_FILE = "full_chain.pem"

def get_route53_zone(domain):
    route53_conn = route53.connect(
        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )
    route53_id = None
    fqdn = tldextract.extract(domain)
    tld = fqdn.domain + '.' + fqdn.suffix
    # fetch Route53 hosted zone
    for zone in route53_conn.list_hosted_zones():
        # remove trailing . from zone name
        if zone.name[:-1] == tld:
            route53_id = zone.id
    if route53_id is None:
        raise ValueError('domain {} not found in Route53 hosted zones'.format(tld))
    # create txt record for the specified domain
    return route53_conn.get_hosted_zone_by_id(route53_id)

def get_txt_record(domain):
    """
    Let's Encrypt expects the following TXT record:
    _acme-challenge.{{ domain }}.
    Note the ending period
    """
    return '_acme-challenge.{0}.'.format(domain)

def upload_dns_challenge(domain, challenge):
    """
    Create TXT record for the specified domain in Route53
    """
    zone = get_route53_zone(domain)
    record_name = get_txt_record(domain)
    cleanup_dns_challenge(domain, challenge)
    print('creating TXT record for letsencrypt challenge')
    # Route53 expects values to be "double-quoted"
    le_challenge = '"{}"'.format(challenge)
    txt_record, change_info = zone.create_txt_record(
        # Notice that this is a full-qualified name.
        name=record_name,
        # let's encrypt challenge
        # Route53 expects values to be "double-quoted"
        values=[le_challenge],
        ttl=TTL
    )
    # wait for DNS to propogate
    sleep(30)
    # zone record sets is a generator - refetch the updated record
    for record_set in zone.record_sets:
        if record_set.name == record_name:
            txt_record = record_set
            break
    print('modified: {0}'.format(txt_record.is_modified()))
    # verify DNS propogation
    answers = dns.resolver.query(record_name, 'TXT')
    for txtdata in answers:
        if le_challenge != str(txtdata):
            raise ValueError('TXT {0} failed to propogate'.format(record_name))

def cleanup_dns_challenge(domain, challenge):
    """
    Delete TXT record
    """
    print('removing DNS challenge')
    zone = get_route53_zone(domain)
    record_name = get_txt_record(domain)
    # check for existing TXT challenge record
    txt_record = None
    for record_set in zone.record_sets:
        if record_set.name == record_name:
            txt_record = record_set
            break
    if txt_record is not None:
        print('removing old TXT record for letsencrypt challenge')
        change_info = txt_record.delete()
        print(change_info)


def deploy_to_api_gateway(domain, certfile):
    print('deploying certificates to API Gateway')
    api_gateway_client = boto3.client(
        'apigateway',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )
    iam = boto3.resource('iam')
    iam_client = boto3.client(
        'iam',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )
    path, filename = os.path.split(certfile)
    certificate_body = None
    with open(certfile) as cert:
        certificate_body = cert.read()
    # get contents of the private key
    certificate_private_key = None
    with open(os.path.join(path, PRIVATE_KEY_FILE)) as cert:
        certificate_private_key = cert.read()
    # get contents of the certificate certificate_chain
    certificate_chain = None
    with open(os.path.join(path, CHAIN_FILE)) as cert:
        certificate_chain = cert.read()
    api = None
    try:
        try:
            api = api_gateway_client.get_domain_name(
                domainName=domain
            )
        except botocore.exceptions.ClientError as e:
            print(e.response['Error']['Code'])
            api = None
        if api is None:
            print('creating domain name ({0}) in API Gateway'.format(domain))
            api = api_gateway_client.create_domain_name(
                domainName=domain,
                certificateName=os.path.basename(certfile),
                certificateBody=certificate_body,
                certificatePrivateKey=certificate_private_key,
                certificateChain=certificate_chain
            )
        else:
            print('renewing domain name ({0}) in API Gateway'.format(domain))
            # Zappa showed the way!
            # Zappa/zappa/letsencrypt.py
            # upload certificate to IAM
            new_cert_name = domain + str(time.time())
            iam.create_server_certificate(
                ServerCertificateName=new_cert_name,
                CertificateBody=certificate_body,
                PrivateKey=certificate_private_key,
                CertificateChain=certificate_chain
            )
            # point certificate to API Gateway
            api_gateway_client.update_domain_name(
                domainName=domain,
                patchOperations=[
                    {
                        'op': 'replace',
                        'path': '/certificateName',
                        'value': new_cert_name,
                    }
                ]
            )

        # create CNAME record that points the 
        cloud_front_distribution_name = api['distributionDomainName']
        print('Create Alias record from {0} to {1}'.format(domain, cloud_front_distribution_name))
    except botocore.exceptions.ClientError as e:
        print('Failed to create API')
        print(e.response['Error']['Code'])
        raise(e)

if __name__ == "__main__":
    hook = sys.argv[1]
    domain = sys.argv[2]
    txt_challenge = sys.argv[4]
    cert = sys.argv[4]

    print(hook)
    print(domain)
    print(txt_challenge)
    if hook == 'deploy_challenge':
        upload_dns_challenge(domain, txt_challenge)
    if hook == 'clean_challenge':
        cleanup_dns_challenge(domain, txt_challenge)
    if hook == 'deploy_cert':
        deploy_to_api_gateway(domain, cert)
    if hook == 'unchanged_cert':
        deploy_to_api_gateway(domain, cert)