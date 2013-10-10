import pytest
from pytest_mozwebqa import split_class_and_test_names
from pytest_mozwebqa.selenium_client import Client

from plugin import navigation


def pytest_runtest_setup(item):
    # If we're using the selenium fixture, mark the test as
    # skip_selenium to prevent mozwebqa from autostarting the browser,
    # but we still want mozwebqa for passing testsetup to page objects
    if 'selenium' in item.funcargnames and 'skip_selenium' not in item.keywords:
        item.keywords['skip_selenium'] = True


@pytest.fixture
def selenium(mozwebqa, request):
    """A fixture giving the user more control over the mozwebqa selenium client

    Used as a context manager, and takes a fixture (or fixture name) and optional
    base_url as arguments, allowing navigation to any page on any appliance.

    Example usage:

        with selenium('cnf_about_pg') as pg:
            pg.do_stuff()

    To connect to another appliance, pass in a new base_url:

        with selenium('cnf_about_pg', 'https://10.11.12.13') as pg:
            pg.do_stuff()

    """
    # Start to bootstrap the selenium client like mozwebqa does,
    # Doesn't currently support sauce labs, but could be made to do so if needed
    test_id = '.'.join(split_class_and_test_names(request.node.nodeid))
    mozwebqa.selenium_client = Client(test_id, request.session.config.option)

    def cm_wrapper(fixture, base_url=None):
        return SeleniumContextManager(mozwebqa, fixture, base_url)

    return cm_wrapper


class SeleniumContextManager(object):
    def __init__(self, testsetup, fixture, base_url=None):
        self.testsetup = testsetup

        # If fixture is a string, get the real callable from navigation by name
        if isinstance(fixture, basestring):
            self.fixture = getattr(navigation, fixture)
        # Otherwise, assume this is already a fixture
        else:
            self.fixture = fixture

        # Override testsetup base_url for connecting to different appliances in
        # a test run
        if base_url:
            self.testsetup.base_url = base_url

    def __enter__(self):
        # More mozwebqa bootstrapping, start the browser, expose some
        # client attrs on testsetup, navigate to the requested url,
        # return a Page instance with the current testsetup
        # This should mimic the behavior of mozwebqa as closely as possible

        self.testsetup.selenium_client.start()
        copy_attrs = (
            'selenium',
            'timeout',
            'default_implicit_wait'
        )
        for attr in copy_attrs:
            setattr(self.testsetup, attr, getattr(self.testsetup.selenium_client, attr))

        self.testsetup.selenium.maximize_window()
        home_page_logged_in = navigation.home_page_logged_in(self.testsetup)
        # If you passed in the home_page_logged_in fixture, this will be funny.
        return self.fixture(home_page_logged_in)

    def __exit__(self, *args, **kwargs):
        self.testsetup.selenium_client.stop()
