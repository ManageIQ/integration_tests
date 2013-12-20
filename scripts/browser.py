#!/usr/bin/env python
from IPython import embed

from fixtures import navigation as nav
from utils.browser import browser_session, testsetup

with browser_session() as browser:
    pg = nav.home_page_logged_in(testsetup)
    embed()
