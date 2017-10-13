UI modeling
===========

Introduction
------------

This guide shall explain you how does our framework represents things in ManageIQ and its UI and
other endpoints.

Libraries
=========

We use a couple of libraries we designed based on our experience and these libraries work together
to bring us a good developer experience:

* `Navmazing <https://pypi.python.org/pypi/navmazing>`_ - A UI navigation framework which
  registers navigation locations to classes that represent objects or their collections. We
  recommend reading the documentation on the PyPI package page. Referred to as **NM**.
  
  .. note:: Responsible person: *psavage*

* `Widgetastic <https://pypi.python.org/pypi/widgetastic.core>`_ - Page Object Model on steroids.
  Allows mostly declarative specification (Django model inspired) of how does the UI look, what
  things are present, provides unified read and fill interface, rich logs and other useful magic.
  Referred to as **WT**.
  
  .. note:: Responsible person: *mfalesni*

* `Sentaku <http://sentaku.readthedocs.io/en/latest/>`_ - Library that allows you to create an
  object which will have multiple implementations of underlying methods, switching the
  implementations based on context. Curently (Oct 2017) being slowly rolled out in certain parts.
  
  .. note:: Responsible people: *ronny*, *psavage*

Another important concept is :doc:`collections` which you **must** read if you want to create new
models as this guide assumes you are aware of these concepts already.

High-level process description
==============================

Here I will briefly describe the usual code flow how things interact. Think of it as a typical use
case. Don't worry if you don't understand some of the concepts presented here, they will be
explained later.

* A test wants to create something in the UI (``things_collection.create(...)``)

  * The ``create`` method needs to go to the ``Add`` page of ``things_collection``, therefore it
    asks **NM**

    * **NM** starts working by instantiating the final step for target location, then the step's
      **WT** view and it checks whether it already is there. The view does not have to be specified,
      but it is specified for most of our navigation steps.

    * If it is not there, it tries to do the same to the *prerequisite* location recursively until
      it reaches a location that is on screen now or some of the root locations, like
      *LoginPage* or *BaseLoggedInPage* which are the usual "safe points".

    * If there are any steps to be made afterwards, it starts backtracking back to the target
      location by executing the steps' code.

    * **NM**'s navigation returns the **WT** view of the last step.

  * With the **WT** view returned from **NM** knowing that we indeed are on that particular
    location, what usually happens next is that the ``create`` method dumps a dictionary of data
    into view's fill method.

    * **WT**'s view fill goes through the view and fills each widget that was specified in the
      dictionary with the appropriate value. Widgets whose names weren't in the keys will be
      skipped. ``None`` values are also skipped.

  * ``fill`` tells you if it changed anything or not. You then decide what to do next. Usually what
    happens next is that some button is clicked and then a flash messages are asserted.
    You can also create an instance of another view if you know that by clicking the button you will
    get bumped somewhere else and then assert whether that location is displayed or not

  * Finally, ``create`` calls ``instantiate`` on the collection which takes all the required values
    and creates an instance of the thing that was just created in the UI

Some caveats:

* There is a big difference between ``int`` and ``str``. If you insert a numeric
  value into an ordinary input, you need to have it as a string. Of course if you use a widget where
  the only sensible values are numbers, then it will be operating with integers. But if values come
  eg. from YAML, then the numeric value is automatically considered a number unless quoted.
* Remember that Widgetastic doesn't touch fields which already have the required value. In that case
  ``fill`` returns False so you know that nothing was changed.


Navmazing
=========

For the initial explanation on Navmazing, read the guide on PyPI.

We beef Navmazing up locally with extra features, like error detection and Widgetastic integration
in ManageIQ tests. The important ones for developers are Widgetastic integration and object
injection.

If you specify ``VIEW`` on the navigation step class, it then has a default behaviour with
the ``am_i_here`` method, which you don't need to write then. You can also use the ``view`` property
which gives you an instance of that view class. For writing steps, the most useful thing you will
use is the ``prerequisite_view`` as you need to make that particular step from the previous location
and not from the one you are writing the step in.

You usually navigate withing the context of some object. Navmazing then passes the object into the
Widgetastic view as well - ``self.context["object"]``. You then use it to assert things in the UI
with the data pulled from the object, like titles and so on.

Let's look at an example here:

.. code-block:: python

    @navigator.register(NamespaceCollection)
    class Add(CFMENavigateStep):
        VIEW = NamespaceAddView
        prerequisite = NavigateToAttribute('parent', 'Details')

        def step(self):
            self.prerequisite_view.configuration.item_select('Add a New Namespace')

This piece of code tells us these things:

* We register this location against ``NamespaceCollection``.
* We name the location ``Add``.
* The location's UI is represented by ``NamespaceAddView``.
* In order to get to this location, we first need to go to the ``Details`` location of this object's
  parent (``self.parent``). This is the declarative recursive relationship mentioned in the high
  level process description.
* In order to get from parent's details to the dialog for adding a new namespace, we need to click
  on the "Add a New Namespace" item in the ``Configuration`` dropdown. We use ``prerequisite_view``
  because on the actual ``Add`` view there is no Configuration dropdown.

The step definition can also contain the ``resetter`` method. That one is used when you have pages
that remember certain settings and you want to make sure, that before the step executes, the page
is in a known state.

The "root" navigation locations, like login page, dashboard, the initial pages of all menu item
destinations ... these are registered against so-called ``Server`` instance. When dealing with the
appliance object, it is ``appliance.server`` if you need to navigate to one of those.

If you are going to implement new models, make sure you look around for existing navigation
locations that you may build on top of.

.. warning:: The actual ``step`` method should *ideally* contain one singular action, like clicking
  a button or selecting a thing from tree. This is not a hard requirement, but unless it is needed,
  we should avoid it.

Also when picking a prerequisite, try **avoiding unnecessary steps**. And example would be a page
with a tree on left side. If you know the tree path of your model object and the object has a
parent, you don't need to invoke parent's details first and then go on with the actual object's
details, because it will select an item in the tree twice while you can just go straight for the
object's item since selecting the parent is not a prerequisite for getting there.


Widgetastic
===========

For the initial explanation on Widgetastic, read the guide on PyPI.

If you know Django models, then Widgetastic should be very familiar and intuitive for you. If not,
it should be intuitive.

Let's start with a code sample:

.. code-block:: python

    from cfme.base.login import BaseLoggedInPage

    class SomeForm(BaseLoggedInPage):
        title = Text('#title_text')
        name = Input(name='field_name')
        type = BootstrapSelect(id='field_type')

        @property
        def is_displayed(self):
            return self.title.text == 'Editing "{}"'.format(self.context['object'].name)

.. note:: All views (for the main UI) except the login page descend from ``BaseLoggedInPage`` in
  some manner.

In Widgetastic, interactive and non-interactive UI elements are represented by so-called widgets,
which are classes that implement interaction with the UI element in a consistent manner.

Widgets are usally grouped on a ``View``, which itself is also a widget, so you can nest the
structure if you need.

Each widget has its own rules concerning constructor parameters, you should read the documentation
for each of them.

Any sequential actions happen in the order of definition on the view. So if you fill some values by
feeding a dictionary into the ``view.fill(...)`` method, it will always follow the order of
definition.

If you have a nested view and the order is important, you need to decorate it with ``View.nested``,
otherwise the view will be out of the assumed order.

You can fence the element lookup on the view by setting ``ROOT`` to a locator. Then before any
element is looked up as a result of interaction of any of the widgets on the particular view, the
``ROOT`` element is looked up first and the following lookup happens in context of it. Imagine the
use case as if you had multiple boxes that have IDs and then have the same classes and no IDs on
things inside. This way you can divide and control.

.. warning::  If you want to instantiate a view for testing, use ``appliance.browser.create_view``
  and pass the view class and optionally the object that the view uses for asserting. If you want to
  instantiate a plain widget, grab a Widgetastic's ``Browser`` (``appliance.browser.widgetastic``)
  and put it as **the first argument** before any widget's init parameters. If you don't pass the
  browser, it will not work (I told you so).

.. note:: If you want to understand why, read about Python's descriptors. If you instantiate a
  ``Widget`` without the browser or a parent widget as a first argument, the ``Widget`` class
  recognizes it and instead of instantiating an instance of that particular
  ``Widget`` it creates and returns an instance of ``WidgetDescriptor`` that remembers the widget
  class, args and kwargs and it then instantiates the true widget instance upon accessing on the
  parent's instance using descriptor protocol. Try accessing the same widget on a class and on the
  instance. See the difference?

Apart from this simple usage, Widgetastic allows you to do a number of advanced constructs that are
described in Widgetastic's guide. You should familiarize with them. Especially with Version picking
which is probably the most used feature.

Sentaku
=======

WIP.