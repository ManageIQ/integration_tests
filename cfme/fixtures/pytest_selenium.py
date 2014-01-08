from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from utils import conf
from utils.browser import browser


def baseurl():
    return conf.env['base_url']


ajax_wait_js = """
var inflight = function() {
    return Array.prototype.slice.call(arguments,0).reduce(function (n, f) {
        try {flt = f() || 0;
             flt=(Math.abs(flt)+flt)/2; return flt + n;} catch (e) { return n }}, 0)};
return inflight(function() { return jQuery.active},
                function() { return Ajax.activeRequestCount},
                function() { return window.miqAjaxTimers},
                function() { if (document.readyState == "complete") { return 0 } else { return 1}});
"""


# END CFME specific stuff, should eventually factor
# out everything below into a lib

def elements(o):
    '''Convert o to list of matching WebElements. Strings are considered xpath.'''
    t = type(o)
    if t == str:
        return browser().find_elements_by_xpath(o)
    elif t == WebElement:
        return [o]
    elif t == tuple:
        return browser().find_elements(*o)
    else:
        raise TypeError("Don't know how to convert %s to WebElement." % o)


def element(o):
    matches = elements(o)
    if not matches:
        raise NoSuchElementException("Element {} not found on page.".format(o))
    return elements(o)[0]


def wait_until(f, msg="Webdriver wait timed out"):
    WebDriverWait(browser(), 120.0).until(f, msg)


def _nothing_in_flight(s):
    #sleep(0.5)
    in_flt = s.execute_script(ajax_wait_js)
    #print in_flt
    return in_flt == 0


def wait_for_ajax():
    wait_until(_nothing_in_flight, "Ajax wait timed out")


def is_displayed(loc):
    try:
        return element(loc).is_displayed()
    except NoSuchElementException:
        return False


def wait_for_element(loc):
    wait_until(lambda s: is_displayed(loc), "Element '{}' did not appear as expected.".format(loc))


def click(loc):
    ActionChains(browser()).move_to_element(element(loc)).click().perform()
    wait_for_ajax()


def move_to_element(loc):
    ActionChains(browser()).move_to_element(element(loc)).perform()


def text(loc):
    return element(loc).text


def tag(loc):
    return element(loc).tag_name


def get_attribute(loc, attr):
    return element(loc).get_attribute(attr)


def send_keys(loc, text):
    if text is not None:
        ActionChains(browser()).move_to_element(element(loc)).send_keys(text).perform()
        wait_for_ajax()


def set_text(loc, text):
    if text is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        el.clear()
        el.send_keys(text)
        wait_for_ajax()


def select_by_text(loc, value):
    if value is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        Select(el).select_by_visible_text(value)
        wait_for_ajax()


def select_by_value(loc, text):
    if text is not None:
        el = element(loc)
        ActionChains(browser()).move_to_element(el).perform()
        Select(el).select_by_value(text)
        wait_for_ajax()


def checkbox(loc, set_to=False):
    '''Checks a given checkbox

    Finds an element given by loc and checks it

    Args:
        loc: The locator of the element
        value: The attr value to compare against

    Returns: None
    '''
    el = element(loc)
    ActionChains(browser()).move_to_element(el).perform()
    if el.is_selected() is not set_to:
        el.click()
        wait_for_ajax()


def current_url():
    return browser().current_url


def get(url):
    return browser().get(url)


def move_to_fn(*els):
    def f():
        for el in els:
            move_to_element(el)
    return f


def click_fn(*els):
    def f():
        for el in els:
            click(el)
    return f
