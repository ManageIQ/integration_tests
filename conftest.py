import pytest

def _read(filename):
    stream = file(filename, 'r')
    import yaml
    return yaml.load(stream)

def pytest_addoption(parser):
    group = parser.getgroup('cfme', 'cfme')
    group._addoption('--cfmedata',
                     action='store',
                     dest='cfme_data_filename',
                     metavar='path',
                     help='location of yaml file containing fixture data') 

def pytest_runtest_setup(item):
    if item.config.option.cfme_data_file:
        CfmeSetup.data = _read(item.config.option.cfme_data_filename)


@pytest.fixture
def cfme_data(request):
    return CfmeSetup(request)

class CfmeSetup:
    '''
        This class is just used for monkey patching
    '''
    def __init__(self, request):
        self.request = request
