# -*- coding: utf-8 -*-
import pytest
import re
import requests
try:
    # Faster, C-ext
    from cStringIO import StringIO
except ImportError:
    # Slower, pure python
    from StringIO import StringIO
from PyPDF2 import PdfFileReader

from cfme.configure.about import product_assistance as about


@pytest.fixture(scope="module")
def guides():
    return [loc for loc in about.locators.iterkeys() if loc.endswith("_guide")]


@pytest.fixture(scope="session")
def docs_info():
    return [
        'Control',
        'Lifecycle and Automation',
        'Quick Start',
        'Settings And Operations',
        'Insight',
        'Integration Services'
    ]


def test_links(guides, soft_assert):
    """Test whether the PDF documents are present."""
    pytest.sel.force_navigate("about")
    for link in guides:
        locator = getattr(about, link)
        url = pytest.sel.get_attribute(locator, "href")
        soft_assert(
            requests.head(url, verify=False).status_code == 200,
            "'{}' is not accessible".format(pytest.sel.text(locator).encode("utf-8").strip())
        )


@pytest.mark.meta(blockers=[1026943])
def test_contents(guides, soft_assert):
    """Test contents of each document."""
    pytest.sel.force_navigate("about")
    for link in guides:
        locator = getattr(about, link)
        url = pytest.sel.get_attribute(locator, "href")
        data = requests.get(url, verify=False)
        pdf = PdfFileReader(StringIO(data.content))
        pdf_info = pdf.getDocumentInfo()
        soft_assert("CloudForms" in pdf_info["/Title"], "CloudForms is not in the title!")

        # don't include the word 'guide'
        p = re.compile("(.*) Guide")
        title_text = p.search(pytest.sel.text(locator)).group(1).lower()
        pdf_title = pdf_info["/Title"].lower()
        soft_assert(title_text in pdf_title, "{} not in {}".format(
            title_text, pdf_title))


@pytest.mark.meta(blockers=[1026939])
def test_info(guides, soft_assert):
    pytest.sel.force_navigate("about")
    for link in guides:
        l_a = getattr(about, link)
        # l_icon also implicitly checks for the icon url == text url
        l_icon = lambda: pytest.sel.element(
            "../a[contains(@href, '{}')]/img".format(
                pytest.sel.get_attribute(l_a, "href").rsplit("/", 1)[-1]
            ),
            root=l_a
        )
        l_icon_a = lambda: pytest.sel.element("..", root=l_icon)
        soft_assert(
            pytest.sel.get_attribute(l_icon, "alt") == pytest.sel.get_attribute(l_icon_a, "title"),
            "Icon alt attr should match icon title attr ({})".format(pytest.sel.text(l_a))
        )
        soft_assert(
            pytest.sel.get_attribute(l_icon_a, "href") == pytest.sel.get_attribute(l_a, "href"),
            "Icon url should match text url ({})".format(pytest.sel.text(l_a))
        )


@pytest.mark.meta(blockers=[1026946])
def test_all_docs_present(guides, docs_info):
    pytest.sel.force_navigate("about")
    docs_list = list(docs_info)
    for link in guides:
        for doc in docs_list:
            if doc.lower() in pytest.sel.text(getattr(about, link)).lower():
                break
        else:
            continue
        docs_list.remove(doc)
    assert len(docs_list) == 0, "All documents should be available ({} are missing)".format(
        ", ".join(docs_list)
    )
