# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import six
import time
from cached_property import cached_property

from widgetastic.exceptions import NoSuchElementException, UnexpectedAlertPresentException
from widgetastic.widget import ClickableMixin, TextInput, Widget, View, do_not_read_this_widget
from widgetastic.xpath import quote

from wait_for import wait_for, wait_for_decorator


class CandidateNotFound(Exception):
    """
    Raised if there is no candidate found whilst trying to traverse a tree in
    :py:meth:`cfme.web_ui.Tree.click_path`.
    """
    def __init__(self, d):
        self.d = d

    @property
    def message(self):
        return ", ".join("{}: {}".format(k, v) for k, v in six.iteritems(self.d))

    def __str__(self):
        return self.message


class DropdownDisabled(Exception):
    pass


class DropdownItemDisabled(Exception):
    pass


class Button(Widget, ClickableMixin):
    """A PatternFly/Bootstrap button

    .. code-block:: python

        Button('Text of button (unless it is an input ...)')
        Button('contains', 'Text of button (unless it is an input ...)')
        Button(title='Show xyz')  # And such
        assert button.active
        assert not button.disabled
    """
    CHECK_VISIBILITY = True

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
        self.logger.info('asserting there are no error messages')
        for message in self.messages:
            if message.type not in {'success', 'info'}:
                self.logger.error('%s: %r', message.type, message.text)
                raise AssertionError('assert_no_error: {}: {}'.format(message.type, message.text))
            else:
                self.logger.info('%s: %r', message.type, message.text)

    def assert_message(self, text, t=None):
        if t is not None:
            self.logger.info('asserting the message %r of type %r is present', text, t)
        else:
            self.logger.info('asserting the message %r is present', text)
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
        """Select an item in the navigation.

        Args:
            *levels: Items to be clicked in the navigation.

        Keywords:
            anyway: Default behaviour is that if you try selecting an already selected item, it will
                not do it. If you pass ``anyway=True``, it will click it anyway.
        """
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
    """Represents the Tab widget.

    Selects itself automatically when any child widget gets accessed, ensuring that the widget is
    visible.
    """
    TAB_NAME = None

    @property
    def tab_name(self):
        return self.TAB_NAME or type(self).__name__.capitalize()

    def element(self):
        return self.browser.element(
            './li[normalize-space(.)={}]'.format(quote(self.tab_name)),
            parent=self)

    def is_active(self):
        return 'active' in self.browser.classes(self.element())

    def select(self):
        if not self.is_active():
            self.logger.info('opened the tab %s', self.tab_name)
            self.browser.click(self.element())

    def child_widget_accessed(self, widget):
        # Select the tab
        self.select()


class Accordion(View, ClickableMixin):
    """Bootstrap/Patternfly accordions.

    They are like views that contain widgets. If a widget is accessed in the accordion, the
    accordion makes sure that it is open.

    You need to set the ACCORDION_NAME to correspond with teh text in the accordion.

    If the accordion is in an exotic location, you also have to change the ROOT_LOCATOR. Bear in
    mind that the A_LOCATOR is joined immediately behind that locator.

    Accordions can contain trees. Basic TREE_LOCATOR is tuned after ManageIQ so if your UI has a
    different structure, you should change this locator accordingly.
    """
    ACCORDION_NAME = None
    ROOT_LOCATOR = './/div[contains(@class, "panel-group") and ./div[contains(@class, "panel")]]'
    A_LOCATOR = '/div/div/h4/a[normalize-space(text())={}]'
    TREE_LOCATOR = '|'.join([
        '../../..//div[contains(@class, "treeview") and ./ul]',
        '../../..//div[./ul[contains(@class, "dynatree-container")]]'])

    @property
    def accordion_name(self):
        return self.ACCORDION_NAME or type(self).__name__.capitalize()

    def __locator__(self):
        return self.ROOT_LOCATOR + self.A_LOCATOR.format(quote(self.accordion_name))

    @property
    def is_opened(self):
        attr = self.browser.get_attribute('aria-expanded', self)
        if attr is None:
            # Try other way
            panel = self.browser.element(
                '../../../div[contains(@class, "panel-collapse")]', parent=self)
            classes = self.browser.classes(panel)
            return 'collapse' in classes and 'in' in classes
        else:
            return attr.lower().strip() == 'true'

    @property
    def is_closed(self):
        attr = self.browser.get_attribute('aria-expanded', self)
        return attr is None or attr.lower().strip() == 'false'

    def open(self):
        if self.is_closed:
            self.logger.info('opening')
            self.click()

    def close(self):
        if self.is_open:
            self.click()

    def child_widget_accessed(self, widget):
        # Open the Accordion
        self.open()

    def read(self):
        if self.is_closed:
            do_not_read_this_widget()
        return super(Accordion, self).read()

    @cached_property
    def tree_id(self):
        try:
            div = self.browser.element(self.TREE_LOCATOR, parent=self)
        except NoSuchElementException:
            raise AttributeError('No tree in the accordion')
        else:
            return self.browser.get_attribute('id', div)


class BootstrapSelect(Widget, ClickableMixin):
    """This class represents the Bootstrap Select widget.

    Args:
        id: id of the select, that is the ``data-id`` attribute on the ``button`` tag.
    """
    def __init__(self, parent, id, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.id = id

    def __locator__(self):
        return self.browser.element(
            './/button[normalize-space(@data-id)={}]/..'.format(quote(self.id)))

    @property
    def is_open(self):
        return 'open' in self.browser.classes(self)

    @property
    def is_multiple(self):
        return 'show-tick' in self.browser.classes(self)

    def open(self):
        if not self.is_open:
            self.logger.debug('opened')
            self.click()

    def close(self):
        if self.is_open:
            self.logger.debug('closed')
            self.click()

    def select_by_visible_text(self, *items):
        """Selects items in the select.

        Args:
            *items: Items to be selected. If the select does not support multiple selections and you
                pass more than one item, it will raise an exception.
        """
        if len(items) > 1 and not self.is_multiple:
            raise ValueError(
                'The BootstrapSelect {} does not allow multiple selections'.format(self.id))
        self.open()
        for text in items:
            self.logger.info('selecting by visible text: %r', text)
            self.browser.click(
                './div/ul/li/a[./span[contains(@class, "text") and normalize-space(.)={}]]'.format(
                    quote(text)),
                parent=self)
        self.close()

    @property
    def all_selected_options(self):
        return [
            self.browser.text(e)
            for e in self.browser.elements(
                './div/ul/li[contains(@class, "selected")]/a/span[contains(@class, "text")]',
                parent=self)]

    @property
    def selected_option(self):
        return self.all_selected_options[0]

    def read(self):
        if self.is_multiple:
            return self.all_selected_options
        else:
            return self.selected_option

    def fill(self, items):
        if not isinstance(items, (list, tuple, set)):
            items = {items}
        elif not isinstance(items, set):
            items = set(items)

        if set(self.all_selected_options) == items:
            return False
        else:
            self.select_by_visible_text(*items)
            return True


class BootstrapTreeview(Widget):
    """A class representing the Bootstrap treeview used in newer builds.

    Implements ``expand_path``, ``click_path``, ``read_contents``. All are implemented in manner
    very similar to the original :py:class:`Tree`.

    You don't have to specify the ``tree_id`` if the hosting object implements ``tree_id``.

    Args:
        tree_id: Id of the tree, the closest div to the root ``ul`` element.
    """
    ROOT_ITEM = './ul/li[1]'
    SELECTED_ITEM = './ul/li[contains(@class, "node-selected")]'
    CHILD_ITEMS = (
        './ul/li[starts-with(@data-nodeid, {id}) and not(@data-nodeid={id})'
        ' and count(./span[contains(@class, "indent")])={indent}]')
    CHILD_ITEMS_TEXT = (
        './ul/li[starts-with(@data-nodeid, {id}) and not(@data-nodeid={id})'
        ' and contains(normalize-space(text()), {text})'
        ' and count(./span[contains(@class, "indent")])={indent}]')
    ITEM_BY_NODEID = './ul/li[@data-nodeid={}]'
    IS_EXPANDABLE = './span[contains(@class, "expand-icon")]'
    IS_EXPANDED = './span[contains(@class, "expand-icon") and contains(@class, "fa-angle-down")]'
    IS_CHECKABLE = './span[contains(@class, "check-icon")]'
    IS_CHECKED = './span[contains(@class, "check-icon") and contains(@class, "fa-check-square-o")]'
    IS_LOADING = './span[contains(@class, "expand-icon") and contains(@class, "fa-spinner")]'
    INDENT = './span[contains(@class, "indent")]'

    def __init__(self, parent, tree_id=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self._tree_id = tree_id

    @property
    def tree_id(self):
        """If you did not specify the tree_id when creating the tree, it will try to pull it out of
        the parent object.

        This is useful if some kinds of objects contain trees regularly, then the definition gets
        simpler and the tree id is not neded to be specified.
        """
        if self._tree_id is not None:
            return self._tree_id
        else:
            try:
                return self.parent.tree_id
            except AttributeError:
                raise NameError(
                    'You have to specify tree_id to BootstrapTreeview if the parent object does '
                    'not implement .tree_id!')

    def image_getter(self, item):
        """Look up the image that is hidden in the style tag

        Returns:
            The name of the image without the hash, path and extension.
        """
        image_node = self.browser.element('./span[contains(@class, "node-image")]', parent=item)
        style = self.browser.get_attribute('style', image_node)
        image_href = re.search(r'url\("([^"]+)"\)', style).groups()[0]
        return re.search(r'/([^/]+)-[0-9a-f]+\.png$', image_href).groups()[0]

    def __locator__(self):
        return '#{}'.format(self.tree_id)

    def read(self):
        return self.currently_selected

    def fill(self, value):
        if self.currently_selected == value:
            return False
        self.click_path(*value)
        return True

    @property
    def currently_selected(self):
        nodeid = self.get_nodeid(self.selected_item).split('.')
        root_id_len = len(self.get_nodeid(self.root_item).split('.'))
        result = []
        for end in range(root_id_len, len(nodeid) + 1):
            current_nodeid = '.'.join(nodeid[:end])
            text = self.browser.text(self.get_item_by_nodeid(current_nodeid))
            result.append(text)
        return result

    @property
    def root_item(self):
        return self.browser.element(self.ROOT_ITEM, parent=self)

    @property
    def selected_item(self):
        return self.browser.element(self.SELECTED_ITEM, parent=self)

    def indents(self, item):
        return len(self.browser.elements(self.INDENT, parent=item))

    def is_expandable(self, item):
        return bool(self.browser.elements(self.IS_EXPANDABLE, parent=item))

    def is_expanded(self, item):
        return bool(self.browser.elements(self.IS_EXPANDED, parent=item))

    def is_checkable(self, item):
        return bool(self.browser.elements(self.IS_CHECKABLE, parent=item))

    def is_checked(self, item):
        return bool(self.browser.elements(self.IS_CHECKED, parent=item))

    def is_loading(self, item):
        return bool(self.browser.elements(self.IS_LOADING, parent=item))

    def is_collapsed(self, item):
        return not self.is_expanded(item)

    def is_selected(self, item):
        return 'node-selected' in self.browser.classes(item)

    def get_nodeid(self, item):
        return self.browser.get_attribute('data-nodeid', item)

    def get_expand_arrow(self, item):
        return self.browser.element(self.IS_EXPANDABLE, parent=item)

    def child_items(self, item):
        """Returns all child items of given item.

        Args:
            item: WebElement of the node.

        Returns:
            List of *all* child items of the item.
        """
        nodeid = quote(self.get_nodeid(item))
        node_indents = self.indents(item)
        return self.browser.elements(
            self.CHILD_ITEMS.format(id=nodeid, indent=node_indents + 1), parent=self)

    def child_items_with_text(self, item, text):
        """Returns all child items of given item that contain the given text.

        Args:
            item: WebElement of the node.
            text: Text to be matched

        Returns:
            List of all child items of the item *that contain the given text*.
        """
        nodeid = quote(self.get_nodeid(item))
        text = quote(text)
        node_indents = self.indents(item)
        return self.browser.elements(
            self.CHILD_ITEMS_TEXT.format(id=nodeid, text=text, indent=node_indents + 1),
            parent=self)

    def get_item_by_nodeid(self, nodeid):
        nodeid_q = quote(nodeid)
        try:
            return self.browser.element(self.ITEM_BY_NODEID.format(nodeid_q), parent=self)
        except NoSuchElementException:
            raise CandidateNotFound({
                'message':
                    'Could not find the item with nodeid {} in Boostrap tree {}'.format(
                        nodeid,
                        self.tree_id),
                'path': '',
                'cause': ''})

    def expand_node(self, nodeid):
        """Expands a node given its nodeid. Must be visible

        Args:
            nodeid: ``nodeId`` of the node

        Returns:
            ``True`` if it was possible to expand the node, otherwise ``False``.
        """
        self.logger.debug('Expanding node %s on tree %s', nodeid, self.tree_id)
        node = self.get_item_by_nodeid(nodeid)
        if not self.is_expandable(node):
            return False
        if self.is_collapsed(node):
            arrow = self.get_expand_arrow(node)
            self.browser.click(arrow)
            time.sleep(0.1)
            wait_for(
                lambda: not self.is_loading(self.get_item_by_nodeid(nodeid)),
                delay=0.2, num_sec=30)
            wait_for(
                lambda: self.is_expanded(self.get_item_by_nodeid(nodeid)),
                delay=0.2, num_sec=10)
        return True

    def collapse_node(self, nodeid):
        """Collapses a node given its nodeid. Must be visible

        Args:
            nodeid: ``nodeId`` of the node

        Returns:
            ``True`` if it was possible to expand the node, otherwise ``False``.
        """
        self.logger.debug('Collapsing node %s on tree %s', nodeid, self.tree_id)
        node = self.get_item_by_nodeid(nodeid)
        if not self.is_expandable(node):
            return False
        if self.is_expanded(node):
            arrow = self.get_expand_arrow(node)
            self.browser.click(arrow)
            time.sleep(0.1)
            wait_for(
                lambda: self.is_collapsed(self.get_item_by_nodeid(nodeid)),
                delay=0.2, num_sec=10)
        return True

    @staticmethod
    def _process_step(step):
        """Steps can be plain strings or tuples when matching images"""
        if isinstance(step, tuple):
            image = step[0]
            step = step[1]
        else:
            image = None
        return image, step

    @staticmethod
    def _repr_step(image, step):
        if isinstance(step, re._pattern_type):
            # Make it look like r'pattern'
            step_repr = 'r' + re.sub(r'^[^"\']', '', repr(step.pattern))
        else:
            step_repr = step
        if image is None:
            return step_repr
        else:
            return '{}[{}]'.format(step_repr, image)

    @classmethod
    def pretty_path(cls, path):
        return '/'.join(cls._repr_step(*cls._process_step(step)) for step in path)

    def validate_node(self, node, matcher, image):
        """Helper method that matches nodes by given conditions.

        Args:
            node: Node that is matched
            matcher: If it is an instance of regular expression, that one is used, otherwise
                equality comparison is used. Against item name.
            image: If not None, then after the matcher matches, this will do an additional check for
                the image name

        Returns:
            A :py:class:`bool` if the node is correct or not.
        """
        text = self.browser.text(node)
        if isinstance(matcher, re._pattern_type):
            match = matcher.match(text) is not None
        else:
            match = matcher == text
        if not match:
            return False
        if image is not None and self.image_getter(node) != image:
            return False
        return True

    def expand_path(self, *path, **kwargs):
        """Expands given path and returns the leaf node.

        The path items can be plain strings. In that case, exact string matching happens. Path items
        can also be compiled regexps, where the ``match`` method is used to determine if the node
        is the one we want. And finally, the path items can be 2-tuples, where the second item can
        be the string or regular expression and the first item is the image to be matched using
        :py:meth:`image_getter` method.

        Args:
            *path: The path (explained above)

        Returns:
            The leaf WebElement.

        Raises:
            :py:class:`exceptions.CandidateNotFound` when the node is not found in the tree.
        """
        self.browser.plugin.ensure_page_safe()
        self.logger.info('Expanding path %s on tree %s', self.pretty_path(path), self.tree_id)
        node = self.root_item
        step = path[0]
        steps_tried = [step]
        image, step = self._process_step(step)
        path = path[1:]
        if not self.validate_node(node, step, image):
            raise CandidateNotFound({
                'message':
                    'Could not find the item {} in Boostrap tree {}'.format(
                        self.pretty_path(steps_tried),
                        self.tree_id),
                'path': path,
                'cause': 'Root node did not match {}'.format(self._repr_step(image, step))})

        for step in path:
            steps_tried.append(step)
            image, step = self._process_step(step)
            if not self.expand_node(self.get_nodeid(node)):
                raise CandidateNotFound({
                    'message':
                        'Could not find the item {} in Boostrap tree {}'.format(
                            self.pretty_path(steps_tried),
                            self.tree_id),
                    'path': path,
                    'cause': 'Could not expand the {} node'.format(self._repr_step(image, step))})
            if isinstance(step, basestring):
                # To speed up the search when having a string to match, pick up items with that text
                child_items = self.child_items_with_text(node, step)
            else:
                # Otherwise we need to go through all of them.
                child_items = self.child_items(node)
            for child_item in child_items:
                if self.validate_node(child_item, step, image):
                    node = child_item
                    break
            else:
                raise CandidateNotFound({
                    'message':
                        'Could not find the item {} in Boostrap tree {}'.format(
                            self.pretty_path(steps_tried),
                            self.tree_id),
                    'path': path,
                    'cause': 'Was not found in {}'.format(
                        self._repr_step(*self._process_step(steps_tried[-2])))})

        return node

    def click_path(self, *path, **kwargs):
        """Expands the path and clicks the leaf node.

        See :py:meth:`expand_path` for more informations about synopsis.
        """
        node = self.expand_path(*path, **kwargs)
        self.logger.info('clicking node %r', path[-1])
        self.browser.click(node)
        return node

    def read_contents(self, nodeid=None, include_images=False, collapse_after_read=False):
        """Reads the contents of the tree into a tree structure of strings and lists.

        This method is called recursively.

        Args:
            nodeid: id of the node where the process should start from.
            include_images: If True, the values will be tuples where first item will be the image
                name and the second item the item name. If False then the values are just the item
                names.
            collapse_after_read: If True, then every branch that was read completely gets collapsed.

        Returns:
            :py:class:`list`
        """
        if nodeid is None:
            return self.read_contents(
                nodeid=self.get_nodeid(self.root_item),
                include_images=include_images,
                collapse_after_read=collapse_after_read)

        item = self.get_item_by_nodeid(nodeid)
        self.expand_node(nodeid)
        result = []

        for child_item in self.child_items(item):
            result.append(
                self.read_contents(
                    nodeid=self.get_nodeid(child_item),
                    include_images=include_images,
                    collapse_after_read=collapse_after_read))

        if collapse_after_read:
            self.collapse_node(nodeid)

        if include_images:
            this_item = (self.image_getter(item), self.browser.text(item))
        else:
            this_item = self.browser.text(item)
        if result:
            return [this_item, result]
        else:
            return this_item

    def check_uncheck_node(self, check, *path, **kwargs):
        leaf = self.expand_path(*path, **kwargs)
        if not self.is_checkable(leaf):
            raise TypeError('Item with path {} in {} is not checkable'.format(
                self.pretty_path(path), self.tree_id))
        checked = self.is_checked(leaf)
        if checked != check:
            self.logger.info('%s %r', 'Checking' if check else 'Unchecking', path[-1])
            self.browser.click(self.IS_CHECKABLE, parent=leaf)

    def check_node(self, *path, **kwargs):
        """Expands the passed path and checks a checkbox that is located at the node."""
        return self.check_uncheck_node(True, *path, **kwargs)

    def uncheck_node(self, *path, **kwargs):
        """Expands the passed path and unchecks a checkbox that is located at the node."""
        return self.check_uncheck_node(False, *path, **kwargs)

    def node_checked(self, *path, **kwargs):
        """Check if a checkbox is checked on the node in that path."""
        leaf = self.expand_path(*path, **kwargs)
        if not self.is_checkable(leaf):
            return False
        return self.is_checked(leaf)


class Dropdown(Widget):
    """Represents the Patternfly/Bootstrap dropdown.

    Args:
        text: Text of the button, can be the inner text or the titel attribute.
    """
    BUTTON_DIV_LOCATOR = (
        './/div[contains(@class, "dropdown") and ./button[normalize-space(.)={0} or '
        'normalize-space(@title)={0}]]')
    BUTTON_LOCATOR = './button'
    ITEMS_LOCATOR = './ul/li/a'
    ITEM_LOCATOR = './ul/li/a[normalize-space(.)={}]'

    def __init__(self, parent, text, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.text = text

    def __locator__(self):
        return self.BUTTON_DIV_LOCATOR.format(quote(self.text))

    @property
    def is_enabled(self):
        """Returns if the toolbar itself is enabled and therefore interactive."""
        button = self.browser.element(self.BUTTON_LOCATOR, parent=self)
        return 'disabled' not in self.browser.classes(button)

    def _verify_enabled(self):
        if not self.is_enabled:
            raise DropdownDisabled('Dropdown "{}" is not enabled'.format(self.text))

    @property
    def is_open(self):
        return 'open' in self.browser.classes(self)

    def open(self):
        self._verify_enabled()
        if not self.is_open:
            self.browser.click(self)

    def close(self, ignore_nonpresent=False):
        try:
            self._verify_enabled()
            if self.is_open:
                self.browser.click(self)
        except NoSuchElementException:
            if not ignore_nonpresent:
                raise

    @property
    def items(self):
        """Returns a list of all dropdown items as strings."""
        return [
            self.browser.text(el) for el in self.browser.elements(self.ITEMS_LOCATOR, parent=self)]

    def item_element(self, item):
        """Returns a WebElement for given item name."""
        return self.browser.element(self.ITEM_LOCATOR.format(quote(item)), parent=self)

    def item_enabled(self, item):
        """Returns whether the given item is enabled.

        Args:
            item: Name of the item.

        Returns:
            Boolean - True if enabled, False if not.
        """
        self._verify_enabled()
        el = self.item_element(item)
        li = self.browser.element('..', parent=el)
        return 'disabled' not in self.browser.classes(li)

    def item_select(self, item, handle_alert=None):
        """Opens the dropdown and selects the desired item.

        Args:
            item: Item to be selected
            handle_alert: How to handle alerts. None - no handling, True - confirm, False - dismiss.
        """
        self.logger.info('Selecting %r', item)
        try:
            self.open()
            if not self.item_enabled(item):
                raise DropdownItemDisabled(
                    'Item "{}" of dropdown "{}" is disabled'.format(item, self.text))
            self.browser.click(self.item_element(item), ignore_ajax=handle_alert is not None)
            if handle_alert is not None:
                self.browser.handle_alert(cancel=not handle_alert, wait=10.0)
                self.browser.plugin.ensure_page_safe()
        finally:
            try:
                self.close(ignore_nonpresent=True)
            except UnexpectedAlertPresentException:
                self.logger.warning('There is an unexpected alert present.')
                pass
