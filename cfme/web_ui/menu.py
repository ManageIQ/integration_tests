import ui_navigate as nav

from cfme.fixtures import pytest_selenium as sel

#: Locator for the unordered list that holds the top-level nav tabs.
toplevel_tabs_loc = '//div[@class="navbar"]/ul'
#: Locator for a specific top-level navigation tab.
#: Needs a tab name to be %-interpolated.
toplevel_loc = toplevel_tabs_loc + '/li/a[normalize-space(.)="%s"]'
#: Locator for the unordered list that holds second-level nav links.
#: Needs a top-level tab name to be %-interpolated.
secondlevel_links_loc = toplevel_loc + '/../ul'
#: Locator for a specific second-level nav link
#: Needs a top-level tab name and second-level link name to be %-interpolated.
secondlevel_loc = secondlevel_links_loc + '/li/a[normalize-space(.)="%s"]'


def nav_to_fn(toplevel, secondlevel=None):
    def f(_):
        toplevel_elem = sel.element(toplevel_loc % toplevel)
        if secondlevel is None:
            sel.click(toplevel_elem)
        else:
            sel.move_to_element(toplevel_elem)
            sel.click(sel.element(secondlevel_loc % (toplevel, secondlevel)))
    return f


def reverse_lookup(toplevel_path, secondlevel_path=None):
    """Reverse lookup for navigation destinations defined in this module, based on menu text

    Usage:

        # Returns 'clouds'
        reverse_lookup('Clouds')

        # Returns 'clouds_providers'
        reverse_lookup('Clouds', 'Providers')

        # Returns 'automate_import_export'
        reverse_lookup('Automate', 'Import / Export')

    """
    if secondlevel_path:
        menu_path = '%s/%s' % (toplevel_path, secondlevel_path)
    else:
        menu_path = toplevel_path

    for (toplevel_dest, toplevel), secondlevels in sections.items():
        if menu_path == toplevel:
            return toplevel_dest
        for secondlevel_dest, secondlevel in secondlevels:
            if menu_path == '%s/%s' % (toplevel, secondlevel):
                return secondlevel_dest


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
