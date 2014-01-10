Web UI Usage
============

The :py:mod:`cfme.web_ui` module is provides a number of objects to help with
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
