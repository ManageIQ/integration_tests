import random

import pytest

from common import randomness

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium,
]

def test_generate_random_string_noargs():
    random_string = randomness.generate_random_string()
    # 8 is the default length
    assert len(random_string) == 8

def test_generate_random_string_args():
    length = 16
    random_string = randomness.generate_random_string(length)
    assert len(random_string) == length

def test_generate_random_int_noargs():
    # maxint is the default max, so no need to check against it
    random_int = randomness.generate_random_int()
    assert 0 <= random_int

def test_generate_random_int_args():
    max = 1
    random_int = randomness.generate_random_int(max)
    assert 0 <= random_int <= max

def test_generate_random_uuid():
    # Not sure if there's a better test than a string of normal uuid length (36)
    uuid = randomness.generate_random_uuid_as_str()
    assert len(uuid) == 36
    assert isinstance(uuid, basestring)

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
        # Object type should still be dict
        assert isinstance(self.after, type(self.before))

    def test_randomizevalues_bogus_randomizer(self):
        # Unmatched randomizer shouldn't change
        assert self.after['notrandom'] == self.before['notrandom']

    def test_randomizevalues_again(self):
        # If we generate the dict again, it should be newly randomized
        again = randomness.RandomizeValues.from_dict(self.before)
        assert self.after != self.again

