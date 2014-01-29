"""
cfme.web_ui.accordion
---------------------

A set of functions for dealing with the accordions.


"""
import cfme.fixtures.pytest_selenium as sel

DHX_ITEM = 'div[contains(@class, "dhx_acc_item")]'
DHX_LABEL = 'div[contains(@class, "dhx_acc_item_label")]'
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

    Args:
        name: The name of the accordion.
    Returns: ``True`` if the button is depressed, ``False`` if not.
    """

    xpath = locate(name)
    root = sel.element(xpath)
    el = sel.element('./%s/%s' % (DHX_LABEL, DHX_ARROW), root)
    class_att = sel.get_attribute(el, 'class').split(" ")
    if "item_opened" in class_att:
        return True
    else:
        return False
