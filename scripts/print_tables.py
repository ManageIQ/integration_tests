#!/usr/bin/env python
'''
Created on Jun 19, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-

# pylint: disable=C0103
# pylint: disable=E1101
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import Table
from sqlalchemy import event
import db

metadata = MetaData()
metadata.bind = engine = create_engine(os.environ.get('CFME_DB_URL'))
metadata.reflect()

ignore_tables = ['schema_migrations']
join_tables = ['conditions_miq_policies', 'hosts_storages', 
            'vdi_desktop_pools_vdi_users', 'vdi_desktops_vdi_users',
            'miq_roles_features', 'miq_servers_product_updates',
            'storages_vms_and_templates', 'miq_proxies_product_updates',
            'ext_management_systems_vdi_desktop_pools']
bad_tables = ignore_tables + join_tables

for table in metadata.sorted_tables:
    # Punt on join tables for now
    # if table.name in bad_tables:
    #     continue
    name = table.name
    new_name = ""
    got_underscore = False
    for idx, char in enumerate(name):
        if idx == 0 or got_underscore:
            new_name += char.upper()
            got_underscore = False
        elif char == '_':
            got_underscore = True
        elif char == 's' and idx == len(name) - 1:
            pass
        elif char == 's' and name[idx+1] == '_':
            pass
        else:
            new_name += char
    if new_name[-2:] == 'ie':
        new_name = new_name[:-2] + 'y'

    print "'%s': '%s'," % (new_name, name)
