#!/usr/bin/env python2
from __future__ import unicode_literals
from utils.db import cfmedb

for table_name in cfmedb():
    print(table_name)
