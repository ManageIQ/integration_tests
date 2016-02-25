#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
import sys

import yaycl_crypt

from utils import conf

for conf_name in sys.argv[1:]:
    conf_name = conf_name.strip()
    yaycl_crypt.encrypt_yaml(conf, conf_name)
    print('{} conf encrypted'.format(conf_name))
