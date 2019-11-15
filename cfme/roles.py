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
        'Cloud Intel': ['Dashboard', 'Reports', 'Chargeback', 'Timelines', 'RSS'],
        'Services': ['My Services', 'Catalogs', 'Workloads', 'Requests'],
        'Compute': {
            'Clouds': [
                'Providers',
                'Availability Zones',
                'Host Aggregates',
                'Tenants',
                'Flavors',
                'Instances',
                'Stacks',
                'Key Pairs',
                'Topology'
            ],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores',
                'PXE',
                'Networking',
                'Topology'
            ],
            'Physical Infrastructure': [
                'Overview',
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ],
            'Containers': [
                'Overview',
                'Providers',
                'Projects',
                'Routes',
                'Container Services',
                'Replicators',
                'Pods',
                'Containers',
                'Container Nodes',
                'Volumes',
                'Container Builds',
                'Image Registries',
                'Container Images',
                'Container Templates',
                'Topology'
            ],
            'Migration': [
                'Migration Plans',
                'Infrastructure Mappings',
                'Migration Settings'
            ]
        },
        'Configuration': ['Management'],
        'Networks': [
            'Providers',
            'Networks',
            'Subnets',
            'Network Routers',
            'Security Groups',
            'Floating IPs',
            'Network Ports',
            'Load Balancers',
            'Topology'
        ],
        'Storage': {
            'Block Storage': [
                'Managers',
                'Volumes',
                'Volume Snapshots',
                'Volume Backups',
                'Volume Types'
            ],
            'Object Storage': [
                'Managers',
                'Object Store Containers',
                'Object Store Objects'
            ]
        },
        'Control': ['Explorer', 'Simulation', 'Import / Export', 'Log'],
        'Automation': {
            'Ansible': ['Playbooks', 'Repositories', 'Credentials'],
            'Ansible Tower': ['Explorer', 'Jobs'],
            'Automate': [
                'Explorer',
                'Simulation',
                'Generic Objects',
                'Customization',
                'Import / Export',
                'Log',
                'Requests'
            ]
        },
        'Optimize': ['Utilization', 'Planning', 'Bottlenecks'],
        'Monitor': {
            'Alerts': ['Overview', 'All Alerts']
        }
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

role_access_ui_511z = {
    'evmgroup-super_administrator': {
        'Overview': [
            'Dashboard',
            'Reports',
            'Utilization',
            'Chargeback',
            'Optimization'
        ],
        'Services': ['My Services', 'Catalogs', 'Workloads', 'Requests'],
        'Compute': {
            'Clouds': [
                'Providers',
                'Availability Zones',
                'Host Aggregates',
                'Tenants',
                'Flavors',
                'Instances',
                'Stacks',
                'Key Pairs',
                'Topology'
            ],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores',
                'PXE',
                'Firmware Registry',
                'Networking',
                'Topology'
            ],
            'Physical Infrastructure': [
                'Overview',
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ],
            'Containers': [
                'Overview',
                'Providers',
                'Projects',
                'Routes',
                'Container Services',
                'Replicators',
                'Pods',
                'Containers',
                'Container Nodes',
                'Volumes',
                'Container Builds',
                'Image Registries',
                'Container Images',
                'Container Templates',
                'Topology'
            ]
        },
        'Migration': [
            'Migration Plans',
            'Infrastructure Mappings',
            'Migration Settings'
        ],
        'Configuration': ['Management'],
        'Networks': [
            'Providers',
            'Networks',
            'Subnets',
            'Network Routers',
            'Security Groups',
            'Floating IPs',
            'Network Ports',
            'Topology'
        ],
        'Storage': {
            'Block Storage': [
                'Managers',
                'Volumes',
                'Volume Snapshots',
                'Volume Backups',
                'Volume Types'
            ],
            'Object Storage': [
                'Managers',
                'Object Store Containers',
                'Object Store Objects'
            ]
        },
        'Control': ['Explorer', 'Simulation', 'Import / Export', 'Log'],
        'Automation': {
            'Ansible': ['Playbooks', 'Repositories', 'Credentials'],
            'Ansible Tower': ['Explorer', 'Jobs'],
            'Automate': [
                'Explorer',
                'Simulation',
                'Generic Objects',
                'Customization',
                'Import / Export',
                'Log',
                'Requests'
            ]
        },
        'Monitor': {
            'Alerts': ['Overview', 'All Alerts']
        },
    },
    'evmgroup-administrator': {
        'Overview': ['Dashboard', 'Reports', 'Utilization', 'Chargeback'],
        'Services': ['My Services', 'Catalogs', 'Workloads', 'Requests'],
        'Compute': {
            'Clouds': [
                'Providers',
                'Availability Zones',
                'Host Aggregates',
                'Flavors',
                'Instances',
                'Stacks',
                'Topology'
            ],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores',
                'PXE',
                'Networking',
                'Topology'
            ],
            'Physical Infrastructure': [
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ],
            'Containers': [
                'Overview',
                'Providers',
                'Projects',
                'Routes',
                'Container Services',
                'Replicators',
                'Pods',
                'Containers',
                'Container Nodes',
                'Volumes',
                'Container Builds',
                'Image Registries',
                'Container Images',
                'Topology'
            ]
        },
        'Configuration': ['Management'],
        'Networks': ['Providers', 'Networks', 'Security Groups', 'Floating IPs'],
        'Storage': {
            'Object Storage': [
                'Object Store Containers',
                'Object Store Objects'
            ]
        },
        'Control': ['Explorer', 'Simulation', 'Import / Export', 'Log'],
        'Automation': {
            'Ansible': ['Playbooks', 'Repositories', 'Credentials'],
            'Ansible Tower': ['Explorer', 'Jobs'],
            'Automate': [
                'Explorer',
                'Simulation',
                'Customization',
                'Import / Export',
                'Log'
            ]
        }
    },
    'evmgroup-approver': {
        'Overview': ['Dashboard', 'Reports', 'Chargeback'],
        'Services': ['My Services', 'Workloads', 'Requests'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores',
                'PXE'
            ],
            'Physical Infrastructure': [
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ]
        },
        'Control': ['Explorer', 'Simulation', 'Log']
    },
    'evmgroup-auditor': {
        'Overview': ['Dashboard', 'Reports', 'Utilization', 'Chargeback'],
        'Services': ['My Services', 'Workloads'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores',
                'PXE',
                'Networking'
            ],
            'Physical Infrastructure': [
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ]
        },
        'Control': ['Explorer', 'Simulation', 'Log'],
        'Automation': {
            'Ansible': ['Playbooks', 'Repositories', 'Credentials'],
            'Ansible Tower': ['Explorer']
        }
    },
    'evmgroup-desktop': {
        'Overview': ['Dashboard'],
        'Services': ['Workloads', 'Requests'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Virtual Machines'],
            'Physical Infrastructure': [
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ]
        },
        'Configuration': ['Management'],
        'Automation': {
            'Ansible Tower': ['Explorer']
        }
    },
    'evmgroup-operator': {
        'Overview': ['Dashboard', 'Reports', 'Chargeback'],
        'Services': ['My Services', 'Workloads'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores',
                'PXE'
            ],
            'Physical Infrastructure': [
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ]
        },
        'Configuration': ['Management'],
        'Automation': {
            'Ansible': ['Playbooks', 'Repositories', 'Credentials'],
            'Ansible Tower': ['Explorer']
        }
    },
    'evmgroup-security': {
        'Overview': ['Dashboard', 'Reports', 'Chargeback'],
        'Services': ['My Services', 'Workloads'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores'
            ],
            'Physical Infrastructure': ['Providers', 'Servers']
        },
        'Control': ['Explorer', 'Simulation', 'Log']
    },
    'evmgroup-support': {
        'Overview': ['Dashboard', 'Reports', 'Chargeback'],
        'Services': ['My Services', 'Workloads'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores'
            ],
            'Physical Infrastructure': [
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ]
        },
        'Control': ['Explorer', 'Simulation', 'Log']
    },
    'evmgroup-user': {
        'Overview': ['Dashboard', 'Reports', 'Chargeback'],
        'Services': ['My Services', 'Workloads', 'Requests'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': [
                'Providers',
                'Clusters',
                'Hosts',
                'Virtual Machines',
                'Resource Pools',
                'Datastores'
            ],
            'Physical Infrastructure': [
                'Providers',
                'Chassis',
                'Racks',
                'Servers',
                'Storages',
                'Switches',
                'Topology'
            ]
        }
    },
    'evmgroup-vm_user': {
        'Services': ['Workloads', 'Requests'],
        'Compute': {
            'Clouds': ['Instances'],
            'Infrastructure': ['Virtual Machines']
        },
        'Configuration': ['Management'],
        'Automation': {
            'Ansible': ['Playbooks', 'Repositories', 'Credentials'],
            'Ansible Tower': ['Explorer']
        }
    }
}
