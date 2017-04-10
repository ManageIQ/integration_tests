# -*- coding: utf-8 -*-
import atexit
import re
import os
from collections import namedtuple
from datetime import date
from jsmin import jsmin
from selenium.common.exceptions import WebDriverException
from lxml.html import document_fromstring
from math import ceil
from tempfile import NamedTemporaryFile
from wait_for import wait_for

from widgetastic.exceptions import NoSuchElementException
from widgetastic.log import logged
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import (
    Table as VanillaTable,
    TableColumn as VanillaTableColumn,
    TableRow as VanillaTableRow,
    Widget,
    View,
    Select,
    TextInput,
    Text,
    Checkbox,
    ParametrizedView,
    WidgetDescriptor,
    FileInput as BaseFileInput,
    do_not_read_this_widget)
from widgetastic.utils import ParametrizedLocator, Parameter, attributize_string
from widgetastic.xpath import quote
from widgetastic_patternfly import (
    Accordion as PFAccordion, CandidateNotFound, BootstrapTreeview, Button, Input, BootstrapSelect,
    ViewChangeButton, CheckableBootstrapTreeview)
from cached_property import cached_property


class DynaTree(Widget):
    """ A class directed at CFME Tree elements

    """

    XPATH = """\
    function xpath(root, xpath) {
        if(root == null)
            root = document;
        var nt = XPathResult.ANY_UNORDERED_NODE_TYPE;
        return document.evaluate(xpath, root, null, nt, null).singleNodeValue;
    }
    """

    # This function retrieves the root of the tree. Can wait for the tree to get initialized
    TREE_GET_ROOT = """\
    function get_root(loc) {
        var start_time = new Date();
        var root = null;
        while(root === null && ((new Date()) - start_time) < 10000)
        {
            try {
                root = $(loc).dynatree("getRoot");
            } catch(err) {
                // Nothing ...
            }
        }

        return root;
    }
    """

    # This function is used to DRY the decision on which text to match
    GET_LEVEL_NAME = XPATH + """\
    function get_level_name(level, by_id) {
        if(by_id){
            return level.li.getAttribute("id");
        } else {
            var e = xpath(level.li, "./span/a");
            if(e === null)
                return null;
            else
                return e.textContent;
        }
    }
    """

    # needs xpath to work, provided by dependencies of the other functions
    EXPANDABLE = """\
    function expandable(el) {
        return xpath(el.li, "./span/span[contains(@class, 'dynatree-expander')]") !== null;
    }
    """

    # This function reads whole tree. If it faces an ajax load, it returns false.
    # If it does not return false, the result is complete.
    READ_TREE = jsmin(TREE_GET_ROOT + GET_LEVEL_NAME + EXPANDABLE + """\
    function read_tree(root, read_id, _root_tree) {
        if(read_id === undefined)
            read_id = false;
        if(_root_tree === undefined)
            _root_tree = true;
        if(_root_tree) {
            root = get_root(root);
            if(root === null)
                return null;
            if(expandable(root) && (!root.bExpanded)) {
                root.expand();
                if(root.childList === null && root.data.isLazy){
                    return false;
                }
            }
            var result = new Array();
            var need_wait = false;
            var children = (root.childList === null) ? [] : root.childList;
            for(var i = 0; i < children.length; i++) {
                var child = children[i];
                var sub = read_tree(child, read_id, false);
                if(sub === false)
                    need_wait = true;
                else
                    result.push(sub);
            }
            if(need_wait)
                return false;
            else if(children.length == 0)
                return null;
            else
                return result;
        } else {
            if(expandable(root) && (!root.bExpanded)) {
                root.expand();
                if(root.childList === null && root.data.isLazy){
                    return false;
                }
            }
            var name = get_level_name(root, read_id);

            var result = new Array();
            var need_wait = false;
            var children = (root.childList === null) ? [] : root.childList;
            for(var i = 0; i < children.length; i++) {
                var child = children[i];
                var sub = read_tree(child, read_id, false);
                if(sub === false)
                    need_wait = true;
                else
                    result.push(sub);
            }
            if(need_wait)
                return false;
            else if(children.length == 0)
                return name;
            else
                return [name, result]

        }
    }
    """)

    def __init__(self, parent, tree_id=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self._tree_id = tree_id

    @property
    def tree_id(self):
        if self._tree_id is not None:
            return self._tree_id
        else:
            try:
                return self.parent.tree_id
            except AttributeError:
                raise NameError(
                    'You have to specify tree_id to BootstrapTreeview if the parent object does '
                    'not implement .tree_id!')

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
        items = self.browser.elements(
            './/li[.//span[contains(@class, "dynatree-active")]]/span/a',
            parent=self,
            check_visibility=True)
        return map(self.browser.text, items)

    def root_el(self):
        return self.browser.element(self)

    def _get_tag(self):
        if getattr(self, 'tag', None) is None:
            self.tag = self.browser.tag(self)
        return self.tag

    def read_contents(self, by_id=False):
        result = False
        while result is False:
            self.browser.plugin.ensure_page_safe()
            result = self.browser.execute_script(
                "{} return read_tree(arguments[0], arguments[1]);".format(self.READ_TREE),
                self.__locator__(),
                by_id)
        return result

    @staticmethod
    def _construct_xpath(path, by_id=False):
        items = []
        for item in path:
            if by_id:
                items.append('ul/li[@id={}]'.format(quote(item)))
            else:
                items.append('ul/li[./span/a[normalize-space(.)={}]]'.format(quote(item)))

        return './' + '/'.join(items)

    def _item_expanded(self, id):
        span = self.browser.element('.//li[@id={}]/span'.format(quote(id)), parent=self)
        return 'dynatree-expanded' in self.browser.get_attribute('class', span)

    def _item_expandable(self, id):
        return bool(
            self.browser.elements(
                './/li[@id={}]/span/span[contains(@class, "dynatree-expander")]'.format(quote(id)),
                parent=self))

    def _click_expander(self, id):
        expander = self.browser.element(
            './/li[@id={}]/span/span[contains(@class, "dynatree-expander")]'.format(quote(id)),
            parent=self)
        return self.browser.click(expander)

    def expand_id(self, id):
        self.browser.plugin.ensure_page_safe()
        if not self._item_expanded(id) and self._item_expandable(id):
            self.logger.debug('expanding node %r', id)
            self._click_expander(id)
            wait_for(lambda: self._item_expanded(id), num_sec=15, delay=0.5)

    def child_items(self, id, ids=False):
        self.expand_id(id)
        items = self.browser.elements('.//li[@id={}]/ul/li'.format(quote(id)), parent=self)
        result = []
        for item in items:
            if ids:
                result.append(self.browser.get_attribute('id', item))
            else:
                text_item = self.browser.element('./span/a', parent=item)
                result.append(self.browser.text(text_item))
        return result

    def expand_path(self, *path, **kwargs):
        """ Exposes a path.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.

        Keywords:
            by_id: Whether to match ids instead of text.

        Returns: The leaf web element.

        """
        by_id = kwargs.pop("by_id", False)
        current_path = []
        last_id = None
        node = None

        for item in path:
            if last_id is None:
                last_id = self.browser.get_attribute(
                    'id', self.browser.element('./ul/li', parent=self))
            self.expand_id(last_id)
            if isinstance(item, re._pattern_type):
                self.logger.debug('Looking for regexp %r in path %r', item.pattern, current_path)
                for child_item in self.child_items(last_id, ids=by_id):
                    if item.match(child_item) is not None:
                        # found
                        item = child_item
                        break
                else:
                    raise CandidateNotFound(
                        {'message': "r{!r}: could not be found in the tree.".format(item.pattern),
                         'path': current_path,
                         'cause': None})
            current_path.append(item)
            xpath = self._construct_xpath(current_path, by_id=by_id)
            try:
                node = self.browser.element(xpath, parent=self)
            except NoSuchElementException:
                raise CandidateNotFound(
                    {'message': "{}: could not be found in the tree.".format(item),
                     'path': current_path,
                     'cause': None})

            last_id = self.browser.get_attribute('id', node)

        if node is not None:
            self.expand_id(last_id)

        return self.browser.element('./span', parent=node)

    def click_path(self, *path, **kwargs):
        """ Exposes a path and then clicks it.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.

        Keywords:
            by_id: Whether to match ids instead of text.

        Returns: The leaf web element.

        """
        leaf = self.expand_path(*path, **kwargs)
        title = self.browser.element('./a', parent=leaf)

        self.logger.info("Path %r yielded menuitem %r", path, self.browser.text(title))
        if title is not None:
            self.browser.plugin.ensure_page_safe()
            self.browser.click(title)

            checkbox_locator = './span[contains(@class, "dynatree-checkbox")]'
            if self.browser.is_displayed(checkbox_locator, parent=leaf):
                checkbox = self.browser.element(checkbox_locator, parent=leaf)
                self.browser.click(checkbox)

        return leaf


class CheckableDynaTree(DynaTree):
    """ Checkable variation of CFME Tree. This widget not only expands a tree for a provided path,
    but also checks a checkbox.
    """

    IS_CHECKABLE = './span[contains(@class, "dynatree-checkbox")]'
    IS_CHECKED = './../span[contains(@class, "dynatree-selected")]'

    def is_checkable(self, item):
        return bool(self.browser.elements(self.IS_CHECKABLE, parent=item))

    def is_checked(self, item):
        return bool(self.browser.elements(self.IS_CHECKED, parent=item))

    def check_uncheck_node(self, check, *path, **kwargs):
        leaf = self.expand_path(*path, **kwargs)
        if not self.is_checkable(leaf):
            raise TypeError('Item is not checkable')
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

    def fill(self, path):
        if self.node_checked(*path):
            return False
        else:
            self.check_node(*path)
            return True

    def read(self):
        do_not_read_this_widget()


def CheckableManageIQTree(tree_id=None):  # noqa
    return VersionPick({
        Version.lowest(): CheckableDynaTree(tree_id),
        '5.7.0.1': CheckableBootstrapTreeview(tree_id),
    })


def ManageIQTree(tree_id=None):  # noqa
    return VersionPick({
        Version.lowest(): DynaTree(tree_id),
        '5.7.0.1': BootstrapTreeview(tree_id),
    })


class SummaryFormItem(Widget):
    """The UI item that shows the values for objects that are NOT VMs, Providers and such ones."""
    LOCATOR = (
        './/h3[normalize-space(.)={}]/following-sibling::div[1]/div'
        '/label[normalize-space(.)={}]/following-sibling::div')

    def __init__(self, parent, group_title, item_name, text_filter=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.group_title = group_title
        self.item_name = item_name
        if text_filter is not None and not callable(text_filter):
            raise TypeError('text_filter= must be a callable')
        self.text_filter = text_filter

    def __locator__(self):
        return self.LOCATOR.format(quote(self.group_title), quote(self.item_name))

    @property
    def text(self):
        if not self.is_displayed:
            return None
        ui_text = self.browser.text(self)
        if self.text_filter is not None:
            # Process it
            ui_text = self.text_filter(ui_text)

        return ui_text

    def read(self):
        text = self.text
        if text is None:
            do_not_read_this_widget()
        return text


class MultiBoxSelect(View):

    ROOT = ParametrizedLocator("(.//table[@id={@id|quote}]){@number}")
    available_options = Select(id=Parameter("@available_items"))
    chosen_options = Select(id=Parameter("@chosen_items"))

    def __init__(self, parent, id, number="", move_into=None, move_from=None,
            available_items="choices_chosen", chosen_items="members_chosen", logger=None):
        View.__init__(self, parent, logger=logger)
        self.available_items = available_items
        self.chosen_items = chosen_items
        self.id = id
        if number:
            self.number = "[{}]".format(number)
        else:
            self.number = number
        if isinstance(move_into, WidgetDescriptor):
            self._move_into = move_into.klass(self, **move_into.kwargs)
        else:
            self._move_into = move_into
        if isinstance(move_from, WidgetDescriptor):
            self._move_from = move_from.klass(self, **move_from.kwargs)
        else:
            self._move_from = move_from

    def _values_to_remove(self, values):
        return list(self.all_options - set(values))

    def _values_to_add(self, values):
        return list(set(values) - self.all_options)

    @property
    def move_into_button(self):
        if isinstance(self._move_into, Button):
            button = self._move_into
        elif isinstance(self._move_into, basestring):
            button = self.browser.element(self._move_into, self)
        return button

    @property
    def move_from_button(self):
        if isinstance(self._move_from, Button):
            button = self._move_from
        elif isinstance(self._move_from, basestring):
            button = self.browser.element(self._move_from, self)
        return button

    def fill(self, values):
        if set(values) == self.all_options:
            return False
        else:
            values_to_remove = self._values_to_remove(values)
            values_to_add = self._values_to_add(values)
            if values_to_remove:
                self.chosen_options.fill(values_to_remove)
                self.move_from_button.click()
                self.browser.plugin.ensure_page_safe()
            if values_to_add:
                self.available_options.fill(values_to_add)
                self.move_into_button.click()
                self.browser.plugin.ensure_page_safe()
            return True

    @property
    def all_options(self):
        return {option.text for option in self.chosen_options.all_options}

    def read(self):
        return list(self.all_options)


class CheckboxSelect(Widget):

    ROOT = ParametrizedLocator(".//div[@id={@search_root|quote}]")

    def __init__(self, parent, search_root, text_access_func=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.search_root = search_root
        self._access_func = text_access_func

    @property
    def checkboxes(self):
        """All checkboxes."""
        return {Checkbox(self, id=el.get_attribute("id")) for el in self.browser.elements(
            ".//input[@type='checkbox']", parent=self)}

    @property
    def selected_checkboxes(self):
        """Only selected checkboxes."""
        return {cb for cb in self.checkboxes if cb.selected}

    @cached_property
    def selected_text(self):
        """Only selected checkboxes' text descriptions."""
        return {self.browser.element("./..", parent=cb).text for cb in self.selected_checkboxes}

    @property
    def selected_values(self):
        """Only selected checkboxes' values."""
        return {cb.get_attribute("value") for cb in self.selected_checkboxes}

    @property
    def unselected_checkboxes(self):
        """Only unselected checkboxes."""
        return {cb for cb in self.checkboxes if not cb.selected}

    @property
    def unselected_values(self):
        """Only unselected checkboxes' values."""
        return {cb.get_attribute("value") for cb in self.unselected_checkboxes}

    def checkbox_by_id(self, id):
        """Find checkbox's WebElement by id."""
        return Checkbox(self, id=id)

    def _values_to_remove(self, values):
        return list(self.selected_text - set(values))

    def _values_to_add(self, values):
        return list(set(values) - self.selected_text)

    def select_all(self):
        """Selects all checkboxes."""
        for cb in self.unselected_checkboxes:
            cb.fill(True)

    def unselect_all(self):
        """Unselects all checkboxes."""
        for cb in self.selected_checkboxes:
            cb.fill(False)

    def checkbox_by_text(self, text):
        """Returns checkbox's WebElement searched by its text."""
        if self._access_func is not None:
            for cb in self.checkboxes:
                txt = self._access_func(cb)
                if txt == text:
                    return cb
            else:
                raise NameError("Checkbox with text {} not found!".format(text))
        else:
            # Has to be only single
            return Checkbox(
                self,
                locator=".//*[normalize-space(.)={}]/input[@type='checkbox']".format(quote(text))
            )

    def fill(self, values):
        if set(values) == self.selected_text:
            return False
        else:
            for value in self._values_to_remove(values):
                checkbox = self.checkbox_by_text(value)
                checkbox.fill(False)
            for value in self._values_to_add(values):
                checkbox = self.checkbox_by_text(value)
                checkbox.fill(True)
            return True

    def read(self):
        """Only selected checkboxes."""
        return [cb for cb in self.checkboxes if cb.selected]


# ManageIQ table objects definition
class TableColumn(VanillaTableColumn):
    @property
    def checkbox(self):
        try:
            return self.browser.element('./input[@type="checkbox"]', parent=self)
        except NoSuchElementException:
            return None

    @property
    def checked(self):
        checkbox = self.checkbox
        if checkbox is None:
            return None
        return self.browser.is_selected(checkbox)

    def check(self):
        if not self.checked:
            self.browser.click(self.checkbox)

    def uncheck(self):
        if self.checked:
            self.browser.click(self.checkbox)


class TableRow(VanillaTableRow):
    Column = TableColumn


class Table(VanillaTable):
    CHECKBOX_ALL = '|'.join([
        './thead/tr/th[1]/input[contains(@class, "checkall")]',
        './tr/th[1]/input[contains(@class, "checkall")]'])
    SORTED_BY_LOC = (
        './thead/tr/th[contains(@class, "sorting_asc") or contains(@class, "sorting_desc")]')
    SORT_LINK = './thead/tr/th[{}]/a'
    Row = TableRow

    @property
    def checkbox_all(self):
        try:
            return self.browser.element(self.CHECKBOX_ALL, parent=self)
        except NoSuchElementException:
            return None

    @property
    def all_checked(self):
        checkbox = self.checkbox_all
        if checkbox is None:
            return None
        return self.browser.is_selected(checkbox)

    def check_all(self):
        if not self.all_checked:
            self.browser.click(self.checkbox_all)

    def uncheck_all(self):
        self.check_all()
        self.browser.click(self.checkbox_all)

    @property
    def sorted_by(self):
        """Returns the name of column that the table is sorted by. Attributized!"""
        return attributize_string(self.browser.text(self.SORTED_BY_LOC, parent=self))

    @property
    def sort_order(self):
        """Returns the sorting order of the table for current column.

        Returns:
            ``asc`` or ``desc``
        """
        klass = self.browser.get_attribute('class', self.SORTED_BY_LOC, parent=self)
        return re.search(r'sorting_(asc|desc)', klass).groups()[0]

    def click_sort(self, column):
        """Clicks the sorting link in the given column. The column gets attributized."""
        self.logger.info('click_sort(%r)', column)
        column = attributize_string(column)
        column_position = self.header_index_mapping[self.attributized_headers[column]]
        self.browser.click(self.SORT_LINK.format(column_position + 1), parent=self)

    def sort_by(self, column, order='asc'):
        """Sort table by column and in given direction.

        Args:
            column: Name of the column, can be normal or attributized.
            order: Sorting order. ``asc`` or ``desc``.
        """
        self.logger.info('sort_by(%r, %r)', column, order)
        column = attributize_string(column)

        # Sort column
        if self.sorted_by != column:
            self.click_sort(column)
        else:
            self.logger.debug('sort_by(%r, %r): column already selected', column, order)

        # Sort order
        if self.sort_order != order:
            self.logger.info('sort_by(%r, %r): changing the sort order', column, order)
            self.click_sort(column)
            self.logger.debug('sort_by(%r, %r): order already selected', column, order)


class SummaryTable(VanillaTable):
    """Table used in Provider, VM, Host, ... summaries.

    Todo:
        * Make it work properly with rowspan (that is for the My Company Tags).

    Args:
        title: Title of the table (eg. ``Properties``)
    """
    BASELOC = './/table[./thead/tr/th[contains(@align, "left") and normalize-space(.)={}]]'
    Image = namedtuple('Image', ['alt', 'title', 'src'])

    def __init__(self, parent, title, *args, **kwargs):
        VanillaTable.__init__(self, parent, self.BASELOC.format(quote(title)), *args, **kwargs)

    @property
    def fields(self):
        """Returns a list of the field names in the table (the left column)."""
        return [row[0].text for row in self]

    def get_field(self, field_name):
        """Returns the table row of the field with this name.

        Args:
            field_name: Name of the field (left column)

        Returns:
            An instance of :py:class:`VanillaRow`
        """
        try:
            return self.row((0, field_name))
        except IndexError:
            raise NameError('Could not find field with name {!r}'.format(field_name))

    def get_text_of(self, field_name):
        """Returns the text of the field with this name.

        Args:
            field_name: Name of the field (left column)

        Returns:
            :py:class:`str`
        """
        return self.get_field(field_name)[1].text

    def get_img_of(self, field_name):
        """Returns the information about the image in the field with this name.

        Args:
            field_name: Name of the field (left column)

        Returns:
            A 3-tuple: ``alt``, ``title``, ``src``.
        """
        try:
            img_el = self.browser.element('./img', parent=self.get_field(field_name)[1])
        except NoSuchElementException:
            return None

        return self.Image(
            self.browser.get_attribute('alt', img_el),
            self.browser.get_attribute('title', img_el),
            self.browser.get_attribute('src', img_el))

    def click_at(self, field_name):
        """Clicks the field with this name.

        Args:
            field_name: Name of the field (left column)
        """
        return self.get_field(field_name)[1].click()

    def read(self):
        return {field: self.get_text_of(field) for field in self.fields}


class Accordion(PFAccordion):
    @property
    def is_dimmed(self):
        return bool(
            self.browser.elements('.//div[contains(@id, "tree") and contains(@class, "dimmed")]'))


class Calendar(TextInput):
    """A CFME calendar form field

    Calendar fields are readonly, and managed by the dxhtmlCalendar widget. A Calendar field
    will accept any object that can be coerced into a string, but the value may not match the format
    expected by dhtmlxCalendar or CFME. For best results, either a ``datetime.date`` or
    ``datetime.datetime`` object should be used to create a valid date field.

    Args:
        name: "name" property of the readonly calendar field.
    """

    # Expects: arguments[0] = element, arguments[1] = value to set
    set_angularjs_value_script = """\
        (function(elem, value){
        var angular_elem = angular.element(elem);
        var $parse = angular_elem.injector().get('$parse');
        var getter = $parse(elem.getAttribute('ng-model'));
        var setter = getter.assign;
        angular_elem.scope().$apply(function($scope) { setter($scope, value); });
    }(arguments[0], arguments[1]));
    """

    def fill(self, value):
        # input = self.browser.element(self.name)
        if isinstance(value, date):
            date_str = value.strftime('%m/%d/%Y')
        else:
            date_str = str(value)
        self.move_to()
        # need to write to a readonly field: resort to evil
        if self.browser.get_attribute("ng-model", self) is not None:
            self.browser.execute_script(self.set_angularjs_value_script, self.browser.element(self),
             date_str)
        else:
            self.browser.set_attribute("value", date_str, self)
            # Now when we set the value, we need to simulate a change event.
            if self.browser.get_attribute("data-date-autoclose", self):
                # New one
                script = "$(arguments[0]).trigger('changeDate');"
            else:
                # Old one
                script = "$(arguments[0]).change();"
            try:
                self.browser.execute_script(script, self.browser.element(self))
            except WebDriverException as e:
                self.logger.warning(
                    "An exception was raised during handling of the Cal #{}'s change event:\n{}"
                    .format(self.name, str(e)))
        self.browser.plugin.ensure_page_safe()
        return True


class SNMPHostsField(View):

    _input = Input("host")

    def __init__(self, parent, logger=None):
        View.__init__(self, parent, logger=logger)

    def fill(self, values):
        fields = self.host_fields
        if isinstance(values, basestring):
            values = [values]
        if len(values) > len(fields):
            raise ValueError("You cannot specify more hosts than the form allows!")
        return any(fields[i].fill(value) for i, value in enumerate(values))

    @property
    def host_fields(self):
        """Returns list of locators to all host fields"""
        if self._input.is_displayed:
            return [self._input]
        else:
            return [Input(self, "host_{}".format(i)) for i in range(1, 4)]


class SNMPTrapsField(Widget):

    def __init__(self, parent, logger=None):
        Widget.__init__(self, parent, logger=logger)

    def fill_oid_field(self, i, oid):
        oid_field = Input(self, "oid__{}".format(i))
        return oid_field.fill(oid)

    def fill_type_field(self, i, type_):
        type_field = BootstrapSelect(self, "var_type__{}".format(i))
        return type_field.fill(type_)

    def fill_value_field(self, i, value):
        value_field = Input(self, "value__{}".format(i))
        return value_field.fill(value)

    def fill(self, traps):
        result = []
        for i, trap in enumerate(traps, 1):
            assert 2 <= len(trap) <= 3, "The tuple must be at least 2 items and max 3 items!"
            if len(trap) == 2:
                trap += (None,)
            oid, type_, value = trap
            result.append(any((
                self.fill_oid_field(i, oid),
                self.fill_type_field(i, type_),
                self.fill_value_field(i, value)
            )))
        return any(result)

    def read(self):
        do_not_read_this_widget()


class SNMPForm(View):
    hosts = SNMPHostsField()
    version = BootstrapSelect("snmp_version")
    id = Input("trap_id")
    traps = SNMPTrapsField()


class ScriptBox(Widget):
    """Represents a script box as is present on the customization templates pages.
    This box has to be activated before keys can be sent. Since this can't be done
    until the box element is visible, and some dropdowns change the element, it must
    be activated "inline".

    Args:
    """

    def __init__(self, parent, locator=None, item_name=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.locator = locator
        self.item_name = item_name

    def __locator__(self):
        if not self.locator:
            self.locator = "//textarea[contains(@id, 'method_data')]"
        return self.locator

    @property
    def name(self):
        if not self.item_name:
            self.item_name = 'ManageIQ.editor'
        return self.item_name

    @property
    def script(self):
        return self.browser.execute_script('{}.getValue();'.format(self.name))

    def fill(self, value):
        if self.script == value:
            return False
        self.browser.execute_script('{}.setValue(arguments[0]);'.format(self.name), value)
        self.browser.execute_script('{}.save();'.format(self.name))
        return True

    def read(self):
        return self.script

    def get_value(self):
        script = self.browser.execute_script('return {}.getValue();'.format(self.name))
        script = script.replace('\\"', '"').replace("\\n", "\n")
        return script

    def workaround_save_issue(self):
        # We need to fire off the handlers manually in some cases ...
        self.browser.execute_script(
            "{}._handlers.change.map(function(handler) {{ handler() }});".format(self.item_name))


class Paginator(Widget):
    """ Represents Paginator control that includes First/Last/Next/Prev buttons
    and a control displaying amount of items on current page vs overall amount.

    It is mainly used in Paginator Pane.
    """
    PAGINATOR_CTL = './/ul[@class="pagination"]'
    CUR_PAGE_CTL = './li/span/input[@name="limitstart"]/..'
    PAGE_BUTTON_CTL = './li[contains(@class, {})]/span'

    def __locator__(self):
        return self._paginator

    @property
    def _paginator(self):
        return self.browser.element(self.PAGINATOR_CTL, parent=self.parent_view)

    def _is_enabled(self, element):
        return 'disabled' not in self.browser.classes(element.find_element_by_xpath('..'))

    def _click_button(self, cmd):
        cur_page_btn = self.browser.element(self.PAGE_BUTTON_CTL.format(quote(cmd)),
                                            parent=self._paginator)
        if self._is_enabled(cur_page_btn):
            self.browser.click(cur_page_btn)
        else:
            raise NoSuchElementException('such button {} is absent/grayed out'.format(cmd))

    def next_page(self):
        self._click_button('next')

    def prev_page(self):
        self._click_button('prev')

    def last_page(self):
        self._click_button('last')

    def first_page(self):
        self._click_button('first')

    def page_info(self):
        cur_page = self.browser.element(self.CUR_PAGE_CTL, parent=self._paginator)
        text = cur_page.text
        return re.search('(\d+)\s+of\s+(\d+)', text).groups()


class PaginationPane(View):
    """ Represents Paginator Pane with the following controls.

    The intention of this view is to use it as nested view on f.e. Infrastructure Providers page.
    """
    ROOT = '//div[@id="paging_div"]'

    check_all_items = Checkbox(id='masterToggle')
    sort_by = BootstrapSelect(id='sort_choice')
    items_on_page = BootstrapSelect(id='ppsetting')
    paginator = Paginator()

    @property
    def exists(self):
        return self.is_displayed

    def check_all(self):
        self.check_all_items.fill(True)

    def uncheck_all(self):
        self.check_all()
        self.check_all_items.fill(False)

    def sort(self, value):
        self.sort_by.select_by_visible_text(value)

    @property
    def sorted_by(self):
        raise NotImplementedError('to implement it when needed')

    @property
    def items_per_page(self):
        selected = self.items_on_page.selected_option
        return int(re.sub(r'\s+items', '', selected))

    def set_items_per_page(self, value):
        self.items_on_page.select_by_visible_text(str(value))

    def _parse_pages(self):
        max_item, item_amt = self.paginator.page_info()

        item_amt = int(item_amt)
        max_item = int(max_item)
        items_per_page = self.items_per_page

        # obtaining amount of existing pages, there is 1 page by default
        if item_amt == 0:
            page_amt = 1
        else:
            # round up after dividing total item count by per-page
            page_amt = int(ceil(float(item_amt) / float(items_per_page)))

        # calculating current_page_number
        if max_item <= items_per_page:
            cur_page = 1
        else:
            # round up after dividing highest displayed item number by per-page
            cur_page = int(ceil(float(max_item) / float(items_per_page)))

        return cur_page, page_amt

    @property
    def cur_page(self):
        return self._parse_pages()[0]

    @property
    def pages_amount(self):
        return self._parse_pages()[1]

    def next_page(self):
        self.paginator.next_page()

    def prev_page(self):
        self.paginator.prev_page()

    def first_page(self):
        if self.cur_page != 1:
            self.paginator.first_page()

    def last_page(self):
        if self.cur_page != self.pages_amount:
            self.paginator.last_page()

    def pages(self):
        """Generator to iterate over pages, yielding after moving to the next page"""
        if self.exists:
            # start iterating at the first page
            if self.cur_page != 1:
                self.logger.debug('Resetting paginator to first page')
                self.first_page()

            # Adding 1 to pages_amount to include the last page in loop
            for page in range(1, self.pages_amount + 1):
                yield self.cur_page
                if self.cur_page == self.pages_amount:
                    # last or only page, stop looping
                    break
                else:
                    self.logger.debug('Paginator advancing to next page')
                    self.next_page()

        else:
            return

    @property
    def items_amount(self):
        return self.paginator.page_info()[1]

    def find_row_on_pages(self, table, *args, **kwargs):
        """Find first row matching filters provided by kwargs on the given table widget

        Args:
            table: Table widget object
            args: Filters to be passed to table.row()
            kwargs: Filters to be passed to table.row()
        """
        self.first_page()
        for _ in self.pages():
            try:
                row = table.row(*args, **kwargs)
            except IndexError:
                continue
            if not row:
                continue
            else:
                return row
        else:
            raise NoSuchElementException('Row matching filter {} not found on table {}'
                                         .format(kwargs, table))


class Stepper(View):
    """ A CFME Stepper Control

    .. code-block:: python

        stepper = Stepper(locator='//div[contains(@class, "timeline-stepper")]')
        stepper.increase()
    """
    ROOT = ParametrizedLocator('{@locator}')

    minus_button = Button('-')
    plus_button = Button('+')
    value_field = Input(locator='.//input[contains(@class, "bootstrap-touchspin")]')

    def __init__(self, parent, locator, logger=None):
        View.__init__(self, parent=parent, logger=logger)

        self.locator = locator

    def read(self):
        return int(self.value_field.read())

    def decrease(self):
        self.minus_button.click()

    def increase(self):
        self.plus_button.click()

    def set_value(self, value):
        value = int(value)
        if value < 1:
            raise ValueError('The value cannot be less than 1')

        steps = value - self.read()
        if steps == 0:
            return False
        elif steps > 0:
            operation = self.increase
        else:
            operation = self.decrease

        steps = abs(steps)
        for step in range(steps):
            operation()
        return True

    def fill(self, value):
        return self.set_value(value)


class RadioGroup(Widget):
    """ CFME Radio Group Control

    .. code-block:: python

        radio_group = RadioGroup(locator='//span[contains(@class, "timeline-option")]')
        radio_group.select(radio_group.button_names()[-1])
    """
    BUTTONS = './/label[input[@type="radio"]]'

    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent=parent, logger=logger)
        self.locator = locator

    def __locator__(self):
        return self.locator

    def _get_button(self, name):
        br = self.browser
        return next(btn for btn in br.elements(self.BUTTONS) if br.text(btn) == name)

    @property
    def button_names(self):
        return [self.browser.text(btn) for btn in self.browser.elements(self.BUTTONS)]

    @property
    def selected(self):
        names = self.button_names
        for name in names:
            if 'ng-valid-parse' in self.browser.classes('.//input[@type="radio"]',
                                                        parent=self._get_button(name)):
                return name

        else:
            # radio button doesn't have any marks to make out which button is selected by default.
            # so, returning first radio button's name
            return names[0]

    def select(self, name):
        button = self._get_button(name)
        if self.selected != name:
            button.click()
            return True
        return False

    def read(self):
        return self.selected

    def fill(self, name):
        return self.select(name)


class BreadCrumb(Widget):
    """ CFME BreadCrumb navigation control

    .. code-block:: python

        breadcrumb = BreadCrumb()
        breadcrumb.click_location(breadcrumb.locations[0])
    """
    ROOT = '//ol[@class="breadcrumb"]'
    ELEMENTS = './/li'

    def __init__(self, parent, locator=None, logger=None):
        Widget.__init__(self, parent=parent, logger=logger)
        self._locator = locator or self.ROOT

    def __locator__(self):
        return self._locator

    @property
    def _path_elements(self):
        return self.browser.elements(self.ELEMENTS, parent=self)

    @property
    def locations(self):
        return [self.browser.text(loc) for loc in self._path_elements]

    @property
    def active_location(self):
        br = self.browser
        return next(br.text(loc) for loc in self._path_elements if 'active' in br.classes(loc))

    def click_location(self, name, handle_alert=True):
        br = self.browser
        location = next(loc for loc in self._path_elements if br.text(loc) == name)
        result = br.click(location, ignore_ajax=handle_alert)
        if handle_alert:
            self.browser.handle_alert(wait=2.0, squash=True)
            self.browser.plugin.ensure_page_safe()
        return result


class ItemsToolBarViewSelector(View):
    """ represents toolbar's view selector control
        it is present on pages with items like Infra or Cloud Providers pages

    .. code-block:: python

        view_selector = View.nested(ItemsToolBarViewSelector)

        view_selector.select('Tile View')
        view_selector.selected
    """
    ROOT = './/div[contains(@class, "toolbar-pf-view-selector")]'
    grid_button = VersionPick({
        Version.lowest(): ViewChangeButton(title='Grid View'),
        '5.7.0': Button(title='Grid View')})
    tile_button = VersionPick({
        Version.lowest(): ViewChangeButton(title='Tile View'),
        '5.7.0': Button(title='Tile View')})
    list_button = VersionPick({
        Version.lowest(): ViewChangeButton(title='List View'),
        '5.7.0': Button(title='List View')})

    @property
    def _view_buttons(self):
        yield self.grid_button
        yield self.tile_button
        yield self.list_button

    def select(self, title):
        for button in self._view_buttons:
            if button.title == title:
                return button.click()
        else:
            raise ValueError("The view with title {title} isn't present".format(title=title))

    @property
    def selected(self):
        return next(btn.title for btn in self._view_buttons if btn.active)


class DetailsToolBarViewSelector(View):
    """ represents toolbar's view selector control
        it is present on pages like Infra Providers Details page

    .. code-block:: python

        view_selector = View.nested(DetailsToolBarViewSelector)

        view_selector.select('Dashboard View')
        view_selector.selected
    """
    ROOT = './/div[contains(@class, "toolbar-pf-view-selector")]'
    summary_button = VersionPick({
        Version.lowest(): ViewChangeButton(title='Summary View'),
        '5.7.0': Button(title='Summary View')})
    dashboard_button = VersionPick({
        Version.lowest(): ViewChangeButton(title='Dashboard View'),
        '5.7.0': Button(title='Dashboard View')})

    @property
    def _view_buttons(self):
        yield self.dashboard_button
        yield self.summary_button

    def select(self, title):
        for button in self._view_buttons:
            if button.title == title:
                return button.click()
        else:
            raise ValueError("The view with title {title} isn't present".format(title=title))

    @property
    def selected(self):
        return next(btn.title for btn in self._view_buttons if btn.active)


class Search(View):
    """ Represents search_text control
    # TODO Add advanced search
    """
    search_text = Input(name="search_text")
    search_btn = Text("//div[@id='searchbox']//div[contains(@class, 'form-group')]"
                      "/*[self::a or (self::button and @type='submit')]")
    clear_btn = Text(".//*[@id='searchbox']//div[contains(@class, 'clear')"
                     "and not(contains(@style, 'display: none'))]/div/button")

    def clear_search(self):
        if not self.is_empty:
            self.clear_btn.click()
            self.search_btn.click()

    def search(self, text):
        self.search_text.fill(text)
        self.search_btn.click()

    @property
    @logged(log_result=True)
    def is_empty(self):
        return not bool(self.search_text.value)


class UpDownSelect(View):
    """Multiselect with two arrows (up/down) next to it. Eg. in AE/Domain priority selection.

    Args:
        select_loc: Locator for the select box (without Select element wrapping)
        up_loc: Locator of the Move Up arrow.
        down_loc: Locator with Move Down arrow.
    """

    select = Select(ParametrizedLocator('{@select_loc}'))
    up = Text(ParametrizedLocator('{@up_loc}'))
    down = Text(ParametrizedLocator('{@down_loc}'))

    def __init__(self, parent, select_loc, up_loc, down_loc, logger=None):
        View.__init__(self, parent, logger=logger)
        self.select_loc = select_loc
        self.up_loc = up_loc
        self.down_loc = down_loc

    @property
    def is_displayed(self):
        return self.select.is_displayed and self.up.is_displayed and self.down.is_displayed

    def read(self):
        return self.items

    @property
    def items(self):
        return [option.text for option in self.select.all_options]

    def move_up(self, item):
        item = str(item)
        assert item in self.items
        self.select.deselect_all()
        self.select.select_by_visible_text(item)
        self.up.click()

    def move_down(self, item):
        item = str(item)
        assert item in self.items
        self.select.deselect_all()
        self.select.select_by_visible_text(item)
        self.down.click()

    def move_top(self, item):
        item = str(item)
        assert item in self.items
        self.select.deselect_all()
        while item != self.items[0]:
            self.select.select_by_visible_text(item)
            self.up.click()

    def move_bottom(self, item):
        item = str(item)
        assert item in self.items
        self.select.deselect_all()
        while item != self.items[-1]:
            self.select.select_by_visible_text(item)
            self.down.click()

    def fill(self, items):
        if not isinstance(items, (list, tuple)):
            items = [items]
        current_items = self.items[:len(items)]
        if current_items == items:
            return False
        items = map(str, items)
        for item in reversed(items):  # reversed because every new item at top pushes others down
            self.move_top(item)
        return True


class AlertEmail(View):
    """This set of widgets can be found in Control / Explorer / Alerts when you edit an alert."""

    @ParametrizedView.nested
    class recipients(ParametrizedView):  # noqa
        PARAMETERS = ("email", )
        ALL_EMAILS = ".//a[starts-with(@title, 'Remove')]"
        email = Text(ParametrizedLocator(".//a[text()={email|quote}]"))

        def remove(self):
            self.email.click()

        @classmethod
        def all(cls, browser):
            return [(browser.text(e), ) for e in browser.elements(cls.ALL_EMAILS)]

    ROOT = ParametrizedLocator(".//div[@id={@id|quote}]")
    RECIPIENTS = "./div[@id='edit_to_email_div']//a"
    add_button = Text(".//div[@title='Add']")
    recipients_input = TextInput("email")

    def __init__(self, parent, id="edit_email_div", logger=None):
        View.__init__(self, parent, logger=logger)
        self.id = id

    def fill(self, values):
        if isinstance(values, basestring):
            values = [values]
        if self.all_emails == set(values):
            return False
        else:
            values_to_remove = self._values_to_remove(values)
            values_to_add = self._values_to_add(values)
            for value in values_to_remove:
                self.recipients(value).remove()
            for value in values_to_add:
                self._add_recipient(value)
            return True

    def _values_to_remove(self, values):
        return list(self.all_emails - set(values))

    def _values_to_add(self, values):
        return list(set(values) - self.all_emails)

    def _add_recipient(self, email):
        self.recipients_input.fill(email)
        self.add_button.click()

    @property
    def all_emails(self):
        return {self.browser.text(e) for e in self.browser.elements(self.RECIPIENTS)}

    def read(self):
        return list(self.all_emails)


class TimelinesZoomSlider(View):
    """This control represents Timeline's Zoom Slider

    """
    ROOT = ParametrizedLocator('{@locator}')
    zoom_in_button = Text(locator='//button[@id="timeline-pf-zoom-in"]')  # "+" button
    zoom_out_button = Text(locator='//button[@id="timeline-pf-zoom-out"]')  # "-" button

    def __init__(self, parent, locator, logger=None):
        View.__init__(self, parent, logger=logger)
        self.locator = locator

    @property
    def value(self):
        return float(self.browser.get_attribute('value', self))

    @cached_property
    def max(self):
        return float(self.browser.get_attribute('max', self))

    @cached_property
    def min(self):
        return float(self.browser.get_attribute('min', self))

    def zoom_in(self):
        self.zoom_in_button.click()

    def zoom_out(self):
        self.zoom_out_button.click()

    def zoom_max(self):
        while self.value < self.max:
            self.zoom_in()

    def zoom_min(self):
        while self.value > self.min:
            self.zoom_out()

    def read(self):
        return self.value


class TimelinesFilter(View):
    """represents Filter Part of Timelines view

    """
    # common
    event_type = BootstrapSelect(id='tl_show')
    event_category = BootstrapSelect(id='tl_category_management')
    time_period = Stepper(locator='//div[contains(@class, "timeline-stepper")]')
    time_range = BootstrapSelect(id='tl_range')
    time_position = BootstrapSelect(id='tl_timepivot')
    # todo: implement correct switch between management/policy views when switchable views done
    apply = Text(locator='.//div[contains(@class, "timeline-apply")]')
    # management controls
    detailed_events = Checkbox(name='showDetailedEvents')
    # policy controls
    policy_event_category = BootstrapSelect(id='tl_category_policy')
    policy_event_status = RadioGroup(locator='//span[contains(@class, "timeline-option")]')


class TimelinesChart(View):
    """represents Chart part of Timelines View

    # currently only event collection is available
    # todo: to add widgets for all controls and add chart objects interaction functionality
    """
    ROOT = '//div[contains(@class, "timeline-container")]'
    CATEGORIES = './/*[name()="g" and contains(@class, "timeline-pf-labels")]' \
                 '//*[name()="text" and @class="timeline-pf-label"]'

    EVENTS = '(.//*[name()="g" and contains(@class, "timeline-pf-drops-container")]/*[name()="g" ' \
             'and @class="timeline-pf-drop-line"])[{pos}]/*[name()="text" ' \
             'and contains(@class, "timeline-pf-drop")]'

    legend = Table(locator='//div[@id="legend"]/table')
    zoom = TimelinesZoomSlider(locator='//input[@id="timeline-pf-slider"]')

    class TimelinesEvent(object):
        def __repr__(self):
            attrs = [attr for attr in self.__dict__.keys() if not attr.startswith('_')]
            params = ", ".join(["{}={}".format(attr, getattr(self, attr)) for attr in attrs])
            return "TimelinesEvent({})".format(params)

    def __init__(self, parent, logger=None):
        super(TimelinesChart, self).__init__(parent=parent, logger=logger)

    def get_categories(self, *categories):
        br = self.browser
        prepared_categories = []
        for num, element in enumerate(br.elements(self.CATEGORIES), start=1):
            # categories have number of events inside them
            mo = re.search('^(.*?)(\s\(\s*\d+\s*\)\s*)*$', br.text(element))
            category_name = mo.groups()[0]

            if len(categories) == 0 or (len(categories) > 0 and category_name in categories):
                prepared_categories.append((num, category_name))
        return prepared_categories

    def _is_group(self, evt):
        return 'timeline-pf-event-group' in self.browser.classes(evt)

    def _prepare_event(self, evt, category):
        node = document_fromstring(evt)
        # lxml doesn't replace <br> with \n in this case. so this has to be done by us
        for br in node.xpath("*//br"):
            br.tail = "\n" + br.tail if br.tail else "\n"

        # parsing event and preparing its attributes
        event = self.TimelinesEvent()
        for line in node.text_content().split('\n'):
            attr_name, attr_val = re.search('^(.*?):(.*)$', line).groups()
            attr_name = attr_name.strip().lower().replace(' ', '_')
            setattr(event, attr_name, attr_val.strip())
        event.category = category
        return event

    def _click_group(self, group):
        self.browser.execute_script("""jQuery.fn.art_click = function () {
                                    this.each(function (i, e) {
                                    var evt = new MouseEvent("click");
                                    e.dispatchEvent(evt);
                                    });};
                                    $(arguments[0]).art_click();""", group)

    def get_events(self, *categories):
        got_categories = self.get_categories(*categories)
        events = []
        for category in got_categories:
            cat_position, cat_name = category
            # obtaining events for each category
            for raw_event in self.browser.elements(self.EVENTS.format(pos=cat_position)):
                if not self._is_group(raw_event):
                    # if ordinary event
                    event_text = self.browser.get_attribute('data-content', raw_event)
                    events.append(self._prepare_event(event_text, cat_name))
                else:
                    # if event group
                    # todo: compare old table with new one if any issues
                    self.legend.clear_cache()
                    self._click_group(raw_event)
                    self.legend.wait_displayed()
                    for row in self.legend.rows():
                        event_text = self.browser.get_attribute('innerHTML', row['Event'])
                        events.append(self._prepare_event(event_text, cat_name))
        return events


class TimelinesView(View):
    """represents Timelines page
    """
    title = Text(locator='//h1')
    breadcrumb = BreadCrumb()

    @View.nested
    class filter(TimelinesFilter):  # NOQA
        pass

    @View.nested
    class chart(TimelinesChart):  # NOQA
        pass

    @property
    def is_displayed(self):
        return self.title.text == 'Timelines'


class AttributeValueForm(View):
    @View.nested
    class fields(ParametrizedView):  # noqa
        PARAMETERS = ('id', )

        attribute = Input(
            locator=ParametrizedLocator('.//input[@id=concat({@attr_prefix|quote}, {id|quote})]'))
        value = Input(
            locator=ParametrizedLocator('.//input[@id=concat({@val_prefix|quote}, {id|quote})]'))

        @property
        def attr_prefix(self):
            return self.parent.attr_prefix

        @property
        def val_prefix(self):
            return self.parent.val_prefix

        # TODO: Figure out how to smuggle some extra data to the all classmethod
        # TODO: since it is now impossible to pass the attr_prefix to it.

    ATTRIBUTES = ParametrizedLocator('.//input[starts-with(@id, {@attr_prefix|quote})]')

    def __init__(self, parent, attr_prefix, val_prefix, start=1, end=5, logger=None):
        View.__init__(self, parent, logger=logger)
        self.attr_prefix = attr_prefix
        self.val_prefix = val_prefix
        self.start = start
        self.end = end

    @property
    def count(self):
        return (self.end - self.start) + 1

    @property
    def current_attributes(self):
        attributes = [
            (i, self.browser.get_attribute('value', e))
            for i, e in enumerate(self.browser.elements(self.ATTRIBUTES), self.start)]
        return [a for a in attributes if a]

    def attribute_to_id(self, attribute):
        for id, attr in self.current_attributes:
            if attr == attribute:
                return id
        else:
            return None

    def read(self):
        result = {}
        for id, attribute in self.current_attributes:
            if not attribute:
                continue
            value = self.fields(id=str(id)).value.read()
            result[attribute] = value
        return result

    def clear(self):
        changed = False
        for id, attr in self.current_attributes:
            field = self.fields(id=str(id))
            if field.attribute.fill(''):
                changed = True
            if field.value.fill(''):
                changed = True
        return changed

    def fill(self, values):
        if hasattr(values, 'items') and hasattr(values, 'keys'):
            values = list(values.items())
        if len(values) > self.count:
            raise ValueError(
                'This form is supposed to have only {} fields, passed {} items'.format(
                    self.count, len(values)))
        changed = self.clear()
        for id, (key, value) in enumerate(values, self.start):
            field = self.fields(id=str(id))
            if field.fill({'attribute': key, 'value': value}):
                changed = True
        return changed


class FileInput(BaseFileInput):
    """ represents enhanced FileInput control.
    Accepts a string. If the string is a file, then it is put in the input. Otherwise a temporary
    file is generated and that one is fed to the file input.

    technical debt:
    ronny:
        this introduces a requirement for out of band resource and file management, we should avoid
        something like that
        while this is merge-able as it adds functionality, we should clearly mark this as technical
        debt needing a better resource management exposed from widgetastic or our wrappers
    """
    def fill(self, value):
        if not os.path.isfile(value):
            f = NamedTemporaryFile()
            f.write(str(value))
            f.flush()
            value = os.path.abspath(f.name)
            atexit.register(f.close)
        return super(FileInput, self).fill(value)
