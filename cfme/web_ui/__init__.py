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
  * :py:class:`Table`
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


Example usage of Radio
^^^^^^^^^^^^^^^^^^^^^^
A Radio object is defined by its group name and is simply used like so::

  radio = Radio("schedule__schedule_type")

A specific radio element can then be returned by running the following::

  el = radio.choice('immediately')
  click(el)

The :py:class:`Radio` object can be reused over and over with repeated calls to
the :py:func:`Radio.choice` method.
"""

import re
from unittestzero import Assert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from cfme.fixtures.pytest_selenium import browser
import cfme.fixtures.pytest_selenium as sel
from cfme import exceptions
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
        items: A generator yielding a :py:class:`Table.Row` object which is
            addressable using the header names or index.

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

    def click_item(self, header, data):
        """
        Clicks on an item defined in the row.

        Uses the header identifier and a data to determine which item to click on.

        Args:
            header: A string or int, describing which column to inspect.
            data: The value to be compared when trying to identify the correct row
                to click.

        Raises:
            cfme.exceptions.NotAllItemsClicked: If some items were unable to be found.
        """
        clicked = []
        if isinstance(data, str):
            data = [data]
        list_gen = self._items_generator()
        for value in data:
            for item in list_gen:
                if isinstance(header, str):
                    cell_value = getattr(item, header).text
                elif isinstance(header, int):
                    cell_value = item[header].text
                if cell_value == value:
                    sel.click(item.data)
                    clicked.append(item)
                    break
        if len(data) != len(clicked):
            missed_items = set(data) - set(clicked)
            raise exceptions.NotAllItemsClicked(
                "Not all the required data elements were clicked [%s]"
                % ", ".join(list(missed_items)))

    class Row():
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
                loc.click_item(*value)
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


class Radio():
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
