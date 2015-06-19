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

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager

from cfme.configure.about import product_assistance as about
from utils import version


def pdf_get_text(file_obj, page_nums):
    output = StringIO()
    manager = PDFResourceManager()
    laparams = LAParams(all_texts=True, detect_vertical=True)
    converter = TextConverter(manager, output, laparams=laparams)
    interpreter = PDFPageInterpreter(manager, converter)
    for page in PDFPage.get_pages(file_obj, page_nums):
        interpreter.process_page(page)
    converter.close()
    text = output.getvalue().replace('\n', ' ')
    output.close()
    return text


@pytest.fixture(scope="module")
def guides():
    return [
        loc
        for loc
        in about.locators.iterkeys()
        if loc.endswith("_guide")
        and (
            version.pick(about.locators[loc])
            if isinstance(about.locators[loc], dict)
            else about.locators[loc]
        ) is not None]


@pytest.fixture(scope="session")
def docs_info():
    if version.current_version() < "5.4.0.1" or (not version.appliance_is_downstream()):
        return [
            'Control',
            'Lifecycle and Automation',
            'Quick Start',
            'Settings And Operations',
            'Insight',
            'Integration Services'
        ]
    else:
        return [
            'Insight',
            'Control',
            'Lifecycle and Automation',
            'REST API',
            'SOAP API',
            'User',
            'Settings and Operations'
        ]


@pytest.mark.sauce
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


@pytest.mark.meta(blockers=[1145326, "GH#ManageIQ/manageiq:2246"])
def test_contents(guides, soft_assert):
    """Test contents of each document."""
    pytest.sel.force_navigate("about")
    precomp_noguide = re.compile("(.*) Guide")
    cur_ver = version.current_version()
    for link in guides:
        locator = getattr(about, link)
        url = pytest.sel.get_attribute(locator, "href")
        data = requests.get(url, verify=False)
        pdf_titlepage_text_low = pdf_get_text(StringIO(data.content), [0]).lower()
        # don't include the word 'guide'
        title_text_low = precomp_noguide.search(pytest.sel.text(locator)).group(1).lower()
        expected = [title_text_low]
        if cur_ver == version.LATEST:
            expected.append('manageiq')
        else:
            expected.append('cloudforms')
            maj_min = '{}.{}'.format(cur_ver.version[0], cur_ver.version[1])
            expected.append(version.get_product_version(maj_min))

        for exp_str in expected:
            soft_assert(exp_str in pdf_titlepage_text_low,
                "{} not in {}".format(exp_str, pdf_titlepage_text_low))


@pytest.mark.sauce
@pytest.mark.meta(blockers=[1232434, "GH#ManageIQ/manageiq:2246"])
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
