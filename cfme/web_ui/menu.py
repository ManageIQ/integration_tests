import ui_navigate as nav

from cfme.fixtures import pytest_selenium as sel
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from utils import version
from utils.wait import wait_for

# All top-level menu items
toplevel_tabs_loc = '//div[@class="navbar"]/ul'
# Specific top-level menu item (toplevel_loc.format(tl_item_text))
toplevel_loc = '//div[@class="navbar"]/ul/li/a[normalize-space(.)="{}"]'
# Locator targeting the first item of the specific top-level menu item
secondlevel_first_item_loc = '//div[@class="navbar"]/ul/li/a[normalize-space(.)="{}"]/../ul/li[1]/a'
# All submenus that are not currently active (but can be hovered)
inactive_box_loc = "//ul[@id='maintab']//ul[contains(@class, 'inactive')]"


def any_box_displayed():
    """Checks whether any of the not-currently-selected toplevel items is hovered (active).

    First part of the condition is for the 5.3+ pop-up, second is for 5.2.
    """
    return version.pick({
        version.LOWEST: lambda: sel.is_displayed("//a[contains(@class, 'maintab_active')]"),
        "5.3": lambda: any(map(sel.is_displayed, sel.elements(inactive_box_loc)))
    })()


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


def get_current_toplevel_name():
    """Returns text of the currently selected top level menu item."""
    get_rid_of_the_menu_box()
    return sel.text(
        version.pick({
            "5.3": "//ul[@id='maintab']/li[not(contains(@class, 'in'))]/a",
            version.LOWEST: "//ul[@id='maintab']/li/ul[not(contains(@style, 'none'))]/../a"
        })).encode("utf-8").strip()


def get_rid_of_the_menu_box():
    """Moves the mouse pointer away from the menu location and waits for the popups to hide."""
    ActionChains(sel.browser()).move_to_element(sel.element("#tP")).perform()
    wait_for(lambda: not any_box_displayed(), num_sec=10, delay=0.1, message="menu box")

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


def is_page_active(toplevel, secondlevel=None):
    try:
        if get_current_toplevel_name() != toplevel:
            return False
    except NoSuchElementException:
        return False
    if secondlevel:
        try:
            sel.element("//div[@class='navbar']//ul/li[@class='active']"
                        "/a[normalize-space(.)='{}']/..".format(secondlevel))
        except NoSuchElementException:
            return False
    return True


def nav_to_fn(toplevel, secondlevel=None):
    def f(_):
        if not is_page_active(toplevel):
            try:
                # Try to circumvent the issue on fir
                get_rid_of_the_menu_box()
                open_top_level(toplevel)
                get_rid_of_the_menu_box()
                if get_current_toplevel_name() != toplevel:
                    # Infrastructure / Requests workaround
                    sel.move_to_element(get_top_level_element(toplevel))
                    # Using pure move_to_element to not move the mouse anywhere else
                    # So in this case, we move the mouse to the first item of the second level
                    ActionChains(sel.browser())\
                        .move_to_element(sel.element(secondlevel_first_item_loc.format(toplevel)))\
                        .click()\
                        .perform()
                    get_rid_of_the_menu_box()
                    # Now when we went directly to the first item, everything should just work
                    tl = get_current_toplevel_name()
                    if tl != toplevel:
                        raise Exception("Navigation screwed! (wanted {}, got {}".format(toplevel,
                                                                                        tl))
            except NoSuchElementException:
                if visible_toplevel_tabs():  # Target menu is missing
                    raise
                else:
                    return  # no menu at all, assume single permission

        # Can't do this currently because silly menu traps us
        # if is_page_active(toplevel, secondlevel):
        #     return
        if secondlevel is not None:
            get_rid_of_the_menu_box()
            open_second_level(get_top_level_element(toplevel), secondlevel)
            get_rid_of_the_menu_box()
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
    for menu_elem in sel.elements('li/a', root=toplevel_tabs_loc):
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
        menu_elem = sel.element(toplevel_loc.format(menu_name))
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
