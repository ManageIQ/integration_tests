"""A set of functions for dealing with accordions in the UI.

Usage:

    Using Accordions is simply a case of either selecting it to return the element,
    or using the built in click method. As shown below::

      acc = web_ui.accordion

      acc.click('Diagnostics')
      acc.is_active('Diagnostics')
"""

from xml.sax.saxutils import quoteattr, unescape

import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import AccordionItemNotFound
from cfme.web_ui import Tree, BootstrapTreeview
from utils import version
from utils.log import logger
from utils.wait import wait_for

DHX_ITEM = 'div[contains(@class, "dhx_acc_item") or @class="topbar"]'
DHX_LABEL = '*[contains(@class, "dhx_acc_item_label") or contains(@data-remote, "true")]'
DHX_ARROW = 'div[contains(@class, "dhx_acc_item_arrow")]'
NEW_ACC = '//div[@id="accordion"]//h4[@class="panel-title"]//a[normalize-space(.)={}]'


def locate(name):
    """ Returns an accordion by name

    Args:
        name: The name of the accordion.
    Returns: A web element of the selected accordion.
    """
    xpath = version.pick({
        version.LOWEST: '//{}/{}//span[normalize-space(.)="{}"]'.format(
            DHX_ITEM, DHX_LABEL, name),
        '5.5.0.6': NEW_ACC.format(unescape(quoteattr(name)))})
    return xpath


def click(name):
    """ Clicks an accordion and returns it

    Args:
        name: The name of the accordion.
    Returns: A web element of the clicked accordion.
    """
    try:
        el = sel.element(locate(name))
        if not is_active(name):
            return sel.click(el)
    except sel.NoSuchElementException:
        raise AccordionItemNotFound("Accordion item '{}' not found!".format(name))


def _get_accordion_collapsed(name):
    """ Returns if an accordion is collapsed or not, used with is_active

    Args:
        name: The name of the accordion
    Returns: ``True`` if the accordion is open, ``False`` if it is closed.
    """

    if version.current_version() < '5.5.0.6':
        root = sel.element(locate(name))
        # It seems there are two possibilities, so let's handle both.
        loc = "|".join([
            "./{}/{}".format(DHX_LABEL, DHX_ARROW),
            "../{}".format(DHX_ARROW)])
        el = sel.element(loc, root=root)
        class_att = sel.get_attribute(el, 'class').split(" ")
        return "item_opened" in class_att
    else:
        class_att = sel.get_attribute(sel.element(locate(name)), 'class').split(" ")
        return "collapsed" not in class_att


def is_active(name):
    """ Checks if an accordion is currently open

    Note: Only works on traditional accordions.

    Args:
        name: The name of the accordion.
    Returns: ``True`` if the button is depressed, ``False`` if not.
    """

    try:
        return _get_accordion_collapsed(name)
    except sel.NoSuchElementException:
        raise AccordionItemNotFound("Accordion item '{}' not found!".format(name))


DYNATREE = "../../..//div[@class='panel-body']//ul[@class='dynatree-container']"
TREEVIEW = '../../..//div[contains(@class, "treeview")]'
ANY_TREE = '|'.join([DYNATREE, TREEVIEW])


def tree(name, *path):
    """Get underlying Tree() object. And eventually click path.

    If the accordion is not active, will be clicked.
    Attention! The object is 'live' so when it's obscured, it won't work!

    Usage:
        accordion.tree("Something").click_path("level 1", "level 2")
        accordion.tree("Something", "level 1", "level 2")  # is the same

    Args:
        *path: If specified, it will directly pass these parameters into click_path of Tree.
            Otherwise it returns the Tree object.
    """
    try:
        if not is_active(name):
            logger.debug('Clicking accordion item %s because it is not active.', name)
            click(name)
    except AccordionItemNotFound:
        logger.debug('Clicking accordion item %s because AccordionItemNotFound raised.', name)
        click(name)

    locator = locate(name)
    # Wait a bit for any of the trees to appear
    wait_for(
        lambda: sel.is_displayed(ANY_TREE, root=locator),
        quiet=True, silent_failure=True, delay=0.2, timeout=5)
    if sel.is_displayed(DYNATREE, root=locator):
        # Dynatree detected
        tree = Tree(sel.element(DYNATREE, root=locator))
    elif sel.is_displayed(TREEVIEW, root=locator):
        # treeview detected
        el = sel.element(TREEVIEW, root=locator)
        tree_id = sel.get_attribute(el, 'id')
        tree = BootstrapTreeview(tree_id)
    else:
        raise TypeError('None of the supported trees was detected.')

    if path:
        return tree.click_path(*path)
    else:
        return tree
