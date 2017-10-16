from cfme.utils.appliance import BaseCollection, BaseEntity

import pytest

data = [
    {'name': 'john', 'age': '42'},
    {'name': 'max', 'age': '34'},
    {'name': 'simone', 'age': '24'}
]


class Vet(BaseEntity):
    def init(self, name, age):
        self.name = name
        self.age = age


class VetCollection(BaseCollection):
    ENTITY = Vet

    def instantiate(self, name, age):
        return self.ENTITY(self, name, age)

    def all(self):
        items = []
        for info in data:
            items.append(self.instantiate(info['name'], info['age']))
        return items


@pytest.fixture
def collection():
    return VetCollection(None)


def test_collection(collection):
    print collection.all()
