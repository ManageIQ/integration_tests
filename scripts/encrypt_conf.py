#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Script to encrypt config files.

Usage:

   scripts/encrypt_conf.py confname1 confname2 ... confnameN
   scripts/encrypt_conf.py credentials
"""
import sys
from utils import _conf

for conf_name in sys.argv[1:]:
    _conf.encrypt_yaml(conf_name.strip())
