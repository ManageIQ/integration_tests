import pytest

from cached_property import cached_property


@pytest.fixture
def test_object():
    return LazycacheTester()


# The thing that our test properties will return, simulating an "expensive" value
# Also makes it easy to ensure caching is (or isn't) happening
class PropertyObject(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        # simplify equality checks in tests below
        return self.value == other


class LazycacheTester(object):
    @cached_property
    def cached_property(self):
        return PropertyObject('cached')

    @property
    def normal_property(self):
        return PropertyObject(None)


def test_lazycache_property_sanity(test_object):
    # slighty odd test, demonstrates that the entire reason for lazycache existing is sane:
    # properties aren't cached and separate calls return two separate objects
    not_cached = test_object.normal_property
    assert id(not_cached) is not test_object.normal_property


def test_lazycache_get(test_object):
    # Retrive the cached object
    cached = test_object.cached_property
    # the expected value was returned
    assert cached == 'cached'
    # future calls to that property return the exact same object
    assert cached is test_object.cached_property


def test_lazycache_set(test_object):
    # setting works, and doesn't destroy the caching
    test_object.cached_property = 'new value'
    cached = test_object.cached_property
    # the expected value was returned
    assert cached == 'new value'
    # setting a new value didn't destroy the caching behavior
    assert cached is test_object.cached_property


def test_lazycache_del(test_object):
    # set the cache to a different value, then clear
    test_object.cached_property = 'new value'
    del(test_object.cached_property)
    # run the get test again with our test_object to ensure the value is correct
    # and caching is still in-place
    test_lazycache_get(test_object)


def test_lazycache_del_twice(test_object):
    # initialize the cache
    assert test_object.cached_property
    # deleting the property twice also doesn't explode
    del(test_object.cached_property)
    del(test_object.cached_property)


def test_lazycache_del_no_cache(test_object):
    # can call del even if the cache hasn't been created, nothing explodes
    del(test_object.cached_property)
