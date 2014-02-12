"""Provides a number of objects to help with managing certain elements in the CFME UI.

 Specifically there are two categories of objects, organizational and elemental.

* **Organizational**

  * :py:class:`Region`
  * :py:mod:`cfme.web_ui.menu`

* **Elemental**

  * :py:class:`Form`
  * :py:class:`InfoBlock`
  * :py:class:`Quadicon`
  * :py:class:`Radio`
  * :py:class:`Table`
  * :py:class:`TabStripForm`
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

import selenium
from selenium.common import exceptions as sel_exceptions
from singledispatch import singledispatch

import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions
from cfme.fixtures.pytest_selenium import browser
from cfme.web_ui import tabstrip

from utils.log import logger


class Region(object):
    """
    Base class for all UI regions/pages

    Args:
        locators: A dict of locator objects for the given region
        title: A string containing the title of the page
        identifying_loc: Not sure

    Usage:

        page = Region(locators={
            'configuration_button': (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']"),
            'discover_button': (By.CSS_SELECTOR,
                "tr[title='Discover Cloud Providers']>td.td_btn_txt>" "div.btn_sel_text")
            },
            title='CloudForms Management Engine: Cloud Providers'
        )

    The elements can then accessed like so::

        page.configuration_button

    Locator attributes will return the locator tuple for that particular element,
    and can be passed on to other functions, such as :py:func:`element` and :py:func:`click`.

    """
    def __getattr__(self, name):
        return self.locators[name]

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

    Usage:

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

    .. note::

        A table is defined by the containers of the header and data areas, and offsets to them.
        This allows a table to include one or more padding rows above the header row. In
        the example above, there is no padding row, as our offset values are set to 0.

    """
    def __init__(self, header_data=None, row_data=None):
        self.header_data = header_data
        self.row_data = row_data
        self._hc = []
        self.init = 0

    @staticmethod
    def _convert_header(header):
        """Convers header cell text into something usable as an identifier.

        Static method which replaces spaces in headers with underscores and strips out
        all other characters to give an identifier.

        Args:
            header: A header name to be converted.

        Returns: A string holding the converted header.
        """
        return re.sub('[^0-9a-zA-Z ]+', '', header).replace(' ', '_').lower()

    @property
    def is_displayed(self):
        """ Whether the table is displayed or not.

        Returns: True if visible, otherwise False
        """
        return sel.is_displayed(self.header_data)

    def _update_cache(self):
        """Updates the internal cache of headers

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
        """A generator method holding the Row objects

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
        """Returns a generator object yielding the rows in the Table

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
        """Submits multiple cells to be clicked on

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
        """Clicks on a cell defined in the row.

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
        """An object representing a row in a Table.

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
    logger.debug('  Filling in [%s], with value "%s"' % (operation, value))
    op = tag_types[operation]
    if op == sel.click:
        if value is True:
            op(loc)
    else:
        op(loc, value)


@fill.register(Table)
def _sd_fill_table(table, cells):
    """ How to fill a table with a value (by selecting the value as cells in the table)
    See Table.click_cells
    """
    table._update_cache()
    logger.debug('  Clicking Table cell')
    table.click_cells(cells)


@fill.register(sel.ObservedText)
def _sd_fill_otext(ot, value):
    """Filled just like a text box."""
    logger.debug('  Filling in [ObservedText], with value "%s"' % value)
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

    For Form objects, the :py:func:`cfme.web_ui.fill` function can also accept
    a list of super tuples instead of a dict. This has the advantage of being able to
    do things like multiple selects in a multiselect without running multiple calls
    to the ``fill`` function, e.g.::

        child_vm_info = [
            ('child_vm', 'machine1'),
            ('child_vm', 'machine2'),
        ]

    This would then be able to make two selections, whereas a dict would not be able
    to do that due to the reuse of the child_vm key.

    Note:
        Using supertuples in a list, although ordered due to the properties of a List,
        will not overide the field order defined in the Form.
    """

    def __init__(self, fields=None, identifying_loc=None):
        self.locators = dict((key, value) for key, value in fields)
        self.fields = fields
        self.identifying_loc = identifying_loc


class _TabStripField(object):
    """A form field type for use in TabStripForms"""
    def __init__(self, ident_string, arg):
        self.ident_string = ident_string
        self.arg = arg


@fill.register(_TabStripField)
def _tabstrip_fill(tabstrip_field, value):
    tabstrip.select_tab(tabstrip_field.ident_string)
    fill(tabstrip_field.arg, value)


class TabStripForm(Form):
    """
    A class for interacting with tabstrip-contained Form elements on pages.

    This behaves exactly like a :py:class:`Form`, but is able to deal with form
    elements being broken up into tabs, accessible via a tab strip.

    Args:
        fields: A list of field name/locator tuples (same as Form implementation)
        tab_fields: A dict with tab names as keys, and each key's value being a list of
            field name/locator tuples. The ordering of fields within a tab is guaranteed
            (as it is with the normal Form) but the ordering of tabs is not guaranteed by default.
            If such ordering is needed, tab_fields can be a ``collections.OrderedDict``.
        identifying_loc: A locator which should be present if the form is visible.

    Usage:

        provisioning_form = web_ui.TabStripForm(
            tab_fields={
                'Request': [
                    ('email', '//input[@name="requester__owner_email"]'),
                    ('first_name', '//input[@id="requester__owner_first_name"]'),
                    ('last_name', '//input[@id="requester__owner_last_name"]'),
                    ('notes', '//textarea[@id="requester__request_notes"]'),
                ],
                'Catalog': [
                    ('instance_name', '//input[@name="service__vm_name"]'),
                    ('instance_description', '//textarea[@id="service__vm_description"]'),
                ]
            }
        )

    Each tab's fields will be exposed by their name on the resulting instance just like fields
    on a Form. Don't use duplicate field names in the ``tab_fields`` dict.

    Forms can then be filled in like so::

        request_info = {
            'email': 'your@email.com',
            'first_name': 'First',
            'last_name': 'Last',
            'notes': 'Notes about this request',
            'instance_name': 'An instance name',
            'instance_description': 'This is my instance!',
        }
        web_ui.fill(provisioning_form, request_info)

    """

    def __init__(self, fields=None, tab_fields=None, identifying_loc=None):
        fields = fields or list()
        for tab_ident, field in tab_fields.iteritems():
            for field_name, field_locator in field:
                fields.append((field_name, _TabStripField(tab_ident, field_locator)))
        super(TabStripForm, self).__init__(fields, identifying_loc)


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
    logger.info('Beginning to fill in form...')
    if isinstance(values, dict):
        values = list((key[0], values[key[0]]) for key in form.fields if key[0] in values)
    elif isinstance(values, list):
        values = list(val for key in form.fields for val in values if val[0] == key[0])

    for field, value in values:
        if value is not None:
            loc = form.locators[field]
            logger.debug(' Dispatching fill for "%s", with value "%s"' % (field, value))
            fill(loc, value)  # re-dispatch to fill for each item

    if action:
        sel.click(form.region.__getattr__(action))
    logger.debug('Finished filling in form')


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

    A Tree object is set up by using a locator which contains the node elements. This element
    will usually be a ``<ul>`` in the case of a Dynatree, or a ``<table>`` in the case of a
    Legacy tree.

    Usage:

         tree = web_ui.Tree((By.XPATH, '//table//tr[@title="Datastore"]/../..'))

    The path can then be navigated to return the last object in the path list, like so::

        tree.click_path('Automation', 'VM Lifecycle Management (VMLifecycle)',
            'VM Migrate (Migrate)')

    Each path element will be expanded along the way, but will not be clicked.

    Note:
      For legacy trees, the first element is often ignore as it is not a proper tree
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
    Quadicon
    """"""""

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
