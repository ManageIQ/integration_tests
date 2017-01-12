#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
import argparse
import yaycl_crypt

from utils import conf


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('-e', '--encrypt', default=False, dest='encrypt', action='store_true',
                        help='encrypts the file specified')
    parser.add_argument('-d', '--decrypt', default=False, dest='decrypt', action='store_true',
                        help='decrypts the file specified')
    parser.add_argument('--file', dest='file', default='credentials',
                        help='file name in "conf" to be encrypted/decrypted')
    parser.add_argument('--delete', dest='delete', default=False,
                        help='If set to False, encrypt_yaml will not delete the unencrypted '
                             'config of the same name, and decrypt_yaml will similarly not '
                             'delete its encrypted counterpart.')
    args = parser.parse_args()
    return args


args = parse_cmd_line()
conf_name = args.file.strip()
if args.encrypt:
    yaycl_crypt.encrypt_yaml(conf, conf_name, delete=args.delete)
    print('{} conf encrypted'.format(conf_name))
if args.decrypt:
    yaycl_crypt.decrypt_yaml(conf, conf_name, delete=args.delete)
    print('{} conf decrypted'.format(conf_name))
