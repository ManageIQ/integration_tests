from __future__ import unicode_literals

def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme')
    parser.addoption("--page-screenshots", action="store_true", default=False,
        help="take screenshots for each page visited")
