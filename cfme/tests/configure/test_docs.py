# -*- coding: utf-8 -*-
import pytest
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

from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger

# This is list of tested links expected to be on the documentation page
# Keys here correspond to nested view names from configure.documentation.LinksView
doc_titles = {
    'policies': 'policies and profiles guide',
    'general': 'general configuration',
    'inventory': 'managing infrastructure and inventory',
    'automation': 'methods available for automation',
    'monitoring': 'monitoring, alerts, and reporting',
    'providers': 'managing providers',
    'rest': 'red hat cloudforms rest api',
    'scripting': 'scripting actions in cloudforms',
    'vm_hosts': 'provisioning virtual machines and hosts'}


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


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
@pytest.mark.sauce
def test_links(appliance):
    """Test whether the PDF documents are present."""
    view = navigate_to(appliance.server, 'Documentation')
    for link_widget in view.links.sub_widgets:
        # link_widget is nested view, we care about 'link' widget here
        try:
            href = view.browser.get_attribute(attr='href', locator=link_widget.link.locator)
        except AttributeError:
            logger.warning('Skipping link check, No link widget defined for {}'.format(
                link_widget.TEXT))
            continue
        # Check the link is reachable
        try:
            resp = requests.head(href, verify=False, timeout=10)
        except (requests.Timeout, requests.ConnectionError) as ex:
            pytest.fail(str(ex))

        assert 200 <= resp.status_code < 400, \
            "Unable to access URL '{}' from doc link ({})".format(href, link_widget.read())


@pytest.mark.tier(3)
@pytest.mark.ignore_stream("upstream")
def test_contents(appliance, soft_assert):
    """Test title of each document."""
    view = navigate_to(appliance.server, 'Documentation')
    cur_ver = appliance.version
    for doc_type, title in doc_titles.items():
        doc_widget = getattr(view.links, doc_type, None)
        if not doc_widget:
            logger.warning('Skipping contents check for document: "{}: {}", no widget to read'
                           .format(doc_type, title))

        href = view.browser.get_attribute(attr='href',
                                          locator=doc_widget.link.locator)
        data = requests.get(href, verify=False)
        pdf_titlepage_text_low = pdf_get_text(StringIO(data.content), [0]).lower()
        # don't include the word 'guide'
        expected = [title]
        if cur_ver == version.LATEST:
            expected.append('manageiq')
        else:
            expected.append('cloudforms')
            maj_min = '{}.{}'.format(cur_ver.version[0], cur_ver.version[1])
            expected.append(version.get_product_version(maj_min))

        for exp_str in expected:
            soft_assert(exp_str in pdf_titlepage_text_low, "{} not in {}"
                                                           .format(exp_str, pdf_titlepage_text_low))


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.ignore_stream("upstream")
def test_info(appliance, soft_assert):
    """
    Test the alt/title and href attributes.
    Each doc link is an anchor with image child element, and then the link text anchor
    Verify anchor title matches alt in anchor image
    Verify image anchor href matches link text href"""
    view = navigate_to(appliance.server, 'Documentation')
    for link_widget in view.links.sub_widgets:
        if not (hasattr(link_widget, 'img_anchor') or hasattr(link_widget, 'img')):
            # This check only applies to the PDF links, essentially factors out customer portal link
            continue
        # Check img_anchor title attribute against img alt attribute
        title = view.browser.get_attribute(attr='title', locator=link_widget.img_anchor.locator)
        alt = view.browser.get_attribute(attr='alt', locator=link_widget.img.locator)
        soft_assert(title == alt, 'Image title/alt check failed for documentation link: {}'
                                  .format(link_widget.TEXT))

        # Check img_anchor href matches link text href
        img_href = view.browser.get_attribute(attr='href', locator=link_widget.img_anchor.locator)
        text_href = view.browser.get_attribute(attr='href', locator=link_widget.link.locator)
        soft_assert(img_href == text_href, 'href attributes check failed for documentation link: {}'
                                           .format(link_widget.TEXT))


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_all_docs_present(appliance):
    """
    Check that all the documents that we expect to be in the UI are present
    Use the doc_titles dict keys to query widget is_displayed
    """
    view = navigate_to(appliance.server, 'Documentation')
    for doc_type, title in doc_titles.items():
        # check widget exists
        assert hasattr(view.links, doc_type)
        # check widget (and therefore document link) is displayed
        assert getattr(view.links, doc_type).is_displayed
