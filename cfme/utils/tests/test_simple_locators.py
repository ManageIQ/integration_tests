import pytest


@pytest.fixture(scope='module')
def test_page(browser, datafile, appliance):
    selenium = appliance.browser.widgetastic.selenium
    test_page_html = datafile('/utils/tests/test_simple_locators/elements.html').read()
    selenium.get('data:text/html;base64,{}'.format(test_page_html.encode('base64')))


@pytest.fixture(scope='function')
def assert_len(appliance):
    sel = appliance.browser.widgetastic.selenium

    def f(locator, required_len):
        assert len(sel.elements(locator)) == required_len
    return f


pytestmark = pytest.mark.usefixtures('test_page')


def test_by_id(assert_len):
    # should exist
    assert_len('#id1', 1)
    assert_len('#id2', 1)

    # shouldn't exist
    assert_len('#id3', 0)


def test_by_class(assert_len):
    # should exist
    assert_len('.class1', 2)
    assert_len('.class2', 1)

    # shouldn't exist
    assert_len('.class3', 0)


def test_by_element_with_id(assert_len):
    # should exist
    assert_len('h1#id1', 1)
    assert_len('h2#id2', 1)

    # shouldn't exist
    assert_len('h1#id2', 0)
    assert_len('h2#id1', 0)


def test_by_element_with_class(assert_len):
    # should exist
    assert_len('h1.class1', 1)
    assert_len('h2.class1', 1)
    assert_len('h2.class2', 1)

    # shouldn't exist
    assert_len('h1.class3', 0)


def test_by_element_with_id_and_class(assert_len):
    # should exist
    assert_len('h1#id1.class1', 1)
    assert_len('h2#id2.class2', 1)
    assert_len('h2#id2.class2', 1)

    # shouldn't exist
    assert_len('h1#id1.class2', 0)
    assert_len('h3#h2.class1', 0)
    assert_len('h1#h2.class3', 0)


def test_by_locator_list(assert_len):
    # should exist
    assert_len(['#id1', '.class2'], 2)

    # shouldn't exist
    assert_len(['#id3', '.class3'], 0)
