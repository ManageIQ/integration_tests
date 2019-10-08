from cfme.utils.log import logger


def _remove_page(roles, group, pages):
    if group in roles:
        for page in pages:
            if page in roles[group]:
                roles[group].remove(page)
            else:
                logger.info("Page %s attempted to be removed from role %s, "
                            "but isn't in there anyway", page, group)
    else:
        logger.info("Attempted to remove a page from role %s, but role "
                    "doesn't exist", group)


def _remove_from_all(roles, r_page):
    for group in roles:
        for page in roles[group]:
            if page == r_page:
                roles[group].remove(page)
            else:
                logger.info("Page %s attempted to be removed from role %s, "
                            "but isn't in there anyway", page, group)


group_data = {
    'evmgroup-administrator': [
        'control_explorer',
        'control_simulation',
        'control_import_export',
        'control_log',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'infrastructure_pxe',
        'infrastructure_requests',
        'clouds_providers',
        'clouds_availability_zones',
        'clouds_flavors',
        'clouds_security_groups',
        'clouds_instances',
        'clouds_stacks',
        'my_settings',
        'tasks',
        'about',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'automate_explorer',
        'automate_simulation',
        'automate_customization',
        'automate_import_export',
        'automate_log',
        'automate_requests',
        'my_services',
        'services_catalogs',
        'services_requests',
        'services_workloads',
        'utilization',
        'planning',
        'bottlenecks'
    ],
    'evmgroup-approver': [
        'control_explorer',
        'control_simulation',
        'control_log',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'infrastructure_pxe',
        'infrastructure_requests',
        'clouds_instances',
        'my_settings',
        'tasks',
        'about',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'services_requ,ests'
        'services_workloads'
    ],
    'evmgroup-auditor': [
        'control_explorer',
        'control_simulation',
        'control_log',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'infrastructure_pxe',
        'clouds_instances',
        'my_settings',
        'tasks',
        'about',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'services_workloads',
        'utilization',
        'planning',
        'bottlenecks'
    ],
    'evmgroup-desktop': [
        'services_requests',
        'services_workloads',
        'dashboard',
        'infrastructure_config_management',
        'infrastructure_requests',
        'infrastructure_virtual_machines',
        'clouds_instances',
        'my_settings',
        'about'
    ],
    'evmgroup-operator': [
        'services_workloads',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'infrastructure_pxe',
        'clouds_instances',
        'my_settings',
        'tasks',
        'about'
    ],
    'evmgroup-security': [
        'control_explorer',
        'control_simulation',
        'control_log',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'clouds_instances',
        'my_settings',
        'tasks',
        'about',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'services_workloads'
    ],
    'evmgroup-super_administrator': [
        'control_explorer',
        'control_simulation',
        'control_import_export',
        'control_log',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'infrastructure_pxe',
        'infrastructure_requests',
        'infrastructure_config_management',
        'clouds_providers',
        'clouds_availability_zones',
        'clouds_flavors',
        'clouds_security_groups',
        'clouds_instances',
        'clouds_tenants',
        'clouds_stacks',
        'my_settings',
        'tasks',
        'configuration',
        'about',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'automate_explorer',
        'automate_simulation',
        'automate_customization',
        'automate_import_export',
        'automate_log',
        'automate_requests',
        'my_services',
        'services_catalogs',
        'services_requests',
        'services_workloads',
        'utilization',
        'planning',
        'bottlenecks'
    ],
    'evmgroup-support': [
        'control_explorer',
        'control_simulation',
        'control_log',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'clouds_instances',
        'my_settings',
        'tasks',
        'about',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'services_workloads'
    ],
    'evmgroup-user': [
        'services_workloads',
        'services_requests',
        'dashboard',
        'reports',
        'chargeback',
        'timelines',
        'rss',
        'infrastructure_providers',
        'infrastructure_clusters',
        'infrastructure_hosts',
        'infrastructure_virtual_machines',
        'infrastructure_resource_pools',
        'infrastructure_datastores',
        'infrastructure_requests',
        'clouds_instances',
        'my_settings',
        'tasks',
        'about'
    ],
    'evmgroup-user_limited_self_service': [
        'clouds_instances',
        'services_requests',
        'infrastructure_virtual_machines',
        'infrastructure_requests',
        'my_settings',
        'about'
    ],
    'evmgroup-user_self_service': [
        'clouds_instances',
        'services_requests',
        'infrastructure_config_management',
        'infrastructure_virtual_machines',
        'infrastructure_requests',
        'my_settings',
        'about'
    ],
    'evmgroup-vm_user': [
        'clouds_instances',
        'infrastructure_config_management',
        'infrastructure_virtual_machines',
        'infrastructure_requests',
        'services_requests',
        'services_workloads',
        'my_settings',
        'about'
    ]
}

# Matches structure/string format of VerticalNavigation output for tree, not UI access control tree
# TODO include non-vertical nav RBAC to settings, help
# TODO RBAC goes deeper than veritcal nav, into accordions. example cloud intel -> Reports
role_access_ui_510z = {
    'evmgroup-super_administrator': {
        'Automation': {
            'Ansible': ['Credentials', 'Repositories', 'Playbooks'],
            'Ansible Tower': ['Jobs', 'Explorer'],
            'Automate': ['Log', 'Generic Objects', 'Simulation', 'Import / Export', 'Customization',
                         'Requests', 'Explorer']},
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Flavors', 'Instances', 'Providers', 'Host Aggregates', 'Availability Zones',
                       'Key Pairs', 'Tenants', 'Stacks', 'Topology'],
            'Containers': ['Container Nodes', 'Containers', 'Providers', 'Overview',
                           'Container Templates', 'Image Registries', 'Container Builds',
                           'Container Services', 'Volumes', 'Container Images', 'Routes', 'Pods',
                           'Replicators', 'Projects', 'Topology'],
            'Infrastructure': ['Datastores', 'Networking', 'Providers', 'Virtual Machines', 'Hosts',
                               'Clusters', 'Topology', 'PXE', 'Resource Pools'],
            'Physical Infrastructure': ['Overview', 'Providers', 'Chassis', 'Racks', 'Switches',
                                        'Servers', 'Storages', 'Topology'],
            'Migration': ['Migration Plans', 'Infrastructure Mappings', 'Migration Settings']},
        'Configuration': ['Management'],
        'Control': ['Import / Export', 'Log', 'Explorer', 'Simulation'],
        'Monitor': {
            'Alerts': ['Overview', 'All Alerts']},
        'Networks': ['Subnets', 'Load Balancers', 'Providers', 'Security Groups', 'Floating IPs',
                     'Network Ports', 'Topology', 'Networks', 'Network Routers'],
        'Optimize': ['Bottlenecks', 'Planning', 'Utilization'],
        'Services': ['Requests', 'Workloads', 'Catalogs', 'My Services'],
        'Storage': {
            'Block Storage': ['Volume Snapshots', 'Managers', 'Volume Backups', 'Volumes',
                              'Volume Types'],
            'Object Storage': ['Managers', 'Object Store Containers', 'Object Store Objects']}
    },
    'evmgroup-administrator': {
        'Automation': {
            'Ansible': ['Credentials', 'Repositories', 'Playbooks'],
            'Ansible Tower': ['Jobs', 'Explorer'],
            'Automate': ['Log', 'Simulation', 'Import / Export', 'Customization', 'Explorer']},
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Flavors', 'Instances', 'Providers', 'Host Aggregates', 'Availability Zones',
                       'Stacks', 'Topology'],
            'Containers': ['Container Nodes', 'Containers', 'Providers', 'Overview',
                           'Image Registries', 'Container Builds', 'Container Services',
                           'Volumes', 'Container Images', 'Routes', 'Pods', 'Replicators',
                           'Projects', 'Topology'],
            'Infrastructure': ['Datastores', 'Networking', 'Providers', 'Virtual Machines', 'Hosts',
                               'Clusters', 'Topology', 'PXE', 'Resource Pools'],
            'Physical Infrastructure': ['Providers', 'Chassis', 'Racks', 'Switches', 'Servers',
                                        'Storages', 'Topology']},
        'Configuration': ['Management'],
        'Control': ['Import / Export', 'Log', 'Explorer', 'Simulation'],
        'Networks': ['Providers', 'Security Groups', 'Floating IPs', 'Networks'],
        'Optimize': ['Bottlenecks', 'Planning', 'Utilization'],
        'Services': ['Requests', 'Workloads', 'Catalogs', 'My Services'],
        'Storage': {
            'Object Storage': ['Object Store Containers', 'Object Store Objects']}
    },
    'evmgroup-approver': {
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Datastores', 'Providers', 'Virtual Machines', 'Hosts', 'Clusters',
                               'PXE', 'Resource Pools'],
            'Physical Infrastructure': ['Providers', 'Chassis', 'Racks', 'Switches', 'Servers',
                                        'Storages', 'Topology']},
        'Control': ['Explorer', 'Log', 'Simulation'],
        'Services': ['Requests', 'Workloads', 'My Services'],
    },
    'evmgroup-auditor': {
        'Automation': {
            'Ansible': ['Credentials', 'Repositories', 'Playbooks'],
            'Ansible Tower': ['Explorer']},
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Datastores', 'Providers', 'Virtual Machines', 'Hosts', 'Clusters',
                               'Networking', 'PXE', 'Resource Pools'],
            'Physical Infrastructure': ['Providers', 'Chassis', 'Racks', 'Switches', 'Servers',
                                        'Storages', 'Topology']},
        'Control': ['Explorer', 'Log', 'Simulation'],
        'Optimize': ['Bottlenecks', 'Planning', 'Utilization'],
        'Services': ['Workloads', 'My Services']},
    'evmgroup-desktop': {
        'Automation': {
            'Ansible Tower': ['Explorer']},
        'Cloud Intel': ['Dashboard'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Virtual Machines'],
            'Physical Infrastructure': ['Providers', 'Chassis', 'Racks', 'Switches', 'Servers',
                                        'Storages', 'Topology']},
        'Configuration': ['Management'],
        'Services': ['Requests', 'Workloads']
    },
    'evmgroup-operator': {
        'Automation': {
            'Ansible': ['Credentials', 'Repositories', 'Playbooks'],
            'Ansible Tower': ['Explorer']},
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Datastores', 'Providers', 'Virtual Machines', 'Hosts', 'Clusters',
                               'PXE', 'Resource Pools'],
            'Physical Infrastructure': ['Providers', 'Chassis', 'Racks', 'Switches', 'Servers',
                                        'Storages', 'Topology']},
        'Configuration': ['Management'],
        'Services': ['Workloads', 'My Services']
    },
    'evmgroup-security': {
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Datastores', 'Providers', 'Virtual Machines', 'Hosts',
                               'Clusters', 'Resource Pools'],
            'Physical Infrastructure': ['Providers', 'Servers']},
        'Control': ['Explorer', 'Log', 'Simulation'],
        'Services': ['My Services', 'Workloads']
    },
    'evmgroup-support': {
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Datastores', 'Providers', 'Virtual Machines', 'Hosts', 'Clusters',
                               'Resource Pools'],
            'Physical Infrastructure': ['Providers', 'Chassis', 'Racks', 'Switches', 'Servers',
                                        'Storages', 'Topology']},
        'Control': ['Explorer', 'Log', 'Simulation'],
        'Services': ['My Services', 'Workloads']
    },
    'evmgroup-user': {
        'Cloud Intel': ['Timelines', 'RSS', 'Dashboard', 'Reports', 'Chargeback'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Datastores', 'Providers', 'Virtual Machines', 'Hosts', 'Clusters',
                               'Resource Pools'],
            'Physical Infrastructure': ['Providers', 'Chassis', 'Racks', 'Switches', 'Servers',
                                        'Storages', 'Topology']},
        'Services': ['Requests', 'Workloads', 'My Services']
    },
    'evmgroup-vm_user': {
        'Automation': {
            'Ansible': ['Credentials', 'Repositories', 'Playbooks'],
            'Ansible Tower': ['Explorer']},
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Virtual Machines']},
        'Configuration': ['Management'],
        'Services': ['Requests', 'Workloads'],
    }
}

role_access_ssui = {
    'evmgroup-user_limited_self_service': {
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Virtual Machines']},
        'Services': ['Requests', 'Catalogs', 'My Services']
    },
    'evmgroup-user_self_service': {
        'Automation': {
            'Ansible': ['Credentials', 'Repositories', 'Playbooks'],
            'Ansible Tower': ['Explorer']},
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Virtual Machines'],
            'Physical Infrastructure': ['Providers']},
        'Configuration': ['Management'],
        'Services': ['Requests', 'Catalogs', 'My Services']
    },
}
