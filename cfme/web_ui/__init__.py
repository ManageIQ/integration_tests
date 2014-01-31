"""Provides a number of objects to help with managing certain elements in the CFME UI.

 Specifically there are two categories of objects, organizational and elemental.

* **Organizational**

  * :py:class:`Region`
  * :py:mod:`cfme.web_ui.menu`

* **Elemental**

  * :py:mod:`cfme.web_ui.accordion`
  * :py:class:`Form`
  * :py:class:`InfoBlock`
  * :py:class:`Table`
  * :py:mod:`cfme.web_ui.toolbar`
  * :py:class:`Tree`
  * :py:class:`Radio`


Example usage of Accordion
^^^^^^^^^^^^^^^^^^^^^^^^^^

Using Accordions is simply a case of either selecting it to return the element,
or using the built in click method. As shown below::

  acc = web_ui.accordion

  acc.click('Diagnostics')
  acc.is_active('Diagnostics')


Example usage of Form
^^^^^^^^^^^^^^^^^^^^^

Below is an example of how to define a form.::

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

  provider_info = {'type_select': "OpenStack",
                   'name_text': "RHOS-01",
                   'hostname_text': "RHOS-01",
                   'ipaddress_text': "10.0.0.0",
                   'api_port': "5000",}
  web_ui.fill(provider_form, request_info)


Example usage of InfoBlock
^^^^^^^^^^^^^^^^^^^^^^^^^^
An InfoBlock only needs to know the **type** of InfoBlocks you are trying to address. You can
then return either text, the first element inside the value or all elements::

  block = web_ui.InfoBlock("form")

  block.text('Basic Information', 'Hostname')
  block.element('Basic Information', 'Company Name')
  block.elements('NTP Servers', 'Servers')

These will return a string, a webelement and a List of webelements respectively.


Example usage of Table
^^^^^^^^^^^^^^^^^^^^^^
A table is defined by the containers of the header and data areas, and offsets to them.
This allows a table to include one or more padding rows above the header row. Notice in
the example below, there is no padding row, as our offset values are set to 0.::

  table = Table(header_data=('//div[@id="prov_pxe_img_div"]//thead', 0),
                row_data=('//div[@id="prov_pxe_img_div"]//tbody', 0))

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

We can also perform the same, by using the index of the row, like so::

  table.click_cell(1, 'Tiger')


Example usage of toolbar
^^^^^^^^^^^^^^^^^^^^^^^^
The main CFME toolbar is accessed by using the Root and Sub titles of the buttons, simply::

  tb = web_ui.toolbar
  tb.select('Configuration', 'Add a New Host')


Example usage of Tree
^^^^^^^^^^^^^^^^^^^^^
A Tree object is set up by using a locator which contains the node elements. This element
will usually be a ``<ul>`` in the case of a Dynatree, or a ``<table>`` in the case of a
Legacy tree. The Tree is instantiated, like so::

  tree = web_ui.Tree((By.XPATH, '//table//tr[@title="Datastore"]/../..'))

The path can then be navigated to return the last object in the path list, like so::

  tree.click_path('Automation', 'VM Lifecycle Management (VMLifecycle)', 'VM Migrate (Migrate)')

Each path element will be expanded along the way, but will not be clicked.


Example usage of Quadicon
^^^^^^^^^^^^^^^^^^^^^^^^^
A Quadicon is used by defining the name of the icon and the type. After that, it can be used
to obtain the locator of the Quadicon, or query its quadrants, via attributes like so::

  qi = web_ui.Quadicon('hostname.local', 'host')
  qi.creds
  click(qi)


Example usage of Radio
^^^^^^^^^^^^^^^^^^^^^^
A Radio object is defined by its group name and is simply used like so::

  radio = Radio("schedule__schedule_type")

A specific radio element can then be returned by running the following::

  el = radio.choice('immediately')
  click(el)

The :py:class:`Radio` object can be reused over and over with repeated calls to
the :py:func:`Radio.choice` method.


Example usage of Regions
^^^^^^^^^^^^^^^^^^^^^^^^

Below is an example of how to define a region.::

  page = Region(locators=
                {'configuration_button': (By.CSS_SELECTOR,
                     "div.dhx_toolbar_btn[title='Configuration']"),
                 'discover_button': (By.CSS_SELECTOR,
                     "tr[title='Discover Cloud Providers']>td.td_btn_txt>"
                     "div.btn_sel_text")},
              title='CloudForms Management Engine: Cloud Providers')

The elements can then accessed like so.::

  page.configuration_button

Which will return the locator tuple for that particular element.

"""

import re
import os.path
from unittestzero import Assert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from cfme.fixtures.pytest_selenium import browser
import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions
from selenium.common import exceptions as sel_exceptions
import selenium
from singledispatch import singledispatch
import types


class Region(object):
    """
    Base class for all UI regions/pages

    Args:
        locators: A dict of locator objects for the given region
        title: A string containing the title of the page
        identifying_loc: Not sure
    Return: A :py:class:`Region`
    """
    def __getattr__(self, name):
        return self.locators[name]

    def __init__(self, locators=None, title=None, identifying_loc=None):
        self.locators = locators
        self.identifying_loc = identifying_loc
        self.title = title

    def is_displayed(self):
        """
        Checks to see if the region is currently displayed

        Returns: A boolean describing if the region is currently displayed
        """
        Assert.true(self.identifying_loc is not None or
                    self.title is not None,
                    msg="Region doesn't have an identifying locator or title," +
                    "can't determine if it's current page.")
        if self.identifying_loc:
            ident_match = browser().is_displayed(self.locators[self.identifying_loc])
        else:
            ident_match = True
            if self.title:
                title_match = browser().title == self.title
            else:
                title_match = True
        return ident_match and title_match


def get_context_current_page():
    """
    Returns the current page name

    Returns: A string containing the current page name
    """
    url = browser().current_url()
    stripped = url.lstrip('https://')
    return stripped[stripped.find('/'):stripped.rfind('?')]


def handle_popup(cancel=False):
    """
    Handles a popup

    Args:
        cancel: If ``True``, clicks OK, if ``False``, clicks Cancel
    """
    wait = WebDriverWait(browser(), 30.0)
    # throws timeout exception if not found
    wait.until(EC.alert_is_present())
    popup = browser().switch_to_alert()
    answer = 'cancel' if cancel else 'ok'
    print popup.text + " ...clicking " + answer
    popup.dismiss() if cancel else popup.accept()


class Table(object):
    """
    Helper class for Table/List objects

    Turns CFME custom Table/Lists into iterable objects using a generator.

    Args:
        header_data: A tuple, containing an XPATH string locator and an offset value.
            These point to the container of the header row. The offset is used in case
            there is a padding row above the header, or in the case that the header
            and the data are contained inside the same table element.
        row_data: A tuple, containing an XPATH string locator and an offset value.
            These point to the container of the data rows. The offset is used in case
            there is a padding row above the data rows, or in the case that the header
            and the data are contained inside the same table element.

    Attributes:
        header_indexes: A dict of header names related to their index as a column.

    Returns: A :py:class:`Table` object.

    """
    def __init__(self, header_data=None, row_data=None):
        self.header_data = header_data
        self.row_data = row_data
        self._hc = []
        self.init = 0

    @staticmethod
    def _convert_header(header):
        """
        Convers header cell text into something usable as an identifier.

        Static method which replaces spaces in headers with underscores and strips out
        all other characters to give an identifier.

        Args:
            header: A header name to be converted.

        Returns: A string holding the converted header.
        """
        return re.sub('[^0-9a-zA-Z ]+', '', header).replace(' ', '_').lower()

    def _update_cache(self):
        """
        Updates the internal cache of headers

        This allows columns to be moved and the Table updated. The variable _hc stores
        the header cache element and the list of headers are stored in _headers. The
        attribute header_indexes is then created, before finally creating the items
        attribute.
        """
        self._hc = sel.element(self.header_data[0] + '//tr[%i]' % (self.header_data[1] + 1))
        self._headers = sel.elements('td | th', root=self._hc)
        self.header_indexes = {
            self._convert_header(cell.text): self._headers.index(cell) + 1
            for cell in self._headers}

    def _rows_generator(self):
        """
        A generator method holding the Row objects

        This generator yields Row objects starting at the first data row.

        Yields:
            :py:class:`Table.Row` object corresponding to the next row in the table.
        """
        self._update_cache()
        index = self.row_data[1] + 1
        data = sel.element(self.row_data[0] + '//tr[%i]' % (index))
        yield self.Row(self.header_indexes, data, self.row_data[0])
        while isinstance(data, selenium.webdriver.remote.webelement.WebElement):
            index += 1
            try:
                data = sel.element(self.row_data[0] + '//tr[%i]' % (index))
                item = self.Row(self.header_indexes, data, self.row_data[0])
                yield item
            except:
                data = []

    def rows(self):
        """
        Returns a generator object yielding the rows in the Table

        Return: A generator of the rows in the Table.
        """
        return self._rows_generator()

    def find_cell(self, header, value):
        """
        Finds an item in the Table by iterating through each visible item,
        this work used to be done by the :py:meth::`click_cell` method but
        has not been abstracted out to be called separately.

        Args:
            header: A string or int, describing which column to inspect.
            data: The value to be compared when trying to identify the correct row
                to click.

        Return: WebElement of the element if item was found, else ``None``.
        """
        list_gen = self._rows_generator()

        for item in list_gen:
            if isinstance(header, basestring):
                cell_value = getattr(item, header).text
            elif isinstance(header, int):
                cell_value = item[header].text
            if cell_value == value:
                return item
        else:
            return None

    def click_cells(self, data):
        """
        Submits multiple cells to be clicked on

        Args:
            data: A dicts of header names and values direct from yamls, as an example
                ``{'name': ['wing', 'nut']}, {'age': ['12']}`` would click on the cells
                who had ``wing`` and ``nut`` in the name column and ``12`` in the age
                column. The yaml example for this would be as follows::

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
        for header, values in data.items():
            if isinstance(values, basestring):
                values = [values]
            for value in values:
                res = self.click_cell(header, value)
                if not res:
                    failed_clicks.append("%s:%s" % (header, value))
        if failed_clicks:
            raise exceptions.NotAllItemsClicked(failed_clicks)

    def click_cell(self, header, value):
        """
        Clicks on a cell defined in the row.

        Uses the header identifier and a data to determine which cell to click on.

        Args:
            header: A string or int, describing which column to inspect.
            data: The value to be compared when trying to identify the correct row
                to click the cell in.

        Return: ``True`` if item was found and clicked, else ``False``.
        """
        item = self.find_cell(header, value)
        if item:
            sel.click(getattr(item, header))
            return True
        else:
            return False

    class Row(object):
        """
        An object representing a row in a Table.

        The Row object returns a dymanically addressable attribute space so that
        the tables headers are automatically generated.

        Notes:
            Attributes are dynamically generated

        Returns: A :py:class:`Table.Row` object.
        """
        def __init__(self, header_indexes, data, loc):
            self.header_indexes = header_indexes
            self.data = data
            self.loc = loc

        def __getattr__(self, name):
            """
            Returns Row element by header name
            """
            return sel.elements('td[%s]' % self.header_indexes[name], root=self.data)[0]

        def __getitem__(self, index):
            """
            Returns Row element by header index
            """
            index += 1
            return sel.elements('td[%i]' % index, root=self.data)[0]

        def __str__(self):
            return ",".join([el.text for el in sel.elements('td', root=self.data)])


@singledispatch
def fill(arg, content):
    """
    Fills in a UI component with the given content.

    Usage:
        fill(textbox, "text to fill")
        fill(myform, [ ... data to fill ...])
        fill(radio, "choice to select")

    Default implementation just throws an error.
    """
    raise NotImplementedError('Unable to fill {} into this type: {}'.format(content, arg))


@fill.register(str)
def _sd_fill_string(loc, value):
    """
    How to 'fill' a string.  Assumes string is a locator for a UI input element,
    eg textbox, radio button, select list, etc.
    value is the value to input into that element.

    Usage:
        fill("//input[@type='text' and @id='username']", 'admin')

    Raises:
        cfme.exceptions.UnidentifiableTagType: If the element/object is unknown.
    """
    tag_types = {'select': sel.select,
                 'text': sel.set_text,
                 'checkbox': sel.checkbox,
                 'a': sel.click,
                 'img': sel.click,
                 'image': sel.click,
                 'textarea': sel.set_text,
                 'password': sel.set_text,
                 'file': sel.send_keys}

    tag = sel.tag(loc)
    ttype = sel.get_attribute(loc, 'type')

    if ttype in tag_types:
        operation = ttype
    elif tag in tag_types:
        operation = tag
    else:
        raise exceptions.UnidentifiableTagType(
            "Tag '%s' with type '%s' is not a known form element to Form" %
            (tag, ttype))
    op = tag_types[operation]
    if op == sel.click:
        op(loc)
    else:
        op(loc, value)


@fill.register(Table)
def _sd_fill_table(table, cells):
    """ How to fill a table with a value (by selecting the value as cells in the table)
    See Table.click_cells
    """
    table._update_cache()
    table.click_cells(cells)


@fill.register(sel.ObservedText)
def _sd_fill_otext(ot, value):
    """Filled just like a text box."""
    sel.set_text(ot, value)


@fill.register(types.NoneType)
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

    Returns:
        A :py:class:`Form` object.
    """

    def __init__(self, fields=None, identifying_loc=None):
        self.locators = dict((key, value) for key, value in fields)
        self.fields = fields
        self.identifying_loc = identifying_loc


@fill.register(Form)
def _sd_fill_form(form, values, action=None):
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
    if isinstance(values, dict):
        values = list((key[0], values[key[0]]) for key in form.fields if key[0] in values)
    elif isinstance(values, list):
        values = list(val for key in form.fields for val in values if val[0] == key[0])

    for field, value in values:
        if value is not None:
            loc = form.locators[field]
            fill(loc, value)  # re-dispatch to fill for each item

    if action:
        sel.click(form.region.__getattr__(action))


class Radio(object):
    """ A class for Radio button groups

    Radio allows the usage of HTML radio elements without resorting to previous
    practice of iterating over elements to find the value. The name of the radio
    group is passed and then when choices are required, the locator is built.

    Args:
        name: The HTML elements ``name`` attribute that identifies a group of radio
            buttons.

    Returns: A :py:class:`Radio` object.
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


@fill.register(Radio)
def _sd_fill_radio(radio, value):
    """How to fill a radio button group (by selecting the given value)"""
    sel.click(radio.choice(value))


class Tree(object):
    """ A class directed at CFME Tree elements

    The Tree class aims to deal with all kinds of CFME trees, at time of writing there
    are two distinct types. One which uses ``<table>`` elements and another which uses
    ``<ul>`` elements.

    Args:
        locator: This is a locator object pointing to either the outer ``<table>`` or
            ``<ul>`` element which contains the rest of the table.

    Returns: A :py:class:`Tree` object.
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

        .. note:: For legacy trees, the first element is often ignore as it is not a proper tree
           element ie. in Automate->Explorer the Datastore element doesn't really exist, so we
           omit it from the click map.

           Legacy trees rely on a complex ``<table><tbody><tr><td>`` setup. We class a ``<tbody>``
           as a node.

        .. note:: Dynatrees, rely on a ``<ul><li>`` setup. We class a ``<li>`` as a node.
        """
        self.root_el = sel.element(self.locator)
        if sel.tag(self.root_el) == 'ul':
            # Dynatree
            self.expandable = 'span'
            self.is_expanded_condition = ('class', 'dynatree-expanded')
            self.node_search = "//li/span/a[contains(., '%s')]/../.."
            self.click_expand = "span/span"
            self.leaf = "span/a"
        elif sel.tag(self.root_el) == 'table':
            # Legacy Tree
            self.expandable = 'tr/td[1]/img'
            self.is_expanded_condition = ('src', 'open.png')
            self.node_search = "//tbody/tr/td/table/tbody/tr/td[4]/span[contains(., '%s')]/../../.."
            self.click_expand = "tr/td[1]/img"
            self.leaf = "tr/td/span"
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

    """
    def __init__(self, itype):
        if itype == "detail":
            self._box_locator = '//div[@class="modbox"]/h2[@class="modtitle"][contains(., "%s")]/..'
            self._pair_locator = 'table/tbody/tr/td[1][@class="label"][contains(., "%s")]/..'
            self._value_locator = 'td[2]'
        elif itype == "form":
            self._box_locator = '//fieldset/p[@class="legend"][contains(., "%s")]/..'
            self._pair_locator = 'table/tbody/tr/td[1][@class="key"][contains(., "%s")]/..'
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
    """ Represents a single quadruple icon in the CFME UI.

    A Quadicon contains multiple quadrants. These are accessed via attributes.
    The qtype is currently one of the following and determines which attribute names
    are present. They are mapped internally and can be reassigned easily if the UI changes.

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

    Args:
       name: The label of the icon.
       qtype: The type of the quad icon.
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
