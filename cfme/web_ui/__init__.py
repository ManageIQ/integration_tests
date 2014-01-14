"""
cfme.web_ui
-----------

The :py:mod:`cfme.web_ui` module provides a number of objects to help with
managing certain elements in the CFME UI. Specifically there two categories of
objects, organizational and elemental.

* **Organizational**

  * :py:class:`Region`
  * :py:mod:`cfme.web_ui.menu`

* **Elemental**

  * :py:class:`Form`
  * :py:class:`InfoBlock`
  * :py:class:`Table`
  * :py:mod:`cfme.web_ui.toolbar`
  * :py:class:`Tree`
  * :py:class:`Radio`

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


Example usage of Form
^^^^^^^^^^^^^^^^^^^^^

Below is an example of how to define a form.::

  request_form = web_ui.Form(HostProvision.page,
      ['requester_tab_button', 'email_text', 'first_name_text',
      'last_name_text', 'notes_tarea', 'manager_text'])

Forms can then be filled in like so.::

  request_info = {'requester_tab_button': Click,
                  'email_text': 'test@example.com',
                  'first_name_text': 'John',
                  'last_name_text': 'Doe',
                  'notes_tarea': 'Lots of notes',
                  'manager_text': 'No Manager'}
  request_form.fill_fields(request_info)


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

  table.click_item('name', 'Mike')

We can also perform the same, by using the index of the row, like so::

  table.click_item(1, 'Tiger')


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

  tree.click_path(['Automation', 'VM Lifecycle Management (VMLifecycle)', 'VM Migrate (Migrate)'])

Each path element will be expanded along the way, but will not be clicked.


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
from unittestzero import Assert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from cfme.fixtures.pytest_selenium import browser
import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions
from selenium.common import exceptions as sel_exceptions
import selenium


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

    def __init__(self, locators={}, title=None, identifying_loc=None):
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
        self._headers = self._hc.find_elements_by_xpath('td | th')
        self.header_indexes = {
            self._convert_header(cell.text): self._headers.index(cell) + 1
            for cell in self._headers}

    def _items_generator(self):
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

    def items(self):
        """
        Returns a generator object yielding the items in the Table

        Return: A generator of the items in the Table.
        """
        return self._items_generator()

    def find_item(self, header, value):
        """
        Finds an item in the Table by iterating through each visible item,
        this work used to be done by the :py:meth::`click_item` method but
        has not been abstracted out to be called separately.

        Args:
            header: A string or int, describing which column to inspect.
            data: The value to be compared when trying to identify the correct row
                to click.

        Return: WebElement of the element if item was found, else ``None``.
        """
        list_gen = self._items_generator()

        for item in list_gen:
            if isinstance(header, basestring):
                cell_value = getattr(item, header).text
            elif isinstance(header, int):
                cell_value = item[header].text
            if cell_value == value:
                return item
        else:
            return None

    def click_items(self, data):
        """
        Submits multiple elements to be clicked on

        Args:
            data: A dicts of header names and values direct from yamls, as an example
                ``{'name': ['wing', 'nut']}, {'age': ['12']}`` would click on the items
                who had ``wing`` and ``nut`` in the name column and ``12`` in the age
                column. The yaml example for this would be as follows::

                    list_items:
                        name:
                            - wing
                            - nut
                        age:
                            - 12

        Raises:
            NotAllItemsClicked: If some items were unable to be found.
        """
        failed_clicks = []
        for header, values in data.items():
            if isinstance(values, basestring):
                values = [values]
            for value in values:
                res = self.click_item(header, value)
                if not res:
                    failed_clicks.append("%s:%s" % (header, value))
        if failed_clicks:
            raise exceptions.NotAllItemsClicked(failed_clicks)

    def click_item(self, header, value):
        """
        Clicks on an item defined in the row.

        Uses the header identifier and a data to determine which item to click on.

        Args:
            header: A string or int, describing which column to inspect.
            data: The value to be compared when trying to identify the correct row
                to click.

        Return: ``True`` if item was found and clicked, else ``False``.
        """
        item = self.find_item(header, value)
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
            return self.data.find_elements_by_xpath('td[%s]' % self.header_indexes[name])[0]

        def __getitem__(self, index):
            """
            Returns Row element by header index
            """
            index += 1
            return self.data.find_elements_by_xpath('td[%i]' % index)[0]

        def __str__(self):
            return ",".join([el.text for el in self.data.find_elements_by_xpath('td')])


class Form(object):
    """A helper class for interacting with Form elements on pages.

    The Form class takes a set of locators and binds them together to create a
    unified Form object. This Form object has a defined field order so that the
    user does not have to worry about which order the information is provided.
    This enables the data to be provided as a dict meaning it can be passed directly
    from yamls.

    Args:
        region: Expects a :py:class:`Region`. All locators must be present within the same Region
            context. The region argument is required to define the scope for the retrieval
            of locators.
        field_order: A dict of field names. If this is left empty then no elements
            will be completed. The argument not only defines the order of the elements
            but also which elements comprise part of the form.

    Returns:
        A :py:class:`Form` object.
    """

    field_order = None
    tag_types = {'select': sel.select_by_text,
                 'text': sel.set_text,
                 'checkbox': sel.checkbox,
                 'a': sel.click,
                 'textarea': sel.set_text,
                 'password': sel.set_text}

    def __init__(self, region=None, field_order=None):
        self.field_order = field_order
        self.region = region

    def fill_fields(self, values, action=None):
        """Fills in field elements on forms

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

        Raises:
            cfme.exceptions.UnidentifiableTagType: If the element/object is unknown.
        """
        if isinstance(values, dict):
            values = list((key, values[key]) for key in self.field_order if key in values)
        elif isinstance(values, list):
            values = list(val for key in self.field_order for val in values if val[0] == key)

        for field, value in values:
            loc = self.region.__getattr__(field)
            if isinstance(loc, Table):
                loc._update_cache()
                loc.click_items(value)
                continue
            if isinstance(loc, Radio):
                sel.click(loc.choice(value))
                continue
            tag = sel.tag(loc)
            ttype = sel.get_attribute(loc, 'type')

            if ttype in self.tag_types:
                operation = ttype
            elif tag in self.tag_types:
                operation = tag
            else:
                raise exceptions.UnidentifiableTagType(
                    "Tag '%s' with type '%s' is not a known form element to Form" %
                    (tag, ttype))

            if tag == 'a':
                self.tag_types[operation](loc)
            else:
                self.tag_types[operation](loc, value)

        if action:
            sel.click(self.region.__getattr__(action))


class Radio(object):
    """ A helper object for Radio button groups

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


class Tree(object):
    """ A helper class directed at CFME Tree elements

    The Tree class aims to deal with all kinds of CFME trees, at time of writing there
    are two distinct types. One which uses ``<table>`` elements and another which uses
    ``<ul>`` elements.

    On invocation, the class first determines which type of Tree object it is dealing
    with and then sets the internal variables to match elements of the specific tree class.
    There are currently 4 attributes needed in the tree classes.

    * expandable: the element to check if the tree is expanded/collapsed.
    * is_expanded_condition: a tuple containing the element attribute and value to
      identify that an element **is** expanded.
    * node_search: an XPATH which describes a node, needing expansion with format specifier for
      matching.
    * click_expand: the element to click on to expand the tree at that level.

    .. note:: For legacy trees, the first element is often ignore as it is not a proper tree element
       ie. in Automate->Explorer the Datastore element doesn't really exist, so we omit it from
       the click map.

       Legacy trees rely on a complex ``<table><tbody><tr><td>`` setup. We class a ``<tbody>``
       as a node.

    .. note:: Dynatrees, rely on a ``<ul><li>`` setup. We class a ``<li>`` as a node.

    Args:
        locator: This is a locator object pointing to either the outer ``<table>`` or
            ``<ul>`` element which contains the rest of the table.
        no_root_icon: Some trees do not have an icon for the first root element and as such
            do not need it to be expanded as this is done gratis. A bool is expected.

    Returns: A :py:class:`Tree` object.
    """

    def __init__(self, locator):
        self.root_el = sel.element(locator)
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

    def is_expanded(self, el):
        """ Checks to see if an element is expanded

        Args:
            el: The element to check.

        Returns: ``True`` if the element is expanded, ``False`` if not.
        """
        meta = el.find_element_by_xpath(self.expandable)
        if self.is_expanded_condition[1] in sel.get_attribute(
                meta, self.is_expanded_condition[0]):
            return True
        else:
            return False

    def expand(self, el):
        """ Expands a tree node

        Checks if a tree node needs expanding and then expands it.

        Args:
            el: The element to expand.
        """
        if not self.is_expanded(el):
            sel.click(el.find_element_by_xpath(self.click_expand))

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
        root = kwargs.get('root', None)
        root_el = root if root else self.root_el
        path = list(path)

        if root:
            self.expand(root_el)

        needle = path.pop(0)
        xpath = self.node_search % needle

        try:
            new_leaf = root_el.find_element_by_xpath(xpath)
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
        sel.click(leaf.find_element_by_xpath(self.leaf))
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
            els = self.container(ident).find_elements_by_xpath("*")
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
    def __init__(self, name):
        self.name = name

    def checkbox(self):
        return "//input[@type='checkbox' and ../../..//a[@title='%s']]" % self.name

    def locate(self):
        return "//div[@id='quadicon' and ../../..//a[@title='%s']]" % self.name

    def __str__(self):
        return self.locate()
