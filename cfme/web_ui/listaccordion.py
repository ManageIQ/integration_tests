"""A set of functions for dealing with accordions in the UI.

Usage:

    Using Accordions is simply a case of either selecting it to return the element,
    or using the built in click method. As shown below::

      acc = web_ui.accordion

      acc.click('Diagnostics')
      acc.is_active('Diagnostics')

Note:
    Inactive links are not available in any way.
"""

import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import ListAccordionLinkNotFound

DHX_ITEM = 'div[contains(@class, "dhx_acc_item") or @class="topbar"]'
DHX_LABEL = '*[contains(@data-remote, "true") and .="%s"]'


def locate(name):
    """ Returns a list-accordion by name

    Args:
        name: The name of the accordion.
    Returns: An xpath locator of the selected accordion.
    """
    label_to_use = DHX_LABEL % (name)
    xpath = '//%s/%s' % (DHX_ITEM, label_to_use)
    return xpath


def click(name):
    """ Clicks an accordion and returns it

    Args:
        name: The name of the accordion.
    """
    xpath = locate(name)
    el = sel.element(xpath)
    was_active = is_active(name)
    sel.click(el)
    if not was_active:
        # sel.wait_for_element(cls._content_element(name))
        # This is ugly but the above doesn't work
        import time
        time.sleep(3)


def _content_element(name):
    """ Element with content of section specified by name

    Args:
        name: The name of the accordion.
    """
    root = sel.element(locate(name))
    el = sel.element('./../following-sibling::div[1]', root=root)
    return el


def is_active(name):
    """ Checks if an accordion is currently open

    Args:
        name: The name of the accordion.
    Returns: ``True`` if the button is depressed, ``False`` if not.
    """
    return sel.is_displayed(_content_element(name))


def is_link_internal(name, link_title):
    """ Checks if link in accordion is internal or not

    Args:
        name: Name of the accordion.
        link_title: Title of link in expanded accordion section.
    """
    link_root = _content_element(name)
    link = ListAccordionLink(link_title, link_root)
    return link.is_internal()


def select(name, link_title):
    """ Clicks an active link in accordion section

    Args:
        name: Name of the accordion.
        link_title: Title of link in expanded accordion section.
    """
    if not is_active(name):
        click(name)
    link_root = _content_element(name)
    link = ListAccordionLink(link_title, link_root)
    link.click()


class ListAccordionLink(object):
    """ Active link in an accordion section

    Args:
        title: The title of the link.
    """
    def __init__(self, title, root=None):
        self.root = root
        self.title = title

    def locate(self):
        """ Locates an active link.

        Returns: An XPATH locator for the element."""
        return './/div[@class="panecontent"]//a[@title="%s"]/img/..' % self.title

    def _check_exists(self):
        try:
            sel.element(self.locate(), root=self.root)
        except sel.NoSuchElementException:
            raise ListAccordionLinkNotFound(
                'No active link with title "{}" found.'.format(self.title))

    def is_internal(self):
        """ Checks if the link leads internally or not

        Returns: ``True`` if the element is an internal link, ``False`` if not.
        """
        self._check_exists()
        el = sel.element(self.locate(), root=self.root)
        img = sel.element('./img', root=el)
        if 'internal' in sel.get_attribute(img, 'src'):
            return True
        else:
            return False

    def click(self):
        """ Clicks a link by title.

        Args:
            title: The title of the button to check.

        Raises:
            ListAccordionLinkNotFound: when active link is not found.
        """
        self._check_exists()
        sel.click(sel.element(self.locate(), root=self.root))
