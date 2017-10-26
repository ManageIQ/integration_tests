Designing Models
================

Collections/Entity Model
------------------------

In general, any object that is represented in the MiQ Appliance is going to be only relevant
along with the context of a particular appliance. The objects in the codebase are designed
to function similarly to REST API based objects where you have a Collection object that
handles the creation/searching/non-instance functions, and then an Entity object that handles
the particular instance usage.

.. warning:: The Collections/Entity model is now at version 3 and is constructed differently to the previous
             iteration. Please read this carefully.

Changes to previous model versions
----------------------------------

Previously, in versions 1 and 2 of the Collection/Entity model we required people to design accomodate
certain arguments as the first arguments to the collection and entity objects. In version 1 there was no
checking against the order of these arguments. Version 2 became a little more strict. In version 3, the
model designer has all of this taken out of their hands as we use the attrs library and subclassing
to design a better Collections/Entity model.

Take the example below

.. code-block:: python

                @attr.s
                class Repository(BaseEntity, Fillable):
                    """A class representing one Embedded Ansible repository in the UI."""

                    name = attr.ib()
                    url = attr.ib()
                    description = attr.ib(default="")
                    scm_credentials = attr.ib(default=None)
                    scm_branc = attr.ib(default=False)
                    clean = attr.ib(default=False)
                    delete_on_update = attr.ib(default=False)

                    _collections = {'playbooks': PlaybooksCollection}

                    def exists(self):
                        pass

                @attr.s
                class RepositoryCollection(BaseCollection):
                    """Collection object for the :py:class:`cfme.ansible.repositories.Repository`."""

                    ENTITY = Repository

                    def create(self, name, url, description=None, scm_credentials=None, scm_branch=None,
                               clean=None, delete_on_update=None, update_on_launch=None):
                        pass

Instantiating objects
---------------------

Collection objects should be obtained via an ``IPAppliance`` object. All base/root level objects, that
is objects which have an appliance as their parent, will be accessible via the ``IPAppliance`` objects
``collections`` manager.

.. note:: Not all collections objects are yet available via the ``IPAppliance`` object.

See the example below which demonstrates how to obtain a Datastore collection, and then instantiate
a ``Datastore`` object.

.. code-block:: python

                provider = get_crud('vsphere55')  # An example provider

                dc = appliance.collections.datastore
                dc.instantiate('name', provider)

Filtering collections
---------------------

Some collections support filtering. This means that the base/root collection can be asked to supply a subset
of the information if would normally return using the ``all()`` or indeed other methods. To filter a
collection object, use the following pattern

.. code-block:: python

                dc = appliance.collection.datastore
                dc_filtered = dc.filter({'provider': provider})

Automatically generated filtered collections
--------------------------------------------

``BaseEntity`` objects have the special ability to create filtered collections. These appear, much
like the ``collections`` attribute on the ``IPAppliance`` instances. Consider the example above where
the ``Repository`` object is given the ``_collections`` attribute. This contains a dictionary of
collection names, along with the collection class that should be instantiated. The collection is then
instantiated with the following filter, like so:

.. code-block:: python

                repo = appliance.collections.repositories.all()[0]
                playbook_collection = repo.collections.playbooks
                playbook_collection.all()  # returns ONLY playbooks from that repo

                # equivalent code
                playbook_collection = PlaybookCollection(self.appliance, filters={'parent': self})

In the example above, the ``BaseEntity`` automatically instantiates the playbook collection object
with a ``parent`` filter. The playbook collection object would then need to honour that filter
when returning the playbooks. A collection isn't under any obligation to support a certain filter.

.. note:: In the future filter names which are supported may need to be defined somewhere to allow
          unsupported filters to be reported as warnings.

Collection Methods
------------------

* ``__init__()`` - This method is hidden inside the ``BaseCollection`` object and shouldn't be
  overidden without good reason. There are exceptional circumstances and these should be discussed
  with a core developer.
  done at init time, using ``__attrs_post_init__`` method is used instead.
* ``instantiate()`` - This method is provided by the ``BaseCollection`` and uses the ``ENTITY``
  attribute of the collection class to determine which class to use in creating the entity.
* ``create()`` - The collection object **should** provider a ``create()`` method where appropriate.
  This method will attempt to create the object on the appliance **must** call
  ``self.instantiate`` to obtain the object to return.


Entity Methods
--------------

* ``__init__()`` - This method is hidden inside the ``BaseEntity`` object and shouldn't be overidden
  without good reason. There are exceptional circumstances and these should be discussed
  with a core developer.


Example
-------

Below is an example of the usage of a collection object described above

.. code-block:: python

                repo = appliance.collections.ansible_repositories.all()[0]

                playbook = repo.collections.playbooks.all()[0]

                playbook.update({'name': 'updated_name'})
