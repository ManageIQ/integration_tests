'''
@author: psavage
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
import requests
from unittestzero import Assert


@pytest.mark.nondestructive
class TestDocs:
    def test_docs(self, cnf_about_pg):
        '''Tests all docs are reachable'''
        for link in cnf_about_pg.docs_links:
            Assert.equal(
                requests.head(link, verify=False).status_code, 200,
                link + " : Is not accessible")
