#!/usr/bin/env python2
from utils.db import cfmedb

for table_name in cfmedb():
    print(table_name)
