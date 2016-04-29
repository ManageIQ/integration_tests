# -*- coding: utf-8 -*-
import inspect
from ui_navigate import UINavigate

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, toolbar
from lya import AttrDict
from selenium.common.exceptions import NoSuchElementException
from utils import version


class Menu(UINavigate):
    """ Menu class for navigation

    The Menu() class uses the UINavigate() class to supply an instance of a menu. This menu is a
    navigatable system that uses destination endpoints and traverses each endpoint in a path and
    run the function associated with that destination, toreach the final destination.

    In CFME, an example would be navigating to the form to add a new provider. We have a
    ``clouds_providers`` destination which will ensure we are logged in
    and sitting at the Clouds / Providers page. Then there will be a ``add_new_cloud_provider``
    destination, which will have the ``clouds_provider`` as it's parent. When navigating to
    ``add_new_cloud_provider``, we will first run the function associated with the parent
    ``clouds_provider`` and then run the next function which is associated with the final endpoint.

    The Menu() system is used extensively in CFME-QE and is often grafted onto at module import.
    To accomplish this, the Menu uses a deferral system to stack up graft requests until the menu
    is ready to be initialized. This is necessary because Menu now needs to know what *version* of
    the product it is dealing with.

    :py:meth:`Menu.initialize` is used to initialize the object and collapse the stacked tree
    grafts. It is currently called inside :py:func:`cfme.fixtures.pytest_selenium.force_navigate`
    so it is set up *just* before the navigation is requested.
    """

    # 5.5- locators
    toplevel_tabs_loc = '//nav[contains(@class, "navbar")]/div/ul[@id="maintab"]'
    toplevel_loc = toplevel_tabs_loc + ('/li/a[normalize-space(.)="{}"'
        'and (contains(@class, "visible-lg"))]')
    TOP_LEV_ACTIVE = '//ul[@id="maintab"]/li[contains(@class,"active")]/a[normalize-space(.)="{}"]'
    TOP_LEV_INACTIVE = ('//ul[@id="maintab"]/li[contains(@class,"dropdown")]'
        '/a[normalize-space(.)="{}"]')
    SECOND_LEV_ACTIVE = '/../ul[contains(@class,"nav")]/li/a[normalize-space(.)="{}"]'
    SECOND_LEV_INACTIVE = '/../ul[contains(@class,"dropdown-menu")]/li/a[normalize-space(.)="{}"]'
    SECOND_LEV_ACTIVE_HREF = '/../ul[contains(@class,"nav")]/li/a[@href="{}"]'
    SECOND_LEV_INACTIVE_HREF = '/../ul[contains(@class,"dropdown-menu")]/li/a[@href="{}"]'

    # Upstream locators
    ROOT = '//ul[@id="maintab"]/..'
    NAMED_LEV = ('/../div/ul[contains(@class,"list-group")]/li[contains(@class,"list-group-item")]'
        '/a[normalize-space(.)="{}"]')
    ACTIVE_LEV = ('/../div/ul[contains(@class,"list-group")]/li[contains(@class,"active")]'
        '/a')
    ANY_LEV = ('/../div/ul[contains(@class,"list-group")]/li[contains(@class,"list-group-item")]'
        '/a')

    def __init__(self):
        self._branches = None
        self._branch_stack = []
        super(Menu, self).__init__()

    def initialize(self):
        """Initializes the menu object by collapsing the grafted tree items onto the tree"""
        if not self._branches:
            self._branches = self._branch_convert(self.sections)
            self.add_branch('toplevel', self._branches)
            while self._branch_stack:
                name, branches = self._branch_stack.pop(0)
                self.add_branch(name, branches)
            if version.current_version() < "5.6.0.1" or version.current_version() == version.LATEST:
                self.CURRENT_TOP_MENU = "//ul[@id='maintab']/li[not(contains(@class, 'drop'))]/a[2]"
            else:
                self.CURRENT_TOP_MENU = "{}{}".format(self.ROOT, self.ACTIVE_LEV)

    def add_branch(self, name, branches):
        """Adds a branch to the tree at a given destination

        This method will either:

        * Add the tree item to a stack to be precessed in the :py:meth:`Menu.initialize` method
        * Directly add the tree item to the UINavigate class

        This decision is based on whether the :py:meth:`Menu.initialize` method has already been
        called. As there are a default set of navigation endpoints that are always present in the
        tree, the :py:meth:`Menu.initialize` method is only ever able to be run once.
        """
        if self._branches:
            super(Menu, self).add_branch(name, branches)
        else:
            self._branch_stack.append((name, branches))

    def get_current_toplevel_name(self):
        """Returns text of the currently selected top level menu item."""
        return self.get_current_menu_state()[0]

    def get_current_menu_state(self):
        """Returns the current menu state

        This function returns what each level of the menu is pointing to, or None, if that level
        of menu is unused. Future work could possibly see this method using recursion to allow
        unlimited levels of menu to be used, however it is unlikely that more than 3 will ever be
        used.
        """
        lev = [None, None, None]
        lev[0] = (sel.text(self.CURRENT_TOP_MENU).encode("utf-8").strip())
        if version.current_version() < "5.6.0.1" or version.current_version() == version.LATEST:
            try:
                lev[1] = sel.text("//nav[contains(@class, 'navbar')]//ul/li[@class='active']/a") \
                    .encode("utf-8").strip()
            except NoSuchElementException:
                pass
        else:
            lev[1] = sel.text("{}{}".format(
                self.CURRENT_TOP_MENU, self.ACTIVE_LEV)).encode("utf-8").strip()
            try:
                lev[2] = sel.text("{}{}{}".format(
                    self.CURRENT_TOP_MENU, self.ACTIVE_LEV, self.ACTIVE_LEV)).encode(
                        "utf-8").strip()
            except NoSuchElementException:
                pass

        return lev

    @staticmethod
    def _tree_func_with_grid(*args):
        def f():
            accordion.tree(*args)
            toolbar.select('Grid View')
        return f

    @property
    def sections(self):
        """Dictionary of navigation elements.

        These can be either (nav destination name, section title) section tuples, or dictionary
        objects containing more section tuples.
        Keys are toplevel sections (the main tabs), values are a supertuple of secondlevel
        sections, or thirdlevel sections.
        You can also add a resetting callable that is called after clicking the second or third
        level.

        The main tab destination is usually the first secondlevel page in that tab
        Since this is redundant, it's arguable that the toplevel tabs should be
        nav destination at all; they're included here "just in case". The toplevel
        and secondlevel destinations exist at the same level of nav_tree because the
        secondlevel destinations don't depend on the toplevel nav taking place to reach
        their destination.
        """
        if version.current_version() < "5.6.0.1" or version.current_version() == version.LATEST:
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
                        self._tree_func_with_grid(
                            "Instances by Provider", "Instances by Provider")),
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
                        self._tree_func_with_grid("VMs & Templates", "All VMs & Templates")),
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
        else:
            sections = {
                ('cloud_intelligence', 'Cloud Intel'): (
                    ('dashboard', 'Dashboard'),
                    ('reports', 'Reports'),
                    ('chargeback', 'Chargeback'),
                    ('timelines', 'Timelines'),
                    ('rss', 'RSS')
                ),
                ('compute', 'Compute'): {
                    ('clouds', 'Clouds'): (
                        ('clouds_providers', 'Providers', lambda: toolbar.select('Grid View')),
                        ('clouds_availability_zones', 'Availability Zones'),
                        ('clouds_tenants', 'Tenants'),
                        ('clouds_flavors', 'Flavors'),
                        ('clouds_security_groups', 'Security Groups'),
                        ('clouds_instances', 'Instances',
                            self._tree_func_with_grid(
                                "Instances by Provider", "Instances by Provider")),
                        ('clouds_stacks', 'Stacks')
                    ),
                    ('services', 'Services'): (
                        ('my_services', 'My Services'),
                        ('services_catalogs', 'Catalogs'),
                        ('services_workloads', 'Workloads'),
                        ('services_requests', 'Requests')
                    ),
                    ('infrastructure', 'Infrastructure'): (
                        ('infrastructure_providers',
                            'Providers', lambda: toolbar.select('Grid View')),
                        ('infrastructure_clusters', "/ems_cluster"),
                        ('infrastructure_hosts', "/host"),
                        ('infrastructure_virtual_machines', 'Virtual Machines',
                            self._tree_func_with_grid("VMs & Templates", "All VMs & Templates")),
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
                },
                ('n_configuration', 'Configuration'): (
                    ('infrastructure_config_management', 'Configuration Management'),
                ),
                ('containers', 'Containers'): (
                    ('containers_providers', 'Providers'),
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
                ('configure', 'Settings'): (
                    ('my_settings', 'My Settings'),
                    ('tasks', 'Tasks'),
                    ('configuration', 'Configuration'),
                    ('about', 'About')
                )
            }
        return sections

    def is_page_active(self, toplevel, secondlevel=None, thirdlevel=None):
        """ Checks three levels of menu to return if the menu is active

        Usage:

          menu.is_page_active('Compute', 'Clouds', 'Providers')
          menu.is_page_active('Compute', 'Clouds')
        """
        present = self.get_current_menu_state()
        required = toplevel, secondlevel, thirdlevel
        for present, required in zip(present, required):
            if required and present != required:
                return False
        else:
            return True

    @staticmethod
    def _try_nav(el):
        href = sel.get_attribute(el, 'href')
        sel.execute_script('document.location.href = arguments[0];', href)
        sel.wait_for_ajax()

    @staticmethod
    def _try_reset_action(reset_action, _final, nav_fn):
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
                    nav_fn()

    @classmethod
    def _nav_to_fn(cls, toplevel, secondlevel=None, thirdlevel=None, reset_action=None,
            _final=False):
        """ Returns a navigation function

        This is a helper function that returns another function that knows how to navigate to
        a particular destination. It is used internally in the menu system.
        """

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
                    active_loc = (cls.TOP_LEV_ACTIVE + cls.SECOND_LEV_ACTIVE_HREF).format(
                        top_level, second_level)
                    inactive_loc = (cls.TOP_LEV_INACTIVE + cls.SECOND_LEV_INACTIVE_HREF).format(
                        top_level, second_level)
                else:
                    active_loc = (cls.TOP_LEV_ACTIVE + cls.SECOND_LEV_ACTIVE).format(
                        top_level, second_level)
                    inactive_loc = (cls.TOP_LEV_INACTIVE + cls.SECOND_LEV_INACTIVE).format(
                        top_level, second_level)
                el = "{} | {}".format(active_loc, inactive_loc)
                cls._try_nav(el)

            else:
                active_loc = cls.TOP_LEV_ACTIVE.format(top_level)
                inactive_loc = cls.TOP_LEV_INACTIVE.format(top_level)
                el = "{} | {}".format(active_loc, inactive_loc)
                cls._try_nav(el)

            nav_fn = lambda: cls._nav_to_fn(toplevel, secondlevel, reset_action, _final=True)
            cls._try_reset_action(reset_action, _final, nav_fn)
            # todo move to element on the active tab to clear the menubox
            sel.wait_for_ajax()

        def f2(_):
            args = [toplevel, secondlevel, thirdlevel]
            loc = cls.ROOT
            for arg in args:
                if arg:
                    loc = "{}{}".format(loc, cls.NAMED_LEV).format(arg)
                else:
                    break
            cls._try_nav(loc)

            nav_fn = lambda: cls._nav_to_fn(toplevel, secondlevel, thirdlevel, reset_action,
                _final=True)
            cls._try_reset_action(reset_action, _final, nav_fn)

        if version.current_version() < "5.6.0.1" or version.current_version() == version.LATEST:
            return f
        else:
            return f2

    def reverse_lookup(self, toplevel_path, secondlevel_path=None, thirdlevel_path=None):
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
        if thirdlevel_path:
            menu_path = '{}/{}/{}'.format(toplevel_path, secondlevel_path, thirdlevel_path)
        elif secondlevel_path:
            menu_path = '{}/{}'.format(toplevel_path, secondlevel_path)
        else:
            menu_path = toplevel_path

        def pco_b(level, str_so_far, next_levels=None):
            if len(level) == 2:
                level_dest, level = level
                reset_action = None
            else:
                level_dest, level, reset_action = level
            if callable(level):
                level = level()
            else:
                level = level
            if str_so_far:
                str_so_far = "{}/{}".format(str_so_far, level)
            else:
                str_so_far = level

            if menu_path == str_so_far:
                return level_dest
            else:
                if next_levels:
                    return process_level(next_levels, str_so_far)
                else:
                    return False

        def process_level(levels, str_so_far=None):
            if isinstance(levels, tuple):
                for level in levels:
                    ache = pco_b(level, str_so_far)
                    if ache:
                        return ache
            else:
                for level, next_levels in levels.items():
                    ache = pco_b(level, str_so_far, next_levels)
                    if ache:
                        return ache

        return process_level(self.sections)

    def _old_visible_toplevel_tabs(self):
        """Method returning the visible toplevel_tabs in 5.4"""
        menu_names = []
        ele = 'li/a[2]'

        for menu_elem in sel.elements(ele, root=self.toplevel_tabs_loc):
            menu_names.append(sel.text(menu_elem))
        return menu_names

    def _old_visible_pages(self):
        """Method returning the visible pages in 5.4"""
        menu_names = self._old_visible_toplevel_tabs()

        # Now go from tab to tab and pull the secondlevel names from the visible links
        displayed_menus = []
        for menu_name in menu_names:
            menu_elem = sel.element(self.toplevel_loc.format(menu_name))
            sel.move_to_element(menu_elem)
            for submenu_elem in sel.elements('../ul/li/a', root=menu_elem):
                displayed_menus.append((menu_name, sel.text(submenu_elem)))
        return displayed_menus

        # Do reverse lookups so we can compare to the list of nav destinations for this group

    def _new_visible_pages(self):
        """Method returning the visible toplevel_tabs in 5.6+"""
        nodes = []

        def proc_node(loc, c=0, prev_node=None):
            if not prev_node:
                prev_node = []
            for el in sel.elements(loc + self.ANY_LEV):
                sel.move_to_element(el)
                new_loc = loc + self.NAMED_LEV.format(el.text)
                nn = prev_node[:]
                nn.append(el.text)
                proc_node(new_loc, c + 1, nn)
            else:
                nodes.append(prev_node)

        proc_node(self.ROOT)
        return nodes

    def visible_pages(self):
        """Return a list of all the menu pages currently visible top- and second-level pages

        Mainly useful for RBAC testing

        """
        if version.current_version() < "5.6.0.1" or version.current_version() == version.LATEST:
            displayed_menus = self._old_visible_pages()
        else:
            displayed_menus = self._new_visible_pages()
        return sorted(
            [self.reverse_lookup(*displayed) for displayed in displayed_menus if displayed])

    def _branch_convert(self, input_set):
        """Converts a set of nav points into the graftable tree nodes for the UINavigate module"""
        _branches = dict()
        for (toplevel_dest, toplevel), secondlevels in input_set.items():
            if isinstance(secondlevels, dict):
                for (secondlevel_dest, secondlevel), thirdlevels in secondlevels.items():
                    for level in thirdlevels:
                        if len(level) == 2:
                            thirdlevel_dest, thirdlevel = level
                            reset_action = None
                        elif len(level) == 3:
                            thirdlevel_dest, thirdlevel, reset_action = level
                        else:
                            raise Exception(
                                "Wrong length of menu navigation tuple! ({})".format(len(level)))
                        _branches[thirdlevel_dest] = self._nav_to_fn(
                            toplevel, secondlevel, thirdlevel, reset_action)
                    _branches[secondlevel_dest] = self._nav_to_fn(
                        toplevel, secondlevel, reset_action)
            else:
                for level in secondlevels:
                    if len(level) == 2:
                        secondlevel_dest, secondlevel = level
                        reset_action = None
                    elif len(level) == 3:
                        secondlevel_dest, secondlevel, reset_action = level
                    else:
                        raise Exception(
                            "Wrong length of menu navigation tuple! ({})".format(len(level)))
                    _branches[secondlevel_dest] = self._nav_to_fn(
                        toplevel, secondlevel, reset_action)
            _branches[toplevel_dest] = [self._nav_to_fn(toplevel, None), {}]
        return _branches


##
# Tree class DSL
# TODOS:
# * Maybe kwargify the functions? So we can then specify the args directly in the methods and
#   not pull them from the context. (probably more question on ui_navigate itself)
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

    Note:
        This class currently is incompatible with a multiple menu object system. It relies on
        the ``nav`` attribute of this module. It needs to be fixed before FW3.0.
    """
    nav.add_branch(cls.__name__, _scavenge_class(cls, ignore_navigate=True))
    return cls

nav = Menu()
