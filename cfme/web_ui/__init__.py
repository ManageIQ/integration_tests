"""Provides a number of objects to help with managing certain elements in the CFME UI.

 Specifically there are two categories of objects, organizational and elemental.

* **Organizational**

  * :py:class:`Region`
  * :py:mod:`cfme.web_ui.menu`

* **Elemental**

  * :py:class:`AngularCalendarInput`
  * :py:class:`AngularSelect`
  * :py:class:`ButtonGroup`
  * :py:class:`Calendar`
  * :py:class:`ColorGroup`
  * :py:class:`CheckboxTable`
  * :py:class:`CheckboxSelect`
  * :py:class:`DHTMLSelect`
  * :py:class:`DriftGrid`
  * :py:class:`DynamicTable`
  * :py:class:`EmailSelectForm`
  * :py:class:`Filter`
  * :py:class:`Form`
  * :py:class:`InfoBlock`
  * :py:class:`Input`
  * :py:class:`MultiFill`
  * :py:class:`Quadicon`
  * :py:class:`Radio`
  * :py:class:`ScriptBox`
  * :py:class:`Select`
  * :py:class:`ShowingInputs`
  * :py:class:`SplitCheckboxTable`
  * :py:class:`SplitTable`
  * :py:class:`StatusBox`
  * :py:class:`Table`
  * :py:class:`Tree`
  * :py:mod:`cfme.web_ui.accordion`
  * :py:mod:`cfme.web_ui.cfme_exception`
  * :py:mod:`cfme.web_ui.expression_editor`
  * :py:mod:`cfme.web_ui.flash`
  * :py:mod:`cfme.web_ui.form_buttons`
  * :py:mod:`cfme.web_ui.jstimelines`
  * :py:mod:`cfme.web_ui.listaccordion`
  * :py:mod:`cfme.web_ui.menu`
  * :py:mod:`cfme.web_ui.mixins`
  * :py:mod:`cfme.web_ui.paginator`
  * :py:mod:`cfme.web_ui.search`
  * :py:mod:`cfme.web_ui.tabstrip`
  * :py:mod:`cfme.web_ui.toolbar`

"""

import atexit
import os
import re
import types
from datetime import date
from collections import Sequence, Mapping, Callable
from tempfile import NamedTemporaryFile
from xml.sax.saxutils import quoteattr

from cached_property import cached_property
from selenium.common import exceptions as sel_exceptions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.file_detector import LocalFileDetector
from multimethods import multimethod, multidispatch, Anything

import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions, js
from cfme.fixtures.pytest_selenium import browser
# For backward compatibility with code that pulls in Select from web_ui instead of sel
from cfme.fixtures.pytest_selenium import Select
from utils import attributize_string, castmap, normalize_space, version
from utils.log import logger
from utils.pretty import Pretty


class Selector(object):
    """
    Special Selector object allowing object resolution on attr access

    The Selector is a simple class which allows a 'super' widget to support multiple
    implementations. This is achieved by the use of a ``decide`` method which accesses
    attrs of the object set by the ``__init__`` of the child class. These attributes
    are then used to decide which type of object is on a page. In some cases, this can
    avoid a version pick if the information used to instantiate both old and new implementations
    can be identical. This is most noteably if using an "id" which remains constant from
    implementation to implementation.

    As an example, imagine the normal "checkbox" is replaced wit ha fancy new web 2.0
    checkbox. Both have an "input" element, and give it the same "id". When the decide method is
    invoked, the "id" is inspected and used to determine if it is an old or a new style widget.
    We then set a hidden attribute of the super widget and proxy all further attr requests to
    that object.

    This means that in order for things to behave as expect ALL implementations must also expose
    the same "public" API.
    """

    def __init__(self):
        self._obj = None

    def __getattr__(self, name):
        if not self._obj:
            self._obj = self.decide()
        return getattr(self._obj, name)

    def decide(self):
        raise Exception('This widget does not have a "decide" method which is mandatory')


class Region(Pretty):
    """
    Base class for all UI regions/pages

    Args:
        locators: A dict of locator objects for the given region
        title: A string containing the title of the page,
               or a versioned dict of page title strings
        identifying_loc: Single locator key from locators used by :py:meth:`Region.is_displayed`
                         to check if the region is currently visible

    Usage:

        page = Region(locators={
            'configuration_button': (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']"),
            'discover_button': (By.CSS_SELECTOR,
                "tr[title='Discover Cloud Providers']>td.td_btn_txt>" "div.btn_sel_text")
            },
            title='Cloud Providers',
            identifying_loc='discover_button'
        )

    The elements can then accessed like so::

        page.configuration_button

    Locator attributes will return the locator tuple for that particular element,
    and can be passed on to other functions, such as :py:func:`element` and :py:func:`click`.

    Note:

        When specifying a region title, omit the "Cloudforms Management Engine: " or "ManageIQ: "
        prefix. They're included on every page, and different for the two versions of the appliance,
        and :py:meth:`is_displayed` strips them off before checking for equality.

    """
    pretty_attrs = ['title']

    def __getattr__(self, name):
        if hasattr(self, 'locators') and name in self.locators:
            locator = self.locators[name]
            if isinstance(locator, dict):
                return version.pick(locator)
            else:
                return locator
        else:
            raise AttributeError("Region has no attribute named " + name)

    def __init__(self, locators=None, title=None, identifying_loc=None, **kwargs):
        self.locators = locators
        self.identifying_loc = identifying_loc
        self._title = title
        self.infoblock = InfoBlock  # Legacy support

    @property
    def title(self):
        # support title being a versioned dict
        if isinstance(self._title, dict):
            self._title = version.pick(self._title)
        return self._title

    def is_displayed(self):
        """
        Checks to see if the region is currently displayed.

        Returns: A boolean describing if the region is currently displayed
        """
        if not self.identifying_loc and not self.title:
            logger.warning("Region doesn't have an identifying locator or title, "
                "can't determine if current page.")
            return True

        # All page titles have a prefix; strip it off
        try:
            browser_title = browser().title.split(': ', 1)[1]
        except IndexError:
            browser_title = None

        if self.identifying_loc and sel.is_displayed(
                self.locators[self.identifying_loc], _no_deeper=True):
            ident_match = True
        else:
            if not self.title:
                logger.info('Identifying locator for region not found')
            else:
                logger.info('Identifying locator for region %s not found', self.title)
            ident_match = False

        if self.title is None:
            # If we don't have a title we can't match it, and some Regions are multi-page
            # so we can't have a title set.
            title_match = True
        elif self.title and browser_title == self.title:
            title_match = True
        else:
            logger.info("Title %s doesn't match expected title %s", browser_title, self.title)
            title_match = False
        return title_match and ident_match


def get_context_current_page():
    """
    Returns the current page name

    Returns: A string containing the current page name
    """
    url = browser().current_url()
    stripped = url.lstrip('https://')
    return stripped[stripped.find('/'):stripped.rfind('?')]


class CachedTableHeaders(object):
    """the internal cache of headers

    This allows columns to be moved and the Table updated. The :py:attr:`headers` stores
    the header cache element and the list of headers are stored in _headers. The
    attribute header_indexes is then created, before finally creating the items
    attribute.
    """
    def __init__(self, table):
        self.headers = sel.elements('td | th', root=table.header_row)
        self.indexes = {
            attributize_string(cell.text): index
            for index, cell in enumerate(self.headers)}


class Table(Pretty):
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
        hidden_locator: If the table can disappear, you probably want ot set this param as it
            instructs the table that if it cannot find the table on the page but the element
            represented by ``hidden_locator`` is visible, it assumes no data and returns no rows.

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

    pretty_attrs = ['_loc']

    def __init__(self, table_locator, header_offset=0, body_offset=0, hidden_locator=None):
        self._headers = None
        self._header_indexes = None
        self._loc = table_locator
        self.header_offset = int(header_offset)
        self.body_offset = int(body_offset)
        self.hidden_locator = hidden_locator

    @property
    def header_row(self):
        """Property representing the ``<tr>`` element that contains header cells"""
        # thead/tr containing header data
        # xpath is 1-indexed, so we need to add 1 to the offset to get the correct row
        return sel.element('./thead/tr[{}]'.format(self.header_offset + 1), root=sel.element(self))

    @property
    def body(self):
        """Property representing the ``<tbody>`` element that contains body rows"""
        # tbody containing body rows
        return sel.element('./tbody', root=sel.element(self))

    @cached_property
    def _headers_cache(self):
        return CachedTableHeaders(self)

    def verify_headers(self):
        """Verifies whether the headers in the table correspond with the cached ones."""
        current_headers = CachedTableHeaders(self)
        cached_headers = self._headers_cache
        if current_headers.indexes != cached_headers.indexes:
            raise exceptions.UsingSharedTables(
                ('{cn} suspects that you are using shared tables! '
                'That means you are using one {cn} instance to represent different UI tables. '
                'This is not possible due to the header caching, but also wrong from the '
                'design point of view. Please, create separate instances of {cn} for EACH table '
                'in the user interface.').format(cn=type(self).__name__))

    def _update_cache(self):
        """refresh the cache in case we know its stale"""
        try:
            del self._headers_cache
        except AttributeError:
            pass  # it's not cached, dont try to be eager
        else:
            self._headers_cache

    @property
    def headers(self):
        """List of ``<td>`` or ``<th>`` elements in :py:attr:`header_row`

         """
        return self._headers_cache.headers

    @property
    def header_indexes(self):
        """Dictionary of header name: column index for this table's rows

        Derived from :py:attr:`headers`

        """
        return self._headers_cache.indexes

    def locate(self):
        return sel.move_to_element(self._loc)

    @property
    def _root_loc(self):
        return self.locate()

    def rows(self):
        """A generator method holding the Row objects

        This generator yields Row objects starting at the first data row.

        Yields:
            :py:class:`Table.Row` object corresponding to the next row in the table.
        """
        try:
            index = self.body_offset
            row_elements = sel.elements('./tr', root=self.body)
            for row_element in row_elements[index:]:
                yield self.create_row_from_element(row_element)
        except (exceptions.CannotScrollException, NoSuchElementException):
            if self.hidden_locator is None:
                # No hiding is documented here, so just explode
                raise
            elif not sel.is_displayed(self.hidden_locator):
                # Hiding is documented but the element that signalizes that it is all right is not
                # present so explode too.
                raise
            else:
                # The table is not present but there is something that signalizes it is all right
                # but no data.
                return

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
            if isinstance(header, basestring):
                return getattr(matching_cell_rows[0], header)
            else:
                return matching_cell_rows[0][header]
        except IndexError:
            return None

    def find_rows_by_cells(self, cells, partial_check=False):
        """A fast row finder, based on cell content.

        If you pass a regexp as a value, then it will be used with its ``.match()`` method.

        Args:
            cells: A dict of ``header: value`` pairs or a sequence of
                nested ``(header, value)`` pairs.
            partial_check: If to use the ``in`` operator rather than ``==``.

        Returns: A list of containing :py:class:`Table.Row` objects whose contents
            match all of the header: value pairs in ``cells``

        """
        # accept dicts or supertuples
        cells = dict(cells)
        cell_text_loc = (
            './/td/descendant-or-self::*[contains(normalize-space(text()), "{}")]/ancestor::tr[1]')
        matching_rows_list = list()
        for value in cells.values():
            # Get all td elements that contain the value text
            matching_elements = sel.elements(cell_text_loc.format(value),
                root=sel.move_to_element(self._root_loc))
            if matching_elements:
                matching_rows_list.append(set(matching_elements))

        # Now, find the common row elements that matched all the input cells
        # (though not yet matching values to headers)
        if not matching_rows_list:
            # If none matched, short out
            return []

        rows_elements = list(reduce(lambda set1, set2: set1 & set2, matching_rows_list))

        # Convert them to rows
        # This is slow, which is why we do it after reducing the row element pile,
        # and not when building matching_rows_list, but it makes comparing header
        # names and expected values easy
        rows = [self.create_row_from_element(element) for element in rows_elements]

        # Only include rows where the expected values are in the right columns
        matching_rows = list()

        def matching_row_filter(heading, value):
            text = normalize_space(row[heading].text)
            if isinstance(value, re._pattern_type):
                return value.match(text) is not None
            elif partial_check:
                return value in text
            else:
                return text == value

        for row in rows:
            if all(matching_row_filter(*cell) for cell in cells.items()):
                matching_rows.append(row)

        return matching_rows

    def find_row_by_cells(self, cells, partial_check=False):
        """Find the first row containing cells

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`

        Returns: The first matching row found, or None if no matching row was found

        """
        try:
            rows = self.find_rows_by_cells(cells, partial_check=partial_check)
            return rows[0]
        except IndexError:
            return None

    def click_rows_by_cells(self, cells, click_column=None, partial_check=False):
        """Click the cell at ``click_column`` in the rows matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
            click_column: Which column in the row to click, defaults to None,
                which will attempt to click the row element

        Note:
            The value of click_column can be a string or an int, and will be passed directly to
            the item accessor (``__getitem__``) for :py:class:`Table.Row`

        """
        rows = self.find_rows_by_cells(cells, partial_check=partial_check)
        if click_column is not None:
            rows = [row[click_column] for row in rows]

        for row in rows:
            if row is None:
                self.verify_headers()  # Suspected shared table use
            sel.click(row)

    def click_row_by_cells(self, cells, click_column=None, partial_check=False):
        """Click the cell at ``click_column`` in the first row matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
            click_column: See :py:meth:`Table.click_rows_by_cells`

        """
        row = self.find_row_by_cells(cells, partial_check=partial_check)
        if row is None:
            raise NameError('No row matching {} found'.format(repr(cells)))
        elif click_column is not None:
            row = row[click_column]

        if row is None:
            self.verify_headers()   # Suspected shared table use
        sel.click(row)

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
                    failed_clicks.append("{}:{}".format(header, value))
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
            # This *might* lead to the shared table. So be safe here.
            self.verify_headers()
            return False

    class Row(Pretty):
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
        pretty_attrs = ['row_element', 'table']

        def __init__(self, row_element, parent_table):
            self.table = parent_table
            self.row_element = row_element

        @property
        def columns(self):
            """A list of WebElements corresponding to the ``<td>`` elements in this row"""
            return sel.elements('./td', root=self.row_element)

        def __getattr__(self, name):
            """
            Returns Row element by header name
            """
            try:
                return self.columns[self.table.header_indexes[attributize_string(name)]]
            except (KeyError, IndexError):
                # Suspected shared table use
                self.table.verify_headers()
                # If it did not fail at that time, reraise
                raise

        def __getitem__(self, index):
            """
            Returns Row element by header index or name
            """
            try:
                return self.columns[index]
            except TypeError:
                # Index isn't an int, assume it's a string
                return getattr(self, attributize_string(index))
            except IndexError:
                # Suspected shared table use
                self.table.verify_headers()
                # If it did not fail at that time, reraise
                raise

        def __str__(self):
            return ", ".join(["'{}'".format(el.text) for el in self.columns])

        def __eq__(self, other):
            if isinstance(other, type(self)):
                # Selenium elements support equality checks, so we can, too.
                return self.row_element == other.row_element
            else:
                return id(self) == id(other)

        def locate(self):
            # table.create_row_from_element(row_instance) might actually work...
            return sel.move_to_element(self.row_element)


class CAndUGroupTable(Table):
    """Type of tables used in C&U, not tested in others.

    Provides ``.groups()`` generator which yields group objects. A group objects consists of the
    rows that are located in the group plus the summary informations. THe main principle is that
    all the rows inside group are stored in group object's ``.rows`` and when the script encounters
    the end of the group, it will store the summary data after the data rows as attributes, so eg.
    ``Totals:`` will become ``group.totals``. All the rows are represented as dictionaries.
    """
    class States:
        NORMAL_ROWS = 0
        GROUP_SUMMARY = 1

    class Group(object):
        def __init__(self, group_id, headers, rows, info_rows):
            self.id = group_id
            self.rows = [dict(zip(headers, row)) for row in rows]
            info_headers = headers[1:]
            for info_row in info_rows:
                name = info_row[0]
                rest = info_row[1:]
                data = dict(zip(info_headers, rest))
                group_attr = attributize_string(name)
                setattr(self, group_attr, data)

        def __repr__(self):
            return '<CAndUGroupTable.Group {}'.format(repr(self.id))

    def paginated_rows(self):
        from cfme.web_ui import paginator
        for page in paginator.pages():
            for row in self.rows():
                yield row

    def find_group(self, group_id):
        """Finds a group by its group ID (the string that is alone on the line)"""
        for group in self.groups():
            if group.id == group_id:
                return group_id
        else:
            raise KeyError('Group {} not found'.format(group_id))

    def groups(self):
        headers = map(sel.text, self.headers)
        headers_length = len(headers)
        rows = self.paginated_rows()
        current_group_rows = []
        current_group_summary_rows = []
        current_group_id = None
        state = self.States.NORMAL_ROWS
        while True:
            try:
                row = rows.next()
            except StopIteration:
                if state == self.States.GROUP_SUMMARY:
                    row = None
                else:
                    break
            if state == self.States.NORMAL_ROWS:
                if len(row.columns) == headers_length:
                    current_group_rows.append(tuple(map(sel.text, row.columns)))
                else:
                    # Transition to the group summary
                    current_group_id = sel.text(row.columns[0]).strip()
                    state = self.States.GROUP_SUMMARY
            elif state == self.States.GROUP_SUMMARY:
                # row is None == we are at the end of the table so a slightly different behaviour
                if row is not None:
                    fc_length = len(sel.text(row.columns[0]).strip())
                if row is None or fc_length == 0:
                    # Done with group
                    yield self.Group(
                        current_group_id, headers, current_group_rows, current_group_summary_rows)
                    current_group_rows = []
                    current_group_summary_rows = []
                    current_group_id = None
                    state = self.States.NORMAL_ROWS
                else:
                    current_group_summary_rows.append(tuple(map(sel.text, row.columns)))
            else:
                raise RuntimeError('This should never happen')

        if current_group_id is not None or current_group_rows or current_group_summary_rows:
            raise ValueError(
                'GroupTable could not be parsed properly: {} {} {}'.format(
                    current_group_id, repr(current_group_rows), repr(current_group_summary_rows)))


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

        self._header_loc, header_offset = header_data
        self._body_loc, body_offset = body_data
        self.header_offset = int(header_offset)
        self.body_offset = int(body_offset)

    @property
    def _root_loc(self):
        return self._body_loc

    @property
    def header_row(self):
        """Property representing the ``<tr>`` element that contains header cells"""
        # thead/tr containing header data
        # xpath is 1-indexed, so we need to add 1 to the offset to get the correct row
        return sel.element(
            'tr[{}]'.format(self.header_offset + 1), root=sel.element(self._header_loc))

    @property
    def body(self):
        """Property representing the element that contains body rows"""
        # tbody containing body rows
        return sel.element(self._body_loc)

    def locate(self):
        # Use the header locator as the overall table locator
        return sel.move_to_element(self._header_loc)


class SortTable(Table):
    """This table is the same as :py:class:`Table`, but with added sorting functionality."""
    @property
    def _sort_by_cell(self):
        try:
            return sel.element("./th[contains(@class, 'sorting_')]", root=self.header_row)
        except NoSuchElementException:
            return None

    @property
    def sorted_by(self):
        """Return column name what is used for sorting now.
        """
        cell = self._sort_by_cell
        if cell is None:
            return None
        return sel.text("./a", root=cell).encode("utf-8")

    @property
    def sort_order(self):
        """Return order.

        Returns: 'ascending' or 'descending'
        """
        cell = self._sort_by_cell
        if cell is None:
            return None

        cls = sel.get_attribute(cell, "class")
        if "sorting_asc" in cls:
            return "ascending"
        elif "sorting_desc" in cls:
            return "descending"
        else:
            return None

    def click_header_cell(self, text):
        """Clicks on the header to change sorting conditions.

        Args:
            text: Header cell text.
        """
        sel.click(sel.element("./th/a[normalize-space(.)='{}']".format(text), root=self.header_row))

    def sort_by(self, header, order):
        """Sorts the table by given conditions

        Args:
            header: Text of the header cell to use for sorting.
            order: ascending or descending
        """
        order = order.lower().strip()
        if header != self.sorted_by:
            # Change column to order by
            self.click_header_cell(header)
            if self.sorted_by != header:
                raise Exception(
                    "Detected malfunction in table ordering (wanted {}, got {})".format(
                        header, self.sorted_by))
        if order != self.sort_order:
            # Change direction
            self.click_header_cell(header)
            if self.sort_order != order:
                raise Exception("Detected malfunction in table ordering (wanted {}, got {})".format(
                    order, self.sort_order))


class CheckboxTable(Table):
    """:py:class:`Table` with support for checkboxes

    Args:
        table_locator: See :py:class:`cfme.web_ui.Table`
        header_checkbox_locator: Locator of header checkbox (default `None`)
                                 Specify in case the header checkbox is not part of the header row
        body_checkbox_locator: Locator for checkboxes in body rows
        header_offset: See :py:class:`cfme.web_ui.Table`
        body_offset: See :py:class:`cfme.web_ui.Table`
    """
    _checkbox_loc = ".//input[@type='checkbox']"

    def __init__(self, table_locator, header_offset=0, body_offset=0,
            header_checkbox_locator=None, body_checkbox_locator=None):
        super(CheckboxTable, self).__init__(table_locator, header_offset, body_offset)
        if body_checkbox_locator:
            self._checkbox_loc = body_checkbox_locator
        self._header_checkbox_loc = header_checkbox_locator

    @property
    def header_checkbox(self):
        """Checkbox used to select/deselect all rows"""
        if self._header_checkbox_loc is not None:
            return sel.element(self._header_checkbox_loc)
        else:
            return sel.element(self._checkbox_loc, root=self.header_row)

    def select_all(self):
        """Select all rows using the header checkbox or one by one if not present"""
        if self._header_checkbox_loc is None:
            for row in self.rows():
                self._set_row_checkbox(row, True)
        else:
            sel.uncheck(self.header_checkbox)
            sel.check(self.header_checkbox)

    def deselect_all(self):
        """Deselect all rows using the header checkbox or one by one if not present"""
        if self._header_checkbox_loc is None:
            for row in self.rows():
                self._set_row_checkbox(row, False)
        else:
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

    def select_rows_by_indexes(self, *indexes):
        """Select rows specified by row indexes (starting with 0)
        """
        for i, row in enumerate(self.rows()):
            if i in indexes:
                self._set_row_checkbox(row, True)

    def deselect_rows_by_indexes(self, *indexes):
        """Deselect rows specified by row indexes (starting with 0)
        """
        for i, row in enumerate(self.rows()):
            if i in indexes:
                self._set_row_checkbox(row, False)

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
                    failed_selects.append("{}:{}".format(header, value))
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

    def _set_row_by_cells(self, cells, set_to=False, partial_check=False):
        row = self.find_row_by_cells(cells, partial_check=partial_check)
        self._set_row_checkbox(row, set_to)

    def select_row_by_cells(self, cells, partial_check=False):
        """Select the first row matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`

        """
        self._set_row_by_cells(cells, True, partial_check)

    def deselect_row_by_cells(self, cells, partial_check=False):
        """Deselect the first row matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`

        """
        self._set_row_by_cells(cells, False, partial_check)

    def _set_rows_by_cells(self, cells, set_to=False, partial_check=False):
        rows = self.find_rows_by_cells(cells)
        for row in rows:
            self._set_row_checkbox(row, set_to)

    def select_rows_by_cells(self, cells, partial_check=False):
        """Select the rows matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
        """
        self._set_rows_by_cells(cells, True, partial_check)

    def deselect_rows_by_cells(self, cells, partial_check=False):
        """Deselect the rows matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
        """
        self._set_rows_by_cells(cells, False, partial_check)


class SplitCheckboxTable(SplitTable, CheckboxTable):
    """:py:class:`SplitTable` with support for checkboxes

    Args:
        header_data: See :py:class:`cfme.web_ui.SplitTable`
        body_data: See :py:class:`cfme.web_ui.SplitTable`
        header_checkbox_locator: See :py:class:`cfme.web_ui.CheckboxTable`
        body_checkbox_locator: See :py:class:`cfme.web_ui.CheckboxTable`
        header_offset: See :py:class:`cfme.web_ui.Table`
        body_offset: See :py:class:`cfme.web_ui.Table`
    """
    _checkbox_loc = './/img[contains(@src, "item_chk")]'

    def __init__(self, header_data, body_data,
            header_checkbox_locator=None, body_checkbox_locator=None):
        # To limit multiple inheritance surprises, explicitly call out to SplitTable's __init__
        SplitTable.__init__(self, header_data, body_data)

        # ...then set up CheckboxTable's locators here
        self._header_checkbox_loc = header_checkbox_locator
        if body_checkbox_locator:
            self._checkbox_loc = body_checkbox_locator


class PagedTable(Table):
    """:py:class:`Table` with support for paginator

    Args:
        table_locator: See :py:class:`cfme.web_ui.Table`
        header_checkbox_locator: Locator of header checkbox (default `None`)
                                 Specify in case the header checkbox is not part of the header row
        body_checkbox_locator: Locator for checkboxes in body rows
        header_offset: See :py:class:`cfme.web_ui.Table`
        body_offset: See :py:class:`cfme.web_ui.Table`
    """
    def find_row_on_all_pages(self, header, value):
        from cfme.web_ui import paginator
        for _ in paginator.pages():
            sel.wait_for_element(self)
            row = self.find_row(header, value)
            if row is not None:
                return row


class SplitPagedTable(SplitTable, PagedTable):
    """:py:class:`SplitTable` with support for paginator

    Args:
        header_data: See :py:class:`cfme.web_ui.SplitTable`
        body_data: See :py:class:`cfme.web_ui.SplitTable`
        header_offset: See :py:class:`cfme.web_ui.Table`
        body_offset: See :py:class:`cfme.web_ui.Table`
    """
    def __init__(self, header_data, body_data):
        # To limit multiple inheritance surprises, explicitly call out to SplitTable's __init__
        SplitTable.__init__(self, header_data, body_data)


def table_in_object(table_title):
    """If you want to point to tables inside object view, this is what you want to use.

    Works both on down- and upstream.

    Args:
        table_title: Text in `p` element preceeding the table
    Returns: XPath locator for the desired table.
    """
    return ("//table[(preceding-sibling::p[1] | preceding-sibling::h3[1])[normalize-space(.)={}]]"
        .format(quoteattr(table_title)))


@multimethod(lambda loc, value: (sel.tag(loc), sel.get_attribute(loc, 'type')))
def fill_tag(loc, value):
    """ Return a tuple of function to do the filling, and a value to log."""
    raise NotImplementedError("Don't know how to fill {} into this type: {}".format(value, loc))


@fill_tag.method(("select", Anything))
def fill_select_tag(select, value):
    return (sel.select, value)


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
@fill_tag.method((Anything, 'submit'))
def fill_click(el, val):
    """Click only when given a truthy value"""
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
def fill(loc, content, **kwargs):
    """
    Fills in a UI component with the given content.

    Usage:
        fill(textbox, "text to fill")
        fill(myform, [ ... data to fill ...])
        fill(radio, "choice to select")

    Returns: True if any UI action was taken, False otherwise

    """
    action, logval = fill_tag(loc, content)
    if hasattr(loc, 'name'):
        ident = loc.name
    else:
        ident = loc
    logger.debug('  Filling in [%s], with value %s', ident, logval)
    prev_state = action(loc, content)
    sel.detect_observed_field(loc)
    return prev_state


@fill.method((Mapping, Anything))
def _version_pick(m, a, **kwargs):
    return fill(version.pick(m), a, **kwargs)


@fill.method((Table, Mapping))
def _sd_fill_table(table, cells):
    """ How to fill a table with a value (by selecting the value as cells in the table)
    See Table.click_cells
    """
    table._update_cache()
    logger.debug('  Clicking Table cell')
    table.click_cells(cells)
    return bool(cells)


@fill.method((CheckboxTable, object))
def _sd_fill_checkboxtable(table, cells):
    """ How to fill a checkboxtable with a value (by selecting the right rows)
    See CheckboxTable.select_by_cells
    """
    table._update_cache()
    logger.debug('  Selecting CheckboxTable row')
    table.select_rows(cells)
    return bool(cells)


@fill.method((Callable, object))
def fill_callable(f, val):
    """Fill in a Callable by just calling it with the value, allow for arbitrary actions"""
    return f(val)


@fill.method((Select, types.NoneType))
@fill.method((Select, object))
def fill_select(slist, val):
    logger.debug('  Filling in {} with value {}'.format(str(slist), val))
    prev_sel = sel.select(slist, val)
    slist.observer_wait()
    return prev_sel


class Calendar(Pretty):
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
        return sel.move_to_element(Input(self.name))


@fill.method((Calendar, object))
def _sd_fill_date(calendar, value):
    input = sel.element(calendar)
    if isinstance(value, date):
        date_str = '{}/{}/{}'.format(value.month, value.day, value.year)
    else:
        date_str = str(value)

    # need to write to a readonly field: resort to evil
    if sel.get_attribute(input, 'ng-model') is not None:
        sel.set_angularjs_value(input, date_str)
    else:
        sel.set_attribute(input, "value", date_str)
        # Now when we set the value, we need to simulate a change event.
        if sel.get_attribute(input, "data-date-autoclose"):
            # New one
            script = "$(\"#{}\").trigger('changeDate');"
        else:
            # Old one
            script = (
                "if(typeof $j == 'undefined') {var jq = $;} else {var jq = $j;} "
                "jq(\"#{}\").change();")
        try:
            sel.execute_script(script.format(calendar.name))
        except sel_exceptions.WebDriverException as e:
            logger.warning(
                "An exception was raised during handling of the Cal #{}'s change event:\n{}"
                .format(calendar.name, str(e)))
    sel.wait_for_ajax()

    return True


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
    referenced in the same way a Region's locators can. You can also add one more field which will
    be a :py:class:`dict` of metadata, determining mostly field validity. See :py:meth:`field_valid`

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
        web_ui.fill(provider_form, provider_info)

    Note:
        Using supertuples in a list, although ordered due to the properties of a List,
        will not overide the field order defined in the Form.
    """

    pretty_attrs = ['fields']

    def __init__(self, fields=None, identifying_loc=None):
        self.metadata = {}
        self.locators = {}
        for field in fields:
            try:
                self.locators[field[0]] = field[1]
                if len(field) == 3:
                    self.metadata[field[0]] = field[2]
            except IndexError:
                raise ValueError("fields= can be 2- or 3-tuples only! (name, loc[, metadata])")

        self.fields = fields
        self.identifying_loc = identifying_loc

    def field_valid(self, field_name):
        """Add the validity constraints here."""
        if field_name not in self.metadata:
            return True
        metadata = self.metadata[field_name]
        if "removed_since" in metadata:
            removed_since = metadata["removed_since"]
            return version.current_version() < removed_since
        if "appeared_in" in metadata:
            appeared_in = metadata["appeared_in"]
            return version.current_version() >= appeared_in

        return True

    def fill(self, fill_data):
        fill(self, fill_data)


@fill.method((Form, Sequence))
def _fill_form_list(form, values, action=None, action_always=False):
    """Fills in field elements on forms

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

        action_always: if True, perform the action even if none of the
                       values to be filled in required any UI
                       interaction (eg, text boxes already had the
                       text to be filled in, checkbox already checked,
                       etc)

    """
    logger.info('Beginning to fill in form...')
    sel.wait_for_ajax()
    values = list(val for key in form.fields for val in values if val[0] == key[0])
    res = []
    for field, value in values:
        if value is not None and form.field_valid(field):
            loc = form.locators[field]
            logger.trace(' Dispatching fill for %s', field)
            fill_prev = fill(loc, value)  # re-dispatch to fill for each item
            res.append(fill_prev != value)  # note whether anything changed
        elif value is None and isinstance(form.locators[field], Select):
            fill_prev = fill(form.locators[field], None)
            res.append(fill_prev != value)
        else:
            res.append(False)

    if action and (any(res) or action_always):  # only perform action if something changed
        logger.debug(' Invoking end of form action')
        fill(action, True)  # re-dispatch with truthy value
    logger.debug('Finished filling in form')
    return any(res) or action_always


@fill.method((object, Mapping))
def _fill_form_dict(form, values, **kwargs):
    """Fill in a dict by converting it to a list"""
    return _fill_form_list(form, values.items(), **kwargs)


class Input(Pretty):
    """Class designed to handle things about ``<input>`` tags that have name attr in one place.

    Also applies on ``textarea``, which is basically input with multiple lines (if it has name).

    Args:
        *names: Possible values (or) of the ``name`` attribute.

    Keywords:
        use_id: Whether to use ``id`` instead of ``name``. Useful if there is some input that does
            not have ``name`` attribute present.
    """
    pretty_attrs = ['_names', '_use_id']

    def __init__(self, *names, **kwargs):
        self._names = names
        self._use_id = kwargs.pop("use_id", False)

    @property
    def names(self):
        if len(self._names) == 1 and isinstance(self._names[0], dict):
            return (version.pick(self._names[0]),)
        else:
            return self._names

    def _generate_attr(self, name):
        return "@{}={}".format("id" if self._use_id else "name", quoteattr(name))

    def locate(self):
        # If the end of the locator is changed, modify also the choice in Radio!!!
        return '//*[(self::input or self::textarea) and ({})]'.format(
            " or ".join(self._generate_attr(name) for name in self.names)
        )

    @property
    def angular_help_block(self):
        """Returns the angular helper text (like 'Required')."""
        loc = "{}/following-sibling::span".format(self.locate())
        if sel.is_displayed(loc):
            return sel.text(loc).strip()
        else:
            return None

    def __add__(self, string):
        return self.locate() + string

    def __radd__(self, string):
        return string + self.locate()


class FileInput(Input):
    """A file input handling widget.

    Accepts a string. If the string is a file, then it is put in the input. Otherwise a temporary
    file is generated and that one is fed to the file input.
    """
    pass


@fill.method((FileInput, Anything))
def _fill_file_input(i, a):
    # Engage the selenium's file detector so we can reliably transfer the file to the browser
    with browser().file_detector_context(LocalFileDetector):
        # We need a raw element so we can send_keys to it
        input_el = sel.element(i.locate())
        if browser().file_detector.is_local_file(a) is None:
            # Create a temp file
            f = NamedTemporaryFile()
            f.write(str(a))
            f.flush()
            input_el.send_keys(f.name)
            atexit.register(f.close)
        else:
            # It already is a file ...
            input_el.send_keys(a)
    # Since we used raw selenium element, wait for ajax here ...
    sel.wait_for_ajax()


class Radio(Input):
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
    def choice(self, val):
        """ Returns the locator for a choice

        Args:
            val: A string representing the ``value`` attribute of the specific radio
                element.

        Returns: A string containing the XPATH of the specific radio element.

        """
        # Ugly, but working - all the conditions are in parentheses
        return re.sub(r"\]$", " and @value={}]".format(quoteattr(val)), self.locate())

    def observer_wait(self, val):
        sel.detect_observed_field(self.choice(val))


@fill.method((Radio, object))
def _fill_radio(radio, value):
    """How to fill a radio button group (by selecting the given value)"""
    logger.debug(' Filling in Radio{} with value "{}"'.format(tuple(radio.names), value))
    sel.click(radio.choice(value))
    radio.observer_wait(value)


class Tree(Pretty):
    """ A class directed at CFME Tree elements

    The Tree class aims to deal with all kinds of CFME trees

    Args:
        locator: This is a locator object pointing to the ``<ul>`` element which contains the rest
            of the table.

    Returns: A :py:class:`Tree` object.

    A Tree object is set up by using a locator which contains the node elements. This element
    will usually be a ``<ul>`` in the case of a Dynatree.

    Usage:

         tree = web_ui.Tree((By.XPATH, '//table//tr[@title="Datastore"]/../..'))

    The path can then be navigated to return the last object in the path list, like so::

        tree.click_path('Automation', 'VM Lifecycle Management (VMLifecycle)',
            'VM Migrate (Migrate)')

    Each path element will be expanded along the way, but will not be clicked.

    When used in a :py:class:`Form`, a list of path tuples is expected in the form fill data.
    The paths will be passed individually to :py:meth:`Tree.check_node`::

        form = Form(fields=[
            ('tree_field', List(locator)),
        ])

        form_fill_data = {
            'tree_field': [
                ('Tree Node', 'Value'),
                ('Tree Node', 'Branch Node', 'Value'),
            ]
        ]

    Note: Dynatrees, rely on a ``<ul><li>`` setup. We class a ``<li>`` as a node.

    """
    pretty_attrs = ['locator']

    def __init__(self, locator):
        self.locator = locator

    @cached_property
    def tree_id(self):
        if isinstance(self.locator, basestring) and re.match(r"^[a-zA-Z0-9_-]+$", self.locator):
            return self.locator
        else:
            el = sel.element(self.locator)
            tag = sel.tag(el)
            tree_id = None
            if tag == "ul":
                try:
                    parent = sel.element("..", root=el)
                    id_attr = sel.get_attribute(parent, "id")
                    if id_attr:
                        tree_id = id_attr
                except sel.NoSuchElementException:
                    pass
            elif tag == "div":
                tree_id = sel.get_attribute(el, "id") or None
            else:
                raise ValueError("Unknown element ({}) passed to the Tree!".format(tag))

            if tree_id is None:
                raise ValueError("Could not retrieve the id for Tree {}".format(repr(tree_id)))
            else:
                return tree_id

    def locate(self):
        return "#{}".format(self.tree_id)

    def root_el(self):
        return sel.element(self)

    def _get_tag(self):
        if getattr(self, 'tag', None) is None:
            self.tag = sel.tag(self)
        return self.tag

    def read_contents(self, by_id=False):
        result = False
        while result is False:
            sel.wait_for_ajax()
            result = sel.execute_script(
                "{} return read_tree(arguments[0], arguments[1]);".format(js.read_tree),
                self.locate(),
                by_id)
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
        result = False

        # Ensure we pass str to the javascript. This handles objects that represent themselves
        # using __str__ and generally, you should only pass str because that is what makes sense
        path = castmap(str, path)

        # We sometimes have to wait for ajax. In that case, JS function returns false
        # Then we repeat and wait. It does not seem completely possible to wait for the data in JS
        # as it runs on one thread it appears. So this way it will try to drill multiple times
        # each time deeper and deeper :)
        while result is False:
            sel.wait_for_ajax()
            try:
                result = sel.execute_script(
                    "{} return find_leaf(arguments[0],arguments[1],arguments[2]);".format(
                        js.find_leaf),
                    self.locate(),
                    path,
                    by_id)
            except sel.WebDriverException as e:
                text = str(e)
                match = re.search(r"TREEITEM /(.*?)/ NOT FOUND IN THE TREE", text)
                if match is not None:
                    item = match.groups()[0]
                    raise exceptions.CandidateNotFound(
                        {'message': "{}: could not be found in the tree.".format(item),
                         'path': path,
                         'cause': e})
                match = re.search(r"^CANNOT FIND TREE /(.*?)/$", text)
                if match is not None:
                    tree_id = match.groups()[0]
                    raise exceptions.TreeNotFound(
                        "Tree {} / {} not found.".format(tree_id, self.locator))
                # Otherwise ...
                raise
        return result

    def click_path(self, *path, **kwargs):
        """ Exposes a path and then clicks it.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.

        Keywords:
            by_id: Whether to match ids instead of text.

        Returns: The leaf web element.

        """
        # Ensure we pass str to the javascript. This handles objects that represent themselves
        # using __str__ and generally, you should only pass str because that is what makes sense
        path = castmap(str, path)

        leaf = self.expand_path(*path, **kwargs)
        logger.info("Path %r yielded menuitem %r", path, sel.text(leaf))
        if leaf is not None:
            sel.wait_for_ajax()
            sel.click(leaf)
        return leaf

    @classmethod
    def browse(cls, tree, *path):
        """Browse through tree via path.

        If node not found, raises exception.
        If the browsing reached leaf(str), returns True if also the step was last, otherwise False.
        If the result of the path is a subtree, it is returned.

        Args:
            tree: List with tree.
            *path: Path to browse.
        """
        # Ensure we pass str to the javascript. This handles objects that represent themselves
        # using __str__ and generally, you should only pass str because that is what makes sense
        path = castmap(str, path)

        current = tree
        for i, step in enumerate(path, start=1):
            for node in current:
                if isinstance(node, list):
                    if node[0] == step:
                        current = node[1]
                        break
                else:
                    if node == step:
                        return i == len(path)
            else:
                raise Exception("Could not find node {}".format(step))
        return current

    @classmethod
    def flatten_level(cls, tree):
        """Extracts just node names from current tree (top).

        It makes:

        .. code-block:: python

            ["asd", "fgh", ("ijk", [...]), ("lmn", [...])]

        to

        .. code-block:: python

            ["asd", "fgh", "ijk", "lmn"]

        Useful for checking of contents of current tree level
        """
        return map(lambda item: item[0] if isinstance(item, list) else item, tree)

    def find_path_to(self, target, exact=False):
        """ Method used to look up the exact path to an item we know only by its regexp or partial
        description.

        Expands whole tree during the execution.

        Args:
            target: Item searched for. Can be regexp made by
                :py:func:`re.compile <python:re.compile>`,
                otherwise it is taken as a string for `in` matching.
            exact: Useful in string matching. If set to True, it matches the exact string.
                Default is False.
        Returns: :py:class:`list` with path to that item.
        """
        if not isinstance(target, re._pattern_type):
            if exact:
                target = re.compile(r"^{}$".format(re.escape(str(target))))
            else:
                target = re.compile(r".*?{}.*?".format(re.escape(str(target))))

        def _find_in_tree(t, p=None):
            if p is None:
                p = []
            for item in t:
                if isinstance(item, list):
                    if target.match(item[0]) is None:
                        subtree = _find_in_tree(item[1], p + [item[0]])
                        if subtree is not None:
                            return subtree
                    else:
                        return p + [item[0]]
                else:
                    if target.match(item) is not None:
                        return p + [item]
            else:
                return None

        result = _find_in_tree(self.read_contents())
        if result is None:
            raise NameError("{} not found in tree".format(target.pattern))
        else:
            return result


class CheckboxTree(Tree):
    """Tree that has a checkbox on each node, adds methods to check/uncheck them"""

    node_checkbox = "../span[@class='dynatree-checkbox']"

    def _is_checked(self, leaf):
        return 'dynatree-selected' in \
            sel.get_attribute(sel.element("..", root=leaf), 'class')

    def _check_uncheck_node(self, path, check=False):
        """ Checks or unchecks a node.

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
            check: If ``True``, the node is checked, ``False`` the node is unchecked.
        """
        leaf = self.expand_path(*path)
        cb = sel.element(self.node_checkbox, root=leaf)
        if check is not self._is_checked(leaf):
            sel.click(cb)

    def check_node(self, *path):
        """ Convenience function to check a node

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
        """
        self._check_uncheck_node(path, check=True)

    def uncheck_node(self, *path):
        """ Convenience function to uncheck a node

        Args:
            *path: The path as multiple positional string arguments denoting the course to take.
        """
        self._check_uncheck_node(path, check=False)


@fill.method((Tree, Sequence))
def _fill_tree_seq(tree, values):
    tree.click_path(*values)


@sel.select.method((CheckboxTree, Sequence))
@fill.method((CheckboxTree, Sequence))
def _select_chkboxtree_seq(cbtree, values):
    """values should be a list of tuple pairs, where the first item is the
       path to select, and the second is whether to check or uncheck.

       Usage:

         select(cbtree, [(['Foo', 'Bar'], False),
                         (['Baz'], True)])
    """
    for (path, to_select) in values:
        if to_select:
            cbtree.check_node(*path)
        else:
            cbtree.uncheck_node(*path)


class InfoBlock(Pretty):
    DETAIL = "detail"
    FORM = "form"
    PF = "patternfly"
    _TITLE_CACHE = {}

    pretty_attrs = ["title"]

    def __new__(cls, title, detail=None):
        # Caching
        if title not in cls._TITLE_CACHE:
            cls._TITLE_CACHE[title] = super(InfoBlock, cls).__new__(cls)
            cls._TITLE_CACHE[title].__init__(title)
        instance = cls._TITLE_CACHE[title]
        if detail is None:
            return instance
        else:
            return instance.member(detail)

    def __init__(self, title):
        if all(map(lambda a: hasattr(self, a), ["title", "_type", "_member_cache"])):
            return
        self.title = title
        self._type = None
        self._member_cache = {}

    @property
    def type(self):
        if self._type is None:
            self.root  # To retrieve it
        return self._type

    @property
    def root(self):
        possible_locators = [
            # Detail type
            version.pick({
                '5.3': '//table//th[contains(normalize-space(.), "{}")]/../../../..'.format(
                    self.title),
                version.LOWEST:
                '//div[@class="modbox"]/h2[@class="modtitle"]'
                '[contains(normalize-space(.), "{}")]/..'.format(self.title)
            }),
            # Form type
            (
                '//*[p[@class="legend"][contains(normalize-space(.), "{}")] and table/tbody/tr/td['
                'contains(@class, "key")]]'.format(self.title)
            ),
            # Newer Form type (master.20150311020845_547fd06 onwards)
            (
                '//*[h3[contains(normalize-space(.), "{}")] and table/tbody/tr/td['
                'contains(@class, "key")]]'.format(self.title)
            ),
            # Newer Form type used in AC tagging:
            (
                '//h3[contains(normalize-space(.), "{}")]/following-sibling::div/table/tbody/tr/td['
                'contains(@class, "key")]/../../../..'.format(self.title)
            ),
            # The root element must contain table element because listaccordions were caught by the
            # locator. It used to be fieldset but it seems it can be really anything
            # And here comes a new one, this time no table. (eg. 5.5.0.7 Configuration/About)
            (
                '//*[h3[contains(normalize-space(.), "{}")] and '
                'div[contains(@class, "form-horizontal")]/div/label]'.format(self.title)
            )
        ]
        found = sel.elements("|".join(possible_locators))
        if not found:
            raise exceptions.BlockTypeUnknown("The block type requested is unknown")
        root_el = found[0]
        if sel.elements("./table/tbody/tr/td[contains(@class, 'key')]", root=root_el):
            self._type = self.FORM
        elif sel.elements("./div[contains(@class, 'form-horizontal')]/div/label", root=root_el):
            self._type = self.PF
        else:
            self._type = self.DETAIL
        return root_el

    def member(self, name):
        if name not in self._member_cache:
            self._member_cache[name] = self.Member(self, name)
        return self._member_cache[name]

    def by_member_icon(self, icon):
        """In case you want to find the item by icon in the value field (like OS infra diff.)"""
        if self._type == self.PF:
            raise NotImplementedError(
                "I haven't implemented icons+patternfly infoblock yet, so fix me if you see this.")
        l = ".//table/tbody/tr/td[2]/img[contains(@src, {})]/../../td[1]".format(quoteattr(icon))
        return self.member(sel.text(l))

    def __call__(self, member):
        """A present for @smyers"""
        return self.member(member)

    ##
    #
    # Shortcuts for old-style access
    #
    @classmethod
    def text(cls, *args, **kwargs):
        return cls(*args, **kwargs).text

    @classmethod
    def element(cls, *args, **kwargs):
        return cls(*args, **kwargs).element

    @classmethod
    def elements(cls, *args, **kwargs):
        return cls(*args, **kwargs).elements

    @classmethod
    def icon_href(cls, *args, **kwargs):
        return cls(*args, **kwargs).icon_href

    @classmethod
    def container(cls, args, **kwargs):
        try:
            return sel.element(cls(*args, **kwargs).container)
        except sel_exceptions.NoSuchElementException:
            raise exceptions.ElementOrBlockNotFound(
                "Either the element of the block could not be found")

    class Member(Pretty):
        pretty_attrs = "name", "ib"

        def __init__(self, ib, name):
            self.ib = ib
            self.name = name

        @property
        def pair_locator(self):
            if self.ib.type == InfoBlock.DETAIL:
                return './/table/tbody/tr/td[1][@class="label"][normalize-space(.)="{}"]/..'.format(
                    self.name)
            elif self.ib.type == InfoBlock.FORM:
                return './/table/tbody/tr/td[1][@class="key"][normalize-space(.)="{}"]/..'.format(
                    self.name)
            elif self.ib.type == InfoBlock.PF:
                return (
                    './div[contains(@class, "form-horizontal")]'
                    '/div[label[normalize-space(.)="{}"]]/div'.format(self.name))

        @property
        def pair(self):
            return sel.element(self.pair_locator, root=self.ib.root)

        @property
        def container(self):
            if self.ib.type == InfoBlock.PF:
                # Because we get the element directly, not the two tds
                return self.pair
            else:
                return sel.element("./td[2]", root=self.pair)

        def locate(self):
            return self.container

        @property
        def elements(self):
            return sel.elements("./*", root=self.container)

        @property
        def element(self):
            return self.elements[0]

        @property
        def text(self):
            return sel.text(self.container).encode("utf-8").strip()

        @property
        def icon_href(self):
            try:
                return sel.get_attribute(sel.element("./img", root=self.container), "src")
            except sel_exceptions.NoSuchElementException:
                return None

        @property
        def title(self):
            return sel.get_attribute(self.pair, "title") or None


@fill.method((InfoBlock, Sequence))
def _ib_seq(ib, i):
    for item in i:
        sel.click(ib.member(item))


@fill.method((InfoBlock, basestring))
def _ib_str(ib, s):
    fill([s])


@fill.method((InfoBlock.Member, bool))
def _ib_m_seq(member, b):
    if b:
        sel.click(member)


class Quadicon(Pretty):
    """
    Represents a single quadruple icon in the CFME UI.

    A Quadicon contains multiple quadrants. These are accessed via attributes.
    The qtype is currently one of the following and determines which attribute names
    are present. They are mapped internally and can be reassigned easily if the UI changes.

    A Quadicon is used by defining the name of the icon and the type. After that, it can be used
    to obtain the locator of the Quadicon, or query its quadrants, via attributes.

    Args:
       name: The label of the icon.
       qtype: The type of the quad icon. By default it is ``None``, therefore plain quad without any
            retrievable data usable for selecting/clicking.

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

    * **datastore** - *from the infra/datastores page* - has quads:

      * a. **type** - File system type
      * b. **no_vm** - Number of VMs
      * c. **no_host** - Number of hosts
      * d. **avail_space** - Available space

    * **repository** - *from the infra/repositories page* - has no quads
    * **cluster** - *from the infra/cluster page* - has no quads
    * **resource_pool** - *from the infra/resource_pool page* - has no quads
    * **stack** - *from the clouds/stacks page* - has no quads

    Returns: A :py:class:`Quadicon` object.
    """

    pretty_attrs = ['_name', '_qtype']

    QUADS = {
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
        "stack": {},
        "datastore": {
            "type": ("a", 'img'),
            "no_vm": ("b", 'txt'),
            "no_host": ("c", 'txt'),
            "avail_space": ("d", 'img'),
        },
        "cluster": {},
        "repository": {},
        "resource_pool": {},
        "template": {
            "os": ("a", 'img'),
            "state": ("b", 'img'),
            "vendor": ("c", 'img'),
            "no_snapshot": ("d", 'txt'),
        },
        "image": {
            "os": ("a", 'img'),
            "state": ("b", 'img'),
            "vendor": ("c", 'img'),
            "no_snapshot": ("d", 'txt'),
        },
        "middleware": {},   # Middleware quads have no fields
        None: {},  # If you just want to find the quad and not mess with data
    }

    def __init__(self, name, qtype=None):
        self._name = name
        self.qtype = qtype

    @property
    def qtype(self):
        return self._qtype

    @qtype.setter
    def qtype(self, value):
        assert value in self.QUADS
        self._qtype = value

    @property
    def _quad_data(self):
        return self.QUADS[self.qtype]

    def checkbox(self):
        """ Returns:  a locator for the internal checkbox for the quadicon"""
        return "//input[@type='checkbox' and ../../..//a[{}]]".format(self.a_cond)

    @property
    def exists(self):
        try:
            self.locate()
            return True
        except sel.NoSuchElementException:
            return False

    @property
    def a_cond(self):
        if self.qtype == "middleware":
            return "contains(normalize-space(@title), {name})"\
                .format(name=quoteattr('Name: {}'.format(self._name)))
        else:
            return "@title={name} or @data-original-title={name}".format(name=quoteattr(self._name))

    def locate(self):
        """ Returns:  a locator for the quadicon anchor"""
        try:
            return sel.move_to_element(
                'div/a',
                root="//div[contains(@id, 'quadicon') and ../../..//a[{}]]".format(self.a_cond))
        except sel.NoSuchElementException:
            quads = sel.elements("//div[contains(@id, 'quadicon')]/../../../tr/td/a")
            if not quads:
                raise sel.NoSuchElementException("Quadicon {} not found. No quads present".format(
                    self._name))
            else:
                quad_names = [self._get_title(quad) for quad in quads]
                raise sel.NoSuchElementException(
                    "Quadicon {} not found. These quads are present:\n{}".format(
                        self._name, ", ".join(quad_names)))

    def _locate_quadrant(self, corner):
        """ Returns: a locator for the specific quadrant"""
        return "//div[contains(@class, {}) and ../../../..//a[{}]]".format(
            quoteattr("{}72".format(corner)), self.a_cond)

    def __getattr__(self, name):
        """ Queries the quadrants by name

        Args:
            name: The name of the quadrant identifier, as defined above.
        Returns: A string containing a representation of what is in the quadrant.
        """
        if name in self._quad_data:
            corner, rtype = self._quad_data[name]
            locator = self._locate_quadrant(corner)
            # We have to have a try/except here as some quadrants
            # do not exist if they have no data, e.g. current_state in a host
            # with no credentials.
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

    @classmethod
    def _get_title(cls, el):
        title = sel.get_attribute(el, "title")
        if title is not None:
            return title
        else:
            return sel.get_attribute(el, "data-original-title")

    @classmethod
    def all(cls, qtype=None, this_page=False):
        """Allows iteration over Quadicons.

        Args:
            qtype: Quadicon type. Refer to the constructor for reference.
            this_page: Whether to look for Quadicons only on current page (do not list pages).
        Returns: :py:class:`list` of :py:class:`Quadicon`
        """
        from cfme.web_ui import paginator  # Prevent circular imports
        if this_page:
            pages = (None, )  # Single, current page. Since we dont care about the value, using None
        else:
            pages = paginator.pages()
        for page in pages:
            for href in sel.elements("//div[contains(@id, 'quadicon')]/../../../tr/td/a"):
                yield cls(cls._get_title(href), qtype)

    @classmethod
    def first(cls, qtype=None):
        return cls(cls.get_first_quad_title(), qtype=qtype)

    @staticmethod
    def select_first_quad():
        fill("//div[contains(@id, 'quadicon')]/../..//input", True)

    @staticmethod
    def get_first_quad_title():
        first_quad = "//div[contains(@id, 'quadicon')]/../../../tr/td/a"
        title = sel.get_attribute(first_quad, "title")
        if title:
            return title
        else:
            return sel.get_attribute(first_quad, "data-original-title") or ""  # To ensure str

    @classmethod
    def any_present(cls):
        try:
            cls.get_first_quad_title()
        except NoSuchElementException:
            return False
        except AttributeError:
            # This is needed so that if there is no browser, we fail nicely, this in turn is
            # needed to make the docs not error.
            return False
        else:
            return True

    @property
    def name(self):
        """ Returns name of the quadicon."""
        return self._name

    @property
    def check_for_single_quadrant_icon(self):
        """ Checks if the quad icon is a single quadrant icon."""
        for quadrant_name in self._quad_data.iterkeys():
            # These quadrant will be displayed if it is a regular quad
            quadrant_id = self._quad_data[quadrant_name][0]  # It is a tuple
            if sel.is_displayed(self._locate_quadrant(quadrant_id)):
                return False
        return sel.is_displayed(self._locate_quadrant("e"))  # Image has only 'e'


class DHTMLSelect(Select):
    """
    A special Select object for CFME's icon enhanced DHTMLx Select elements.

    Args:
        loc: A locator.

    Returns a :py:class:`cfme.web_ui.DHTMLSelect` object.

    """

    @staticmethod
    def _log(meth, val=None):
        if val:
            val_string = " with value {}".format(val)
        logger.debug('Filling in DHTMLSelect using (%s)%s', meth, val_string)

    def _get_select_name(self):
        """ Get's the name reference of the element from its hidden attribute.
        """

        root_el = sel.element(self)
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
            'return {}.getOptionByIndex({}}.getSelectedIndex()).content'.format(name, name))

    @property
    def options(self):
        """ Returns a list of options of the select as webelements.

        Returns: A list of Webelements.
        """
        name = self._get_select_name()
        return browser().execute_script('return {}.DOMlist.children'.format(name))

    def select_by_index(self, index, _cascade=None):
        """ Selects an option by index.

        Args:
            index: The select element's option by index.
        """
        name = self._get_select_name()
        if index is not None:
            if not _cascade:
                self._log('index', index)
            browser().execute_script('{}.selectOption({})'.format(name, index))

    def select_by_visible_text(self, text):
        """ Selects an option by visible text.

        Args:
            text: The select element option's visible text.
        """
        name = self._get_select_name()
        if text is not None:
            self._log('visible_text', text)
            value = browser().execute_script(
                'return {}.getOptionByLabel("{}").value'.format(name, text))
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
            index = browser().execute_script('return {}.getIndexByValue("{}")'.format(name, value))
            self.select_by_index(index, _cascade=True)

    def locate(self):
        return sel.move_to_element(self._loc)


@sel.select.method((DHTMLSelect, basestring))
def select_dhtml(dhtml, s):
    dhtml.select_by_visible_text(s)


class Filter(Form):
    """ Filters requests pages

    This class inherits Form as its base and adds a few methods to assist in filtering
    request pages.

    Usage:
        f = Filter(fields=[
            ('type', Select('//select[@id="type_choice"]')),
            ('approved', Input("state_choice__approved")),
            ('denied', Input"state_choice__denied")),
            ('pending_approval', Input("state_choice__pending_approval")),
            ('date', Select('//select[@id="time_period"]')),
            ('reason', Input("reason_text")),
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
    """Represents a UI widget where there are two select boxes, one with
    possible selections, and another with selected items.  Has two
    arrow buttons to move items between the two"""

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


class UpDownSelect(Region):
    """Multiselect with two arrows (up/down) next to it. Eg. in AE/Domain priority selection.

    Args:
        select_loc: Locator for the select box (without Select element wrapping)
        up_loc: Locator of the Move Up arrow.
        down_loc: Locator with Move Down arrow.
    """
    def __init__(self, select_loc, up_loc, down_loc):
        super(UpDownSelect, self).__init__(locators=dict(
            select=Select(select_loc, multi=True),
            up=up_loc,
            down=down_loc,
        ))

    def get_items(self):
        return map(lambda el: el.text.encode("utf-8"), self.select.options)

    def move_up(self, item):
        item = str(item)
        assert item in self.get_items()
        self.select.deselect_all()
        sel.select(self.select, item)
        sel.click(self.up)

    def move_down(self, item):
        item = str(item)
        assert item in self.get_items()
        self.select.deselect_all()
        sel.select(self.select, item)
        sel.click(self.down)

    def move_top(self, item):
        item = str(item)
        assert item in self.get_items()
        self.select.deselect_all()
        while item != self.get_items()[0]:
            sel.select(self.select, item)
            sel.click(self.up)

    def move_bottom(self, item):
        item = str(item)
        assert item in self.get_items()
        self.select.deselect_all()
        while item != self.get_items()[-1]:
            sel.select(self.select, item)
            sel.click(self.down)


@fill.method((UpDownSelect, Sequence))
def _fill_uds_seq(uds, seq):
    seq = map(str, seq)
    for item in reversed(seq):  # reversed because every new item at top pushes others down
        uds.move_top(item)


class ScriptBox(Pretty):
    """Represents a script box as is present on the customization templates pages.
    This box has to be activated before keys can be sent. Since this can't be done
    until the box element is visible, and some dropdowns change the element, it must
    be activated "inline".

    Args:
    """

    pretty_attrs = ['locator']

    def __init__(self, name=None, ta_locator="//textarea[contains(@id, 'method_data')]"):
        self._name = name
        self.ta_loc = ta_locator

    @property
    def name(self):
        if not self._name:
            self._name = version.pick({
                version.LOWEST: 'miqEditor',
                '5.5': 'ManageIQ.editor'})
        return self._name

    def get_value(self):
        script = sel.execute_script('return {}.getValue();'.format(self.name))
        script = script.replace('\\"', '"').replace("\\n", "\n")
        return script

    def workaround_save_issue(self):
        # We need to fire off the handlers manually in some cases ...
        sel.execute_script(
            "{}._handlers.change.map(function(handler) {{ handler() }});".format(self.name))
        sel.wait_for_ajax()


@fill.method((ScriptBox, Anything))
def fill_scriptbox(sb, script):
    """This function now clears and sets the ScriptBox.
    """
    logger.info("Filling ScriptBox {} with\n{}".format(sb.name, script))
    sel.execute_script('{}.setValue(arguments[0]);'.format(sb.name), script)
    sel.wait_for_ajax()
    sel.execute_script('{}.save();'.format(sb.name))
    sel.wait_for_ajax()


class CheckboxSelect(Pretty):
    """Class used for filling those bunches of checkboxes I (@mfalesni) always hated to search for.

    Can fill by values, text or both. To search the text for the checkbox, you have 2 choices:

    * If the text can be got from parent's tag (like `<div><input type="checkbox">blablabla</div>`
        where blablabla is the checkbox's description looked up), you can leave the
        `text_access_func` unfilled.
    * If there is more complicated layout and you don't mind a bit slower operation, you can pass
        the text_access_func, which should be like `lambda checkbox_el: get_text_of(checkbox_el)`.
        The checkbox `WebElement` is passed to it and the description text is the expected output
        of the function.

    Args:
        search_root: Root element for checkbox search
        text_access_func: Function returning descriptive text about passed CB element.
    """

    pretty_attrs = ['_root']

    def __init__(self, search_root, text_access_func=None):
        self._root = search_root
        self._access_func = text_access_func

    @property
    def checkboxes(self):
        """All checkboxes."""
        return set(sel.elements(".//input[@type='checkbox']", root=sel.element(self._root)))

    @property
    def selected_checkboxes(self):
        """Only selected checkboxes."""
        return {cb for cb in self.checkboxes if cb.is_selected()}

    @property
    def selected_values(self):
        """Only selected checkboxes' values."""
        return {sel.get_attribute(cb, "value") for cb in self.selected_checkboxes}

    @property
    def unselected_checkboxes(self):
        """Only unselected checkboxes."""
        return {cb for cb in self.checkboxes if not cb.is_selected()}

    @property
    def unselected_values(self):
        """Only unselected checkboxes' values."""
        return {sel.get_attribute(cb, "value") for cb in self.unselected_checkboxes}

    def checkbox_by_id(self, id):
        """Find checkbox's WebElement by id."""
        return sel.element(
            ".//input[@type='checkbox' and @id='{}']".format(id), root=sel.element(self._root)
        )

    def select_all(self):
        """Selects all checkboxes."""
        for cb in self.unselected_checkboxes:
            sel.check(cb)

    def unselect_all(self):
        """Unselects all checkboxes."""
        for cb in self.selected_checkboxes:
            sel.uncheck(cb)

    def checkbox_by_text(self, text):
        """Returns checkbox's WebElement by searched by its text."""
        if self._access_func is not None:
            for cb in self.checkboxes:
                txt = self._access_func(cb)
                if txt == text:
                    return cb
            else:
                raise NameError("Checkbox with text {} not found!".format(text))
        else:
            # Has to be only single
            return sel.element(
                ".//*[contains(., '{}')]/input[@type='checkbox']".format(text),
                root=sel.element(self._root)
            )

    def check(self, values):
        """Checking function.

        Args:
            values: Dictionary with key=CB name, value=bool with status.

        Look in the function to see.
        """
        for name, value in values.iteritems():
            if isinstance(name, sel.ByText):
                sel.checkbox(self.checkbox_by_text(str(name)), value)
            else:
                sel.checkbox(self.checkbox_by_id(name), value)


@fill.method((CheckboxSelect, bool))
def fill_cb_select_bool(select, all_state):
    if all_state is True:
        return select.select_all()
    else:
        return select.unselect_all()


@fill.method((CheckboxSelect, list))
@fill.method((CheckboxSelect, set))
def fill_cb_select_set(select, names):
    return select.check({k: True for k in names})


@fill.method((CheckboxSelect, Mapping))
def fill_cb_select_dictlist(select, dictlist):
    return select.check(dictlist)


@fill.method((CheckboxSelect, basestring))
@fill.method((CheckboxSelect, sel.ByText))
def fill_cb_select_string(select, cb):
    return fill(select, {cb})


class ShowingInputs(Pretty):
    """This class abstracts out as a container of inputs, that appear after preceeding was filled.

    Args:
        *locators: In-order-of-display specification of locators.
    Keywords:
        min_values: How many values are required (Default: 0)
    """
    pretty_attrs = ['locators', 'min_values']

    def __init__(self, *locators, **kwargs):
        self._locators = locators
        self._min = kwargs.get("min_values", 0)

    def zip(self, with_values):
        if len(with_values) < self._min:
            raise ValueError("Not enough values provided ({}, expected {})".format(
                len(with_values), self._min)
            )
        if len(with_values) > len(self._locators):
            raise ValueError("Too many values provided!")
        return zip(self._locators, with_values)

    def __getitem__(self, i):
        """To delegate access to the separate locators"""
        return self._locators[i]


@fill.method((ShowingInputs, Sequence))
def _fill_showing_inputs_seq(si, i):
    for loc, val in si.zip(i):
        fill(loc, val)


@fill.method((ShowingInputs, basestring))
def _fill_showing_inputs_str(si, s):
    fill(si, [s])


class MultiFill(object):
    """Class designed to fill the same value to multiple fields

    Args:
        *fields: The fields where the value will be mirrored
    """
    def __init__(self, *fields):
        self.fields = fields


@fill.method((MultiFill, object))
def _fill_multi_obj(mf, o):
    for field in mf.fields:
        fill(field, o)


class DriftGrid(Pretty):
    """ Class representing the table (grid) specific to host drift analysis comparison page
    """

    def __init__(self, loc="//div[@id='drift_grid_div']"):
        self.loc = loc

    def get_cell(self, row_text, col_index):
        """ Finds cell element of the grid specified by column index and row text

        Args:
            row_text: Title text of the cell's row
            col_index: Column index of the cell, starting with 0 for 1st data-containing column

        Note:
            `col_index` of 0 is used for the 2nd actual column in the drift grid, because
            the 1st column does not contain headers, only row descriptions.

        Returns:
            Selenium element of the cell.
        """
        self.expand_all_sections()
        cell_loc = ".//div/div[1][contains(., '{}')]/../div[{}]".format(row_text, col_index + 2)
        cell = sel.element(cell_loc, root=self.loc)
        return cell

    def cell_indicates_change(self, row_text, col_index):
        """  Finds out if a cell, specified by column index and row text, indicates change

        Args:
            row_text: Title text of the cell's row
            col_index: Column index of the cell

        Note:
            `col_index` of 0 is used for the 2nd actual column in the drift grid, because
            the 1st column does not contain headers, only row descriptions.

        Returns:
            ``True`` if there is a change present, ``False`` otherwise
        """
        cell = self.get_cell(row_text, col_index)

        # Cell either contains an image
        try:
            cell_img = sel.element(".//img", root=cell)
            if sel.get_attribute(cell_img, "alt") == 'Changed from previous':
                return True
        # or text
        except NoSuchElementException:
            if version.current_version() <= '5.3':
                cell_textdiv = sel.element("./div", root=cell)
                if 'mark' in sel.get_attribute(cell_textdiv, 'class'):
                    return True
            else:  # LOWEST
                if 'color: rgb(33, 160, 236)' in sel.get_attribute(cell, 'style'):
                    return True
        return False

    def expand_all_sections(self):
        """ Expands all sections to make the row elements found therein available
        """
        while True:
            # We need to do this one by one because the DOM changes on every expansion
            try:
                el = sel.element(
                    './/div/span[contains(@class, "toggle") and contains(@class, "expand")]',
                    root=self.loc)
                sel.click(el)
            except NoSuchElementException:
                break


class ButtonGroup(object):
    def __init__(self, key):
        """ A ButtonGroup is a set of buttons next to each other, as is used on the DefaultViews
        page.

        Args:
            key: The name of the key field text before the button group.
        """
        self.key = key

    @property
    def _icon_tag(self):
        if version.current_version() >= 5.6:
            return 'i'
        else:
            return 'img'

    @property
    def _state_attr(self):
        if version.current_version() >= 5.6:
            return 'title'
        else:
            return 'alt'

    @property
    def locator(self):
        attr = re.sub(r"&amp;", "&", quoteattr(self.key))  # We don't need it in xpath
        if version.current_version() < "5.5":
            return '//td[@class="key" and normalize-space(.)={}]/..'.format(attr)
        else:
            return (
                '//label[contains(@class, "control-label") and normalize-space(.)={}]/..'
                .format(attr))

    def locate(self):
        """ Moves to the element """
        # Use the header locator as the overall table locator
        return sel.move_to_element(self.locator)

    @property
    def locator_base(self):
        if version.current_version() < "5.5":
            return self.locator + "/td[2]"
        else:
            return self.locator + "/div"

    @property
    def active(self):
        """ Returns the alt tag text of the active button in thr group. """
        loc = sel.element(self.locator_base + '/ul/li[@class="active"]/{}'.format(self._icon_tag))
        return loc.get_attribute(self._state_attr)

    def status(self, alt):
        """ Returns the status of the button identified by the Alt Text of the image. """
        active_loc = self.locator_base + '/ul/li/{}[@{}="{}"]'.format(
            self._icon_tag, self._state_attr, alt)
        try:
            sel.element(active_loc)
            return True
        except NoSuchElementException:
            pass
        inactive_loc = self.locator_base + '/ul/li/a/{}[@alt="{}"]'.format(self._icon_tag, alt)
        try:
            sel.element(inactive_loc)
            return False
        except NoSuchElementException:
            pass

    def choose(self, alt):
        """ Sets the ButtonGroup to select the button identified by the alt text. """
        if not self.status(alt):
            inactive_loc = self.locator_base + '/ul/li/a/{}[@alt="{}"]'.format(self._icon_tag, alt)
            sel.click(inactive_loc)


@fill.method((ButtonGroup, basestring))
def _fill_showing_button_group(tb, s):
    tb.choose(s)


class ColorGroup(object):

    def __init__(self, key):
        """ A ColourGroup is a set of colour buttons next to each other, as is used on the DefaultViews
        page.

        Args:
            key: The name of the key field text before the button group.
        """
        self.key = key
        self.locator = '//td[@class="key" and text()="{}"]/..'.format(self.key)

    def locate(self):
        """ Moves to the element """
        # Use the header locator as the overall table locator
        return sel.move_to_element(self.locator)

    @property
    def active(self):
        """ Returns the alt tag text of the active button in thr group. """
        loc = sel.element(self.locator + '/td[2]/div[contains(@title, "selected")]')
        color = re.search('The (.*?) theme', loc.get_attribute('title')).groups()[0]
        return color

    def status(self, color):
        """ Returns the status of the color button identified by the Title Text of the image. """
        active_loc = self.locator + '/td[2]/div[contains(@title, "{}")' \
            'and contains(@title, "selected")]'.format(color)
        try:
            sel.element(active_loc)
            return True
        except NoSuchElementException:
            pass
        inactive_loc = self.locator + '/td[2]/div[contains(@title, "{}")' \
            'and contains(@title, "Click")]'.format(color)
        try:
            sel.element(inactive_loc)
            return False
        except NoSuchElementException:
            pass

    def choose(self, color):
        """ Sets the ColorGroup to select the button identified by the title text. """
        if not self.status(color):
            inactive_loc = self.locator + '/td[2]/div[contains(@title, "{}")' \
                'and contains(@title, "Click")]'.format(color)
            sel.click(inactive_loc)


@fill.method((ColorGroup, basestring))
def _fill_showing_color_group(tb, s):
    tb.choose(s)


class DynamicTable(Pretty):
    """A table that can add or remove the rows.

    """
    pretty_attrs = "root_loc", "default_row_item"
    ROWS = ".//tbody/tr[not(contains(@id, 'new_tr'))]"
    DELETE_ALL = {
        version.LOWEST: ".//tbody/tr/td/img[@alt='Delete']",
        '5.6': './/tbody/tr/td/button/i[contains(@class, "minus")]'
    }

    def __init__(self, root_loc, default_row_item=None):
        self.root_loc = root_loc
        self.default_row_item = default_row_item

    @property
    def rows(self):
        return map(lambda r_el: self.Row(self, r_el), sel.elements(self.ROWS, root=self.root_loc))

    @cached_property
    def header_names(self):
        return map(sel.text, sel.elements(".//thead/tr/th", root=self.root_loc))

    def click_add(self):
        sel.click(sel.element(
            ".//tbody/tr[@id='new_tr']/td//img | .//tbody/tr[@id='new_tr']/td//i",
            root=self.root_loc))

    def click_save(self):
        if version.current_version() < "5.6":
            sel.click(sel.element(
                ".//tbody/tr[@id='new_tr']/td//input[@type='image']", root=self.root_loc))
        else:
            # 5.6+ uses the same button.
            self.click_add()

    def delete_row(self, by):
        pass

    def clear(self):
        while True:
            buttons = sel.elements(self.DELETE_ALL)
            if not buttons:
                break
            sel.click(buttons[0])

    def add_row(self, data):
        self.click_add()
        editing_row = self.Row(self, ".//tbody/tr[@id='new_tr']")
        fill(editing_row, data)
        self.click_save()

    class Row(object):
        def __init__(self, table, root):
            self.table = table
            self.root = root

        @property
        def values(self):
            cells = sel.elements("./td", root=self.root)
            return dict(zip(self.table.header_names, map(sel.text, cells)))

        @property
        def inputs(self):
            result = []
            for cell in sel.elements("./td", root=self.root):
                inputs = sel.elements("./input", root=cell)
                if not inputs:
                    result.append(None)
                else:
                    result.append(inputs[0])
            return result

        @property
        def inputs_for_filling(self):
            return dict(zip(self.table.header_names, self.inputs))


@fill.method((DynamicTable.Row, Mapping))
def _fill_dt_row_map(dtr, m):
    for name, input in dtr.inputs_for_filling.iteritems():
        fill(input, m.get(name, None))


@fill.method((DynamicTable.Row, Anything))
def _fill_dt_row_other(dtr, anything):
    mapping_fields = [name for name in dtr.table.header_names if name.strip()]
    if isinstance(anything, (list, tuple)) and len(anything) == len(mapping_fields):
        # Create the dict and fill by dict
        fill(dtr, dict(zip(mapping_fields, anything)))
    else:
        # Use the default field
        if dtr.table.default_row_item is None:
            raise Exception("Cannot fill table row with anything when we dont know the def. field")
        fill(dtr, {dtr.table.default_row_item: anything})


@fill.method((DynamicTable, list))
def _fill_dt_list(dt, l, clear_before=False):
    if clear_before:
        dt.clear()
    for item in l:
        dt.add_row(item)


@fill.method((DynamicTable, Anything))
def _fill_dt_anything(dt, anything, **kwargs):
    fill(dt, [anything], **kwargs)


fill.prefer((DynamicTable, Anything), (object, Mapping))
fill.prefer((DynamicTable.Row, Anything), (object, Mapping))
fill.prefer((Select, types.NoneType), (object, types.NoneType))
fill.prefer((DHTMLSelect, types.NoneType), (object, types.NoneType))
fill.prefer((object, types.NoneType), (Select, object))


class AngularSelect(object):
    BUTTON = "//button[@data-id='{}']"

    def __init__(self, loc, none=None, multi=False):
        self.none = none
        if isinstance(loc, AngularSelect):
            self._loc = loc._loc
        else:
            self._loc = self.BUTTON.format(loc)
        self.multi = multi

    def locate(self):
        return sel.move_to_element(self._loc)

    @property
    def select(self):
        return Select('select#{}'.format(self.did), multi=self.multi)

    @property
    def did(self):
        return sel.element(self._loc).get_attribute('data-id')

    @property
    def is_broken(self):
        return sel.is_displayed(self) and sel.is_displayed(self.select)

    @property
    def is_open(self):
        el = sel.element(self._loc)
        return el.get_attribute('aria-expanded') == "true"

    def open(self):
        sel.click(self._loc)

    def select_by_visible_text(self, text):
        if not self.is_open:
            self.open()
        new_loc = self._loc + '/../div/ul/li/a[contains(., "{}")]'.format(text)
        e = sel.element(new_loc)
        sel.execute_script("arguments[0].scrollIntoView();", e)
        sel.click(new_loc)

    def select_by_value(self, value):
        value = str(value)  # Because what we read from the page is a string
        options_map = [a.value for a in self.select.all_options]
        index = options_map.index(value)
        if not self.is_open:
            self.open()
        new_loc = self._loc + '/../div/ul/li[@data-original-index={}]'.format(index)
        e = sel.element(new_loc)
        sel.execute_script("arguments[0].scrollIntoView();", e)
        sel.click(new_loc)

    @property
    def all_options(self):
        return self.select.all_options

    @property
    def classes(self):
        """Combines class from the button and from select."""
        return sel.classes(self) | sel.classes("select#{}".format(self.did))

    @property
    def options(self):
        return self.select.options

    @property
    def first_selected_option(self):
        new_loc = self._loc + '/span'
        e = sel.element(new_loc)
        text = e.text
        for option in self.all_options:
            if option.text == text:
                return option
        return None

    @property
    def first_selected_option_text(self):
        new_loc = self._loc + '/span'
        e = sel.element(new_loc)
        text = e.text
        return text


@fill.method((AngularSelect, sel.ByText))
@fill.method((AngularSelect, basestring))
def _fill_angular_string(obj, s):
    if s:
        obj.select_by_visible_text(s)
    else:
        return


@fill.method((AngularSelect, sel.ByValue))
def _fill_angular_value(obj, s):
    if s.value:
        obj.select_by_value(s.value)
    else:
        return


@fill.method((AngularSelect, list))
def _fill_angular_list(obj, l):
    for i in l:
        fill(obj, i)


class AngularCalendarInput(Pretty):
    pretty_attrs = "input_name", "click_away_element"

    def __init__(self, input_name, click_away_element):
        self.input_name = input_name
        self.click_away_element = click_away_element

    @property
    def input(self):
        return Input(self.input_name, use_id=True)

    @property
    def clear_button(self):
        return sel.element("../a/img", root=self.input)

    def locate(self):
        return self.input.locate()

    def fill(self, value):
        if isinstance(value, date):
            value = '{}/{}/{}'.format(value.month, value.day, value.year)
        else:
            value = str(value)
        try:
            sel.click(self.input)
            sel.set_text(self.input, value)
        finally:
            # To ensure the calendar itself is closed
            sel.click(self.click_away_element)

    def clear(self):
        if sel.text(self.input).strip():
            sel.click(self.clear_button)


@fill.method((AngularCalendarInput, Anything))
def _fill_angular_calendar_input(obj, a):
    return obj.fill(a)


class EmailSelectForm(Pretty):
    """Class encapsulating the e-mail selector, eg. in Control/Alarms editing."""
    fields = Region(locators=dict(
        from_address=Input('from'),
        user_emails={
            version.LOWEST: Select("//select[@id='user_email']"),
            "5.5": AngularSelect("user_email")},
        manual_input=Input('email'),
        add_email_manually={
            version.LOWEST: "(//img | //i)[@title='Add' and contains(@onclick, 'add_email')]",
            "5.5": "//div[@alt='Add']/i"}
    ))

    @property
    def to_emails(self):
        """Returns list of e-mails that are selected"""
        return [
            sel.text(el)
            for el
            in sel.elements("//a[contains(@href, 'remove_email')]")
        ]

    @property
    def user_emails(self):
        """Returns list of e-mail that users inside CFME have so that they can be selected"""
        try:
            return [
                sel.get_attribute(el, "value")
                for el
                in self.fields.user_emails.options
                if len(sel.get_attribute(el, "value").strip()) > 0
            ]
        except NoSuchElementException:  # It disappears when empty
            return []

    def remove_email(self, email):
        """Remove specified e-mail

        Args:
            email: E-mail to remove
        """
        if email in self.to_emails:
            sel.click("//a[contains(@href, 'remove_email')][normalize-space(.)='{}']".format(email))
            return email not in self.to_emails
        else:
            return True

    @to_emails.setter
    def to_emails(self, emails):
        """Function for filling e-mails

        Args:
            emails: List of e-mails that should be filled. Any existing e-mails that are not in this
                variable will be deleted.
        """
        if isinstance(emails, basestring):
            emails = [emails]
        # Delete e-mails that have nothing to do here
        for email in self.to_emails:
            if email not in emails:
                assert self.remove_email(email), "Could not remove e-mail '{}'".format(email)
        # Add new
        for email in emails:
            if email in self.to_emails:
                continue
            if email in self.user_emails:
                sel.select(self.fields.user_emails, sel.ByValue(email))
            else:
                fill(self.fields.manual_input, email)
                sel.click(self.fields.add_email_manually)
                assert email in self.to_emails, "Adding e-mail '{}' manually failed!".format(email)


@fill.method((EmailSelectForm, basestring))
@fill.method((EmailSelectForm, list))
@fill.method((EmailSelectForm, set))
@fill.method((EmailSelectForm, tuple))
def fill_email_select_form(form, emails):
    form.to_emails = emails


class BootstrapSwitch(object):
    def __init__(self, input_id):
        """A Bootstrap On/Off switch

        Args:
            input_id: The HTML ID of the input element associated with the checkbox
        """
        self.input_id = input_id
        self.loc_container = "//input[@id={}]/..".format(quoteattr(self.input_id))
        self.on_off = "{}/span[contains(@class, 'bootstrap-switch-handle-{}')]".format(
            self.loc_container, '{}')

    def fill(self, val):
        """Convenience function"""
        if val:
            self.check()
        else:
            self.uncheck()

    def check(self):
        """Checks the bootstrap box"""
        el = sel.element(self.on_off.format("off"))
        sel.click(el)

    def uncheck(self):
        """Unchecks the bootstrap box"""
        el = sel.element(self.on_off.format("on"))
        sel.click(el)

    def is_selected(self):
        if sel.is_displayed("//div[contains(@class, 'bootstrap-switch-on')]{}"
                .format(self.loc_container)):
            return True
        else:
            return False


@fill.method((BootstrapSwitch, bool))
def fill_bootstrap_switch(bs, val):
    bs.fill(val)


class OldCheckbox(object):
    def __init__(self, input_id):
        """An original HTML checkbox element

        Args:
            input_id: The HTML ID of the input element associated with the checkbox
        """
        self.input_id = input_id
        self.locator = "//input[@id={}]".format(quoteattr(input_id))

    def fill(self, val):
        """
        Checks or unchecks

        Args:
            value: The value the checkbox should represent as a bool (or None to do nothing)

        Returns: Previous state of the checkbox
        """

        if val is not None:
            selected = self.is_selected()

            if selected is not val:
                logger.debug("Setting checkbox {} to {}".format(str(self.locator), str(val)))
                sel.click(self._el)
            return selected

    def check(self):
        """Convenience function"""
        self.fill(True)

    def uncheck(self):
        """Convenience function"""
        self.fill(False)

    def _el(self):
        return sel.move_to_element(self.locator)

    def is_selected(self):
        return self._el().is_selected()


@fill.method((OldCheckbox, bool))
def fill_oldcheckbox_switch(ob, val):
    ob.fill(val)


class CFMECheckbox(Selector):
    def __init__(self, input_id):
        self.input_id = input_id
        super(CFMECheckbox, self).__init__()

    def decide(self):
        ref_loc = "//input[@id={}]/../span" \
            "[contains(@class, 'bootstrap-switch-label')]".format(quoteattr(self.input_id))
        if sel.is_displayed(ref_loc):
            return BootstrapSwitch(self.input_id)
        else:
            return OldCheckbox(self.input_id)


@fill.method((CFMECheckbox, bool))
def fill_cfmecheckbox_switch(ob, val):
    ob.fill(val)


def breadcrumbs():
    """Returns a list of breadcrumbs.

    Returns:
        :py:class:`list` of breadcrumbs if they are present, :py:class:`NoneType` otherwise.
    """
    result = map(sel.text_sane, sel.elements('//ol[contains(@class, "breadcrumb")]/li'))
    return result if result else None


SUMMARY_TITLE_LOCATORS = [
    '//h1'
]

SUMMARY_TITLE_LOCATORS = '|'.join(SUMMARY_TITLE_LOCATORS)


def summary_title():
    """Returns a title of the page.

    Returns:
        :py:class:`str` if present, :py:class:`NoneType` otherwise.
    """
    try:
        return sel.text_sane(SUMMARY_TITLE_LOCATORS)
    except sel.NoSuchElementException:
        return None


class StatusBox(object):
    """ Status box as seen in containers overview page

    Status box modelling.

    Args:
        name: The name of the status box as it appears in CFME, e.g. 'Nodes'

    Returns: A StatusBox instance.

    """
    def __init__(self, name):
        self.name = name

    def value(self):
        return sel.element(
            '//span[contains(@class, "card-pf-aggregate-status-count")]'
            '/../../span[contains(., "{}")]/span'.format(self.name)).text
