# -*- coding: utf-8 -*-
import inspect
from functools import wraps
from selenium.common.exceptions import \
    (ErrorInResponseException, InvalidSwitchToTargetException, NoSuchAttributeException,
     NoSuchElementException, NoAlertPresentException, UnexpectedAlertPresentException,
     InvalidElementStateException, MoveTargetOutOfBoundsException, WebDriverException,
     StaleElementReferenceException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.file_detector import LocalFileDetector, UselessFileDetector
from selenium.webdriver.remote.webelement import WebElement
from smartloc import Locator
from textwrap import dedent
from time import sleep

from .beacon import before_element_query, element_found, element_not_found


class BrowserParentContextProxy(object):
    def __init__(self, browser, parents):
        self._browser = browser
        self._parents = parents

    def __getattr__(self, attr):
        value = getattr(self._browser, attr)
        try:
            argspec = inspect.getargspec(value)
            args = argspec.args
            if 'parents' not in args:
                return value

            # Otherwise wrap it
            @wraps(value)
            def wrapped(*args, **kwargs):
                # Inject parents into the arguments
                if 'parents' not in kwargs:
                    kwargs['parents'] = self._parents
                return value(*args, **kwargs)

            return wrapped
        except TypeError:
            return value


class Browser(object):
    """Equivalent of pytest_selenium - browser functions"""
    def __init__(self, navigator):
        self.navigator = navigator

    @property
    def selenium(self):
        return self.navigator.selenium

    def in_parent_context(self, parents):
        return BrowserParentContextProxy(self, parents)

    @staticmethod
    def _process_locator(locator):
        if isinstance(locator, WebElement):
            return locator
        try:
            return Locator(locator)
        except TypeError:
            if hasattr(locator, '__element__'):
                return locator.__element__()
            else:
                raise

    def elements(self, locator, parents=None, check_visibility=False, _suppress_signal=False):
        locator = self._process_locator(locator)
        if not _suppress_signal:
            before_element_query.trigger(browser=self, locator=locator)
        # Get result
        if isinstance(locator, WebElement):
            result = [locator]
        else:
            # Get the direct parent object
            parents = list(parents) if parents else []
            if parents:
                root_element = self.element(parents.pop(0), parents=parents, _suppress_signal=True)
            else:
                root_element = self.selenium
            result = root_element.find_elements(*locator)

        if check_visibility:
            result = filter(self.is_displayed, result)

        if not _suppress_signal:
            for element in result:
                element_found.trigger(browser=self, locator=locator, element=element)

        return result

    def element(self, locator, parents=None, check_visibility=False):
        try:
            return self.elements(locator, parents=parents, check_visibility=check_visibility)[0]
        except IndexError:
            element_not_found.trigger(browser=self, locator=locator)
            raise NoSuchElementException('Could not find an element {}'.format(repr(locator)))

    def click(self, locator, parents=None, check_visibility=False):
        self.move_to_element(locator, parents=parents, check_visibility=check_visibility)
        # and then click on current mouse position
        ActionChains(self.selenium).click().perform()

    def is_displayed(self, locator, parents=None):
        retry = True
        tries = 10
        while retry:
            retry = False
            try:
                return self.move_to_element(locator, parents=parents).is_displayed()
            except (NoSuchElementException, MoveTargetOutOfBoundsException):
                return False
            except StaleElementReferenceException:
                if isinstance(locator, WebElement) or tries <= 0:
                    # We cannot fix this one.
                    raise
                retry = True
                tries -= 1
                sleep(0.1)

        # Just in case
        return False

    def move_to_element(self, locator, parents=None, check_visibility=False):
        el = self.element(locator, parents=parents, check_visibility=check_visibility)
        if el.tag_name == "option":
            # Instead of option, let's move on its parent <select> if possible
            parent = self.element("..", parents=[el])
            if parent.tag_name == "select":
                self.move_to_element(parent, parents=parents)
                return el
        move_to = ActionChains(self.selenium).move_to_element(el)
        try:
            move_to.perform()
        except MoveTargetOutOfBoundsException:
            # ff workaround
            self.execute_script("arguments[0].scrollIntoView();", el)
            try:
                move_to.perform()
            except MoveTargetOutOfBoundsException:  # This has become desperate now.
                raise MoveTargetOutOfBoundsException(
                    "Despite all the workarounds, scrolling to `{}` was unsuccessful.".format(
                        locator))
        return el

    def execute_script(self, script, *args, **kwargs):
        return self.selenium.execute_script(dedent(script), *args, **kwargs)

    def classes(self, *args, **kwargs):
        """Return a list of classes attached to the element."""
        return set(self.execute_script(
            "return arguments[0].classList;", self.element(*args, **kwargs)))

    def tag(self, *args, **kwargs):
        return self.element(*args, **kwargs).tag_name

    def get_attribute(self, attr, *args, **kwargs):
        return self.element(*args, **kwargs).get_attribute(attr)

    def send_keys(self, text, *args, **kwargs):
        text = text or ''
        file_intercept = False
        # If the element is input type file, we will need to use the file detector
        if self.tag(*args, **kwargs) == 'input':
            type_attr = self.get_attribute('type', *args, **kwargs)
            if type_attr and type_attr.strip() == 'file':
                file_intercept = True
        try:
            if file_intercept:
                # If we detected a file upload field, let's use the file detector.
                self.selenium.file_detector = LocalFileDetector()
            self.move_to_element(*args, **kwargs).send_keys(text)
        finally:
            # Always the UselessFileDetector for all other kinds of fields, so do not leave
            # the LocalFileDetector there.
            if file_intercept:
                self.selenium.file_detector = UselessFileDetector()

    # So on ...
