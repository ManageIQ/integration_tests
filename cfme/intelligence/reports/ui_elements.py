# -*- coding: utf-8 -*-
"""This file contains element definitions of elements that are common in reports."""
from xml.sax.saxutils import quoteattr

from collections import Sequence, Mapping, Callable
from contextlib import contextmanager

from cached_property import cached_property
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import AngularSelect, Calendar, Form, Region, Table, Select, fill
from utils import deferred_verpick, version
from utils.log import logger
from utils.wait import wait_for, TimedOutError
from utils.pretty import Pretty


class NotDisplayedException(Exception):
    pass


class PivotCalcSelect(Pretty):
    """This class encapsulates those JS pseudo-selects in Edit Report/Consolidation"""
    _entry = "//div[@class='dhx_combo_box']"
    _arrow = "//img[@class='dhx_combo_img']"
    _box = "//div[contains(@class, 'dhx_combo_list')]"
    _box_items = ".//div/div"
    _box_checkbox = (
        ".//div/div[normalize-space(text())='{}']/preceding-sibling::*[1][@type='checkbox']")
    pretty_attrs = ['_id']

    def __init__(self, root_el_id):
        self._id = root_el_id
        self._close_box = True

    @property
    def id(self):
        return self._id

    @classmethod
    def all(cls):
        """For debugging purposes"""
        return [
            cls(sel.get_attribute(x, "id"))
            for x
            in sel.elements("//td[contains(@id, 'pivotcalc_id_')]")
        ]

    def _get_root_el(self):
        return sel.element((By.ID, self._id))

    def _get_entry_el(self):
        return sel.element(self._entry, root=self._get_root_el())

    def _get_arrow_el(self):
        return sel.element(self._arrow, root=self._get_entry_el())

    def _open_box(self):
        self.close_all_boxes()
        sel.click(self._get_arrow_el())

    @classmethod
    def close_all_boxes(cls):
        """No other solution as the boxes have no ID"""
        for box in sel.elements(cls._box):
            sel.browser().execute_script(
                "if(arguments[0].style.display != 'none') arguments[0].style.display = 'none';", box
            )

    def _get_box(self):
        """Caching of the opened box"""
        if getattr(self, "_box_id", None) is None:
            self._open_box()
            for box in sel.elements(self._box):
                try:
                    sel.move_to_element(box)
                    if sel.is_displayed(box):
                        self._box_id = box.id
                        return box
                except sel.NoSuchElementException:
                    pass
            else:
                raise Exception("Could not open the box!")
        else:
            el = WebElement(sel.browser(), self._box_id)
            try:
                el.tag_name
                if not sel.is_displayed(el):
                    raise NotDisplayedException()
                return el
            except (StaleElementReferenceException, NoSuchElementException, NotDisplayedException):
                del self._box_id
                return self._get_box()

    def _get_box_items(self):
        return [sel.text(item) for item in sel.elements(self._box_items, root=self._get_box())]

    def _get_checkbox_of(self, name):
        return sel.element(self._box_checkbox.format(name), root=self._get_box())

    def clear_selection(self):
        for item in self._get_box_items():
            sel.uncheck(self._get_checkbox_of(item))
        if self._close_box:
            self.close_all_boxes()

    def items(self):
        result = self._get_box_items()
        if self._close_box:
            self.close_all_boxes()
        return result

    def check(self, item):
        return sel.check(self._get_checkbox_of(item))

    def uncheck(self, item):
        return sel.uncheck(self._get_checkbox_of(item))

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(repr(self._id)))

    def __str__(self):
        return repr(self)


@fill.method((PivotCalcSelect, basestring))
def _fill_pcs_str(o, s):
    logger.info("  Filling %s with string %s", str(o), str(s))
    o.clear_selection()
    o.check(s)
    o.close_all_boxes()


@fill.method((PivotCalcSelect, Sequence))
def _fill_pcs_seq(o, l):
    logger.info("  Filling %s with sequence %s", str(o), str(l))
    o.clear_selection()
    for name in l:
        o.check(name)
    o.close_all_boxes()


@fill.method((PivotCalcSelect, Callable))
def _fill_pcs_callable(o, c):
    logger.info("  Filling %s with callable %s", str(o), str(c))
    for item in o.items():
        logger.info("    Calling callable on item %s", item)
        result = bool(c(item))
        logger.info("      Setting item %s to %s", item, str(result))
        if result is True:
            o.check(item)
        else:
            o.uncheck(item)
    o.close_all_boxes()


@fill.method((PivotCalcSelect, Mapping))
def _fill_pcs_map(o, m):
    logger.info("  Filling {} with mapping {}".format(str(o), str(m)))
    for item, value in m.iteritems():
        value = bool(value)
        logger.info("  Setting item {} to {}".format(item, str(value)))
        if value:
            o.check(item)
        else:
            o.uncheck(item)
    o.close_all_boxes()


class RecordGrouper(Pretty):
    """This class encapsulates the grouping editing in Edit Report/Consolidation in the table at
    the bottom

    Filling this element expects a :py:class:`dict`. The key of the dictionary is the name of the
    column (leftmost table cell). The value of the dictionary is a list of values that will get
    selected in the dropdown (Minimum, Average, ...)

    .. code-block:: yaml

       CPU - % Overallocated:
         - Maximum
         - Minimum
         - Average
    """
    pretty_attrs = ['_table_loc']

    def __init__(self, table_loc):
        self._table_loc = table_loc
        self.table = Table(table_loc)

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(repr(self._table_loc)))


@fill.method((RecordGrouper, Mapping))
def _fill_recordgrouper(rg, d):
    logger.info("  Filling {} with data {}".format(str(rg), str(d)))
    for row_column_name, content in d.iteritems():
        row = rg.table.find_row("column_name", row_column_name)
        if version.current_version() >= "5.5":
            select = sel.element("./select", root=row.calculations)
            select_id = sel.get_attribute(select, "id")
            fill(AngularSelect(select_id, multi=True), content)
        else:
            fill(PivotCalcSelect(sel.get_attribute(row.calculations, "id")), content)


class ColumnStyleTable(Pretty):
    """We cannot inherit Table because it does too much WebElement chaining. This avoids that
    with using xpath-only locating making it much more reliable.

    This is the kind of table that is used in Styling tab. The fill value is expected to be a
    :py:class:`dict`. Keys of the dictionary are names of the columns (leftmost table cell).
    The values of the dictionary are lists up to 3 fields long. First element of each of the lists
    is the ``Style`` to be selected in the same-named table column. Second one is the operation
    (``=``, ``IS NULL``, ...) to happen. If the operation has some operand, it is the third (and
    last) element of the list. If any of the lists has operation set as ``Default``, no other lists
    cannot follow after them.


    .. code-block:: yaml

       Name:
        -
            - Blue Text
            - "="
            - asdf
        -
            - Yellow Background
            - IS NULL
        -
            - Red Background
            - IS NOT NULL

    Args:
        div_id: `id` of `div` where the table is located in.
    """
    pretty_attrs = ['_div_id']

    def __init__(self, div_id):
        self._div_id = div_id

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(repr(self._div_id)))

    def get_style_select(self, name, id=0):
        """Return Select element with selected style.

        Args:
            name: Text written in leftmost column of the wanted row.
            id: Sequential id in the sub-row, 0..2.
        Returns: :py:class:`cfme.web_ui.Select`.
        """
        return Select(
            "//div[@id={}]//table/tbody/tr[td[1][normalize-space(.)={}]]/td[2]/select"
            "[@id[substring(., string-length() -1) = '_{}'] and contains(@id, 'style_')]"
            .format(quoteattr(self._div_id), quoteattr(name), id)
        )

    def get_if_select(self, name, id=0):
        """Return Select element with operator selection.

        Args:
            name: Text written in leftmost column of the wanted row.
            id: Sequential id in the sub-row, 0..2.
        Returns: :py:class:`cfme.web_ui.Select`.
        """
        return Select(
            "//div[@id={}]//table/tbody/tr[td[1][normalize-space(.)={}]]/td[3]/select"
            "[@id[substring(., string-length() -1) = '_{}'] and contains(@id, 'styleop')]"
            .format(quoteattr(self._div_id), quoteattr(name), id)
        )

    def get_if_input(self, name, id=0):
        """Return the `input` element with value selection.

        Args:
            name: Text written in leftmost column of the wanted row.
            id: Sequential id in the sub-row, 0..2.
        Returns: :py:class:`str` with locator.
        """
        return (
            "//div[@id={}]//table/tbody/tr[td[1][normalize-space(.)={}]]/td[3]/input"
            "[@id[substring(., string-length() -1) = '_{}'] and contains(@id, 'styleval')]"
            .format(quoteattr(self._div_id), quoteattr(name), id)
        )


@fill.method((ColumnStyleTable, Mapping))
def _fill_cst_map(cst, d):
    logger.info("  Filling {} with mapping {}".format(str(cst), str(d)))
    for key, values in d.iteritems():
        if not isinstance(values, Sequence) and not isinstance(values, basestring):
            values = [values]
        assert 1 <= len(values) <= 3, "Maximum 3 formatters"
        for i, value in enumerate(values):
            if isinstance(value, basestring):
                value = [value, "Default"]  # Default value when just string used.
            assert 2 <= len(value) <= 3, "Must be string or 2-or-3-tuple"
            fill(cst.get_style_select(key, i), value[0])
            fill(cst.get_if_select(key, i), value[1])
            if len(value) == 3:
                fill(cst.get_if_input(key, i), value[2])


class ColumnHeaderFormatTable(Table):
    """Used to fill the table with header names and value formatting.

    The value expected for filling is a :py:class:`dict` where keys are names of the columns
    (leftmost cells in the table) and values are :py:class:`dict` , :py:class:`str` or
    :py:class:`list`. In case of dictionary, the ``header`` and ``format`` fields are required, they
    correspond to the table columns. If a string is specified, it is considered a header. If a list
    is specified, then first item in it is considered a ``header``, second one a ``format``
    (if present).

    .. code-block:: yaml

       Archived:
           header: Test1
           format: Boolean (T/F)
       Busy:
           header: Such busy
           format: Boolean (Yes/No)
       asdf: fghj
       qwer:
       - thisisheader
       - thisisformat
    """
    pass


@fill.method((ColumnHeaderFormatTable, Mapping))
def __fill_chft_map(chft, d):
    logger.info("  Filling {} with mapping {}".format(str(chft), str(d)))
    for key, value in d.iteritems():
        row = chft.find_row("column_name", key)
        if isinstance(value, dict):
            header = value.get("header", None)
            format = value.get("format", None)
        elif isinstance(value, basestring):
            header = value
            format = None
        elif isinstance(value, Sequence):
            if len(value) == 1:
                header = value[0]
            elif len(value) == 2:
                header, format = value
            else:
                raise ValueError("Wrong sequence length")
        else:
            raise Exception()
        logger.info("   Filling values {}, {}".format(str(header), str(format)))
        fill(sel.element(".//input", root=row.header), header)
        fill(Select(sel.element(".//select", root=row.format)), format)


class MenuShortcuts(Pretty):
    """This class operates the web ui object that handles adding new menus and shortcuts for widgets

    The expected object for filling is one of :py:class:`dict`, :py:class:`list` or :py:class:`str`.
    If :py:class:`dict`, then the keys are menu item names and their values are their aliases. If
    you don't want to specify an alias for such particular menu item, use None. :py:class:`str`
    behaves same as single element :py:class:`list`. If :py:class:`list`, then it is the same as it
    would be with :py:class:`dict` but you cannot specify aliases, just menu names.

    Args:
        select_name: Name of the select
    """
    pretty_attrs = ['_select_name']

    def __init__(self, select_name):
        self._select_name = select_name

    @property
    def select(self):
        return version.pick({
            version.LOWEST: Select("select#{}".format(self._select_name)),
            "5.5": AngularSelect(self._select_name)})

    @property
    def opened_boxes_ids(self):
        """Return ids of all opened boxes."""
        return [
            # it's like 's_3'
            int(sel.get_attribute(el, "id").rsplit("_", 1)[-1])
            for el
            in sel.elements("//div[@title='Drag this Shortcut to a new location']")
            if sel.is_displayed(el)
        ]

    def close_box(self, id):
        sel.click("//a[@id='s_{}_close']".format(id))

    def get_text_of(self, id):
        return sel.get_attribute("//input[@id='shortcut_desc_{}']".format(id), "value")

    def set_text_of(self, id, text):
        sel.set_text("//input[@id='shortcut_desc_{}']".format(id), text)

    @cached_property
    def mapping(self):
        """Determine mapping Menu item => menu item id.

        Needed because the boxes with shortcuts are accessible only via ids.
        Need to close boxes because boxes displayed are not in the Select.
        """
        # Save opened boxes
        closed_boxes = []
        for box_id in self.opened_boxes_ids:
            closed_boxes.append((self.get_text_of(box_id), box_id))
            self.close_box(box_id)
        # Check the select
        result = {}
        for option in self.select.options:
            try:
                result[sel.text(option)] = int(sel.get_attribute(option, "value"))
            except (ValueError, TypeError):
                pass
        # Restore box layout
        for name, id in closed_boxes:
            sel.select(self.select, sel.ByValue(str(id)))
            self.set_text_of(id, name)

        return result

    def clear(self):
        """Clear the selection."""
        for id in self.opened_boxes_ids:
            self.close_box(id)

    def add(self, menu, alias=None):
        """Add a new shortcut.

        Args:
            menu: What menu item to select.
            alias: Optional alias for this menu item.
        """
        if menu not in self.mapping:
            raise NameError("Unknown menu location {}!".format(menu))
        sel.select(self.select, sel.ByValue(str(self.mapping[menu])))
        if alias is not None:
            self.set_text_of(self.mapping[menu], alias)


@fill.method((MenuShortcuts, Mapping))
def _fill_ms_map(ms, d):
    ms.clear()
    for menu, alias in d.iteritems():
        ms.add(menu, alias)


@fill.method((MenuShortcuts, Sequence))
def _fill_ms_seq(ms, seq):
    ms.clear()
    for menu in seq:
        ms.add(menu)


@fill.method((MenuShortcuts, basestring))
def _fill_ms_str(ms, s):
    fill(ms, [s])


class Timer(object):
    form = Form(fields=[
        ("run", Select("//select[@id='timer_typ']")),
        ("hours", Select("//select[@id='timer_hours']")),
        ("days", Select("//select[@id='timer_days']")),
        ("weeks", Select("//select[@id='timer_weeks']")),
        ("months", Select("//select[@id='timer_months']")),
        ("time_zone", Select("//select[@id='time_zone']")),
        ("start_date", Calendar("miq_date_1")),
        ("start_hour", Select("//select[@id='start_hour']")),
        ("start_min", Select("//select[@id='start_min']")),
    ])


@fill.method((Timer, Mapping))
def _fill_timer_map(t, d):
    return fill(t.form, d)


class ExternalRSSFeed(object):
    """This element encapsulates selection of an external RSS source either from canned selection or
    custom one.

    It expects a :py:class:`str` filling object. If the string is not found in the dropdown, it is
    considered to be custom url, so it selects custom URL option in the dropdown and fills the text
    input with the URL. If the option is available in the dropdown, then it is selected.
    """
    form = Region(locators=dict(
        rss_url=Select("//select[@id='rss_url']"),
        txt_url="//input[@id='txt_url']"
    ))


@fill.method((ExternalRSSFeed, basestring))
def _fill_rss_str(erf, s):
    try:
        sel.select(erf.form.rss_url, s)
    except NoSuchElementException:
        sel.select(erf.form.rss_url, "<Enter URL Manually>")
        sel.send_keys(erf.form.txt_url, s)


class DashboardWidgetSelector(Pretty):
    """This object encapsulates the selector of widgets that will appear on a dashboard.

    It cannot move them around, just add and remove them.

    The filling of this element expects a :py:class:`list` of strings (or just :py:class:`str`
    itself). The strings are names of the widgets.
    """
    _button_open_close = ".//img[contains(@src, 'combo_select.gif')]"
    _combo_list = (
        "//div[contains(@class, 'dhx_combo_list') and div/div[normalize-space(.)='Add a Widget']]")
    _selected = (".//div[@id='modules']//div[contains(@id, 'w_')]/div/h2/div"
        "/span[contains(@class, 'modtitle_text')]")
    _remove_button = ".//div[@id='modules']//div[contains(@id, 'w_')]/div"\
        "/h2[div/span[contains(@class, 'modtitle_text') and normalize-space(.)='{}']]"\
        "/a[@title='Remove this widget']"
    pretty_attrs = ['_root_loc']

    def __init__(self, root_loc="//div[@id='form_widgets_div']"):
        self._root_loc = root_loc

    def _open_close_combo(self):
        sel.click(sel.element(self._button_open_close, root=sel.element(self._root_loc)))

    @property
    def _is_combo_opened(self):
        return sel.is_displayed(self._combo_list)

    def _open_combo(self):
        if not self._is_combo_opened:
            self._open_close_combo()

    def _close_combo(self):
        if self._is_combo_opened:
            self._open_close_combo()

    @property
    @contextmanager
    def combo(self):
        self._open_combo()
        yield sel.element(self._combo_list)
        self._close_combo()

    @property
    def selected_items(self):
        self._close_combo()
        return [
            sel.text(item).encode("utf-8")
            for item
            in sel.elements(self._selected, root=sel.element(self._root_loc))
        ]

    def deselect(self, *items):
        self._close_combo()
        for item in items:
            sel.click(
                sel.element(
                    self._remove_button.format(item),
                    root=sel.element(self._root_loc)))

    def select(self, *items):
        for item in items:
            if item not in self.selected_items:
                with self.combo as combo:
                    sel.click(
                        sel.element("./div/div[contains(., '{}')]".format(item), root=combo))

    def clear(self):
        for item in self.selected_items:
            self.deselect(item)


class NewerDashboardWidgetSelector(DashboardWidgetSelector):
    """Dashboard widget selector from 5.5 onwards."""
    _button_open_close = ".//div[contains(@class, 'dropdown-menu open')]"
    _combo_list = "//div[contains(@class, 'dropdown-menu open')]/ul"

    _remove_button = ".//a[../../h3[normalize-space(.)='{}']]"
    _selected = "./div[@id='modules']/div/div/div/h3"
    _select = AngularSelect("widget")

    def select(self, *items):
        sel.wait_for_ajax()
        for item in items:
            self._select.select_by_visible_text(item)

    # Disable some functions
    def _open_close_combo(self):
        pass

    _is_combo_opened = False

    def _open_combo(self):
        pass

    def _close_combo(self):
        pass

    @property
    @contextmanager
    def combo(self):
        yield


@fill.method((DashboardWidgetSelector, Sequence))
def _fill_dws_seq(dws, seq):
    dws.clear()
    dws.select(*seq)


@fill.method((DashboardWidgetSelector, basestring))
def _fill_dws_str(dws, s):
    fill(dws, [s])


class FolderManager(Pretty):
    """Class used in Reports/Edit Reports menus."""
    _fields = deferred_verpick({
        version.LOWEST:
        ".//div[@id='folder_grid']/div[contains(@class, 'objbox')]/table/tbody/tr/td",
        "5.5.0.7": ".//div[@id='folder_grid']/ul/li"})
    _field = deferred_verpick({
        version.LOWEST:
        ".//div[@id='folder_grid']/div[contains(@class, 'objbox')]/table/tbody/tr"
        "/td[normalize-space(.)='{}']",
        "5.5.0.7": ".//div[@id='folder_grid']/ul/li[normalize-space(.)='{}']"})
    pretty_attrs = ['root']

    # Keep the number of items in versions the same as buttons' and actions' values!
    # If a new version arrives, extend all the tuples :)
    versions = (version.LOWEST, "5.5.0.7")
    actions = ("_click_button", "_click_button_i")
    buttons = {
        "move_top": ("Move selected folder top", "fa-angle-double-up"),
        "move_bottom": ("Move selected folder to bottom", "fa-angle-double-down"),
        "move_up": ("Move selected folder up", "fa-angle-up"),
        "move_down": ("Move selected folder down", "fa-angle-down"),
        "delete_folder": ("Delete selected folder and its contents", "fa-times"),
        "add_subfolder": ("Add subfolder to selected folder", "fa-plus"),
    }

    class _BailOut(Exception):
        pass

    def __init__(self, root):
        self.root = lambda: sel.element(root)

    def __repr__(self):
        return "{}({})".format(type(self).__name__, str(repr(self.root)))

    @classmethod
    def bail_out(cls):
        """If something gets wrong, you can use this method to cancel editing of the items in
        the context manager.

        Raises: :py:class:`FolderManager._BailOut` exception
        """
        raise cls._BailOut()

    def _click_button(self, alt):
        sel.click(sel.element(".//img[@alt='{}']".format(alt), root=self.root))

    def _click_button_i(self, klass):
        sel.click(sel.element("i.{}".format(klass), root=self.root))

    def __getattr__(self, attr):
        """Resulve the button clicking action."""
        try:
            a_tuple = self.buttons[attr]
        except KeyError:
            raise AttributeError("Action {} does not exist".format(attr))
        action = version.pick(dict(zip(self.versions, self.actions)))
        action_meth = getattr(self, action)
        action_data = version.pick(dict(zip(self.versions, a_tuple)))

        def _click_function():
            action_meth(action_data)

        return _click_function

    def commit(self):
        self._click_button("Commit expression element changes")

    def discard(self):
        self._click_button("Discard expression element changes")

    @property
    def _all_fields(self):
        return sel.elements(self._fields, root=self.root)

    @property
    def fields(self):
        """Returns all fields' text values"""
        return map(lambda el: sel.text(el).encode("utf-8"), self._all_fields)

    @property
    def selected_field_element(self):
        """Return selected field's element.

        Returns: :py:class:`WebElement` if field is selected, else `None`
        """
        if version.current_version() < "5.5.0.7":
            active = "cellselected"
        else:
            active = "active"
        selected_fields = filter(lambda el: active in sel.get_attribute(el, "class"),
                                 self._all_fields)
        if len(selected_fields) == 0:
            return None
        else:
            return selected_fields[0]

    @property
    def selected_field(self):
        """Return selected field's text.

        Returns: :py:class:`str` if field is selected, else `None`
        """
        sf = self.selected_field_element
        return None if sf is None else sel.text(sf).encode("utf-8").strip()

    def add(self, subfolder):
        self.add_subfolder()
        wait_for(lambda: self.selected_field_element is not None, num_sec=5, delay=0.1)
        sel.double_click(self.selected_field_element, wait_ajax=False)
        if version.current_version() < "5.5.0.7":
            input = wait_for(
                lambda: sel.elements("./input", root=self.selected_field_element),
                num_sec=5, delay=0.1, fail_condition=[])[0][0]
            sel.set_text(input, subfolder)
            sel.send_keys(input, Keys.RETURN)
        else:
            sel.handle_alert(prompt=subfolder)

    def select_field(self, field):
        """Select field by text.

        Args:
            field: Field text.
        """
        sel.click(sel.element(self._field.format(field), root=self.root))
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
        self.delete_folder()

    def move_first(self, field):
        self.select_field(field)
        self.move_top()

    def move_last(self, field):
        self.select_field(field)
        self.move_bottom()

    def clear(self):
        for field in self.fields:
            self.delete_field(field)


@fill.method((FolderManager, basestring))
def _fill_fm_str(fm, s):
    if not fm.has_field(s):
        fm.add(s)


@fill.method((FolderManager, Sequence))
def _fill_fm_seq(fm, i):
    if isinstance(i, tuple):  # Let's consider tuple as "deleter"
        fm.clear()
    for item in i:
        fill(fm, item)
