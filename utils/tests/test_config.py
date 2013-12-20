import os

import pytest

from utils import conf

test_yaml_contents = '''
test_key: test_value
'''

local_test_yaml_contents = '''
test_key: test_overridden_value
'''


@pytest.fixture(scope='function')
def test_yaml(request, random_string):
    test_yaml = create_test_yaml(request, test_yaml_contents, random_string)
    filename, ext = os.path.splitext(os.path.basename(test_yaml.name))
    return filename


# This is broken out into a non-fixture func
# to facilitate making local yamls overrides
def create_test_yaml(request, contents, filename, local=False):
    if local:
        suffix = '.local.yaml'
    else:
        suffix = '.yaml'
    filename += suffix

    confdir = request.session.fspath.join('conf')
    full_path = str(confdir.join(filename))

    test_yaml = open(full_path, 'w')
    test_yaml.write(contents)
    test_yaml.flush()
    test_yaml.seek(0)

    request.addfinalizer(lambda: os.remove(full_path))
    request.addfinalizer(lambda: conf.clear())

    return test_yaml


def test_conf_yamls_dict(test_yaml):
    # Dict lookup method works
    assert conf[test_yaml]['test_key'] == 'test_value'


def test_conf_yamls_attr(test_yaml):
    # Attribute lookup method works
    assert getattr(conf, test_yaml)['test_key'] == 'test_value'


def test_conf_yamls_override(request, test_yaml):
    # Make a .local.yaml file with the same root name as test_yaml,
    # Check that the local override works.
    with create_test_yaml(request, local_test_yaml_contents, test_yaml, local=True):
        assert conf[test_yaml]['test_key'] == 'test_overridden_value'


def test_conf_yamls_import(test_yaml):
    # Emulate from utils.conf import $test_yaml
    mod = __import__('utils.conf', globals(), locals(), [test_yaml])
    assert getattr(mod, test_yaml) == conf[test_yaml]


def test_conf_yamls_not_found(random_string):
    # Make sure the the raising of ConfigNotFoundException
    # is caught as conf.NotFoundException
    try:
        conf[random_string]
    except conf.NotFoundException:
        # test passes, return out
        return

    pytest.fail('conf.NotFoundException not raised for nonexistent yaml')
