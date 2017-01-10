#!/usr/bin/env python2
from cfme.utils.db import cfmedb

for table_name in cfmedb():
    print(table_name)
