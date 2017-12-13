"""Provides a number of objects to help with managing certain elements in the CFME UI.

 Specifically there are two categories of objects, organizational and elemental.

* **Organizational**

  * :py:class:`Region`
  * :py:mod:`cfme.web_ui.menu`

* **Elemental**

  * :py:class:`AngularSelect`
  * :py:class:`DriftGrid`
  * :py:class:`Form`
  * :py:class:`InfoBlock`
  * :py:class:`Input`
  * :py:class:`Select`
  * :py:class:`Table`
  * :py:class:`Tree`
  * :py:mod:`cfme.web_ui.flash`
  * :py:mod:`cfme.web_ui.form_buttons`
  * :py:mod:`cfme.web_ui.listaccordion`
  * :py:mod:`cfme.web_ui.mixins`
  * :py:mod:`cfme.web_ui.toolbar`

"""

from collections import Sequence, Mapping, Callable
from xml.sax.saxutils import quoteattr, unescape

import re
import types
from cached_property import cached_property
from multimethods import multimethod, multidispatch, Anything
from selenium.common import exceptions as sel_exceptions
from selenium.common.exceptions import NoSuchElementException
from widgetastic.xpath import quote

import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions
# For backward compatibility with code that pulls in Select from web_ui instead of sel
from cfme.fixtures.pytest_selenium import Select
from cfme.fixtures.pytest_selenium import browser
from cfme.utils import attributize_string, normalize_space, version
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty


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


@fill.method((object, types.NoneType))
@fill.method((types.NoneType, object))
def _sd_fill_none(*args, **kwargs):
    """ Ignore a NoneType """
    pass


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
