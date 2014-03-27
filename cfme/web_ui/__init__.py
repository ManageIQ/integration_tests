"""Provides a number of objects to help with managing certain elements in the CFME UI.

 Specifically there are two categories of objects, organizational and elemental.

* **Organizational**

  * :py:class:`Region`
  * :py:mod:`cfme.web_ui.menu`

* **Elemental**

  * :py:class:`CheckboxTable`
  * :py:class:`DHTMLSelect`
  * :py:class:`Filter`
  * :py:class:`Form`
  * :py:class:`InfoBlock`
  * :py:class:`Quadicon`
  * :py:class:`Radio`
  * :py:class:`Select`
  * :py:class:`SplitTable`
  * :py:class:`Table`
  * :py:class:`Tree`
  * :py:mod:`cfme.web_ui.accordion`
  * :py:mod:`cfme.web_ui.flash`
  * :py:mod:`cfme.web_ui.listnav`
  * :py:mod:`cfme.web_ui.menu`
  * :py:mod:`cfme.web_ui.paginator`
  * :py:mod:`cfme.web_ui.tabstrip`
  * :py:mod:`cfme.web_ui.toolbar`

"""

import os
import re
import types
from datetime import date
from selenium.webdriver.common.action_chains import ActionChains
from collections import Sequence, Mapping
from selenium.common import exceptions as sel_exceptions
from selenium.webdriver.support.select import Select as SeleniumSelect
from multimethods import multimethod, multidispatch, Anything

import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions
from cfme.fixtures.pytest_selenium import browser

from utils.log import logger


class Region(object):
    """
    Base class for all UI regions/pages

    Args:
        locators: A dict of locator objects for the given region
        title: A string containing the title of the page
        identifying_loc: Single locator key from locators used by :py:meth:`Region.is_displayed`
                         to check if the region is currently visible

    Usage:

        page = Region(locators={
            'configuration_button': (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']"),
            'discover_button': (By.CSS_SELECTOR,
                "tr[title='Discover Cloud Providers']>td.td_btn_txt>" "div.btn_sel_text")
            },
            title='CloudForms Management Engine: Cloud Providers',
            identifying_loc='discover_button'
        )

    The elements can then accessed like so::

        page.configuration_button

    Locator attributes will return the locator tuple for that particular element,
    and can be passed on to other functions, such as :py:func:`element` and :py:func:`click`.

    """
    def __getattr__(self, name):
        if hasattr(self, 'locators'):
            return self.locators[name]
        else:
            raise AttributeError("Region has no attribute named " + name)

    def __init__(self, locators=None, title=None, identifying_loc=None, infoblock_type=None):
        self.locators = locators
        self.identifying_loc = identifying_loc
        self.title = title
        if infoblock_type:
            self.infoblock = InfoBlock(infoblock_type)

    def is_displayed(self):
        """
        Checks to see if the region is currently displayed

        Returns: A boolean describing if the region is currently displayed
        """
        msg = "Region doesn't have an identifying locator or title, " +\
            "can't determine if current page."
        assert self.identifying_loc or self.title, msg

        # Automatically match ident/title if no identifying_loc/title
        ident_match = (not self.identifying_loc or
            sel.is_displayed(self.locators[self.identifying_loc]))
        title_match = (not self.title or
            browser().title == self.title)
        return title_match and ident_match


def get_context_current_page():
    """
    Returns the current page name

    Returns: A string containing the current page name
    """
    url = browser().current_url()
    stripped = url.lstrip('https://')
    return stripped[stripped.find('/'):stripped.rfind('?')]


class Table(object):
    """
    Helper class for Table/List objects

    Turns CFME custom Table/Lists into iterable objects using a generator.

    Args:
        table_locator: locator pointing to a table element with child thead and tbody elements
            representing that table's header and body row containers
        header_offset: In the case of a padding table row above the header, the row offset
            can be used to skip rows in ``<thead>`` to locate the correct header row. This offset
            is 1-indexed, not 0-indexed, so an offset of 1 is the first child row element
        body_offset: In the case of a padding table row above the body rows, the row offset
            can be used to skip rows in ``<ttbody>`` to locate the correct header row. This offset
            is 1-indexed, not 0-indexed, so an offset of 1 is the first child row element

    Attributes:
        header_indexes: A dict of header names related to their int index as a column.

    Usage:

        table = Table('//div[@id="prov_pxe_img_div"]//table')

    The HTML code for the table looks something like this::

        <div id="prov_pxe_img_div">
          <table>
              <thead>
                  <tr>
                      <th>Name</th>
                      <th>Animal</th>
                      <th>Size</th>
                  </tr>
              </thead>
              <tbody>
                  <tr>
                      <td>John</td>
                      <td>Monkey</td>
                      <td>Small</td>
                  </tr>
                  <tr>
                      <td>Mike</td>
                      <td>Tiger</td>
                      <td>Large</td>
                  </tr>
              </tbody>
          </table>
        </div>

    We can now click on an element in the list like so, by providing the column
    name and the value that we are searching for::

        table.click_cell('name', 'Mike')

    We can also perform the same, by using the index of the column, like so::

        table.click_cell(1, 'Tiger')

    Additionally, the rows of a table can be iterated over, and that row's columns can be accessed
    by name or index (left to right, 0-index)::

        for row in table.rows()
            # Get the first cell in the row
            row[0]
            # Get the row's contents for the column with header 'Row Name'
            # All of these will work, though the first is preferred
            row.row_name, row['row_name'], row['Row Name']

    When doing bulk opererations, such as selecting rows in a table based on their content,
    the ``*_by_cells`` methods are able to find matching row much more quickly than iterating,
    as the work can be done with fewer selenium calls.

        * :py:meth:`find_rows_by_cells`
        * :py:meth:`find_row_by_cells`
        * :py:meth:`click_rows_by_cells`
        * :py:meth:`click_row_by_cells`

    Note:

        A table is defined by the containers of the header and data areas, and offsets to them.
        This allows a table to include one or more padding rows above the header row. In
        the example above, there is no padding row, as our offset values are set to 0.

    """
    def __init__(self, table_locator, header_offset=0, body_offset=0):
        self._headers = None
        self._header_indexes = None
        self._loc = table_locator
        self.header_offset = int(header_offset)
        self.body_offset = int(body_offset)

    @property
    def header_row(self):
        """Property representing the ``<tr>`` element that contains header cells"""
        # thead/tr containing header data
        # xpath is 1-indexed, so we need to add 1 to the offset to get the correct row
        return sel.element('thead/tr[%d]' % (self.header_offset + 1), root=sel.element(self))

    @property
    def body(self):
        """Property representing the ``<tbody>`` element that contains body rows"""
        # tbody containing body rows
        return sel.element('tbody', root=sel.element(self))

    @property
    def headers(self):
        """List of ``<td>`` or ``<th>`` elements in :py:attr:`header_row`

         """
        if self._headers is None:
            self._update_cache()
        return self._headers

    @property
    def header_indexes(self):
        """Dictionary of header name: column index for this table's rows

        Derived from :py:attr:`headers`

        """
        if self._header_indexes is None:
            self._update_cache()
        return self._header_indexes

    def locate(self):
        return self._loc

    @staticmethod
    def _convert_header(header):
        """Convers header cell text into something usable as an identifier.

        Static method which replaces spaces in headers with underscores and strips out
        all other characters to give an identifier.

        Args:
            header: A header name to be converted.

        Returns: A string holding the converted header.
        """
        return re.sub('[^0-9a-zA-Z_]+', '', header.replace(' ', '_')).lower()

    @property
    def is_displayed(self):
        """ Whether the table is displayed or not.

        Returns: True if visible, otherwise False
        """
        return sel.is_displayed(self.header_row)

    def _update_cache(self):
        """Updates the internal cache of headers

        This allows columns to be moved and the Table updated. The :py:attr:`headers` stores
        the header cache element and the list of headers are stored in _headers. The
        attribute header_indexes is then created, before finally creating the items
        attribute.
        """
        self._headers = sel.elements('td | th', root=self.header_row)
        self._header_indexes = {
            self._convert_header(cell.text): self.headers.index(cell) for cell in self.headers}

    def rows(self):
        """A generator method holding the Row objects

        This generator yields Row objects starting at the first data row.

        Yields:
            :py:class:`Table.Row` object corresponding to the next row in the table.
        """
        index = self.body_offset
        row_elements = sel.elements('tr', root=self.body)
        for row_element in row_elements[index:]:
            yield self.create_row_from_element(row_element)

    def find_row(self, header, value):
        """
        Finds a row in the Table by iterating through each visible item.

        Args:
            header: A string or int, describing which column to inspect.
            value: The value to be compared when trying to identify the correct row
                to return.

        Returns:
            :py:class:`Table.Row` containing the requested cell, else ``None``.

        """
        return self.find_row_by_cells({header: value})

    def find_cell(self, header, value):
        """
        Finds an item in the Table by iterating through each visible item,
        this work used to be done by the :py:meth::`click_cell` method but
        has not been abstracted out to be called separately.

        Args:
            header: A string or int, describing which column to inspect.
            value: The value to be compared when trying to identify the correct cell
                to click.

        Returns: WebElement of the element if item was found, else ``None``.

        """
        matching_cell_rows = self.find_rows_by_cells({header: value})
        try:
            return getattr(matching_cell_rows[0], header)
        except IndexError:
            return None

    def find_rows_by_cells(self, cells):
        """A fast row finder, based on cell content.

        Args:
            cells: A dict of ``header: value`` pairs or a sequence of
                nested ``(header, value)`` pairs.

        Returns: A list of containing :py:class:`Table.Row` objects whose contents
            match all of the header: value pairs in ``cells``

        """
        # accept dicts or supertuples
        cells = dict(cells)
        cell_text_loc = '//td/descendant-or-self::*[contains(text(), "%s")]/ancestor::tr[1]'
        matching_rows_list = list()
        for value in cells.values():
            # Get all td elements that contain the value text
            matching_rows_list.append(sel.elements(cell_text_loc % value))

        # Now, find the common row elements that matched all the input cells
        # (though not yet matching values to headers)
        # Why not use set intersection here? Good question!
        # https://code.google.com/p/selenium/issues/detail?id=7011
        rows_elements = reduce(lambda l1, l2: [item for item in l1 if item in l2],
            matching_rows_list)

        # Convert them to rows
        # This is slow, which is why we do it after reducing the row element pile,
        # and not when building matching_rows_list, but it makes comparing header
        # names and expected values easy
        rows = [self.create_row_from_element(element) for element in rows_elements]

        # Only include rows where the expected values are in the right columns
        matching_rows = list()
        matching_row_filter = lambda heading, value: row[heading].text == value
        for row in rows:
            if all(matching_row_filter(*cell) for cell in cells.items()):
                matching_rows.append(row)

        return matching_rows

    def find_row_by_cells(self, cells):
        """Find the first row containing cells

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`

        Returns: The first matching row found, or None if no matching row was found

        """
        try:
            rows = self.find_rows_by_cells(cells)
            return rows[0]
        except IndexError:
            return None

    def click_rows_by_cells(self, cells, click_column=None):
        """Click the cell at ``click_column`` in the rows matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
            click_column: Which column in the row to click, defaults to None,
                which will attempt to click the row element

        Note:
            The value of click_column can be a string or an int, and will be passed directly to
            the item accessor (``__getitem__``) for :py:class:`Table.Row`

        """
        rows = self.find_rows_by_cells(cells)
        if click_column is None:
            map(sel.click, rows)
        else:
            map(sel.click, [row[click_column] for row in rows])

    def click_row_by_cells(self, cells, click_column=None):
        """Click the cell at ``click_column`` in the first row matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
            click_column: See :py:meth:`Table.click_rows_by_cells`

        """
        row = self.find_row_by_cells(cells)
        if click_column is None:
            sel.click(row)
        else:
            sel.click(row[click_column])

    def create_row_from_element(self, row_element):
        """Given a row element in this table, create a :py:class:`Table.Row`

        Args:
            row_element: A table row (``<tr>``) WebElement representing a row in this table.

        Returns: A :py:class:`Table.Row` for ``row_element``

        """
        return Table.Row(row_element, self)

    def click_cells(self, cell_map):
        """Submits multiple cells to be clicked on

        Args:
            cell_map: A mapping of header names and values, representing cells to click.
                As an example, ``{'name': ['wing', 'nut']}, {'age': ['12']}`` would click on
                the cells which had ``wing`` and ``nut`` in the name column and ``12`` in
                the age column. The yaml example for this would be as follows::

                    list_items:
                        name:
                            - wing
                            - nut
                        age:
                            - 12

        Raises:
            NotAllItemsClicked: If some cells were unable to be found.

        """
        failed_clicks = []
        for header, values in cell_map.items():
            if isinstance(values, basestring):
                values = [values]
            for value in values:
                res = self.click_cell(header, value)
                if not res:
                    failed_clicks.append("%s:%s" % (header, value))
        if failed_clicks:
            raise exceptions.NotAllItemsClicked(failed_clicks)

    def click_cell(self, header, value):
        """Clicks on a cell defined in the row.

        Uses the header identifier and a value to determine which cell to click on.

        Args:
            header: A string or int, describing which column to inspect.
            value: The value to be compared when trying to identify the correct cell
                to click the cell in.

        Returns: ``True`` if item was found and clicked, else ``False``.

        """
        cell = self.find_cell(header, value)
        if cell:
            sel.click(cell)
            return True
        else:
            return False

    class Row(object):
        """An object representing a row in a Table.

        The Row object returns a dymanically addressable attribute space so that
        the tables headers are automatically generated.

        Args:
            row_element: A table row ``WebElement``
            parent_table: :py:class:`Table` containing ``row_element``

        Notes:
            Attributes are dynamically generated. The index/key accessor is more flexible
            than the attr accessor, as it can operate on int indices and header names.

        """
        def __init__(self, row_element, parent_table):
            self.table = parent_table
            self.row_element = row_element

        @property
        def columns(self):
            """A list of WebElements corresponding to the ``<td>`` elements in this row"""
            return sel.elements('td', root=self.row_element)

        def __getattr__(self, name):
            """
            Returns Row element by header name
            """
            return self.columns[self.table.header_indexes[name]]

        def __getitem__(self, index):
            """
            Returns Row element by header index or name
            """
            try:
                return self.columns[index]
            except TypeError:
                # Index isn't an int, assume it's a string
                return getattr(self, self.table._convert_header(index))
            # Let IndexError raise

        def __str__(self):
            return ", ".join(["'%s'" % el.text for el in self.columns])

        def __eq__(self, other):
            if isinstance(other, type(self)):
                # Selenium elements support equality checks, so we can, too.
                return self.row_element == other.row_element
            else:
                return id(self) == id(other)

        def locate(self):
            # table.create_row_from_element(row_instance) might actually work...
            return self.row_element


class SplitTable(Table):
    """:py:class:`Table` that supports the header and body rows being in separate tables

    Args:
        header_data: A tuple, containing an element locator and an offset value.
            These point to the container of the header row. The offset is used in case
            there is a padding row above the header, or in the case that the header
            and the body are contained inside the same table element.
        body_data: A tuple, containing an element locator and an offset value.
            These point to the container of the body rows. The offset is used in case
            there is a padding row above the body rows, or in the case that the header
            and the body are contained inside the same table element.

    Usage:

        table = SplitTable(header_data=('//div[@id="header_table"]//table/tbody', 0),
            body_data=('//div[@id="body_table"]//table/tbody', 1))

    The HTML code for a split table looks something like this::

        <div id="prov_pxe_img_div">
          <table id="header_table">
              <tbody>
                  <tr>
                      <td>Name</td>
                      <td>Animal</td>
                      <td>Size</td>
                  </tr>
              </tbody>
          </table>
          <table id="body_table">
              <tbody>
                  <tr>
                      <td>Useless</td>
                      <td>Padding</td>
                      <td>Row</td>
                  </tr>
                  <tr>
                      <td>John</td>
                      <td>Monkey</td>
                      <td>Small</td>
                  </tr>
                  <tr>
                      <td>Mike</td>
                      <td>Tiger</td>
                      <td>Large</td>
                  </tr>
              </tbody>
          </table>
        </div>

    Note the use of the offset to skip the "Useless Padding Row" in ``body_data``. Most split
    tables require an offset for both the heading and body rows.

    """
    def __init__(self, header_data, body_data):
        self._headers = None
        self._header_indexes = None

        self._header_loc, header_offset = header_data
        self._body_loc, body_offset = body_data
        self.header_offset = int(header_offset)
        self.body_offset = int(body_offset)

    @property
    def header_row(self):
        """Property representing the ``<tr>`` element that contains header cells"""
        # thead/tr containing header data
        # xpath is 1-indexed, so we need to add 1 to the offset to get the correct row
        return sel.element('tr[%d]' % (self.header_offset + 1), root=sel.element(self._header_loc))

    @property
    def body(self):
        """Property representing the element that contains body rows"""
        # tbody containing body rows
        return sel.element(self._body_loc)

    def locate(self):
        # Use the header locator as the overall table locator
        return self._header_loc


class CheckboxTable(Table):
    """:py:class:`Table` with support for checkboxes

    Args:
        table_locator: See :py:class:`cfme.web_ui.Table`
        header_checkbox_locator: Locator of header checkbox (default `None`)
                                 Specify in case the header checkbox is not part of the header row
        header_offset: See :py:class:`cfme.web_ui.Table`
        body_offset: See :py:class:`cfme.web_ui.Table`
    """

    _checkbox_loc = ".//input[@type='checkbox']"

    def __init__(self, table_locator, header_checkbox_locator=None, header_offset=0, body_offset=0):
        super(CheckboxTable, self).__init__(table_locator, header_offset, body_offset)
        self._header_checkbox_loc = header_checkbox_locator

    @property
    def header_checkbox(self):
        """Checkbox used to select/deselect all rows"""
        if self._header_checkbox_loc is not None:
            return sel.element(self._header_checkbox_loc)
        else:
            return sel.element(self._checkbox_loc, root=self.header_row)

    def select_all(self):
        """Select all rows using the header checkbox"""
        sel.uncheck(self.header_checkbox)
        sel.check(self.header_checkbox)

    def deselect_all(self):
        """Deselect all rows using the header checkbox"""
        sel.check(self.header_checkbox)
        sel.uncheck(self.header_checkbox)

    def _set_row_checkbox(self, row, set_to=False):
        row_checkbox = sel.element(self._checkbox_loc, root=row.locate())
        sel.checkbox(row_checkbox, set_to)

    def _set_row(self, header, value, set_to=False):
        """ Internal method used to select/deselect a row by column header and cell value

        Args:
            header: See :py:meth:`Table.find_row`
            value: See :py:meth:`Table.find_row`
            set_to: Select if `True`, deselect if `False`
        """
        row = self.find_row(header, value)
        if row:
            self._set_row_checkbox(row, set_to)
            return True
        else:
            return False

    def select_row(self, header, value):
        """Select a single row specified by column header and cell value

        Args:
            header: See :py:meth:`Table.find_row`
            value: See :py:meth:`Table.find_row`

        Returns: `True` if successful, `False` otherwise
        """
        return self._set_row(header, value, True)

    def deselect_row(self, header, value):
        """Deselect a single row specified by column header and cell value

        Args:
            header: See :py:meth:`Table.find_row`
            value: See :py:meth:`Table.find_row`

        Returns: `True` if successful, `False` otherwise
        """
        return self._set_row(header, value, False)

    def _set_rows(self, cell_map, set_to=False):
        """ Internal method used to select/deselect multiple rows

        Args:
            cell_map: See :py:meth:`Table.click_cells`
            set_to: Select if `True`, deselect if `False`
        """
        failed_selects = []
        for header, values in cell_map.items():
            if isinstance(values, basestring):
                values = [values]
            for value in values:
                res = self._set_row(header, value, set_to)
                if not res:
                    failed_selects.append("%s:%s" % (header, value))
        if failed_selects:
            raise exceptions.NotAllCheckboxesFound(failed_selects)

    def select_rows(self, cell_map):
        """Select multiple rows

        Args:
            cell_map: See :py:meth:`Table.click_cells`

        Raises:
            NotAllCheckboxesFound: If some cells were unable to be found
        """
        self._set_rows(cell_map, True)

    def deselect_rows(self, cell_map):
        """Deselect multiple rows

        Args:
            cell_map: See :py:meth:`Table.click_cells`

        Raises:
            NotAllCheckboxesFound: If some cells were unable to be found
        """
        self._set_rows(cell_map, False)

    def _set_row_by_cells(self, cells, set_to=False):
        row = self.find_row_by_cells(cells)
        self._set_row_checkbox(row, set_to)

    def select_row_by_cells(self, cells):
        """Select the first row matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`

        """
        self._set_row_by_cells(cells, True)

    def deselect_row_by_cells(self, cells):
        """Deselect the first row matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`

        """
        self._set_row_by_cells(cells, False)

    def _set_rows_by_cells(self, cells, set_to=False):
        rows = self.find_rows_by_cells(cells)
        for row in rows:
            self._set_row_checkbox(row, set_to)

    def select_rows_by_cells(self, cells):
        """Select the rows matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
        """
        self._set_rows_by_cells(cells, True)

    def deselect_rows_by_cells(self, cells):
        """Deselect the rows matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
        """
        self._set_rows_by_cells(cells, False)


@multimethod(lambda loc, value: (sel.tag(loc), sel.get_attribute(loc, 'type')))
def fill_tag(loc, value):
    ''' Return a tuple of function to do the filling, and a value to log.'''
    raise NotImplementedError("Don't know how to fill {} into this type: {}".format(value, loc))


@fill_tag.method((Anything, 'text'))
@fill_tag.method((Anything, 'textarea'))
def fill_text(textbox, val):
    return (sel.set_text, val)


@fill_tag.method((Anything, 'password'))
def fill_password(pwbox, password):
    return (sel.set_text, "********")


@fill_tag.method(('a', Anything))
@fill_tag.method(('img', Anything))
@fill_tag.method((Anything, 'image'))
def fill_click(el, val):
    '''Click only when given a truthy value'''
    def click_if(e, v):
        if v:
            sel.click(e)
    return (click_if, val)


@fill_tag.method((Anything, 'file'))
def fill_file(fd, val):
    return (sel.send_keys, val)


@fill_tag.method((Anything, 'checkbox'))
def fill_checkbox(cb, val):
    return (sel.checkbox, bool(val))


@multidispatch
def fill(loc, content):
    """
    Fills in a UI component with the given content.

    Usage:
        fill(textbox, "text to fill")
        fill(myform, [ ... data to fill ...])
        fill(radio, "choice to select")

    """
    action, logval = fill_tag(loc, content)
    logger.debug('  Filling in [%s], with value "%s"' % (loc, logval))
    action(loc, content)
    sel.detect_observed_field(loc)


@fill.method((Table, object))
def _sd_fill_table(table, cells):
    """ How to fill a table with a value (by selecting the value as cells in the table)
    See Table.click_cells
    """
    table._update_cache()
    logger.debug('  Clicking Table cell')
    table.click_cells(cells)


@fill.method((CheckboxTable, object))
def _sd_fill_checkboxtable(table, cells):
    """ How to fill a checkboxtable with a value (by selecting the right rows)
    See CheckboxTable.select_by_cells
    """
    table._update_cache()
    logger.debug('  Selecting CheckboxTable row')
    table.select_rows(cells)


class Calendar(object):
    """A CFME calendar form field

    Calendar fields are readonly, and managed by the dxhtmlCalendar widget. A Calendar field
    will accept any object that can be coerced into a string, but the value may not match the format
    expected by dhtmlxCalendar or CFME. For best results, either a ``datetime.date`` or
    ``datetime.datetime`` object should be used to create a valid date field.

    Args:
        name: "name" property of the readonly calendar field.

    Usage:

        calendar = web_ui.Calendar("miq_date_1")
        web_ui.fill(calendar, date(2000, 1, 1))
        web_ui.fill(calendar, '1/1/2001')

    """
    def __init__(self, name):
        self.name = name

    def locate(self):
        return '//input[@name="%s"]' % self.name


@fill.method((Calendar, object))
def _sd_fill_date(calendar, value):
    input = sel.element(calendar)
    if isinstance(value, date):
        date_str = '%s/%s/%s' % (value.month, value.day, value.year)
    else:
        date_str = str(value)

    # need to write to a readonly field: resort to evil
    browser().execute_script("arguments[0].value = '%s'" % date_str, input)


@fill.method((object, types.NoneType))
@fill.method((types.NoneType, object))
def _sd_fill_none(*args, **kwargs):
    """ Ignore a NoneType """
    pass


class Form(Region):
    """
    A class for interacting with Form elements on pages.

    The Form class takes a set of locators and binds them together to create a
    unified Form object. This Form object has a defined field order so that the
    user does not have to worry about which order the information is provided.
    This enables the data to be provided as a dict meaning it can be passed directly
    from yamls. It inherits the base Region class, meaning that locators can still be
    referenced in the same way a Region's locators can.

    Args:
        fields: A list of field name/locator tuples. The argument not only defines
            the order of the elements but also which elements comprise part of the form.
        identifying_loc: A locator which should be present if the form is visible.

    Usage:

      provider_form = web_ui.Form(
          fields=[
              ('type_select', "//*[@id='server_emstype']"),
              ('name_text', "//*[@id='name']"),
              ('hostname_text', "//*[@id='hostname']"),
              ('ipaddress_text', "//*[@id='ipaddress']"),
              ('amazon_region_select', "//*[@id='hostname']"),
              ('api_port', "//*[@id='port']"),
          ])

    Forms can then be filled in like so.::

        provider_info = {
           'type_select': "OpenStack",
           'name_text': "RHOS-01",
           'hostname_text': "RHOS-01",
           'ipaddress_text': "10.0.0.0",
           'api_port': "5000",
        }
        web_ui.fill(provider_form, request_info)

    Note:
        Using supertuples in a list, although ordered due to the properties of a List,
        will not overide the field order defined in the Form.
    """

    def __init__(self, fields=None, identifying_loc=None):
        self.locators = dict((key, value) for key, value in fields)
        self.fields = fields
        self.identifying_loc = identifying_loc

    def fill(self, fill_data):
        fill(self, fill_data)


@fill.method((Form, Sequence))
def _fill_form_list(form, values, action=None):
    """
    Fills in field elements on forms

    Takes a set of values in dict or supertuple format and locates form elements,
    in the correct order, and fills them in.

    Note:
        Currently supports, text, textarea, select, checkbox, radio, password, a
        and Table objects/elements.

    Args:
        values: a dict or supertuple formatted set of data where
            each key is the name of the form locator from the page model. Some
            objects/elements, such as :py:class:`Table` objects, support providing
            multiple values to be clicked on in a single call.
        action: a locator which will be clicked when the form filling is complete

    """
    logger.info('Beginning to fill in form...')
    values = list(val for key in form.fields for val in values if val[0] == key[0])

    for field, value in values:
        if value is not None:
            loc = form.locators[field]
            logger.debug(' Dispatching fill for "%s"' % field)
            fill(loc, value)  # re-dispatch to fill for each item

    if action:
        logger.debug(' Invoking end of form action')
        sel.click(sel.element(action))
    logger.debug('Finished filling in form')


@fill.method((object, Mapping))
def _fill_form_dict(form, values, action=None):
    '''Fill in a dict by converting it to a list'''
    fill(form, values.items(), action=action)


class Radio(object):
    """ A class for Radio button groups

    Radio allows the usage of HTML radio elements without resorting to previous
    practice of iterating over elements to find the value. The name of the radio
    group is passed and then when choices are required, the locator is built.

    Args:
        name: The HTML elements ``name`` attribute that identifies a group of radio
            buttons.

    Usage:

        radio = Radio("schedule__schedule_type")

    A specific radio element can then be returned by running the following::

        el = radio.choice('immediately')
        click(el)

    The :py:class:`Radio` object can be reused over and over with repeated calls to
    the :py:func:`Radio.choice` method.
    """
    def __init__(self, name):
        self.name = name

    def choice(self, val):
        """ Returns the locator for a choice

        Args:
            val: A string representing the ``value`` attribute of the specific radio
                element.

        Returns: A string containing the XPATH of the specific radio element.

        """
        return "//input[@name='%s' and @value='%s']" % (self.name, val)

    def observer_wait(self, val):
        sel.detect_observed_field(self.choice(val))


@fill.method((Radio, object))
def _fill_radio(radio, value):
    """How to fill a radio button group (by selecting the given value)"""
    logger.debug(' Filling in Radio (%s) with value "%s"' % (radio.name, value))
    sel.click(radio.choice(value))
    radio.observer_wait(value)


class Tree(object):
    """ A class directed at CFME Tree elements

    The Tree class aims to deal with all kinds of CFME trees, at time of writing there
    are two distinct types. One which uses ``<table>`` elements and another which uses
    ``<ul>`` elements.

    Args:
        locator: This is a locator object pointing to either the outer ``<table>`` or
            ``<ul>`` element which contains the rest of the table.

    Returns: A :py:class:`Tree` object.

    A Tree object is set up by using a locator which contains the node elements. This element
    will usually be a ``<ul>`` in the case of a Dynatree, or a ``<table>`` in the case of a
    Legacy tree.

    Usage:

         tree = web_ui.Tree((By.XPATH, '//table//tr[@title="Datastore"]/../..'))

    The path can then be navigated to return the last object in the path list, like so::

        tree.click_path('Automation', 'VM Lifecycle Management (VMLifecycle)',
            'VM Migrate (Migrate)')

    Each path element will be expanded along the way, but will not be clicked.

    When used in a :py:class:`Form`, a list of path tuples is expected in the form fill data.
    The paths will be passed individually to :py:meth:`Tree.select_node`::

        form = Form(fields=[
            ('tree_field', List(locator)),
        ])

        form_fill_data = {
            'tree_field': [
                ('Tree Node', 'Value'),
                ('Tree Node', 'Branch Node', 'Value'),
            ]
        ]

    Note:
      For legacy trees, the first element is often ignored as it is not a proper tree
      element ie. in Automate->Explorer the Datastore element doesn't really exist, so we
      omit it from the click map.

      Legacy trees rely on a complex ``<table><tbody><tr><td>`` setup. We class a ``<tbody>``
      as a node.

    Note: Dynatrees, rely on a ``<ul><li>`` setup. We class a ``<li>`` as a node.

    """

    def __init__(self, locator):
        self.locator = locator

    def _detect(self):
        """ Detects which type of tree is being used

        On invocation, first determines which type of Tree object it is dealing
        with and then sets the internal variables to match elements of the specific tree class.

        There are currently 4 attributes needed in the tree classes.

        * expandable: the element to check if the tree is expanded/collapsed.
        * is_expanded_condition: a tuple containing the element attribute and value to
          identify that an element **is** expanded.
        * node_search: an XPATH which describes a node, needing expansion with format specifier for
          matching.
        * click_expand: the element to click on to expand the tree at that level.
        """
        self.root_el = sel.element(self.locator)
        if sel.tag(self.root_el) == 'ul':
            # Dynatree
            self.expandable = 'span'
            self.is_expanded_condition = ('class', 'dynatree-expanded')
            self.node_search = "//li/span/a[contains(., '%s')]/../.."
            self.click_expand = "span/span"
            self.leaf = "span/a"
            self.node_select_support = False
        elif sel.tag(self.root_el) == 'table':
            # Legacy Tree
            self.expandable = 'tr/td[1]/img'
            self.is_expanded_condition = ('src', 'open.png')
            self.node_search = "//tbody/tr/td/table/tbody/tr/td[4]/span[contains(., '%s')]/../../.."
            self.click_expand = "tr/td[1]/img"
            self.leaf = "tr/td/span"
            self.node_select_support = True
            self.node_select = "tr/td[2]/img"
            self.node_images = {'select': ['iconCheckAll', 'radio_on'],
                                'deselect': ['iconUncheckAll', 'radio_off']}
        else:
            raise exceptions.TreeTypeUnknown(
                'The locator described does not point to a known tree type')

    def _is_expanded(self, el):
        """ Checks to see if an element is expanded

        Args:
            el: The element to check.

        Returns: ``True`` if the element is expanded, ``False`` if not.
        """
        meta = sel.element(self.expandable, root=el)
        if self.is_expanded_condition[1] in sel.get_attribute(
                meta, self.is_expanded_condition[0]):
            return True
        else:
            return False

    def _expand(self, el):
        """ Expands a tree node

        Checks if a tree node needs expanding and then expands it.

        Args:
            el: The element to expand.
        """
        if not self._is_expanded(el):
            sel.click(sel.element(self.click_expand, root=el))

    def expose_path(self, *path, **kwargs):
        """ Clicks through a series of elements in a path.

        Clicks through a tree, by expanding the levels in a single straight path and
        returns the final element without clicking it.

        .. note: This is a recursive function.

        The function determines if it is starting at the root element, or if it is in the
        middle of a path, this is required because the first entrace into a tree needs to be
        treated different. Plus we need to set the root element because one will not be supplied.

        The next step is to check if the current element is expanded and if not, to
        expand it.

        Finally we search for the next element in the list and then recursively
        call the :py:meth:`click_path` function again, this time with the reduced path, and
        substituting the matching element as the new root element.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
            root: The root path to begin at. This is usually not set manually
                and is required for the recursion.

        Returns: The element at the end of the tree.

        Raises:
            cfme.exceptions.CandidateNotFound: A candidate in the tree could not be found to
                continue down the path.
            cfme.exceptions.TreeTypeUnknown: A locator was passed to the constructor which
                does not correspond to a known tree type.

        """

        #The detect here is required every time to avoid a StaleElementException if the
        #Tree goes off screen and returns.
        self._detect()

        root = kwargs.get('root', None)
        root_el = root if root else self.root_el
        path = list(path)

        if root:
            self._expand(root_el)

        needle = path.pop(0)
        xpath = self.node_search % needle

        try:
            new_leaf = sel.element(xpath, root=root_el)
        except sel_exceptions.NoSuchElementException:
            raise exceptions.CandidateNotFound("%s: could not be found in the tree." % needle)

        if path:
            return self.expose_path(*path, root=new_leaf)
        else:
            return new_leaf

    def click_path(self, *path, **kwargs):
        """ Exposes a path and then clicks it.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
            root: The root path to begin at. This is usually not set manually
                and is required for the recursion during :py:meth:expose_path:.

        Returns: The leaf web element.

        """
        root = kwargs.get('root', None)
        leaf = self.expose_path(*path, root=root)
        sel.click(sel.element(self.leaf, root=leaf))
        return leaf

    def _select_or_deselect_node(self, *path, **kwargs):
        """ Selects or deselects a node.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
            select: If ``True``, the node is selected, ``False`` the node is deselected.
            root: The root path to begin at. This is usually not set manually
                and is required for the recursion during :py:meth:expose_path:.
        """
        self._detect()
        select = kwargs.get('select', False)
        if self.node_select_support:
            root = kwargs.get('root', None)
            leaf = self.expose_path(*path, root=root)
            leaf_chkbox = sel.element(self.node_select, root=leaf)
            for img_type in self.node_images['select']:
                if img_type in sel.get_attribute(leaf_chkbox, 'src'):
                    node_open = True
                else:
                    node_open = False
            if select is not node_open:
                sel.click(leaf_chkbox)
        else:
            raise Exception('This Tree type does not support select yet.')

    def select_node(self, *path, **kwargs):
        """ Convenience function to select a node

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
            root: The root path to begin at. This is usually not set manually
                and is required for the recursion during :py:meth:expose_path:.
        """
        kwargs.update({'select': True})
        self._select_or_deselect_node(*path, **kwargs)

    def deselect_node(self, *path, **kwargs):
        """ Convenience function to deselect a node

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
            root: The root path to begin at. This is usually not set manually
                and is required for the recursion during :py:meth:expose_path:.
        """
        kwargs.update({'select': False})
        self._select_or_deselect_node(*path, **kwargs)


@fill.method((Tree, object))
def _fill_tree(tree, values):
    # Assume a list of paths, select_node on each path
    for path in values:
        logger.debug(' Navigating the tree: %s' % " -> ".join(path))
        tree.select_node(*path)


class InfoBlock(object):
    """ A helper class for information blocks on pages

    This class is able to work with both ``detail`` type information blocks and
    ``form`` style information blocks. It is invoked with a single argument describing
    the type of blocks to be addressed and adjusts the html elements accordingly.

    Args:
        itype: The type of information blocks to address, either ``detail`` or ``form``.

    Returns: Either a string if the element contains just text, or the element.

    Raises:
        exceptions.BlockTypeUnknown: If the Block type requested by itype is unknown.
        exceptions.ElementOrBlockNotFound: If the Block or Key requested is not found.
        exceptions.NoElementsInsideValue: If the Key contains no elements.

    An InfoBlock only needs to know the **type** of InfoBlocks you are trying to address.
    You can then return either text, the first element inside the value or all elements.

    Usage:

        block = web_ui.InfoBlock("form")

        block.text('Basic Information', 'Hostname')
        block.element('Basic Information', 'Company Name')
        block.elements('NTP Servers', 'Servers')

    These will return a string, a webelement and a List of webelements respectively.

    """
    def __init__(self, itype):
        if itype == "detail":
            self._box_locator = '//div[@class="modbox"]/h2[@class="modtitle"][contains(., "%s")]/..'
            self._pair_locator = 'table/tbody/tr/td[1][@class="label"][.="%s"]/..'
            self._value_locator = 'td[2]'
        elif itype == "form":
            self._box_locator = '//fieldset/p[@class="legend"][contains(., "%s")]/..'
            self._pair_locator = 'table/tbody/tr/td[1][@class="key"][.="%s"]/..'
            self._value_locator = 'td[2]'
        else:
            raise exceptions.BlockTypeUnknown("The block type requested is unknown")

    def get_el_or_els(self, ident, all_els=False):
        """ Returns either a single element or a list of elements from a Value.

        Args:
            ident: A List of identifiers.
            all_els: A Boolean describing if the function should return a single element
                or a list of elements.
        Returns: Either a single element or a List of elements.
        """
        try:
            els = sel.elements("*", root=self.container(ident))
        except sel_exceptions.NoSuchElementException:
            raise exceptions.NoElementsInsideValue("No Elements are found inside the value")
        if els == []:
            return None
        if all_els:
            return els
        else:
            return els[0]

    def elements(self, *ident):
        """ A Convenience wrapper for :py:meth:get_el_or_els

        Args:
            *indent: Identifiers in the form of strings.
        Returns: Either a single element or a List of elements.
        """
        return self.get_el_or_els(ident, all_els=True)

    def element(self, *ident):
        """ A Convenience wrapper for :py:meth:get_el_or_els

        Args:
            *indent: Identifiers in the form of strings.
        Returns: Either a single element or a List of elements.
        """
        return self.get_el_or_els(ident, all_els=False)

    def text(self, *ident):
        """ Returns the textual component of a Value

        Args:
            *indent: Identifiers in the form of strings.
        Returns: A string of the elements in the Value.
        """
        return self.container(ident).text

    def container(self, ident):
        """ Searches for a key/value pair inside a header/block arrangement.

        Args:
            indent: Identifiers in the form of a list of strings.
        Returns: The Value as a WebElement
        """
        xpath_core = "%s/%s/%s" % (self._box_locator, self._pair_locator, self._value_locator)
        xpath = xpath_core % (ident[0], ident[1])
        try:
            el = sel.element(xpath)
        except sel_exceptions.NoSuchElementException:
            raise exceptions.ElementOrBlockNotFound(
                "Either the element of the block could not be found")
        return el


class Quadicon(object):
    """
    Represents a single quadruple icon in the CFME UI.

    A Quadicon contains multiple quadrants. These are accessed via attributes.
    The qtype is currently one of the following and determines which attribute names
    are present. They are mapped internally and can be reassigned easily if the UI changes.

    A Quadicon is used by defining the name of the icon and the type. After that, it can be used
    to obtain the locator of the Quadicon, or query its quadrants, via attributes.

    Args:
       name: The label of the icon.
       qtype: The type of the quad icon.

    Usage:

        qi = web_ui.Quadicon('hostname.local', 'host')
        qi.creds
        click(qi)

    .. rubric:: Known Quadicon Types and Attributes

    * **host** - *from the infra/host page* - has quads:

      * a. **no_vm** - Number of VMs
      * b. **state** - The current state of the host
      * c. **vendor** - The vendor of the host
      * d. **creds** - If the creds are valid

    * **infra_prov** - *from the infra/providers page* - has quads:

      * a. **no_host** - Number of hosts
      * b. *Blank*
      * c. **vendor** - The vendor of the provider
      * d. **creds** - If the creds are valid

    * **vm** - *from the infra/virtual_machines page* - has quads:

      * a. **os** - The OS of the vm
      * b. **state** - The current state of the vm
      * c. **vendor** - The vendor of the vm's host
      * d. **no_snapshot** - The number of snapshots
      * g. **policy** - The state of the policy

    * **cloud_prov** - *from the cloud/providers page* - has quads:

      * a. **no_instance** - Number of instances
      * b. **no_image** - Number of machine images
      * c. **vendor** - The vendor of the provider
      * d. **creds** - If the creds are valid

    * **instance** - *from the cloud/instances page* - has quads:

      * a. **os** - The OS of the instance
      * b. **state** - The current state of the instance
      * c. **vendor** - The vendor of the instance's host
      * d. **no_snapshot** - The number of snapshots
      * g. **policy** - The state of the policy

    Returns: A :py:class:`Quadicon` object.
    """

    _quads = {
        "host": {
            "no_vm": ("a", 'txt'),
            "state": ("b", 'img'),
            "vendor": ("c", 'img'),
            "creds": ("d", 'img'),
        },
        "infra_prov": {
            "no_host": ("a", 'txt'),
            "vendor": ("c", 'img'),
            "creds": ("d", 'img'),
        },
        "vm": {
            "os": ("a", 'img'),
            "state": ("b", 'img'),
            "vendor": ("c", 'img'),
            "no_snapshot": ("d", 'txt'),
            "policy": ("g", 'img'),
        },
        "cloud_prov": {
            "no_vm": ("a", 'txt'),
            "no_image": ("b", 'txt'),
            "vendor": ("b", 'img'),
            "creds": ("d", 'img'),
        },
        "instance": {
            "os": ("a", 'img'),
            "state": ("b", 'img'),
            "vendor": ("c", 'img'),
            "no_snapshot": ("d", 'txt'),
            "policy": ("g", 'img'),
        },
    }

    def __init__(self, name, qtype):
        self._name = name
        self._qtype = qtype
        self._quad_data = self._quads[self._qtype]

    def checkbox(self):
        """ Returns:  a locator for the internal checkbox for the quadicon"""
        return "//input[@type='checkbox' and ../../..//a[@title='%s']]" % self._name

    def locate(self):
        """ Returns:  a locator for the quadicon itself"""
        return "//div[@id='quadicon' and ../../..//a[@title='%s']]" % self._name

    def _locate_quadrant(self, corner):
        """ Returns: a locator for the specific quadrant"""
        return "//div[contains(@class, '%s72') and ../../../..//a[@title='%s']]" \
            % (corner, self._name)

    def __getattr__(self, name):
        """ Queries the quadrants by name

        Args:
            name: The name of the quadrant identifier, as defined above.
        Returns: A string containing a representation of what is in the quadrant.
        """
        if name in self._quad_data:
            corner, rtype = self._quad_data[name]
            locator = self._locate_quadrant(corner)
            #.. We have to have a try/except here as some quadrants
            #.. do not exist if they have no data, e.g. current_state in a host
            #.. with no credentials.
            try:
                el = sel.element(locator)
            except sel_exceptions.NoSuchElementException:
                return None
            if rtype == 'txt':
                return el.text
            if rtype == 'img':
                img_el = sel.element('.//img', root=el)
                img_name = sel.get_attribute(img_el, 'src')
                path, filename = os.path.split(img_name)
                root, ext = os.path.splitext(filename)
                return root
        else:
            return object.__getattribute__(self, name)

    def __str__(self):
        return self.locate()


class Select(SeleniumSelect, object):
    """ A poor man's Proxy class for the real selenium Select() object.

    We differ in one important point, that we can instantiate the object
    without it being present on the page. The object is located at the beginning
    of each function call.

    Args:
        loc: A locator.

    Returns: A :py:class:`cfme.web_ui.Select` object.
    """

    def __init__(self, loc, multi=False):
        self.loc = loc
        self.is_multiple = multi

    @property
    def _el(self):
        el = sel.element(self.loc)
        ActionChains(browser()).move_to_element(el).perform()
        return el

    def observer_wait(self):
        sel.detect_observed_field(self.loc)


@fill.method((Select, object))
def fill_select(slist, val):
    stype = type(slist)
    logger.debug('  Filling in %s with value %s' % (stype, val))
    sel.select(slist, val)
    slist.observer_wait()


class DHTMLSelect(Select):
    """
    A special Select object for CFME's icon enhanced DHTMLx Select elements.

    Args:
        loc: A locator.

    Returns: A :py:class:`cfme.web_ui.DHTMLSelect` object.
    """

    @staticmethod
    def _log(meth, val=None):
        if val:
            val_string = " with value %s" % val
        logger.debug('Filling in DHTMLSelect using (%s)%s' % (meth, val_string))

    def _get_select_name(self):
        """ Get's the name reference of the element from its hidden attribute.
        """

        root_el = sel.element(self.loc)
        el = sel.element("div/input[2]", root=root_el)
        name = sel.get_attribute(el, 'name')
        return name

    @property
    def all_selected_options(self):
        """ Returns all selected options.

        Note: Since the DHTML select can only have one option selected at a time, we
            simple return the first element (the only element).
        Returns: A Web element.
        """
        return [self.first_selected_option]

    @property
    def first_selected_option(self):
        """ Returns the first selected option in the DHTML select

        Note: In a DHTML select, there is only one option selectable at a time.

        Returns: A webelement.
        """
        name = self._get_select_name()
        return browser().execute_script(
            'return %s.getOptionByIndex(%s.getSelectedIndex()).content' % (name, name))

    @property
    def options(self):
        """ Returns a list of options of the select as webelements.

        Returns: A list of Webelements.
        """
        name = self._get_select_name()
        return browser().execute_script('return %s.DOMlist.children' % name)

    def select_by_index(self, index, _cascade=None):
        """ Selects an option by index.

        Args:
            index: The select element's option by index.
        """
        name = self._get_select_name()
        if index is not None:
            if not _cascade:
                self._log('index', index)
            browser().execute_script('%s.selectOption(%s)' % (name, index))

    def select_by_visible_text(self, text):
        """ Selects an option by visible text.

        Args:
            text: The select element option's visible text.
        """
        name = self._get_select_name()
        if text is not None:
            self._log('visible_text', text)
            value = browser().execute_script('return %s.getOptionByLabel("%s").value'
                                             % (name, text))
            self.select_by_value(value, _cascade=True)

    def select_by_value(self, value, _cascade=None):
        """ Selects an option by value.

        Args:
            value: The select element's option value.
        """
        name = self._get_select_name()
        if value is not None:
            if not _cascade:
                self._log('value', value)
            index = browser().execute_script('return %s.getIndexByValue("%s")' % (name, value))
            self.select_by_index(index, _cascade=True)


class Filter(Form):
    """ Filters requests pages

    This class inherits Form as its base and adds a few methods to assist in filtering
    request pages.

    Usage:
        f = Filter(fields=[
            ('type', Select('//select[@id="type_choice"]')),
            ('approved', '//input[@id="state_choice__approved"]'),
            ('denied', '//input[@id="state_choice__denied"]'),
            ('pending_approval', '//input[@id="state_choice__pending_approval"]'),
            ('date', Select('//select[@id="time_period"]')),
            ('reason', '//input[@id="reason_text"]'),
        ])

        f.apply_filter(type="VM Clone", approved=False,
            pending_approval=False, date="Last 24 Hours", reason="Just Because")
    """

    buttons = {
        'default_off': '//div[@id="buttons_off"]/li/a/img[@alt="Set filters to default"]',
        'default_on': '//div[@id="buttons_on"]/li/a/img[@alt="Set filters to default"]',
        'apply': '//div[@id="buttons_on"]//a[@title="Apply the selected filters"]',
        'reset': '//div[@id="buttons_on"]//a[@title="Reset filter changes"]'
    }

    def default_filter(self):
        """ Method to reset the filter back to defaults.
        """
        sel.click(self.buttons['default_off'])
        sel.click(self.buttons['default_on'])

    def reset_filter(self):
        """ Method to reset the changes to the filter since last applying.
        """
        sel.click(self.buttons['reset'])

    def apply_filter(self, **kwargs):
        """ Method to apply a filter.

        First resets the filter to default and then applies the filter.

        Args:
            **kwargs: A dictionary of form elements to fill and their values.
        """
        self.default_filter()
        self.fill(kwargs)
        sel.click(self.buttons['apply'])


class MultiSelect(Region):
    '''Represents a UI widget where there are two select boxes, one with
    possible selections, and another with selected items.  Has two
    arrow buttons to move items between the two'''

    def __init__(self,
                 available_select=None,
                 selected_select=None,
                 select_arrow=None,
                 deselect_arrow=None):
        self.available_select = available_select
        self.selected_select = selected_select
        self.select_arrow = select_arrow
        self.deselect_arrow = deselect_arrow


@sel.select.method((MultiSelect, Sequence))
def select_multiselect(ms, values):
    sel.select(ms.available_select, values)
    sel.click(ms.select_arrow)


@fill.method((MultiSelect, Sequence))
def fill_multiselect(ms, items):
    sel.select(ms, items)
