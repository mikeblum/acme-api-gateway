import argparse
import logging
import os
from pprint import pprint
import subprocess
from time import sleep

import tldextract
from urlparse import urlparse
import dns.resolver

import boto3
import route53

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import OpenSSL

from acme import client
from acme import messages
from acme import jose
from acme import challenges

from certbot import achallenges

from Crypto.PublicKey import RSA

DIRECTORY_URL = 'https://acme-staging.api.letsencrypt.org/directory'
BITS = 2048  # minimum for Boulder
CSR_FILE = 'csr.der'
DOMAIN = 'api.ipbot.io'
EMAIL = 'letsencrypt@{domain}'.format(domain=DOMAIN)
TTL=60 # seconds


logging.basicConfig(level=logging.DEBUG)

def _upload_dns_challange(challenge):
    # create TXT ACME challenge record to route53
    print('setting up ACME TXT for letsencrypt challenge')
    route53_conn = route53.connect(
        aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )
    route53_id = None
    fqdn = tldextract.extract(DOMAIN)
    tld = fqdn.domain + '.' + fqdn.suffix
    # fetch Route53 hosted zone
    for zone in route53_conn.list_hosted_zones():
        # remove trailing . from zone name
        if zone.name[:-1] == tld:
            route53_id = zone.id
    if route53_id is None:
        raise ValueError('domain {} not found in Route53 hosted zones'.format(tld))
    le_challange = challenge['token']
    # Route53 expects values to be "double-quoted"
    le_challange = '"{}"'.format(le_challange)
    print('setting dns-challange as: {0}'.format(le_challange))
    record_name = '_acme-challenge.{0}.'.format(DOMAIN) 
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
    txt_record, change_info = zone.create_txt_record(
        # Notice that this is a full-qualified name.
        name=record_name,
        # let's encrypt challange
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
        print('challange: {0}'.format(le_challange))
        print('dns: {0}'.format(txtdata))
        if le_challange != str(txtdata):
            raise ValueError('TXT {0} failed to propogate'.format(record_name))


def get_lets_encrypt_client():
    # generate_private_key requires cryptography>=0.5
    key = jose.JWKRSA(key=rsa.generate_private_key(
        public_exponent=65537,
        key_size=BITS,
        backend=default_backend()))
    return client.Client(DIRECTORY_URL, key)

def request_acme_challange(acme_client):
    new_reg = messages.NewRegistration.from_data(email=EMAIL)
    le_register = acme_client.register(new_reg)
    # agree to Let's Encrypt's TOS
    acme_client.agree_to_tos(le_register)

    le_auth = acme_client.request_challenges(
        identifier=messages.Identifier(typ=messages.IDENTIFIER_FQDN, value=DOMAIN),
        new_authzr_uri=le_register.new_authzr_uri)
    for challenge in le_auth.body.challenges:
        challenge = challenge.to_json()
        logging.debug(challenge)
        if challenge['type'] == 'dns-01':
            _upload_dns_challange(challenge)
    le_auth, auth_response = acme_client.poll(le_auth)
    print(le_auth)
    # solve acme challange
    solve_acme_challange(acme_client, le_auth, auth_response)

def solve_acme_challange(acme_client, le_auth, auth_response):
    # generate CSR
    result = subprocess.call(['./generate-csr.sh', DOMAIN])
    if result != 0:
        raise ValueError('failed to generate CSR')
    # solve acme challange
    fo = open(CSR_FILE, 'r')
    csr = OpenSSL.crypto.load_certificate_request(
              OpenSSL.crypto.FILETYPE_PEM, fo.read())
    try:
        certr = acme_client.request_issuance(jose.util.ComparableX509(csr), (le_auth,))
    except messages.Error as error:
        print ("domain verification for {domain} failed: {error}".format(domain=DOMAIN, error=error))

if __name__ == '__main__':
    acme_client = get_lets_encrypt_client()
    request_acme_challange(acme_client)
