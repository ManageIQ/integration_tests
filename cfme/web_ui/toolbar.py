"""A set of functions for dealing with the toolbar buttons

The main CFME toolbar is accessed by using the Root and Sub titles of the buttons.

Usage:

    tb = web_ui.toolbar
    tb.select('Configuration', 'Add a New Host')

"""
import cfme.fixtures.pytest_selenium as sel
from selenium.webdriver.common.by import By
from cfme.exceptions import ToolbarOptionGreyedOrUnavailable
from utils import version
from utils.log import logger
from xml.sax.saxutils import quoteattr, unescape


def xpath_quote(x):
    """Putting strings in xpath requires unescape also"""
    # TODO: Move it to some library!
    return unescape(quoteattr(x))


def root_loc(root):
    """ Returns the locator of the root button

    Args:
        root: The string name of the button.
    Returns: A locator for the root button.
    """
    return (By.XPATH,
            ("//div[contains(@class, 'dhx_toolbar_btn')][contains(@title, {0})] | "
             "//div[contains(@class, 'dhx_toolbar_btn')][contains(@data-original-title, {0})] | "
             "//button[normalize-space(.) = {0}] |"
             "//button[@data-original-title = {0}] |"
             "//a[@data-original-title = {0}]/.. |"
             "//a[@title = {0}]/.. |"
             "//button[@title = {0}]")
            .format(xpath_quote(root)))


def sub_loc(sub):
    """ Returns the locator of the sub button

    Args:
        sub: The string name of the button.
    Returns: A locator for the sub button.
    """
    return (
        By.XPATH,
        ("//div[contains(@class, 'btn_sel_text')][normalize-space(text()) = {0}]/../.. |"
         "//ul[contains(@class, 'dropdown-menu')]//li[normalize-space(.) = {0}]").format(
            xpath_quote(sub)))


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


def select(*args, **kwargs):
    logger.debug('Selecting %r', args)
    if version.current_version() > '5.5.0.7':
        return pf_select(*args, **kwargs)
    else:
        return old_select(*args, **kwargs)


def pf_select(root, sub=None, invokes_alert=False):
    """ Clicks on a button by calling the click event with the jquery trigger.

    Args:
        root: The root button's name as a string.
        sub: The sub button's name as a string. (optional)
        invokes_alert: If ``True``, then the behaviour is little bit different. After the last
            click, no ajax wait and no move away is done to be able to operate the alert that
            appears after click afterwards. Defaults to ``False``.
    Returns: ``True`` if everything went smoothly
    Raises: :py:class:`cfme.exceptions.ToolbarOptionGreyedOrUnavailable`
    """

    sel.wait_for_ajax()
    if isinstance(root, dict):
        root = version.pick(root)
    if isinstance(sub, dict):
        sub = version.pick(sub)

    if sub:
        q_sub = xpath_quote(sub).replace("'", "\\'")
        sel.execute_script(
            "return $('a:contains({})').trigger('click')".format(q_sub))
    else:
        q_root = xpath_quote(root).replace("'", "\\'")
        try:
            sel.element("//button[@data-original-title = {0}] | "
                        "//a[@data-original-title = {0}]".format(q_root))
            sel.execute_script(
                "return $('*[data-original-title={}]').trigger('click')".format(q_root))
        except sel.NoSuchElementException:
            try:
                sel.element("//button[@title={}]".format(q_root))
                sel.execute_script(
                    "return $('button[title={}]').trigger('click')".format(q_root))
            except sel.NoSuchElementException:
                try:
                    sel.element("//button[contains(@title, {})]".format(q_root))
                    sel.execute_script(
                        "return $('button:contains({})').trigger('click')".format(q_root))
                except sel.NoSuchElementException:
                    # The view selection buttons?
                    sel.click("//li/a[@title={}]/*[self::i or self::img]/../..".format(q_root))

    if not invokes_alert:
        sel.wait_for_ajax()
    return True


def old_select(root, sub=None, invokes_alert=False):
    """ Clicks on a button by calling the dhtmlx toolbar callEvent.

    Args:
        root: The root button's name as a string.
        sub: The sub button's name as a string. (optional)
        invokes_alert: If ``True``, then the behaviour is little bit different. After the last
            click, no ajax wait and no move away is done to be able to operate the alert that
            appears after click afterwards. Defaults to ``False``.
    Returns: ``True`` if everything went smoothly
    Raises: :py:class:`cfme.exceptions.ToolbarOptionGreyedOrUnavailable`
    """
    # wait for ajax on select to prevent pickup up a toolbar button in the middle of a page change
    sel.wait_for_ajax()
    if isinstance(root, dict):
        root = version.pick(root)
    if sub is not None and isinstance(sub, dict):
        sub = version.pick(sub)

    root_obj = version.pick({'5.4': 'miq_toolbars',
        '5.5.0.7': 'ManageIQ.toolbars'})

    if sub:
        search = sub_loc(sub)
    else:
        search = root_loc(root)

    eles = sel.elements(search)

    for ele in eles:
        idd = sel.get_attribute(ele, 'idd')
        if idd:
            break
    else:
        raise ToolbarOptionGreyedOrUnavailable(
            "Toolbar button {}/{} is greyed or unavailable!".format(root, sub))

    buttons = sel.execute_script('return {}'.format(root_obj))
    tb_name = None
    for tb_key, tb_obj in buttons.iteritems():
        for btn_key, btn_obj in tb_obj['buttons'].iteritems():
            if btn_obj['name'] == idd:
                tb_name = tb_key
    if not tb_name:
        raise ToolbarOptionGreyedOrUnavailable(
            "Toolbar button {}/{} is greyed or unavailable!".format(root, sub))

    sel.execute_script(
        "{}['{}']['obj'].callEvent('onClick', ['{}'])".format(root_obj, tb_name, idd))

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
    if {"pres", "active", "pres_dis"}.intersection(set(class_att)):
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
        if {"tr_btn_disabled", "disabled"}.intersection(set(class_att)):
            logger.debug("%s option greyed out, mouseover reason: %s",
                sub, sel.get_attribute(el, 'title'))
            return True
    else:
        if {"disabled", "dis"}.intersection(set(class_att)):
            return True
    return False


RELOAD_LOC = "//div[@title='Reload current display']|//button[@title='Reload Current Display']"


def refresh():
    """Refreshes page, attempts to use cfme refresh button otherwise falls back to browser refresh.
    """
    if sel.is_displayed(RELOAD_LOC):
        sel.click(RELOAD_LOC)
    else:
        sel.refresh()


def exists(root, sub=None, and_is_not_greyed=False):
    """ Checks presence and usability of toolbar buttons.

    By default it checks whether the button is available, not caring whether it is greyed or not.
    You can optionally enable check for greyedness.

    Args:
        root: Button name.
        sub: Item name (optional)
        and_is_not_greyed: Check if the button is available to click.

    """
    sel.wait_for_ajax()
    if isinstance(root, dict):
        root = version.pick(root)
    if isinstance(sub, dict):
        sub = version.pick(sub)

    try:
        greyed = is_greyed(root, sub)
        if and_is_not_greyed:
            return not greyed
        else:
            return True
    except sel.NoSuchElementException:
        return False
