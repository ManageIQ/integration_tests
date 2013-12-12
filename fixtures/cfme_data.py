import pytest

from utils.cfme_data import load_cfme_data


def pytest_addoption(parser):
    group = parser.getgroup('cfme', 'cfme')
    group._addoption('--cfmedata', action='store', default=None,
        dest='cfme_data_filename', metavar='CFME_DATA',
        help='location of yaml file containing fixture data')

@pytest.fixture(scope="session")
def cfme_data(request):
    return load_cfme_data(request.config.option.cfme_data_filename)
