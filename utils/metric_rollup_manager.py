from datetime import datetime, timedelta
from random import choice, randrange
from cached_property import cached_property

import fauxfactory

from cfme.containers.provider import ContainersProvider
from utils.providers import list_providers_by_class


class MetricRollupManager(object):

    def __init__(self, appliance):
        self._pushed_metrics = []
        self._metric_rollups_tbl = appliance.db.get('metric_rollups')

    @cached_property
    def _default_resource_params(self):
        """Used for generate default resource parameters, ones in a session
        Returns: metric_rollups table and resource parameters dict"""
        out = {}
        provider = choice(list_providers_by_class(ContainersProvider))
        out['parent_ems_id'] = provider.ems_id
        out['resource_id'] = out['parent_ems_id']
        out['resource_name'] = provider.name
        out['resource_type'] = 'ExtManagementSystem'
        return out

    @cached_property
    def columns(self):
        return self._metric_rollups_tbl.__table__.columns

    @property
    def pushed_metrics(self):
        return self._pushed_metrics

    def delete_all(self):
        """Delete all the pushed rollups (self._pushed_metrics),
        using the creation time as whereclause (accurate enough)"""
        creation_times = [metric['created_on'] for metric in self._pushed_metrics]
        self._metric_rollups_tbl.__table__.delete().where(
            self._metric_rollups_tbl.created_on.in_(creation_times)
        ).execute()
        self._pushed_metrics = []

    def push_metric_rollup(self, **kwargs):

        """Pushing metrics into metric_rollups with the given resources

            Args:
                * kwargs: values to insert, each field that hasn't supplied
                          will get a random value
            Returns:
                metric rollup inserted parameters
        """

        res_default = self._default_resource_params
        capture_interval_name = kwargs.get('capture_interval_name', choice(['daily', 'hourly']))

        prox = self._metric_rollups_tbl.__table__.insert().values(
            resource_type=kwargs.get('resource_type', res_default['resource_type']),
            resource_name=kwargs.get('resource_name', res_default['resource_name']),
            resource_id=kwargs.get('resource_id', res_default['resource_id']),
            parent_ems_id=kwargs.get('parent_ems_id', res_default['parent_ems_id']),
            capture_interval_name=capture_interval_name,
            timestamp=kwargs.get('timestamp', (datetime.now() - (
                timedelta(hours=randrange(24)) if capture_interval_name == 'hourly'
                else timedelta(days=randrange(30))))),
            time_profile_id=kwargs.get('time_profile_id', 1),
            created_on=kwargs.get('created_on', datetime.now()),
            cpu_usage_rate_average=kwargs.get('cpu_usage_rate_average',
                                              fauxfactory.gen_integer(1, 100)),
            mem_usage_absolute_average=kwargs.get('mem_usage_absolute_average',
                                                  fauxfactory.gen_integer(1, 100)),
            derived_vm_numvcpus=kwargs.get('derived_vm_numvcpus',
                                           fauxfactory.gen_integer(1, 4)),
            net_usage_rate_average=kwargs.get('net_usage_rate_average',
                                              fauxfactory.gen_integer(1, 1000)),
            derived_memory_available=kwargs.get('derived_memory_available', 8192),
            derived_memory_used=kwargs.get('derived_memory_used',
                                           fauxfactory.gen_integer(1, 8192)),
            stat_container_group_create_rate=kwargs.get(
                'stat_container_group_create_rate', fauxfactory.gen_integer(1, 100)),
            stat_container_group_delete_rate=kwargs.get(
                'stat_container_group_delete_rate', fauxfactory.gen_integer(1, 50)),
            stat_container_image_registration_rate=kwargs.get(
                'stat_container_image_registration_rate', fauxfactory.gen_integer(1, 25)),
            tag_names=kwargs.get('tag_names', 'environment/prod')
        ).execute()

        self._pushed_metrics.append(prox.last_inserted_params())
        return self._pushed_metrics[-1]
