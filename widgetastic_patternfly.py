# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import ClickableMixin, TextInput, Widget, View
from widgetastic.xpath import quote

from wait_for import wait_for_decorator


class Button(Widget, ClickableMixin):
    """A PatternFly/Bootstrap button

    .. code-block:: python

        Button('Text of button (unless it is an input ...)')
        Button('contains', 'Text of button (unless it is an input ...)')
        Button(title='Show xyz')  # And such
        assert button.active
        assert not button.disabled
    """

    def __init__(self, parent, *text, **kwargs):
        logger = kwargs.pop('logger', None)
        Widget.__init__(self, parent, logger=logger)
        if text:
            if kwargs:
                raise TypeError('If you pass button text then do not pass anything else.')
            if len(text) == 1:
                self.locator_conditions = 'normalize-space(.)={}'.format(quote(text[0]))
            elif len(text) == 2 and text[0].lower() == 'contains':
                self.locator_conditions = 'contains(normalize-space(.), {})'.format(quote(text[1]))
            else:
                raise TypeError('An illegal combination of text params')
        else:
            # Join the kwargs
            self.locator_conditions = ' and '.join(
                '@{}={}'.format(attr, quote(value)) for attr, value in kwargs.items())

    # TODO: Handle input value the same way as text for other tags
    def __locator__(self):
        return (
            './/*[(self::a or self::button or (self::input and (@type="button" or @type="submit")))'
            ' and contains(@class, "btn") and ({})]'.format(self.locator_conditions))

    @property
    def active(self):
        return 'active' in self.browser.classes(self)

    @property
    def disabled(self):
        return self.browser.get_attribute('disabled', self) == 'disabled'


class Input(TextInput):
    """Patternfly input

    Has some additional methods.
    """
    @property
    def help_block(self):
        e = self.browser.element(self)
        try:
            help_block = self.browser.element('./following-sibling::span', parent=e)
        except NoSuchElementException:
            return None
        else:
            return self.browser.text(help_block)


class FlashMessages(Widget):
    """Represents the block of flash messages."""
    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.locator = locator

    def __locator__(self):
        return self.locator

    def read(self):
        result = []
        for message in self.messages:
            result.append(message.read())
        return result

    @property
    def messages(self):
        result = []
        try:
            for flash_div in self.browser.elements(
                    './div[contains(@class, "alert")]', parent=self, check_visibility=True):
                result.append(FlashMessage(self, flash_div, logger=self.logger))
        except NoSuchElementException:
            pass
        return result

    def dismiss(self):
        for message in self.messages:
            message.dismiss()

    def assert_no_error(self):
        for message in self.messages:
            if message.type not in {'success', 'info'}:
                raise AssertionError('assert_no_error: {}: {}'.format(message.type, message.text))

    def assert_message(self, text, t=None):
        for message in self.messages:
            if message.text == text:
                if t is not None:
                    if message.type == t:
                        return True
                else:
                    return True
        else:
            if t is not None:
                e_text = '{}: {}'.format(t, text)
            else:
                e_text = text
            raise AssertionError('assert_message: {}'.format(e_text))


class FlashMessage(Widget):
    """Not to be instantiated on View"""

    TYPE_MAPPING = {
        "alert-warning": "warning",
        "alert-success": "success",
        "alert-danger": "error",
        "alert-info": "info"
    }

    def __init__(self, parent, flash_div, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.flash_div = flash_div

    def __locator__(self):
        return self.flash_div

    def read(self):
        return self.text

    @property
    def text(self):
        return self.browser.text('./strong', parent=self)

    def dismiss(self):
        self.logger.info('dismissed %r', self.text)
        return self.browser.click('./button[contains(@class, "close")]', parent=self)

    @property
    def icon(self):
        try:
            e = self.browser.element('./span[contains(@class, "pficon")]', parent=self)
        except NoSuchElementException:
            return None
        for class_ in self.browser.classes(e):
            if class_.startswith('pficon-'):
                return class_[7:]
        else:
            return None

    @property
    def type(self):
        for class_ in self.browser.classes(self):
            if class_ in self.TYPE_MAPPING:
                return self.TYPE_MAPPING[class_]
        else:
            raise ValueError(
                'Could not find a proper alert type. Available classes: {!r} Alert has: {!r}'
                .format(self.TYPE_MAPPING, self.browser.classes(self)))


class NavDropdown(Widget, ClickableMixin):
    """The dropdowns used eg. in navigation. Usually located in the top navbar."""

    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.locator = locator

    def __locator__(self):
        return self.locator

    def read(self):
        return self.text

    @property
    def expandable(self):
        try:
            self.browser.element('./a/span[contains(@class, "caret")]', parent=self)
        except NoSuchElementException:
            return False
        else:
            return True

    @property
    def expanded(self):
        if not self.expandable:
            return False
        return 'open' in self.browser.classes(self)

    @property
    def collapsed(self):
        return not self.expanded

    def expand(self):
        if not self.expandable:
            raise ValueError('{} is not expandable'.format(self.locator))
        if not self.expanded:
            self.click()
            if not self.expanded:
                raise Exception('Could not expand {}'.format(self.locator))
            else:
                self.logger.info('expanded')

    def collapse(self):
        if not self.expandable:
            return
        if self.expanded:
            self.click()
            if self.expanded:
                raise Exception('Could not collapse {}'.format(self.locator))
            else:
                self.logger.info('collapsed')

    @property
    def text(self):
        try:
            return self.browser.text('./a/p', parent=self)
        except NoSuchElementException:
            return None

    @property
    def icon(self):
        try:
            el = self.browser.element('./a/span[contains(@class, "pficon")]', parent=self)
            for class_ in self.browser.classes(el):
                if class_.startswith('pficon-'):
                    return class_[7:]
            else:
                return None
        except NoSuchElementException:
            return None

    @property
    def items(self):
        return [
            self.browser.text(element)
            for element
            in self.browser.elements('./ul/li[not(contains(@class, "divider"))]', parent=self)]

    def has_item(self, item):
        return item in self.items

    def item_enabled(self, item):
        if not self.has_item(item):
            raise ValueError('There is not such item {}'.format(item))
        element = self.browser.element(
            './ul/li[normalize-space(.)={}]'.format(quote(item)), parent=self)
        return 'disabled' not in self.browser.classes(element)

    def select_item(self, item):
        if not self.item_enabled(item):
            raise ValueError('Cannot click disabled item {}'.format(item))

        self.expand()
        self.logger.info('selecting item {}'.format(item))
        self.browser.click('./ul/li[normalize-space(.)={}]'.format(quote(item)), parent=self)


class VerticalNavigation(Widget):
    """The Patternfly Vertical navigation."""
    CURRENTLY_SELECTED = './/li[contains(@class, "active")]/a'
    LINKS = './li/a'
    ITEMS_MATCHING = './li[a[normalize-space(.)={}]]'
    DIV_LINKS_MATCHING = './ul/li/a[span[normalize-space(.)={}]]'
    SUB_LEVEL = './following-sibling::div[contains(@class, "nav-pf-")]'
    SUB_ITEM_LIST = './div[contains(@class, "nav-pf-")]/ul'
    CHILD_UL_FOR_DIV = './li[a[normalize-space(.)={}]]/div[contains(@class, "nav-pf-")]/ul'
    MATCHING_LI_FOR_DIV = './ul/li[a[span[normalize-space(.)={}]]]'

    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.locator = locator

    def __locator__(self):
        return self.locator

    def read(self):
        return self.currently_selected

    def nav_links(self, *levels):
        if not levels:
            return [self.browser.text(el) for el in self.browser.elements(self.LINKS, parent=self)]
        # Otherwise
        current_item = self
        for i, level in enumerate(levels):
            li = self.browser.element(
                self.ITEMS_MATCHING.format(quote(level)),
                parent=current_item)

            try:
                current_item = self.browser.element(self.SUB_ITEM_LIST, parent=li)
            except NoSuchElementException:
                if i == len(levels) - 1:
                    # It is the last one
                    return []
                else:
                    raise

        return [
            self.browser.text(el) for el in self.browser.elements(self.LINKS, parent=current_item)]

    def nav_item_tree(self, start=None):
        start = start or []
        result = {}
        for item in self.nav_links(*start):
            sub_items = self.nav_item_tree(start=start + [item])
            result[item] = sub_items or None
        if result and all(value is None for value in result.values()):
            # If there are no child nodes, then just make it a list
            result = list(six.iterkeys(result))
        return result

    @property
    def currently_selected(self):
        return [
            self.browser.text(el)
            for el
            in self.browser.elements(self.CURRENTLY_SELECTED, parent=self)]

    def select(self, *levels, **kwargs):
        levels = list(levels)
        self.logger.info('Selecting %r in navigation', levels)
        anyway = kwargs.pop('anyway', True)
        if levels == self.currently_selected and not anyway:
            return

        passed_levels = []
        current_div = self.get_child_div_for(*passed_levels)
        for level in levels:
            passed_levels.append(level)
            finished = passed_levels == levels
            link = self.browser.element(
                self.DIV_LINKS_MATCHING.format(quote(level)), parent=current_div)
            expands = bool(
                self.browser.elements(self.SUB_LEVEL, parent=link))
            if expands and not finished:
                self.logger.debug('moving to %s to open the next level', level)
                self.browser.move_to_element(link)

                @wait_for_decorator(timeout='10s', delay=0.2)
                def other_div_displayed():
                    return 'is-hover' in self.browser.classes(
                        self.MATCHING_LI_FOR_DIV.format(quote(level)),
                        parent=current_div)

                # The other child div should be displayed
                current_div_width = current_div.size['width']
                new_div = self.get_child_div_for(*passed_levels)
                # We need to generate a correct stroke to a neighbouring div
                new_div_width = new_div.size['width']
                mouse_stroke_x = (current_div_width / 2) + (new_div_width / 2)
                self.logger.debug('moving mouse by %d px right to the next level', mouse_stroke_x)
                self.browser.move_by_offset(mouse_stroke_x, 0)
                current_div = new_div
            elif not expands and not finished:
                raise ValueError(
                    'You are trying to expand {!r} which cannot be expanded'.format(passed_levels))
            else:
                # finished
                self.logger.debug('finishing the menu selection by clicking on %s', level)
                self.browser.click(link)

    def get_child_div_for(self, *levels):
        current = self
        for level in levels:
            try:
                current = self.browser.element(
                    self.CHILD_UL_FOR_DIV.format(quote(level)),
                    parent=current)
            except NoSuchElementException:
                return None

        return self.browser.element('..', parent=current)


class Tab(View):
    """Represents the Tab widget."""
    TAB_NAME = None
    SAFE_NAMES = {'element', 'is_active', 'select', 'TAB_NAME'}

    def element(self):
        return self.browser.element(
            './li[normalize-space(.)={}]'.format(quote(self.TAB_NAME)),
            parent=self)

    def is_active(self):
        return 'active' in self.browser.classes(self.element())

    def select(self):
        if not self.is_active():
            self.logger.info('opened the tab %s', self.TAB_NAME)
            self.browser.click(self.element())

    def read(self):
        self.select()
        return super(Tab, self).read()

    def fill(self, value):
        self.select()
        return super(Tab, self).fill(value)


class BootstrapSelect(Widget, ClickableMixin):
    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.locator = locator

    def __locator__(self):
        return self.browser.element('..', parent=self.locator)

    @property
    def is_open(self):
        return 'open' in self.browser.classes(self)

    def open(self):
        if not self.is_open:
            self.logger.debug('opened')
            self.click()

    def close(self):
        if self.is_open:
            self.logger.debug('closed')
            self.click()

    def select_by_visible_text(self, text):
        self.open()
        self.logger.info('selecting by visible text: %r', text)
        self.browser.click(
            './div/ul/li/a[./span[contains(@class, "text") and normalize-space(.)={}]]'.format(
                quote(text)),
            parent=self)

    @property
    def selected_option(self):
        return self.browser.text('./button/span[contains(@class, "filter-option")]', parent=self)

    def read(self):
        return self.selected_option

    def fill(self, text):
        if self.selected_option == text:
            return False
        else:
            self.select_by_visible_text(text)
            return True
