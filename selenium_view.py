# -*- coding: utf-8 -*-
import inspect
import time
from textwrap import dedent
from threading import Lock

from selenium.common.exceptions import (
    NoSuchElementException, MoveTargetOutOfBoundsException, StaleElementReferenceException,
    NoAlertPresentException, UnexpectedAlertPresentException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.file_detector import LocalFileDetector, UselessFileDetector
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from smartloc import Locator

from xml.sax.saxutils import quoteattr

from wait_for import wait_for

# Move away
from utils.version import Version


# TODO: Resolve this issue in smartloc
# Monkey patch By
def is_valid(cls, strategy):
    return strategy in {'xpath', 'css'}

By.is_valid = classmethod(is_valid)


class LocatorNotImplemented(NotImplementedError):
    pass


class LocatorDescriptor(object):
    """This class handles instantiating and caching of the widgets on view."""
    _seq_cnt = 0
    _seq_cnt_lock = Lock()

    def __new__(cls, *args, **kwargs):
        o = super(LocatorDescriptor, cls).__new__(cls)
        with LocatorDescriptor._seq_cnt_lock:
            o._seq_id = LocatorDescriptor._seq_cnt
            LocatorDescriptor._seq_cnt += 1
        return o

    def __init__(self, klass, *args, **kwargs):
        self.klass = klass
        self.args = args
        self.kwargs = kwargs

    def __get__(self, obj, type=None):
        if obj is None:  # class access
            return self

        # Cache on LocatorDescriptor
        if self not in obj._widget_cache:
            obj._widget_cache[self] = self.klass(obj, *self.args, **self.kwargs)
        return obj._widget_cache[self]

    def __repr__(self):
        if self.args:
            args = ', ' + ', '.join(repr(arg) for arg in self.args)
        else:
            args = ''
        if self.kwargs:
            kwargs = ', ' + ', '.join(
                '{}={}'.format(k, repr(v)) for k, v in self.kwargs.iteritems())
        else:
            kwargs = ''
        return '{}({}{}{})'.format(type(self).__name__, self.klass.__name__, args, kwargs)


class Browser(object):
    """Equivalent of pytest_selenium - browser functions.

    This class contains methods that wrap the default selenium functionality in a convenient way,
    mitigating known issues and generally improving the developer experience.

    Subclass it if you want to present more informations (like product version) to the widgets.
    """
    def __init__(self, selenium, plugin_class=None):
        self.selenium = selenium
        plugin_class = plugin_class or DefaultPlugin
        self.plugin = plugin_class(self)

    @property
    def browser(self):
        return self

    @property
    def product_version(self):
        raise NotImplementedError('You have to implement product_version')

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

    def elements(self, locator, parent=None, check_visibility=False):
        self.plugin.ensure_page_safe()
        locator = self._process_locator(locator)
        # Get result
        if isinstance(locator, WebElement):
            result = [locator]
        else:
            # Get the direct parent object
            if parent:
                root_element = self.elements(parent)
            else:
                root_element = self.selenium
            result = root_element.find_elements(*locator)

        if check_visibility:
            result = filter(self.is_displayed, result)

        return result

    def element(self, locator, *args, **kwargs):
        try:
            elements = self.elements(locator, *args, **kwargs)
            if len(elements) > 1:
                visible_elements = filter(self.is_displayed, elements)
                if visible_elements:
                    return visible_elements[0]
                else:
                    return elements[0]
            else:
                return elements[0]
        except IndexError:
            raise NoSuchElementException('Could not find an element {}'.format(repr(locator)))

    def perform_click(self):
        ActionChains(self.selenium).click().perform()

    def click(self, *args, **kwargs):
        self.move_to_element(*args, **kwargs)
        # and then click on current mouse position
        self.perform_click()
        try:
            self.plugin.ensure_page_safe()
        except UnexpectedAlertPresentException:
            pass

    def is_displayed(self, locator, *args, **kwargs):
        kwargs['check_visibility'] = False
        retry = True
        tries = 10
        while retry:
            retry = False
            try:
                return self.move_to_element(locator, *args, **kwargs).is_displayed()
            except (NoSuchElementException, MoveTargetOutOfBoundsException):
                return False
            except StaleElementReferenceException:
                if isinstance(locator, WebElement) or tries <= 0:
                    # We cannot fix this one.
                    raise
                retry = True
                tries -= 1
                time.sleep(0.1)

        # Just in case
        return False

    def move_to_element(self, locator, *args, **kwargs):
        el = self.element(locator, *args, **kwargs)
        if el.tag_name == "option":
            # Instead of option, let's move on its parent <select> if possible
            parent = self.element("..", parents=[el])
            if parent.tag_name == "select":
                self.move_to_element(parent)
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

    def text(self, *args, **kwargs):
        return self.element(*args, **kwargs).text

    def get_attribute(self, attr, *args, **kwargs):
        return self.element(*args, **kwargs).get_attribute(attr)

    def set_attribute(self, attr, value, *args, **kwargs):
        return self.execute_script(
            "arguments[0].setAttribute(arguments[1], arguments[2]);",
            self.element(*args, **kwargs), attr, value)

    def clear(self, *args, **kwargs):
        return self.element(*args, **kwargs).clear()

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

    def get_alert(self):
        return self.selenium.switch_to_alert()

    def is_alert_present(self):
        try:
            self.get_alert().text
        except NoAlertPresentException:
            return False
        else:
            return True

    def dismiss_any_alerts(self):
        """Loops until there are no further alerts present to dismiss.

        Useful for handling the cases where the alert pops up multiple times.
        """
        try:
            while self.is_alert_present():
                alert = self.get_alert()
                alert.dismiss()
        except NoAlertPresentException:  # Just in case. is_alert_present should be reliable
            pass

    def handle_alert(self, cancel=False, wait=30.0, squash=False, prompt=None, check_present=False):
        """Handles an alert popup.

        Args:
            cancel: Whether or not to cancel the alert.
                Accepts the Alert (False) by default.
            wait: Time to wait for an alert to appear.
                Default 30 seconds, can be set to 0 to disable waiting.
            squash: Whether or not to squash errors during alert handling.
                Default False
            prompt: If the alert is a prompt, specify the keys to type in here
            check_present: Does not squash
                :py:class:`selenium.common.exceptions.NoAlertPresentException`

        Returns:
            True if the alert was handled, False if exceptions were
            squashed, None if there was no alert.

        No exceptions will be raised if ``squash`` is True and ``check_present`` is False.

        Raises:
            utils.wait.TimedOutError: If the alert popup does not appear
            selenium.common.exceptions.NoAlertPresentException: If no alert is present when
                accepting or dismissing the alert.

        """
        # throws timeout exception if not found
        try:
            if wait:
                WebDriverWait(self.selenium, wait).until(expected_conditions.alert_is_present())
            popup = self.get_alert()
            if prompt is not None:
                popup.send_keys(prompt)
            popup.dismiss() if cancel else popup.accept()
            # Should any problematic "double" alerts appear here, we don't care, just blow'em away.
            self.dismiss_any_alerts()
            return True
        except NoAlertPresentException:
            if check_present:
                raise
            else:
                return None
        except Exception:
            if squash:
                return False
            else:
                raise

    # So on ...


class Widget(object):
    """Base class for all UI objects.

    Does couple of things:
    * Ensures it gets instantiated with a browser or another widget as parent. If you create an
      instance in a class, it then creates a LocatorDescriptor which is then invoked on the instance
      and instantiates the widget with underlying browser.
    * Implements some basic interface for all widgets.
    """

    def __new__(cls, *args, **kwargs):
        """Implement some typing saving magic.

        Unless you are passing a Widget or Browser as a first argument which implies the
        instantiation of an actual widget, it will return LocatorDescriptor instead which will
        resolve automatically inside of View instance.
        """
        if args and isinstance(args[0], (Widget, Browser)):
            return super(Widget, cls).__new__(cls, *args, **kwargs)
        else:
            return LocatorDescriptor(cls, *args, **kwargs)

    def __init__(self, parent):
        self.parent = parent

    @property
    def browser(self):
        try:
            return self.parent.browser
        except AttributeError:
            raise ValueError('Unknown value {} specified as parent.'.format(repr(self.parent)))

    @property
    def parent_view(self):
        if isinstance(self.parent, View):
            return self.parent
        else:
            return None

    @property
    def is_displayed(self):
        return self.browser.is_displayed(self)

    def wait_displayed(self):
        wait_for(lambda: self.is_displayed, timeout='15s', delay=0.2)

    def move_to(self):
        return self.browser.move_to_element(self)

    def fill(self):
        """Interactive objects like inputs, selects, checkboxes, et cetera should implement fill.

        Returns:
            A boolean whether it changed the value or not.
        """
        raise NotImplementedError(
            'Widget {} does not implement fill()!'.format(type(self).__name__))

    def read(self):
        """Each object should implement read so it is easy to get the value of such object."""
        raise NotImplementedError(
            'Widget {} does not implement read()!'.format(type(self).__name__))

    def __element__(self):
        """Default functionality, resolves :py:meth:`__locator__`."""
        try:
            return self.browser.element(self)
        except AttributeError:
            raise LocatorNotImplemented('You have to implement __locator__ or __element__')


def _gen_locator_meth(loc):
    def __locator__(self):  # noqa
        return loc
    return __locator__


class ViewMetaclass(type):
    """metaclass that ensures nested widgets' functionality from the declaration point of view."""
    def __new__(cls, name, bases, attrs):
        new_attrs = {}
        for key, value in attrs.iteritems():
            if inspect.isclass(value) and getattr(value, '__metaclass__', None) is cls:
                new_attrs[key] = LocatorDescriptor(value)
            else:
                new_attrs[key] = value
        if 'ROOT' in new_attrs:
            # For handling the root locator of the View
            rl = Locator(new_attrs['ROOT'])
            new_attrs['__locator__'] = _gen_locator_meth(rl)
        return super(ViewMetaclass, cls).__new__(cls, name, bases, new_attrs)


class View(Widget):
    """View is a kind of abstract widget that can hold another widgets. Remembers the order,
    so therefore it can function like a form with defined filling order.
    """
    __metaclass__ = ViewMetaclass

    def __init__(self, parent, additional_context=None):
        super(View, self).__init__(parent)
        self.context = additional_context or {}
        self._widget_cache = {}

    def flush_widget_cache(self):
        # Recursively ...
        for view in self._views:
            view._widget_cache.clear()
        self._widget_cache.clear()

    @classmethod
    def widget_names(cls):
        result = []
        for key in dir(cls):
            value = getattr(cls, key)
            if isinstance(value, LocatorDescriptor):
                result.append((key, value))
        return [name for name, _ in sorted(result, key=lambda pair: pair[1]._seq_id)]

    @property
    def _views(self):
        return [view for view in self if isinstance(view, View)]

    @property
    def is_displayed(self):
        try:
            return super(View, self).is_displayed
        except LocatorNotImplemented:
            return True

    def move_to(self):
        try:
            return super(View, self).move_to()
        except LocatorNotImplemented:
            return None

    def fill(self, values):
        widget_names = self.widget_names()
        was_change = False
        for name, value in values.iteritems():
            if name not in widget_names:
                raise NameError('View {} does not have widget {}'.format(type(self).__name__, name))
            if value is None:
                continue

            widget = getattr(self, name)
            if widget.fill(value):
                was_change = True

        self.after_fill(was_change)
        return was_change

    def read(self):
        result = {}
        for widget_name in self.widget_names():
            widget = getattr(self, widget_name)
            try:
                value = widget.read()
            except (NotImplementedError, NoSuchElementException):
                continue

            result[widget_name] = value

        return result

    def after_fill(self, was_change):
        pass

    def __iter__(self):
        for widget_attr in self.widget_names():
            yield getattr(self, widget_attr)


class VersionPick(object):
    """A class that implements the version picking functionality.

    Basic usage is a descriptor in which you place instances of VersionPick in a view. Whenever is
    this instance accessed from an instance, it automatically picks the correct variant based on
    product_version defined in the Browser.

    You can also use this separately using hte .pick() method.
    """
    def __init__(self, version_dict):
        self.version_dict = version_dict

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, repr(self.version_dict))

    def pick(self, version):
        # convert keys to Versions
        v_dict = {Version(k): v for (k, v) in self.version_dict.items()}
        versions = v_dict.keys()
        sorted_matching_versions = sorted(filter(lambda v: v <= version, versions),
                                          reverse=True)
        return v_dict.get(sorted_matching_versions[0]) if sorted_matching_versions else None

    def __get__(self, o, type=None):
        if o is None:
            # On a class, therefore not resolving
            return self

        result = self.pick(o.browser.product_version)
        if isinstance(result, LocatorDescriptor):
            # Resolve it instead of the class
            return result.__get__(o)
        else:
            return result


class Input(Widget):
    """Class designed to handle things about ``<input>`` tags that have name attr in one place.

    Also applies on ``textarea``, which is basically input with multiple lines (if it has name).

    Args:
        *names: Possible values (or) of the ``name`` attribute.

    Keywords:
        use_id: Whether to use ``id`` instead of ``name``. Useful if there is some input that does
            not have ``name`` attribute present.
    """
    def __init__(self, parent, *names, **kwargs):
        super(Input, self).__init__(parent)
        self._names = names
        self._use_id = kwargs.pop("use_id", False)

    @property
    def names(self):
        if len(self._names) == 1:
            return (self._names[0], )
        else:
            return self._names

    def _generate_attr(self, name):
        return "@{}={}".format("id" if self._use_id else "name", quoteattr(name))

    def __locator__(self):
        # If the end of the locator is changed, modify also the choice in Radio!!!
        return '//*[(self::input or self::textarea) and ({})]'.format(
            " or ".join(self._generate_attr(name) for name in self.names)
        )

    @property
    def angular_help_block(self):
        """Returns the angular helper text (like 'Required')."""
        loc = "{}/following-sibling::span".format(self.locate())
        if self.browser.is_displayed(loc):
            return self.browser.text(loc).strip()
        else:
            return None

    def read(self):
        return self.browser.get_attribute('value', self)

    def fill(self, text):
        text = text or ''
        old_text = self.read()
        if old_text == text:
            return False
        self.browser.clear(self)
        self.browser.send_keys(text, self)
        return True

    def __add__(self, string):
        return Locator(self.__locator__() + string)

    def __radd__(self, string):
        return Locator(string + self.__locator__())


class Checkbox(Widget):
    def __init__(self, parent, *names, **kwargs):
        super(Checkbox, self).__init__(parent)
        self._names = names
        self._use_id = kwargs.pop("use_id", False)

    @property
    def names(self):
        if len(self._names) == 1:
            return (self._names[0], )
        else:
            return self._names

    def _generate_attr(self, name):
        return "@{}={}".format("id" if self._use_id else "name", quoteattr(name))

    def __locator__(self):
        # If the end of the locator is changed, modify also the choice in Radio!!!
        return '//input[@type="checkbox" and ({})]'.format(
            " or ".join(self._generate_attr(name) for name in self.names)
        )

    def read(self):
        return self.browser.get_attribute(self, 'checked') == 'true'

    def fill(self, value):
        if (value and not self.read()) or (not value and self.read()):
            self.browser.click(self)
            return True
        else:
            return False


class Clickable(object):
    def click(self, **kwargs):
        self.browser.click(self, **kwargs)

    def __call__(self):
        """Convenience function to allow view.widget() do click."""
        return self.click()


class Button(Widget, Clickable):
    ALLOWED_ATTRS = {'title', 'alt'}

    def __init__(self, parent, *text, **by_attr):
        Widget.__init__(self, parent)
        if text:
            if len(text) > 1:
                raise TypeError('For text based buttons you can only pass one param')
            else:
                self.text = text[0]
        else:
            self.text = None
            self.attr = None
            for attr, value in by_attr.iteritems():
                if attr not in self.ALLOWED_ATTRS:
                    raise NameError('Attribute {} is not allowed for buttons'.format(attr))
                if self.attr:
                    raise ValueError('You are specifying multiple attributes to match')
                self.attr = (attr, value)

    def fill(self, value):
        if value:
            self.click()
        return value

    def __locator__(self):
        if self.text is not None:
            return (
                '(//a | //button)[contains(@class, "btn") and normalize-space(.)={}]'.format(
                    quoteattr(self.text)))
        else:
            return (
                '(//a | //button)[contains(@class, "btn") and @{}={}]'.format(
                    self.attr[0], quoteattr(self.attr[1])))


class Text(Widget, Clickable):
    def __init__(self, parent, locator):
        super(Text, self).__init__(parent)
        self.locator = locator

    def __locator__(self):
        return self.locator

    def read(self):
        return self.browser.text(self)


class AttributeValue(Widget):
    def __init__(self, parent, locator, attribute):
        super(AttributeValue, self).__init__(parent)
        self.locator = locator
        self.attribute = attribute

    def __locator__(self):
        return self.locator

    def fill(self, value):
        current = self.read()
        if current != value:
            self.browser.set_attribute(self.attribute, value, self)
            return True
        else:
            return False

    def read(self):
        return self.browser.get_attribute(self.attribute, self)


class DefaultPlugin(object):
    ENSURE_PAGE_SAFE = '''\
        return {
            jquery: (typeof jQuery === "undefined") ? true : jQuery.active < 1,
            prototype: (typeof Ajax === "undefined") ? true : Ajax.activeRequestCount < 1,
            document: document.readyState == "complete"
        }
        '''

    def __init__(self, browser):
        self.browser = browser

    def ensure_page_safe(self, timeout='10s'):
        # THIS ONE SHOULD ALWAYS USE JAVASCRIPT ONLY, NO OTHER SELENIUM INTERACTION
        self.browser.dismiss_any_alerts()

        def _check():
            result = self.browser.execute_script(self.ENSURE_PAGE_SAFE)
            # TODO: Logging
            try:
                return all(result.values())
            except AttributeError:
                return True

        wait_for(_check, timeout=timeout, delay=0.2)
