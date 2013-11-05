'''
@author: psavage
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
import requests
import StringIO
from unittestzero import Assert
from PyPDF2 import PdfFileReader


@pytest.fixture
def docs_info(request):
    '''Returns required documentation data from cfme_data'''
    docs_list = ['Control',
                'Installation',
                'Lifecycle and Automation',
                'Quick Start',
                'Settings And Operations',
                'Insight',
                'Integration Services']
    return docs_list


@pytest.mark.nondestructive
class TestDocs:
    def test_docs_info(self, cnf_about_pg):
        '''Test all doc links are formed correctly'''
        #
        # Disabling for https://bugzilla.redhat.com/show_bug.cgi?id=1026939
        #
        #for link in cnf_about_pg.docs_links:
        #    Assert.equal(link['icon_alt'], link['icon_title'],
        #                 "Icon alt attr should match icon title attr")
        #    Assert.equal(link['icon_url'], link['text_url'],
        #                 "Icon url should match text url")

    def test_docs_links(self, cnf_about_pg):
        '''Test all links are reachable'''
        for link in cnf_about_pg.docs_links:
            Assert.equal(
                requests.head(link['text_url'], verify=False).status_code,
                200, link['text_url'] + " : Is not accessible")

    def test_docs_contents(self, cnf_about_pg):
        '''Test contents of each document'''
        #
        # Disabling for https://bugzilla.redhat.com/show_bug.cgi?id=1026943
        #
        for link in cnf_about_pg.docs_links:
            doc = requests.get(link['text_url'], verify=False)
            pdf = PdfFileReader(StringIO.StringIO(doc.content))
            pdf_info = pdf.getDocumentInfo()
            #Assert.true(link['text_title'] in pdf_info['/Title'],
            #            "'" + pdf_info['/Title'] + "' should contain '" +
            #            link['text_title'] + "'")

    def test_all_docs_present(self, cnf_about_pg, docs_info):
        '''Test all docs are present as defined in the yaml'''
        #
        # Disabling for https://bugzilla.redhat.com/show_bug.cgi?id=1026946
        #
        docs_list = list(docs_info)
        for link in cnf_about_pg.docs_links:
            for doc in docs_list:
                if doc.lower() in link['text_title'].lower():
                    break
            else:
                continue
            docs_list.remove(doc)
        #Assert.equal(0, len(docs_list),
        #             "All documents should be available '" +
        #             ",".join(docs_list) + "' are missing.")
