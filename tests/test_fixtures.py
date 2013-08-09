import pytest
from unittestzero import Assert

from plugin import navigation

fixture_names = filter(lambda x: x.endswith('_pg'), dir(navigation))

@pytest.mark.nondestructive
@pytest.mark.parametrize('fixture_name', fixture_names)
def test_fixture(mozwebqa, fixture_name):
	home_pg = navigation.home_page_logged_in(mozwebqa)
	fixture_pg = getattr(navigation, fixture_name)(home_pg)
	Assert.true(fixture_pg.is_the_current_page)
