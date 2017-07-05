from __future__ import absolute_import
from utils.log import logger


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
