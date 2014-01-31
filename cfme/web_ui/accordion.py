"""A set of functions for dealing with accordions in the UI.


"""
import cfme.fixtures.pytest_selenium as sel

DHX_ITEM = 'div[contains(@class, "dhx_acc_item") or @class="topbar"]'
DHX_LABEL = '*[contains(@class, "dhx_acc_item_label") or contains(@data-remote, "true")]'
DHX_ARROW = 'div[contains(@class, "dhx_acc_item_arrow")]'


def locate(name):
    """ Returns an accordion by name

    Args:
        name: The name of the accordion.
    Returns: A web element of the selected accordion.
    """

    xpath = '//%s/%s[contains(., "%s")]/..' % (DHX_ITEM, DHX_LABEL, name)
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
