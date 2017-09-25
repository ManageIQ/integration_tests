Designing Models
================

General Guidelines
------------------

In general, any object that is represented in the MiQ Appliance is going to be only relevant
along with the context of a particular appliance. The objects in the codebase are designed
to function similarly to REST API based objects where you have a Collection object that
handles the creation/searching/non-instance functions, and then an Entity object that handles
the particular instance usage.

Arguments
---------

A collection object **must** take an appliance as its **first** argument. This is to ensure
that

a) any objects created with the collection will have the correct context and
b) that there is a consistent API for collection objects.

An entity object **must** take a collection as its **first** argument. This is to ensure that

a) the entity can access an appliance through its collecion and
b) that there is a consistent API for collection objects

.. warning:: Objects **should** never be instantiated directly. They **should** always come from a
             collection.


Collection Methods
------------------

* ``__init__()`` - The collection object **must** take an ``appliance`` argument as its first argument
  and assign this to the ``self.appliance`` attribute.
* ``instantiate()`` - The collection object **should** provide an ``instantiate()`` method which
  will simply return an entity instance with the supplied arguments. It **must** pass ``self``
  as the first argument so that the user doesn't have to.
* ``create()`` - The collection object **should** provider a ``create()`` method where appropriate.
  This method will attempt to create the object on the appliance and **must** then call
  ``self.instantiate`` and return the object.

.. note:: The ``__init__()`` method could in the future become part automatic in the BaseCollection class
          but this is a future feature and is not yet planned.

.. warning:: Failure to comply with the above guidelines in the future may result in an Exception
             being raised

Entity Methods
--------------

* ``__init__()`` - The entity object **must** take a ``collection`` argument as its first argument
  and assign this to the ``self.collection`` attribute. It **must** then assign ``self.appliance`` to
  be equal to ``self.collection.appliance``

.. note:: The ``__init__()`` method could in the future become part automatic in the BaseEntity class
          but this is a future feature and is not yet planned.

.. warning:: Failure to comply with the above guidelines in the future may result in an Exception
             being raised

Example
-------

Below is an example of a generic object using the collection and entity relationships

.. code-block:: python

                from cfme.utils.appliance import BaseCollection, BaseEntity

                class ObjectCollection(BaseCollection):
                    """An object collection"""

                    def __init__(self, appliance):
                        self.appliance = appliance

                    def instantiate(self, name, label):
                        return Object(self, name, label)

                    def create(self, name, label):
                        run_create(name, label)
                        return self.instantiate(name, label)

                class Object(BaseEntity):
                    """An object entity"""

                    def __init__(self, collection, name, label):
                        self.collection = collection
                        self.appliance = self.collection.appliance

                    def update(self, *updates):
                        some_update_mechanism(*updates)

An example of the models usage in testing is described below

.. code-block:: python

                from some.model import ObjectCollection

                def test_something_good(appliance):
                    """A test for something good"""

                    oc = ObjectCollection(appliance)
                    ob = oc.create('ObName', 'ObLabel')
                    ob.update({'label': 'Edited'})
