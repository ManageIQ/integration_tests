# -*- coding: utf-8 -*-
import pytest
from wrapanapi.utils import eval_strings

from cfme.containers.provider import ContainersProvider,\
    ContainersTestItem
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.service import Service
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.template import Template
from cfme.containers.volume import Volume

from cfme.utils import testgen, version
from cfme.utils.version import current_version
from cfme.utils.soft_get import soft_get


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    # The next lines have been removed due to bug introduced in CFME 5.8.1 -
    # https://bugzilla.redhat.com/show_bug.cgi?id=1467639
    # from cfme.containers.container import Container
    #     pytest.mark.polarion('CMP-9945')(
    #         ContainersTestItem(
    #             Container,
    #             'CMP-9945',
    #             expected_fields=[
    #                 'name', 'state', 'last_state', 'restart_count',
    #                 'backing_ref_container_id', 'privileged'
    #             ]
    #         )
    #     ),
    pytest.mark.polarion('CMP-10430')(
        ContainersTestItem(
            Project,
            'CMP-10430',
            expected_fields=['name', 'creation_timestamp', 'resource_version']
        )
    ),
    pytest.mark.polarion('CMP-9877')(
        ContainersTestItem(
            Route,
            'CMP-9877',
            expected_fields=['name', 'creation_timestamp', 'resource_version', 'host_name']
        )
    ),
    pytest.mark.polarion('CMP-9911')(
        ContainersTestItem(
            Pod,
            'CMP-9911',
            expected_fields=[
                'name', 'phase', 'creation_timestamp', 'resource_version',
                'restart_policy', 'dns_policy', 'ip_address'
            ]
        )
    ),
    # TODO Add Node back into the list when other classes are updated to use WT views and widgets.
    # pytest.mark.polarion('CMP-9960')(
    #     ContainersTestItem(
    #         Node,
    #         'CMP-9960',
    #         expected_fields=[
    #             'name', 'creation_timestamp', 'resource_version', 'number_of_cpu_cores',
    #             'memory', 'max_pods_capacity', 'system_bios_uuid', 'machine_id',
    #             'infrastructure_machine_id', 'runtime_version', 'kubelet_version',
    #             'proxy_version', 'operating_system_distribution', 'kernel_version',
    #         ]
    #     )
    # ),
    pytest.mark.polarion('CMP-9978')(
        ContainersTestItem(
            Image,
            'CMP-9978',
            expected_fields={
                version.LOWEST: ['name', 'image_id', 'full_name'],
                '5.7': [
                    'name', 'image_id', 'full_name', 'architecture', 'author',
                    'entrypoint', 'docker_version', 'exposed_ports', 'size'
                ]
            }
        )
    ),
    pytest.mark.polarion('CMP-9890')(
        ContainersTestItem(
            Service,
            'CMP-9890',
            expected_fields=[
                'name', 'creation_timestamp', 'resource_version', 'session_affinity',
                'type', 'portal_ip'
            ]
        )
    ),
    pytest.mark.polarion('CMP-9988')(
        ContainersTestItem(
            ImageRegistry,
            'CMP-9988',
            expected_fields=['host']
        )
    ),
    pytest.mark.polarion('CMP-10316')(
        ContainersTestItem(
            Template,
            'CMP-10316',
            expected_fields=['name', 'creation_timestamp', 'resource_version']
        )
    ),
    pytest.mark.polarion('CMP-10407')(
        ContainersTestItem(Volume,
            'CMP-10407',
            expected_fields=[
                'name',
                'creation_timestamp',
                'resource_version',
                'access_modes',
                'reclaim_policy',
                'status_phase',
                'nfs_server',
                'volume_path']
        )
    )
]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS])
def test_properties(provider, test_item, soft_assert):

    if current_version() < "5.7" and test_item.obj == Template:
        pytest.skip('Templates are not exist in CFME version lower than 5.7. skipping...')

    instances = test_item.obj.get_random_instances(provider, count=2)

    for instance in instances:

        if isinstance(test_item.expected_fields, dict):
            expected_fields = version.pick(test_item.expected_fields)
        else:
            expected_fields = test_item.expected_fields
        for field in expected_fields:
            try:
                soft_get(instance.summary.properties, field)
            except AttributeError:
                soft_assert(False, '{} "{}" properties table has missing field - "{}"'
                                   .format(test_item.obj.__name__, instance.name, field))


def test_pods_conditions(provider, appliance, soft_assert):

    selected_pods_cfme = {pd.name: pd
                          for pd in Pod.get_random_instances(
                              provider, count=3, appliance=appliance)}

    pods_per_ready_status = provider.pods_per_ready_status()
    for pod_name in selected_pods_cfme:
        cfme_pod = selected_pods_cfme[pod_name]

        ose_pod_condition = pods_per_ready_status[pod_name]
        cfme_pod_condition = {_type:
                              eval_strings(
                                  [getattr(getattr(cfme_pod.summary.conditions, _type), "Status")]
                              ).pop()
                              for _type in ose_pod_condition}

        for status in cfme_pod_condition:
            soft_assert(ose_pod_condition[status] == cfme_pod_condition[status],
                        'The Pod {} status mismatch: It is "{}" in openshift while cfme sees "{}".'
                        .format(status, cfme_pod.name, ose_pod_condition[status],
                                cfme_pod_condition[status]))
