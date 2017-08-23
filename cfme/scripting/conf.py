#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
import StringIO

import click

import yaycl_crypt

from cfme.utils import conf


@click.group(help='Functions affecting configuration files')
def main():
    pass


@main.command(help='Tests a yaml file')
@click.argument('conf_name', default='credentials')
def test(conf_name):
    """Test yaml file to see how many keys exist"""
    creds = conf.__getattr__(conf_name)
    print("{} keys found, if this value seems low, there may be a YAML error".format(len(creds)))


@main.command('show-credential', help='Shows the value of a crednetial key')
@click.argument('cred-or-provider-key')
@click.option('--only-credentials', is_flag=True, help='Only search credentials, (not providers)')
def show_credential(cred_or_provider_key, only_credentials):
    """Function to show the given credentials, takes either a provider key or a credential key"""
    data = conf.cfme_data
    if cred_or_provider_key in data.get('management_systems', {}) and not only_credentials:
        endpoints_data = data['management_systems'][cred_or_provider_key].get('endpoints', {})
        for endpoint in endpoints_data:
            print(endpoint)
            cred_key = endpoints_data[endpoint]['credentials']
            cred_dict = conf.credentials[cred_key]
            for k in cred_dict:
                print(" {}: {}".format(k, cred_dict[k]))
    elif cred_or_provider_key in conf.credentials:
        cred_dict = conf.credentials[cred_or_provider_key]
        for k in cred_dict:
            print("{}: {}".format(k, cred_dict[k]))
    else:
        print("Key couldn't be found in providers or credentials YAMLS")


@main.command('show-provider', help='Shows the configuration of a provider')
@click.argument('provider-key')
def show_provider(provider_key):
    """Function to show provider data"""
    output = StringIO.StringIO()
    data = conf.cfme_data
    if provider_key in data.get('management_systems', {}):
        data['management_systems'][provider_key].dump(output)
        print(output.getvalue())
    else:
        print("Key couldn't be found in provider data")


@main.command(help='Encrypts a yaml file')
@click.argument('conf_name', default='credentials')
@click.option('--delete', default=False, is_flag=True,
              help='If supplied delete the unencrypted config of the same name.')
def encrypt(conf_name, delete):
    """Function to encrypt a given conf file"""
    conf_name = conf_name.strip()
    yaycl_crypt.encrypt_yaml(conf, conf_name, delete=delete)
    print('{} conf encrypted'.format(conf_name))
    if not delete:
        print('WARNING: unencrypted file left which will override encrypted')


@main.command(help='Decrypts a yaml file')
@click.argument('conf_name', default='credentials')
@click.option('--delete', default=False, is_flag=True,
              help='If supplied delete the encrypted config of the same name.')
def decrypt(conf_name, delete):
    """Function to decrypt a given conf file"""
    conf_name = conf_name.strip()
    yaycl_crypt.decrypt_yaml(conf, conf_name, delete=delete)
    print('{} conf decrypted'.format(conf_name))


if __name__ == "__main__":
    main()
