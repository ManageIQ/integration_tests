#!/usr/bin/env python3
#
# Script creates self signed SSL cert and the key necessary to sign it.
# This is based off of the code in this article:
#
#          https://skippylovesmalorie.wordpress.com/2010/02/12/how-to-generate-a-self-signed-certificate-using-pyopenssl/
import argparse
import os
from socket import gethostname

from OpenSSL import crypto

# Defaults
default_country = 'US'
default_state = 'North Carolina'
default_city = 'Durham'
default_organization = 'CFME'
default_organizational_unit = 'QE'


def create_key(key_file):
    """Create SSL key in specified key file."""
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 4096)
    with open(os.path.join(key_file), 'wt') as file:
        file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    return key


def create_cert(
        cert_file,
        key,
        country=default_country,
        state=default_state,
        city=default_city,
        organization=default_organization,
        organizational_unit=default_organizational_unit):
    """Create self-signed SSL Certificate and write it out to the
       specified certificate file.  Will automatically fill in
       the common name with the servers FQDN.

       Args:
           cert_file - name of certificate file to generate
           key - PyOpenSSL PKey object.
           country
           state
           city
           organization
           organizational_unit

    """
    cert = crypto.X509()
    cert.get_subject().C = country
    cert.get_subject().ST = state
    cert.get_subject().L = city
    cert.get_subject().O = organization  # noqa
    cert.get_subject().OU = organizational_unit
    cert.get_subject().CN = gethostname()
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha1')

    with open(os.path.join(cert_file), 'wt') as file:
        file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))


# Process command line arguments:
parser = argparse.ArgumentParser(description='Generate SSL key, CSR, and certs.')
parser.add_argument('--keyFile', required=True)
parser.add_argument('--certFile')
parser.add_argument('--C')
parser.add_argument('--ST')
parser.add_argument('--L')
parser.add_argument('--O')
parser.add_argument('--OU')
args = parser.parse_args()

key = create_key(args.keyFile)

if args.certFile is not None:
    create_cert(
        cert_file=args.certFile,
        key=key,
        country=args.C,
        state=args.ST,
        city=args.L,
        organization=args.O,
        organizational_unit=args.OU,
    )
