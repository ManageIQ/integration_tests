"""A set of functions for dealing with the toolbar buttons

The main CFME toolbar is accessed by using the Root and Sub titles of the buttons.

Usage:

    tb = web_ui.toolbar
    tb.select('Configuration', 'Add a New Host')

"""
import cfme.fixtures.pytest_selenium as sel
from selenium.webdriver.common.by import By
from cfme.exceptions import ToolbarOptionGreyedOrUnavailable
from cfme.web_ui import Region
from utils import version
from utils.log import logger
from xml.sax.saxutils import quoteattr

# Common locators
locators = Region(
    locators={
        'grid_view': "//div[@title='Grid View']",
        'list_view': "//div[@title='List View']",
        'tile_view': "//div[@title='Tile View']",
        'compressed_view': "//div[@title='Compressed View']",
        'expanded_view': "//div[@title='Expanded View']",
        'details_view': "//div[@title='Details Mode']",
        'exists_view': "//div[@title='Exists Mode']",
        'hybrid_view': "//div[@title='Hybrid View']",
        'graph_view': "//div[@title='Graph View']",
        'tabular_view': "//div[@title='Tabular View']"
    }
)


def root_loc(root):
    """ Returns the locator of the root button

    Args:
        root: The string name of the button.
    Returns: A locator for the root button.
    """
    return (By.XPATH,
            "//div[contains(@class, 'dhx_toolbar_btn')][contains(@title, %s)]" % quoteattr(root))


def sub_loc(sub):
    """ Returns the locator of the sub button

    Args:
        sub: The string name of the button.
    Returns: A locator for the sub button.
    """
    return (
        By.XPATH,
        "//div[contains(@class, 'btn_sel_text')][normalize-space(text()) = {}]/../..".format(
            quoteattr(sub)))


def select_n_move(el):
    """ Clicks an element and then moves the mouse away

    This is required because if the button is active and we clicked it, the CSS class
    doesn't change until the mouse is moved away.

    Args:
        el: The element to click on.
    Returns: None
    """
    # .. if we don't move the "mouse" the button stays active
    sel.click(el)
    sel.move_to_element(".navbar-brand")


def select(root, sub=None, invokes_alert=False):
    """ Clicks on a button by calling the :py:meth:`click_n_move` method.

    Args:
        root: The root button's name as a string.
        sub: The sub button's name as a string. (optional)
        invokes_alert: If ``True``, then the behaviour is little bit different. After the last
            click, no ajax wait and no move away is done to be able to operate the alert that
            appears after click afterwards. Defaults to ``False``.
    Returns: ``True`` if everything went smoothly
    Raises: :py:class:`cfme.exceptions.ToolbarOptionGreyed`
    """
    # wait for ajax on select to prevent pickup up a toolbar button in the middle of a page change
    sel.wait_for_ajax()
    if isinstance(root, dict):
        root = version.pick(root)
    if sub is not None and isinstance(sub, dict):
        sub = version.pick(sub)

    root_obj = version.pick({'5.4': 'miq_toolbars',
        '5.5.0.7': 'ManageIQ.toolbars'})

    if not is_greyed(root) and not is_greyed(root, sub):
        buttons = sel.execute_script("return {}['center_tb']['buttons']".format(root_obj))

        try:
            button_text_title = sel.get_attribute(sub_loc(sub), 'title')
        except sel.NoSuchElementException:
            raise ToolbarOptionGreyedOrUnavailable(
                "Toolbar button {}/{} is greyed or unavailable!".format(root, sub))

        for key, obj in buttons.iteritems():
            title = obj.get('title', None)
            if button_text_title == title:
                break
        else:
            raise ToolbarOptionGreyedOrUnavailable(
                "Toolbar button {}/{} is greyed or unavailable!".format(root, sub))
        sel.execute_script(
            "{}['center_tb']['obj'].callEvent('onClick', ['{}'])".format(root_obj, key))
    else:
        raise ToolbarOptionGreyedOrUnavailable(
            "Toolbar button {}/{} is greyed or unavailable!".format(root, sub))
    if not invokes_alert:
        sel.wait_for_ajax()
    return True


def is_active(root):
    """ Checks if a button is currently depressed

    Args:
        root: The root button's name as a string.
    Returns: ``True`` if the button is depressed, ``False`` if not.
    """
    el = sel.element(root_loc(root))
    class_att = sel.get_attribute(el, 'class').split(" ")
    if "over" in class_att:
        return True
    else:
        return False


def is_greyed(root, sub=None):
    """ Checks if a button is greyed out.

    Args:
        root: The root button's name as a string.
    Returns: ``True`` if the button is greyed, ``False`` if not.
    """
    if sub:
        btn = sub_loc(sub)
    else:
        btn = root_loc(root)

    el = sel.element(btn)
    class_att = sel.get_attribute(el, 'class').split(" ")

    if sub:
        if "tr_btn_disabled" in class_att:
            logger.debug("{} option greyed out, mouseover reason: {}".format(
                sub, sel.get_attribute(el, 'title')))
            return True
    else:
        if "dis" in class_att:
            return True
    return False


def refresh():
    """Refreshes page, attempts to use cfme refresh button otherwise falls back to browser refresh.
    """
    if sel.is_displayed("//div[@title='Reload current display']"):
        sel.click("//div[@title='Reload current display']")
    else:
        sel.refresh()


def is_vms_grid_view():
    """Returns whether grid view is selected or not.
    """
    return "pres_dis" in sel.get_attribute(locators.grid_view, "class")


def is_vms_list_view():
    """Returns whether list view is selected or not.
    """
    return "pres_dis" in sel.get_attribute(locators.list_view, "class")


def is_vms_tile_view():
    """Returns whether tile view is selected or not.
    """
    return "pres_dis" in sel.get_attribute(locators.tile_view, "class")


def is_vms_expanded_view():
    """Returns whether expanded view is selected or not.
    """
    return "pres" in sel.get_attribute(locators.expanded_view, "class")


def is_vms_compressed_view():
    """Returns whether compressed view is selected or not.
    """
    return "pres" in sel.get_attribute(locators.compressed_view, "class")


def is_vms_details_view():
    """Returns whether details view is selected or not.
    """
    return "pres" in sel.get_attribute(locators.details_view, "class")


def is_vms_exists_view():
    """Returns whether exists mode is selected or not.
    """
    return "pres" in sel.get_attribute(locators.exists_view, "class")


def is_vms_hybrid_view():
    """Returns whether hybrid view is selected or not.
    """
    return "pres" in sel.get_attribute(locators.hybrid_view, "class")


def is_vms_graph_view():
    """Returns whether graph view is selected or not.
    """
    return "pres" in sel.get_attribute(locators.graph_view, "class")


def is_vms_tabular_view():
    """Returns whether tabular view is selected or not.
    """
    return "pres" in sel.get_attribute(locators.tabular_view, "class")


def set_vms_grid_view():
    """Set the view to grid.
    """
    if not is_vms_grid_view():
        sel.click(locators.grid_view)


def set_vms_list_view():
    """Set the view to list.
    """
    if not is_vms_list_view():
        sel.click(locators.list_view)


def set_vms_tile_view():
    """Set the view to tile.
    """
    if not is_vms_tile_view():
        sel.click(locators.tile_view)


def set_vms_expanded_view():
    """Set the view to expanded.
    """
    if not is_vms_expanded_view():
        sel.click(locators.expanded_view)


def set_vms_compressed_view():
    """Set the view to compressed.
    """
    if not is_vms_compressed_view():
        sel.click(locators.compressed_view)


def set_vms_details_view():
    """Set the view to details.
    """
    if not is_vms_details_view():
        sel.click(locators.details_view)


def set_vms_exists_view():
    """Set the view to exists.
    """
    if not is_vms_exists_view():
        sel.click(locators.exists_view)


def set_vms_hybrid_view():
    """Set the view to hybrid.
    """
    if not is_vms_hybrid_view():
        sel.click(locators.hybrid_view)


def set_vms_graph_view():
    """Set the view to graph.
    """
    if not is_vms_graph_view():
        sel.click(locators.graph_view)


def set_vms_tabular_view():
    """Set the view to tabular.
    """
    if not is_vms_tabular_view():
        sel.click(locators.tabular_view)
