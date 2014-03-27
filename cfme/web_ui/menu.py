import ui_navigate as nav

from cfme.fixtures import pytest_selenium as sel

toplevel_loc = '//div[@class="navbar"]//li/a[normalize-space(.)="%s"]'
secondlevel_loc = '../ul/li/a[normalize-space(.)="%s"]'


def nav_to_fn(toplevel, secondlevel=None):
    def f(_):
        toplevel_elem = sel.element(toplevel_loc % toplevel)
        if secondlevel is None:
            sel.click(toplevel_elem)
        else:
            sel.move_to_element(toplevel_elem)
            sel.click(sel.element(secondlevel_loc % secondlevel, root=toplevel_elem))
    return f

# Dictionary of (nav destination name, section title) section tuples
# Keys are toplevel sections (the main tabs), values are a supertuple of secondlevel sections
sections = {
    ('cloud_intelligence', 'Cloud Intelligence'): (
        ('dashboard', 'Dashboard'),
        ('reports', 'Reports'),
        ('chargeback', 'Chargeback'),
        ('timelines', 'Timelines'),
        ('rss', 'RSS')
    ),
    ('services', 'Services'): (
        ('my_services', 'My Services'),
        ('services_catalogs', 'Catalogs'),
        ('services_workloads', 'Workloads'),
        ('services_requests', 'Requests')
    ),
    ('clouds', 'Clouds'): (
        ('clouds_providers', 'Providers'),
        ('clouds_availability_zones', 'Availability Zones'),
        ('clouds_flavors', 'Flavors'),
        ('clouds_security_groups', 'Security Groups'),
        ('clouds_instances', 'Instances')
    ),
    ('infrastructure', 'Infrastructure'): (
        ('infrastructure_providers', 'Providers'),
        ('infrastructure_clusters', 'Clusters'),
        ('infrastructure_hosts', 'Hosts'),
        ('infrastructure_virtual_machines', 'Virtual Machines'),
        ('infrastructure_resource_pools', 'Resource Pools'),
        ('infrastructure_datastores', 'Datastores'),
        ('infrastructure_repositories', 'Repositories'),
        ('infrastructure_pxe', 'PXE'),
        ('infrastructure_requests', 'Requests')
    ),
    ('control', 'Control'): (
        ('control_explorer', 'Explorer'),
        ('control_simulation', 'Simulation'),
        ('control_import_export', 'Import / Export'),
        ('control_log', 'Log')
    ),
    ('automate', 'Automate'): (
        ('automate_explorer', 'Explorer'),
        ('automate_simulation', 'Simulation'),
        ('automate_customization', 'Customization'),
        ('automate_import_export', 'Import / Export'),
        ('automate_log', 'Log'),
        ('automate_requests', 'Requests')
    ),
    ('optimize', 'Optimize'): (
        ('utilization', 'Utilization'),
        ('planning', 'Planning'),
        ('bottlenecks', 'Bottlenecks')
    ),
    ('configure', 'Configure'): (
        ('my_settings', 'My Settings'),
        ('tasks', 'Tasks'),
        ('configuration', 'Configuration'),
        ('smartproxies', 'SmartProxies'),
        ('about', 'About')
    )
}

_branches = dict()
for (toplevel_dest, toplevel), secondlevels in sections.items():
    _branch_dests = dict()
    for secondlevel_dest, secondlevel in secondlevels:
        _branch_dests[secondlevel_dest] = nav_to_fn(toplevel, secondlevel)
    # The main tab destination is always the first secondlevel page in that tab
    # Since this is redundant, it's arguable that the toplevel tabs should be
    # nav destination at all; they're included here "just in case".
    _branches[toplevel_dest] = [
        nav_to_fn(toplevel, None),
        _branch_dests
    ]

nav.add_branch('toplevel', _branches)
