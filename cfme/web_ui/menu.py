# -*- coding: utf-8 -*-
import inspect
import ui_navigate as nav

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, toolbar
from lya import AttrDict
from selenium.common.exceptions import NoSuchElementException


toplevel_tabs_loc = '//nav[contains(@class, "navbar")]/div/ul[@id="maintab"]'
toplevel_loc = toplevel_tabs_loc + ('/li/a[normalize-space(.)="{}"'
    'and (contains(@class, "visible-lg"))]')


def get_current_toplevel_name():
    """Returns text of the currently selected top level menu item."""
    return sel.text("//ul[@id='maintab']/li[not(contains(@class, 'drop'))]/a[2]")\
        .encode("utf-8").strip()


def _tree_func_with_grid(*args):
    def f():
        accordion.tree(*args)
        toolbar.select('Grid View')
    return f

# Dictionary of (nav destination name, section title) section tuples
# Keys are toplevel sections (the main tabs), values are a supertuple of secondlevel sections
# You can also add a resetting callable that is called after clicking the second level.
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
        ('clouds_providers', 'Providers', lambda: toolbar.select('Grid View')),
        ('clouds_availability_zones', 'Availability Zones'),
        ('clouds_tenants', 'Tenants'),
        ('clouds_flavors', 'Flavors'),
        ('clouds_security_groups', 'Security Groups'),
        ('clouds_instances', 'Instances',
            _tree_func_with_grid("Instances by Provider", "Instances by Provider")),
        ('clouds_stacks', 'Stacks')
    ),
    ('containers', 'Containers'): (
        ('containers_providers', 'Providers'),
        ('containers_projects', 'Projects'),
        ('containers_nodes', 'Nodes'),
        ('containers_pods', 'Pods'),
        ('containers_routes', 'Routes'),
        ('containers_replicators', 'Replicators'),
        ('containers_services', 'Services'),
        ('containers_containers', 'Containers'),
        ('containers_images', 'Container Images'),
        ('containers_image_registries', 'Image Registries'),
        ('containers_topology', 'Topology')
    ),
    ('middleware', 'Middleware'): (
        ('middleware_providers', 'Providers'),
        ('middleware_servers', 'Middleware Servers')
    ),
    ('infrastructure', 'Infrastructure'): (
        ('infrastructure_providers', 'Providers', lambda: toolbar.select('Grid View')),
        ('infrastructure_clusters', "/ems_cluster"),
        ('infrastructure_hosts', "/host"),
        ('infrastructure_virtual_machines', 'Virtual Machines',
            _tree_func_with_grid("VMs & Templates", "All VMs & Templates")),
        ('infrastructure_resource_pools', 'Resource Pools'),
        ('infrastructure_datastores', 'Datastores'),
        ('infrastructure_repositories', 'Repositories'),
        ('infrastructure_pxe', 'PXE'),
        ('infrastructure_requests', 'Requests'),
        ('infrastructure_config_management', 'Configuration Management')
    ),
    ('middleware', 'Middleware'): (
        ('middleware_providers', 'Providers'),
        ('middleware_servers', "Middleware Servers"),
        ('middleware_deployments', "Middleware Deployments"),
        ('middleware_topology', "Topology"),
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


TOP_LEV_ACTIVE = '//ul[@id="maintab"]/li[contains(@class,"active")]/a[normalize-space(.)="{}"]'
TOP_LEV_INACTIVE = '//ul[@id="maintab"]/li[contains(@class,"dropdown")]/a[normalize-space(.)="{}"]'
SECOND_LEV_ACTIVE = '/../ul[contains(@class,"nav")]/li/a[normalize-space(.)="{}"]'
SECOND_LEV_INACTIVE = '/../ul[contains(@class,"dropdown-menu")]/li/a[normalize-space(.)="{}"]'
SECOND_LEV_ACTIVE_HREF = '/../ul[contains(@class,"nav")]/li/a[@href="{}"]'
SECOND_LEV_INACTIVE_HREF = '/../ul[contains(@class,"dropdown-menu")]/li/a[@href="{}"]'


def is_page_active(toplevel, secondlevel=None):
    try:
        if get_current_toplevel_name() != toplevel:
            return False
    except NoSuchElementException:
        return False
    if secondlevel:
        try:
            sel.element(("//nav[contains(@class, 'navbar')]//ul/li[@class='active']"
                        "/a[normalize-space(.)='{}']/..".format(secondlevel)))
        except NoSuchElementException:
            return False
    return True


def nav_to_fn(toplevel, secondlevel=None, reset_action=None, _final=False):
    def f(_):
        # Can't do this currently because silly menu traps us
        # if is_page_active(toplevel, secondlevel):
        #     return
        if callable(toplevel):
            top_level = toplevel()
        else:
            top_level = toplevel

        if secondlevel is not None:
            if callable(secondlevel):
                second_level = secondlevel()
            else:
                second_level = secondlevel

            if secondlevel.startswith('/'):
                active_loc = (TOP_LEV_ACTIVE + SECOND_LEV_ACTIVE_HREF).format(
                    top_level, second_level)
                inactive_loc = (TOP_LEV_INACTIVE + SECOND_LEV_INACTIVE_HREF).format(
                    top_level, second_level)
            else:
                active_loc = (TOP_LEV_ACTIVE + SECOND_LEV_ACTIVE).format(top_level, second_level)
                inactive_loc = (TOP_LEV_INACTIVE + SECOND_LEV_INACTIVE).format(
                    top_level, second_level)
            el = "{} | {}".format(active_loc, inactive_loc)

            try:
                href = sel.get_attribute(el, 'href')
                sel.execute_script('document.location.href="{}"'.format(href))
            except NoSuchElementException:
                raise
        else:
            active_loc = TOP_LEV_ACTIVE.format(top_level)
            inactive_loc = TOP_LEV_INACTIVE.format(top_level)
            el = "{} | {}".format(active_loc, inactive_loc)

            try:
                href = sel.get_attribute(el, 'href')
                sel.execute_script('document.location.href="{}"'.format(href))
            except NoSuchElementException:
                raise
        sel.wait_for_ajax()
        if reset_action is not None:
            try:
                if callable(reset_action):
                    reset_action()
                else:
                    sel.click(reset_action)
            except NoSuchElementException:
                if _final:
                    # We have tried to renavigate but still some problem. Never mind and explode.
                    raise
                else:
                    # Work around the problem when the display selector disappears after returning
                    # from VM summary view. Can be fixed by renavigating, it then appears again.
                    nav_to_fn(toplevel, secondlevel, reset_action, _final=True)
        # todo move to element on the active tab to clear the menubox
        sel.wait_for_ajax()
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
        menu_path = '{}/{}'.format(toplevel_path, secondlevel_path)
    else:
        menu_path = toplevel_path

    for (toplevel_dest, toplevel), secondlevels in sections.items():
        if callable(toplevel):
            top_level = toplevel()
        else:
            top_level = toplevel
        if menu_path == top_level:
            return toplevel_dest
        for level in secondlevels:
            if len(level) == 2:
                secondlevel_dest, secondlevel = level
                reset_action = None
            else:
                secondlevel_dest, secondlevel, reset_action = level
            if callable(secondlevel):
                second_level = secondlevel()
            else:
                second_level = secondlevel
            if menu_path == '{}/{}'.format(toplevel, second_level):
                return secondlevel_dest


def visible_toplevel_tabs():
    menu_names = []
    ele = 'li/a[2]'

    for menu_elem in sel.elements(ele, root=toplevel_tabs_loc):
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

# The main tab destination is usually the first secondlevel page in that tab
# Since this is redundant, it's arguable that the toplevel tabs should be
# nav destination at all; they're included here "just in case". The toplevel
# and secondlevel destinations exist at the same level of nav_tree because the
# secondlevel destinations don't depend on the toplevel nav taking place to reach
# their destination.


def branch_convert(input_set):
    _branches = dict()
    for (toplevel_dest, toplevel), secondlevels in input_set.items():
        for level in secondlevels:
            if len(level) == 2:
                secondlevel_dest, secondlevel = level
                reset_action = None
            elif len(level) == 3:
                secondlevel_dest, secondlevel, reset_action = level
            else:
                raise Exception("Wrong length of menu navigation tuple! ({})".format(len(level)))
            _branches[secondlevel_dest] = nav_to_fn(toplevel, secondlevel, reset_action)
        _branches[toplevel_dest] = [nav_to_fn(toplevel, None), {}]
    return _branches

_branches = branch_convert(sections)
nav.add_branch('toplevel', _branches)


##
# Tree class DSL
# TODOS:
# * Maybe kwargify the functions? So we can then specify the args directly in the methods and not
#   pull them from the context. (probably more question on ui_navigate itself)
def _scavenge_class(cls, ignore_navigate=False):
    """Scavenges locations and nav functions from the class. Recursively goes through so no loops.

    Args:
        ignore_navigate: Useful for the initial - root class that has no navigate function.
    """
    if "navigate" not in cls.__dict__ and not ignore_navigate:
        raise ValueError(
            "The nav class {} must contain navigation staticmethod".format(cls.__name__))
    elif not ignore_navigate:
        navigate = (
            cls.navigate.im_func if hasattr(cls.navigate, "im_func") else cls.navigate)
    contents = AttrDict({"subclasses": {}, "direct_navs": {}})
    for key, value in cls.__dict__.iteritems():
        if key.startswith("_") or key == "navigate":
            continue
        if inspect.isclass(value):
            contents.subclasses[value.__name__] = _scavenge_class(value)
        elif callable(value) and value.__name__ != "<lambda>":
            contents.direct_navs[value.__name__] = value
        elif hasattr(value, "im_func"):  # An unbound method, we just take the raw function from it
            contents.direct_navs[value.__name__] = value.im_func
        # Skipping others

    if not contents.subclasses and not contents.direct_navs and not ignore_navigate:
        # Leaf tree location generator
        return navigate
    elif ignore_navigate:
        # Root tree location generator
        result_dict = {}
        result_dict.update(contents.subclasses)
        result_dict.update(contents.direct_navs)
        return result_dict
    else:
        # Non-leaf tree location generator
        result_dict = {}
        result_dict.update(contents.subclasses)
        result_dict.update(contents.direct_navs)
        return [navigate, result_dict]


def extend_nav(cls):
    """A decorator, that when placed on a class will turn it to a nav tree extension.

    Takes the original class and "compiles" it into the nav tree in form of lists/dicts that
    :py:mod:`ui_navigate` takes.

    The classes in the structure are not instantiated during the scavenge process, they serve as a
    sort of static container of namespaced functions.

    Example:

    .. code-block:: python

       @extend_nav
       class infra_vms(object):   # This will extend the node infra_vms
           class node_a(object):  # with node a
               def navigate(_):   # that can be reached this way from preceeding one
                   pass

               def leaf_location(ctx):  # Leaf location, no other child locations
                   pass

               class node_x(object):  # Or an another location that can contain locations
                   def navigate(_):
                       pass

    Args:
        cls: Class to be decorated.
    """
    nav.add_branch(cls.__name__, _scavenge_class(cls, ignore_navigate=True))
    return cls
