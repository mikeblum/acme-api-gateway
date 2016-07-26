import os
import logging
import pprint

import boto3
from boto3.s3.transfer import S3Transfer

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import OpenSSL

from acme import client
from acme import messages
from acme import jose

from acme import challenges
from certbot import achallenges

from Crypto.PublicKey import RSA

logging.basicConfig(level=logging.DEBUG)
pp = pprint.PrettyPrinter(indent=4)


DIRECTORY_URL = 'https://acme-staging.api.letsencrypt.org/directory'
BITS = 2048  # minimum for Boulder
DOMAIN = 'api.magicka.io'
S3_BUCKET = DOMAIN

def upload_token(challenge):
    # upload ACME challenge to S3 @ .well-known/acme-challenge
    s3_client = boto3.client('s3', 'us-east-1')
    s3_transfer = S3Transfer(s3_client)

    token = challenge['token']
    logging.info('Uploading challenge token to S3: {}'.format(token))
    s3_path = '.well-known/acme-challenge/{}'.format(token)
    with open('letsencrypt.txt', 'w') as lets_encrypt:
        lets_encrypt.write(token)

    s3_transfer.upload_file('letsencrypt.txt', S3_BUCKET, 
                          s3_path,
                           extra_args={'ContentType': "text/plain"}
                        )

# generate_private_key requires cryptography>=0.5
key = jose.JWKRSA(key=rsa.generate_private_key(
    public_exponent=65537,
    key_size=BITS,
    backend=default_backend()))
acme = client.Client(DIRECTORY_URL, key)

new_reg = messages.NewRegistration.from_data(email='admin@magicka.io')
regr = acme.register(new_reg)
logging.info('Auto-accepting TOS: %s', regr.terms_of_service)
acme.agree_to_tos(regr)
logging.debug(regr)

authzr = acme.request_domain_challenges(
    DOMAIN,
    new_authzr_uri=regr.new_authzr_uri
)

for challenge in authzr.body.challenges:
    challenge = challenge.to_json()
    if challenge['type'] == 'dns-01':
        upload_token(challenge)

authzr, authzr_response = acme.poll(authzr)
logging.debug(authzr_response)

fo = open('csr.der', 'r')
csrreq = OpenSSL.crypto.load_certificate_request(OpenSSL.crypto.FILETYPE_PEM, fo.read())

try:
    acme.request_issuance(jose.util.ComparableX509(csrreq), (authzr,))
except messages.Error as error:
    print ("This script is doomed to fail as no authorization "
           "challenges are ever solved. Error from server: {0}".format(error))