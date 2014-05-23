"""A set of functions for dealing with accordions in the UI.

Usage:

    Using Accordions is simply a case of either selecting it to return the element,
    or using the built in click method. As shown below::

      acc = web_ui.accordion

      acc.click('Diagnostics')
      acc.is_active('Diagnostics')
"""
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import Tree

DHX_ITEM = 'div[contains(@class, "dhx_acc_item") or @class="topbar"]'
DHX_LABEL = '*[contains(@class, "dhx_acc_item_label") or contains(@data-remote, "true")]'
DHX_ARROW = 'div[contains(@class, "dhx_acc_item_arrow")]'


def locate(name):
    """ Returns an accordion by name

    Args:
        name: The name of the accordion.
    Returns: A web element of the selected accordion.
    """

    xpath = '//%s/%s//span[normalize-space(.)="%s"]' % (DHX_ITEM, DHX_LABEL, name)
    return xpath


def click(name):
    """ Clicks an accordion and returns it

    Args:
        name: The name of the accordion.
    Returns: A web element of the clicked accordion.
    """
    xpath = locate(name)
    el = sel.element(xpath)
    return sel.click(el)


def is_active(name):
    """ Checks if an accordion is currently open

    Note: Only works on traditional accordions.

    Args:
        name: The name of the accordion.
    Returns: ``True`` if the button is depressed, ``False`` if not.
    """

    xpath = locate(name)
    root = sel.element(xpath)
    el = sel.element('./%s/%s' % (DHX_LABEL, DHX_ARROW), root=root)
    class_att = sel.get_attribute(el, 'class').split(" ")
    if "item_opened" in class_att:
        return True
    else:
        return False


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
    click(name)
    tree = Tree(
        sel.first_from(
            # Current tree
            "../../div[contains(@class, 'dhxcont_global_content_area')]//"
            "ul[@class='dynatree-container']",
            # Legacy tree
            "../../div[contains(@class, 'dhxcont_global_content_area')]//"
            "div[@class='containerTableStyle']//table[not(ancestor::tr[contains(@style,'none')])]",
            root=sel.element(locate(name))
        )
    )
    if path:
        return tree.click_path(*path)
    else:
        return tree
