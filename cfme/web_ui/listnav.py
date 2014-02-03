"""
Usage::
    locate('IPMI Enabled')
    click('IPMI Enabled')
"""
import cfme.fixtures.pytest_selenium as sel


def locate(title):
    """ Locates a list nav button.

    Args:
        title: The title of the button.
    Returns: An XPATH locator for the element."""
    return '//div[@class="panecontent"]//a[contains(., "%s")]' % title


def is_internal(title):
    """ Checks if the link leads internally or not

    Args:
        title: The title of the button to check.
    Returns: ``True`` if the element is an internal link, ``False`` if not.
    """
    loc = sel.element(locate(title))
    href = sel.get_attribute(loc, 'href').replace(sel.baseurl(), '')
    img = sel.element('//div[@class="panecontent"]//a[@href="%s"]/img' % href)
    if 'internal' in sel.get_attribute(img, 'src'):
        return True
    else:
        return False


def click(title):
    """ Clicks an element by title.

    Args:
        title: The title of the button to check.
    """
    sel.click(sel.element(locate(title)))
