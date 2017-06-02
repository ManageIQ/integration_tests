#!/usr/bin/env python2
from utils.appliance import current_appliance

for table_name in current_appliance.db:
    print(table_name)
