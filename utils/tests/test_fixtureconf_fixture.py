from __future__ import unicode_literals
import pytest

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium
]


@pytest.mark.fixtureconf('positional argument', kwarg='keyword argument')
def test_fixtureconf_fixture_with_mark(fixtureconf):
    # args and kwargs should be in fixtureconf
    assert fixtureconf['args'] == ('positional argument',)
    assert fixtureconf['kwarg'] == 'keyword argument'


def test_fixtureconf_fixture_without_mark(fixtureconf):
    # no mark = no args stored in fixtureconf, but the fixture should still work
    assert fixtureconf == {'args': (), }
