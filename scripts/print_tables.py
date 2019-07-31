#!/usr/bin/env python3
from cfme.utils.appliance import current_appliance

for table_name in current_appliance.db.client:
    print(table_name)
