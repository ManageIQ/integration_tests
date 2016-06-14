"""parallelizer tester

Useful to make sure tests are being parallelized properly, and then reported correctly.

This file is named specially to prevent being picked up by py.test's default collector, and should
not be run during a normal test run.

"""
import random
from time import sleep

import pytest
from utils import testgen

# add 'wait' to this to slow things down, if desired
pytestmark = pytest.mark.usefixtures('param')
# increase or decrease this to change the number of tests generated
num_copies = 20


def pytest_generate_tests(metafunc):
    # Starts at 10 for vane reason: Artifactor report does a naive sort, so 10 comes before 1
    ids = [i + 10 for i in xrange(num_copies)]
    random.shuffle(ids)
    argvalues = [[v] for v in ids]
    testgen.parametrize(metafunc, ['param'], argvalues, ids=ids, scope='module')


@pytest.fixture
def wait():
    # Add some randomness to make sure reports are getting mixed up like they would in a "real" run
    sleep(random.random() * 5)


@pytest.fixture
def setup_fail():
    raise Exception('I failed to setup!')


@pytest.yield_fixture
def teardown_fail():
    yield
    raise Exception('I failed to teardown!')


def test_passes():
    pass


def test_fails():
    raise Exception('I failed!')


@pytest.mark.xfail
def test_xfails():
    raise Exception('I failed!')


@pytest.mark.xfail
def test_xpasses():
    pass


def test_fails_setup(setup_fail):
    pass


def test_fails_teardown(teardown_fail):
    pass


@pytest.mark.skipif('True')
def test_skipped():
    pass
