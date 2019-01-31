import fauxfactory
import operator
import pytest
import six


from cfme.services.myservice import MyService
from cfme.services.workloads import VmsInstances, TemplatesImages
from cfme.infrastructure.config_management import ConfigManager, ConfigSystem
from cfme.utils.appliance.implementations.ui import navigate_to

from collections import namedtuple
from cfme.utils.blockers import BZ

Param = namedtuple("Param", ["collection", "destination", "entity", "filter", "my_filters"])

params_values = [
    Param(MyService, 'All', 'myservices', 'Service : Name', 'myservice'),
    Param(VmsInstances, 'All', 'workloads_vms', 'VM and Instance : Name',
     ('vms', "All VMs & Instances")),
    Param(TemplatesImages, 'All', 'workloads_templates', 'VM Template and Image : Name',
     ('templates', "All Templates & Images")),

    Param('cloud_providers', 'All', 'cloudprovider', 'Cloud Provider : Name', None),
    Param('cloud_av_zones', 'All', 'availabilityzone', 'Availability Zone : Name', None),
    Param('cloud_host_aggregates', 'All', 'hostaggregate', 'Host Aggregate : Name', None),
    Param('cloud_tenants', 'All', 'tenant', 'Cloud Tenant : Name', None),
    Param('cloud_flavors', 'All', 'flavor', 'Flavor : Name', None),
    Param('cloud_instances', 'All', 'instances', 'Instance : Name',
     ('sidebar.instances', "All Instances")),
    Param('cloud_images', 'All', 'images', 'Image : Name', ('sidebar.images', "All Images")),
    Param('cloud_stacks', 'All', 'orchestration_stacks', 'Orchestration Stack : Name', None),
    Param('cloud_keypairs', 'All', 'key_pairs', 'Key Pair : Name', None),

    Param('infra_providers', 'All', 'infraproviders', 'Infrastructure Provider : Name', None),
    Param('clusters', 'All', 'clusters', 'Cluster / Deployment Role : Name', None),
    Param('hosts', 'All', 'hosts', 'Host / Node : Name', None),
    Param('infra_vms', 'VMsOnly', 'vms', 'Virtual Machine : Name', ('sidebar.vms', "All VMs")),
    Param('infra_templates', 'TemplatesOnly', 'templates', 'Template : Name',
     ('sidebar.templates', "All Templates")),
    Param('resource_pools', 'All', 'resource_pools', 'Resource Pool : Name', None),
    Param('datastores', 'All', 'datastores', 'Datastore : Name',
     ('sidebar.datastores', "All Datastores")),

    Param('physical_providers', 'All', 'physical_providers',
          'Physical Infrastructure Provider : Name', None),
    Param('physical_servers', 'All', 'physical_servers', 'Physical Server : Name', None),

    Param('containers_providers', 'All', 'container_providers', 'Containers Provider : Name', None),
    Param('container_projects', 'All', 'container_projects', 'Container Project : Name', None),
    Param('container_routes', 'All', 'container_routes', 'Container Route : Name', None),
    Param('container_services', 'All', 'container_services', 'Container Service : Name', None),
    Param('container_replicators', 'All', 'container_replicators', 'Container Replicator : Name',
          None),
    Param('container_pods', 'All', 'container_pods', 'Container Pod : Name', None),
    Param('containers', 'All', 'containers', 'Container : Name', None),
    Param('container_nodes', 'All', 'container_nodes', 'Container Node : Name', None),
    Param('container_volumes', 'All', 'container_volumes', 'Persistent Volume : Name', None),
    Param('container_builds', 'All', 'container_builds', 'Container Build : Name', None),
    Param('container_image_registries', 'All', 'image_registries',
          'Container Image Registry : Name', None),
    Param('container_images', 'All', 'container_images', 'Container Image : Name', None),
    Param('container_templates', 'All', 'container_templates', 'Container Template : Name', None),

    Param(ConfigManager, 'All', 'configuration_management', 'Configuration Manager : Name',
     ('sidebar.providers', "All Configuration Management Providers")),
    Param(ConfigSystem, 'All', 'configuration_management_systems',
     'Configured System (Red Hat Satellite) : Hostname',
     ('sidebar.configured_systems', "All Configured Systems")),

    Param('network_providers', 'All', 'network_managers', 'Network Manager : Name', None),
    Param('cloud_networks', 'All', 'network_networks', 'Cloud Network : Name', None),
    Param('network_subnets', 'All', 'network_subnets', 'Cloud Subnet : Name', None),
    Param('network_routers', 'All', 'network_routers', 'Network Router : Name', None),
    Param('network_security_groups', 'All', 'network_security_groups', 'Security Group : Name',
          None),
    Param('network_floating_ips', 'All', 'network_floating_ips', 'Floating IP : Address', None),
    Param('network_ports', 'All', 'network_ports', 'Network Port : Name', None),
    Param('balancers', 'All', 'network_load_balancers', 'Load Balancer : Name', None),

    Param('volumes', 'All', 'block_store_volumes', 'Cloud Volume : Name', None),
    Param('volume_snapshots', 'All', 'block_store_snapshots', 'Cloud Volume Snapshot : Name', None),
    Param('volume_backups', 'All', 'block_store_backups', 'Cloud Volume Backup : Name', None),

    Param('object_store_containers', 'All', 'object_store_containers',
     'Cloud Object Store Container : Name', None),
    Param('object_store_objects', 'All', 'object_store_objects',
     'Cloud Object Store Object : Name', None),

    Param('ansible_tower_providers', 'All', 'ansible_tower_explorer_provider',
     'Automation Manager (Ansible Tower) : Name',
     ('sidebar.providers', 'All Ansible Tower Providers')),
    Param('ansible_tower_systems', 'All', 'ansible_tower_explorer_system',
     'Configured System (Ansible Tower) : Hostname',
     ('sidebar.configured_systems', 'All Ansible Tower Configured Systems')),
    Param('ansible_tower_job_templates', 'All', 'ansible_tower_explorer_job_templates',
     'Template (Ansible Tower) : Name', ('sidebar.job_templates', 'All Ansible Tower Templates')),
    Param('ansible_tower_job_templates', 'All', 'ansible_tower_explorer_job_templates',
     'Job Template (Ansible Tower) : Name',
     ('sidebar.job_templates', 'All Ansible Tower Job Templates')),

    Param('ansible_tower_jobs', 'All', 'ansible_tower_jobs', 'Ansible Tower Job : Name', None)
]

pytestmark = [
    pytest.mark.parametrize(
        'param', params_values,
        ids=['{}-{}'.format(param.entity, param.destination.lower()) for param in params_values]
    ),
    pytest.mark.uncollectif(lambda param, appliance: (
        (param.collection in (MyService, 'physical_providers', 'physical_servers', 'volume_backups',
                       'volume_snapshots') and appliance.version < '5.9') or
        (param.collection in (ConfigManager, 'ansible_tower_providers') and
         appliance.version > '5.10') or
        (param.filter == 'Template (Ansible Tower) : Name' and appliance.version < '5.10') or
        (param.filter == 'Job Template (Ansible Tower) : Name' and appliance.version > '5.10')))
]


def _navigation(param, appliance):
    if isinstance(param.collection, six.string_types):
        view = navigate_to(getattr(appliance.collections, param.collection), param.destination)
    else:
        view = navigate_to(param.collection, param.destination)
    return view


def _filter_displayed(filters, filter):
    if filters.is_displayed:
        assert filter, "Filter wasn't created!"
    else:
        pytest.fail("Filter wasn't created or filters tree is not displayed!")


def _select_filter(filters, filter_name, param):
    if param.my_filters:
        if isinstance(param.my_filters, tuple):
            filters.tree.click_path(param.my_filters[1], "My Filters", filter_name)
        else:
            filters.tree.click_path("My Filters", filter_name)
    else:
        filters.navigation.select(filter_name)


def test_advanced_search_button_displayed(param, appliance):
    """
    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/30h
    """
    view = _navigation(param, appliance)
    if not view.search.is_advanced_search_possible:
        pytest.fail(
            "Advanced search button is not displayed for {}_{}".format(
                param.entity, param.destination.lower())
        )


def test_can_open_advanced_search(param, appliance):
    """
    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/30h
    """
    view = _navigation(param, appliance)
    view.search.open_advanced_search()
    if not view.search.is_advanced_search_opened:
        pytest.fail("Advanced search cannot be opened for {}_{}".format(
            param.destination, param.entity.lower())
        )
    view.search.close_advanced_search()


@pytest.mark.uncollectif(lambda param, appliance: (
    (param.collection in (MyService, 'physical_providers', 'physical_servers', 'volume_backups',
                          'volume_snapshots') and appliance.version < '5.9') or
    (param.collection in (ConfigManager, 'ansible_tower_providers') and appliance.version > '5.10')
    or (param.filter == 'Template (Ansible Tower) : Name' and appliance.version < '5.10') or
    (param.filter == 'Job Template (Ansible Tower) : Name' and appliance.version > '5.10') or
    (param.collection in ('cloud_host_aggregates', 'cloud_instances', 'cloud_images', 'infra_vms',
                          'infra_templates', 'datastores', ConfigManager, 'ansible_tower_providers',
                          'ansible_tower_systems', 'ansible_tower_job_templates', VmsInstances)
    and appliance.version < '5.10'))
    or (param.collection == TemplatesImages and BZ(1626579)) or (param.collection == MyService
                                                                 and BZ(1627078)))
def test_filter_crud(param, appliance):
    """
    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_string('alphanumeric', 10)
    filter_value = fauxfactory.gen_string('alphanumeric', 10)
    filter_value_updated = fauxfactory.gen_string('alphanumeric', 10)
    view = _navigation(param, appliance)
    # create
    view.search.save_filter(
        "fill_field({}, =, {})".format(param.filter, filter_value), filter_name)
    view.search.close_advanced_search()
    view.flash.assert_no_error()
    # read
    if param.my_filters:
        if isinstance(param.my_filters, tuple):
            filters = operator.attrgetter(param.my_filters[0])(view)
            _filter_displayed(filters, filters.tree.has_path(param.my_filters[1], "My Filters",
                                                             filter_name))
        else:
            filters = operator.attrgetter(param.my_filters)(view)
            _filter_displayed(filters, filters.tree.has_path("My Filters", filter_name))
    else:
        filters = view.my_filters
        _filter_displayed(filters, filters.navigation.has_item(filter_name))
    # update
    _select_filter(filters, filter_name, param)
    view.search.open_advanced_search()
    view.search.advanced_search_form.search_exp_editor.select_first_expression()
    view.search.advanced_search_form.search_exp_editor.fill_field(field=param.filter,
                                                                  key='=',
                                                                  value=filter_value_updated)
    # save expression
    view.search.advanced_search_form.save_filter_button.click()
    # save filter
    view.search.advanced_search_form.save_filter_button.click()
    view.search.close_advanced_search()
    _select_filter(filters, filter_name, param)
    # read after update
    view.search.open_advanced_search()
    exp_text = view.search.advanced_search_form.search_exp_editor.expression_text
    assert filter_value_updated in exp_text, "Filter wasn't changed!"
    # delete
    view.search.delete_filter()
    view.search.close_advanced_search()
    if param.my_filters:
        if filters.is_displayed:
            if isinstance(param.my_filters, tuple):
                assert not filters.tree.has_path(param.my_filters[1], "My Filters",
                                                 filter_name), "Filter wasn't deleted!"
            else:
                assert not filters.tree.has_path("My Filters",
                                                 filter_name), "Filter wasn't deleted!"
    else:
        if view.my_filters.is_displayed:
            assert not view.my_filters.navigation.has_item(filter_name), "Filter wasn't deleted!"
