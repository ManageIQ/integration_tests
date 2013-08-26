import pytest

from common import randomness

@pytest.fixture  # IGNORE:E1101
def random_uuid_as_string():
    '''Creates a random uuid and returns is as a string'''
    return randomness.generate_random_uuid_as_str()

@pytest.fixture
def random_string():
    '''Generate a random string for use in tests'''
    return randomness.generate_random_string()
