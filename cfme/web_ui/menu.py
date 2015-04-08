# -*- coding: utf-8 -*-
import inspect
import ui_navigate as nav

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import accordion, toolbar
from fixtures.pytest_store import store
from lya import AttrDict
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from utils import version, classproperty
from utils.wait import wait_for
from utils.version import current_version


class Loc(object):

    @classproperty
    def toplevel_tabs_loc(cls):
        return version.pick({version.LOWEST: '//div[@class="navbar"]/ul',
            '5.4': '//nav[contains(@class, "navbar")]/div/ul[@id="maintab"]'})

    @classproperty
    def toplevel_loc(cls):
        return version.pick({version.LOWEST: ('//div[@class="navbar"]/ul/li'
                                              '/a[normalize-space(.)="{}"]'),
                             '5.4': cls.toplevel_tabs_loc + ('/li/a[normalize-space(.)="{}"'
                                'and (contains(@class, "visible-lg"))]')})

    @classproperty
    def secondlevel_first_item_loc(cls):
        return version.pick({version.LOWEST: ('//div[@class="navbar"]/ul/li'
                                              '/a[normalize-space(.)="{}"]/../ul/li[1]/a'),
            '5.4': cls.toplevel_tabs_loc + '/li/a[normalize-space(.)="{}"]/../ul/li[1]/a'})

    @classproperty
    def inactive_box_loc(cls):
        return version.pick({version.LOWEST: ("//ul[@id='maintab']//"
                                              "ul[contains(@class, 'inactive')]"),
            '5.4': "//ul[@id='maintab']//ul[contains(@class, 'inactive')]"})

    @classproperty
    def a(cls):
        return version.pick({version.LOWEST: "./a",
            '5.4': "./a[contains(@class, 'visible-lg')]"})


def any_box_displayed():
    """Checks whether any of the not-currently-selected toplevel items is hovered (active).

    First part of the condition is for the 5.3+ pop-up, second is for 5.2.
    """
    return version.pick({
        version.LOWEST:
        lambda: sel.is_displayed("//a[contains(@class, 'maintab_active')]", _no_deeper=True),
        "5.3":
        lambda: any(map(
            lambda e: sel.is_displayed(e, _no_deeper=True),
            sel.elements(Loc.inactive_box_loc))),
        "5.4":
        lambda: sel.is_displayed(
            "//li[contains(@class, 'dropdown') and contains(@class, 'open')]", _no_deeper=True)
    })()


def get_top_level_element(title):
    """Returns the ``li`` element representing the menu item in top-level menu."""
    return sel.element((Loc.toplevel_loc + "/..").format(title))


def open_top_level(title):
    """Opens the section."""
    sel.raw_click(sel.element(Loc.a, root=get_top_level_element(title)))


def get_second_level_element(top_level_el, desc):
    """Returns the ``li`` element representing the menu item in second-level menu."""
    if desc.startswith("/"):
        return sel.element("./ul/li/a[@href='{}']/..".format(desc), root=top_level_el)
    else:
        return sel.element("./ul/li/a[normalize-space(.)='{}']/..".format(desc), root=top_level_el)


def open_second_level(top_level_element, desc):
    """Click on second-level menu."""
    second = get_second_level_element(top_level_element, desc)
    sel.raw_click(sel.element("./a", root=second))


def get_current_toplevel_name():
    """Returns text of the currently selected top level menu item."""
    get_rid_of_the_menu_box()
    return sel.text(
        version.pick({
            "5.4": "//ul[@id='maintab']/li[not(contains(@class, 'drop'))]/a[2]",
            "5.3": "//ul[@id='maintab']/li[not(contains(@class, 'in'))]/a",
            version.LOWEST: "//ul[@id='maintab']/li/ul[not(contains(@style, 'none'))]/../a"
        })).encode("utf-8").strip()


def get_rid_of_the_menu_box():
    """Moves the mouse pointer away from the menu location and waits for the popups to hide."""
    # We received quite a lot of errors based on #tP not being visible. This tries to wait for it.
    wait_for(sel.is_displayed, ["#tP"], num_sec=5, delay=0.1, message="page ready")
    ActionChains(sel.browser()).move_to_element(sel.element("#tP")).perform()
    wait_for(lambda: not any_box_displayed(), num_sec=10, delay=0.1, message="menu box")


def os_infra_specific(without_infra, with_infra, with_both=None):
    """If there is even one OS Infra provider, UI changes. This is wrapper for it.

    Args:
        without_infra: What the text should be when there are not OS infra providers.
        with_infra: What the text should be when there is at least on OS Infra provider.
        with_both: If specified, will be used when there are both kinds of providers. If not
            specified, ``without_infra / with_infra`` will be used.
    """
    def _decide():
        if current_version() < "5.4.0.0.25":
            # Don't bother, the code is not in
            return without_infra

        if store.current_appliance.has_os_infra and store.current_appliance.has_non_os_infra:
            return with_both or "{} / {}".format(without_infra, with_infra)
        elif store.current_appliance.has_os_infra:
            return with_infra
        else:
            return without_infra
    return _decide


def _tree_func_with_grid(*args):
    def f():
        accordion.tree(*args)
        toolbar.set_vms_grid_view()
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
        ('clouds_providers', 'Providers', toolbar.set_vms_grid_view),
        ('clouds_availability_zones', 'Availability Zones'),
        ('clouds_tenants', 'Tenants'),
        ('clouds_flavors', 'Flavors'),
        ('clouds_security_groups', 'Security Groups'),
        ('clouds_instances', 'Instances',
            _tree_func_with_grid("Instances by Provider", "Instances by Provider")),
        ('clouds_stacks', 'Stacks')
    ),
    ('infrastructure', 'Infrastructure'): (
        ('infrastructure_providers', 'Providers', toolbar.set_vms_grid_view),
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
    ('storage', 'Storage'): (
        ('filers', 'Filers'),
        ('volumes', 'Volumes'),
        ('luns', 'LUNs'),
        ('file_shares', 'File Shares'),
        ('storage_managers', 'Storage Managers')
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
            sel.element(version.pick({
                "5.4": ("//nav[contains(@class, 'navbar')]//ul/li[@class='active']"
                        "/a[normalize-space(.)='{}']/..".format(secondlevel)),
                version.LOWEST: ("//div[@class='navbar']//ul/li[@class='active']"
                                 "/a[normalize-space(.)='{}']/..".format(secondlevel))
            }))
        except NoSuchElementException:
            return False
    return True


def nav_to_fn(toplevel, secondlevel=None, reset_action=None):
    def f(_):
        if callable(toplevel):
            top_level = toplevel()
        else:
            top_level = toplevel
        if not is_page_active(top_level):
            try:
                # Try to circumvent the issue on fir
                get_rid_of_the_menu_box()
                open_top_level(top_level)
                get_rid_of_the_menu_box()
                if get_current_toplevel_name() != top_level:
                    # Infrastructure / Requests workaround
                    sel.move_to_element(get_top_level_element(top_level))
                    # Using pure move_to_element to not move the mouse anywhere else
                    # So in this case, we move the mouse to the first item of the second level
                    ActionChains(sel.browser())\
                        .move_to_element(sel.element(Loc.secondlevel_first_item_loc.format(
                            top_level)))\
                        .click()\
                        .perform()
                    get_rid_of_the_menu_box()
                    # Now when we went directly to the first item, everything should just work
                    tl = get_current_toplevel_name()
                    if tl != top_level:
                        raise Exception("Navigation screwed! (wanted {}, got {}".format(top_level,
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
            if callable(secondlevel):
                second_level = secondlevel()
            else:
                second_level = secondlevel
            open_second_level(get_top_level_element(top_level), second_level)
            get_rid_of_the_menu_box()

        if reset_action is not None:
            if callable(reset_action):
                reset_action()
            else:
                sel.click(reset_action)
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
            if menu_path == '%s/%s' % (toplevel, second_level):
                return secondlevel_dest


def visible_toplevel_tabs():
    menu_names = []
    ele = version.pick({
        "5.4": 'li/a[2]',
        version.LOWEST: 'li/a'})
    for menu_elem in sel.elements(ele, root=Loc.toplevel_tabs_loc):
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
        menu_elem = sel.element(Loc.toplevel_loc.format(menu_name))
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
