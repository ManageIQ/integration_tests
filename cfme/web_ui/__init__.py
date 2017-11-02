"""Provides a number of objects to help with managing certain elements in the CFME UI.

 Specifically there are two categories of objects, organizational and elemental.

* **Organizational**

  * :py:class:`Region`
  * :py:mod:`cfme.web_ui.menu`

* **Elemental**

  * :py:class:`AngularCalendarInput`
  * :py:class:`AngularSelect`
  * :py:class:`Calendar`
  * :py:class:`ColorGroup`
  * :py:class:`CheckboxTable`
  * :py:class:`DriftGrid`
  * :py:class:`Form`
  * :py:class:`InfoBlock`
  * :py:class:`Input`
  * :py:class:`MultiFill`
  * :py:class:`Select`
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

import re
import time
import types
from datetime import date
from collections import Sequence, Mapping, Callable, Iterable
from xml.sax.saxutils import quoteattr, unescape

from cached_property import cached_property
from selenium.common import exceptions as sel_exceptions
from selenium.common.exceptions import NoSuchElementException
from multimethods import multimethod, multidispatch, Anything
from widgetastic.xpath import quote

import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions, js
from cfme.fixtures.pytest_selenium import browser
# For backward compatibility with code that pulls in Select from web_ui instead of sel
from cfme.fixtures.pytest_selenium import Select
from cfme.utils import attributize_string, castmap, normalize_space, version
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from wait_for import TimedOutError, wait_for


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
        prefix. They are included on every page, and different for the two versions of the
        appliance, and :py:meth:`is_displayed` strips them off before checking for equality.

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
        window_title = browser_title()

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
        elif self.title and window_title == self.title:
            title_match = True
        else:
            logger.info("Title %s doesn't match expected title %s", window_title, self.title)
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

    def rows_as_list(self):
        """Returns rows as list"""
        return [i for i in self.rows()]

    def row_count(self):
        """Returns row count"""
        return len(self.rows_as_list())

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
        if row:
            self._set_row_checkbox(row, set_to)
        else:
            raise sel_exceptions.NoSuchElementException()

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

    def find_row_by_cell_on_all_pages(self, cells):
        """Find the first row containing cells on all pages

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`

        Returns: The first matching row found on any page

        """
        from cfme.web_ui import paginator
        for _ in paginator.pages():
            sel.wait_for_element(self)
            row = self.find_row_by_cells(cells)
            if row is not None:
                return row


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


@fill_tag.method((Anything, 'number'))
def fill_number(bmbox, val):
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
        fields_seen = set()
        for field in fields:
            try:
                if field[0] in fields_seen:
                    raise ValueError('You cannot have duplicate field names in a Form ({})'.format(
                        field[0]))
                self.locators[field[0]] = field[1]
                if len(field) == 3:
                    self.metadata[field[0]] = field[2]
                fields_seen.add(field[0])
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
            try:
                sel.wait_for_element(loc, timeout=10)
            except TypeError:
                # TypeError - when loc is not resolvable to an element, elements() will yell
                # vvv An alternate scenario when element is not resolvable, just wait a bit.
                time.sleep(1)
            except TimedOutError:
                logger.warning("This element [{}] couldn't be waited for".format(loc))
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
        """Returns the first visible angular helper text (like 'Required')."""
        loc = (
            '{0}/following-sibling::span[not(contains(@class, "ng-hide"))]'
            '| {0}/following-sibling::div/span[not(contains(@class, "ng-hide"))]'
            .format(self.locate()))
        try:
            return sel.text(loc).strip()
        except NoSuchElementException:
            return None

    def __add__(self, string):
        return self.locate() + string

    def __radd__(self, string):
        return string + self.locate()


class BootstrapTreeview(object):
    """A class representing the Bootstrap treeview used in newer builds.

    Implements ``expand_path``, ``click_path``, ``read_contents``. All are implemented in manner
    very similar to the original :py:class:`Tree`.

    Args:
        tree_id: Id of the tree, the closest div to the root ``ul`` element.
    """
    ROOT_ITEMS = './ul/li[not(./span[contains(@class, "indent")])]'
    ROOT_ITEMS_WITH_TEXT = (
        './ul/li[not(./span[contains(@class, "indent")]) and contains(normalize-space(.), {text})]')
    SELECTED_ITEM = './ul/li[contains(@class, "node-selected")]'
    CHILD_ITEMS = (
        './ul/li[starts-with(@data-nodeid, {id})'
        ' and count(./span[contains(@class, "indent")])={indent}]')
    CHILD_ITEMS_TEXT = (
        './ul/li[starts-with(@data-nodeid, {id})'
        ' and contains(normalize-space(.), {text})'
        ' and count(./span[contains(@class, "indent")])={indent}]')
    ITEM_BY_NODEID = './ul/li[@data-nodeid={}]'
    IS_EXPANDABLE = './span[contains(@class, "expand-icon")]'
    IS_EXPANDED = './span[contains(@class, "expand-icon") and contains(@class, "fa-angle-down")]'
    IS_CHECKABLE = './span[contains(@class, "check-icon")]'
    IS_CHECKED = './span[contains(@class, "check-icon") and contains(@class, "fa-check-square-o")]'
    IS_LOADING = './span[contains(@class, "expand-icon") and contains(@class, "fa-spinner")]'
    INDENT = './span[contains(@class, "indent")]'

    def __init__(self, tree_id):
        self.tree_id = tree_id

    @classmethod
    def image_getter(cls, item):
        """Look up the image that is hidden in the style tag

        Returns:
            The name of the image without the hash, path and extension.
        """
        try:
            image_node = sel.element('./span[contains(@class, "node-image")]', root=item)
        except NoSuchElementException:
            return None
        style = sel.get_attribute(image_node, 'style')
        image_href = re.search(r'url\("([^"]+)"\)', style).groups()[0]
        return re.search(r'/([^/]+)-[0-9a-f]+\.png$', image_href).groups()[0]

    def locate(self):
        return '#{}'.format(self.tree_id)

    @property
    def selected_item(self):
        return sel.element(self.SELECTED_ITEM, root=self)

    @classmethod
    def indents(cls, item):
        return len(sel.elements(cls.INDENT, root=item))

    @classmethod
    def is_expandable(cls, item):
        return bool(sel.elements(cls.IS_EXPANDABLE, root=item))

    @classmethod
    def is_expanded(cls, item):
        return bool(sel.elements(cls.IS_EXPANDED, root=item))

    @classmethod
    def is_checkable(cls, item):
        return bool(sel.elements(cls.IS_CHECKABLE, root=item))

    @classmethod
    def is_checked(cls, item):
        return bool(sel.elements(cls.IS_CHECKED, root=item))

    @classmethod
    def is_loading(cls, item):
        return bool(sel.elements(cls.IS_LOADING, root=item))

    @classmethod
    def is_collapsed(cls, item):
        return not cls.is_expanded(item)

    @classmethod
    def is_selected(cls, item):
        return 'node-selected' in sel.classes(item)

    @classmethod
    def get_nodeid(cls, item):
        return sel.get_attribute(item, 'data-nodeid')

    @classmethod
    def get_expand_arrow(cls, item):
        return sel.element(cls.IS_EXPANDABLE, root=item)

    def child_items(self, item=None):
        if item is not None:
            nodeid = unescape(quoteattr(self.get_nodeid(item) + '.'))
            node_indents = self.indents(item) + 1
            return sel.elements(self.CHILD_ITEMS.format(id=nodeid, indent=node_indents), root=self)
        else:
            return sel.elements(self.ROOT_ITEMS, root=self)

    def child_items_with_text(self, item, text):
        text = unescape(quoteattr(text))
        if item is not None:
            nodeid = unescape(quoteattr(self.get_nodeid(item) + '.'))
            node_indents = self.indents(item) + 1
            return sel.elements(
                self.CHILD_ITEMS_TEXT.format(id=nodeid, text=text, indent=node_indents), root=self)
        else:
            return sel.elements(self.ROOT_ITEMS_WITH_TEXT.format(text=text), root=self)

    def get_item_by_nodeid(self, nodeid):
        nodeid_q = unescape(quoteattr(nodeid))
        try:
            return sel.element(self.ITEM_BY_NODEID.format(nodeid_q), root=self)
        except NoSuchElementException:
            raise exceptions.CandidateNotFound({
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
        logger.trace('Expanding node %s on tree %s', nodeid, self.tree_id)
        node = self.get_item_by_nodeid(nodeid)
        if not self.is_expandable(node):
            return False
        if self.is_collapsed(node):
            arrow = self.get_expand_arrow(node)
            sel.click(arrow)
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
        logger.trace('Collapsing node %s on tree %s', nodeid, self.tree_id)
        node = self.get_item_by_nodeid(nodeid)
        if not self.is_expandable(node):
            return False
        if self.is_expanded(node):
            arrow = self.get_expand_arrow(node)
            sel.click(arrow)
            time.sleep(0.1)
            wait_for(
                lambda: self.is_collapsed(self.get_item_by_nodeid(nodeid)),
                delay=0.2, num_sec=10)
        return True

    @classmethod
    def _process_step(cls, step):
        """Steps can be plain strings or tuples when matching images"""
        if isinstance(step, dict):
            # Version pick and call again ...
            return cls._process_step(version.pick(step))
        if isinstance(step, tuple):
            image = step[0]
            step = step[1]
        else:
            image = None
        if not isinstance(step, (basestring, re._pattern_type)):
            step = str(step)
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

    @classmethod
    def validate_node(cls, node, matcher, image):
        text = sel.text(node)
        if isinstance(matcher, re._pattern_type):
            match = matcher.match(text) is not None
        else:
            match = matcher == text
        if not match:
            return False
        if image is not None and cls.image_getter(node) != image:
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
        sel.wait_for_ajax()
        logger.info('Expanding path %s on tree %s', self.pretty_path(path), self.tree_id)
        node = None
        steps_tried = []

        for step in path:
            steps_tried.append(step)
            image, step = self._process_step(step)
            if node is not None and not self.expand_node(self.get_nodeid(node)):
                raise exceptions.CandidateNotFound({
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
                try:
                    cause = 'Was not found in {}'.format(
                        self._repr_step(*self._process_step(steps_tried[-2])))
                except IndexError:
                    # There is only one item, probably root?
                    cause = 'Could not find {}'.format(
                        self._repr_step(*self._process_step(steps_tried[0])))
                raise exceptions.CandidateNotFound({
                    'message':
                        'Could not find the item {} in Boostrap tree {}'.format(
                            self.pretty_path(steps_tried),
                            self.tree_id),
                    'path': path,
                    'cause': cause})

        return node

    def click_path(self, *path, **kwargs):
        """Expands the path and clicks the leaf node.

        See :py:meth:`expand_path` for more informations about synopsis.
        """
        node = self.expand_path(*path, **kwargs)
        sel.click(node)
        return node

    def read_contents(self, nodeid=None, include_images=False, collapse_after_read=False):
        if nodeid is not None:
            item = self.get_item_by_nodeid(nodeid)
            self.expand_node(nodeid)
        else:
            item = None
        result = []

        for child_item in self.child_items(item):
            result.append(
                self.read_contents(
                    nodeid=self.get_nodeid(child_item),
                    include_images=include_images,
                    collapse_after_read=collapse_after_read))

        if collapse_after_read and nodeid is not None:
            self.collapse_node(nodeid)

        if include_images and item is not None:
            this_item = (self.image_getter(item), sel.text(item))
        elif item is not None:
            this_item = sel.text(item)
        else:
            this_item = None
        if result and this_item is not None:
            return [this_item, result]
        elif result:
            return result
        else:
            return this_item

    def check_uncheck_node(self, check, *path, **kwargs):
        leaf = self.expand_path(*path, **kwargs)
        if not self.is_checkable(leaf):
            raise TypeError('Item with path {} in {} is not checkable'.format(
                self.pretty_path(path), self.tree_id))
        checked = self.is_checked(leaf)
        if checked != check:
            sel.click(sel.element(self.IS_CHECKABLE, root=leaf))

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
            if t is None:
                return
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
                return

        result = _find_in_tree(self.read_contents())
        if result is None:
            raise NameError("{} not found in tree".format(target.pattern))
        else:
            return result


@fill.method((BootstrapTreeview, Sequence))
def _fill_bstree_seq(tree, values):
    if not values:
        return None
    try:
        if isinstance(values[0], types.StringTypes):
            tree.click_path(*values)
        elif isinstance(values[0], Iterable):
            for check in values:
                tree.check_uncheck_node(check[1], *check[0])
    except IndexError:
        tree.click_path(*values)


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
            '//table//th[contains(normalize-space(.), "{}")]/../../../..'.format(
                self.title),
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


class DriftGrid(Pretty):
    """ Class representing the table (grid) specific to host drift analysis comparison page
    """

    def __init__(self, loc="//div[@id='compare-grid']"):
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
        cell_loc = ".//th[contains(normalize-space(.), '{}')]/../td[{}]".format(row_text,
                                                                                col_index + 1)
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
            cell_img = sel.element(".//i | .//img", root=cell)
            return sel.get_attribute(cell_img, "title") == 'Changed from previous'
        # or text
        except NoSuchElementException:
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


fill.prefer((Select, types.NoneType), (object, types.NoneType))
fill.prefer((object, types.NoneType), (Select, object))


class AngularSelect(Pretty):
    BUTTON = "//button[@data-id='{}']"

    pretty_attrs = ['_loc', 'none', 'multi', 'exact']

    def __init__(self, loc, none=None, multi=False, exact=False):
        self.none = none
        if isinstance(loc, AngularSelect):
            self._loc = loc._loc
        else:
            self._loc = self.BUTTON.format(loc)
        self.multi = multi
        self.exact = exact

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
        if self.exact:
            new_loc = self._loc + '/../div/ul/li/a[normalize-space(.)={}]'.format(
                unescape(quoteattr(text)))
        else:
            new_loc = self._loc + '/../div/ul/li/a[contains(normalize-space(.), {})]'.format(
                unescape(quoteattr(text)))
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


def breadcrumbs():
    """Returns a list of breadcrumbs names if names==True else return as elements.

    Returns:
        :py:class:`list` of breadcrumbs if they are present, :py:class:`NoneType` otherwise.
    """
    elems = sel.elements('//ol[contains(@class, "breadcrumb")]/li')
    return elems if elems else None


def breadcrumbs_names():
    elems = breadcrumbs()
    if elems:
        return map(sel.text_sane, elems)


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


def browser_title():
    """Returns a title of the page.

    Returns:
        :py:class:`str` if present, :py:class:`NoneType` otherwise.
    """
    try:
        return browser().title.split(': ', 1)[1]
    except IndexError:
        return None


def controller_name():
    """Returns a title of the page.

    Returns:
        :py:class:`str` if present, :py:class:`NoneType` otherwise.
    """
    return sel.execute_script('return ManageIQ.controller;')


def match_location(controller=None, title=None, summary=None):
    """Does exact match of passed data

        Returns:
        :py:class:`bool`
    """
    result = []
    if controller:
        result.append(controller_name() == controller)
    if title:
        result.append(browser_title() == title)
    if summary:
        result.append((summary_title() == summary) or
                      (sel.is_displayed('//h3[normalize-space(.) = {}]'.format(quote(summary)))))

    return all(result)
