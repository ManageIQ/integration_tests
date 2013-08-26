import random

import pytest
from unittestzero import Assert

from common import randomness

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium,
]

def test_generate_random_string_noargs():
    random_string = randomness.generate_random_string()
    # 8 is the default length
    Assert.equal(len(random_string), 8)

def test_generate_random_string_args():
    length = 16
    random_string = randomness.generate_random_string(length)
    Assert.equal(len(random_string), length)

def test_generate_random_int_noargs():
    # maxint is the default max, so no need to check against it
    random_int = randomness.generate_random_int()
    Assert.greater(random_int, 0)

def test_generate_random_int_args():
    maxvalue = 1
    random_int = randomness.generate_random_int(maxvalue)
    Assert.greater_equal(random_int, 0)
    Assert.less_equal(random_int, maxvalue)

def test_generate_random_uuid():
    # Not sure if there's a better test than a string of normal uuid length (36)
    uuid = randomness.generate_random_uuid_as_str()
    Assert.equal(len(uuid), 36)
    Assert.true(isinstance(uuid, basestring))

def test_randomness_fixtures(random_uuid_as_string, random_string):
    # Make sure the fixtures work as intended
    Assert.equal(len(random_uuid_as_string), 36)
    Assert.true(isinstance(random_uuid_as_string, basestring))
    Assert.true(isinstance(random_string, basestring))

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
        Assert.not_equal(self.after['str'], self.before['str'])
        Assert.not_equal(self.after['tuple'], self.before['tuple'])
        Assert.not_equal(self.after['list'], self.before['list'])
        Assert.not_equal(self.after['set'], self.before['set'])

    def test_randomizevalues_type(self):
        # Object type should still be dict
        Assert.true(isinstance(self.after, type(self.before)))

    def test_randomizevalues_bogus_randomizer(self):
        # Unmatched randomizer shouldn't change
        Assert.equal(self.after['notrandom'], self.before['notrandom'])

    def test_randomizevalues_again(self):
        # If we generate the dict again, it should be newly randomized
        Assert.not_equal(self.after, self.again)
