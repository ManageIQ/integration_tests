import pytest
from cfme.utils.pytest_shortcuts import fixture_filter


class FakeMetaFunc(object):
    definition = None
    fixturenames = ['a']


def _values(val):
    return tuple(getattr(val, 'values', val))


@pytest.mark.parametrize('structure', [
    pytest.param(pytest.param(1, 2), id='param'),
    pytest.param([1, 2], id='list'),
    pytest.param([1, 2], id='tuple'),
    pytest.param(pytest.mark.skip(reason="fun")((1, 2)), id='legacy_mark')
])
def test_fixture_filter(structure):
    argnames, argvalues = fixture_filter(FakeMetaFunc(), ['a', 'b'], [structure])
    argvalues = [_values(x) for x in argvalues]
    assert argvalues == [(1,)]
