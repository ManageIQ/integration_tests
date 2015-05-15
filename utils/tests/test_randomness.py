# -*-coding: utf-8
import pytest
from utils import randomness

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium,
]


def test_randomness_fixtures(random_uuid_as_string, random_string):
    """Make sure the fixtures work as intended"""
    assert len(random_uuid_as_string) == 36
    assert isinstance(random_uuid_as_string, basestring)
    assert isinstance(random_string, basestring)


@pytest.fixture(scope="class")
def random_stash(request):
    request.cls.before = {
        'str': '{random_str}',
        'tuple': ('{random_str}',),
        'list': ['{random_str}'],
        'set': set(['{random_str}']),
        'notrandom': '{random_thisisabogusrandomizer}',
    }
    request.cls.after = randomness.RandomizeValues.from_dict(request.cls.before)
    request.cls.again = randomness.RandomizeValues.from_dict(request.cls.before)


@pytest.mark.usefixtures("random_stash")
class TestRandomizeValues(object):
    def test_randomizevalues(self):
        # These should be different in the two dicts
        assert self.after['str'] != self.before['str']
        assert self.after['tuple'] != self.before['tuple']
        assert self.after['list'] != self.before['list']
        assert self.after['set'] != self.before['set']

    def test_randomizevalues_type(self):
        """Object type should still be dict"""
        assert isinstance(self.after, type(self.before))

    def test_randomizevalues_bogus_randomizer(self):
        """Unmatched randomizer shouldn't change"""
        assert self.after['notrandom'] == self.before['notrandom']

    def test_randomizevalues_again(self):
        """If we generate the dict again, it should be newly randomized"""
        assert self.after != self.again
