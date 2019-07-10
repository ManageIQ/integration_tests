import re
from collections import namedtuple
from datetime import datetime
from random import random

import pytest


vpor_values_pattern = """---
:avg:
  :cpu_usagemhz_rate_average: {}
  :derived_memory_used: {}
  :max_cpu_usage_rate_average: {}
  :max_mem_usage_absolute_average: {}
:dev:
  :cpu_usagemhz_rate_average: {}
  :derived_memory_used: {}
  :max_cpu_usage_rate_average: {}
  :max_mem_usage_absolute_average: {}
"""

vpor_data_instance = namedtuple('vpor_data_instance',
                                [
                                    'resource_type',
                                    'resource_id',
                                    'resource_name',
                                    'cpu_usagemhz_rate_average',
                                    'derived_memory_used',
                                    'max_cpu_usage_rate_average',
                                    'max_mem_usage_absolute_average'
                                ])

cpu_usagemhz_rate_average__data_range = 8196  # 13 bit depth
derived_memory_used__data_range = 100  # Percents
max_cpu_usage_rate_average__data_range = 8196  # 13 bit depth
max_mem_usage_absolute_average__data_range = 100  # Percents


def gen_vpor_values():
    return vpor_values_pattern.format(
        random(), random() * cpu_usagemhz_rate_average__data_range,
        random() * derived_memory_used__data_range,
        random() * derived_memory_used__data_range,
        random(), random() * max_cpu_usage_rate_average__data_range,
        random() * max_mem_usage_absolute_average__data_range,
        random() * max_mem_usage_absolute_average__data_range
    )


@pytest.fixture(scope='module')
def vporizer(appliance):

    """Grabbing vim_performance_operating_ranges table data for nodes and projects.
    In case that no such data exists, inserting fake rows"""

    db = appliance.db.client
    vpor = db['vim_performance_operating_ranges']

    container_nodes = db['container_nodes']
    container_pods = db['container_groups']
    container_projects = db['container_projects']
    created_at = datetime.now()
    vpor_data_list = []

    tables_2_names = list(zip(
        (container_nodes, container_projects, container_pods),
        ('ContainerNode', 'ContainerProject', 'ContainerGroup')
    ))
    for table, resource_type in tables_2_names:
        ids = []
        for resource in db.session.query(table).all():
            def get_resource_vpor_data():
                return vpor.__table__.select().where(
                    (vpor.resource_id == resource.id) &
                    (vpor.resource_type == resource_type)
                ).execute().fetchone()
            # Checking whether values has already inserted to the table for this resource.
            # Should be True only in case that the appliance age is greater than 24h
            # if there isn't such row, insert...
            if not get_resource_vpor_data():
                ids.append(
                    vpor.__table__.insert().values(
                        resource_type=resource_type, resource_id=resource.id,
                        created_at=created_at, days=30, updated_at=datetime.now(),
                        time_profile_id=1, values=gen_vpor_values()
                    ).execute().inserted_primary_key[0]
                )
            # now, collecting the values from the table
            resource_vpor_data = get_resource_vpor_data()
            vpor_values_match = re.search(vpor_values_pattern.replace('{}', r'([\d\.\-e]+)'),
                                          resource_vpor_data['values'])
            if not vpor_values_match:
                raise Exception('Could not parse VPOR values from row: values={}'
                                .format(resource_vpor_data['values']))
            vpor_values = [float(v) for v in vpor_values_match.groups()]
            vpor_data_list.append(
                vpor_data_instance(
                    resource_vpor_data['resource_type'],
                    resource_vpor_data['resource_id'], resource.name,
                    vpor_values[0], vpor_values[1], vpor_values[2], vpor_values[3]
                )
            )

    yield vpor_data_list

    vpor.__table__.delete().where(vpor.id.in_(ids)).execute()
