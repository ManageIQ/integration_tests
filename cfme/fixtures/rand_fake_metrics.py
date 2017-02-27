from datetime import datetime, timedelta
from random import sample

import pytest

from cfme.containers.provider import ContainersProvider
from utils.providers import list_providers_by_class
from utils.metric_rollup_manager import MetricRollupManager


@pytest.yield_fixture(scope='session')
def rand_fake_metrics(appliance):
    """This fixture used to create random (fake) metrics.
    Delete fake metrics at the end of the session.
    """
    rollup_manager = MetricRollupManager(appliance)
    provider = list_providers_by_class(ContainersProvider)[-1]
    ext_management_systems = appliance.db['ext_management_systems']
    ems_id = ext_management_systems.__table__.select().where(
        ext_management_systems.name == provider.name
    ).execute().fetchall()[0].id

    container_projects = appliance.db['container_projects']
    projects = container_projects.__table__.select().where(True).execute().fetchall()
    projects = sample(projects, min(3, len(projects)))

    container_nodes = appliance.db['container_nodes']
    nodes = container_nodes.__table__.select().where(
        container_nodes.ems_id == ems_id).execute().fetchall()

    for days_ago in xrange(30):

        timestamp = datetime.now() - timedelta(days=days_ago)
        rollup_manager.push_metric_rollup(
            resource_type='ExtManagementSystem', resource_name=provider.name,
            resource_id=ems_id, timestamp=timestamp,
            capture_interval_name="daily", parent_ems_id=ems_id
        )
        for project in projects:
            rollup_manager.push_metric_rollup(
                resource_type='ContainerProject', resource_name=project.name,
                resource_id=project.id, timestamp=timestamp,
                capture_interval_name="daily", parent_ems_id=ems_id
            )
        for node in nodes:
            rollup_manager.push_metric_rollup(
                resource_type='ContainerNode', resource_name=node.name,
                resource_id=node.id, timestamp=timestamp,
                capture_interval_name="daily", parent_ems_id=ems_id
            )

    for hour_ago in xrange(24):

        timestamp = datetime.now() - timedelta(days=hour_ago)

        for project in projects:
            rollup_manager.push_metric_rollup(
                resource_type='ContainerProject', resource_name=project.name,
                resource_id=project.id, timestamp=timestamp,
                capture_interval_name="hourly", parent_ems_id=ems_id
            )
        for node in nodes:
                rollup_manager.push_metric_rollup(
                    resource_type='ContainerNode', resource_name=node.name,
                    resource_id=node.id, timestamp=timestamp,
                    apture_interval_name="hourly", parent_ems_id=ems_id
                )

    yield rollup_manager.pushed_metrics

    rollup_manager.delete_all()
