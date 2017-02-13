# -*- coding: utf-8 -*-
import re
from datetime import date
from jsmin import jsmin
from selenium.common.exceptions import WebDriverException
from math import ceil
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
    Text,
    TextInput,
    Checkbox,
    ParametrizedView,
    WidgetDescriptor,
    do_not_read_this_widget)
from widgetastic.utils import ParametrizedLocator, Parameter
from widgetastic.xpath import quote
from widgetastic_patternfly import (
    Accordion as PFAccordion, CandidateNotFound, BootstrapTreeview, Button, Input, BootstrapSelect)
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

        return self.browser.element('./span/a', parent=node)

    def click_path(self, *path, **kwargs):
        """ Exposes a path and then clicks it.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.

        Keywords:
            by_id: Whether to match ids instead of text.

        Returns: The leaf web element.

        """
        leaf = self.expand_path(*path, **kwargs)
        self.logger.info("Path %r yielded menuitem %r", path, self.browser.text(leaf))
        if leaf is not None:
            self.browser.plugin.ensure_page_safe()
            self.browser.click(leaf)
        return leaf


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
            ".//input[@type='checkbox']")}

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

    def fill(self, value):
        if isinstance(value, date):
            date_str = value.strftime('%m/%d/%Y')
        else:
            date_str = str(value)
        self.move_to()
        # need to write to a readonly field: resort to evil
        if self.browser.get_attribute("ng-model", self) is not None:
            # self.set_angularjs_value(self, date_str)
            raise NotImplementedError
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
        self.paginator.first_page()

    def last_page(self):
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
        assert item in self.items()
        self.select.deselect_all()
        while item != self.items[0]:
            self.select.select_by_visible_text(item)
            self.up.click()

    def move_bottom(self, item):
        item = str(item)
        assert item in self.items()
        self.select.deselect_all()
        while item != self.items()[-1]:
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
        email = Text(ParametrizedLocator(".//a[text()='{email}']"))

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
