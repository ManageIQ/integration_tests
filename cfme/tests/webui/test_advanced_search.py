import pytest
import six

from cfme.services.myservice import MyService
from cfme.services.workloads import VmsInstances, TemplatesImages
from cfme.utils.appliance.implementations.ui import navigate_to

params_values = [
    (MyService, 'All', 'myservices', 'Service : Name'),
    (VmsInstances, 'All', 'workloads_vms', 'VM and Instance : Name'),
    (TemplatesImages, 'All', 'workloads_templates', 'VM Template and Image : Name'),

    ('cloud_providers', 'All', 'cloudprovider', 'Cloud Provider : Name'),
    ('cloud_av_zones', 'All', 'availabilityzone', 'Availability Zone : Name'),
    ('cloud_host_aggregates', 'All', 'hostaggregate', 'Host Aggregate : Name'),
    ('cloud_tenants', 'All', 'tenant', 'Cloud Tenant : Name'),
    ('cloud_flavors', 'All', 'flavor', 'Flavor : Name'),
    ('cloud_instances', 'All', 'instances', 'Instance : Name'),
    ('cloud_images', 'All', 'images', 'Image : Name'),
    ('cloud_stacks', 'All', 'orchestration_stacks', 'Orchestration Stack : Name'),
    ('cloud_keypairs', 'All', 'key_pairs', 'Key Pair : Name'),

    ('infra_providers', 'All', 'infraproviders', 'Infrastructure Provider : Name'),
    ('clusters', 'All', 'clusters', 'Cluster / Deployment Role : Name'),
    ('hosts', 'All', 'hosts', 'Host / Node : Name'),
    ('infra_vms', 'VMsOnly', 'vms', 'Virtual Machine : Name'),
    ('infra_templates', 'TemplatesOnly', 'templates', 'Template : Name'),
    ('resource_pools', 'All', 'resource_pools', 'Resource Pool : Name'),
    ('datastores', 'All', 'datastores', 'Datastore : Name'),

    ('physical_providers', 'All', 'physical_providers', 'Physical Infrastructure Provider : Name'),
    ('physical_servers', 'All', 'physical_servers', 'Physical Server : Name'),

    ('containers_providers', 'All', 'container_providers', 'Containers Provider : Name'),
    ('container_projects', 'All', 'container_projects', 'Container Project : Name'),
    ('container_routes', 'All', 'container_routes', 'Container Route : Name'),
    ('container_services', 'All', 'container_services', 'Container Service : Name'),
    ('container_replicators', 'All', 'container_replicators', 'Container Replicator : Name'),
    ('container_pods', 'All', 'container_pods', 'Container Pod : Name'),
    ('containers', 'All', 'containers', 'Container : Name'),
    ('container_nodes', 'All', 'container_nodes', 'Container Node : Name'),
    ('container_volumes', 'All', 'container_volumes', 'Persistent Volume : Name'),
    ('container_builds', 'All', 'container_builds', 'Container Build : Name'),
    ('container_image_registries', 'All', 'image_registries', 'Container Image Registry : Name'),
    ('container_images', 'All', 'container_images', 'Container Image : Name'),
    ('container_templates', 'All', 'container_templates', 'Container Template : Name'),

    ('config_manager', 'All', 'configuration_management', 'Configuration Manager : Name'),
    ('config_system', 'All', 'configuration_management_systems',
     'Configured System (Red Hat Satellite) : Hostname'),

    ('network_providers', 'All', 'network_managers', 'Network Manager : Name'),
    ('cloud_networks', 'All', 'network_networks', 'Cloud Network : Name'),
    ('network_subnets', 'All', 'network_subnets', 'Cloud Subnet : Name'),
    ('network_routers', 'All', 'network_routers', 'Network Router : Name'),
    ('network_security_groups', 'All', 'network_security_groups', 'Security Group : Name'),
    ('network_floating_ips', 'All', 'network_floating_ips', 'Floating IP : Address'),
    ('network_ports', 'All', 'network_ports', 'Network Port : Name'),
    ('balancers', 'All', 'network_load_balancers', 'Load Balancer : Name'),

    ('volumes', 'All', 'block_store_volumes', 'Cloud Volume : Name'),
    ('volume_snapshots', 'All', 'block_store_snapshots', 'Cloud Volume Snapshot : Name'),
    ('volume_backups', 'All', 'block_store_backups', 'Cloud Volume Backup : Name'),

    ('object_store_containers', 'All', 'object_store_containers',
     'Cloud Object Store Container : Name'),
    ('object_store_objects', 'All', 'object_store_objects',
     'Cloud Object Store Object : Name'),

    ('ansible_tower_providers', 'All', 'ansible_tower_explorer_provider',
     'Automation Manager (Ansible Tower) : Name'),
    ('ansible_tower_systems', 'All', 'ansible_tower_explorer_system',
     'Configured System (Ansible Tower) : Hostname'),
    ('ansible_tower_job_templates', 'All', 'ansible_tower_explorer_job_templates',
     'Job Template (Ansible Tower) : Name'),
    ('ansible_tower_jobs', 'All', 'ansible_tower_jobs', 'Ansible Tower Job : Name'),
]

pytestmark = [
    pytest.mark.parametrize(
        'params', params_values,
        ids=['{}-{}'.format(param[2], param[1].lower()) for param in params_values]
    ),
    pytest.mark.uncollectif(lambda params, appliance: params[0] in (MyService, 'physical_providers',
        'physical_servers', 'volume_backups', 'volume_snapshots') and appliance.version < 5.9)
]


def _navigation(params, appliance):
    if isinstance(params[0], six.string_types):
        view = navigate_to(getattr(appliance.collections, params[0]), params[1])
    else:
        view = navigate_to(params[0], params[1])
    return view


def test_advanced_search_button_displayed(params, appliance):
    view = _navigation(params, appliance)
    if not view.search.is_advanced_search_possible:
        pytest.fail(
            "Advanced search button is not displayed for {}_{}".format(
                params[2], params[1].lower())
        )


def test_can_open_advanced_search(params, appliance):
    view = _navigation(params, appliance)
    view.search.open_advanced_search()
    if not view.search.is_advanced_search_opened:
        pytest.fail("Advanced search cannot be opened for {}_{}".format(
            params[2], params[1].lower())
        )
