# -*- coding: utf-8 -*-
import re
from cached_property import cached_property
from multimethods import Anything
from xml.sax.saxutils import quoteattr

from cfme import exceptions
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import fill, paginator
from utils import version
from utils.log import logger
from utils.pretty import Pretty


def _convert_header(header):
    """Convers header cell text into something usable as an identifier.

    Static method which replaces spaces in headers with underscores and strips out
    all other characters to give an identifier.

    Args:
        header: A header name to be converted.

    Returns: A string holding the converted header.
    """
    return re.sub('[^0-9a-zA-Z_]+', '', header.replace(' ', '_')).lower()


class CachedTableHeaders(object):
    """the internal cache of headers

    This allows columns to be moved and the Table updated. The :py:attr:`headers` stores
    the header cache element and the list of headers are stored in _headers. The
    attribute header_indexes is then created, before finally creating the items
    attribute.
    """
    def __init__(self, table):
        self.headers = sel.elements('td | th', root=table.header)
        self.indexes = {
            _convert_header(cell.text): index
            for index, cell in enumerate(self.headers)}


class TableEntryPoint(Pretty):
    pretty_attrs = ['header_offset', 'body_offset']

    def __init__(self, header_offset, body_offset):
        self.header_offset = header_offset
        self.body_offset = body_offset

    @property
    def header(self):
        raise NotImplementedError('You have to use the derived class')

    @property
    def body(self):
        raise NotImplementedError('You have to use the derived class')

    @cached_property
    def headers_cache(self):
        return CachedTableHeaders(self)

    def update_cache(self):
        """refresh the cache in case we know its stale"""
        try:
            del self.headers_cache
        except AttributeError:
            pass  # it's not cached, dont try to be eager
        else:
            self.headers_cache

    @property
    def rows(self):
        for row in sel.elements('./tr', root=self.body)[self.body_offset:]:
            yield row


class Ordinary(TableEntryPoint):
    pretty_attrs = ['header_offset', 'body_offset', 'locator']

    def __init__(self, locator, header_offset=0, body_offset=0):
        super(Ordinary, self).__init__(header_offset, body_offset)
        self.locator = locator

    def locate(self):
        return self.locator

    @property
    def header(self):
        return sel.element('./thead/tr[{}]'.format(self.header_offset + 1), root=self.locator)

    @property
    def body(self):
        return sel.element('./tbody', root=self.locator)


class Split(TableEntryPoint):
    pretty_attrs = ['header_offset', 'body_offset', 'header_locator', 'body_locator']

    def __init__(self, header_locator, body_locator, header_offset=0, body_offset=0):
        super(Split, self).__init__(header_offset, body_offset)
        self.header_locator = header_locator
        self.body_locator = body_locator

    @property
    def header(self):
        return sel.element('./tr[{}]'.format(self.header_offset + 1), root=self.header_locator)

    @property
    def body(self):
        return sel.element(self.body_locator)

    def locate(self):
        return self.body_locator


def InObject(table_title, header_offset=0, body_offset=0):
    """If you want to point to tables inside object view, this is what you want to use.

    Uses Ordinary entry point.

    Args:
        table_title: Text in `p` element preceeding the table
    Returns: XPath locator for the desired table.
    """
    title = quoteattr(table_title)
    locator = '|'.join([
        '//h1[contains(@id, "title")][normalize-space(.)={}]/../../..//table'.format(title),
        '//table[(preceding-sibling::p[1]|preceding-sibling::h3[1])[normalize-space(.)={}]]'.format(
            title)
        ])
    return Ordinary(locator, header_offset=header_offset, body_offset=body_offset)


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
    FEATURES = {}
    CLASS_CACHE = {}
    pretty_attrs = ['entry_point']

    @classmethod
    def feature(cls, name):
        def f(feature_mixin):
            if name in cls.FEATURES:
                raise NameError('Feature {} already specified!'.format(name))
            cls.FEATURES[name] = feature_mixin
            return feature_mixin
        return f

    @classmethod
    def create(cls, entry_point, features=None, table_args=None):
        # Make it a sorted list so the generated class names are the same
        features = sorted(features or [])
        table_args = table_args or {}
        mro = [cls]
        for feature in features:
            if feature not in cls.FEATURES:
                raise NameError(
                    'Feature {} not found in the feature table ({})'.format(
                        repr(feature), repr(cls.FEATURES.keys())))
            mro.append(cls.FEATURES[feature])
        if len(mro) > 1:
            mro.reverse()
            new_table_type_name = ''.join(f.title() for f in features) + 'Table'
            if new_table_type_name not in cls.CLASS_CACHE:
                cls.CLASS_CACHE[new_table_type_name] = type(new_table_type_name, tuple(mro), {})
            new_cls = cls.CLASS_CACHE[new_table_type_name]
        else:
            # Do not create a new class if no feature selected
            new_cls = cls
        return new_cls(entry_point, **table_args)

    def __init__(self, entry_point, **kwargs):
        self.entry_point_raw = entry_point
        if hasattr(self, 'initialize'):
            self.initialize(**kwargs)

    @cached_property
    def entry_point(self):
        """Ensures we can pass string, entry point, or verpick dictionary."""
        if isinstance(self.entry_point_raw, dict):
            picked = version.pick(self.entry_point_raw)
            if not isinstance(picked, TableEntryPoint):
                return Ordinary(picked)
            else:
                return picked
        elif not isinstance(self.entry_point_raw, TableEntryPoint):
            return Ordinary(self.entry_point_raw)
        else:
            return self.entry_point_raw

    def fill(self, cells):
        self.entry_point.update_cache()
        logger.debug('  Clicking Table cell')
        self.click_cells(cells)
        return bool(cells)

    @property
    def headers(self):
        """List of ``<td>`` or ``<th>`` elements in :py:attr:`header_row`

         """
        return self.entry_point.headers_cache.headers

    @property
    def header_indexes(self):
        """Dictionary of header name: column index for this table's rows

        Derived from :py:attr:`headers`

        """
        return self.entry_point.headers_cache.indexes

    def locate(self):
        return sel.move_to_element(self.entry_point)

    def rows(self):
        """A generator method holding the Row objects

        This generator yields Row objects starting at the first data row.

        Yields:
            :py:class:`Table.Row` object corresponding to the next row in the table.
        """
        for row_element in self.entry_point.rows:
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
            if isinstance(header, basestring):
                return getattr(matching_cell_rows[0], header)
            else:
                return matching_cell_rows[0][header]
        except IndexError:
            return None

    def find_rows_by_cells(self, cells, partial_check=False):
        """A fast row finder, based on cell content.

        Args:
            cells: A dict of ``header: value`` pairs or a sequence of
                nested ``(header, value)`` pairs.

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
                root=sel.move_to_element(self))
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
        if partial_check:
            matching_row_filter = lambda heading, value: value in row[heading].text
        else:
            matching_row_filter = lambda heading, value: row[heading].text == value
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
        if click_column is None:
            map(sel.click, rows)
        else:
            map(sel.click, [row[click_column] for row in rows])

    def click_row_by_cells(self, cells, click_column=None, partial_check=False):
        """Click the cell at ``click_column`` in the first row matched by ``cells``

        Args:
            cells: See :py:meth:`Table.find_rows_by_cells`
            click_column: See :py:meth:`Table.click_rows_by_cells`

        """
        row = self.find_row_by_cells(cells, partial_check=partial_check)
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
            return sel.elements('td', root=self.row_element)

        def __getattr__(self, name):
            """
            Returns Row element by header name
            """
            return self.columns[self.table.header_indexes[name.lower()]]

        def __getitem__(self, index):
            """
            Returns Row element by header index or name
            """
            try:
                return self.columns[index]
            except TypeError:
                # Index isn't an int, assume it's a string
                return getattr(self, _convert_header(index))
            # Let IndexError raise

        def __str__(self):
            return ", ".join([repr(el.text) for el in self.columns])

        def __eq__(self, other):
            if isinstance(other, type(self)):
                # Selenium elements support equality checks, so we can, too.
                return self.row_element == other.row_element
            else:
                return id(self) == id(other)

        def locate(self):
            # table.create_row_from_element(row_instance) might actually work...
            return sel.move_to_element(self.row_element)


@Table.feature('sort')
class SortMixin(object):
    """This table is the same as :py:class:`Table`, but with added sorting functionality."""
    @property
    def _sort_by_cell(self):
        try:
            return sel.element(
                "./th[contains(@class, 'sorting_')]",
                root=self.entry_point.header
            )
        except sel.NoSuchElementException:
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
        sel.click(sel.element(
            "./th/a[normalize-space(.)='{}']".format(text),
            root=self.entry_point.header))

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
            assert self.sorted_by == header, "Detected malfunction in table ordering"
        if order != self.sort_order:
            # Change direction
            self.click_header_cell(header)
            assert self.sort_order == order, "Detected malfunction in table ordering"


@Table.feature('checkbox')
class CheckboxMixin(object):
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

    def initialize(self, header_checkbox_locator=None, body_checkbox_locator=None):
        if body_checkbox_locator:
            self._checkbox_loc = body_checkbox_locator
        self._header_checkbox_loc = header_checkbox_locator

    @property
    def header_checkbox(self):
        """Checkbox used to select/deselect all rows"""
        if self._header_checkbox_loc is not None:
            return sel.element(self._header_checkbox_loc)
        else:
            return sel.element(self._checkbox_loc, root=self.entry_point.header)

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

    def fill(self, cells):
        self.entry_point.update_cache()
        logger.debug('  Selecting CheckboxTable row')
        self.select_rows(cells)
        return bool(cells)


@Table.feature('paged')
class PagedMixin(object):
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
        for page in paginator.pages():
            sel.wait_for_element(self)
            row = self.find_row(header, value)
            if row is not None:
                return row


@fill.method((Table, Anything))
def _fill_table_compat(table, cells):
    return table.fill(cells)
