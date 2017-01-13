Page Development
================

Introduction
------------

This file is intended to explain how pages should be developed and specify what functionality
should exist in them. Refering to the image below, a page model should contain the following:

* Locators to elements which appear only on that page or set of pages related to the object in
  question.
* Menu items to graft onto the main menu for use inside the pages and operations.
* Classes that are related to objects in the database which are acted upon with CRUD operations
  on that page or set of pages.
* Methods which are used to CRUD operations, with an aim that any of these can use a different
  backend where possible.

Anything else should be added as part of a web_ui component, a fixture or a utility.

.. image:: /_static/framework.png

Pages are read-only python modeling of the CFME UI, allowing the functional tests of the UI to
be ignorant of the underlying page structure. As such, UI elements (pages, regions, forms, etc.)
modeled in `cfme_pages` must provide helper methods and properties to expose a usable
interface to `cfme_tests`. This is explained in more detail in the section on
*Writing Tests* in :doc:`dev_guide`.

Pages should be modeled as a part of writing tests. Code in `cfme_pages` must never depend on
code in `cfme_tests`.

When writing pages, a few points should be noted:

* Follow the standard naming convention for locators

  * Name of element, followed by type from the type list

* Type list: button, select, text, textbox, radio, option
* Ensure that your element is presented in an expected way. As an example,
  presenting a div containing and unordered list in one place and simply
  the unordered list in another, causes an unpredictable inconsistency as
  to how to handle the locator.
* Try to avoid using localized text as part of a locator where possible

Example
-------

Since the majority of development happens in tests and page models, we will deconstruct a page
to see how it is composedW.e will now look at a specific example using the ``cloud/provider.py``
file. Note that there may be subtle differences between the file and this documentation as the
content evolves. It is expected that this document will be updated with any significant changes.

Imports
^^^^^^^

To begin with we have the imports, we have added comments after each to specify their use::

  from functools import partial                   # Standard library
  from selenium.webdriver.common.by import By     # Convenience functions for locators, ID etc.
  import cfme                                     # Core cfme module
  import cfme.web_ui.menu                         # Standard menu for grafting additional menus onto
  from cfme.web_ui import Region, Quadicon, Form  # Loads the Region, Quadicon and Form UI elements
  import cfme.web_ui.flash as flash               # Flash message handler
  import cfme.fixtures.pytest_selenium as sel     # The selenium zero-level functions
  import utils.conf as conf                       # Loads all configuration from the yamls
  from utils.update import Updateable             # Updatable class to give update capabilities
  import cfme.web_ui.toolbar as tb                # Toolbar UI element for clicking Center Toolbar

Locators
^^^^^^^^

Now that we have the tools we need to begin crafting a page, we can start to define the locators.
Locators are used to point to elements on a page. They can reference any html element and will
typically be used:

* to pull out text for comparision, *e.g. making sure a flash message matches what is expected.*
* to send text to, *e.g. for inputting data into forms.*
* to click, *e.g. a button.*

Below is an excerpt from the set of locators on the page::

  page = Region(
      locators={
          'add_submit': "//img[@alt='Add this Cloud Provider']",
          'creds_validate_btn': "//div[@id='default_validate_buttons_on']"
                                "/ul[@id='form_buttons']/li/a/img",
          'creds_verify_disabled_btn': "//div[@id='default_validate_buttons_off']"
                                       "/ul[@id='form_buttons']/li/a/img",
          'cancel_button': "//img[@title='Cancel']",
          'save_button': "//img[@title='Save Changes']",
      },
      title='CloudForms Management Engine: Cloud Providers')

Locators are usually supplied as a Python dict. The key is a name which should conform to the
:doc:`abbrev` guidelines. The value is one of three:

* an XPATH string, as depicted above
* a tuple, containing a CSS selector, e.g. ``(By.CSS_SELECTOR, "div.dhtmlxInfoBarLabel-2 > ul")``
* a tuple, containing an ID selector, e.g. ``(By.ID, "text_button")``

These elements can then be used to perform actions as shown later in the file by::

          if cancel:
              sel.click(page.cancel_button)

Forms
^^^^^

A recent edition to the codebase has been the introduction of Forms using the
:py:class:`cfme.web_ui.Form` web_ui component. Forms allow the defining of a set of locators
which correspond to fields. Data can then be sent to the form object to fill in the fields
automatically, without worrying about field type. We begin by defining a Form::

  form = Form(
      fields=[
          ('type_select', "//*[@id='server_emstype']"),
          ('name_text', "//*[@id='name']"),
          ('hostname_text', "//*[@id='hostname']"),
          ('ipaddress_text', "//*[@id='ipaddress']"),
          ('amazon_region_select', "//*[@id='hostname']"),
          ('api_port', "//*[@id='port']"),
      ])

Notice that a Form is very similar to a Region. In fact, a Form inherits a Region so as above
when we clicked on the cancel button by referencing it as an attribute of the page object. We
can do the same here. ``sel.set_text(form.api_port, "6000")``, for example, would set the text
of the locator described by key value ``api_port`` to ``6000``.

The details to fill in the form are loaded into a variable inside the management object
called ``OpenStackDetails`` in this case::

          def __init__(self, hostname=None, ip_address=None, api_port=None):
              self.details = {'hostname_text': hostname,
                              'ipaddress_text': ip_address,
                              'api_port': api_port,
                              'type_select': 'OpenStack'}

These details are then passed to the Forms fill_fields function::

          details.details.update({'name_text': self.name})
          form.fill_fields(details.details)

Notice that there has been an amendment to the ``details`` dictionary when it has been passed into
the ``_fill_details`` function, and a new key/value called ``name_text`` has been added.

The :py:meth:`cfme.web_ui.Form.fill_fields` Form method then takes these values, does an inspection
of the element types to find out how to handle them (you couldn't set text on a select box for
example), and then sets the values in the most appropriate way.

Toolbar
^^^^^^^

A Toolbar button can be accessed by simple using it in the following way::

  tb.select('Configuration', 'Add a New Cloud Provider')

but in cases where we may have several ``Configuration`` buttons, we can make things a little
simpler to type by making use of ``partial``. Which takes a function and some arguments to create
a shortened form of the function call. In the example below, we define this::

  cfg_btn = partial(tb.select, 'Configuration')

We can now use the toolbars by doing something like the following::

  cfg_btn('Add a New Cloud Provider')


Navigation Menu
^^^^^^^^^^^^^^^

In our provider page we are going to hook in the toolbar button presses to the navigation tree.
This means we are able to do something the code below and have the page execute the toolbar button
clicks to navigate to the page in question. We could simply use the
:py:func:`cfme.web_ui.toolbar.select` function, but to make it clearer that we expect to navigate
away from the current page, using the ``navigate_to`` function is better::

  navigate_to(Provider, 'New')

We need to add a few buttons to the center menu to handle "Add a New Cloud Provider", "Discover
Cloud Providers" and a special case.

The navigation is tree-esque but you cannot determine all tree
nodes and destinations like before. This is because navmazing as a library is far more dynamic
and allows for very powerful navigation. So to add new navigation points onto the tree, we need to
give them a prerequisite step. This can be something to actually perform, or it can be achieved by
linking it to a previous navigation.::

  @navigator.register(CloudProvider, 'Add')
  class New(CFMENavigateStep):
      prerequisite = NavigateToSibling('All')

      def step(self):
          cfg_btn('Add a New Cloud Provider')


  @navigator.register(CloudProvider, 'Discover')
  class Discover(CFMENavigateStep):
      prerequisite = NavigateToSibling('All')

      def step(self):
          cfg_btn('Discover Cloud Providers')


  @navigator.register(CloudProvider, 'Details')
  class Details(CFMENavigateStep):
      prerequisite = NavigateToSibling('All')

      def step(self):
          sel.click(Quadicon(self.obj.name, self.obj.quad_name))


  @navigator.register(CloudProvider, 'Edit')
  class Edit(CFMENavigateStep):
      prerequisite = NavigateToSibling('All')

      def step(self):
          sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
          cfg_btn('Edit Selected Cloud Provider')

As you can see all these steps rely on the ``All`` step, which already exists. Simliar to the old method
these new steps are grafted on to the navigation tree in a way, but the prerequisite step has no
knowledge of the subsequent steps. This is because prerequisite can be dynamic in nature. The product
may be of a certain version/state which requires either the prerequisite or the step to be performed
in a different way.
