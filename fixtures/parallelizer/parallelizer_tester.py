"""parallelizer tester

Useful to make sure tests are being parallelized properly, and then reported correctly.

This file is named specially to prevent being picked up by py.test's default collector, and should
not be run during a normal test run.

"""
import random
from time import sleep

import pytest

# uncommment this to slow things down, if desired
# pytestmark= pytest.mark.usefixtures("wait")

num_copies = 20


@pytest.fixture(
    params=xrange(10, 10 * num_copies),
    autouse=True,
    scope='module',
)
def the_param():
    pass


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
