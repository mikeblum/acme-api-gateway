#!/usr/bin/env python2

import logging
import os
from pprint import pprint
import sys
from time import sleep

import tldextract
import dns.resolver

import boto3
import route53

# logging.basicConfig(level=logging.DEBUG)
TTL = 60 # seconds

def upload_dns_challange(domain, challenge):
    """
    Create TXT record for the specified domain in Route53
    """
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
    le_challange = challenge
    print('setting dns-challange for letsencrypt key: {0}'.format(le_challange))
    record_name = '_acme-challenge.{0}.'.format(domain) 
    # create txt record for the specified domain
    zone = route53_conn.get_hosted_zone_by_id(route53_id)
    # check for existing TXT challange record
    txt_record = None
    for record_set in zone.record_sets:
        if record_set.name == record_name:
            txt_record = record_set
            break
    if txt_record is not None:
        print('removing old TXT record for letsencrypt challange')
        change_info = txt_record.delete()
        print(change_info)
    print('creating TXT record for letsencrypt challange')
    # Route53 expects values to be "double-quoted"
    le_challange = '"{}"'.format(le_challange)
    txt_record, change_info = zone.create_txt_record(
        # Notice that this is a full-qualified name.
        name=record_name,
        # let's encrypt challange
        # Route53 expects values to be "double-quoted"
        values=[le_challange],
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
        if le_challange != str(txtdata):
            raise ValueError('TXT {0} failed to propogate'.format(record_name))

def cleanup_dns_challange(domain, challenge):
    print('removing DNS challange')

def deploy_to_api_gateway(domain, cert):
    print('deploying certificates to API Gateway')
    api_gateway_client = boto3.client('apigateway')

if __name__ == "__main__":
    hook = sys.argv[1]
    domain = sys.argv[2]
    txt_challenge = sys.argv[4]
    cert = sys.argv[4]

    print(hook)
    print(domain)
    print(txt_challenge)
    if hook == 'deploy_challenge':
        upload_dns_challange(domain, txt_challenge)
    if hook == 'clean_challenge':
        cleanup_dns_challange(domain, txt_challenge)
    if hook == 'deploy_cert':
        deploy_to_api_gateway(domain, cert)
