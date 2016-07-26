import os
import logging

import boto3
from boto3.s3.transfer import S3Transfer

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import OpenSSL

from acme import client
from acme import messages
from acme import jose

from Crypto.PublicKey import RSA

logging.basicConfig(level=logging.DEBUG)


DIRECTORY_URL = 'https://acme-staging.api.letsencrypt.org/directory'
BITS = 2048  # minimum for Boulder
DOMAIN = 'api.magicka.io'
S3_BUCKET = DOMAIN

# upload ACME challenge to S3 @ .well-known/acme-challenge
s3_client = boto3.client('s3', 'us-east-1')
s3_transfer = S3Transfer(s3_client)
with open('letsencrypt.txt', 'w') as lets_encrypt:
    lets_encrypt.write("letsencrypt")

s3_transfer.upload_file('letsencrypt.txt', S3_BUCKET, 
                      '.well-known/acme-challenge/letsencrypt',
                       extra_args={'ContentType': "text/plain"}
                    )

# generate_private_key requires cryptography>=0.5
key = jose.JWKRSA(key=rsa.generate_private_key(
    public_exponent=65537,
    key_size=BITS,
    backend=default_backend()))
acme = client.Client(DIRECTORY_URL, key)

regr = acme.register()
logging.info('Auto-accepting TOS: %s', regr.terms_of_service)
acme.agree_to_tos(regr)
logging.debug(regr)

authzr = acme.request_challenges(
    identifier=messages.Identifier(typ=messages.IDENTIFIER_FQDN, value=DOMAIN),
    new_authzr_uri=regr.new_authzr_uri)
logging.debug(authzr)

authzr, authzr_response = acme.poll(authzr)

fo = open('csr.der', 'r')
csrreq = OpenSSL.crypto.load_certificate_request(OpenSSL.crypto.FILETYPE_PEM, fo.read())

try:
    acme.request_issuance(jose.util.ComparableX509(csrreq), (authzr,))
except messages.Error as error:
    print ("This script is doomed to fail as no authorization "
           "challenges are ever solved. Error from server: {0}".format(error))