import pytest
from pytest_mozwebqa import split_class_and_test_names
from pytest_mozwebqa.selenium_client import Client

def pytest_runtest_setup(item):
    # If we're using the selenium fixture, mark the test as
    # skip_selenium to prevent mozwebqa from autostarting the browser,
    # but we still want mozwebqa for passing testsetup to page objects
    if 'selenium' in item.funcargnames and 'skip_selenium' not in item.keywords:
        item.keywords['skip_selenium'] = True

@pytest.fixture
def selenium(mozwebqa, request):
    """A fixture giving the user more control over the mozwebqa selenium client"""
    # Start to bootstrap the selenium client like mozwebqa does,
    # Doesn't currently support sauce labs, but could be made to do so if needed
    test_id = '.'.join(split_class_and_test_names(request.node.nodeid))
    mozwebqa.selenium_client = Client(test_id, request.session.config.option)

    def cm_wrapper(url, page_obj):
        return SeleniumContextManager(mozwebqa, url, page_obj)

    return cm_wrapper

class SeleniumContextManager(object):
    def __init__(self, testsetup, url, page_obj):
        self.testsetup = testsetup
        self.url = url
        self.page_obj = page_obj

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

        self.testsetup.base_url = self.url
        self.testsetup.selenium.get(self.url)
        return self.page_obj(self.testsetup)

    def __exit__(self, *args, **kwargs):
        self.testsetup.selenium_client.stop()


