#!/usr/bin/env python

import pytest
from unittestzero import Assert
from pages.login import login_page, login


@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("selenium")
def test_login(request):
    print(dir(request.config))
    login(request.config.option.user, request.config.option.password)
    Assert.true(login_page.is_current_page(), "Could not determine if logged in")
