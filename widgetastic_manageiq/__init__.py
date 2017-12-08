# -*- coding: utf-8 -*-
import atexit
import json
import math
from collections import namedtuple
from datetime import date
from math import ceil
from tempfile import NamedTemporaryFile

import os
import re
import six
from cached_property import cached_property
from jsmin import jsmin
from lxml.html import document_fromstring
from selenium.common.exceptions import WebDriverException
from wait_for import TimedOutError, wait_for
from widgetastic.exceptions import NoSuchElementException
from widgetastic.log import logged
from widgetastic.utils import ParametrizedLocator, Parameter, ParametrizedString, attributize_string
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
    FileInput as BaseFileInput,
    ClickableMixin,
    ConditionalSwitchableView,
    do_not_read_this_widget)
from widgetastic.xpath import quote
from widgetastic_patternfly import (
    Accordion as PFAccordion, BootstrapSwitch, BootstrapTreeview,
    BootstrapSelect, Button, CheckableBootstrapTreeview,
    Dropdown, Input, VerticalNavigation, Tab)

from cfme.exceptions import ItemNotFound
from cfme.utils.blockers import BZ


class DynamicTableAddError(Exception):
    """Raised when an attempt to add or save a row to a `widgetastic_manageiq.DynamicTable` fails"""
    pass


# TODO: replace below calls with direct calls later
CheckableManageIQTree = CheckableBootstrapTreeview
ManageIQTree = BootstrapTreeview


class SummaryFormItem(Widget):
    """The UI item that shows the values for objects that are NOT VMs, Providers and such ones."""
    LOCATOR = (
        './/h3[normalize-space(.)={}]/following-sibling::div/div'
        '//label[normalize-space(.)={}]/following-sibling::div')
    SINGLE_ITEM_LOCATOR = '//label[normalize-space(.)={}]/following-sibling::div'

    def __init__(self, parent, group_title, item_name, text_filter=None, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.group_title = group_title
        self.item_name = item_name
        if text_filter is not None and not callable(text_filter):
            raise TypeError('text_filter= must be a callable')
        self.text_filter = text_filter

    def __locator__(self):
        if not self.group_title:
            return self.SINGLE_ITEM_LOCATOR.format(quote(self.item_name))
        else:
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


class SummaryForm(Widget):
    """Represents a group of SummaryFormItem widgets.

    Args:
        group_title (str): title of a summary form, e.g. "Basic Information"
    """

    ROOT = ParametrizedLocator(".//h3[normalize-space(.)={@group_title|quote}]")
    ALL_LABELS = "./following-sibling::div//label"
    LABEL_TEXT = "./following-sibling::div//label[normalize-space(.)={}]/following-sibling::div"

    def __init__(self, parent, group_title, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.group_title = group_title

    @property
    def items(self):
        """Returns a list of the items names."""
        b = self.browser
        return [b.text(el) for el in b.elements(self.ALL_LABELS)]

    def get_item(self, item_name):
        return self.browser.element(self.LABEL_TEXT.format(quote(item_name)))

    def click_at(self, item_name):
        """Clicks the item with this name.

        Args:
            item_name: Name of the item
        """
        return self.browser.click(self.get_item(item_name))

    def get_text_of(self, item_name):
        """Returns the text of the item with this name.

        Args:
            item_name: Name of the item

        Returns:
            :py:class:`str` or
            :py:class:`list` in case a few values present for 1 field(covers multiple tags)
        """

        multiple_lines = self.get_item(item_name).text.splitlines()
        if len(multiple_lines) > 1:
            return multiple_lines
        else:
            return multiple_lines[0]

    def read(self):
        return {item: self.get_text_of(item) for item in self.items}


class MultiBoxSelect(View):

    """This view combines two `<select>` elements and buttons for moving items between them.

    This view can be found in policy profile, alert profiles adding screens; assigning actions to an
    event, assigning conditions to a policy screens and so on.

    Args:
        available_items (str): provided value of `<select>` id for available items
        chosen_items (str): provided value of `<select>` id for available items
        move_into (str): provided value of `data-submit` attribute for 'move_into' button
        move_from (str): provided value of `data-submit` attribute for 'move_from' button

    """

    available_options = Select(id=Parameter("@available_items"))
    chosen_options = Select(id=Parameter("@chosen_items"))
    move_into_button = Button(**{"data-submit": Parameter("@move_into")})
    move_from_button = Button(**{"data-submit": Parameter("@move_from")})

    def __init__(self, parent, move_into="choices_chosen_div", move_from="members_chosen_div",
            available_items="choices_chosen", chosen_items="members_chosen", logger=None):
        View.__init__(self, parent, logger=logger)
        self.available_items = available_items
        self.chosen_items = chosen_items
        self.move_into = move_into
        self.move_from = move_from

    def _values_to_remove(self, values):
        return list(set(self.all_options) - set(values))

    def _values_to_add(self, values):
        return list(set(values) - set(self.all_options))

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
        return [option.text for option in self.chosen_options.all_options]

    def read(self):
        return self.all_options


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


class BootstrapSwitchSelect(View):
    """BootstrapSwitchSelect view.

    This view is very similar to CheckboxSelect view. BootstrapSwitches used instead of
    usual Checkboxes. It can be found in policy's events assignment screen since CFME 5.8.1.

    """

    ROOT = ParametrizedLocator(".//div[@id={@search_root|quote}]")
    BS_LOCATOR = ".//text()[normalize-space(.)='{}']/preceding-sibling::div[1]//input"

    def __init__(self, parent, search_root, logger=None):
        View.__init__(self, parent, logger=logger)
        self.search_root = search_root

    def _get_attr_from_text(self, attr, text):
        return self.browser.element(self.BS_LOCATOR.format(text)).get_attribute(attr)

    @cached_property
    def all_labels(self):
        elements = self.browser.elements(".//div[@class='form-horizontal']")
        labels = []
        for el in elements:
            labels.extend(self.browser.text(el).split(" Yes No ")[1:])
        return labels

    @ParametrizedView.nested
    class _bootstrap_switch(ParametrizedView):  # noqa
        PARAMETERS = ("id_attr", )
        switch = BootstrapSwitch(id=Parameter("id_attr"))

    def switch_by_text(self, text):
        id_attr = self._get_attr_from_text("id", text)
        return self._bootstrap_switch(id_attr).switch

    @cached_property
    def selected_text(self):
        return [label for label in self.all_labels if self.switch_by_text(label).selected]

    def _values_to_remove(self, values):
        return list(set(self.selected_text) - set(values))

    def _values_to_add(self, values):
        return list(set(values) - set(self.selected_text))

    def fill(self, values):
        if set(values) == set(self.selected_text):
            return False
        else:
            for value in self._values_to_remove(values):
                self.switch_by_text(value).fill(False)
            for value in self._values_to_add(values):
                self.switch_by_text(value).fill(True)
            try:
                del self.selected_text
            except AttributeError:
                pass
            return True

    def read(self):
        return self.selected_text


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
        './tr/th[1]/input[contains(@class, "checkall")]',
        './/input[@id="masterToggle"]',
        './/th[1]/input[@id="check-all"]'
    ])
    SORTED_BY_LOC = '|'.join([
        # Old one
        './thead/tr/th[contains(@class, "sorting_asc") or contains(@class, "sorting_desc")]',
        # New one
        './thead/tr/th[./div/i[contains(@class, "fa-sort-")]]/a',
        './thead/tr/th[contains(@class, "ng-binding ng-scope")]'])
    SORTED_BY_CLASS_LOC = '|'.join([
        # Old one
        './thead/tr/th[contains(@class, "sorting_asc") or contains(@class, "sorting_desc")]',
        # New one
        './thead/tr/th/div/i[contains(@class, "fa-sort-")]'])
    SORT_LINK = './thead/tr/th[{}]'
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
        klass = self.browser.get_attribute('class', self.SORTED_BY_CLASS_LOC, parent=self)
        # We get two group matches and one of them will always be None, therefore empty filter
        # for filtering the None out
        try:
            return filter(
                None, re.search(r'sorting_(asc|desc)|fa-sort-(asc|desc)', klass).groups())[0]
        except IndexError:
            raise ValueError(
                'Could not figure out which column is used for sorting now. The class was {!r}'
                .format(klass))
        except AttributeError:
            raise TypeError('SORTED_BY_CLASS_LOC tag did not provide any class. Maybe fix Table?')

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
        fields_names = []
        for field in self:
            if self.browser.get_attribute('class', field[0]):
                fields_names.append(field[0].text)
        return fields_names

    def get_field(self, field_name):
        """Returns the table row or list of elements for rowspam case
                of the field with this name.
        Args:
            field_name: Name of the field (left column)

        Returns:
            An instance of :py:class:`VanillaRow` or list of :py:class:`WebElement`
        """
        rowspan_path = './tbody//td[contains(text(), {})]/following-sibling::td'.format(
            quote(field_name))
        try:
            rowspan_attribute = self.browser.get_attribute('rowspan', self.row((0, field_name))[0])
        except IndexError:
            raise NameError('Could not find field with name {!r}'.format(field_name))
        if not rowspan_attribute:
            return self.row((0, field_name))
        else:
            rowspan_image_element = self.browser.element('{}/*[self::i or self::img]'.format(
                rowspan_path), self)
            rowspan_child_class = rowspan_image_element.get_attribute('class')
            if not rowspan_child_class:
                rowspan_child_class = rowspan_image_element.get_attribute('alt')
            multiple_fields = self.browser.elements(
                './tbody//*[self::i or self::img][contains(@class|@alt, {})]/parent::td'.format(
                    quote(rowspan_child_class), self))
            return multiple_fields

    def get_text_of(self, field_name):
        """Returns the text of the field with this name.

        Args:
            field_name: Name of the field (left column)

        Returns:
            :py:class:`str`
        """
        fields = self.get_field(field_name)
        if isinstance(fields, (list, tuple)):
            return [field.text for field in fields]
        else:
            return fields[1].text

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


class NestedSummaryTable(SummaryTable):
    HEADER_IN_ROWS = './tbody/tr[1]/td'
    HEADERS = './tbody/tr[1]/td/strong'

    def __init__(self, parent, title, *args, **kwargs):
        SummaryTable.__init__(self, parent, title, *args, **kwargs)

    def _all_rows(self):
        for row_pos in range(1, len(self.browser.elements(self.ROWS, parent=self))):
            yield self.Row(self, row_pos)

    def read(self):
        return [{key: col.text for key, col in row} for row in self]


class StatusBox(Widget, ClickableMixin):
    card = Text(ParametrizedLocator('.//div[@pf-aggregate-status-card and (normalize-space'
                                    '(.//h2/a/span[contains(@class, '
                                    '"card-pf-aggregate-status-count")]/following::'
                                    'text())={@name|quote} or normalize-space(.//span'
                                    '[contains(@class, "card-pf-aggregate-status-title")]'
                                    '/text())={@name|quote})]'))

    def __init__(self, parent, name, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.name = name

    def click(self, *args, **kwargs):
        self.card.click(*args, **kwargs)

    @property
    def value(self):
        text = self.card.read()
        match = re.search(r'\d+', text)
        return int(match.group())

    def read(self):
        return {self.name: self.value}


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
        if isinstance(values, six.string_types):
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


class SSUIVerticalNavigation(VerticalNavigation):
    """The Patternfly Vertical navigation."""
    CURRENTLY_SELECTED = './/li[contains(@class, "active")]/a/span'


class SSUIInput(Input):

    locator = ParametrizedLocator('.//*[self::input and @uib-tooltip={@text|quote}]')

    def __init__(self, parent, text, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.text = text


class SSUIlist(Widget, ClickableMixin):
    """Represents the list of items like Services ,
    Orders or service catalogs in SSUI pages.
    """

    @ParametrizedView.nested
    class list(ParametrizedView):  # noqa
        PARAMETERS = ("item_name",)
        list_item = Text(
            ParametrizedLocator('.//div/span/*[normalize-space(.)={item_name|quote}]'))

        def list_click(self):
            """Clicks the list item with this name."""

            return self.list_item.click()

    def click_at(self, item_name):
        """Clicks the list item with this name.

        Args:
            item_name: Name of the item
        """

        return self.list(item_name).list_click()


class SSUIDropdown(Dropdown):
    """Represents the SSUI dropdown."""

    ROOT = ParametrizedLocator(
        './/span[contains(@class, "dropdown") and .//button[contains(@class, "dropdown-toggle")]'
        '/span[normalize-space(.)={@text|quote}]]')
    BUTTON_LOCATOR = './/button'
    ITEMS_LOCATOR = './ul/li/a'
    ITEM_LOCATOR = './/ul/li/a[normalize-space(.)={}]'

    def __init__(self, parent, text, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.text = text


class SSUIAppendToBodyDropdown(Dropdown):
    """This is a special dropdown where the dropdown options
       are appended to the body and not to the dropdown."""

    ITEMS_LOCATOR = '//ul[contains(@class, "dropdown-menu")]/li/a'
    ITEM_LOCATOR = '//ul[contains(@class, "dropdown-menu")]/li/a[normalize-space(.)={}]'

    def __init__(self, parent, text, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.text = text


class SSUIConfigDropdown(Dropdown):
    """This is a special dropdown where the dropdown options
       are appended to the body and not to the dropdown."""

    ROOT = ParametrizedLocator(
        './/button[@id={@text|quote}]')

    BUTTON_LOCATOR = '//button'
    ITEMS_LOCATOR = '//ul[contains(@class, "dropdown-menu")]/li/a'
    ITEM_LOCATOR = '//ul[contains(@class, "dropdown-menu")]/li/a[normalize-space(.)={}]'

    def __init__(self, parent, text, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.text = text


class SSUIPrimarycard(Widget, ClickableMixin):
    """Represents a primary card on dashboard like Total Service or Total Requests."""

    @ParametrizedView.nested
    class primary_card(ParametrizedView):  # noqa
        PARAMETERS = ("item_name",)
        card = Text(
            ParametrizedLocator('.//div[@class="ss-dashboard__card-primary__count"]/h2'
                                '[./following-sibling::h3[normalize-space(.)={item_name|quote}]]'))

        def card_click(self):
            """Clicks the primary card with this name."""

            return self.card.click()

        def card_count(self):
            """Gets the count displayed on card"""

            return self.browser.text(self.card)

    def __init__(self, parent, logger=None):
        Widget.__init__(self, parent, logger=logger)

    def click_at(self, item_name):
        """Clicks the card item with this name.

        Args:
            item_name: Name of the card
        """
        return self.primary_card(item_name).card_click()

    def get_count(self, item_name):
        """
        Returns the count displayed on UI.

        Args:
            item_name: Name of the card
        """
        return self.primary_card(item_name).card_count()

    @property
    def is_displayed(self):
        """Checks if Total service card is displayed"""

        return self.primary_card("Total Services").card.is_displayed


class SSUIAggregatecard(Widget, ClickableMixin):
    """Represents an aggregate card like Current Services or Retired services."""

    @ParametrizedView.nested
    class aggregate_card(ParametrizedView):  # noqa
        PARAMETERS = ("item_name",)
        card = Text(ParametrizedLocator(
                    './/div[@class="card-pf-body"]'
                    '/p[./preceding-sibling::h2[normalize-space(.)={item_name|quote}]]'
                    '/span[2]'))

        def card_click(self):
            """Clicks the primary card with this name."""

            return self.card.click()

        def card_count(self):
            """Gets the count displayed on card"""

            return self.browser.text(self.card)

    def __init__(self, parent, logger=None):
        Widget.__init__(self, parent, logger=logger)

    def click_at(self, item_name):
        """Clicks the card item with this name.

        Args:
            item_name: Name of the card
        """
        return self.aggregate_card(item_name).card_click()

    def get_count(self, item_name):
        """
        Returns the count displayed on UI.

        Args:
            item_name: Name of the card
        """
        return self.aggregate_card(item_name).card_count()


class SSUIServiceCatalogcard(Widget, ClickableMixin):
    """Represents an service catalog card in SSUI."""

    @ParametrizedView.nested
    class catalog_card(ParametrizedView):  # noqa
        PARAMETERS = ("item_name",)

        card = Text(ParametrizedLocator('.//div[@class="card-content"]/div'
                                        '/ss-card/h3[normalize-space(.)={item_name|quote}]'))

        def card_click(self):
            """Clicks the primary card with this name."""

            return self.card.click()

    def __init__(self, parent, logger=None):
        Widget.__init__(self, parent, logger=logger)

    def click_at(self, item_name):
        """Clicks the card item with this name.

        Args:
            item_name: Name of the card
        """
        return self.catalog_card(item_name).card_click()


class Notification(Widget, ClickableMixin):
    """Represent Notification drawer"""

    @ParametrizedView.nested
    class notification_drawer(ParametrizedView):  # noqa
        PARAMETERS = ("message",)
        notification_bell = Text('.//li/a[contains(@title, "notifications")]/i')
        events = Text(".//h4[contains(@class, 'panel-title')]")
        find_event = Text(ParametrizedLocator('.//div[contains(@class, "drawer-pf-notification")]'
                                              '/div/span'
                                              '[contains(normalize-space(.), {message|quote})]'))

        def click_bell(self):
            """Opens and closes the notification bell at the Nav bar"""
            self.notification_bell.click()

        def event_click(self):
            """Clicks the Event under Notification."""
            self.click_bell()
            self.events.click()
            self.find_event.click()
            # close events and bell
            self.events.click()
            self.click_bell()

    def __init__(self, parent, logger=None):
        Widget.__init__(self, parent, logger=logger)

    def dismiss(self):
        """Closes the notification window"""

        return self.notification_drawer().click_bell()

    def assert_message(self, message):
        """Finds the events in the notification drawer"""

        try:
            self.notification_drawer(message).event_click()
            return True
        except NoSuchElementException:
            return False


class DialogButton(Button):
    """Multiple buttons with same name are present in Dialog UI.
       So need to specify the div too.
    """
    def __locator__(self):
        return (
            './/div[@class="modal-footer"]/*[(self::a or self::button or'
            '(self::input and (@type="button" or @type="submit")))'
            ' and contains(@class, "btn") {}]'.format(self.locator_conditions))


class DragandDropElements(View):
    """Drag elements to a drop place."""
    @ParametrizedView.nested
    class dialog_element(ParametrizedView):  # noqa
        PARAMETERS = ("drag_item", "drop_item")

        dragged_element = ParametrizedLocator('.//*[@id="toolbox"]/div/dialog-editor-field-static'
                                              '/ul/li[normalize-space(.)={drag_item|quote}]')

        dropped_element = ParametrizedLocator('.//div[normalize-space(.)={drop_item|quote}]')

        @property
        def drag_div(self):
            return self.browser.element(self.dragged_element)

        @property
        def drop_div(self):
            return self.browser.element(self.dropped_element)

    def __init__(self, parent, logger=None):
        View.__init__(self, parent=parent, logger=logger)

    def drag_and_drop(self, dragged_widget, dropped_widget):
        dragged_widget_el = self.dialog_element(dragged_widget, dropped_widget).drag_div
        dropped_widget_el = self.dialog_element(dragged_widget, dropped_widget).drop_div
        self.browser.drag_and_drop(dragged_widget_el, dropped_widget_el)
        self.browser.plugin.ensure_page_safe()


class DialogBootstrapSwitch(BootstrapSwitch):
    """New dialog editor has different locator than BootstrapSwitch"""
    ROOT = ParametrizedLocator(
        './/div[./preceding-sibling::label[normalize-space(.)={@label|quote}]]'
        '/span/div/div[contains(@class, "bootstrap-switch-container")]//input')


class DragandDrop(View):

    def __init__(self, parent, logger=None):
        View.__init__(self, parent=parent, logger=logger)

    def drag_and_drop(self, dragged_widget, dropped_widget):
        self.browser.drag_and_drop(dragged_widget, dropped_widget)
        self.browser.plugin.ensure_page_safe()


class DialogElement(Widget, ClickableMixin):
    """Represents the element in new dialog editor"""

    @ParametrizedView.nested
    class element(ParametrizedView):  # noqa
        PARAMETERS = ("element_name", )

        ele_label = Text(ParametrizedLocator(
            './/dialog-editor-field/div[@class="form-group"]'
            '/label[normalize-space(.)={element_name|quote}]'))

        edit_icon = Text(ParametrizedLocator(
            './/div[contains(normalize-space(.), {element_name|quote})]'
            '/div/button/span/i[contains(@class, "pficon-edit")]'))

        def edit_icon_click(self):
            """Clicks the edit icon with this name."""
            wait_for(
                lambda: self.ele_label.is_displayed, delay=5, num_sec=30,
                message="waiting for element to be displayed"
            )
            self.ele_label.click()
            wait_for(
                lambda: self.edit_icon.is_displayed, delay=5, num_sec=30,
                message="waiting for element to be displayed"
            )
            return self.edit_icon.click()

    def edit_element(self, element_name):
        """Clicks the edit_icon_click.

        Args:
            element_name: Name of the element
        """
        return self.element(element_name).edit_icon_click()

    def drag_and_drop(self, dragged_widget, dropped_widget):
        dragged_widget_el = self.element(dragged_widget).drag_drop_div
        dropped_widget_el = self.element(dropped_widget).drag_drop_div
        self.browser.drag_and_drop(dragged_widget_el, dropped_widget_el)
        self.browser.plugin.ensure_page_safe()


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
        return re.search('(\d+)?-?(\d+)\s+of\s+(\d+)', text).groups()


class ReportDataControllerMixin(object):
    """
    This is helper mixin for several widgets which use Miq JS API
    """
    def _invoke_cmd(self, cmd, data=None):
        raw_data = {'controller': 'reportDataController', 'action': cmd}
        if data:
            raw_data['data'] = [data]
        json_data = json.dumps(raw_data)
        js_cmd = 'sendDataWithRx({data}); return ManageIQ.qe.gtl.result'.format(data=json_data)
        self.logger.info("executed command: {cmd}".format(cmd=js_cmd))
        # command result is always stored in this global variable
        self.browser.plugin.ensure_page_safe()
        result = self.browser.execute_script(js_cmd)
        self.browser.plugin.ensure_page_safe()
        return result

    def _call_item_method(self, method):
        raw_data = {'controller': 'reportDataController',
                    'action': 'get_item',
                    'data': [self.entity_id]}
        js_data = json.dumps(raw_data)
        js_cmd = ('sendDataWithRx({data}); '
                  'return ManageIQ.qe.gtl.result.{method}()').format(data=js_data, method=method)
        self.logger.info("executed command: {cmd}".format(cmd=js_cmd))
        self.browser.plugin.ensure_page_safe()
        result = self.browser.execute_script(js_cmd)
        self.browser.plugin.ensure_page_safe()
        return result

    def get_ids_by_keys(self, **keys):
        updated_keys = keys.copy()
        for key in updated_keys:
            # js api compares values in lower case but don't replace space with underscore
            updated_keys[key.replace('_', ' ')] = str(updated_keys.pop(key))

        raw_data = {'controller': 'reportDataController',
                    'action': 'query',
                    'data': [updated_keys]}
        js_cmd = ('sendDataWithRx({data}); '
                  'return ManageIQ.qe.gtl.result').format(data=json.dumps(raw_data))
        self.logger.info("executed command: {cmd}".format(cmd=js_cmd))
        self.browser.plugin.ensure_page_safe()
        result = self.browser.execute_script(js_cmd)
        self.browser.plugin.ensure_page_safe()
        try:
            return [int(eid['id']) for eid in result]
        except (TypeError, IndexError):
            return None


class JSPaginationPane(View, ReportDataControllerMixin):
    """ Represents Paginator Pane with js api provided by ManageIQ.

    The intention of this view is to use it as nested view on f.e. Infrastructure Providers page.
    """
    @property
    def is_displayed(self):
        # upstream sometimes shows old pagination page and sometime new one
        paginator = ("return $('#paging_div').length !== 0 || "
                     "document.getElementsByTagName('miq-pagination').length != 0")
        return self.browser.execute_script(paginator)

    @property
    def exists(self):
        return self.is_displayed

    def check_all(self):
        self._invoke_cmd('select_all', True)

    def uncheck_all(self):
        self._invoke_cmd('select_all', False)

    def sort(self, sort_by, ascending=True):
        # in order to change both sorting and direction, command has to be called twice
        data = {'columnName': sort_by, 'isAscending': ascending}
        self._invoke_cmd('set_sorting', data)

    @property
    def sorted_by(self):
        return self._invoke_cmd('get_sorting')

    @property
    def items_per_page(self):
        return self._invoke_cmd('get_items_per_page')

    def set_items_per_page(self, value):
        self._invoke_cmd('set_items_per_page', value)

    @property
    def cur_page(self):
        return self._invoke_cmd('get_current_page')

    @property
    def pages_amount(self):
        # this js call returns None from time to time. this is workaround until it is fixed in js
        return wait_for(self._invoke_cmd, ['get_pages_amount'], num_sec=10, fail_condition=None)[0]

    def next_page(self):
        self._invoke_cmd('next_page')

    def prev_page(self):
        self._invoke_cmd('previous_page')

    def first_page(self):
        self._invoke_cmd('first_page')

    def last_page(self):
        self._invoke_cmd('last_page')

    def go_to_page(self, value):
        self._invoke_cmd('go_to_page', value)

    @property
    def items_amount(self):
        return self._invoke_cmd('pagination_range')['total']

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
    def min_item(self):
        return self._invoke_cmd('pagination_range')['start']

    @property
    def max_item(self):
        return self._invoke_cmd('pagination_range')['end']

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

    def reset_selection(self):
        if self.is_displayed:
            self.check_all()
            self.uncheck_all()
            return True
        return False


class NonJSPaginationPane(View):
    """ Represents Paginator Pane with the following controls.

    The intention of this view is to use it as nested view on f.e. Infrastructure Providers page.
    """
    ROOT = '//div[@id="paging_div"]'

    check_all_items = Checkbox(id='masterToggle')
    sort_by = BootstrapSelect(id='sort_choice')
    items_on_page = BootstrapSelect(id='ppsetting')
    paginator = Paginator()

    @property
    def is_displayed(self):
        # there are cases when paging_div is shown but it is empty
        return (
            self.check_all_items.is_displayed or
            self.paginator.is_displayed and
            self.items_on_page.is_displayed
        )

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
        """Selects number of items to be displayed on page.
        Args:
            value: Ideally value is a positive int
        """
        try:
            int(value)
        except ValueError:
            raise ValueError("Value should be integer and not {}".format(value))

        if self.browser.product_version >= '5.8.2':
            items_text = str(value)
        else:
            items_text = '{} items'.format(value)
        self.items_on_page.select_by_visible_text(items_text)

    def _parse_pages(self):
        min_item, max_item, item_amt = self.paginator.page_info()

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
        return self.paginator.page_info()[2]

    @property
    def min_item(self):
        return self.paginator.page_info()[0]

    @property
    def max_item(self):
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

    def reset_selection(self):
        if self.is_displayed:
            self.check_all()
            self.uncheck_all()
            return True
        return False


def PaginationPane(*args, **kwargs):  # noqa
    parent = kwargs.get("parent")
    verpick_obj = VersionPick({
        Version.lowest(): NonJSPaginationPane(*args, **kwargs),
        '5.9': JSPaginationPane(*args, **kwargs),
    })
    return verpick_obj.pick(parent.browser.product_version) if parent else verpick_obj


class SSUIPaginator(Paginator):
    """ Represents Paginator control for SSUI."""

    PAGINATOR_CTL = './/ul[@class="pagination"]'
    CUR_PAGE_CTL = './li[3]/span/..'
    PAGE_BUTTON_CTL = './li[contains(@class, {})]/span'


class SSUIPaginationPane(NonJSPaginationPane):
    """ Represents Paginator Pane for SSUI."""

    ROOT = '//div[@class="pagination-footer"]'

    check_all_items = Checkbox(id='masterToggle')
    sort_by = BootstrapSelect(id='sort_choice')
    items_on_page = SSUIDropdown('items')
    paginator = SSUIPaginator()

    def set_items_per_page(self, value):
        """Selects number of items to be displayed on page.

        Args:
            value: value like 5 items or 10 items.
        """
        self.items_on_page.item_select(value)


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
    LABELS = ('.//*[(self::label or (self::div and @class="radio-inline")) '
              'and input[@type="radio"]]')
    BUTTON = './/input[@type="radio"]'

    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent=parent, logger=logger)
        self.locator = locator

    def __locator__(self):
        return self.locator

    def _get_parent_label(self, name):
        br = self.browser
        try:
            return next(btn for btn in br.elements(self.LABELS) if br.text(btn) == name)
        except StopIteration:
            raise NoSuchElementException("RadioButton {name} is absent on page".format(name=name))

    @property
    def button_names(self):
        return [self.browser.text(btn) for btn in self.browser.elements(self.LABELS)]

    @property
    def selected(self):
        names = self.button_names
        for name in names:
            bttn = self.browser.element(self.BUTTON, parent=self._get_parent_label(name))
            if ('ng-valid-parse' in self.browser.classes(bttn) or
                    bttn.get_attribute('checked') is not None):
                return name

        else:
            # radio button doesn't have any marks to make out which button is selected by default.
            # so, returning first radio button's name
            return names[0]

    def select(self, name):
        if self.selected != name:
            self.browser.element(self.BUTTON, parent=self._get_parent_label(name)).click()
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
    grid_button = Button(title='Grid View')
    tile_button = Button(title='Tile View')
    list_button = Button(title='List View')

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
        if self.is_displayed:
            return next(btn.title for btn in self._view_buttons if btn.active)
        else:
            return None

    def read(self):
        return self.selected

    @property
    def is_displayed(self):
        return self.grid_button.is_displayed


class DetailsToolBarViewSelector(View):
    """ represents toolbar's view selector control
        it is present on pages like Infra Providers Details page

    .. code-block:: python

        view_selector = View.nested(DetailsToolBarViewSelector)

        view_selector.select('Dashboard View')
        view_selector.selected
    """
    ROOT = './/div[contains(@class, "toolbar-pf-view-selector")]'
    summary_button = Button(title='Summary View')
    dashboard_button = Button(title='Dashboard View')

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
        if self.is_displayed:
            return next(btn.title for btn in self._view_buttons if btn.active)
        else:
            return None

    @property
    def is_displayed(self):
        # cloud provider detail page has empty view selector.
        # so, default is_displayed works wrong in such case
        return self.summary_button.is_displayed

    def read(self):
        return self.selected


class CompareToolBarMixin(View):
    """ It represents mixin for compare toolbar actions. """

    @property
    def _view_buttons(self):
        """It should be overridden as per concern nested class buttons. """
        pass

    def select(self, title):
        for button in self._view_buttons:
            if button.title == title:
                return button.click()
        else:
            raise ValueError("The Mode with title {title} isn't present".format(title=title))

    @property
    def selected(self):
        if self.is_displayed:
            return next(btn.title for btn in self._view_buttons if btn.active)
        else:
            return None

    def read(self):
        return self.selected


class CompareToolBarActionsView(View):
    """ represents compare toolbar's actions control
        it is present on pages like compare selected items and drift

    .. code-block:: python

        actions = View.nested(CompareToolBarActions)

        action.AttributeSelector.select('Attributes with different values')
        action.AttributeSelector.select.selected
    """

    ROOT = './/div[contains(@class, "toolbar-pf-actions")]'

    @View.nested
    class attribute_selector(CompareToolBarMixin):  # noqa
        all_values_button = Button(title="All attributes")
        diff_values_button = Button(title="Attributes with different values")
        same_values_button = Button(title="Attributes with same values")

        @property
        def _view_buttons(self):
            yield self.all_values_button
            yield self.diff_values_button
            yield self.same_values_button

    @View.nested
    class modes_selector(CompareToolBarMixin):  # noqa
        details_mode = Button(title="Details Mode")
        exists_mode = Button(title="Exists Mode")

        @property
        def _view_buttons(self):
            yield self.details_mode
            yield self.exists_mode

    @View.nested
    class views_selector(CompareToolBarMixin):  # noqa
        expanded_button = Button(title="Expanded View")
        compressed_button = Button(title="Compressed View")

        @property
        def _view_buttons(self):
            yield self.expanded_button
            yield self.compressed_button


class ReportToolBarViewSelector(View):
    """ represents toolbar's view selector control

    .. code-block:: python

        view_selector = View.nested(ReportToolBarViewSelector)

        view_selector.select('Graph View')
        view_selector.selected
    """
    ROOT = './/div[contains(@class, "toolbar-pf")]'
    graph_button = Button(title='Graph View')
    hybrid_button = Button(title='Hybrid View')
    tabular_button = Button(title='Tabular View')

    @property
    def _view_buttons(self):
        yield self.graph_button
        yield self.hybrid_button
        yield self.tabular_button

    def select(self, title):
        for button in self._view_buttons:
            if button.title == title:
                return button.click()
        else:
            raise ValueError("The view with title {title} isn't present".format(title=title))

    @property
    def selected(self):
        if self.is_displayed:
            return next(btn.title for btn in self._view_buttons if btn.active)
        else:
            return None

    def read(self):
        return self.selected

    @property
    def is_displayed(self):
        return self.graph_button.is_displayed


class AdvancedFilterSave(View):
    """ View for Advanced Filter save """
    expression_text = Text(
        locator='//label[contains(text(), "Search Expression")]/following-sibling::div')
    search_name_field = Input(id='search_name')
    global_search = Checkbox(id='search_type')
    save_filter_button = Button('Save')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.search_name_field.is_displayed and
            self.global_search.is_displayed
        )


class AdvancedFilterLoad(View):
    """ View for load Advanced Filter """
    filter_dropdown = BootstrapSelect(id='chosen_search')
    save_filter_button = Button('Load')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return self.filter_dropdown.is_displayed


class AdvancedFilterUserInput(View):
    """ View for Advanced Filter user input """
    USER_INPUT_FIELD = (
        '//div[@id="user_input_filter"]//div[contains(normalize-space(.), {})]/input')
    user_input_cancel = Button('Cancel')
    user_input_apply = Button(title='Apply the current filter (Enter)')
    # We have different close button for user input
    close_button = Text(
        locator='//div[@id="quicksearchbox"]//button[@data-dismiss="modal"]')

    @property
    def is_displayed(self):
        return self.user_input_apply.is_displayed


class AdvancedSearchView(View):
    """ Advanced Search View """
    import expression_editor as exp_editor
    search_exp_editor = exp_editor.ExpressionEditor()

    load_filter_button = Button('Load')
    apply_filter_button = Button('Apply')
    save_filter_button = Button('Save')
    delete_filter_button = Button('Delete')
    reset_filter_button = Button('Reset')
    close_button = Text(locator='//div[@id="advsearchModal"]//button[@data-dismiss="modal"]')

    save_filter_form = View.nested(AdvancedFilterSave)
    load_filter_form = View.nested(AdvancedFilterLoad)
    filter_user_input_form = View.nested(AdvancedFilterUserInput)

    @property
    def is_displayed(self):
        return (
            self.search_exp_editor.is_displayed or
            self.save_filter_form.is_displayed or
            self.load_filter_form.is_displayed or
            self.filter_user_input_form.is_displayed
        )


class Search(View):
    """ Represents search_text control """
    search_input = Input(id="search_text")
    search_button = Text("//div[@id='searchbox']//div[contains(@class, 'form-group')]"
                         "/*[self::a or (self::button and @type='submit')]")

    clear_button = Text(".//*[@id='searchbox']//div[contains(@class, 'clear') "
                        "and not(contains(@style, 'display: none'))]/div/button")
    filter_clear_button = Text('//a[contains(@href, "adv_search_clear")]')
    advanced_search_button = Button(title='Advanced Search')

    advanced_search_form = View.nested(AdvancedSearchView)

# ================================= Simple Search ====================================

    @property
    def has_quick_search_box(self):
        return self.search_input.is_displayed

    def clear_simple_search(self):
        """ Clear simple search field """
        if not self.is_empty:
            self.clear_button.click()
            self.search_button.click()

    def simple_search(self, text):
        """ Search text using simple search """
        self.search_input.fill(text)
        self.search_button.click()

    @property
    @logged(log_result=True)
    def is_empty(self):
        """ Checks if simple search field is emply """
        return not bool(self.search_input.value)


# ================================= Advanced Search ===============================
    @property
    def is_advanced_search_opened(self):
        """Checks whether the advanced search box is currently opened"""
        return self.advanced_search_form.is_displayed

    def reset_filter(self):
        """Clears the filter expression

            Returns: result of clicking reset when enabled(True),
                false when reset is button is disabled
        """
        view = self.advanced_search_form
        if not view.reset_filter_button.disabled:
            view.reset_filter_button.click()
            reset_result = True
        else:
            reset_result = False
        view.close_button.click()
        return reset_result

    def apply_filter(self):
        """ Applies an existing filter

            Returns: Apply button state, True - if active and clicked,
                False - disabled, or not visible
        """
        try:
            self.advanced_search_form.apply_filter_button.click()
            return True
        except NoSuchElementException:
            return False

    def delete_filter(self, cancel=False):
        """If possible, deletes the currently loaded filter

            Returns: Delet button state, True - if active and clicked,
                False - disabled, or not visible
        """
        try:
            self.advanced_search_form.delete_filter_button.click(handle_alert=not cancel)
            return True
        except NoSuchElementException:
            return False

    def save_filter(self, expression_program, save_name, global_search=False, apply_filter=False,
                    cancel=False):
        """Fill the filtering expression and save it

            Args:
                expression_program: the expression to be filled.
                save_name: Name of the filter to be saved with.
                global_search: Whether to check the Global search checkbox.
                apply_filter: Apply filter or not, default(False) not to apply
                cancel: Whether to cancel the save dialog without saving
            Returns: True - if fields where updated
        """
        self.open_advanced_search()
        self.advanced_search_form.search_exp_editor.fill(expression_program)
        self.advanced_search_form.save_filter_button.click()
        updated = self.advanced_search_form.save_filter_form.fill({
            'search_name_field': save_name,
            'global_search': global_search
        })
        if cancel:
            self.advanced_search_form.save_filter_form.cancel_button.click()
        elif updated:
            self.advanced_search_form.save_filter_form.save_filter_button.click()
            if apply_filter:
                self.apply_filter()
                self.close_advanced_search()
        return updated

    def load_filter(self, saved_filter=None, report_filter=None, fill_callback=None,
                    apply_filter=False, cancel_on_user_filling=False, cancel=False):
        """Load saved filter

            Args:
                saved_filter: `Choose a saved XYZ filter`
                report_filter: `Choose a XYZ report filter`
                apply_filter: Apply filter or not, default(False) not to apply
                cancel_on_user_filling: If True, user input form will be closed
                cancel: Whether to cancel the load dialog without loading
            Returns: True - if fields where updated
        """
        self.open_advanced_search()
        if self.advanced_search_form.load_filter_button.disabled:
            raise NoSuchElementException(
                'Load Filter button disabled, cannot load filter: {}'.format(saved_filter))
        assert saved_filter is not None or report_filter is not None, "At least 1 param required!"

        self.advanced_search_form.load_filter_button.click()
        # We apply it to the whole form but it will fill only one of the selects
        if saved_filter is not None:
            updated = self.advanced_search_form.load_filter_form.fill(
                {'filter_dropdown': saved_filter})
        else:
            updated = self.advanced_search_form.load_filter_form.fill(
                {'filter_dropdown': report_filter})
        if cancel:
            self.advanced_search_form.load_filter_form.cancel_button.click()
        elif updated:
            self.advanced_search_form.load_filter_form.save_filter_button.click()
            if apply_filter:
                self.apply_filter()
                self._process_user_filling(fill_callback, cancel_on_user_filling)
                self.close_advanced_search()
        return updated

    def advanced_search(self, expression_program, user_input=None, cancel_on_user_filling=False):
        """ Fill the filtering expression and apply it

            Args:
                expression_program: Expression to fill to the filter.
        """
        self.open_advanced_search()
        self.advanced_search_form.search_exp_editor.fill(expression_program)
        self.apply_filter()
        self._process_user_filling(user_input, cancel_on_user_filling)
        self.close_advanced_search()

    def _process_user_filling(self, user_input, cancel_on_user_filling=False):
        """ This function handles answering CFME's requests on user input.

        A `user_input` function is passed. If the box with user input appears, all requested
        inputs are gathered and iterated over. On each element the `user_input` function is
        called
        with 2 parameters: text which precedes the element itself to do matching, and the element.

        This function does not check return status after `user_input` call.

            Args:
                user_input: The function to be called on each user input.
        """
        user_input_form = self.advanced_search_form.filter_user_input_form
        wait_for(
            lambda: self.advanced_search_form.load_filter_button.is_displayed, fail_condition=True,
            num_sec=10, delay=2, message='Waiting for button became active')
        if isinstance(user_input, dict):
            for user_input_label, user_input_value in user_input.items():
                field_for_input = self.browser.element(
                    user_input_form.USER_INPUT_FIELD.format(quote(user_input_label)))
                field_for_input.send_keys(user_input_value)
            if cancel_on_user_filling:
                user_input_form.user_input_cancel.click()
            else:
                wait_for(
                    lambda: user_input_form.user_input_apply.is_displayed,
                    num_sec=10, delay=2, message='Waiting for button became active')
                user_input_form.user_input_apply.click()

    @property
    def is_advanced_search_possible(self):
        """Checks for advanced search possibility in the quadicon view"""
        return self.advanced_search_button.is_displayed

    @property
    def is_advanced_search_applied(self):
        """Checks whether any filter is in effect on quadicon view"""
        return self.filter_clear_button.is_displayed

    def open_advanced_search(self):
        """Make sure the advanced search box is opened. """
        if not self.is_advanced_search_opened:
            self.advanced_search_button.click()
            wait_for(lambda: self.is_advanced_search_opened, fail_condition=False,
                     num_sec=10, delay=2, message='Waiting for advanced search to open')

    def close_advanced_search(self):
        """Checks if the advanced search box is open and if it does, closes it."""
        if self.is_advanced_search_opened:
            # the reason for this check that both buttons() are present in DOM
            if self.advanced_search_form.close_button.is_displayed:
                self.advanced_search_form.close_button.click()
            else:
                self.advanced_search_form.filter_user_input_form.close_button.click()
            wait_for(lambda: self.is_advanced_search_opened, fail_condition=True,
                     num_sec=10, delay=2, message='Waiting for advanced search to close')

    def remove_search_filters(self):
        """If any filter is applied in the quadicon view, it will be disabled."""
        if self.is_advanced_search_applied:
            self.close_advanced_search()
            self.filter_clear_button.click()
        self.clear_simple_search()


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
        if isinstance(values, six.string_types):
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
    calendar = TextInput(locator='.//input[@class="form-control"]')
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
    ROOT = ParametrizedLocator('{@locator}')
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

    def __init__(self, parent, locator=None, logger=None):
        super(TimelinesChart, self).__init__(parent=parent, logger=logger)
        self.locator = locator or '//div[contains(@class, "timeline-container")]'

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
                    self.logger.debug('RAW events in get_events: %r', event_text)
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
        self.logger.debug('ALL events in get_events array: %r', events)
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

    @property
    def is_timelines(self):
        """method to check title text for base Timelines without overriding is_displayed"""
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


class BaseQuadIconEntity(ParametrizedView, ClickableMixin):
    """ represents QuadIcon entity. one of states entity can be in
    It is expected that some properties like "data" will be overridden in its children

    """
    PARAMETERS = ('entity_id',)
    ROOT = ParametrizedLocator('.//table[./tbody/tr/td/*[(self::a or self::span) and '
                               'substring(@href, string-length(@href)'
                               '-string-length("/{entity_id}")+1)="/{entity_id}"]]')
    LIST = '//dl[contains(@class, "tile")]/*[self::dt or self::dd]'
    label = Text(locator=ParametrizedLocator('./tbody/tr/td/*[(self::a or self::span) and '
                                             'substring(@href, string-length(@href)-'
                                             'string-length("/{entity_id}")+1)="/{entity_id}"]'))
    checkbox = Checkbox(locator='./tbody/tr/td/input[@type="checkbox"]')
    QUADRANT = './/div[@class="flobj {pos}72"]/*[self::p or self::img or self::div]'

    @property
    def is_checked(self):
        return self.checkbox.selected

    def check(self):
        return self.checkbox.fill(True)

    def uncheck(self):
        return self.checkbox.fill(False)

    @property
    def name(self):
        return self.browser.get_attribute('title', self.label)

    @property
    def data(self):
        """ every entity like QuadIcon/ListEntity etc displays some data,
        which is different for each entity type.
        This is property which should hold such data.
        To override this property in concrete classes.
        """
        return {}

    def read(self):
        return self.is_checked

    def fill(self, values):
        return self.check(values)

    @property
    def is_displayed(self):
        try:
            list_exists = self.browser.element(self.LIST).is_displayed()
        except NoSuchElementException:
            list_exists = False
        return not list_exists and super(BaseQuadIconEntity, self).is_displayed


class BaseTileIconEntity(ParametrizedView):
    """ represents Tile Icon entity. one of states entity can be in

    """
    PARAMETERS = ('entity_id',)
    ROOT = ParametrizedLocator('.//table[.//table[./tbody/tr/td/*[(self::a or self::span) and '
                               'substring(@href, string-length(@href)-'
                               'string-length("/{entity_id}")+1)="/{entity_id}"]]]')
    LIST = '//dl[contains(@class, "tile")]/*[self::dt or self::dd]'
    quad_icon = ParametrizedView.nested(BaseQuadIconEntity)

    @property
    def is_checked(self):
        return self.quad_icon(self.context['entity_id']).is_checked

    def check(self):
        return self.quad_icon(self.context['entity_id']).check()

    def uncheck(self):
        return self.quad_icon(self.context['entity_id']).uncheck()

    @property
    def name(self):
        return self.quad_icon(self.context['entity_id']).name

    @property
    def data(self):
        """ every entity like QuadIcon/ListEntity etc displays some data,
        which is different for each entity type.
        This is property which should hold such data.
        """
        quad_data = self.quad_icon(self.context['entity_id']).data
        br = self.browser
        # it seems we don't have list widget in other places.
        # so, this code just parses it, creates dict and adds it to quad icon dict
        els = [br.text(el) for el in br.elements(locator=self.LIST)]
        list_data = dict(zip(els[::2], els[1::2]))  # get first and second element and join them
        quad_data.update(list_data)
        return quad_data

    def read(self):
        return self.quad_icon(self.context['entity_id']).read()

    def fill(self, values):
        return self.quad_icon(self.context['entity_id']).fill()

    @property
    def is_displayed(self):
        try:
            return (super(BaseTileIconEntity, self).is_displayed and
                    self.browser.is_displayed(self.LIST))
        except NoSuchElementException:
            return False


class BaseListEntity(ParametrizedView, ClickableMixin):
    """ represents List entity. one of states entity can be in

    """
    PARAMETERS = ('entity_id',)
    ROOT = ParametrizedLocator('.//tr[contains(@onclick, "miqRowClick(\'{entity_id}\'")]')
    parent_table = Table(locator='./ancestor::table[1]')
    checkbox = Checkbox(locator='.//input[@type="checkbox"]')

    @property
    def is_checked(self):
        return self.checkbox.selected

    def check(self):
        return self.checkbox.fill(True)

    def uncheck(self):
        return self.checkbox.fill(False)

    @property
    def name(self):
        return self.data['name'] if 'name' in self.data else None

    @property
    def data(self):
        """ every entity like QuadIcon/ListEntity etc displays some data,
        which is different for each entity type.
        This is property which should hold such data.
        """
        br = self.browser
        col_names = [col_name for col_name in self.parent_table.headers]
        col_names = map(lambda c: c.replace(' ', '_').lower() if c else c, col_names)
        col_values = [br.text(val) for val in br.elements('./td', parent=self)]
        return dict(col for col in zip(col_names, col_values) if col[0] is not None)

    def read(self):
        return self.is_checked

    def fill(self, values):
        return self.check(values)


class NonJSBaseEntity(View):
    """ represents Proxy class which represents Entity despite of state it is in.
        it passes calls to concrete entity taking into account which entity type is displayed atm
    """
    quad_entity = BaseQuadIconEntity
    list_entity = BaseListEntity
    tile_entity = BaseTileIconEntity

    def __init__(self, parent, entity_id, name=None, logger=None):
        View.__init__(self, parent, logger=logger)
        self.entity_id = entity_id
        self._name = name

    def _get_existing_entity(self):
        for item in (self.quad_entity, self.tile_entity, self.list_entity):
            if item(entity_id=self.entity_id).is_displayed:
                return item(entity_id=self.entity_id)
        else:
            raise NoSuchElementException("Item {id} isn't found on page".format(id=self.entity_id))

    @property
    def name(self):
        # ugly hack for 5.8 to provide entity name even when it is not displayed on current page
        try:
            item = self._get_existing_entity()
            return item.name
        except NoSuchElementException:
            return self._name

    def __getattr__(self, name):
        if name.startswith('__'):
            return self.__dict__[name]

        item = self._get_existing_entity()
        return getattr(item, name)

    def __str__(self):
        return str(self.__repr__())

    def __repr__(self):
        try:
            return repr(self._get_existing_entity())
        except NoSuchElementException:
            return '< {c} name {n}, id {id} >'.format(c=self.__class__,
                                                      n=self.name or "",
                                                      id=self.entity_id or "")

    @property
    def is_displayed(self):
        try:
            self._get_existing_entity()
            return True
        except NoSuchElementException:
            return False


class JSBaseEntity(View, ReportDataControllerMixin):
    """ represents Entity, no matter what state it is in.
        It is implemented using ManageIQ JS API
    """
    QUADRANT = './/div[@class="flobj {pos}72"]/*[self::p or self::img or self::div]'

    def __init__(self, parent, entity_id, name=None, logger=None):
        View.__init__(self, parent, logger=logger)
        self.entity_id = entity_id
        self._name = name or self.name

    @property
    def is_checked(self):
        checked = self._call_item_method('is_selected')
        if checked is None:
            return False
        else:
            return checked

    @property
    def name(self):
        if self.is_displayed:
            return self.data['name'] if 'name' in self.data else None
        else:
            return getattr(self, '_name', None)

    def check(self):
        self._call_item_method('select')

    def uncheck(self):
        self._call_item_method('unselect')

    def click(self):
        self._call_item_method('click')

    @property
    def data(self):
        """ every entity like QuadIcon/ListEntity etc displays some data,
        which is different for each entity type.
        This is property which should hold such data.
        """
        data = self._invoke_cmd('get_item', self.entity_id)['item']
        cells = data.pop('cells')
        cells = {str(key).replace(' ', '_').lower(): value for key, value in cells.items()}
        data = {str(key).replace(' ', '_').lower(): value for key, value in data.items()}
        data.update(cells)
        return data

    def read(self):
        return self.is_checked

    def fill(self, values):
        if values:
            self.check()
        else:
            self.uncheck()

    @property
    def is_displayed(self):
        try:
            return self._invoke_cmd('is_displayed', self.entity_id)
        except WebDriverException:
            # there is sometimes an exception if such entity is not displayed
            return False


class EntitiesConditionalView(View, ReportDataControllerMixin):
    """ represents Entities view with regard to view selector state

    """
    elements = '//tr[./td/div[@class="quadicon"]]/following-sibling::tr/td/a'
    title = Text('//div[@id="main-content"]//h1')
    search = View.nested(Search)
    paginator = PaginationPane()

    @property
    def _current_page_elements(self):
        elements = []
        if self.browser.product_version < '5.9':
            br = self.browser
            for el in br.elements(self.elements):
                el_id = int(br.get_attribute('href', el).split('/')[-1])
                el_name = br.get_attribute('title', el)
                elements.append({'name': el_name, 'entity_id': el_id})
        else:
            entities = self._invoke_cmd('get_all_items')
            for entity in entities:
                elements.append({'name': entity['item']['cells']['Name'],
                                 'entity_id': entity['item']['id']})
        return elements

    @property
    def entity_ids(self):
        return [el['entity_id'] for el in self._current_page_elements]

    @property
    def entity_names(self):
        """ looks for entities and extracts their names

        Returns: all current page entities
        """
        return [el['name'] for el in self._current_page_elements]

    def get_id_by_name(self, name):
        for el in self._current_page_elements:
            if el['name'] == name:
                return el['entity_id']
        return None

    def get_entities_by_keys(self, **keys):
        # some fields aren't available in Tile or Grid View.
        # So, we decided to switch to List View mode if several keys are passed
        # btw, it isn't necessary in 5.9+
        found_entities = []
        if self.browser.product_version < '5.9':
            # todo: fix this ugly hack somehow else
            view_selector = getattr(self.parent.parent.toolbar, 'view_selector', None)
            if view_selector and view_selector.selected != 'List View':
                view_selector.select('List View')

            if type(self).__name__ in ('GridView', 'TileView'):
                elements = self.parent.entities._current_page_elements
            else:
                elements = self._current_page_elements

            for el in elements:
                entity = self.parent.entity_class(parent=self, entity_id=el['entity_id'],
                                                  name=el['name'])
                for key, value in keys.items():
                    try:
                        if entity.data[key] != str(value):
                            break
                    except KeyError:
                        break
                else:
                    found_entities.append(entity)
        else:
            entity_id = keys.pop('entity_id', None)
            if entity_id:
                found_entities.append(self.parent.entity_class(parent=self, entity_id=entity_id))
            elif 'id' in keys:
                # it turned out that there are some views which have entities with internal id
                # which override entity id in JS code. this is workaround for such case
                elements = self._current_page_elements
                for el in elements:
                    entity = self.parent.entity_class(parent=self, entity_id=el['entity_id'])
                    for key, value in keys.items():
                        try:
                            if entity.data[key] != str(value):
                                break
                        except KeyError:
                            break
                    else:
                        found_entities.append(entity)
            else:
                entities = [self.parent.entity_class(parent=self, entity_id=eid)
                            for eid in self.get_ids_by_keys(**keys)]
                found_entities.extend(entities)
        return found_entities

    @property
    def all_entity_names(self):
        """Gets all entity names from all pages by default"""
        # get_all uses self.entity_names, which handles versioned name query
        return [e.name for e in self.get_all(surf_pages=True)]

    def get_all(self, surf_pages=False):
        """ obtains all entities like QuadIcon displayed by view
        Args:
            surf_pages (bool): current page entities if False, all entities otherwise

        Returns: all entities (QuadIcon/etc.) displayed by view
        """
        if not surf_pages:
            return [self.parent.entity_class(parent=self, entity_id=el['entity_id'],
                                             name=el['name']) for el in self._current_page_elements]
        else:
            entities = []
            for _ in self.paginator.pages():
                entities.extend([self.parent.entity_class(parent=self, entity_id=el['entity_id'],
                                                          name=el['name'])
                                for el in self._current_page_elements])
            return entities

    def get_entity(self, surf_pages=False, use_search=False, **keys):
        """ obtains one entity matched to by_name and stops on that page
        Args:
            keys: only entity which matches to keys will be returned
            surf_pages (bool): current page entity if False, all entities otherwise
            use_search (bool): it filters out all entities except entity with name passed in keys

        Returns: matched entity (QuadIcon/etc.)
        """
        if use_search and 'name' in keys:
            self.search.clear_simple_search()
            self.search.simple_search(text=keys['name'])

        for _ in self.paginator.pages():
            if len(keys) == 1 and 'name' in keys:
                entity_id = self.get_id_by_name(name=keys['name'])
            elif len(keys) == 1 and 'entity_id' in keys:
                entity_id = keys['entity_id']
            else:
                entity_id = None
                try:
                    return self.get_entities_by_keys(**keys)[0]
                except IndexError:
                    pass

            if entity_id:
                return self.parent.entity_class(parent=self, entity_id=entity_id)

            if not surf_pages:
                raise ItemNotFound("Entity {keys} isn't found on this page".format(keys=keys))
        else:
            raise ItemNotFound("Entity {keys} isn't found on this page".format(keys=keys))

    def get_first_entity(self):
        """ obtains first entity on page and returns it
        raises exception if no entities were found

        Returns: matched entity (QuadIcon/etc.)
        """
        for entity_id in self.entity_ids:
            return self.parent.entity_class(parent=self, entity_id=entity_id)

        raise ItemNotFound("No Entities found on this page")

    def apply(self, func, conditions, surf_pages=False):
        """ looks for entities matching to conditions and applies passed func
        :param func:  function to apply
        :param conditions: entities should match to
        :param surf_pages: current page entities if False, all entities otherwise
        :return: list of entities

        Ex:
            from cfme.infrastructure.virtual_machines import Vm
            view = navigate_to(Vm, 'All')
            entities = view.entities.apply(func=lambda e: e.check(),
                                           conditions=[{'name': 'cu-24x7'},
                                                       {'name': 'env-win81-ie11'},
                                                       {'name': 'nachandr-59013-cback001'}])
        """

        if isinstance(conditions, dict):
            conditions = [conditions]
        elif isinstance(conditions, (list, tuple)):
            conditions = conditions[:]
        else:
            raise ValueError('Wrong conditions passed')

        def apply_to_current_page(conditions):
            for keys in conditions:
                entities = self.get_entities_by_keys(**keys)
                map(func, entities)
                return entities

        all_found_entities = []
        if not surf_pages:
            all_found_entities.extend(apply_to_current_page(conditions))
        else:
            for _ in self.paginator.pages():
                all_found_entities.extend(apply_to_current_page(conditions))
        return all_found_entities


class BaseEntitiesView(View):
    """
    should represent the view with different entities like providers
    """
    @property
    def entity_class(self):
        if self.browser.product_version < '5.9':
            return NonJSBaseEntity
        else:
            return JSBaseEntity

    entities = ConditionalSwitchableView(reference='parent.toolbar.view_selector',
                                         ignore_bad_reference=True)

    @entities.register('Grid View', default=True)
    class GridView(EntitiesConditionalView):
        pass

    @entities.register('List View')
    class ListView(EntitiesConditionalView):
        elements = Table(locator='//div[@id="gtl_div"]//table')

        @property
        def entity_names(self):
            """ looks for entities and extracts their names

            Returns: all current page entities
            """
            try:
                return [row.name.text for row in self.elements.rows()]
            except NoSuchElementException:
                return []

        @property
        def _current_page_elements(self):
            elements = []
            if self.browser.product_version < '5.9':
                br = self.browser
                for row in self.elements.rows():
                    # ex: miqRowClick('2', '/ems_infra/', false); return false;
                    attr = br.get_attribute('onclick', row)
                    el_id = int(re.search("miqRowClick\('(\d+)", attr).group(1))
                    el_name = row.name.text if getattr(row, 'name', None) else ''
                    elements.append({'name': el_name, 'entity_id': el_id})
            else:
                entities = self._invoke_cmd('get_all_items')
                for entity in entities:
                    elements.append({'name': entity['item']['cells'].get('Name', None),
                                     'entity_id': entity['item']['id']})
            return elements

    @entities.register('Tile View')
    class TileView(EntitiesConditionalView):
        pass


class DashboardWidgetsPicker(View):
    """Represents widgets picker in Dashboard editing screen (Cloud Intel/Reports/Dashboards).

    Args:
        id (str): id attribute of the root div
    """

    ROOT = ParametrizedLocator(".//div[@id={@id|quote}]")
    select = BootstrapSelect("widget")

    def __init__(self, parent, id, logger=None):
        View.__init__(self, parent=parent, logger=logger)
        self.id = id

    @View.nested
    class dashboard_widgets(ParametrizedView):  # noqa
        PARAMETERS = ("title", )
        ALL_WIDGETS = ".//div[starts-with(@id, 'w_')]"
        DIV = ParametrizedLocator(".//div[contains(@title, {title|quote})]")
        remove_link = Text(ParametrizedLocator(".//div[contains(@title, {title|quote})]//a/i"))

        def remove(self):
            self.remove_link.click()

        @property
        def div(self):
            return self.browser.element(self.DIV)

        @classmethod
        def all(cls, browser):
            return [
                (e.get_attribute("title").split('"')[1], ) for
                e in browser.elements(cls.ALL_WIDGETS)
            ]

    def add_dashboard_widget(self, widget):
        self.select.fill(widget)

    def remove_dashboard_widget(self, widget):
        self.dashboard_widgets(widget).remove()

    @property
    def all_dashboard_widgets(self):
        widgets = list(self.dashboard_widgets)
        if widgets:
            return [self.browser.text(widget.div) for widget in widgets]
        else:
            return []

    def _values_to_remove(self, values):
        return list(set(self.all_dashboard_widgets) - set(values))

    def _values_to_add(self, values):
        return list(set(values) - set(self.all_dashboard_widgets))

    def fill(self, values):
        if isinstance(values, six.string_types):
            values = [values]
        if set(values) == set(self.all_dashboard_widgets):
            return False
        else:
            values_to_remove = self._values_to_remove(values)
            values_to_add = self._values_to_add(values)
            for value in values_to_remove:
                self.remove_dashboard_widget(value)
            for value in values_to_add:
                self.add_dashboard_widget(value)
            return True

    def drag_and_drop(self, dragged_widget, dropped_widget):
        dragged_widget_el = self.dashboard_widgets(dragged_widget).div
        dragged_middle = self.browser.middle_of(dragged_widget_el)
        dropped_middle = self.browser.middle_of(self.dashboard_widgets(dropped_widget).div)
        drop_x = dropped_middle.x
        # In order to perform a successful drag and drop we should drop a dragged widget a bit above
        # or below of the dropped widget center. If the dragged widget is above of the dropped one
        # we should add a small delta to "y" coordinate of the dropped widget middle, otherwise that
        # delta should be deducted.
        drop_y = dropped_middle.y + math.copysign(5, dropped_middle.y - dragged_middle.y)
        self.browser.drag_and_drop_to(dragged_widget_el, to_x=drop_x, to_y=drop_y)
        self.browser.plugin.ensure_page_safe()

    def read(self):
        return self.all_dashboard_widgets


class MenuShortcutsPicker(View):
    """Represents shortcut picker in Menu Widget editing screen
    (Cloud Intel/Reports/Dashboard Widgets/Menus).

    Args:
        id (str): id attribute of the root div
        select_id (str): id attribute for BootstrapSelect
        names_locator (str): xpath for all elements with shortcuts names
    """

    ROOT = ParametrizedLocator(".//div[@id={@id|quote}]")
    select = BootstrapSelect(Parameter("@select_id"))

    def __init__(self, parent, id, select_id, names_locator=None, logger=None):
        View.__init__(self, parent=parent, logger=logger)
        self.id = id
        self.select_id = select_id
        self.names_locator = names_locator

    @ParametrizedView.nested
    class shortcut(ParametrizedView):  # noqa
        PARAMETERS = ("number",)
        alias = Input(name=ParametrizedString("shortcut_desc_{number}"))
        remove_button = Text(ParametrizedLocator(".//a[@id=s_{@number|quote}_close]"))

        def fill(self, alias):
            self.alias.fill(alias)

        def remove(self):
            self.remove_button.click()

    @property
    def all_elements(self):
        return self.browser.elements(self.names_locator)

    def add_shortcut(self, shortcut, alias):
        # We need to get all options from the dropdown before picking
        mapping = self.mapping
        self.select.fill(shortcut)
        if shortcut != alias:
            self.shortcut(mapping[shortcut]).fill(alias)

    @cached_property
    def mapping(self):
        return {option.text: option.value for option in self.select.all_options}

    @property
    def all_shortcuts(self):
        if self.all_elements:
            return [shortcut.get_attribute("value") for shortcut in self.all_elements]
        else:
            return []

    def clear(self):
        for el in self.browser.elements(".//a[@title='Remove this Shortcut']"):
            self.browser.click(el)

    def fill(self, values):
        dict_values = None
        if isinstance(values, six.string_types):
            values = [values]
        if isinstance(values, dict):
            dict_values = values
            values = values.values()
        if set(values) == set(self.all_shortcuts):
            return False
        else:
            self.clear()
            if dict_values is not None:
                dict_values_to_add = dict_values
            else:
                dict_values_to_add = {value: value for value in values}
            for shortcut, alias in dict_values_to_add.iteritems():
                self.add_shortcut(shortcut, alias)
            return True

    def read(self):
        return self.all_shortcuts


class DynamicTable(VanillaTable):
    """Extend the widget.Table class to implement row_add for dynamic tables with an 'Actions'
    column.
    In these tables, the top or bottom row can be clicked to add a new row, and when it is
    clicked the row is replaced (top or bottom) with a row containing fillable widgets.

    When the row is saved, it is moved to the bottom of the table. This behavior is specifc to
    some MIQ dynamic tables.

    Args:
        action_row: index of the action row, generally 0 or -1, defaults to 0

        See Widgetastic.widget.Table for more arguments
    """

    def __init__(self, *args, **kwargs):
        self.action_row = kwargs.pop('action_row', 0)  # pull this off and pass the rest up
        super(DynamicTable, self).__init__(*args, **kwargs)

    def row_add(self):
        """Use the action-cell column widget to add a row

        Clicks on the row directly, not the action button

        Returns:
            int positive row index of the action row where the new widgets should be displayed
        """
        # convert action_row into a positive index
        if self.action_row >= 0:
            pos_action_index = self.action_row
        else:
            pos_action_index = self._process_negative_index(nindex=self.action_row)

        try:
            self[pos_action_index].click()
        except IndexError:  # self.action_row must have been None
            raise DynamicTableAddError('DynamicTable action_row index "{}" not found in table'
                                       .format(self.action_row))
        return pos_action_index

    def row_save(self, row=None):
        """Save the row, assuming attributized columns includes 'actions'

        Implements behavior of AnalysisProfile type tables, where the row is moved to the bottom
        on save

        Returns:
            int row index of the last row in the table
        """
        try:
            self[row or self.action_row].actions.click()
        except IndexError:  # self.action_row must have been None
            raise DynamicTableAddError('DynamicTable action_row index "{}" not found in table'
                                       .format(self.action_row))
        return self._process_negative_index(nindex=-1)  # use process_negative_index to get last row


class FolderManager(Widget):
    """ Represents the folder manager in Edit Report Menus screen
    (Cloud Intel/Reports/Edit Report Menus).

    """
    ROOT = ParametrizedLocator('{@locator}')

    top_button = Button(title="Move selected folder top")
    up_button = Button(title="Move selected folder up")
    down_button = Button(title="Move selected folder down")
    bottom_button = Button(title="Move selected folder to bottom")
    delete_button = Button(title="Delete selected folder and its contents")
    add_button = Button(title="Add subfolder to selected folder")

    commit_button = Button("Commit")
    discard_button = Button("Discard")

    _fields = ".//div[@id='folder_grid']/div/div/div"
    _field = ".//div[@id='folder_grid']/div/div/div[normalize-space(.)={folder}]"

    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.locator = locator

    class _BailOut(Exception):
        pass

    @classmethod
    def bail_out(cls):
        """If something gets wrong, you can use this method to cancel editing of the items in
        the context manager.
        Raises: :py:class:`FolderManager._BailOut` exception
        """
        raise cls._BailOut()

    def commit(self):
        self.commit_button.click()

    def discard(self):
        self.discard_button.click()

    @property
    def _all_fields(self):
        return self.browser.elements(self._fields)

    @property
    def fields(self):
        """Returns all fields' text values"""
        return [el.text for el in self._all_fields]

    @property
    def selected_field_element(self):
        """Return selected field's element.
        Returns: :py:class:`WebElement` if field is selected, else `None`
        """
        selected_fields = [el for el in self._all_fields if "active" in el.get_attribute("class")]
        if len(selected_fields) == 0:
            return None
        else:
            return selected_fields[0]

    @property
    def selected_field(self):
        """Return selected field's text.
        Returns: :py:class:`str` if field is selected, else `None`
        """
        if self.selected_field_element is None:
            return None
        else:
            return self.selected_field_element.text.encode("utf-8").strip()

    def add(self, subfolder):
        self.add_subfolder()
        wait_for(lambda: self.selected_field_element is not None, num_sec=5, delay=0.1)
        self.browser.double_click(self.selected_field_element, wait_ajax=False)
        self.browser.handle_alert(prompt=subfolder)

    def select_field(self, field):
        """Select field by text.
        Args:
            field: Field text.
        """
        self.browser.click(self.browser.element(self._field.format(folder=quote(field))))
        wait_for(lambda: self.selected_field is not None, num_sec=5, delay=0.1)

    def has_field(self, field):
        """Returns if the field is present.
        Args:
            field: Field to check.
        """
        try:
            self.select_field(field)
            return True
        except (NoSuchElementException, TimedOutError):
            return False

    def delete_field(self, field):
        self.select_field(field)
        self.delete_button.click()

    def move_first(self, field):
        self.select_field(field)
        self.top_button.click()

    def move_last(self, field):
        self.select_field(field)
        self.bottom_button.click()

    def clear(self):
        for field in self.fields:
            self.delete_field(field)

    def read(self):
        return self.fields


class ViewButtonGroup(Widget):
    """This widget represents one of the button groups used in My Settings to set views.

    Args:
        title: Title of the section where the group is located.
        name: Name in front of the button group.
    """
    ROOT = ParametrizedLocator(
        './/fieldset[./h3[normalize-space(.)={@title|quote}]]'
        '/div[./label[normalize-space(.)={@name|quote}]]')
    ALL_ITEMS = './div/ul/li//i'
    ACTIVE_ITEM = './div/ul/li[contains(@class, "active")]//i'
    PARTICULAR_ITEM = (
        './div/ul/li//i[normalize-space(@title)={name} or normalize-space(@alt)={name}]')

    def __init__(self, parent, title, name, logger=None):
        super(ViewButtonGroup, self).__init__(parent, logger=logger)
        self.title = title
        self.name = name

    @property
    def buttons(self):
        """Return a list of all buttons' text"""
        result = []
        for item_element in self.browser.elements(self.ALL_ITEMS):
            result.append(
                self.browser.get_attribute('alt', item_element) or
                self.browser.get_attribute('title', item_element))
        return result

    @property
    def active_button(self):
        """Returns the currently active button."""
        selected = self.browser.element(self.ACTIVE_ITEM)
        return self.browser.get_attribute('title', selected)

    def select_button(self, name):
        """Selects a button by its alt/title.

        Args:
            name: ``alt`` or ``title`` of the button.
        """
        button_element = self.browser.element(self.PARTICULAR_ITEM.format(name=quote(name)))
        self.browser.click(button_element)

    def read(self):
        return self.active_button

    def fill(self, value):
        if self.active_button == value:
            return False
        self.select_button(value)
        return True


class BaseNonInteractiveEntitiesView(View, ReportDataControllerMixin):
    """Represents Quadicons appearing in views like Edit Tags, etc.

    """
    elements = ('//tr[./td/div[@class="quadicon"]]/following-sibling::tr/td/*[self::a or '
                'self::span]')

    @property
    def _current_page_elements(self):
        elements = []
        if self.browser.product_version < '5.9':
            br = self.browser
            for el in br.elements(self.elements):
                el_id = int(br.get_attribute('href', el).split('/')[-1])
                el_name = br.get_attribute('title', el)
                elements.append({'name': el_name, 'entity_id': el_id})
        else:
            entities = self._invoke_cmd('get_all_items')
            for entity in entities:
                elements.append({'name': entity['item']['cells']['Name'],
                                 'entity_id': entity['item']['id']})
        return elements

    @property
    def entity_ids(self):
        return [el['entity_id'] for el in self._current_page_elements]

    @property
    def entity_names(self):
        """ looks for entities and extracts their names

        Returns: all current page entities
        """
        return [el['name'] for el in self._current_page_elements]

    def get_id_by_name(self, name):
        for el in self._current_page_elements:
            if el['name'] == name:
                return el['entity_id']
        return None

    def get_entity_by_keys(self, **keys):
        if self.browser.product_version < '5.9':
            for el in self._current_page_elements:
                entity = self.entity_class(parent=self, entity_id=el['entity_id'], name=el['name'])
                for key, value in keys.items():
                    try:
                        if entity.data[key] != str(value):
                            break
                    except KeyError:
                        break
                else:
                    return entity
        else:
            entity_id = keys.pop('entity_id', None)
            if entity_id:
                return self.entity_class(parent=self, entity_id=entity_id)
            else:
                try:
                    return self.entity_class(parent=self, entity_id=self.get_ids_by_keys(**keys)[0])
                except IndexError:
                    pass
        return None

    @property
    def entity_class(self):
        if self.browser.product_version < '5.9':
            return NonJSBaseEntity
        else:
            return JSBaseEntity

    def get_all(self):
        """ obtains all entities like QuadIcon displayed by view

        Returns: all entities (QuadIcon/etc.) displayed by view
        """
        return [self.entity_class(parent=self, entity_id=eid) for eid in self.entity_ids]

    def get_entity(self, **keys):
        """ obtains one entity matched to some of keys
        raises exception several entities were found
        Args:
            keys: only entity which match to keys will be returned

        Returns: matched entities (QuadIcon/etc.)
        """
        if len(keys) == 1 and 'name' in keys:
            entity_id = self.get_id_by_name(name=keys['name'])
        elif len(keys) == 1 and 'entity_id' in keys:
            entity_id = keys['entity_id']
        else:
            entity_id = None
            entity = self.get_entity_by_keys(**keys)
            if entity:
                return entity

        if entity_id:
            return self.entity_class(parent=self, entity_id=entity_id)

        raise ItemNotFound("Entity {keys} isn't found on this page".format(keys=keys))

    def get_first_entity(self):
        """ obtains first entity

        Returns: matched entity (QuadIcon/etc.)
        """
        for entity_id in self.entity_ids:
            return self.entity_class(parent=self, entity_id=entity_id)

        raise ItemNotFound("No Entities found on this page")


class FonticonPicker(Widget):
    """Widget, designed for the icon picker.

    Works around the need to open the modal by executing some JavaScript interacting with the
    relevant Angular scope.

    Kudos to @himdel for getting me the right steps to do this.

    Args:
        name: Value of the ``input-name`` of ``miq-fonticon-picker``.
    """
    ROOT = ParametrizedLocator('.//miq-fonticon-picker[@input-name={@name|quote}]/*')

    def __init__(self, parent, name, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.name = name

    @property
    def value(self):
        selected = self.browser.execute_script(jsmin('''
            var scope = angular.element(arguments[0]).scope();
            return scope.$ctrl.selected;
        '''), self.browser.element(self))
        if not selected:
            return None
        return selected.rsplit(' ', 1)[-1] or None

    def read(self):
        return self.value

    def fill(self, value):
        if value == self.value:
            return False

        self.browser.execute_script(jsmin('''
            var scope = angular.element(arguments[0]).scope();
            scope.$ctrl.selected = 'fa ' + arguments[1];
            scope.$apply();
            scope.$ctrl.iconChanged({ selected: scope.$ctrl.selected });
        '''), self.browser.element(self), value)
        self.browser.plugin.ensure_page_safe()
        return True


class PotentiallyInvisibleTab(Tab):
    """Tab, that can be potentially invisible."""
    def select(self):
        if not self.is_displayed:
            self.logger.info('Tab not present and ignoring turned on - not touching the tab.')
            return
        return super(PotentiallyInvisibleTab, self).select()


class Splitter(Widget):
    """ Represents the frame splitter

    """

    left_button = Text("//span[@class='fa fa-angle-left']")
    right_button = Text("//span[@class='fa fa-angle-right']")

    def __init__(self, parent, logger=None):
        Widget.__init__(self, parent, logger=logger)

    def pull_left(self):
        if self.left_button.is_displayed:
            self.left_button.click()

    def pull_right(self):
        if self.right_button.is_displayed:
            self.right_button.click()

    def reset(self):
        for _ in range(4):
            self.pull_left()
        for _ in range(2):
            self.pull_right()


class DriftComparison(Widget):
    """Represents Drift Analysis Sections Comparison Table

        Args:
        locator: Locator for Drift Analysis Sections Comparison Table.
    """

    ROOT = ParametrizedLocator('{@locator}')
    ALL_SECTIONS = ".//tr[@data-exp-id]"
    CELLS = "./td//i"
    SECTION = ".//th[contains(text(), {})]/ancestor::tr"
    INDENT = ".//tr[contains(@data-parent, {id})]"

    def __init__(self, parent, locator, logger=None):
        Widget.__init__(self, parent, logger=logger)
        self.locator = locator

    @property
    def available_sections(self):
        """ All element for drift sections """
        return [section for section in self.browser.elements(self.ALL_SECTIONS, parent=self)]

    def section_element(self, drift_section):
        """ Element for drift section
            Args:
                drift_section: name for section(Can be partial text)
            Return:
                Section web element
        """
        return self.browser.element(self.SECTION.format(quote(drift_section)))

    def is_changed(self, drift_section):
        """ Check if section was changed
            Args:
                drift_section: name for section(Can be partial text)
            Return:
                bool: True if changed, otherwise False
        """
        cells = self.browser.elements(
            self.CELLS, parent=self.section_element(drift_section))
        attrs = [self.browser.get_attribute("class", cell) for cell in cells]
        return "drift-delta" in attrs

    def parent_id(self, drift_section):
        """
            Args:
                drift_section: name for section(Can be partial text)
            Return:
                int: id numder
        """
        elements = self.browser.elements("{}/following-sibling::tr".format(
            self.SECTION.format(quote(drift_section))), parent=self)
        return self.browser.get_attribute("data-parent", elements[0])

    def section_attributes(self, drift_section):
        """ Children elements under section
            Args:
                drift_section: name for section(Can be partial text)
            Return:
                list: attributes elements
        """
        att_id = self.parent_id(drift_section)
        return [child for child in self.browser.elements(self.INDENT.format(
            id=quote(att_id)), parent=self)]

    def check_section_attribute_availability(self, drift_section):
        """Check if at least one attribute is available in the DOM
            Can be used to check drift attributes options for section
            Args:
                drift_section: name for section(Can be partial text)
            Return:
                bool: True if available, otherwise False
        """
        try:
            self.section_attributes(drift_section)
            return True
        except AttributeError:
            return False

    @property
    def section_values(self):
        return {section.text: self.is_changed(section.text) for section in self.available_sections}

    def read(self):
        return self.section_values
