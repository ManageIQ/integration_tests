import ui_navigate as nav

from cfme.fixtures import pytest_selenium as sel
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from utils.wait import wait_for

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
secondlevel_first_item_loc = secondlevel_links_loc + '/li[1]/a'

inactive_box_loc = "//ul[@id='maintab']//ul[contains(@class, 'inactive')]"


def any_box_displayed():
    """Checks whether any of the not-currently-selected toplevel items is hovered (active).

    First part of the condition is for the 5.3+ pop-up, second is for 5.2.
    """
    return any(map(sel.is_displayed, sel.elements(inactive_box_loc)))\
        or sel.is_displayed("//a[contains(@class, 'maintab_active')]")


def get_top_level_element(title):
    """Returns the ``li`` element representing the menu item in top-level menu."""
    return sel.element("//div[@class='navbar']/ul/li/a[normalize-space(.)='{}']/..".format(title))


def open_top_level(title):
    """Opens the section."""
    sel.raw_click(sel.element("./a", root=get_top_level_element(title)))


def get_second_level_element(top_level_el, title):
    """Returns the ``li`` element representing the menu item in second-level menu."""
    return sel.element("./ul/li/a[normalize-space(.)='{}']/..".format(title), root=top_level_el)


def open_second_level(top_level_element, title):
    """Click on second-level menu."""
    second = get_second_level_element(top_level_element, title)
    sel.raw_click(sel.element("./a", root=second))


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


def nav_to_fn(toplevel, secondlevel=None):
    def f(_):
        try:
            # TODO: Now with the workaround few lines lower, it may be possible to spare clicks here
            open_top_level(toplevel)
        except NoSuchElementException:
            if visible_toplevel_tabs():  # Target menu is missing
                raise
            else:
                return  # no menu at all, assume single permission

        if secondlevel is not None:
            # Move to the bottom-right (timedate)
            # It is needed to go down there so we cannot accdentally hit the top menu in the next
            # step. Slight performance hit on FF, almost none on Chrome.
            ActionChains(sel.browser()).move_to_element(sel.element("#tP")).perform()
            # Wait for the box going away. Required for 5.2 since there is a few secs timeout on it.
            # Here is the thing. 5.3 does the popup which goes away immediately when moved away
            # 5.2 does not do the popup, but instead of it the seond level menu changes.
            # There is a few seconds timeout after which the second level menu restores its contents
            wait_for(lambda: not any_box_displayed(), num_sec=10, delay=0.1, message="menu box")
            open_second_level(get_top_level_element(toplevel), secondlevel)
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

    Note:

        It may be tempting to use this when you don't know the name of a page, e.g.:

            go_to(reverse_lookup('Infrastructure', 'Providers'))

        Don't do that; use the nav tree name.

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


def visible_toplevel_tabs():
    menu_names = []
    toplevel_links = sel.element(toplevel_tabs_loc)
    for menu_elem in sel.elements('li/a', root=toplevel_links):
        menu_names.append(sel.text(menu_elem))
    return menu_names


def visible_pages():
    """Return a list of all the menu pages currently visible top- and second-level pages

    Mainly useful for RBAC testing

    """
    # Gather up all the visible toplevel tabs
    menu_names = visible_toplevel_tabs()

    # Now go from tab to tab and pull the secondlevel names from the visible links
    displayed_menus = []
    for menu_name in menu_names:
        menu_elem = sel.element(toplevel_loc % menu_name)
        sel.move_to_element(menu_elem)
        for submenu_elem in sel.elements('../ul/li/a', root=menu_elem):
            displayed_menus.append((menu_name, sel.text(submenu_elem)))

    # Do reverse lookups so we can compare to the list of nav destinations for this group
    return sorted([reverse_lookup(*displayed) for displayed in displayed_menus])

# Construct the nav tree based on sections
_branches = dict()
# The main tab destination is usually the first secondlevel page in that tab
# Since this is redundant, it's arguable that the toplevel tabs should be
# nav destination at all; they're included here "just in case". The toplevel
# and secondlevel destinations exist at the same level of nav_tree because the
# secondlevel destinations don't depend on the toplevel nav taking place to reach
# their destination.
for (toplevel_dest, toplevel), secondlevels in sections.items():
    for secondlevel_dest, secondlevel in secondlevels:
        _branches[secondlevel_dest] = nav_to_fn(toplevel, secondlevel)
    _branches[toplevel_dest] = [nav_to_fn(toplevel, None), {}]

nav.add_branch('toplevel', _branches)
