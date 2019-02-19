import attr
import pytest

from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.modeling.base import EntityCollections
from cfme.modeling.base import load_appliance_collections
from cfme.modeling.base import parent_of_type
from cfme.utils.appliance import DummyAppliance


@attr.s
class MyEntity(BaseEntity):
    name = attr.ib()


@attr.s
class MyCollection(BaseCollection):
    ENTITY = MyEntity


@attr.s
class MyNewEntity(BaseEntity):
    name = attr.ib()

    _collections = {'entities': MyCollection}


@attr.s
class MyEntityWithDeclared(BaseEntity):

    collections = EntityCollections.declared(
        entities=MyCollection,
    )


@attr.s
class MyNewCollection(BaseCollection):
    ENTITY = MyNewEntity


@pytest.fixture
def dummy_appliance():
    return DummyAppliance()


def test_appliance_collections_dir(dummy_appliance):
    base_level_collections = set(load_appliance_collections())
    assert base_level_collections.issubset(dir(dummy_appliance.collections))


def test_appliance_collection(dummy_appliance):
    obj = dummy_appliance.collections.datastores
    assert obj.parent == dummy_appliance


def test_appliance_collections_instantiate(dummy_appliance):
    obj = dummy_appliance.collections.datastores.instantiate('doop', 'dedoop')
    assert obj
    assert obj.parent == dummy_appliance.collections.datastores
    assert obj.appliance == dummy_appliance


def test_appliance_collection_object_filter(dummy_appliance):
    filtered_obj = dummy_appliance.collections.datastores.filter({'filtera': 'filterb'})
    assert filtered_obj.parent == dummy_appliance
    assert filtered_obj.filters['filtera'] == 'filterb'


def test_appliance_collection_chain_filter(dummy_appliance):
    filtered_obj = dummy_appliance.collections.datastores.filter({'filtera': 'filterb'})
    nested_filtered_obj = filtered_obj.filter({'filterc': 'filterd'})
    assert filtered_obj.parent == dummy_appliance
    assert nested_filtered_obj.filters['filtera'] == 'filterb'
    assert nested_filtered_obj.filters['filtera'] == 'filterb'


def test_object_collections(dummy_appliance):
    obj = MyNewCollection(dummy_appliance).instantiate('name')
    assert obj.collections.entities


def test_object_collections_parent_filter(dummy_appliance):
    obj = MyNewCollection(dummy_appliance).instantiate('name')
    assert obj.collections.entities.filters['parent'] == obj


def test_parent_relationship(dummy_appliance):
    obj = MyNewCollection(dummy_appliance).instantiate('name')
    new_obj = obj.collections.entities.instantiate('boop')
    assert new_obj.parent.parent.parent.parent == dummy_appliance


def test_parent_walker(dummy_appliance):
    obj = MyNewCollection(dummy_appliance).instantiate('name')
    new_obj = obj.collections.entities.instantiate('boop')
    assert parent_of_type(new_obj, MyNewEntity) == obj
    assert parent_of_type(new_obj, DummyAppliance) == dummy_appliance


def test_declared_entity_collections(dummy_appliance):
    obj = MyEntityWithDeclared(dummy_appliance)
    new_obj = obj.collections.entities.instantiate('boop')
    assert parent_of_type(new_obj, MyEntityWithDeclared) is obj
    assert parent_of_type(new_obj, DummyAppliance) is dummy_appliance
